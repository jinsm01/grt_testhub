"""
LightRAG API 视图
提供知识图谱的构建、查询、可视化等接口
"""
import asyncio
import logging
import os
import shutil
import threading
import uuid
from pathlib import Path
from typing import List

from asgiref.sync import async_to_sync, sync_to_async
from django.db import models, transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


class KnowledgeGraphPagination(PageNumberPagination):
    """知识图谱分页类"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

from apps.projects.models import Project

from .lightrag_service import LightRAGService
from .models import (
    KnowledgeGraph,
    KnowledgeGraphBuildTask,
    KnowledgeGraphQueryHistory,
    RequirementDocument,
)
from .serializers import (
    KnowledgeGraphBuildRequestSerializer,
    KnowledgeGraphQuerySerializer,
    KnowledgeGraphSerializer,
    KnowledgeGraphStatsSerializer,
    KnowledgeGraphVersionCompareSerializer,
    RequirementDocumentSerializer,
    DocumentUploadSerializer,
)

logger = logging.getLogger(__name__)


class KnowledgeGraphViewSet(viewsets.ModelViewSet):
    """知识图谱视图集"""
    
    queryset = KnowledgeGraph.objects.all()
    serializer_class = KnowledgeGraphSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = KnowledgeGraphPagination
    
    def get_queryset(self):
        """只返回当前用户有权限的图谱（包括自己的和公共的）"""
        queryset = super().get_queryset()
        project_id = self.request.query_params.get('project_id')
        search = self.request.query_params.get('search')

        if project_id:
            # 如果指定了项目，返回该项目的图谱
            queryset = queryset.filter(project_id=project_id)
        else:
            # 如果没有指定项目，返回用户的图谱 + 公共图谱
            queryset = queryset.filter(
                models.Q(created_by=self.request.user) | models.Q(is_public=True)
            )
        
        # 搜索功能
        if search:
            queryset = queryset.filter(name__icontains=search)

        return queryset
    
    def perform_create(self, serializer):
        """创建时设置创建者"""
        serializer.save(created_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """删除知识图谱时同时删除文件目录"""
        graph = self.get_object()

        # 删除文件目录
        working_dir = Path(graph.get_working_dir())
        if working_dir.exists():
            try:
                shutil.rmtree(working_dir)
                logger.info(f"已删除知识图谱文件目录: {working_dir}")
            except Exception as e:
                logger.error(f"删除知识图谱文件目录失败 {working_dir}: {str(e)}")

        # 执行数据库删除
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['post'], url_path='batch_delete')
    def batch_delete(self, request):
        """
        批量删除知识图谱

        POST /api/requirement-analysis/knowledge-graphs/batch_delete/
        Request Body: { "ids": [1, 2, 3] }
        """
        ids = request.data.get('ids', [])

        if not ids:
            return Response(
                {'error': '请提供要删除的知识图谱ID列表'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 获取当前用户有权限删除的图谱
        queryset = self.get_queryset().filter(id__in=ids)

        if not queryset.exists():
            return Response(
                {'error': '未找到可删除的知识图谱'},
                status=status.HTTP_404_NOT_FOUND
            )

        deleted_count = 0
        failed_count = 0
        failed_ids = []

        for graph in queryset:
            try:
                # 删除文件目录
                working_dir = Path(graph.get_working_dir())
                if working_dir.exists():
                    try:
                        shutil.rmtree(working_dir)
                        logger.info(f"已删除知识图谱文件目录: {working_dir}")
                    except Exception as e:
                        logger.error(f"删除知识图谱文件目录失败 {working_dir}: {str(e)}")

                # 删除数据库记录
                graph.delete()
                deleted_count += 1
            except Exception as e:
                logger.error(f"删除知识图谱 {graph.id} 失败: {str(e)}")
                failed_count += 1
                failed_ids.append(graph.id)

        return Response({
            'success': True,
            'deleted_count': deleted_count,
            'failed_count': failed_count,
            'failed_ids': failed_ids,
            'message': f'成功删除 {deleted_count} 个知识图谱' + (f'，失败 {failed_count} 个' if failed_count > 0 else '')
        })

    @action(detail=True, methods=['post'])
    def build(self, request, pk=None):
        """
        构建知识图谱
        
        POST /api/requirement-analysis/knowledge-graphs/{id}/build/
        """
        graph = self.get_object()
        
        # 检查图谱状态
        if graph.status == 'building':
            return Response(
                {'error': '知识图谱正在构建中，请稍后再试'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 获取关联的文档
        documents = graph.documents.all()
        if not documents:
            return Response(
                {'error': '知识图谱没有关联文档，无法构建'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 检查文档是否有文本内容
        valid_documents = []
        for doc in documents:
            if doc.extracted_text:
                valid_documents.append(doc)
        
        if not valid_documents:
            return Response(
                {'error': '关联的文档没有文本内容，请先提取文档文本'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 创建构建任务记录
        task = KnowledgeGraphBuildTask.objects.create(
            task_id=task_id,
            graph=graph,
            status='running',
            progress=0,
            current_document=valid_documents[0].title if valid_documents else '',
            started_at=timezone.now()
        )
        
        # 更新图谱状态为构建中
        graph.status = 'building'
        graph.build_started_at = timezone.now()
        graph.save()
        
        # 异步构建
        def build_graph_async():
            try:
                service = LightRAGService(graph.project_id, graph.id)

                # 定义进度回调函数
                def progress_callback(progress, message):
                    try:
                        task.progress = progress
                        task.current_document = message
                        task.save()
                        logger.info(f"知识图谱 {graph.id} 构建进度: {progress}% - {message}")
                    except Exception as e:
                        logger.warning(f"更新进度失败: {e}")

                # 更新任务进度
                task.progress = 10
                task.save()

                result = async_to_sync(service.build_graph)(valid_documents, progress_callback=progress_callback)

                # 更新任务完成
                task.status = 'completed'
                task.progress = 100
                task.completed_at = timezone.now()
                task.save()

                # 更新图谱状态
                graph.status = 'completed'
                graph.node_count = result.get('nodes', 0)
                graph.edge_count = result.get('edges', 0)
                graph.document_count = len(valid_documents)
                graph.build_completed_at = timezone.now()
                graph.save()

                logger.info(f"知识图谱 {graph.id} 构建完成")
            except Exception as e:
                logger.error(f"知识图谱 {graph.id} 构建失败: {e}")

                # 更新任务失败
                task.status = 'failed'
                task.error_message = str(e)
                task.completed_at = timezone.now()
                task.save()

                # 更新图谱状态
                graph.status = 'failed'
                graph.build_error_message = str(e)
                graph.save()
        
        # 启动后台线程
        thread = threading.Thread(target=build_graph_async)
        thread.daemon = True
        thread.start()
        
        return Response({
            'message': '知识图谱构建任务已启动',
            'graph_id': graph.id,
            'task_id': task_id,
            'document_count': len(valid_documents)
        })

    @action(detail=True, methods=['post'])
    def query(self, request, pk=None):
        """
        查询知识图谱
        
        POST /api/requirement-analysis/knowledge-graphs/{id}/query/
        {
            "query": "查询内容",
            "mode": "local" | "global"
        }
        """
        graph = self.get_object()
        
        if graph.status != 'completed':
            return Response(
                {'error': '知识图谱尚未构建完成，无法查询'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 序列化请求数据
        serializer = KnowledgeGraphQuerySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        query_text = serializer.validated_data['query']
        mode = serializer.validated_data.get('mode', 'local')
        
        try:
            service = LightRAGService(graph.project_id, graph.id)
            result = async_to_sync(service.query)(query_text, mode)
            
            # 保存查询历史
            KnowledgeGraphQueryHistory.objects.create(
                graph=graph,
                query=query_text,
                mode=mode,
                response=result.get('response', ''),
                created_by=request.user
            )
            
            return Response({
                'query': query_text,
                'mode': mode,
                'response': result.get('response', ''),
                'sources': result.get('sources', [])
            })
        except Exception as e:
            logger.error(f"查询知识图谱失败: {e}")
            return Response(
                {'error': f'查询失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def graph_data(self, request, pk=None):
        """
        获取知识图谱可视化数据
        
        GET /api/requirement-analysis/knowledge-graphs/{id}/graph_data/
        """
        graph = self.get_object()
        
        if graph.status != 'completed':
            return Response(
                {'error': '知识图谱尚未构建完成'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            service = LightRAGService(graph.project_id, graph.id)
            result = service.get_graph_data()
            
            if not result:
                return Response(
                    {'error': '无法获取图谱数据'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            return Response({
                'graph_id': graph.id,
                'name': graph.name,
                'nodes': result.get('nodes', []),
                'edges': result.get('edges', []),
                'stats': {
                    'node_count': len(result.get('nodes', [])),
                    'edge_count': len(result.get('edges', []))
                }
            })
        except Exception as e:
            logger.error(f"获取图谱数据失败: {e}")
            return Response(
                {'error': f'获取图谱数据失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def query_history(self, request, pk=None):
        """
        获取查询历史
        
        GET /api/requirement-analysis/knowledge-graphs/{id}/query_history/
        """
        graph = self.get_object()
        history = KnowledgeGraphQueryHistory.objects.filter(graph=graph).order_by('-created_at')[:50]
        
        data = [
            {
                'id': h.id,
                'query': h.query,
                'mode': h.mode,
                'response': h.response[:200] + '...' if len(h.response) > 200 else h.response,
                'created_at': h.created_at,
                'created_by': h.created_by.username
            }
            for h in history
        ]
        
        return Response(data)

    @action(detail=True, methods=['post'])
    def compare_versions(self, request, pk=None):
        """
        比较两个知识图谱版本的差异
        
        POST /api/requirement-analysis/knowledge-graphs/{id}/compare_versions/
        {
            "base_version_id": "1.0.0",
            "compare_version_id": "2.0.0"
        }
        """
        graph = self.get_object()
        
        serializer = KnowledgeGraphVersionCompareSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        base_version_id = serializer.validated_data['base_version_id']
        compare_version_id = serializer.validated_data['compare_version_id']
        
        try:
            service = LightRAGService(graph.project_id, graph.id)
            result = async_to_sync(service.compare_versions)(base_version_id, compare_version_id)
            
            return Response({
                'base_version': base_version_id,
                'compare_version': compare_version_id,
                'differences': result
            })
        except Exception as e:
            logger.error(f"版本对比失败: {e}")
            return Response(
                {'error': f'版本对比失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """
        获取知识图谱的所有版本
        
        GET /api/requirement-analysis/knowledge-graphs/{id}/versions/
        """
        graph = self.get_object()
        versions = graph.versions.all().order_by('-created_at')
        
        data = [
            {
                'id': v.id,
                'version_number': v.version_number,
                'version_name': v.version_name,
                'description': v.description,
                'node_count': v.node_count,
                'edge_count': v.edge_count,
                'document_count': v.document_count,
                'created_at': v.created_at,
                'created_by': v.created_by.username
            }
            for v in versions
        ]
        
        return Response(data)

    @action(detail=True, methods=['post'])
    def create_version(self, request, pk=None):
        """
        创建知识图谱版本
        
        POST /api/requirement-analysis/knowledge-graphs/{id}/create_version/
        {
            "version_number": "1.0.0",
            "version_name": "第一版",
            "description": "初始版本"
        }
        """
        graph = self.get_object()
        
        version_number = request.data.get('version_number')
        version_name = request.data.get('version_name', '')
        description = request.data.get('description', '')
        
        if not version_number:
            return Response(
                {'error': '版本号不能为空'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            service = LightRAGService(graph.project_id, graph.id)
            version = async_to_sync(service.create_version)(
                version_number=version_number,
                version_name=version_name,
                description=description,
                created_by=request.user
            )
            
            return Response({
                'id': version.id,
                'version_number': version.version_number,
                'version_name': version.version_name,
                'description': version.description,
                'node_count': version.node_count,
                'edge_count': version.edge_count,
                'created_at': version.created_at,
                'message': '版本创建成功'
            })
        except Exception as e:
            logger.error(f"创建版本失败: {e}")
            return Response(
                {'error': f'创建版本失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['delete'], url_path='versions/(?P<version_id>[^/.]+)')
    def delete_version(self, request, pk=None, version_id=None):
        """
        删除知识图谱版本
        
        DELETE /api/requirement-analysis/knowledge-graphs/{id}/versions/{version_id}/
        """
        graph = self.get_object()
        
        try:
            version = graph.versions.get(id=version_id)
            version.delete()
            return Response({'message': '版本删除成功'})
        except graph.versions.model.DoesNotExist:
            return Response(
                {'error': '版本不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def compare_versions_real(self, request, pk=None):
        """
        真实比较两个知识图谱版本的差异
        
        POST /api/requirement-analysis/knowledge-graphs/{id}/compare_versions_real/
        {
            "base_version_id": 1,
            "compare_version_id": 2
        }
        """
        graph = self.get_object()
        
        base_version_id = request.data.get('base_version_id')
        compare_version_id = request.data.get('compare_version_id')
        
        if not base_version_id or not compare_version_id:
            return Response(
                {'error': '请提供基准版本ID和对比版本ID'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            service = LightRAGService(graph.project_id, graph.id)
            result = async_to_sync(service.compare_versions_real)(
                base_version_id, compare_version_id
            )
            
            return Response({
                'success': True,
                'base_version_id': base_version_id,
                'compare_version_id': compare_version_id,
                **result
            })
        except Exception as e:
            logger.error(f"版本对比失败: {e}")
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_build_task_status(request, task_id):
    """
    获取构建任务状态
    
    GET /api/requirement-analysis/knowledge-graphs/build-tasks/{task_id}/status/
    """
    try:
        task = KnowledgeGraphBuildTask.objects.get(task_id=task_id)
        return Response({
            'task_id': task.task_id,
            'status': task.status,
            'progress': task.progress,
            'current_document': task.current_document,
            'error_message': task.error_message,
            'started_at': task.started_at,
            'completed_at': task.completed_at
        })
    except KnowledgeGraphBuildTask.DoesNotExist:
        return Response(
            {'error': '任务不存在'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_available_documents(request, project_id):
    """
    获取可用于构建知识图谱的文档列表
    
    GET /api/requirement-analysis/knowledge-graphs/available-documents/{project_id}/
    """
    try:
        project = Project.objects.get(id=project_id)
        
        # 获取项目下已分析完成或已上传且有文本内容的需求文档
        documents = RequirementDocument.objects.filter(
            project=project
        ).exclude(
            extracted_text=''  # 排除没有文本内容的文档
        ).exclude(
            extracted_text__isnull=True
        ).order_by('-created_at')
        
        data = [
            {
                'id': doc.id,
                'title': doc.title,
                'document_type': doc.document_type,
                'status': doc.status,
                'created_at': doc.created_at
            }
            for doc in documents
        ]
        
        return Response({
            'project_id': project_id,
            'project_name': project.name,
            'documents': data,
            'total': len(data)
        })
        
    except Project.DoesNotExist:
        return Response(
            {'error': '项目不存在'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_and_create_graph(request):
    """
    上传文件并创建知识图谱

    POST /api/requirement-analysis/knowledge-graphs/upload-and-create/
    FormData:
        - name: 图谱名称
        - description: 图谱描述
        - project: 项目ID（可选）
        - is_public: 是否公共图谱
        - public_access_level: 公共访问权限
        - files: 上传的文件列表
    """
    try:
        # 获取表单数据
        name = request.data.get('name', '知识图谱')
        description = request.data.get('description', '')
        project_id = request.data.get('project')
        is_public = request.data.get('is_public', 'false').lower() == 'true'
        public_access_level = request.data.get('public_access_level', 'read')
        files = request.FILES.getlist('files')

        if not files:
            return Response(
                {'error': '请至少上传一个文件'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 限制只能上传单个文件
        if len(files) > 1:
            return Response(
                {'error': '只能上传单个文件，请重新选择'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 获取项目
        project = None
        if project_id:
            try:
                project = Project.objects.get(id=project_id)
            except Project.DoesNotExist:
                return Response(
                    {'error': '项目不存在'},
                    status=status.HTTP_404_NOT_FOUND
                )

        # 处理文件上传
        from .services import DocumentProcessor, ImageFlowchartProcessor
        document_ids = []
        for file in files:
            # 确定文档类型
            file_name = file.name.lower()
            if file_name.endswith('.pdf'):
                doc_type = 'pdf'
            elif file_name.endswith('.docx'):
                doc_type = 'docx'
            elif file_name.endswith('.txt'):
                doc_type = 'txt'
            elif file_name.endswith('.md'):
                doc_type = 'md'
            elif file_name.endswith('.png'):
                doc_type = 'png'
            elif file_name.endswith('.jpg') or file_name.endswith('.jpeg'):
                doc_type = 'jpg'
            elif file_name.endswith('.gif'):
                doc_type = 'gif'
            else:
                doc_type = 'txt'

            # 创建文档记录
            doc = RequirementDocument.objects.create(
                title=file.name,
                file=file,
                document_type=doc_type,
                project=project,
                uploaded_by=request.user,
                file_size=file.size
            )

            # 提取文本内容
            try:
                file_path = doc.file.path
                extracted_text = read_file_content(file_path)
                doc.extracted_text = extracted_text
                doc.status = 'analyzed'
                doc.save()
                document_ids.append(doc.id)
            except Exception as e:
                logger.error(f"读取文件内容失败 {file.name}: {e}")
                doc.delete()
                continue

        if not document_ids:
            return Response(
                {'error': '无法读取任何文件内容'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 创建知识图谱
        graph = KnowledgeGraph.objects.create(
            project=project,
            name=name,
            description=description,
            is_public=is_public,
            public_access_level=public_access_level,
            created_by=request.user,
            status='pending'
        )

        # 设置工作目录
        graph.save_working_dir()

        # 关联文档
        graph.documents.set(document_ids)

        return Response({
            'id': graph.id,
            'name': graph.name,
            'description': graph.description,
            'project': project_id,
            'is_public': is_public,
            'document_ids': document_ids,
            'message': '知识图谱创建成功，请调用构建接口开始构建'
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"上传文件创建图谱失败: {e}")
        return Response(
            {'error': f'创建失败: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def read_file_content(file_path):
    """读取文件内容，使用 DocumentProcessor 服务统一处理"""
    from .services import DocumentProcessor, ImageFlowchartProcessor
    import os

    logger.info(f"read_file_content 被调用: {file_path}")
    
    # 检查是否为图片文件
    is_image = ImageFlowchartProcessor.is_image_file(file_path)
    logger.info(f"是否为图片文件: {is_image}")
    
    if is_image:
        logger.info(f"检测到图片文件，使用多模态AI提取文字: {file_path}")
        # 使用多模态AI分析图片
        try:
            result = async_to_sync(ImageFlowchartProcessor.analyze_flowchart_with_vision)(file_path)
            logger.info(f"图片分析完成，结果长度: {len(result) if result else 0}")
            return result
        except Exception as e:
            logger.error(f"图片分析失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return ''

    # 非图片文件使用 docling 解析
    logger.info(f"非图片文件，使用 docling 解析: {file_path}")
    return DocumentProcessor.extract_text_with_docling(file_path)


# ==================== 项目文档管理 API ====================

from rest_framework import generics
from rest_framework.parsers import MultiPartParser, FormParser


class ProjectDocumentListCreateView(generics.ListCreateAPIView):
    """
    项目文档列表和创建 API
    GET /api/requirement-analysis/project-documents/?project_id=1
    POST /api/requirement-analysis/project-documents/
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        project_id = self.request.query_params.get('project_id')
        if project_id:
            return RequirementDocument.objects.filter(project_id=project_id).order_by('-created_at')
        return RequirementDocument.objects.none()
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            from .serializers import DocumentUploadSerializer
            return DocumentUploadSerializer
        return RequirementDocumentSerializer
    
    def perform_create(self, serializer):
        # 保存文档
        document = serializer.save(uploaded_by=self.request.user)
        
        # 异步提取文本内容
        from .services import DocumentProcessor, ImageFlowchartProcessor
        
        def extract_text_async():
            try:
                file_path = document.file.path
                
                # 检查是否为图片文件
                if ImageFlowchartProcessor.is_image_file(file_path):
                    document.status = 'analyzing'
                    document.save()
                    result = async_to_sync(ImageFlowchartProcessor.analyze_flowchart_with_vision)(file_path)
                else:
                    result = DocumentProcessor.extract_text_with_docling(file_path)
                
                document.extracted_text = result
                document.status = 'analyzed'
                document.save()
            except Exception as e:
                logger.error(f"提取文档文本失败: {e}")
                document.status = 'failed'
                document.save()
        
        # 启动后台线程提取文本
        thread = threading.Thread(target=extract_text_async)
        thread.daemon = True
        thread.start()
        
        return document


class ProjectDocumentDetailView(generics.RetrieveDestroyAPIView):
    """
    项目文档详情和删除 API
    GET /api/requirement-analysis/project-documents/{id}/
    DELETE /api/requirement-analysis/project-documents/{id}/
    """
    permission_classes = [IsAuthenticated]
    queryset = RequirementDocument.objects.all()
    serializer_class = RequirementDocumentSerializer
    
    def perform_destroy(self, instance):
        # 删除关联的文件
        if instance.file:
            file_path = instance.file.path
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.error(f"删除文件失败 {file_path}: {e}")
        
        # 删除数据库记录
        instance.delete()
