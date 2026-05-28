"""
LightRAG API 视图
提供知识图谱的构建、查询、可视化等接口
"""
import asyncio
import logging
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

    @action(detail=True, methods=['post'])
    def build(self, request, pk=None):
        """
        构建知识图谱
        
        POST /api/requirement-analysis/knowledge-graphs/{id}/build/
        {
            "document_ids": [1, 2, 3]
        }
        """
        graph = self.get_object()
        
        # 验证请求数据
        serializer = KnowledgeGraphBuildRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        document_ids = serializer.validated_data['document_ids']
        
        # 验证文档是否属于同一项目（公共图谱不限制）
        if graph.project:
            documents = RequirementDocument.objects.filter(
                id__in=document_ids,
                project=graph.project
            )
            if documents.count() != len(document_ids):
                return Response(
                    {'error': '部分文档不存在或不属于当前项目'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            # 公共图谱：验证文档存在即可
            documents = RequirementDocument.objects.filter(id__in=document_ids)
            if documents.count() != len(document_ids):
                return Response(
                    {'error': '部分文档不存在'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # 创建构建任务
        task_id = f"kg_build_{uuid.uuid4().hex[:16]}"
        build_task = KnowledgeGraphBuildTask.objects.create(
            task_id=task_id,
            graph=graph,
            status='pending'
        )
        
        # 更新图谱状态
        graph.status = 'building'
        graph.build_started_at = timezone.now()
        graph.documents.set(documents)
        graph.save()
        
        # 异步执行构建任务
        try:
            # 在新线程中启动异步任务
            def run_build():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(
                        self._build_graph_async(graph.id, document_ids, task_id)
                    )
                finally:
                    loop.close()

            thread = threading.Thread(target=run_build, daemon=True)
            thread.start()

            return Response({
                'message': '知识图谱构建任务已启动',
                'task_id': task_id,
                'graph_id': graph.id,
                'status': 'building'
            })

        except Exception as e:
            logger.error(f"启动构建任务失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")

            graph.status = 'failed'
            graph.build_error_message = str(e)
            graph.save()

            build_task.status = 'failed'
            build_task.error_message = str(e)
            build_task.save()

            return Response(
                {'error': f'构建任务启动失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _setup_lightrag_env(self):
        """设置 LightRAG 环境变量（在同步上下文中执行）"""
        try:
            from .models import AIModelConfig
            
            # 查找 knowledge_graph 或 knowledge_base 配置
            config = AIModelConfig.objects.filter(
                role__in=['knowledge_graph', 'knowledge_base'],
                is_active=True
            ).first()
            
            if not config:
                config = AIModelConfig.objects.filter(is_active=True).first()
            
            if config and config.api_key:
                import os
                os.environ['OPENAI_API_KEY'] = config.api_key
                os.environ['OPENAI_BASE_URL'] = config.base_url or 'https://dashscope.aliyuncs.com/compatible-mode/v1'
                os.environ['OPENAI_MODEL_NAME'] = config.model_name or 'qwen-turbo'
                logger.info(f"已设置环境变量 OPENAI_API_KEY (来源: {config.name})")
                logger.info(f"使用模型: {config.model_name}, max_tokens: {config.max_tokens}, temperature: {config.temperature}")
                return True
        except Exception as e:
            logger.warning(f"设置环境变量失败: {e}")
        return False
    
    async def _build_graph_async(self, graph_id: int, document_ids: List[int], task_id: str):
        """异步构建图谱"""
        try:
            # 获取任务和图谱对象
            build_task = await sync_to_async(KnowledgeGraphBuildTask.objects.get)(task_id=task_id)
            graph = await sync_to_async(KnowledgeGraph.objects.get)(id=graph_id)
            
            # 更新任务状态
            build_task.status = 'running'
            build_task.started_at = timezone.now()
            await sync_to_async(build_task.save)()
            
            # 获取文档对象
            documents = await sync_to_async(list)(
                RequirementDocument.objects.filter(id__in=document_ids)
            )
            
            # 在同步上下文中设置环境变量
            await sync_to_async(self._setup_lightrag_env)()
            
            # 创建 LightRAG 服务并构建
            service = LightRAGService(graph.project_id, graph.id)
            
            # 定义进度回调函数 - 在线程中通过队列发送进度到主事件循环
            import threading
            import queue
            
            progress_queue = queue.Queue()
            
            def progress_callback(progress, current_document):
                # 将进度信息放入队列，由主事件循环处理
                progress_queue.put((progress, current_document))
                logger.info(f"构建进度: {progress}%, 当前文档: {current_document}")
            
            # 启动进度处理任务
            async def process_progress():
                while True:
                    try:
                        # 非阻塞获取队列中的进度
                        progress, current_document = progress_queue.get(timeout=0.1)
                        build_task.progress = progress
                        build_task.current_document = current_document
                        await sync_to_async(build_task.save)()
                        if progress >= 100:
                            break
                    except queue.Empty:
                        # 检查构建是否还在运行
                        await asyncio.sleep(0.1)
                        continue
                    except Exception as e:
                        logger.error(f"处理进度失败: {e}")
            
            # 启动进度处理任务
            progress_task = asyncio.create_task(process_progress())
            
            result = await service.build_graph(documents, progress_callback)

            # 等待进度处理任务完成
            progress_queue.put((100, '构建完成'))
            try:
                await asyncio.wait_for(progress_task, timeout=5.0)
            except asyncio.TimeoutError:
                progress_task.cancel()

            # 更新图谱状态
            if result.get('success'):
                graph.status = 'completed'
                graph.node_count = result.get('nodes', 0)
                graph.edge_count = result.get('edges', 0)
                graph.document_count = result.get('documents', 0)
                graph.build_completed_at = timezone.now()

                build_task.status = 'completed'
                build_task.progress = 100
                build_task.completed_at = timezone.now()
            else:
                graph.status = 'failed'
                graph.build_error_message = result.get('error', '未知错误')

                build_task.status = 'failed'
                build_task.error_message = result.get('error', '未知错误')

            await sync_to_async(graph.save)()
            await sync_to_async(build_task.save)()
            
        except Exception as e:
            import traceback
            logger.error(f"异步构建图谱失败: {e}")
            logger.error(f"堆栈跟踪: {traceback.format_exc()}")
            try:
                build_task = await sync_to_async(KnowledgeGraphBuildTask.objects.get)(task_id=task_id)
                build_task.status = 'failed'
                build_task.error_message = str(e)
                await sync_to_async(build_task.save)()
                
                graph = await sync_to_async(KnowledgeGraph.objects.get)(id=graph_id)
                graph.status = 'failed'
                graph.build_error_message = str(e)
                await sync_to_async(graph.save)()
            except:
                pass
    
    @action(detail=True, methods=['post'])
    def query(self, request, pk=None):
        """
        查询知识图谱
        
        POST /api/requirement-analysis/knowledge-graphs/{id}/query/
        {
            "question": "用户管理模块包含哪些功能？",
            "mode": "mix"
        }
        """
        graph = self.get_object()
        
        if graph.status != 'completed':
            return Response(
                {'error': '知识图谱尚未构建完成，无法查询'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 验证请求数据
        serializer = KnowledgeGraphQuerySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        question = serializer.validated_data['question']
        mode = serializer.validated_data.get('mode', 'mix')
        
        try:
            # 执行查询
            import time
            start_time = time.time()
            
            service = LightRAGService(graph.project_id, graph.id)

            result = async_to_sync(service.query)(question, mode)
            
            query_time = time.time() - start_time
            
            if result.get('success'):
                # 保存查询历史
                KnowledgeGraphQueryHistory.objects.create(
                    graph=graph,
                    question=question,
                    answer=result['answer'],
                    mode=mode,
                    query_time=query_time,
                    created_by=request.user
                )
                
                return Response({
                    'success': True,
                    'question': question,
                    'mode': mode,
                    'answer': result['answer'],
                    'query_time': round(query_time, 2)
                })
            else:
                return Response(
                    {'error': result.get('error', '查询失败')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"查询知识图谱失败: {e}")
            return Response(
                {'error': f'查询失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """
        获取知识图谱统计信息
        
        GET /api/requirement-analysis/knowledge-graphs/{id}/stats/
        """
        graph = self.get_object()
        
        service = LightRAGService(graph.project_id, graph.id)

        stats = service.get_stats()
        
        # 更新数据库中的统计信息
        if stats['has_graph']:
            graph.node_count = stats['nodes']
            graph.edge_count = stats['edges']
            graph.document_count = stats['documents']
            graph.save()
        
        serializer = KnowledgeGraphStatsSerializer({
            'graph_id': graph.id,
            'name': graph.name,
            'status': graph.status,
            'has_graph': stats['has_graph'],
            'nodes': stats['nodes'],
            'edges': stats['edges'],
            'documents': stats['documents'],
            'created_at': graph.created_at,
            'build_completed_at': graph.build_completed_at
        })
        
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def graph_data(self, request, pk=None):
        """
        获取图谱可视化数据
        
        GET /api/requirement-analysis/knowledge-graphs/{id}/graph_data/
        """
        graph = self.get_object()
        
        if graph.status != 'completed':
            return Response(
                {'error': '知识图谱尚未构建完成'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        service = LightRAGService(graph.project_id, graph.id)

        graph_data = service.get_graph_data()
        
        if graph_data:
            return Response({
                'success': True,
                'nodes': graph_data['nodes'],
                'edges': graph_data['edges']
            })
        else:
            return Response(
                {'error': '无法获取图谱数据'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def compare_versions(self, request, pk=None):
        """
        对比版本差异

        POST /api/requirement-analysis/knowledge-graphs/{id}/compare_versions/
        {
            "base_version": "V1",
            "compare_version": "V3"
        }
        """
        graph = self.get_object()

        if graph.status != 'completed':
            return Response(
                {'error': '知识图谱尚未构建完成'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = KnowledgeGraphVersionCompareSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        base_version = serializer.validated_data['base_version']
        compare_version = serializer.validated_data['compare_version']

        try:
            service = LightRAGService(graph.project_id, graph.id)

            result = async_to_sync(service.compare_versions)(base_version, compare_version)

            return Response(result)

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
        from .models import KnowledgeGraphVersion

        versions = KnowledgeGraphVersion.objects.filter(
            graph=graph
        ).order_by('-created_at')

        data = [
            {
                'id': v.id,
                'version_number': v.version_number,
                'version_name': v.version_name,
                'description': v.description,
                'node_count': v.node_count,
                'edge_count': v.edge_count,
                'document_count': v.document_count,
                'created_at': v.created_at.isoformat(),
                'created_by': v.created_by.username if v.created_by else None
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
            "version_number": "V1",
            "version_name": "初始版本",
            "description": "第一次构建的知识图谱"
        }
        """
        graph = self.get_object()

        if graph.status != 'completed':
            return Response(
                {'error': '知识图谱尚未构建完成，无法创建版本'},
                status=status.HTTP_400_BAD_REQUEST
            )

        version_number = request.data.get('version_number')
        version_name = request.data.get('version_name', '')
        description = request.data.get('description', '')

        if not version_number:
            return Response(
                {'error': '请提供版本号'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            service = LightRAGService(graph.project_id, graph.id)

            result = service.create_version(
                version_number=version_number,
                version_name=version_name,
                description=description,
                user=request.user
            )

            if result['success']:
                return Response({
                    'success': True,
                    'message': f'版本 {version_number} 创建成功',
                    'version_id': result['version_id'],
                    'stats': result['stats']
                })
            else:
                return Response(
                    {'error': result.get('error', '创建版本失败')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

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
        from .models import KnowledgeGraphVersion

        graph = self.get_object()

        try:
            version = KnowledgeGraphVersion.objects.get(
                id=version_id,
                graph=graph
            )
            version_number = version.version_number
            version.delete()

            return Response({
                'success': True,
                'message': f'版本 {version_number} 已删除'
            })

        except KnowledgeGraphVersion.DoesNotExist:
            return Response(
                {'error': '版本不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"删除版本失败: {e}")
            return Response(
                {'error': f'删除版本失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def compare_versions_real(self, request, pk=None):
        """
        真正的版本对比（基于快照数据）

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

            result = service.compare_versions_real(
                base_version_id=int(base_version_id),
                compare_version_id=int(compare_version_id)
            )

            return Response(result)

        except Exception as e:
            logger.error(f"版本对比失败: {e}")
            return Response(
                {'error': f'版本对比失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def query_history(self, request, pk=None):
        """
        获取查询历史
        
        GET /api/requirement-analysis/knowledge-graphs/{id}/query_history/?limit=10
        """
        graph = self.get_object()
        
        limit = int(request.query_params.get('limit', 10))
        
        history = KnowledgeGraphQueryHistory.objects.filter(
            graph=graph
        ).order_by('-created_at')[:limit]
        
        data = [
            {
                'id': h.id,
                'question': h.question,
                'answer': h.answer[:200] + '...' if len(h.answer) > 200 else h.answer,
                'mode': h.mode,
                'query_time': h.query_time,
                'created_at': h.created_at
            }
            for h in history
        ]
        
        return Response(data)

    @action(detail=False, methods=['post'], url_path='batch-delete')
    def batch_delete(self, request):
        """
        批量删除知识图谱

        POST /api/requirement-analysis/knowledge-graphs/batch-delete/
        {
            "ids": [1, 2, 3]
        }
        """
        ids = request.data.get('ids', [])

        if not ids:
            return Response(
                {'error': '请提供要删除的图谱ID列表'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 验证权限：只能删除自己创建的或公共图谱
        graphs = KnowledgeGraph.objects.filter(
            id__in=ids
        ).filter(
            models.Q(created_by=request.user) | models.Q(is_public=True)
        )

        if graphs.count() != len(ids):
            return Response(
                {'error': '部分图谱不存在或无权限删除'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 删除关联的文件目录
        deleted_files_count = 0
        for graph in graphs:
            working_dir = Path(graph.get_working_dir())
            if working_dir.exists():
                try:
                    shutil.rmtree(working_dir)
                    deleted_files_count += 1
                    logger.info(f"已删除知识图谱文件目录: {working_dir}")
                except Exception as e:
                    logger.error(f"删除知识图谱文件目录失败 {working_dir}: {str(e)}")

        # 执行数据库删除
        deleted_count = graphs.count()
        graphs.delete()

        return Response({
            'message': f'成功删除 {deleted_count} 个知识图谱，清理 {deleted_files_count} 个文件目录',
            'deleted_count': deleted_count,
            'deleted_files_count': deleted_files_count
        })


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

        # 验证项目
        project = None
        if project_id:
            try:
                project = Project.objects.get(id=project_id)
            except Project.DoesNotExist:
                return Response(
                    {'error': '项目不存在'},
                    status=status.HTTP_404_NOT_FOUND
                )

        # 创建需求文档记录并保存文件
        document_ids = []
        for file in files:
            # 确定文档类型
            ext = file.name.split('.')[-1].lower()
            doc_type_map = {
                'pdf': 'pdf',
                'docx': 'docx',
                'doc': 'docx',
                'txt': 'txt',
                'md': 'md',
                'png': 'png',
                'jpg': 'jpg',
                'jpeg': 'jpeg',
                'gif': 'gif'
            }
            document_type = doc_type_map.get(ext, 'txt')

            # 创建文档记录
            doc = RequirementDocument.objects.create(
                project=project,
                title=file.name,
                document_type=document_type,
                status='analyzed',  # 直接标记为已分析
                uploaded_by=request.user
            )

            # 保存文件到文档的存储路径
            doc.file.save(file.name, file)
            doc.file_size = file.size
            doc.save()

            # 读取文件内容
            try:
                content = read_file_content(doc.file.path)
                doc.extracted_text = content
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
