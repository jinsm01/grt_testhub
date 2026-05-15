# -*- coding: utf-8 -*-
"""
自动化场景 API 视图
"""
import json
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.utils import timezone

from .models import (
    AutomationScenario, ScenarioStep, ScenarioExecution,
    ApiProject, ApiCollection, ApiRequest
)
from .scenario_engine import ScenarioExecutor
from .apifox_importer import ApifoxCliImporter


class AutomationScenarioViewSet(viewsets.ModelViewSet):
    """自动化场景视图集"""
    queryset = AutomationScenario.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project', 'collection']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = AutomationScenario.objects.filter(is_deleted=False)
        project_id = self.request.query_params.get('project')
        collection_id = self.request.query_params.get('collection')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        if collection_id:
            queryset = queryset.filter(collection_id=collection_id)
        return queryset

    def list(self, request, *args, **kwargs):
        """列表查询"""
        queryset = self.get_queryset()
        data = []
        for scenario in queryset:
            data.append({
                'id': scenario.id,
                'name': scenario.name,
                'description': scenario.description,
                'project_id': scenario.project_id,
                'collection_id': scenario.collection_id,
                'collection_name': scenario.collection.name if scenario.collection else None,
                'environment_id': scenario.environment_id,
                'step_count': scenario.steps.filter(is_deleted=False, override_enabled=True).count(),
                'created_at': scenario.created_at,
                'updated_at': scenario.updated_at,
                'created_by': scenario.created_by.username if scenario.created_by else None
            })
        return Response(data)

    def retrieve(self, request, pk=None):
        """获取详情"""
        scenario = get_object_or_404(self.get_queryset(), pk=pk)
        return Response({
            'id': scenario.id,
            'name': scenario.name,
            'description': scenario.description,
            'project_id': scenario.project_id,
            'collection_id': scenario.collection_id,
            'collection_name': scenario.collection.name if scenario.collection else None,
            'environment_id': scenario.environment_id,
            'global_variables': scenario.global_variables,
            'pre_script': scenario.pre_script,
            'post_script': scenario.post_script,
            'flow_control': scenario.flow_control,
            'created_at': scenario.created_at,
            'updated_at': scenario.updated_at,
            'created_by': scenario.created_by.username if scenario.created_by else None
        })

    def create(self, request, *args, **kwargs):
        """创建场景"""
        data = request.data
        scenario = AutomationScenario.objects.create(
            project_id=data.get('project_id'),
            collection_id=data.get('collection_id'),
            name=data.get('name'),
            description=data.get('description', ''),
            environment_id=data.get('environment_id'),
            global_variables=data.get('global_variables', {}),
            pre_script=data.get('pre_script', ''),
            post_script=data.get('post_script', ''),
            flow_control=data.get('flow_control', {}),
            created_by=request.user
        )
        return Response({
            'id': scenario.id,
            'name': scenario.name,
            'message': '创建成功'
        }, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        """更新场景"""
        scenario = get_object_or_404(self.get_queryset(), pk=pk)
        data = request.data

        scenario.name = data.get('name', scenario.name)
        scenario.description = data.get('description', scenario.description)
        scenario.collection_id = data.get('collection_id', scenario.collection_id)
        scenario.environment_id = data.get('environment_id', scenario.environment_id)
        scenario.global_variables = data.get('global_variables', scenario.global_variables)
        scenario.pre_script = data.get('pre_script', scenario.pre_script)
        scenario.post_script = data.get('post_script', scenario.post_script)
        scenario.flow_control = data.get('flow_control', scenario.flow_control)
        scenario.save()

        return Response({
            'id': scenario.id,
            'name': scenario.name,
            'message': '更新成功'
        })

    def destroy(self, request, pk=None):
        """删除场景（软删除）"""
        scenario = get_object_or_404(self.get_queryset(), pk=pk)
        scenario.is_deleted = True
        scenario.save()
        return Response({'message': '删除成功'})

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """执行场景"""
        import traceback
        scenario = get_object_or_404(self.get_queryset(), pk=pk)

        try:
            executor = ScenarioExecutor(
                scenario=scenario,
                environment=scenario.environment,
                executed_by=request.user
            )

            result = executor.execute()
            return Response(result)
        except Exception as e:
            error_msg = f"执行场景失败: {str(e)}"
            error_detail = traceback.format_exc()
            print(f"ERROR: {error_msg}")
            print(f"TRACEBACK: {error_detail}")
            return Response(
                {'error': error_msg, 'detail': error_detail},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def executions(self, request, pk=None):
        """获取执行历史"""
        scenario = get_object_or_404(self.get_queryset(), pk=pk)
        executions = scenario.executions.all()[:20]

        data = []
        for exec in executions:
            data.append({
                'id': exec.id,
                'status': exec.status,
                'total_steps': exec.total_steps,
                'passed_steps': exec.passed_steps,
                'failed_steps': exec.failed_steps,
                'duration': exec.duration,
                'created_at': exec.created_at,
                'executed_by': exec.executed_by.username if exec.executed_by else None
            })

        return Response(data)

    @action(detail=True, methods=['get'])
    def available_references(self, request, pk=None):
        """
        获取可用于引用的场景列表
        （同项目下的其他场景，排除自身和循环引用）
        """
        scenario = get_object_or_404(self.get_queryset(), pk=pk)

        # 获取同项目下的所有场景
        available_scenarios = AutomationScenario.objects.filter(
            project=scenario.project,
            is_deleted=False
        ).exclude(id=scenario.id)

        # 排除会导致循环引用的场景（递归检查）
        def get_all_referenced_scenarios(scenario_id, visited=None):
            """获取场景直接或间接引用的所有场景ID"""
            if visited is None:
                visited = set()
            if scenario_id in visited:
                return visited
            visited.add(scenario_id)

            # 获取该场景引用的所有场景
            referenced_ids = ScenarioStep.objects.filter(
                scenario_id=scenario_id,
                step_type='scenario_ref',
                referenced_scenario__isnull=False
            ).values_list('referenced_scenario_id', flat=True)

            for ref_id in referenced_ids:
                get_all_referenced_scenarios(ref_id, visited)

            return visited

        # 获取当前场景引用的所有场景（避免循环）
        referenced_by_current = get_all_referenced_scenarios(scenario.id)

        # 排除引用当前场景的场景（会形成循环）
        def would_create_cycle(candidate_id):
            """检查引用候选场景是否会形成循环"""
            referenced_by_candidate = get_all_referenced_scenarios(candidate_id)
            return scenario.id in referenced_by_candidate

        data = []
        for s in available_scenarios:
            # 检查是否会导致循环引用
            is_valid = not would_create_cycle(s.id)

            data.append({
                'id': s.id,
                'name': s.name,
                'description': s.description,
                'step_count': s.steps.filter(is_deleted=False, override_enabled=True).count(),
                'is_valid': is_valid,
                'reason': '' if is_valid else '引用会形成循环'
            })

        return Response(data)

    @action(detail=True, methods=['get'])
    def review_summary(self, request, pk=None):
        """获取场景评审摘要"""
        scenario = get_object_or_404(self.get_queryset(), pk=pk)
        summary = scenario.get_review_summary()
        return Response(summary)

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """提交评审"""
        scenario = get_object_or_404(self.get_queryset(), pk=pk)

        status_value = request.data.get('status')
        comment = request.data.get('comment', '')

        if status_value not in ['approved', 'rejected']:
            return Response(
                {'error': '无效的评审状态，必须是 approved 或 rejected'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 更新或创建评审记录
        from .models import ScenarioReviewRecord
        review_record, created = ScenarioReviewRecord.objects.update_or_create(
            scenario=scenario,
            reviewer=request.user,
            defaults={
                'status': status_value,
                'comment': comment,
                'reviewed_at': timezone.now()
            }
        )

        return Response({
            'message': '评审提交成功',
            'status': review_record.status,
            'reviewed_at': review_record.reviewed_at
        })

    @action(detail=True, methods=['post'])
    def reset_reviews(self, request, pk=None):
        """重置评审（重新发起评审）"""
        scenario = get_object_or_404(self.get_queryset(), pk=pk)

        # 检查权限：只有创建者可以重置
        if scenario.created_by != request.user:
            return Response(
                {'error': '只有创建者可以重置评审'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 软删除所有评审记录
        from .models import ScenarioReviewRecord
        ScenarioReviewRecord.objects.filter(scenario=scenario).update(
            is_deleted=True,
            deleted_at=timezone.now()
        )

        return Response({'message': '评审已重置'})


class ScenarioStepViewSet(viewsets.ModelViewSet):
    """场景步骤视图集"""
    queryset = ScenarioStep.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['scenario']

    def get_queryset(self):
        queryset = ScenarioStep.objects.filter(is_deleted=False)
        # 同时兼容 'scenario' 和 'scenario_id' 参数名
        scenario_id = self.request.query_params.get('scenario') or self.request.query_params.get('scenario_id')
        if scenario_id:
            queryset = queryset.filter(scenario_id=scenario_id)
        return queryset.order_by('step_number')

    def list(self, request, *args, **kwargs):
        """列表查询 - 返回树形结构数据"""
        queryset = self.get_queryset()
        
        # 构建步骤字典
        step_dict = {}
        for step in queryset:
            step_data = {
                'id': step.id,
                'step_number': step.step_number,
                'step_alias': step.step_alias,
                'name': step.name,
                'step_type': step.step_type,
                'api_request_id': step.api_request_id,
                'api_request_name': step.api_request.name if step.api_request else None,
                'api_request': {
                    'id': step.api_request.id,
                    'name': step.api_request.name,
                    'method': step.api_request.method,
                    'url': step.api_request.url
                } if step.api_request else None,
                'referenced_scenario_id': step.referenced_scenario_id,
                'referenced_scenario_name': step.referenced_scenario.name if step.referenced_scenario else None,
                'override_enabled': step.override_enabled,
                'override_method': step.override_method,
                'override_url': step.override_url,
                'override_headers': step.override_headers,
                'override_params': step.override_params,
                'override_body': step.override_body,
                'override_extractors': step.override_extractors,
                'override_assertions': step.override_assertions,
                'order': step.order,
                'parent_id': step.parent_id,
                'children': []
            }
            step_dict[step.id] = step_data
        
        # 构建树形结构
        tree_data = []
        for step_id, step_data in step_dict.items():
            parent_id = step_data['parent_id']
            if parent_id and parent_id in step_dict:
                # 有父节点，添加到父节点的 children 中
                step_dict[parent_id]['children'].append(step_data)
            else:
                # 没有父节点，是顶层节点
                tree_data.append(step_data)
        
        # 按 order 排序
        tree_data.sort(key=lambda x: x['order'])
        for step in step_dict.values():
            step['children'].sort(key=lambda x: x['order'])
        
        return Response({'results': tree_data})

    def retrieve(self, request, pk=None):
        """获取详情（包含完整覆盖配置）"""
        step = get_object_or_404(self.get_queryset(), pk=pk)

        # 获取原始接口配置
        original_request = None
        if step.api_request:
            original_request = {
                'id': step.api_request.id,
                'name': step.api_request.name,
                'method': step.api_request.method,
                'url': step.api_request.url,
                'headers': step.api_request.headers,
                'body': step.api_request.body,
                'params': step.api_request.params,
                'assertions': step.api_request.assertions,
                'variable_extractors': step.api_request.variable_extractors
            }

        # 获取引用的场景信息
        referenced_scenario_info = None
        if step.referenced_scenario:
            referenced_scenario_info = {
                'id': step.referenced_scenario.id,
                'name': step.referenced_scenario.name,
                'step_count': step.referenced_scenario.steps.filter(
                    is_deleted=False, override_enabled=True
                ).count()
            }

        return Response({
            'id': step.id,
            'scenario_id': step.scenario_id,
            'step_number': step.step_number,
            'step_alias': step.step_alias,
            'name': step.name,
            'step_type': step.step_type,
            'api_request': original_request,
            'referenced_scenario': referenced_scenario_info,
            'scenario_ref_config': step.scenario_ref_config,
            'override_enabled': step.override_enabled,
            'override_name': step.override_name,
            'override_method': step.override_method,
            'override_url': step.override_url,
            'override_headers': step.override_headers,
            'override_body': step.override_body,
            'override_params': step.override_params,
            'override_assertions': step.override_assertions,
            'override_extractors': step.override_extractors,
            'pre_script': step.pre_script,
            'post_script': step.post_script,
            'control_config': step.control_config,
            'order': step.order,
            'parent_id': step.parent_id
        })

    def create(self, request, *args, **kwargs):
        """创建步骤"""
        data = request.data

        # 获取最大步骤编号
        scenario_id = data.get('scenario_id')
        max_step = ScenarioStep.objects.filter(
            scenario_id=scenario_id
        ).values_list('step_number', flat=True)
        next_step = max(max_step, default=0) + 1

        step = ScenarioStep.objects.create(
            scenario_id=scenario_id,
            step_type=data.get('step_type', 'request'),
            step_number=next_step,
            step_alias=data.get('step_alias', ''),
            name=data.get('name'),
            api_request_id=data.get('api_request_id'),
            referenced_scenario_id=data.get('referenced_scenario_id'),
            scenario_ref_config=data.get('scenario_ref_config', {}),
            override_enabled=data.get('override_enabled', True),
            override_name=data.get('override_name', ''),
            override_method=data.get('override_method', ''),
            override_url=data.get('override_url', ''),
            override_headers=data.get('override_headers', {}),
            override_body=data.get('override_body', {}),
            override_params=data.get('override_params', {}),
            override_assertions=data.get('override_assertions', []),
            override_extractors=data.get('override_extractors', []),
            pre_script=data.get('pre_script', ''),
            post_script=data.get('post_script', ''),
            control_config=data.get('control_config', {}),
            order=next_step
        )

        return Response({
            'id': step.id,
            'step_number': step.step_number,
            'message': '创建成功'
        }, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        """更新步骤（支持场景内编辑）"""
        step = get_object_or_404(self.get_queryset(), pk=pk)
        data = request.data

        # 更新基础信息
        step.name = data.get('name', step.name)
        step.step_alias = data.get('step_alias', step.step_alias)
        step.override_enabled = data.get('override_enabled', step.override_enabled)

        # 更新场景引用配置
        if 'referenced_scenario_id' in data:
            step.referenced_scenario_id = data['referenced_scenario_id']
        if 'scenario_ref_config' in data:
            step.scenario_ref_config = data['scenario_ref_config']

        # 更新接口覆盖配置
        step.override_name = data.get('override_name', step.override_name)
        step.override_method = data.get('override_method', step.override_method)
        step.override_url = data.get('override_url', step.override_url)
        step.override_headers = data.get('override_headers', step.override_headers)
        step.override_body = data.get('override_body', step.override_body)
        step.override_params = data.get('override_params', step.override_params)
        step.override_assertions = data.get('override_assertions', step.override_assertions)
        step.override_extractors = data.get('override_extractors', step.override_extractors)
        step.pre_script = data.get('pre_script', step.pre_script)
        step.post_script = data.get('post_script', step.post_script)
        step.control_config = data.get('control_config', step.control_config)
        step.save()

        return Response({
            'id': step.id,
            'message': '更新成功'
        })

    def destroy(self, request, pk=None):
        """删除步骤（软删除）"""
        step = get_object_or_404(self.get_queryset(), pk=pk)
        step.is_deleted = True
        step.save()
        return Response({'message': '删除成功'})


class ScenarioExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """场景执行记录视图集（只读）"""
    queryset = ScenarioExecution.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['scenario', 'status']

    def get_queryset(self):
        return ScenarioExecution.objects.all().order_by('-created_at')

    def retrieve(self, request, pk=None):
        """获取执行详情（包含嵌套子执行记录）"""
        execution = get_object_or_404(self.get_queryset(), pk=pk)

        # 获取子执行记录（嵌套场景执行）
        child_executions = []
        for child in execution.child_executions.all():
            child_executions.append({
                'id': child.id,
                'scenario_id': child.scenario_id,
                'scenario_name': child.scenario.name if child.scenario else None,
                'parent_step_number': child.parent_step_number,
                'status': child.status,
                'total_steps': child.total_steps,
                'passed_steps': child.passed_steps,
                'failed_steps': child.failed_steps,
                'duration': child.duration,
                'pass_rate': child.pass_rate,
                'inherited_variables': child.inherited_variables,
                'exported_variables': child.exported_variables,
                'start_time': child.start_time,
                'end_time': child.end_time
            })

        # 获取父执行记录信息（如果被引用）
        parent_info = None
        if execution.parent_execution:
            parent_info = {
                'id': execution.parent_execution.id,
                'scenario_id': execution.parent_execution.scenario_id,
                'scenario_name': execution.parent_execution.scenario.name if execution.parent_execution.scenario else None,
                'parent_step_number': execution.parent_step_number
            }

        return Response({
            'id': execution.id,
            'scenario_id': execution.scenario_id,
            'scenario_name': execution.scenario.name,
            'status': execution.status,
            'total_steps': execution.total_steps,
            'passed_steps': execution.passed_steps,
            'failed_steps': execution.failed_steps,
            'duration': execution.duration,
            'pass_rate': execution.pass_rate,
            'execution_context': execution.execution_context,
            'step_results': execution.step_results,
            'inherited_variables': execution.inherited_variables,
            'exported_variables': execution.exported_variables,
            'parent_execution': parent_info,
            'child_executions': child_executions,
            'start_time': execution.start_time,
            'end_time': execution.end_time,
            'created_at': execution.created_at,
            'executed_by': execution.executed_by.username if execution.executed_by else None
        })


# ==================== Apifox V2 导入 API ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apifox_import_v2_validate(request):
    """
    验证 Apifox CLI JSON 文件
    """
    try:
        file_obj = request.FILES.get('file')
        project_id = request.data.get('project_id')

        if not file_obj:
            return Response({'error': '请上传文件'}, status=400)

        # 解析 JSON
        content = file_obj.read().decode('utf-8')
        data = json.loads(content)

        # 验证基本信息
        info = data.get('info', {})
        collection_name = info.get('name', '未命名集合')
        item_count = len(data.get('item', []))

        # 处理 wrapper 结构：如果 items[0] 有嵌套的 item 数组，提取它
        items = data.get('item', [])
        if items and isinstance(items[0], dict) and 'item' in items[0]:
            items = items[0].get('item', [])

        # 统计请求数量（只统计包含 request 字段的项，不包括分组）
        def count_requests(items):
            count = 0
            for item in items:
                # 如果 item 包含 request 字段，说明是一个请求
                if 'request' in item:
                    count += 1
                # 如果有嵌套的 item，递归统计
                if 'item' in item:
                    count += count_requests(item['item'])
            return count

        total_requests = count_requests(items)

        # 提取变量
        variables = [v.get('key', '') for v in data.get('variable', [])]

        # 检查是否已存在同名合集
        existing_collection = None
        if project_id:
            existing = ApiCollection.objects.filter(
                project_id=project_id,
                name=collection_name,
                is_deleted=False
            ).first()
            if existing:
                # 统计现有合集中的接口数量
                existing_request_count = ApiRequest.objects.filter(
                    collection=existing,
                    is_deleted=False
                ).count()
                existing_collection = {
                    'id': existing.id,
                    'name': existing.name,
                    'request_count': existing_request_count,
                    'created_at': existing.created_at.strftime('%Y-%m-%d %H:%M:%S')
                }

        return Response({
            'valid': True,
            'collection_name': collection_name,
            'description': info.get('description', ''),
            'total_requests': total_requests,
            'variables': variables,
            'existing_collection': existing_collection,
            'message': f'验证通过，共 {total_requests} 个请求，{len(variables)} 个变量'
        })

    except json.JSONDecodeError as e:
        return Response({'error': f'JSON 解析失败: {str(e)}'}, status=400)
    except Exception as e:
        return Response({'error': f'验证失败: {str(e)}'}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apifox_import_v2_execute(request):
    """
    执行 Apifox CLI JSON 导入
    """
    try:
        file_obj = request.FILES.get('file')
        project_id = request.data.get('project_id')
        target_collection_id = request.data.get('target_collection_id')
        collection_id = request.data.get('collection_id')

        if not file_obj:
            return Response({'error': '请上传文件'}, status=400)

        if not project_id:
            return Response({'error': '请指定项目 ID'}, status=400)

        # 获取项目
        project = get_object_or_404(ApiProject, pk=project_id)

        # 获取目标集合（可选，用于导入接口请求）
        target_collection = None
        if target_collection_id:
            target_collection = get_object_or_404(ApiCollection, pk=target_collection_id)

        # 解析 JSON
        content = file_obj.read().decode('utf-8')
        data = json.loads(content)

        # 执行导入
        importer = ApifoxCliImporter(request.user, project)
        result = importer.import_from_data(data, target_collection=target_collection)

        return Response({
            'success': result.get('success', True),
            'scenario_id': result.get('scenario_id'),
            'collection_id': result.get('collection_id'),
            'collection_name': result.get('collection_name'),
            'suite_id': result.get('suite_id'),
            'suite_name': result.get('suite_name'),
            'stats': result.get('stats', {}),
            'warnings': result.get('warnings', []),
            'imported_requests': result.get('imported_requests', [])
        })

    except Exception as e:
        import traceback
        return Response({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)
