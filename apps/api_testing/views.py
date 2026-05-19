from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db import models, IntegrityError
from django.utils import timezone
from django.http import HttpResponse, FileResponse, Http404, HttpResponseNotFound
from django.views.static import serve
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import requests
import time
import os
import json
import logging
import uuid
import subprocess
from datetime import datetime, timedelta

from .models import (
    ApiProject, ApiCollection, ApiRequest, Environment,
    RequestHistory, TestSuite, TestExecution, TestSuiteRequest,
    ScheduledTask, TaskExecutionLog, NotificationLog,
    TaskNotificationSetting, OperationLog, AIServiceConfig,
    TestSuiteReviewRecord,
)

from .serializers import (
    ApiProjectSerializer, ApiCollectionSerializer, ApiRequestSerializer,
    EnvironmentSerializer, RequestHistorySerializer, TestSuiteSerializer,
    TestSuiteRequestSerializer, TestExecutionSerializer, UserSerializer,
    ScheduledTaskSerializer, TaskExecutionLogSerializer,
    NotificationLogSerializer, TaskNotificationSettingSerializer,
    NotificationLogDetailSerializer,
    TaskNotificationSettingDetailSerializer, OperationLogSerializer,
    TestSuiteReviewRecordSerializer
)

logger = logging.getLogger(__name__)

from .utils import execute_assertions
from .operation_logger import log_operation
from .variable_resolver import VariableResolver
from .variable_extractor import extract_variables, save_variables_to_environment
from .scenario_engine.context import ScenarioContext
from .serializers import (
    ApiProjectSerializer, ApiCollectionSerializer, ApiRequestSerializer,
    EnvironmentSerializer, RequestHistorySerializer, TestSuiteSerializer,
    TestSuiteRequestSerializer, TestExecutionSerializer, UserSerializer,
    ScheduledTaskSerializer, ScheduledTaskSerializer,
    AIServiceConfigSerializer
)
from .ai_assertion_generator import AIAssertionGenerator

User = get_user_model()


from rest_framework.pagination import PageNumberPagination

class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 1000


class ApiProjectViewSet(viewsets.ModelViewSet):
    queryset = ApiProject.objects.all()
    serializer_class = ApiProjectSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project_type', 'status', 'owner']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name', 'start_date']
    ordering = ['-created_at']
    
    def get_queryset(self):
        # 返回所有项目，不进行权限过滤
        return ApiProject.objects.all()
    
    def perform_create(self, serializer):
        """创建项目时记录日志"""
        instance = serializer.save()
        log_operation(
            operation_type='create',
            resource_type='project',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )
    
    def perform_update(self, serializer):
        """更新项目时记录日志"""
        instance = serializer.save()
        log_operation(
            operation_type='edit',
            resource_type='project',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )
    
    def perform_destroy(self, instance):
        """删除项目时记录日志"""
        log_operation(
            operation_type='delete',
            resource_type='project',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )
        instance.delete()



class ApiCollectionViewSet(viewsets.ModelViewSet):
    queryset = ApiCollection.objects.all()
    serializer_class = ApiCollectionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['project', 'parent']
    
    def get_queryset(self):
        # 返回所有集合，不进行权限过滤
        return ApiCollection.objects.all()

    def perform_create(self, serializer):
        """创建集合时设置创建者并记录日志"""
        instance = serializer.save(created_by=self.request.user)
        log_operation(
            operation_type='create',
            resource_type='collection',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )

    def perform_update(self, serializer):
        """更新集合时记录日志"""
        instance = serializer.save()
        log_operation(
            operation_type='edit',
            resource_type='collection',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )

    def perform_destroy(self, instance):
        """删除集合时记录日志"""
        log_operation(
            operation_type='delete',
            resource_type='collection',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )
        instance.delete()


class ApiRequestViewSet(viewsets.ModelViewSet):
    queryset = ApiRequest.objects.all()
    serializer_class = ApiRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['collection', 'method', 'request_type']
    search_fields = ['name', 'url']
    pagination_class = StandardPagination
    
    def get_queryset(self):
        # 返回所有未删除的接口，不进行权限过滤
        queryset = ApiRequest.objects.filter(is_deleted=False)

        project_id = self.request.query_params.get('project')
        if project_id:
            # 如果指定了项目，则只查询该项目下的接口
            queryset = queryset.filter(
                models.Q(collection__project_id=project_id) | models.Q(
                    collection__isnull=True
                )
            ).distinct()

        return queryset

    def perform_create(self, serializer):
        """创建接口时记录日志"""
        instance = serializer.save()
        log_operation(
            operation_type='create',
            resource_type='request',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )

    def perform_update(self, serializer):
        """更新接口时记录日志"""
        instance = serializer.save()
        log_operation(
            operation_type='edit',
            resource_type='request',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )

    def perform_destroy(self, instance):
        """删除接口时记录日志"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Deleting request {instance.id} - {instance.name}, current is_deleted: {instance.is_deleted}")
        
        log_operation(
            operation_type='delete',
            resource_type='request',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )
        instance.delete()
        
        # 重新查询确认删除状态
        from .models import ApiRequest
        try:
            updated = ApiRequest.all_objects.get(id=instance.id)
            logger.info(f"After delete - request {instance.id} is_deleted: {updated.is_deleted}")
        except ApiRequest.DoesNotExist:
            logger.info(f"Request {instance.id} physically deleted")
        except Exception as e:
            logger.error(f"Error checking delete status: {e}")
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """执行API请求"""
        api_request = self.get_object()
        environment_id = request.data.get('environment_id')
        
        try:
            # 创建变量解析器
            resolver = VariableResolver()

            # 解析环境变量
            variables = {}
            if environment_id:
                env = Environment.objects.get(id=environment_id)
                variables.update(env.variables)
            
            # 使用前端发送的更新后的数据，如果没有则使用数据库中的数据
            request_params = request.data.get('params', api_request.params)
            request_headers = request.data.get('headers', api_request.headers)
            request_body = request.data.get('body', api_request.body)
            request_method = request.data.get('method', api_request.method)
            request_url = request.data.get('url', api_request.url)

            # 替换URL中的变量（先解析动态函数，再替换环境变量）
            url = self._replace_variables(request_url or '', variables)
            url = resolver.resolve(url)

            # 如果URL是相对路径，自动拼接base_url
            if url and not url.startswith(('http://', 'https://')):
                base_url = None
                if environment_id:
                    # 从环境变量中获取base_url
                    base_url_var = variables.get('base_url') or variables.get('baseUrl')
                    if isinstance(base_url_var, dict):
                        base_url = str(
                            base_url_var.get('current_value', '') or
                            base_url_var.get('currentValue', '') or
                            base_url_var.get('initial_value', '') or
                            base_url_var.get('initialValue', '')
                        )
                    elif base_url_var:
                        base_url = str(base_url_var)

                if base_url:
                    # 确保base_url以/结尾，url不以/开头
                    base_url = base_url.rstrip('/')
                    url = url.lstrip('/')
                    url = f"{base_url}/{url}"

            # 准备请求头
            headers = {}
            if isinstance(request_headers, list):
                for header_item in request_headers:
                    if header_item.get('enabled', True) and header_item.get('key'):
                        key = header_item['key']
                        value = self._replace_variables(str(header_item.get('value', '')), variables)
                        value = resolver.resolve(value)
                        headers[key] = value
            else:
                headers = request_headers.copy() if request_headers else {}
                for key, value in headers.items():
                    headers[key] = self._replace_variables(str(value), variables)
                    headers[key] = resolver.resolve(headers[key])

            # 准备请求参数
            params = request_params.copy() if request_params else {}
            for key, value in params.items():
                params[key] = self._replace_variables(str(value), variables)
                params[key] = resolver.resolve(params[key])

            # 准备请求体
            body_data = None
            body_type = 'none'
            if request_body and request_method in ['POST', 'PUT', 'PATCH']:
                # 处理 body 可能是字符串的情况（API Fox 导入的数据）
                if isinstance(request_body, str):
                    try:
                        request_body = json.loads(request_body) if request_body else {}
                    except json.JSONDecodeError:
                        request_body = {'type': 'raw', 'data': request_body}
                
                body_type = request_body.get('type', 'none') if isinstance(request_body, dict) else 'raw'
                body_content = request_body.get('data') if isinstance(request_body, dict) else request_body

                if body_type == 'json':
                    if isinstance(body_content, dict):
                        body_data = self._replace_variables_in_dict(body_content, variables)
                        body_data = self._resolve_variables_in_dict(body_data, resolver)
                    elif isinstance(body_content, str):
                        # 字符串需要先解析为 JSON
                        try:
                            parsed = json.loads(body_content)
                            if isinstance(parsed, dict):
                                body_data = self._replace_variables_in_dict(parsed, variables)
                                body_data = self._resolve_variables_in_dict(body_data, resolver)
                            else:
                                body_data = parsed
                        except json.JSONDecodeError:
                            # 不是有效 JSON（可能包含变量占位符），先进行变量替换
                            body_data = self._replace_variables(body_content, variables)
                            body_data = resolver.resolve(body_data)
                            # 变量替换后，再次尝试解析为 JSON
                            if isinstance(body_data, str):
                                try:
                                    body_data = json.loads(body_data)
                                except json.JSONDecodeError:
                                    # 如果还有未替换的变量（如 {{org_id}}），
                                    # 暂时替换为占位符以便能解析为 JSON
                                    import re
                                    temp_body = re.sub(r'\{\{[^}]+\}\}', '""', body_data)
                                    try:
                                        body_data = json.loads(temp_body)
                                    except json.JSONDecodeError:
                                        # 仍然不是 JSON，保持字符串，但会被当作 raw 处理
                                        pass
                    else:
                        body_data = body_content
                elif body_type == 'raw':
                    if isinstance(body_content, str):
                        body_data = self._replace_variables(body_content, variables)
                        body_data = resolver.resolve(body_data)
                    else:
                        body_data = body_content
                elif body_type in ['form-data', 'x-www-form-urlencoded']:
                    if isinstance(body_content, list):
                        body_data = self._replace_variables_in_dict(body_content, variables)
                        body_data = self._resolve_variables_in_dict(body_data, resolver)
                    else:
                        body_data = body_content
                else:
                    body_data = body_content
            
            # 执行请求
            start_time = time.time()

            # 根据请求体类型决定使用 data 还是 json 参数
            if body_type == 'raw':
                # raw 类型使用 data 参数，发送原始字符串
                response = requests.request(
                    method=request_method,
                    url=url,
                    headers=headers,
                    params=params,
                    data=body_data,
                    timeout=30
                )
            else:
                # json 类型使用 json 参数，自动序列化
                # 如果 body_data 是字符串（JSON 解析失败），尝试解析为 JSON
                if isinstance(body_data, str):
                    try:
                        json_data = json.loads(body_data)
                        response = requests.request(
                            method=request_method,
                            url=url,
                            headers=headers,
                            params=params,
                            json=json_data,
                            timeout=30
                        )
                    except (json.JSONDecodeError, TypeError):
                        # 不是有效的 JSON，作为原始字符串发送，但设置 JSON Content-Type
                        if headers is None:
                            headers = {}
                        headers = headers.copy()
                        headers['Content-Type'] = 'application/json'
                        response = requests.request(
                            method=request_method,
                            url=url,
                            headers=headers,
                            params=params,
                            data=body_data,
                            timeout=30
                        )
                else:
                    response = requests.request(
                        method=request_method,
                        url=url,
                        headers=headers,
                        params=params,
                        json=body_data,
                        timeout=30
                    )
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000  # 转换为毫秒
            
            # 执行断言验证
            assertions = request.data.get('assertions', api_request.assertions) or []
            for assertion in assertions:
                if assertion.get('type') == 'response_time':
                    assertion['actual_time'] = response_time
            assertions_results = execute_assertions(response, assertions)

            # 解析响应体为 JSON
            response_json = None
            try:
                if response.headers.get('content-type', '').startswith('application/json'):
                    response_json = response.json()
                else:
                    response_json = json.loads(response.text)
            except:
                response_json = None

            # 执行变量提取
            extractors = request.data.get('variable_extractors', api_request.variable_extractors) or []
            extraction_result = {'variables': {}, 'results': []}
            if extractors and response_json is not None:
                extraction_result = extract_variables(
                    response_json,
                    dict(response.headers),
                    extractors
                )

                # 单接口执行：保存提取的变量到环境
                if environment_id and extraction_result['variables']:
                    save_variables_to_environment(
                        environment_id,
                        extraction_result['variables'],
                        request.user
                    )

            # 保存请求历史
            history = RequestHistory.objects.create(
                request=api_request,
                environment_id=environment_id,
                request_data={
                    'url': url,
                    'method': request_method,
                    'headers': headers,
                    'params': params,
                    'body': body_data
                },
                response_data={
                    'headers': dict(response.headers),
                    'body': response.text,
                    'json': response_json
                },
                status_code=response.status_code,
                response_time=response_time,
                assertions_results=assertions_results,
                executed_by=request.user
            )

            # 记录执行操作
            log_operation(
                operation_type='execute',
                resource_type='request',
                resource_id=api_request.id,
                resource_name=api_request.name,
                user=request.user
            )

            # 返回包含断言结果和变量提取结果的数据
            history_data = RequestHistorySerializer(history).data
            history_data['assertions_results'] = assertions_results
            history_data['extraction_results'] = extraction_result['results']
            history_data['extracted_variables'] = extraction_result['variables']

            return Response(history_data)
            
        except Environment.DoesNotExist:
            return Response({'error': '指定的执行环境不存在'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # 保存错误历史
            history = RequestHistory.objects.create(
                request=api_request,
                environment_id=environment_id,
                request_data={
                    'url': api_request.url,
                    'method': api_request.method,
                    'headers': api_request.headers,
                    'params': api_request.params,
                    'body': api_request.body
                },
                error_message=str(e),
                executed_by=request.user
            )

            return Response(RequestHistorySerializer(history).data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _replace_variables(self, text, variables, step_context=None):
        """替换文本中的变量，支持跨步骤引用"""
        if not isinstance(text, str):
            return text

        result = text

        # 首先处理跨步骤变量引用格式: {{$.N.request.body.xxx}} 或 {{$.N.response.body.xxx}}
        if step_context:
            import re
            # 匹配跨步骤引用: {{$.数字.request.xxx}} 或 {{$.数字.response.xxx}}
            # 注意: Apifox 格式是 {{$.11.response.body.data[0].id}}
            cross_step_pattern = r'\{\{\$\.(\d+)\.(request|response)(?:\.(.+?))?\}\}'
            
            # 调试: 检查是否匹配到跨步骤变量
            matches = list(re.finditer(cross_step_pattern, result))
            logger.info(f"DEBUG - _replace_variables: text='{text}', step_context={list(step_context.keys()) if step_context else None}, matches={len(matches)}")
            if matches:
                logger.info(f"DEBUG - _replace_variables: 找到 {len(matches)} 个跨步骤引用")
                for m in matches:
                    logger.info(f"DEBUG - 匹配: step={m.group(1)}, type={m.group(2)}, path={m.group(3)}")

            def replace_cross_step_ref(match):
                step_num = int(match.group(1))
                data_type = match.group(2)  # request or response
                json_path = match.group(3) or ''

                if step_num not in step_context:
                    logger.warning(f"步骤 {step_num} 不存在于上下文中")
                    return match.group(0)  # 返回原始字符串

                data_source = step_context[step_num].get(data_type)
                if not data_source:
                    return match.group(0)

                # 如果没有进一步的路径，返回整个数据源
                if not json_path:
                    return json.dumps(data_source) if isinstance(data_source, dict) else str(data_source)

                # 解析具体路径
                try:
                    # 支持 body.data[0].id 或 headers.Authorization 格式
                    current = data_source
                    parts = re.findall(r'([^\.\[\]]+)|\[(\d+)\]', json_path)
                    # 解析路径部分
                    path_parts = []
                    for part in re.finditer(r'\[(\d+)\]|([^\.\[\]]+)', json_path):
                        if part.group(1):  # 数组索引 [0]
                            path_parts.append(int(part.group(1)))
                        else:  # 属性名
                            path_parts.append(part.group(2))

                    for part in path_parts:
                        if isinstance(current, dict):
                            current = current.get(part)
                        elif isinstance(current, list) and isinstance(part, int):
                            if 0 <= part < len(current):
                                current = current[part]
                            else:
                                return match.group(0)
                        else:
                            return match.group(0)

                        if current is None:
                            return match.group(0)

                    # 返回提取的值
                    if isinstance(current, (dict, list)):
                        return json.dumps(current)
                    return str(current)
                except Exception as e:
                    logger.warning(f"解析跨步骤引用失败: {match.group(0)}, 错误: {e}")
                    return match.group(0)

            result = re.sub(cross_step_pattern, replace_cross_step_ref, result)

        # 然后处理普通变量: {{variable_name}}
        for key, value in (variables or {}).items():
            if isinstance(value, dict):
                # 支持下划线命名和小驼峰命名
                replacement = str(
                    value.get('current_value', '') or
                    value.get('currentValue', '') or
                    value.get('initial_value', '') or
                    value.get('initialValue', '')
                )
            else:
                replacement = str(value) if value is not None else ''
            result = result.replace(f'{{{{{key}}}}}', replacement)
        return result

    def _replace_variables_in_dict(self, data, variables, step_context=None):
        """递归替换字典中的变量，支持跨步骤引用"""
        if isinstance(data, dict):
            return {k: self._replace_variables_in_dict(v, variables, step_context) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._replace_variables_in_dict(item, variables, step_context) for item in data]
        elif isinstance(data, str):
            print(f"DEBUG - _replace_variables_in_dict processing str: '{data[:50]}...', step_context={list(step_context.keys()) if step_context else None}")
            return self._replace_variables(data, variables, step_context)
        else:
            return data

    def _resolve_variables_in_dict(self, data, resolver):
        """递归解析字典中的动态函数占位符"""
        if isinstance(data, dict):
            return {k: self._resolve_variables_in_dict(v, resolver) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._resolve_variables_in_dict(item, resolver) for item in data]
        elif isinstance(data, str):
            return resolver.resolve(data)
        else:
            return data

    @action(detail=False, methods=['post'])
    def generate_assertions(self, request):
        """基于响应数据使用AI生成断言"""
        try:
            # 获取请求参数
            status_code = request.data.get('status_code', 200)
            response_body = request.data.get('response_body', {})
            response_headers = request.data.get('response_headers', {})
            response_time = request.data.get('response_time')
            response_time_threshold = request.data.get('response_time_threshold', 5000)

            logger.info(f"开始生成断言请求: status_code={status_code}, response_time={response_time}")

            # 调用AI断言生成器
            assertions = AIAssertionGenerator.generate_assertions(
                status_code=status_code,
                response_body=response_body,
                response_headers=response_headers,
                response_time=response_time,
                response_time_threshold=response_time_threshold
            )

            logger.info(f"断言生成完成: 生成 {len(assertions)} 个断言")

            return Response({
                'assertions': assertions,
                'count': len(assertions),
                'source': 'ai' if assertions and len(assertions) > 0 else 'default'
            })

        except Exception as e:
            logger.error(f"生成断言失败: {e}", exc_info=True)
            return Response(
                {'error': f'生成断言失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def execute_single(self, request):
        """执行单个API请求（无需保存接口）"""
        try:
            # 获取请求参数
            method = request.data.get('method', 'GET')
            url = request.data.get('url', '')
            headers = request.data.get('headers', {})
            params = request.data.get('params', {})
            body = request.data.get('body')
            environment_id = request.data.get('environment_id')

            if not url:
                return Response(
                    {'error': 'URL不能为空'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 创建变量解析器
            resolver = VariableResolver()

            # 解析环境变量
            variables = {}
            if environment_id:
                try:
                    env = Environment.objects.get(id=environment_id)
                    variables.update(env.variables)
                except Environment.DoesNotExist:
                    pass

            # 替换URL中的变量
            final_url = self._replace_variables(url, variables)
            final_url = resolver.resolve(final_url)

            # 如果URL是相对路径，自动拼接base_url
            if final_url and not final_url.startswith(('http://', 'https://')):
                base_url = None
                if environment_id:
                    base_url_var = variables.get('base_url') or variables.get('baseUrl')
                    if isinstance(base_url_var, dict):
                        base_url = str(
                            base_url_var.get('current_value', '') or
                            base_url_var.get('currentValue', '') or
                            base_url_var.get('initial_value', '') or
                            base_url_var.get('initialValue', '')
                        )
                    elif base_url_var:
                        base_url = str(base_url_var)

                if base_url:
                    base_url = base_url.rstrip('/')
                    final_url = final_url.lstrip('/')
                    final_url = f"{base_url}/{final_url}"

            # 准备请求头
            final_headers = {}
            if isinstance(headers, dict):
                for key, value in headers.items():
                    final_headers[key] = resolver.resolve(self._replace_variables(str(value), variables))

            # 准备请求参数
            final_params = {}
            if isinstance(params, dict):
                for key, value in params.items():
                    final_params[key] = resolver.resolve(self._replace_variables(str(value), variables))

            # 准备请求体
            body_data = None
            if body and method in ['POST', 'PUT', 'PATCH']:
                if isinstance(body, dict):
                    body_data = self._replace_variables_in_dict(body, variables)
                    body_data = self._resolve_variables_in_dict(body_data, resolver)
                else:
                    body_data = resolver.resolve(self._replace_variables(str(body), variables))

            # 执行请求
            start_time = time.time()

            request_kwargs = {
                'method': method.upper(),
                'url': final_url,
                'headers': final_headers,
                'params': final_params,
                'timeout': 30
            }

            if body_data is not None:
                if isinstance(body_data, dict):
                    request_kwargs['json'] = body_data
                else:
                    request_kwargs['data'] = body_data

            # 发送请求
            response = requests.request(**request_kwargs)

            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # 转换为毫秒

            # 解析响应
            response_headers = dict(response.headers)
            response_body = response.text

            # 尝试解析JSON响应
            try:
                response_json = response.json()
            except:
                response_json = None

            return Response({
                'status_code': response.status_code,
                'response_time': response_time,
                'response_data': {
                    'headers': response_headers,
                    'body': response_body,
                    'json': response_json
                },
                'request_data': {
                    'method': method,
                    'url': final_url,
                    'headers': final_headers,
                    'params': final_params,
                    'body': body_data
                }
            })

        except Exception as e:
            logger.error(f"执行单个请求失败: {e}", exc_info=True)
            return Response(
                {'error': f'执行请求失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EnvironmentViewSet(viewsets.ModelViewSet):
    queryset = Environment.objects.all()
    serializer_class = EnvironmentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['scope', 'project', 'is_active']
    ordering = ['-created_at']
    
    def get_queryset(self):
        # 返回所有环境，不进行权限过滤
        return Environment.objects.all().order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """激活环境"""
        environment = self.get_object()
        
        # 如果是局部环境，取消同项目下其他环境的激活状态
        if environment.scope == 'LOCAL' and environment.project:
            Environment.objects.filter(
                project=environment.project,
                scope='LOCAL'
            ).update(is_active=False)
        # 如果是全局环境，取消其他全局环境的激活状态
        elif environment.scope == 'GLOBAL':
            Environment.objects.filter(scope='GLOBAL').update(is_active=False)
        
        environment.is_active = True
        environment.save()
        
        return Response({'message': '环境已激活'})

    def perform_create(self, serializer):
        """创建环境时记录日志"""
        instance = serializer.save()
        log_operation(
            operation_type='create',
            resource_type='environment',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )

    def perform_update(self, serializer):
        """更新环境时记录日志"""
        instance = serializer.save()
        log_operation(
            operation_type='edit',
            resource_type='environment',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )

    def perform_destroy(self, instance):
        """删除环境时记录日志"""
        log_operation(
            operation_type='delete',
            resource_type='environment',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )
        instance.delete()


class RequestHistoryViewSet(viewsets.ModelViewSet):
    queryset = RequestHistory.objects.all()
    serializer_class = RequestHistorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['request__request_type', 'status_code']
    search_fields = ['request__name']
    ordering = ['-executed_at']
    pagination_class = StandardPagination

    def get_queryset(self):
        # 返回所有请求历史，不进行权限过滤
        return RequestHistory.objects.all().select_related(
            'request', 'environment', 'executed_by',
            'request__created_by', 'environment__created_by', 'environment__project'
        )

    @action(detail=False, methods=['post'], url_path='batch-delete')
    def batch_delete(self, request):
        """批量删除请求历史"""
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'error': '未提供要删除的记录ID'}, status=status.HTTP_400_BAD_REQUEST)

        # 确保只能删除有权限的记录
        # 先获取有权限的ID列表，避免在distinct()后调用delete()
        queryset = self.get_queryset()
        valid_ids = list(queryset.filter(id__in=ids).values_list('id', flat=True))

        # 使用有权限的ID列表进行删除
        deleted_count, _ = RequestHistory.objects.filter(id__in=valid_ids).delete()

        return Response({'message': f'成功删除 {deleted_count} 条记录'})

    @action(detail=False, methods=['get'], url_path='latest')
    def latest(self, request):
        """获取指定接口的最新执行记录"""
        request_id = request.query_params.get('request_id')
        if not request_id:
            return Response({'error': '缺少 request_id 参数'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 将 request_id 转换为整数
            try:
                request_id = int(request_id)
            except (ValueError, TypeError):
                return Response({'error': 'request_id 必须是有效的整数'}, status=status.HTTP_400_BAD_REQUEST)

            # 获取该接口的最新执行记录
            latest_history = self.get_queryset().filter(
                request_id=request_id
            ).order_by('-executed_at').first()

            if not latest_history:
                return Response({'error': '未找到该接口的执行记录'}, status=status.HTTP_404_NOT_FOUND)

            serializer = self.get_serializer(latest_history)
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestSuiteViewSet(viewsets.ModelViewSet):
    queryset = TestSuite.objects.all()
    serializer_class = TestSuiteSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['project']

    def get_queryset(self):
        queryset = TestSuite.objects.all()

        # 排除自身（用于引用其他场景时）
        exclude_self = self.request.query_params.get('exclude_self')
        if exclude_self:
            queryset = queryset.exclude(id=exclude_self)

        # 时间范围筛选
        created_after = self.request.query_params.get('created_after')
        created_before = self.request.query_params.get('created_before')
        if created_after:
            # 将日期字符串转换为 datetime 的开始时间 (00:00:00)
            from datetime import datetime
            start_date = datetime.strptime(created_after, '%Y-%m-%d')
            queryset = queryset.filter(created_at__gte=start_date)
        if created_before:
            # 将日期字符串转换为 datetime 的结束时间 (23:59:59)
            from datetime import datetime, timedelta
            end_date = datetime.strptime(created_before, '%Y-%m-%d') + timedelta(days=1)
            queryset = queryset.filter(created_at__lt=end_date)

        # 评审状态筛选
        review_status = self.request.query_params.get('review_status')
        if review_status:
            # 根据评审状态筛选测试套件
            # 获取所有测试套件的ID
            suite_ids = list(queryset.values_list('id', flat=True))

            # 获取每个测试套件的评审摘要
            matching_suite_ids = []
            for suite_id in suite_ids:
                try:
                    suite = TestSuite.objects.get(id=suite_id)
                    # 计算评审状态
                    review_records = TestSuiteReviewRecord.objects.filter(test_suite=suite)
                    total_reviews = review_records.count()

                    if total_reviews == 0:
                        overall_status = 'pending'
                    else:
                        approved_count = review_records.filter(status='approved').count()
                        rejected_count = review_records.filter(status='rejected').count()

                        if rejected_count > 0:
                            overall_status = 'rejected'
                        elif approved_count == total_reviews:
                            overall_status = 'approved'
                        else:
                            overall_status = 'partial'

                    if overall_status == review_status:
                        matching_suite_ids.append(suite_id)
                except TestSuite.DoesNotExist:
                    continue

            queryset = queryset.filter(id__in=matching_suite_ids)

        return queryset

    def _replace_variables(self, text, variables, step_context=None):
        """替换文本中的变量，支持跨步骤引用"""
        if not isinstance(text, str):
            return text

        result = text

        # 首先处理跨步骤变量引用格式: {{$.N.request.body.xxx}} 或 {{$.N.response.body.xxx}}
        if step_context:
            import re
            # 匹配跨步骤引用: {{$.数字.request.xxx}} 或 {{$.数字.response.xxx}}
            # 注意: Apifox 格式是 {{$.11.response.body.data[0].id}}
            cross_step_pattern = r'\{\{\$\.(\d+)\.(request|response)(?:\.(.+?))?\}\}'

            # 调试日志
            matches = list(re.finditer(cross_step_pattern, result))
            print(f"DEBUG - TestSuiteViewSet._replace_variables: text='{text}', step_context={list(step_context.keys()) if step_context else None}, matches={len(matches)}")

            def replace_cross_step_ref(match):
                step_num = int(match.group(1))
                data_type = match.group(2)  # request or response
                json_path = match.group(3) or ''

                print(f"DEBUG - replace_cross_step_ref: step_num={step_num}, data_type={data_type}, json_path={json_path}")
                print(f"DEBUG - step_context keys: {list(step_context.keys())}")

                if step_num not in step_context:
                    print(f"DEBUG - step {step_num} not in step_context")
                    return match.group(0)  # 返回原始字符串

                data_source = step_context[step_num].get(data_type)
                print(f"DEBUG - data_source for {data_type}: {data_source is not None}")
                if not data_source:
                    return match.group(0)

                # 如果没有进一步的路径，返回整个数据源
                if not json_path:
                    return json.dumps(data_source) if isinstance(data_source, dict) else str(data_source)

                # 解析具体路径
                try:
                    # 支持 body.data[0].id 或 headers.Authorization 格式
                    current = data_source
                    print(f"DEBUG - current data_source type: {type(current)}")
                    # 解析路径部分
                    path_parts = []
                    for part in re.finditer(r'\[(\d+)\]|([^\.\[\]]+)', json_path):
                        if part.group(1):  # 数组索引 [0]
                            path_parts.append(int(part.group(1)))
                        else:  # 属性名
                            path_parts.append(part.group(2))
                    print(f"DEBUG - path_parts: {path_parts}")

                    for i, part in enumerate(path_parts):
                        print(f"DEBUG - processing part {i}: {part}, current type: {type(current)}")
                        # 如果当前是字符串（通常是 body），尝试解析为 JSON
                        if isinstance(current, str) and i > 0:  # i > 0 确保不是第一层
                            try:
                                current = json.loads(current)
                                print(f"DEBUG - parsed string to JSON")
                            except:
                                pass  # 如果不是有效 JSON，保持原样

                        if isinstance(current, dict):
                            current = current.get(part)
                            print(f"DEBUG - got from dict: {current}")
                        elif isinstance(current, list) and isinstance(part, int):
                            if 0 <= part < len(current):
                                current = current[part]
                            else:
                                print(f"DEBUG - index {part} out of range")
                                return match.group(0)
                        else:
                            print(f"DEBUG - cannot navigate: current is {type(current)}, part is {part}")
                            return match.group(0)

                        if current is None:
                            print(f"DEBUG - current is None after part {part}")
                            return match.group(0)

                    # 返回提取的值
                    print(f"DEBUG - final value: {current}")
                    if isinstance(current, (dict, list)):
                        return json.dumps(current)
                    return str(current)
                except Exception as e:
                    print(f"DEBUG - exception: {e}")
                    return match.group(0)

            result = re.sub(cross_step_pattern, replace_cross_step_ref, result)

        # 然后处理普通变量: {{variable_name}}
        for key, value in (variables or {}).items():
            if isinstance(value, dict):
                # 支持下划线命名和小驼峰命名
                replacement = str(
                    value.get('current_value', '') or
                    value.get('currentValue', '') or
                    value.get('initial_value', '') or
                    value.get('initialValue', '')
                )
            else:
                replacement = str(value) if value is not None else ''
            result = result.replace(f'{{{{{key}}}}}', replacement)
        return result

    def _replace_variables_in_dict(self, data, variables, step_context=None):
        """递归替换字典中的变量，支持跨步骤引用"""
        if isinstance(data, dict):
            return {k: self._replace_variables_in_dict(v, variables, step_context) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._replace_variables_in_dict(item, variables, step_context) for item in data]
        elif isinstance(data, str):
            print(f"DEBUG - TestSuiteViewSet._replace_variables_in_dict processing str: '{data[:50]}...', step_context={list(step_context.keys()) if step_context else None}")
            return self._replace_variables(data, variables, step_context)
        else:
            return data

    def _resolve_variables_in_dict(self, data, resolver):
        """递归解析字典中的动态函数占位符"""
        if isinstance(data, dict):
            return {k: self._resolve_variables_in_dict(v, resolver) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._resolve_variables_in_dict(item, resolver) for item in data]
        elif isinstance(data, str):
            return resolver.resolve(data)
        else:
            return data

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """执行测试套件"""
        test_suite = self.get_object()
        
        try:
            # 创建执行记录
            execution = TestExecution.objects.create(
                test_suite=test_suite,
                status='RUNNING',
                start_time=timezone.now(),
                executed_by=request.user
            )
            
            # 获取套件中的请求 - 预加载request对象及其所有字段
            suite_requests = TestSuiteRequest.objects.filter(
                test_suite=test_suite,
                enabled=True
            ).select_related('request').order_by('order')

            # 统计实际请求数（排除分组类型）
            actual_request_count = sum(1 for sr in suite_requests if sr.step_type != 'group' and sr.request is not None)
            execution.total_requests = actual_request_count
            execution.save()
            
            results = []
            passed_count = 0
            failed_count = 0

            # 创建变量解析器
            resolver = VariableResolver()

            # 用于存储执行过程中提取的变量
            extracted_variables = {}
            
            # 用于支持跨步骤变量引用的步骤上下文
            step_context = {}
            current_step_index = 0
            
            # 初始化logger
            import logging
            logger = logging.getLogger(__name__)

            # 执行每个请求
            for suite_request in suite_requests:
                current_step_index = suite_request.order
                api_request = suite_request.request

                # 处理等待时间步骤
                if suite_request.step_type == 'wait':
                    # 从关联的场景步骤获取 control_config
                    control_config = {}
                    if hasattr(suite_request, 'scenario_step') and suite_request.scenario_step:
                        control_config = suite_request.scenario_step.control_config or {}
                    wait_time = control_config.get('wait_time', 1)
                    step_name = suite_request.override_name or '等待时间'
                    logger.info(f"DEBUG - 执行等待步骤: order={current_step_index}, name={step_name}, wait_time={wait_time}")
                    time.sleep(wait_time)
                    results.append({
                        'name': step_name,
                        'method': 'WAIT',
                        'url': f'等待 {wait_time} 秒',
                        'passed': True,
                        'duration': wait_time * 1000,  # 转换为毫秒
                        'status_code': None,
                        'response_time': wait_time * 1000
                    })
                    passed_count += 1
                    continue

                # 跳过分组类型步骤（group 只是容器，不是真正的接口请求）
                if suite_request.step_type == 'group' or api_request is None:
                    step_name = api_request.name if api_request else '未命名分组'
                    logger.info(f"DEBUG - 跳过分组步骤: order={current_step_index}, name={step_name}")
                    continue

                logger.info(f"DEBUG - 开始执行步骤: order={current_step_index}, name={api_request.name}, id={api_request.id}")

                try:
                    # 调试日志 - 打印完整的请求信息
                    logger.info(f"DEBUG - api_request.id: {api_request.id}")
                    logger.info(f"DEBUG - api_request.name: {api_request.name}")
                    logger.info(f"DEBUG - api_request.url: {api_request.url}")
                    logger.info(f"DEBUG - api_request.variable_extractors: {api_request.variable_extractors}")
                    logger.info(f"DEBUG - api_request.headers type: {type(api_request.headers)}")
                    logger.info(f"DEBUG - api_request.headers value: {api_request.headers}")
                    logger.info(f"DEBUG - suite_request.override_url: {suite_request.override_url}")
                    logger.info(f"DEBUG - suite_request.override_method: {suite_request.override_method}")
                    
                    # 解析环境变量 - 重新查询确保获取最新数据
                    variables = {}
                    # 1. 先加载全局环境变量
                    global_envs = Environment.objects.filter(scope='GLOBAL')
                    for env in global_envs:
                        variables.update(env.variables)
                    # 2. 再加载套件指定的环境变量（会覆盖全局变量）
                    if test_suite.environment:
                        env = Environment.objects.get(id=test_suite.environment.id)
                        variables.update(env.variables)
                    # 3. 添加之前接口提取的变量
                    logger.info(f"DEBUG - 当前 extracted_variables: {extracted_variables}")
                    variables.update(extracted_variables)
                    logger.info(f"DEBUG - 合并后用于替换的 variables: {variables}")
                    
                    # 更新 resolver.context 以便支持 {{variable_name}} 格式的变量替换
                    logger.info(f"DEBUG - 更新前 resolver_id={id(resolver)}, context={resolver.context}")
                    resolver.context.update(extracted_variables)
                    logger.info(f"DEBUG - 更新后 resolver_id={id(resolver)}, context: {resolver.context}")
                    
                    # 获取有效的请求配置（优先使用覆盖配置）
                    effective_method = suite_request.get_effective_method()
                    effective_url = suite_request.get_effective_url()
                    effective_headers = suite_request.get_effective_headers()
                    effective_params = suite_request.get_effective_params()
                    effective_body = suite_request.get_effective_body()
                    
                    logger.info(f"DEBUG - effective_method: {effective_method}")
                    logger.info(f"DEBUG - effective_url: {effective_url}")
                    logger.info(f"DEBUG - effective_headers: {effective_headers}")
                    
                    # 执行前置脚本
                    if suite_request.pre_script:
                        try:
                            logger.info(f"DEBUG - 执行前置脚本")
                            script_context = {
                                'variables': variables,
                                'request': {
                                    'method': effective_method,
                                    'url': effective_url,
                                    'headers': effective_headers,
                                    'params': effective_params,
                                    'body': effective_body
                                }
                            }
                            exec(suite_request.pre_script, script_context)
                            # 更新变量
                            if 'variables' in script_context:
                                variables.update(script_context['variables'])
                                logger.info(f"DEBUG - 前置脚本更新后的变量: {variables}")
                        except Exception as script_error:
                            logger.error(f"DEBUG - 前置脚本执行失败: {str(script_error)}")
                    
                    # 替换URL中的变量（先处理跨步骤引用，再解析动态函数，最后替换环境变量）
                    logger.info(f"DEBUG - Before replace: effective_url={effective_url}")
                    logger.info(f"DEBUG - step_context keys: {list(step_context.keys())}")
                    url = self._replace_variables(effective_url, variables, step_context)
                    logger.info(f"DEBUG - After replace: url={url}")
                    url = resolver.resolve(url)

                    # 如果URL是相对路径，自动拼接base_url
                    if url and not url.startswith(('http://', 'https://')):
                        base_url = None
                        if test_suite.environment:
                            # 从环境变量中获取base_url
                            base_url_var = variables.get('base_url') or variables.get('baseUrl')
                            if isinstance(base_url_var, dict):
                                base_url = str(
                                    base_url_var.get('current_value', '') or
                                    base_url_var.get('currentValue', '') or
                                    base_url_var.get('initial_value', '') or
                                    base_url_var.get('initialValue', '')
                                )
                            elif base_url_var:
                                base_url = str(base_url_var)

                        if base_url:
                            # 确保base_url以/结尾，url不以/开头
                            base_url = base_url.rstrip('/')
                            url = url.lstrip('/')
                            url = f"{base_url}/{url}"

                    # 准备请求头
                    headers = {}
                    # 调试日志
                    logger.info(f"DEBUG - effective_headers: {effective_headers}")
                    logger.info(f"DEBUG - variables: {variables}")
                    
                    # 1. 首先添加环境变量中的常用 Headers (TenantId, Authorization 等)
                    header_vars = ['TenantId', 'Authorization', 'Content-Type', 'Accept']
                    for var_name in header_vars:
                        if var_name in variables:
                            var_value = variables[var_name]
                            if isinstance(var_value, dict):
                                # 获取 current_value 或 initial_value
                                header_value = str(
                                    var_value.get('current_value', '') or
                                    var_value.get('currentValue', '') or
                                    var_value.get('initial_value', '') or
                                    var_value.get('initialValue', '')
                                )
                            else:
                                header_value = str(var_value) if var_value is not None else ''
                            
                            # 解析变量引用
                            header_value = self._replace_variables(header_value, variables, step_context)
                            header_value = resolver.resolve(header_value)
                            
                            if header_value:
                                headers[var_name] = header_value
                                logger.info(f"DEBUG - Header from env: {var_name}={header_value}")
                    
                    # 2. 再添加覆盖配置中的 Headers（优先于原始接口配置）
                    # 支持新的数组格式和旧的对象格式
                    if isinstance(effective_headers, list):
                        # 新的数组格式 [{"key": "Authorization", "value": "Bearer {{token}}", "enabled": true, "description": "..."}]
                        for header_item in effective_headers:
                            if header_item.get('enabled', True) and header_item.get('key'):
                                key = header_item['key']
                                value = self._replace_variables(str(header_item.get('value', '')), variables, step_context)
                                value = resolver.resolve(value)
                                headers[key] = value
                                logger.info(f"DEBUG - Header from effective: {key}={value}")
                    else:
                        # 旧的对象格式 {"Authorization": "Bearer {{token}}"}
                        for key, value in effective_headers.items():
                            processed_value = self._replace_variables(str(value), variables, step_context)
                            processed_value = resolver.resolve(processed_value)
                            headers[key] = processed_value
                            logger.info(f"DEBUG - Header from effective: {key}={processed_value}")

                    params = effective_params.copy() if effective_params else {}
                    for key, value in params.items():
                        params[key] = self._replace_variables(str(value), variables, step_context)
                        params[key] = resolver.resolve(params[key])

                    # 准备请求体 - 与单接口执行逻辑保持一致
                    body_data = None
                    body_type = 'none'
                    if effective_body and effective_method in ['POST', 'PUT', 'PATCH']:
                        # 处理 body 可能是字符串的情况（API Fox 导入的数据）
                        body = effective_body
                        if isinstance(body, str):
                            try:
                                body = json.loads(body) if body else {}
                            except json.JSONDecodeError:
                                body = {'type': 'raw', 'data': body}
                        
                        body_type = body.get('type', 'none') if isinstance(body, dict) else 'raw'
                        body_content = body.get('data') if isinstance(body, dict) else body

                        if body_type == 'json':
                            if isinstance(body_content, dict):
                                logger.info(f"DEBUG - json body_content before replace: {body_content}")
                                logger.info(f"DEBUG - step_context keys: {list(step_context.keys())}")
                                body_data = self._replace_variables_in_dict(body_content, variables, step_context)
                                logger.info(f"DEBUG - json body_data after replace: {body_data}")
                                body_data = self._resolve_variables_in_dict(body_data, resolver)
                                logger.info(f"DEBUG - json body_data after resolve: {body_data}")
                            elif isinstance(body_content, str):
                                # 字符串需要先解析为 JSON
                                try:
                                    parsed = json.loads(body_content)
                                    if isinstance(parsed, dict):
                                        body_data = self._replace_variables_in_dict(parsed, variables, step_context)
                                        body_data = self._resolve_variables_in_dict(body_data, resolver)
                                    else:
                                        body_data = parsed
                                except json.JSONDecodeError:
                                    # 不是有效 JSON（可能包含变量占位符），先进行变量替换
                                    body_data = self._replace_variables(body_content, variables, step_context)
                                    body_data = resolver.resolve(body_data)
                                    # 变量替换后，再次尝试解析为 JSON
                                    if isinstance(body_data, str):
                                        try:
                                            body_data = json.loads(body_data)
                                        except json.JSONDecodeError:
                                            # 如果还有未替换的变量（如 {{org_id}}），
                                            # 暂时替换为占位符以便能解析为 JSON
                                            import re
                                            temp_body = re.sub(r'\{\{[^}]+\}\}', '""', body_data)
                                            try:
                                                body_data = json.loads(temp_body)
                                            except json.JSONDecodeError:
                                                # 仍然不是 JSON，保持字符串
                                                pass
                            else:
                                body_data = body_content
                        elif body_type == 'raw':
                            if isinstance(body_content, str):
                                logger.info(f"DEBUG - raw body_content before replace: {body_content}")
                                logger.info(f"DEBUG - variables for replace: {variables}")
                                body_data = self._replace_variables(body_content, variables, step_context)
                                logger.info(f"DEBUG - raw body_data after replace: {body_data}")
                                body_data = resolver.resolve(body_data)
                                logger.info(f"DEBUG - raw body_data after resolve: {body_data}")
                            else:
                                body_data = body_content
                        elif body_type in ['form-data', 'x-www-form-urlencoded']:
                            if isinstance(body_content, list):
                                body_data = self._replace_variables_in_dict(body_content, variables, step_context)
                                body_data = self._resolve_variables_in_dict(body_data, resolver)
                            else:
                                body_data = body_content
                        else:
                            body_data = body_content

                    # 执行请求
                    start_time = time.time()
                    
                    # 根据请求体类型决定使用 data 还是 json 参数
                    if body_type == 'raw':
                        # raw 类型：尝试解析为 JSON，如果成功则作为 JSON 发送
                        if isinstance(body_data, str):
                            try:
                                json_data = json.loads(body_data)
                                # 是有效的 JSON，使用 json 参数发送（自动设置 Content-Type）
                                response = requests.request(
                                    method=effective_method,
                                    url=url,
                                    headers=headers,
                                    params=params,
                                    json=json_data,
                                    timeout=30
                                )
                            except (json.JSONDecodeError, TypeError):
                                # 不是 JSON，作为原始字符串发送
                                response = requests.request(
                                    method=effective_method,
                                    url=url,
                                    headers=headers,
                                    params=params,
                                    data=body_data,
                                    timeout=30
                                )
                        else:
                            # body_data 不是字符串，直接使用 data 参数
                            response = requests.request(
                                method=effective_method,
                                url=url,
                                headers=headers,
                                params=params,
                                data=body_data,
                                timeout=30
                            )
                    else:
                        # json 类型使用 json 参数，自动序列化
                        # 如果 body_data 是字符串（JSON 解析失败），需要特殊处理
                        if isinstance(body_data, str):
                            try:
                                json_data = json.loads(body_data)
                                response = requests.request(
                                    method=effective_method,
                                    url=url,
                                    headers=headers,
                                    params=params,
                                    json=json_data,
                                    timeout=30
                                )
                            except (json.JSONDecodeError, TypeError):
                                # 不是有效的 JSON，作为原始字符串发送，但设置 JSON Content-Type
                                if headers is None:
                                    headers = {}
                                headers = headers.copy()
                                headers['Content-Type'] = 'application/json'
                                response = requests.request(
                                    method=effective_method,
                                    url=url,
                                    headers=headers,
                                    params=params,
                                    data=body_data,
                                    timeout=30
                                )
                        else:
                            response = requests.request(
                                method=effective_method,
                                url=url,
                                headers=headers,
                                params=params,
                                json=body_data,
                                timeout=30
                            )
                    end_time = time.time()
                    response_time = (end_time - start_time) * 1000
                    
                    # 执行断言验证 - 使用套件请求的断言（支持在套件中为每个请求单独配置断言）
                    # 优先使用 suite_request.assertions，如果没有则回退到 api_request.assertions
                    assertions = suite_request.assertions or api_request.assertions or []
                    logger.info(f"DEBUG - 断言数据: suite_request.assertions={suite_request.assertions}, api_request.assertions={api_request.assertions}")
                    logger.info(f"DEBUG - 最终使用的 assertions={assertions}")
                    # 添加响应时间到断言中
                    for assertion in assertions:
                        if assertion.get('type') == 'response_time':
                            assertion['actual_time'] = response_time
                    
                    # 使用共享的断言执行方法，传入 resolver 和 step_context 用于变量替换
                    logger.info(f"DEBUG - 调用 execute_assertions, assertions count={len(assertions)}, resolver_id={id(resolver)}, context={resolver.context}")
                    assertions_results = execute_assertions(response, assertions, resolver, step_context)
                    logger.info(f"DEBUG - 断言执行结果: {assertions_results}")
                    
                    # 检查所有断言是否通过
                    passed = True
                    error_message = ''

                    # 检查断言结果（已包含套件请求和接口自身的断言）
                    if assertions_results:
                        for assertion_result in assertions_results:
                            if not assertion_result.get('passed', True):
                                passed = False
                                # 如果error已经包含详细信息，直接使用
                                error_detail = assertion_result.get('error')
                                if error_detail:
                                    error_message = f"{assertion_result.get('name', '未命名断言')}: {error_detail}"
                                else:
                                    error_message = f"{assertion_result.get('name', '未命名断言')}: 断言不通过"
                                break

                    # 检查状态码，>= 400 视为失败（与前端逻辑保持一致）
                    if response.status_code >= 400:
                        passed = False
                        if not error_message:
                            error_message = f"状态码错误: {response.status_code}"
                    
                    # 解析响应体为 JSON
                    response_json = None
                    try:
                        if response.headers.get('content-type', '').startswith('application/json'):
                            response_json = response.json()
                        else:
                            response_json = json.loads(response.text)
                    except:
                        response_json = None

                    # 记录步骤上下文（用于跨步骤变量引用）
                    step_context[current_step_index] = {
                        'request': {
                            'method': effective_method,
                            'url': url,
                            'headers': headers,
                            'params': params,
                            'body': body_data
                        },
                        'response': {
                            'status_code': response.status_code,
                            'headers': dict(response.headers),
                            'body': response_json if response_json is not None else response.text
                        }
                    }
                    logger.info(f"DEBUG - 记录步骤 {current_step_index} 上下文")

                    # 执行变量提取
                    extraction_result = {'variables': {}, 'results': []}
                    logger.info(f"DEBUG - 变量提取检查: api_request.variable_extractors={api_request.variable_extractors}, response_json={response_json is not None}")
                    if api_request.variable_extractors and response_json is not None:
                        logger.info(f"DEBUG - 开始执行变量提取: extractors={api_request.variable_extractors}")
                        extraction_result = extract_variables(
                            response_json,
                            dict(response.headers),
                            api_request.variable_extractors
                        )
                        logger.info(f"DEBUG - 变量提取结果: {extraction_result}")
                        # 将提取的变量添加到执行变量中，供后续接口使用
                        extracted_variables.update(extraction_result['variables'])
                        logger.info(f"DEBUG - 更新后的 extracted_variables: {extracted_variables}")
                    else:
                        logger.info(f"DEBUG - 跳过变量提取: variable_extractors={api_request.variable_extractors}, response_json={response_json}")

                    # 执行后置脚本
                    if suite_request.post_script:
                        try:
                            logger.info(f"DEBUG - 执行后置脚本")
                            script_context = {
                                'variables': variables,
                                'response': {
                                    'status_code': response.status_code,
                                    'headers': dict(response.headers),
                                    'body': response_json or response.text,
                                    'text': response.text
                                },
                                'request': {
                                    'method': effective_method,
                                    'url': url,
                                    'headers': headers,
                                    'params': params,
                                    'body': body_data
                                }
                            }
                            exec(suite_request.post_script, script_context)
                            # 更新变量
                            if 'variables' in script_context:
                                variables.update(script_context['variables'])
                                extracted_variables.update(script_context['variables'])
                                logger.info(f"DEBUG - 后置脚本更新后的变量: {variables}")
                        except Exception as script_error:
                            logger.error(f"DEBUG - 后置脚本执行失败: {str(script_error)}")

                    if passed:
                        passed_count += 1
                    else:
                        failed_count += 1

                    results.append({
                        'name': api_request.name,
                        'method': effective_method,
                        'url': url,
                        'status_code': response.status_code,
                        'response_time': response_time,
                        'passed': passed,
                        'error': error_message,
                        'assertions_results': assertions_results,
                        'extraction_results': extraction_result['results'],
                        'extracted_variables': extraction_result['variables'],
                        'request_data': {
                            'url': url,
                            'method': effective_method,
                            'headers': headers,
                            'params': params,
                            'body': body_data
                        },
                        'response_data': {
                            'headers': dict(response.headers),
                            'body': response.text[:5000] if len(response.text) > 5000 else response.text,  # 限制响应体大小
                            'json': response_json
                        }
                    })

                    # 保存请求历史
                    RequestHistory.objects.create(
                        request=api_request,
                        environment=test_suite.environment,
                        request_data={
                            'url': url,
                            'method': effective_method,
                            'headers': headers,
                            'params': params,
                            'body': body_data
                        },
                        response_data={
                            'headers': dict(response.headers),
                            'body': response.text,
                            'json': response_json
                        },
                        status_code=response.status_code,
                        response_time=response_time,
                        assertions_results=assertions_results,
                        executed_by=request.user
                    )
                    
                except Exception as e:
                    failed_count += 1
                    results.append({
                        'name': api_request.name,
                        'method': effective_method,
                        'url': api_request.url,
                        'passed': False,
                        'error': str(e)
                    })
            
            # 更新执行结果
            execution.end_time = timezone.now()
            execution.passed_requests = passed_count
            execution.failed_requests = failed_count
            execution.status = 'COMPLETED' if failed_count == 0 else 'FAILED'
            execution.results = results
            execution.save()

            # 记录执行操作
            log_operation(
                operation_type='execute',
                resource_type='suite',
                resource_id=test_suite.id,
                resource_name=test_suite.name,
                user=request.user
            )

            return Response(TestExecutionSerializer(execution).data)
            
        except Environment.DoesNotExist:
            execution.status = 'FAILED'
            execution.end_time = timezone.now()
            execution.save()
            return Response({'error': '指定的执行环境不存在'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logger.error(f"执行测试套件失败: {str(e)}")
            logger.error(f"错误堆栈: {error_detail}")
            execution.status = 'FAILED'
            execution.end_time = timezone.now()
            execution.save()
            return Response({'error': str(e), 'detail': error_detail}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_create(self, serializer):
        """创建测试套件时记录日志"""
        instance = serializer.save()
        log_operation(
            operation_type='create',
            resource_type='suite',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )

    def perform_update(self, serializer):
        """更新测试套件时记录日志"""
        instance = serializer.save()
        log_operation(
            operation_type='edit',
            resource_type='suite',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )

    def perform_destroy(self, instance):
        """删除测试套件时记录日志"""
        log_operation(
            operation_type='delete',
            resource_type='suite',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )
        instance.delete()

    @action(detail=True, methods=['post'], url_path='add-requests')
    def add_requests(self, request, pk=None):
        """添加请求到测试套件"""
        test_suite = self.get_object()
        request_ids = request.data.get('request_ids', [])

        added_count = 0
        restored_count = 0
        
        print(f"DEBUG - 开始添加请求, request_ids: {request_ids}")
        for request_id in request_ids:
            print(f"DEBUG - 处理 request_id: {request_id}")
            try:
                api_request = ApiRequest.objects.get(id=request_id)
                print(f"DEBUG - 找到 ApiRequest: {api_request.name}")
                
                # 检查是否已存在且被删除的请求，如果是则恢复
                existing_request = TestSuiteRequest.all_objects.filter(
                    test_suite=test_suite,
                    request=api_request,
                    is_deleted=True
                ).first()
                
                print(f"DEBUG - existing_request (is_deleted=True): {existing_request}")
                
                if existing_request:
                    # 恢复已删除的请求
                    print(f"DEBUG - 恢复已删除的请求: {existing_request.id}")
                    existing_request.is_deleted = False
                    existing_request.deleted_at = None
                    existing_request.order = TestSuiteRequest.objects.filter(test_suite=test_suite).count()
                    existing_request.enabled = True
                    existing_request.save(update_fields=['is_deleted', 'deleted_at', 'order', 'enabled'])
                    restored_count += 1
                    print(f"DEBUG - 恢复成功, restored_count: {restored_count}")
                else:
                    # 创建新请求（允许重复添加已存在的接口）
                    print(f"DEBUG - 创建新请求")
                    try:
                        new_request = TestSuiteRequest.objects.create(
                            test_suite=test_suite,
                            request=api_request,
                            order=TestSuiteRequest.objects.filter(test_suite=test_suite).count(),
                            enabled=True,
                            assertions=api_request.assertions or []
                        )
                        print(f"DEBUG - 创建新请求成功: id={new_request.id}, request_id={request_id}")
                        added_count += 1
                        print(f"DEBUG - added_count: {added_count}")
                    except Exception as create_error:
                        print(f"DEBUG - 创建新请求失败: request_id={request_id}, error={str(create_error)}")
                        import traceback
                        print(f"DEBUG - 错误堆栈: {traceback.format_exc()}")
                        logger.error(f"创建请求 {request_id} 失败: {str(create_error)}")
                        raise
                    
            except ApiRequest.DoesNotExist:
                print(f"DEBUG - ApiRequest 不存在: request_id={request_id}")
                continue
            except Exception as e:
                print(f"DEBUG - 添加请求 {request_id} 失败: {str(e)}")
                import traceback
                print(f"DEBUG - 错误堆栈: {traceback.format_exc()}")
                logger.error(f"添加请求 {request_id} 失败: {str(e)}")
                continue
        
        print(f"DEBUG - 添加请求完成, added_count: {added_count}, restored_count: {restored_count}")

        # 更新套件的 updated_at 时间戳
        test_suite.save(update_fields=['updated_at'])
        
        # 返回包含套件数据的响应，确保前端能获取最新数据
        serializer = self.get_serializer(test_suite)
        
        message_parts = []
        if added_count > 0:
            message_parts.append(f'成功添加 {added_count} 个请求')
        if restored_count > 0:
            message_parts.append(f'恢复 {restored_count} 个已删除的请求')
        
        message = '，'.join(message_parts) if message_parts else '操作完成'

        return Response({
            'message': message,
            'added_count': added_count,
            'restored_count': restored_count,
            'suite': serializer.data
        })

    @action(detail=True, methods=['post'], url_path='add-suites')
    def add_suites(self, request, pk=None):
        """添加其他场景作为分组到当前测试套件，支持选择特定步骤"""
        test_suite = self.get_object()
        
        # 兼容旧版 API：suite_ids
        suite_ids = request.data.get('suite_ids', [])
        # 新版 API：suite_selections，支持选择特定步骤
        suite_selections = request.data.get('suite_selections', [])
        
        # 如果没有新版参数，使用旧版参数转换
        if not suite_selections and suite_ids:
            suite_selections = [{'suite_id': sid, 'selected_steps': None} for sid in suite_ids]

        try:
            added_count = 0
            existing_count = 0
            total_requests = 0

            for selection in suite_selections:
                suite_id = selection.get('suite_id')
                selected_steps = selection.get('selected_steps')  # None 表示选择整个场景
                
                if not suite_id:
                    continue
                
                # 获取要引用的场景
                source_suite = TestSuite.objects.get(id=suite_id)

                # 获取该场景下的请求
                source_requests_query = TestSuiteRequest.objects.filter(
                    test_suite=source_suite,
                    enabled=True
                ).select_related('request').order_by('order')
                
                # 如果选择了特定步骤，只获取这些步骤
                if selected_steps:
                    source_requests_query = source_requests_query.filter(id__in=selected_steps)

                source_requests = list(source_requests_query)

                if not source_requests:
                    continue

                # 计算当前基础order
                base_order = TestSuiteRequest.objects.filter(test_suite=test_suite).count()

                # 创建分组节点作为父节点
                group_node = TestSuiteRequest.objects.create(
                    test_suite=test_suite,
                    request=None,  # 分组节点没有关联的请求
                    order=base_order,
                    enabled=True,
                    step_type='group',
                    override_name=source_suite.name,  # 使用场景名称作为分组名称
                    assertions=[],
                    extracted_variables={}
                )
                added_count += 1

                # 构建请求字典和父子关系映射
                # 注意：需要从原场景获取完整的父子关系，而不仅仅是选中的步骤
                children_map = {}  # parent_id -> [child_requests]
                
                # 获取原场景的所有请求以构建完整的children_map
                all_source_requests = TestSuiteRequest.objects.filter(
                    test_suite=source_suite,
                    enabled=True
                ).select_related('request')
                
                all_request_ids = set(all_source_requests.values_list('id', flat=True))
                
                for sr in all_source_requests:
                    if sr.parent_id and sr.parent_id in all_request_ids:
                        if sr.parent_id not in children_map:
                            children_map[sr.parent_id] = []
                        children_map[sr.parent_id].append(sr)

                # 递归处理场景请求，构建树形结构
                # id_mapping: 原场景中的请求ID -> 新创建的请求ID
                id_mapping = {}

                def process_suite_request(suite_request, parent_id, current_order):
                    nonlocal added_count, existing_count, total_requests

                    # 检查是否已处理过此请求
                    if suite_request.id in id_mapping:
                        return current_order

                    api_request = suite_request.request

                    # 如果是分组节点（没有关联request或者是group类型）
                    if not api_request or suite_request.step_type == 'group':
                        # 创建分组节点
                        new_group = TestSuiteRequest.objects.create(
                            test_suite=test_suite,
                            request=None,
                            order=current_order,
                            enabled=True,
                            step_type='group',
                            override_name=suite_request.override_name or '分组',
                            assertions=[],
                            extracted_variables={},
                            parent_id=parent_id
                        )
                        id_mapping[suite_request.id] = new_group.id
                        added_count += 1
                        current_order += 1

                        # 处理子节点，使用新创建的分组作为父节点
                        if suite_request.id in children_map:
                            for child in children_map[suite_request.id]:
                                current_order = process_suite_request(child, new_group.id, current_order)

                        return current_order

                    # 使用 get_or_create 避免重复创建
                    new_request, created = TestSuiteRequest.objects.get_or_create(
                        test_suite=test_suite,
                        request=api_request,
                        defaults={
                            'order': current_order,
                            'enabled': True,
                            'step_type': 'request',
                            'override_name': suite_request.override_name or api_request.name,
                            'override_method': suite_request.override_method,
                            'override_url': suite_request.override_url,
                            'override_headers': suite_request.override_headers or {},
                            'override_params': suite_request.override_params or {},
                            'override_body': suite_request.override_body or {},
                            'pre_script': suite_request.pre_script or '',
                            'post_script': suite_request.post_script or '',
                            'assertions': suite_request.assertions or [],
                            'extracted_variables': suite_request.extracted_variables or {},
                            'parent_id': parent_id
                        }
                    )

                    id_mapping[suite_request.id] = new_request.id

                    if created:
                        added_count += 1
                        total_requests += 1
                        current_order += 1

                        # 处理子节点
                        if suite_request.id in children_map:
                            for child in children_map[suite_request.id]:
                                current_order = process_suite_request(child, new_request.id, current_order)
                    else:
                        existing_count += 1

                    return current_order

                # 处理选中的请求
                current_order = base_order + 1
                
                # 如果选择了特定步骤，需要包含它们的父节点以确保层级结构正确
                selected_step_ids = set(source_requests_query.values_list('id', flat=True))
                
                # 收集所有需要处理的请求（包括选中的和它们的祖先）
                requests_to_process = list(source_requests)
                
                # 如果选择了特定步骤，找出所有顶层节点（在选中集合内且父节点不在选中集合内，或父节点为None）
                if selected_steps:
                    selected_ids_set = set(selected_steps)
                    top_level_requests = []
                    for sr in source_requests:
                        # 节点在选中集合内，且（父节点为None 或 父节点不在选中集合内）
                        if sr.id in selected_ids_set and (sr.parent_id is None or sr.parent_id not in selected_ids_set):
                            top_level_requests.append(sr)
                    requests_to_process = top_level_requests
                
                for suite_request in requests_to_process:
                    current_order = process_suite_request(suite_request, group_node.id, current_order)

            # 更新套件的 updated_at 时间戳
            test_suite.save(update_fields=['updated_at'])

            # 返回包含套件数据的响应
            serializer = self.get_serializer(test_suite)

            message = f'成功添加场景，包含 {total_requests} 个请求'
            if existing_count > 0:
                message += f'，{existing_count} 个请求已存在'

            return Response({
                'message': message,
                'added_count': added_count,
                'existing_count': existing_count,
                'suite': serializer.data
            })

        except TestSuite.DoesNotExist:
            return Response({'error': '场景不存在'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='add-wait-step')
    def add_wait_step(self, request, pk=None):
        """添加等待时间步骤到测试套件"""
        test_suite = self.get_object()
        wait_time = request.data.get('wait_time', 1)
        name = request.data.get('name', '等待时间')
        step_number = request.data.get('step_number')

        try:
            # 获取关联的自动化场景
            scenario = None
            if hasattr(test_suite, 'scenario'):
                scenario = test_suite.scenario
            else:
                # 创建新的自动化场景
                from .models import AutomationScenario
                scenario = AutomationScenario.objects.create(
                    name=test_suite.name,
                    description=test_suite.description,
                    project=test_suite.project,
                    environment=test_suite.environment,
                    legacy_test_suite=test_suite,
                    created_by=request.user
                )

            # 创建 TestSuiteRequest
            current_order = TestSuiteRequest.objects.filter(test_suite=test_suite).count()
            suite_request = TestSuiteRequest.objects.create(
                test_suite=test_suite,
                request=None,
                order=current_order,
                enabled=True,
                step_type='wait',
                override_name=name,
                assertions=[],
                extracted_variables={}
            )

            # 创建关联的 ScenarioStep
            from .models import ScenarioStep
            # 获取当前场景下最大的步骤编号
            existing_steps = ScenarioStep.objects.filter(scenario=scenario).values_list('step_number', flat=True)
            next_step = max(existing_steps, default=0) + 1
            # 使用传入的 step_number 或自动计算的 next_step
            final_step_number = step_number if step_number and step_number > 0 else next_step
            # 如果传入的 step_number 已存在，使用自动计算的
            if final_step_number in existing_steps:
                final_step_number = next_step

            scenario_step = ScenarioStep.objects.create(
                scenario=scenario,
                step_type='wait',
                step_number=final_step_number,
                name=name,
                api_request=None,
                override_enabled=True,
                override_name=name,
                control_config={'wait_time': wait_time},
                order=current_order,
                legacy_suite_request=suite_request
            )

            # 更新套件的 updated_at 时间戳
            test_suite.save(update_fields=['updated_at'])

            serializer = self.get_serializer(test_suite)
            return Response({
                'message': '等待时间步骤添加成功',
                'suite': serializer.data
            })

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        """获取测试套件的评审记录"""
        test_suite = self.get_object()
        records = test_suite.review_records.all().select_related('reviewer')
        serializer = TestSuiteReviewRecordSerializer(records, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """提交评审意见"""
        test_suite = self.get_object()
        user = request.user

        status = request.data.get('status')
        comment = request.data.get('comment', '')

        if status not in ['approved', 'rejected']:
            return Response(
                {'error': '状态必须是 approved 或 rejected'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 更新或创建评审记录
        record, created = TestSuiteReviewRecord.objects.update_or_create(
            test_suite=test_suite,
            reviewer=user,
            defaults={
                'status': status,
                'comment': comment,
                'reviewed_at': timezone.now()
            }
        )

        serializer = TestSuiteReviewRecordSerializer(record)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def review_summary(self, request, pk=None):
        """获取评审摘要信息"""
        test_suite = self.get_object()
        records = test_suite.review_records.all()

        total = records.count()
        approved = records.filter(status='approved').count()
        rejected = records.filter(status='rejected').count()
        pending = records.filter(status='pending').count()

        # 确定整体状态
        if rejected > 0:
            overall_status = 'rejected'
        elif total > 0 and approved == total:
            overall_status = 'approved'
        elif total > 0:
            overall_status = 'partial'
        else:
            overall_status = 'pending'

        return Response({
            'test_suite_id': test_suite.id,
            'test_suite_name': test_suite.name,
            'overall_status': overall_status,
            'total': total,
            'approved': approved,
            'rejected': rejected,
            'pending': pending,
            'records': TestSuiteReviewRecordSerializer(records.select_related('reviewer'), many=True).data
        })

    @action(detail=True, methods=['post'])
    def reset_reviews(self, request, pk=None):
        """重置评审状态 - 只有创建人可以重置"""
        test_suite = self.get_object()
        user = request.user

        # 检查权限：只有创建人可以重置评审
        if test_suite.created_by != user:
            return Response(
                {'error': '只有创建人可以重置评审状态'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 删除所有评审记录
        test_suite.review_records.all().delete()

        return Response({
            'message': '评审状态已重置',
            'test_suite_id': test_suite.id,
            'test_suite_name': test_suite.name
        })


class TestSuiteRequestViewSet(viewsets.ModelViewSet):
    queryset = TestSuiteRequest.objects.all()
    serializer_class = TestSuiteRequestSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['test_suite', 'enabled']
    
    def get_queryset(self):
        # 返回所有测试套件请求，不进行权限过滤
        return TestSuiteRequest.objects.all()
    
    def _update_suite_timestamp(self, test_suite):
        """更新套件的 updated_at 时间戳"""
        if test_suite:
            test_suite.save(update_fields=['updated_at'])
    
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        # 更新关联套件的 updated_at
        instance = self.get_object()
        self._update_suite_timestamp(instance.test_suite)
        return response
    
    def partial_update(self, request, *args, **kwargs):
        # 调试日志
        print(f"DEBUG - partial_update called with data: {request.data}")
        
        # 处理 assertions 中的字符串 'null' 转换为真正的 None
        if 'assertions' in request.data:
            import copy
            assertions = copy.deepcopy(request.data['assertions'])
            if isinstance(assertions, list):
                for assertion in assertions:
                    if isinstance(assertion, dict):
                        expected = assertion.get('expected')
                        expected_value = assertion.get('expected_value')
                        # 处理字符串 'null' 转换为 None
                        if expected == 'null' or expected == 'NULL':
                            assertion['expected'] = None
                        if expected_value == 'null' or expected_value == 'NULL':
                            assertion['expected_value'] = None
            # 修改后的数据重新赋值
            request.data['assertions'] = assertions
        
        response = super().partial_update(request, *args, **kwargs)
        # 更新关联套件的 updated_at
        instance = self.get_object()
        print(f"DEBUG - after update, instance order={instance.order}, parent_id={instance.parent_id}")
        self._update_suite_timestamp(instance.test_suite)
        return response
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        test_suite = instance.test_suite
        response = super().destroy(request, *args, **kwargs)
        # 更新关联套件的 updated_at
        self._update_suite_timestamp(test_suite)
        return response
    
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        # 更新关联套件的 updated_at
        test_suite_id = request.data.get('test_suite')
        if test_suite_id:
            try:
                test_suite = TestSuite.objects.get(id=test_suite_id)
                self._update_suite_timestamp(test_suite)
            except TestSuite.DoesNotExist:
                pass
        return response


class TestExecutionViewSet(viewsets.ModelViewSet):
    queryset = TestExecution.objects.all()
    serializer_class = TestExecutionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['status', 'test_suite']
    search_fields = ['test_suite__name']
    ordering = ['-created_at']
    pagination_class = StandardPagination
    
    def get_queryset(self):
        # 返回所有测试执行记录，不进行权限过滤
        return TestExecution.objects.all()
    
    def destroy(self, request, *args, **kwargs):
        """删除测试执行记录"""
        instance = self.get_object()
        test_suite = instance.test_suite
        
        # 执行删除
        response = super().destroy(request, *args, **kwargs)
        
        # 更新关联套件的 updated_at
        if test_suite:
            test_suite.updated_at = timezone.now()
            test_suite.save(update_fields=['updated_at'])
        
        return response

    def _generate_report_for_execution(self, execution):
        """为指定的 TestExecution 生成报告（供内部调用）"""
        try:
            # 创建报告目录
            results_dir = os.path.join(settings.MEDIA_ROOT, 'api-testing', 'allure-results', f'execution_{execution.id}')
            os.makedirs(results_dir, exist_ok=True)

            # 生成测试结果文件
            self._generate_test_result_files(execution, results_dir)

            # 生成Allure报告
            report_output_dir = os.path.join(settings.MEDIA_ROOT, 'api-testing', 'allure-reports', f'execution_{execution.id}')
            os.makedirs(report_output_dir, exist_ok=True)

            # 使用Allure命令行工具生成完整报告
            import subprocess
            import shutil
            import time
            from pathlib import Path

            # 检查 Java 环境
            java_available = self._check_java_environment()
            if not java_available:
                logger.warning("Java 环境未配置，将使用简单报告")

            # Allure命令行工具路径 - 使用相对路径
            base_dir = Path(__file__).resolve().parent.parent.parent

            # 根据操作系统确定可执行文件名
            if os.name == 'nt':
                allure_executable = 'allure.bat'
            else:
                allure_executable = 'allure'

            allure_cmd = base_dir / 'allure' / 'bin' / allure_executable

            if not allure_cmd.exists():
                logger.warning(f"Allure command not found at: {allure_cmd}, trying system paths")
                # 尝试其他可能的路径
                possible_paths = [
                    Path('/usr/local/bin/allure'),  # 系统安装的allure
                    Path('/usr/bin/allure'),  # 系统安装的allure
                ]
                allure_cmd = None
                for path in possible_paths:
                    if path.exists():
                        allure_cmd = path
                        break

            # 确保所有目录存在
            os.makedirs(results_dir, exist_ok=True)

            if allure_cmd and java_available:
                try:
                    for _ in range(3):  # 重试机制
                        try:
                            # 如果目录已存在，先清理（处理权限问题）
                            if os.path.exists(report_output_dir):
                                try:
                                    shutil.rmtree(report_output_dir)
                                except PermissionError as pe:
                                    logger.warning(f"无法删除目录（权限不足）：{report_output_dir}，尝试清理内容")
                                    # 尝试只删除内容，保留目录
                                    for item in os.listdir(report_output_dir):
                                        item_path = os.path.join(report_output_dir, item)
                                        try:
                                            if os.path.isdir(item_path):
                                                shutil.rmtree(item_path)
                                            else:
                                                os.remove(item_path)
                                        except Exception:
                                            pass  # 跳过无法删除的文件

                            # 构建命令行参数（路径统一使用字符串格式）
                            if os.name == 'nt':
                                # Windows 下通过 cmd /c 执行批处理文件
                                cmd_list = [
                                    'cmd', '/c',
                                    str(allure_cmd),
                                    'generate',
                                    str(Path(results_dir)),
                                    '--clean',
                                    '--output', str(Path(report_output_dir))
                                ]
                            else:
                                # Linux/Mac 直接执行
                                cmd_list = [
                                    str(allure_cmd),
                                    'generate',
                                    str(Path(results_dir)),
                                    '--clean',
                                    '--output', str(Path(report_output_dir))
                                ]

                            # 生成Allure报告
                            result = subprocess.run(
                                cmd_list,
                                check=True,
                                capture_output=True,
                                text=True,
                                timeout=30
                            )
                            logger.info(f"Allure 报告生成成功: {result.stdout}")
                            break
                        except subprocess.TimeoutExpired:
                            if _ == 2:  # 最后一次尝试
                                raise
                            logger.warning(f"Allure 命令超时，第 {_ + 1} 次重试...")
                            time.sleep(1)
                            continue
                except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
                    # 如果Allure命令失败，记录详细错误信息
                    error_detail = str(e)
                    if hasattr(e, 'stderr') and e.stderr:
                        error_detail = f"{error_detail}\nStderr: {e.stderr}"
                    logger.error(f"Allure 命令执行失败: {error_detail}")

                    # 不再使用回退方案，直接返回错误
                    return {'error': 'Allure 报告生成失败', 'detail': error_detail}
            else:
                # 如果没有 Allure 工具或 Java 环境，生成简单的 HTML 报告
                logger.warning("Allure 工具或 Java 环境不可用，生成简单报告")
                os.makedirs(report_output_dir, exist_ok=True)
                fallback_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>测试报告 - {execution.test_suite.name}</title>
    <link rel="icon" type="image/png" href="/favicon.png">
</head>
<body>
    <h1>测试报告</h1>
    <p>测试套件: {execution.test_suite.name}</p>
    <p>状态: {execution.get_status_display()}</p>
    <p>总请求数: {execution.total_requests}</p>
    <p>通过: {execution.passed_requests}</p>
    <p>失败: {execution.failed_requests}</p>
</body>
</html>"""
                with open(os.path.join(report_output_dir, 'index.html'), 'w', encoding='utf-8') as f:
                    f.write(fallback_html)

            # 计算执行时长和通过率
            total = execution.total_requests or 0
            passed = execution.passed_requests or 0
            failed = execution.failed_requests or 0
            pass_rate = (passed / total * 100) if total > 0 else 0

            # 计算执行时长
            duration_str = "N/A"
            if execution.start_time and execution.end_time:
                duration = (execution.end_time - execution.start_time).total_seconds()
                if duration < 60:
                    duration_str = f"{duration:.1f}秒"
                else:
                    duration_str = f"{duration/60:.1f}分钟"

            # 安全获取测试套件和项目信息
            test_suite_name = execution.test_suite.name if execution.test_suite else "未知套件"
            project_name = execution.test_suite.project.name if execution.test_suite and execution.test_suite.project else "未知项目"

            # 创建自定义的summary.html页面作为报告概览
            status_class = "status-passed" if execution.status == "COMPLETED" else "status-failed"
            status_icon = "✓" if execution.status == "COMPLETED" else "✗"
            status_color = "#10b981" if execution.status == "COMPLETED" else "#ef4444"

            index_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>测试报告 - {test_suite_name}</title>
    <link rel="icon" type="image/png" href="/favicon.png">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f8fafc;
            color: #1e293b;
            line-height: 1.6;
        }}

        /* Header */
        .header {{
            background: #fff;
            border-bottom: 1px solid #e2e8f0;
            padding: 0;
        }}

        .header-top {{
            max-width: 1280px;
            margin: 0 auto;
            padding: 20px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .header-brand {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .header-brand h1 {{
            font-size: 20px;
            font-weight: 600;
            color: #1e293b;
        }}

        .header-meta {{
            display: flex;
            align-items: center;
            gap: 24px;
            font-size: 13px;
            color: #64748b;
        }}

        .header-meta span {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .allure-btn {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            background: #7c3aed;
            color: #fff;
            text-decoration: none;
            border: none;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            font-family: inherit;
        }}

        .allure-btn:hover {{
            background: #6d28d9;
            transform: translateY(-1px);
        }}

        .allure-btn:disabled {{
            background: #a78bfa;
            cursor: not-allowed;
            transform: none;
        }}

        /* Main Content */
        .container {{
            max-width: 1280px;
            margin: 0 auto;
            padding: 24px;
        }}

        /* Status Banner */
        .status-banner {{
            background: #fff;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            border: 1px solid #e2e8f0;
            display: flex;
            align-items: center;
            gap: 20px;
        }}

        .status-icon {{
            width: 56px;
            height: 56px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            flex-shrink: 0;
        }}

        .status-icon.success {{
            background: #dcfce7;
            color: #16a34a;
        }}

        .status-icon.failed {{
            background: #fee2e2;
            color: #dc2626;
        }}

        .status-info {{
            flex: 1;
        }}

        .status-info h2 {{
            font-size: 24px;
            font-weight: 600;
            color: #1e293b;
            margin-bottom: 6px;
        }}

        .status-info p {{
            color: #64748b;
            font-size: 14px;
        }}

        .status-badge {{
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
        }}

        .status-badge.success {{
            background: #dcfce7;
            color: #16a34a;
        }}

        .status-badge.failed {{
            background: #fee2e2;
            color: #dc2626;
        }}

        /* Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 24px;
        }}

        .stat-card {{
            background: #fff;
            border-radius: 12px;
            padding: 24px;
            border: 1px solid #e2e8f0;
        }}

        .stat-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}

        .stat-label {{
            font-size: 14px;
            color: #64748b;
            font-weight: 500;
        }}

        .stat-icon {{
            width: 32px;
            height: 32px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
        }}

        .stat-icon.total {{ background: #eff6ff; }}
        .stat-icon.passed {{ background: #dcfce7; }}
        .stat-icon.failed {{ background: #fee2e2; }}
        .stat-icon.duration {{ background: #f3f0ff; }}

        .stat-value {{
            font-size: 36px;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 4px;
        }}

        .stat-sublabel {{
            font-size: 13px;
            color: #94a3b8;
        }}

        /* Progress Section */
        .progress-section {{
            background: #fff;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            border: 1px solid #e2e8f0;
        }}

        .progress-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }}

        .progress-title {{
            font-size: 16px;
            font-weight: 600;
            color: #1e293b;
        }}

        .progress-value {{
            font-size: 18px;
            font-weight: 700;
            color: #16a34a;
        }}

        .progress-bar {{
            height: 10px;
            background: #e2e8f0;
            border-radius: 5px;
            overflow: hidden;
            margin-bottom: 12px;
        }}

        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #22c55e, #16a34a);
            border-radius: 5px;
            transition: width 0.5s ease;
        }}

        .progress-legend {{
            display: flex;
            gap: 20px;
            font-size: 13px;
            color: #64748b;
        }}

        .progress-legend span {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .legend-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }}

        .legend-dot.passed {{ background: #22c55e; }}
        .legend-dot.failed {{ background: #ef4444; }}

        /* Test Results */
        .results-section {{
            background: #fff;
            border-radius: 12px;
            padding: 24px;
            border: 1px solid #e2e8f0;
        }}

        .results-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}

        .results-title {{
            font-size: 18px;
            font-weight: 600;
            color: #1e293b;
        }}

        .results-count {{
            font-size: 14px;
            color: #64748b;
        }}

        .test-list {{
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}

        .test-item {{
            display: flex;
            align-items: flex-start;
            gap: 12px;
            padding: 16px;
            background: #f8fafc;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
        }}

        .test-status {{
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            flex-shrink: 0;
        }}

        .test-status.passed {{
            background: #dcfce7;
            color: #16a34a;
        }}

        .test-status.failed {{
            background: #fee2e2;
            color: #dc2626;
        }}

        .test-content {{
            flex: 1;
        }}

        .test-title-row {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 4px;
        }}

        .method-tag {{
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }}

        .method-tag.get {{ background: #dbeafe; color: #2563eb; }}
        .method-tag.post {{ background: #dcfce7; color: #16a34a; }}
        .method-tag.put {{ background: #fef3c7; color: #d97706; }}
        .method-tag.delete {{ background: #fee2e2; color: #dc2626; }}
        .method-tag.patch {{ background: #f3e8ff; color: #9333ea; }}
        .method-tag.wait {{ background: #fef3c7; color: #d97706; }}

        .test-name {{
            font-weight: 600;
            color: #1e293b;
            font-size: 14px;
        }}

        .test-url {{
            font-size: 13px;
            color: #64748b;
            word-break: break-all;
        }}

        .test-error {{
            margin-top: 8px;
            padding: 8px 12px;
            background: #fee2e2;
            border-radius: 6px;
            font-size: 13px;
            color: #dc2626;
        }}

        /* Empty State */
        .empty-state {{
            text-align: center;
            padding: 60px 20px;
            color: #94a3b8;
        }}

        .empty-state svg {{
            width: 64px;
            height: 64px;
            margin-bottom: 16px;
            opacity: 0.5;
        }}

        /* Footer */
        .footer {{
            text-align: center;
            padding: 40px 20px;
            color: #94a3b8;
            font-size: 13px;
        }}

        /* Responsive */
        @media (max-width: 768px) {{
            .stats-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}

            .header-top {{
                flex-direction: column;
                gap: 16px;
                align-items: flex-start;
            }}

            .status-banner {{
                flex-direction: column;
                text-align: center;
            }}
        }}
    </style>
</head>
<body>
    <header class="header">
        <div class="header-top">
            <div class="header-brand">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" stroke-width="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <path d="M12 6v6l4 2"></path>
                </svg>
                <h1>接口测试报告</h1>
            </div>
            <button onclick="captureReport()" class="allure-btn">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                    <circle cx="8.5" cy="8.5" r="1.5"></circle>
                    <polyline points="21 15 16 10 5 21"></polyline>
                </svg>
                保存报告截图
            </button>
        </div>
    </header>

    <main class="container">
        <!-- Status Banner -->
        <div class="status-banner">
            <div class="status-icon {'success' if execution.status == 'COMPLETED' else 'failed'}">
                {status_icon}
            </div>
            <div class="status-info">
                <h2>{test_suite_name}</h2>
                <p>{project_name} · 执行于 {timezone.localtime(execution.created_at).strftime('%Y-%m-%d %H:%M:%S') if execution.created_at else 'N/A'}</p>
            </div>
            <span class="status-badge {'success' if execution.status == 'COMPLETED' else 'failed'}">
                {execution.get_status_display()}
            </span>
        </div>

        <!-- Stats Grid -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-header">
                    <span class="stat-label">总请求数</span>
                    <div class="stat-icon total">📊</div>
                </div>
                <div class="stat-value">{total}</div>
                <div class="stat-sublabel">个测试用例</div>
            </div>
            <div class="stat-card">
                <div class="stat-header">
                    <span class="stat-label">通过</span>
                    <div class="stat-icon passed">✓</div>
                </div>
                <div class="stat-value" style="color: #16a34a;">{passed}</div>
                <div class="stat-sublabel">成功率 {pass_rate:.1f}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-header">
                    <span class="stat-label">失败</span>
                    <div class="stat-icon failed">✕</div>
                </div>
                <div class="stat-value" style="color: #dc2626;">{failed}</div>
                <div class="stat-sublabel">需要关注</div>
            </div>
            <div class="stat-card">
                <div class="stat-header">
                    <span class="stat-label">执行时长</span>
                    <div class="stat-icon duration">⏱</div>
                </div>
                <div class="stat-value">{duration_str}</div>
                <div class="stat-sublabel">总耗时</div>
            </div>
        </div>

        <!-- Progress Section -->
        <div class="progress-section">
            <div class="progress-header">
                <span class="progress-title">测试通过率</span>
                <span class="progress-value">{pass_rate:.1f}%</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {pass_rate}%"></div>
            </div>
            <div class="progress-legend">
                <span><span class="legend-dot passed"></span> 通过 {passed}</span>
                <span><span class="legend-dot failed"></span> 失败 {failed}</span>
            </div>
        </div>

        <!-- Test Results -->
        <div class="results-section">
            <div class="results-header">
                <span class="results-title">测试结果详情</span>
                <span class="results-count">共 {total} 个请求</span>
            </div>
            <div class="test-list">
"""

            # 添加测试详情
            if execution.results:
                for i, result in enumerate(execution.results):
                    is_passed = result.get('passed', False)
                    status_mark = "✓" if is_passed else "✗"
                    method = result.get('method', 'GET').upper()
                    method_class = method.lower()
                    error_html = f'''<div class="test-error"><strong>错误:</strong> {result.get("error", "")}</div>''' if result.get('error') else ""

                    index_content += f"""                <div class="test-item">
                    <div class="test-status {'passed' if is_passed else 'failed'}">{status_mark}</div>
                    <div class="test-content">
                        <div class="test-title-row">
                            <span class="method-tag {method_class}">{method}</span>
                            <span class="test-name">{result.get('name', f'测试请求 {i+1}')}</span>
                        </div>
                        <div class="test-url">{result.get('url', '')}</div>
                        {error_html}
                    </div>
                </div>
"""
            else:
                index_content += """                <div class="empty-state">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                    </svg>
                    <p>暂无测试详情数据</p>
                </div>
"""

            index_content += f"""            </div>
        </div>

        <footer class="footer">
            <p>报告生成时间: {timezone.localtime(execution.created_at).strftime('%Y-%m-%d %H:%M:%S') if execution.created_at else 'N/A'} · 由 TestHub 生成</p>
        </footer>
    </main>

    <script>
        function captureReport() {{
            const btn = document.querySelector('.allure-btn');
            const originalText = btn.innerHTML;
            btn.innerHTML = '<span>生成中...</span>';
            btn.disabled = true;

            // 临时隐藏按钮以获得干净的截图
            btn.style.display = 'none';

            html2canvas(document.body, {{
                scale: 2, // 高清截图，2倍分辨率
                useCORS: true,
                allowTaint: true,
                backgroundColor: '#f8fafc',
                logging: false,
                windowWidth: document.documentElement.scrollWidth,
                windowHeight: document.documentElement.scrollHeight
            }}).then(canvas => {{
                // 恢复按钮
                btn.style.display = 'inline-flex';
                btn.innerHTML = originalText;
                btn.disabled = false;

                // 下载图片
                const link = document.createElement('a');
                const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
                link.download = '测试报告_' + '{test_suite_name}'.replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, '_') + '_' + timestamp + '.png';
                link.href = canvas.toDataURL('image/png');
                link.click();
            }}).catch(err => {{
                console.error('截图失败:', err);
                btn.style.display = 'inline-flex';
                btn.innerHTML = originalText;
                btn.disabled = false;
                alert('截图失败，请重试');
            }});
        }}
    </script>
</body>
</html>
"""
            # 保存为summary.html，避免覆盖Allure生成的index.html
            summary_file = os.path.join(report_output_dir, 'summary.html')
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(index_content)

            # 生成报告截图
            screenshot_url = None
            try:
                screenshot_url = self._generate_report_screenshot(execution.id, report_output_dir)
                logger.info(f"报告截图生成成功: {screenshot_url}")
            except Exception as e:
                logger.error(f"生成报告截图失败: {str(e)}", exc_info=True)
                # 截图失败不影响报告生成

            return {
                'success': True,
                'report_url': f'/api-testing/allure-reports/execution_{execution.id}/summary.html',
                'screenshot_url': screenshot_url
            }

        except Exception as e:
            import traceback
            error_detail = str(e)
            error_traceback = traceback.format_exc()
            logger.error(f"生成报告失败: {error_detail}\n{error_traceback}")
            return {'error': error_detail, 'detail': error_traceback}

    @action(detail=True, methods=['post'], url_path='generate-allure-report')
    def generate_allure_report(self, request, pk=None):
        """生成Allure报告数据（API接口）"""
        execution = self.get_object()

        result = self._generate_report_for_execution(execution)

        if 'error' in result:
            return Response({
                'error': result['error'],
                'detail': result.get('detail', '')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'message': 'Allure报告生成成功',
            'report_url': result['report_url'],
            'screenshot_url': result.get('screenshot_url')
        })

        try:
            # 创建报告目录
            results_dir = os.path.join(settings.MEDIA_ROOT, 'api-testing', 'allure-results', f'execution_{execution.id}')
            os.makedirs(results_dir, exist_ok=True)
            
            # 生成测试结果文件
            self._generate_test_result_files(execution, results_dir)
            
            # 生成Allure报告
            report_output_dir = os.path.join(settings.MEDIA_ROOT, 'api-testing', 'allure-reports', f'execution_{execution.id}')
            os.makedirs(report_output_dir, exist_ok=True)
            
            # 使用Allure命令行工具生成完整报告
            import subprocess
            import shutil
            import time
            from pathlib import Path
            
            # 检查 Java 环境
            java_available = self._check_java_environment()
            if not java_available:
                logger.warning("Java 环境未配置，将使用简单报告")
            
            # Allure命令行工具路径 - 使用相对路径
            base_dir = Path(__file__).resolve().parent.parent.parent
            
            # 根据操作系统确定可执行文件名
            if os.name == 'nt':
                allure_executable = 'allure.bat'
            else:
                allure_executable = 'allure'
                
            allure_cmd = base_dir / 'allure' / 'bin' / allure_executable

            if not allure_cmd.exists():
                logger.warning(f"Allure command not found at: {allure_cmd}, trying system paths")
                # 尝试其他可能的路径
                possible_paths = [
                    Path('/usr/local/bin/allure'),  # 系统安装的allure
                    Path('/usr/bin/allure'),  # 系统安装的allure
                ]
                allure_cmd = None
                for path in possible_paths:
                    if path.exists():
                        allure_cmd = path
                        break
            
            # 确保所有目录存在
            os.makedirs(results_dir, exist_ok=True)
            
            if allure_cmd and java_available:
                try:
                    for _ in range(3):  # 重试机制
                        try:
                            # 如果目录已存在，先清理（处理权限问题）
                            if os.path.exists(report_output_dir):
                                try:
                                    shutil.rmtree(report_output_dir)
                                except PermissionError as pe:
                                    logger.warning(f"无法删除目录（权限不足）：{report_output_dir}，尝试清理内容")
                                    # 尝试只删除内容，保留目录
                                    for item in os.listdir(report_output_dir):
                                        item_path = os.path.join(report_output_dir, item)
                                        try:
                                            if os.path.isdir(item_path):
                                                shutil.rmtree(item_path)
                                            else:
                                                os.remove(item_path)
                                        except Exception:
                                            pass  # 跳过无法删除的文件
                            
                            # 构建命令行参数（路径统一使用字符串格式）
                            if os.name == 'nt':
                                # Windows 下通过 cmd /c 执行批处理文件
                                cmd_list = [
                                    'cmd', '/c',
                                    str(allure_cmd),
                                    'generate',
                                    str(Path(results_dir)),
                                    '--clean',
                                    '--output', str(Path(report_output_dir))
                                ]
                            else:
                                # Linux/Mac 直接执行
                                cmd_list = [
                                    str(allure_cmd),
                                    'generate',
                                    str(Path(results_dir)),
                                    '--clean',
                                    '--output', str(Path(report_output_dir))
                                ]
                            
                            # 生成Allure报告
                            result = subprocess.run(
                                cmd_list,
                                check=True,
                                capture_output=True,
                                text=True,
                                timeout=30
                            )
                            logger.info(f"Allure 报告生成成功: {result.stdout}")
                            break
                        except subprocess.TimeoutExpired:
                            if _ == 2:  # 最后一次尝试
                                raise
                            logger.warning(f"Allure 命令超时，第 {_ + 1} 次重试...")
                            time.sleep(1)
                            continue
                except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
                    # 如果Allure命令失败，记录详细错误信息
                    error_detail = str(e)
                    if hasattr(e, 'stderr') and e.stderr:
                        error_detail = f"{error_detail}\nStderr: {e.stderr}"
                    logger.error(f"Allure 命令执行失败: {error_detail}")
                    
                    # 不再使用回退方案，直接返回错误
                    return Response({
                        'error': 'Allure 报告生成失败',
                        'detail': error_detail,
                        'suggestion': (
                            '请检查以下项目：\n'
                            '1. Java 是否已安装并配置（JAVA_HOME 或 java 命令可用）\n'
                            '2. Allure 工具是否完整（项目根目录 allure/bin/ 目录）\n'
                            '3. 目录权限是否正确\n'
                            '4. 查看后端日志获取详细错误信息'
                        )
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                # 如果没有 Allure 工具或 Java 环境，生成简单的 HTML 报告
                logger.warning("Allure 工具或 Java 环境不可用，生成简单报告")
                os.makedirs(report_output_dir, exist_ok=True)
                fallback_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>测试报告 - {execution.test_suite.name}</title>
    <link rel="icon" type="image/png" href="/favicon.png">
</head>
<body>
    <h1>测试报告</h1>
    <p>测试套件: {execution.test_suite.name}</p>
    <p>状态: {execution.get_status_display()}</p>
    <p>总请求数: {execution.total_requests}</p>
    <p>通过: {execution.passed_requests}</p>
    <p>失败: {execution.failed_requests}</p>
</body>
</html>"""
                with open(os.path.join(report_output_dir, 'index.html'), 'w', encoding='utf-8') as f:
                    f.write(fallback_html)
            
            # 计算执行时长和通过率
            total = execution.total_requests or 0
            passed = execution.passed_requests or 0
            failed = execution.failed_requests or 0
            pass_rate = (passed / total * 100) if total > 0 else 0
            
            # 计算执行时长
            duration_str = "N/A"
            if execution.start_time and execution.end_time:
                duration = (execution.end_time - execution.start_time).total_seconds()
                if duration < 60:
                    duration_str = f"{duration:.1f}秒"
                else:
                    duration_str = f"{duration/60:.1f}分钟"
            
            # 安全获取测试套件和项目信息
            test_suite_name = execution.test_suite.name if execution.test_suite else "未知套件"
            project_name = execution.test_suite.project.name if execution.test_suite and execution.test_suite.project else "未知项目"
            
            # 创建自定义的summary.html页面作为报告概览
            status_class = "status-passed" if execution.status == "COMPLETED" else "status-failed"
            status_icon = "✓" if execution.status == "COMPLETED" else "✗"
            status_color = "#10b981" if execution.status == "COMPLETED" else "#ef4444"
            
            index_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>测试报告 - {test_suite_name}</title>
    <link rel="icon" type="image/png" href="/favicon.png">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f8fafc;
            color: #1e293b;
            line-height: 1.6;
        }}
        
        /* Header */
        .header {{
            background: #fff;
            border-bottom: 1px solid #e2e8f0;
            padding: 0;
        }}
        
        .header-top {{
            max-width: 1280px;
            margin: 0 auto;
            padding: 20px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .header-brand {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .header-brand h1 {{
            font-size: 20px;
            font-weight: 600;
            color: #1e293b;
        }}
        
        .header-meta {{
            display: flex;
            align-items: center;
            gap: 24px;
            font-size: 13px;
            color: #64748b;
        }}
        
        .header-meta span {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        
        .allure-btn {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            background: #7c3aed;
            color: #fff;
            text-decoration: none;
            border: none;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            font-family: inherit;
        }}
        
        .allure-btn:hover {{
            background: #6d28d9;
            transform: translateY(-1px);
        }}
        
        .allure-btn:disabled {{
            background: #a78bfa;
            cursor: not-allowed;
            transform: none;
        }}
        
        /* Main Content */
        .container {{
            max-width: 1280px;
            margin: 0 auto;
            padding: 24px;
        }}
        
        /* Status Banner */
        .status-banner {{
            background: #fff;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            border: 1px solid #e2e8f0;
            display: flex;
            align-items: center;
            gap: 20px;
        }}
        
        .status-icon {{
            width: 56px;
            height: 56px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            flex-shrink: 0;
        }}
        
        .status-icon.success {{
            background: #dcfce7;
            color: #16a34a;
        }}
        
        .status-icon.failed {{
            background: #fee2e2;
            color: #dc2626;
        }}
        
        .status-info {{
            flex: 1;
        }}
        
        .status-info h2 {{
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 4px;
        }}
        
        .status-info p {{
            color: #64748b;
            font-size: 14px;
        }}
        
        .status-badge {{
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 500;
        }}
        
        .status-badge.success {{
            background: #dcfce7;
            color: #166534;
        }}
        
        .status-badge.failed {{
            background: #fee2e2;
            color: #991b1b;
        }}
        
        /* Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }}
        
        @media (max-width: 1024px) {{
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
        }}
        
        @media (max-width: 640px) {{
            .stats-grid {{ grid-template-columns: 1fr; }}
        }}
        
        .stat-card {{
            background: #fff;
            border-radius: 10px;
            padding: 20px;
            border: 1px solid #e2e8f0;
        }}
        
        .stat-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 12px;
        }}
        
        .stat-label {{
            font-size: 13px;
            color: #64748b;
            font-weight: 500;
        }}
        
        .stat-icon {{
            width: 32px;
            height: 32px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
        }}
        
        .stat-icon.total {{ background: #eff6ff; color: #2563eb; }}
        .stat-icon.passed {{ background: #f0fdf4; color: #16a34a; }}
        .stat-icon.failed {{ background: #fef2f2; color: #dc2626; }}
        .stat-icon.rate {{ background: #f5f3ff; color: #7c3aed; }}
        .stat-icon.time {{ background: #f0f9ff; color: #0891b2; }}
        
        .stat-value {{
            font-size: 28px;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 4px;
        }}
        
        .stat-sublabel {{
            font-size: 12px;
            color: #94a3b8;
        }}
        
        /* Progress Bar */
        .progress-section {{
            background: #fff;
            border-radius: 10px;
            padding: 20px;
            border: 1px solid #e2e8f0;
            margin-bottom: 24px;
        }}
        
        .progress-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}
        
        .progress-title {{
            font-size: 14px;
            font-weight: 600;
            color: #374151;
        }}
        
        .progress-value {{
            font-size: 14px;
            font-weight: 600;
            color: #16a34a;
        }}
        
        .progress-bar {{
            height: 8px;
            background: #e2e8f0;
            border-radius: 4px;
            overflow: hidden;
        }}
        
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #22c55e 0%, #16a34a 100%);
            border-radius: 4px;
            transition: width 0.5s ease;
        }}
        
        .progress-legend {{
            display: flex;
            gap: 24px;
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid #f1f5f9;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            color: #64748b;
        }}
        
        .legend-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }}
        
        .legend-dot.passed {{ background: #22c55e; }}
        .legend-dot.failed {{ background: #ef4444; }}
        
        /* Test Results */
        .results-section {{
            background: #fff;
            border-radius: 10px;
            border: 1px solid #e2e8f0;
            overflow: hidden;
        }}
        
        .results-header {{
            padding: 20px 24px;
            border-bottom: 1px solid #e2e8f0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .results-header h3 {{
            font-size: 16px;
            font-weight: 600;
        }}
        
        .results-count {{
            font-size: 13px;
            color: #64748b;
        }}
        
        .test-list {{
            max-height: 600px;
            overflow-y: auto;
        }}
        
        .test-item {{
            padding: 16px 24px;
            border-bottom: 1px solid #f1f5f9;
            display: flex;
            align-items: flex-start;
            gap: 16px;
            transition: background 0.2s;
        }}
        
        .test-item:hover {{
            background: #f8fafc;
        }}
        
        .test-item:last-child {{
            border-bottom: none;
        }}
        
        .test-status {{
            width: 20px;
            height: 20px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            flex-shrink: 0;
            margin-top: 2px;
        }}
        
        .test-status.passed {{
            background: #dcfce7;
            color: #16a34a;
        }}
        
        .test-status.failed {{
            background: #fee2e2;
            color: #dc2626;
        }}
        
        .test-content {{
            flex: 1;
            min-width: 0;
        }}
        
        .test-title-row {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 6px;
        }}
        
        .test-name {{
            font-weight: 600;
            font-size: 14px;
            color: #1e293b;
        }}
        
        .method-tag {{
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        .method-tag.get {{ background: #dbeafe; color: #1d4ed8; }}
        .method-tag.post {{ background: #dcfce7; color: #15803d; }}
        .method-tag.put {{ background: #ffedd5; color: #9a3412; }}
        .method-tag.delete {{ background: #fee2e2; color: #b91c1c; }}
        .method-tag.patch {{ background: #f3e8ff; color: #7c3aed; }}
        .method-tag.wait {{ background: #ffedd5; color: #9a3412; }}
        
        .test-url {{
            font-size: 13px;
            color: #64748b;
            font-family: 'Monaco', 'Menlo', monospace;
            word-break: break-all;
        }}
        
        .test-error {{
            margin-top: 8px;
            padding: 10px 12px;
            background: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 6px;
            font-size: 12px;
            color: #991b1b;
        }}
        
        .test-error strong {{
            color: #dc2626;
        }}
        
        /* Empty State */
        .empty-state {{
            padding: 60px 24px;
            text-align: center;
            color: #94a3b8;
        }}
        
        .empty-state svg {{
            width: 48px;
            height: 48px;
            margin-bottom: 16px;
            opacity: 0.5;
        }}
        
        /* Footer */
        .footer {{
            margin-top: 32px;
            padding: 20px;
            text-align: center;
            color: #94a3b8;
            font-size: 12px;
            border-top: 1px solid #e2e8f0;
        }}
        
        /* Scrollbar */
        .test-list::-webkit-scrollbar {{
            width: 6px;
        }}
        
        .test-list::-webkit-scrollbar-track {{
            background: #f1f5f9;
        }}
        
        .test-list::-webkit-scrollbar-thumb {{
            background: #cbd5e1;
            border-radius: 3px;
        }}
        
        .test-list::-webkit-scrollbar-thumb:hover {{
            background: #94a3b8;
        }}
    </style>
</head>
<body>
    <header class="header">
        <div class="header-top">
            <div class="header-brand">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect width="24" height="24" rx="6" fill="#7c3aed"/>
                    <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <h1>接口测试报告</h1>
            </div>
            <button onclick="captureReport()" class="allure-btn">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                    <circle cx="8.5" cy="8.5" r="1.5"></circle>
                    <polyline points="21 15 16 10 5 21"></polyline>
                </svg>
                保存报告截图
            </button>
        </div>
    </header>
    
    <main class="container">
        <!-- Status Banner -->
        <div class="status-banner">
            <div class="status-icon {'success' if execution.status == 'COMPLETED' else 'failed'}">
                {status_icon}
            </div>
            <div class="status-info">
                <h2>{test_suite_name}</h2>
                <p>{project_name} · 执行于 {timezone.localtime(execution.created_at).strftime('%Y-%m-%d %H:%M:%S') if execution.created_at else 'N/A'}</p>
            </div>
            <span class="status-badge {'success' if execution.status == 'COMPLETED' else 'failed'}">
                {execution.get_status_display()}
            </span>
        </div>
        
        <!-- Stats Grid -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-header">
                    <span class="stat-label">总请求数</span>
                    <div class="stat-icon total">📊</div>
                </div>
                <div class="stat-value">{total}</div>
                <div class="stat-sublabel">个测试用例</div>
            </div>
            <div class="stat-card">
                <div class="stat-header">
                    <span class="stat-label">通过</span>
                    <div class="stat-icon passed">✓</div>
                </div>
                <div class="stat-value" style="color: #16a34a;">{passed}</div>
                <div class="stat-sublabel">成功率 {pass_rate:.1f}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-header">
                    <span class="stat-label">失败</span>
                    <div class="stat-icon failed">✗</div>
                </div>
                <div class="stat-value" style="color: #dc2626;">{failed}</div>
                <div class="stat-sublabel">需要关注</div>
            </div>
            <div class="stat-card">
                <div class="stat-header">
                    <span class="stat-label">执行时长</span>
                    <div class="stat-icon time">⏱</div>
                </div>
                <div class="stat-value">{duration_str}</div>
                <div class="stat-sublabel">总耗时</div>
            </div>
        </div>
        
        <!-- Progress Bar -->
        <div class="progress-section">
            <div class="progress-header">
                <span class="progress-title">测试通过率</span>
                <span class="progress-value">{pass_rate:.1f}%</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {pass_rate}%"></div>
            </div>
            <div class="progress-legend">
                <div class="legend-item">
                    <span class="legend-dot passed"></span>
                    <span>通过 {passed}</span>
                </div>
                <div class="legend-item">
                    <span class="legend-dot failed"></span>
                    <span>失败 {failed}</span>
                </div>
            </div>
        </div>
        
        <!-- Test Results -->
        <div class="results-section">
            <div class="results-header">
                <h3>测试结果详情</h3>
                <span class="results-count">共 {total} 个请求</span>
            </div>
            <div class="test-list">
"""
            
            # 添加测试结果列表
            if execution.results:
                for i, result in enumerate(execution.results):
                    is_passed = result.get('passed', False)
                    status_mark = "✓" if is_passed else "✗"
                    method = result.get('method', 'GET').upper()
                    method_class = method.lower()
                    error_html = f'''<div class="test-error"><strong>错误:</strong> {result.get("error", "")}</div>''' if result.get('error') else ""
                    
                    index_content += f"""                <div class="test-item">
                    <div class="test-status {'passed' if is_passed else 'failed'}">{status_mark}</div>
                    <div class="test-content">
                        <div class="test-title-row">
                            <span class="method-tag {method_class}">{method}</span>
                            <span class="test-name">{result.get('name', f'测试请求 {i+1}')}</span>
                        </div>
                        <div class="test-url">{result.get('url', '')}</div>
                        {error_html}
                    </div>
                </div>
"""
            else:
                index_content += """                <div class="empty-state">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                    </svg>
                    <p>暂无测试详情数据</p>
                </div>
"""
            
            index_content += f"""            </div>
        </div>
        
        <footer class="footer">
            <p>报告生成时间: {timezone.localtime(execution.created_at).strftime('%Y-%m-%d %H:%M:%S') if execution.created_at else 'N/A'} · 由 TestHub 生成</p>
        </footer>
    </main>
    
    <script>
        function captureReport() {{
            const btn = document.querySelector('.allure-btn');
            const originalText = btn.innerHTML;
            btn.innerHTML = '<span>生成中...</span>';
            btn.disabled = true;
            
            // 临时隐藏按钮以获得干净的截图
            btn.style.display = 'none';
            
            html2canvas(document.body, {{
                scale: 2, // 高清截图，2倍分辨率
                useCORS: true,
                allowTaint: true,
                backgroundColor: '#f8fafc',
                logging: false,
                windowWidth: document.documentElement.scrollWidth,
                windowHeight: document.documentElement.scrollHeight
            }}).then(canvas => {{
                // 恢复按钮
                btn.style.display = 'inline-flex';
                btn.innerHTML = originalText;
                btn.disabled = false;
                
                // 下载图片
                const link = document.createElement('a');
                const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
                link.download = '测试报告_' + '{test_suite_name}'.replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, '_') + '_' + timestamp + '.png';
                link.href = canvas.toDataURL('image/png');
                link.click();
            }}).catch(err => {{
                console.error('截图失败:', err);
                btn.style.display = 'inline-flex';
                btn.innerHTML = originalText;
                btn.disabled = false;
                alert('截图失败，请重试');
            }});
        }}
    </script>
</body>
</html>
"""
            # 保存为summary.html，避免覆盖Allure生成的index.html
            summary_file = os.path.join(report_output_dir, 'summary.html')
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(index_content)
            
            # 生成报告截图
            screenshot_url = None
            try:
                screenshot_url = self._generate_report_screenshot(execution.id, report_output_dir)
                logger.info(f"报告截图生成成功: {screenshot_url}")
            except Exception as e:
                logger.error(f"生成报告截图失败: {str(e)}", exc_info=True)
                # 截图失败不影响报告生成
            
            return Response({
                'message': 'Allure报告生成成功',
                'report_url': f'/api-testing/allure-reports/execution_{execution.id}/summary.html',
                'screenshot_url': screenshot_url
            })
        except Exception as e:
            import traceback
            error_detail = str(e)
            error_traceback = traceback.format_exc()
            logger.error(f"生成Allure报告失败: {error_detail}\n{error_traceback}")
            return Response({
                'error': error_detail,
                'detail': error_traceback
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def _check_java_environment(self):
        """检查 Java 运行环境是否可用"""
        try:
            # 首先检查 JAVA_HOME 环境变量
            java_home = os.environ.get('JAVA_HOME')
            if java_home:
                logger.info(f"检测到 JAVA_HOME: {java_home}")

            # 尝试执行 java -version 命令
            result = subprocess.run(
                ['java', '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # Java 可用，记录版本信息
                java_version = result.stderr.split('\n')[0] if result.stderr else 'Unknown'
                logger.info(f"Java 环境可用: {java_version}")
                return True
            else:
                logger.warning(f"Java 命令执行失败: {result.stderr}")
                return False

        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.warning(f"Java 环境检查失败: {str(e)}")
            return False

    def _generate_report_screenshot(self, execution_id, report_output_dir):
        """使用 Playwright 生成报告截图"""
        import asyncio
        from playwright.async_api import async_playwright

        async def _capture_screenshot():
            async with async_playwright() as p:
                # 启动浏览器
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(viewport={'width': 1920, 'height': 1080})

                # 构建报告文件的本地路径
                report_file = os.path.join(report_output_dir, 'summary.html')
                file_url = f'file://{report_file}'

                # 打开报告页面
                await page.goto(file_url, wait_until='networkidle', timeout=30000)

                # 等待页面内容加载完成
                await page.wait_for_selector('.container', timeout=10000)

                # 等待一段时间确保所有内容渲染完成
                await asyncio.sleep(1)

                # 获取页面完整高度
                page_height = await page.evaluate('document.documentElement.scrollHeight')
                await page.set_viewport_size({'width': 1920, 'height': min(page_height, 4000)})

                # 创建截图保存目录
                screenshot_dir = os.path.join(settings.MEDIA_ROOT, 'api-testing', 'report-screenshots')
                os.makedirs(screenshot_dir, exist_ok=True)

                # 截图保存路径
                screenshot_path = os.path.join(screenshot_dir, f'execution_{execution_id}.png')

                # 截取整个页面
                await page.screenshot(path=screenshot_path, full_page=True)

                await browser.close()

                # 返回截图的 URL
                return f'/media/api-testing/report-screenshots/execution_{execution_id}.png'

        return asyncio.run(_capture_screenshot())

    def _generate_test_result_files(self, execution, report_dir):
        """生成测试结果文件"""
        try:
            # 检查execution.results是否存在
            if not execution.results:
                logger.warning(f"执行记录 {execution.id} 没有结果数据")
                return

            # 生成容器文件，定义测试套件
            container_data = {
                "uuid": str(execution.id),
                "name": execution.test_suite.name,
                "children": []
            }

            # 为每个测试请求添加到children列表
            for i, result in enumerate(execution.results):
                container_data["children"].append(f"{execution.id}-{i}")

            # 保存容器文件
            container_file_path = os.path.join(report_dir, f'{execution.id}-container.json')
            with open(container_file_path, 'w', encoding='utf-8') as f:
                json.dump(container_data, f, ensure_ascii=False, indent=2)

            # 只生成每个测试请求的结果文件，不生成测试套件的结果文件
            for i, result in enumerate(execution.results):
                request_result = {
                    "uuid": f"{execution.id}-{i}",
                    "name": result.get('name', f'测试请求 {i+1}'),
                    "status": "passed" if result.get('passed', False) else "failed",
                    "stage": "finished",
                    "start": int(time.time() * 1000) - 1000,  # 模拟开始时间
                    "stop": int(time.time() * 1000),  # 模拟结束时间
                    "description": f"Method: {result.get('method', 'GET')}\nURL: {result.get('url', '')}",
                    "historyId": f"{execution.test_suite.id}-{i}",
                    "fullName": f"{execution.test_suite.name} / {result.get('name', f'请求 {i+1}')}",
                    "links": [],
                    "labels": [
                        {"name": "suite", "value": execution.test_suite.name},
                        {"name": "testClass", "value": execution.test_suite.name},
                        {"name": "package", "value": "api_testing"},
                        {"name": "project", "value": execution.test_suite.project.name}
                    ],
                    "parameters": [
                        {"name": "method", "value": result.get('method', 'GET')},
                        {"name": "url", "value": result.get('url', '')}
                    ],
                    "steps": [
                        {
                            "name": "发送请求",
                            "status": "passed",
                            "stage": "finished",
                            "start": int(time.time() * 1000) - 1000,
                            "stop": int(time.time() * 1000) - 500,
                            "steps": []
                        },
                        {
                            "name": "验证响应",
                            "status": "passed" if result.get('passed', False) else "failed",
                            "stage": "finished",
                            "start": int(time.time() * 1000) - 500,
                            "stop": int(time.time() * 1000),
                            "steps": []
                        }
                    ]
                }
                
                # 添加错误信息（如果有的话）
                if result.get('error'):
                    request_result["statusDetails"] = {
                        "message": result.get('error'),
                        "trace": ""
                    }
                
                # 保存请求结果
                request_file_path = os.path.join(report_dir, f'{execution.id}-{i}-result.json')
                with open(request_file_path, 'w', encoding='utf-8') as f:
                    json.dump(request_result, f, ensure_ascii=False, indent=2)

        except Exception as e:
            import traceback
            logger.error(f"生成测试结果文件失败: {str(e)}\n{traceback.format_exc()}")
            raise


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """用户列表接口，用于项目成员选择"""
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']


class ScheduledTaskViewSet(viewsets.ModelViewSet):
    """定时任务视图集"""
    queryset = ScheduledTask.objects.all()
    serializer_class = ScheduledTaskSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'last_run_time']
    ordering = ['-created_at']
    
    def get_queryset(self):
        # 返回所有定时任务，不进行权限过滤
        return super().get_queryset()
    
    @action(detail=True, methods=['post'])
    def run_now(self, request, pk=None):
        """立即执行定时任务"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info("=== run_now 方法被调用 ===")
        
        task = self.get_object()
        logger.info(f"获取任务对象: {task.id} - {task.name}")

        try:
            # 创建执行日志
            execution_log = TaskExecutionLog.objects.create(
                task=task,
                status='PENDING',
                executed_by=request.user
            )
            logger.info(f"创建执行日志: {execution_log.id}")
            
            # 异步执行任务
            logger.info("调用 _execute_task_async 方法")
            self._execute_task_async(task, execution_log)
            
            logger.info("任务开始执行")
            return Response(
                {'message': '任务已开始执行', 'execution_id': execution_log.id},
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {'error': f'执行任务失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """激活定时任务"""
        task = self.get_object()
        
        if task.status == 'ACTIVE':
            return Response(
                {'error': '任务已经是激活状态'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        task.status = 'ACTIVE'
        task.next_run_time = task.calculate_next_run()
        task.save()
        
        return Response(
            {'message': '任务已激活', 'next_run_time': task.next_run_time},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """暂停定时任务"""
        task = self.get_object()
        
        if task.status == 'PAUSED':
            return Response(
                {'error': '任务已经是暂停状态'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        task.status = 'PAUSED'
        task.next_run_time = None
        task.save()
        
        return Response(
            {'message': '任务已暂停'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['get'])
    def execution_logs(self, request, pk=None):
        """获取任务执行日志"""
        task = self.get_object()

        logs = TaskExecutionLog.objects.filter(task=task).order_by('-created_at')
        page = self.paginate_queryset(logs)
        
        if page is not None:
            serializer = TaskExecutionLogSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = TaskExecutionLogSerializer(logs, many=True)
        return Response(serializer.data)
    
    def _execute_task_async(self, task, execution_log):
        """异步执行任务"""
        import threading
        from datetime import datetime
        
        # 添加测试日志
        import logging
        logger = logging.getLogger(__name__)
        logger.info("=== _execute_task_async 方法被调用 ===")
        
        def execute():
            try:
                # 更新执行状态
                execution_log.status = 'RUNNING'
                execution_log.start_time = timezone.now()
                execution_log.save()
                
                # 执行任务
                if task.task_type == 'TEST_SUITE':
                    result = self._execute_test_suite(task)
                elif task.task_type == 'API_REQUEST':
                    result = self._execute_api_request(task)
                else:
                    raise ValueError(f"未知的任务类型: {task.task_type}")
                
                # 更新执行结果
                execution_log.status = 'COMPLETED'
                execution_log.end_time = timezone.now()
                execution_log.result = result
                execution_log.save()
                
                # 更新任务统计
                task.update_run_stats(success=True)
                task.last_result = result
                task.save()
                
                # 自动生成报告（如果是测试套件类型）
                if task.task_type == 'TEST_SUITE' and result.get('execution_id'):
                    try:
                        from .models import TestExecution
                        test_execution_id = result.get('execution_id')
                        test_execution = TestExecution.objects.get(id=test_execution_id)
                        logger.info(f"开始为 TestExecution {test_execution_id} 自动生成报告...")
                        # 使用 TestExecutionViewSet 实例来生成报告
                        test_execution_viewset = TestExecutionViewSet()
                        report_result = test_execution_viewset._generate_report_for_execution(test_execution)
                        if 'error' in report_result:
                            logger.error(f"自动生成报告失败: {report_result['error']}")
                        else:
                            logger.info(f"自动生成报告成功: {report_result.get('report_url')}")
                            # 将报告链接添加到结果中
                            result['report_url'] = report_result.get('report_url')
                            execution_log.result = result
                            execution_log.save()
                    except Exception as e:
                        logger.error(f"自动生成报告时出错: {str(e)}", exc_info=True)
                
                logger.info("=== 开始检查发送成功通知 ===")
                # 发送通知（如果配置了）
                # 检查任务是否有通知设置
                notification_setting = None
                if hasattr(task, 'notification_settings'):
                    try:
                        notification_setting = task.notification_settings.first()
                        logger.info(f"获取到通知设置: {notification_setting}")
                        if notification_setting:
                            logger.info(f"通知设置详情 - ID: {notification_setting.id}, 是否启用: {notification_setting.is_enabled}, 成功通知: {notification_setting.notify_on_success}")
                        else:
                            logger.info("没有找到通知设置")
                    except Exception as e:
                        logger.error(f"获取任务通知设置时出错: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    logger.info("任务没有notification_settings属性")
                
                if notification_setting and notification_setting.is_enabled:
                    logger.info("通知设置已启用，准备发送成功通知")
                    if notification_setting.notify_on_success:
                        logger.info("调用 _send_notification 方法发送成功通知")
                        self._send_notification(task, execution_log, success=True)
                    else:
                        logger.info("通知设置中未启用成功通知")
                else:
                    logger.info("通知设置未启用或不存在，跳过成功通知")
                logger.info("=== 结束检查发送成功通知 ===")
                
            except Exception as e:
                # 记录执行失败
                execution_log.status = 'FAILED'
                execution_log.end_time = timezone.now()
                execution_log.error_message = str(e)
                execution_log.save()

                # 更新任务统计
                task.update_run_stats(success=False)
                task.error_message = str(e)
                task.save()

                # 尝试获取 result 中的 execution_id 并生成报告
                try:
                    if 'result' in locals() and result and result.get('execution_id'):
                        from .models import TestExecution
                        test_execution_id = result.get('execution_id')
                        test_execution = TestExecution.objects.get(id=test_execution_id)
                        logger.info(f"失败情况下为 TestExecution {test_execution_id} 生成报告...")
                        # 使用 TestExecutionViewSet 实例来生成报告
                        test_execution_viewset = TestExecutionViewSet()
                        report_result = test_execution_viewset._generate_report_for_execution(test_execution)
                        if 'error' in report_result:
                            logger.error(f"失败情况下生成报告失败: {report_result['error']}")
                        else:
                            logger.info(f"失败情况下生成报告成功: {report_result.get('report_url')}")
                            # 将报告链接添加到结果中
                            result['report_url'] = report_result.get('report_url')
                            execution_log.result = result
                            execution_log.save()
                except Exception as report_e:
                    logger.error(f"失败情况下生成报告时出错: {str(report_e)}", exc_info=True)

                logger.info("=== 开始检查发送失败通知 ===")
                # 发送失败通知（如果配置了）
                # 检查任务是否有通知设置
                notification_setting = None
                if hasattr(task, 'notification_settings'):
                    try:
                        notification_setting = task.notification_settings.first()
                        logger.info(f"获取到通知设置（失败情况）: {notification_setting}")
                        if notification_setting:
                            logger.info(f"通知设置详情（失败情况） - ID: {notification_setting.id}, 是否启用: {notification_setting.is_enabled}, 失败通知: {notification_setting.notify_on_failure}")
                        else:
                            logger.info("没有找到通知设置（失败情况）")
                    except Exception as e:
                        logger.error(f"获取任务通知设置时出错（失败情况）: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    logger.info("任务没有notification_settings属性（失败情况）")
                
                if notification_setting and notification_setting.is_enabled:
                    logger.info("通知设置已启用，准备发送失败通知")
                    if notification_setting.notify_on_failure:
                        logger.info("调用 _send_notification 方法发送失败通知")
                        self._send_notification(task, execution_log, success=False)
                    else:
                        logger.info("通知设置中未启用失败通知")
                else:
                    logger.info("通知设置未启用或不存在，跳过失败通知")
                logger.info("=== 结束检查发送失败通知 ===")
        
        # 在新线程中执行
        thread = threading.Thread(target=execute)
        thread.daemon = True
        thread.start()
    
    def _execute_test_suite(self, task):
        """执行测试套件"""
        from .utils import execute_test_suite
        
        result = execute_test_suite(
            task.test_suite, 
            task.environment, 
            task.created_by
        )
        return result
    
    def _execute_api_request(self, task):
        """执行API请求"""
        from .utils import execute_api_request
        
        result = execute_api_request(
            task.api_request, 
            task.environment, 
            task.created_by
        )
        return result
    
    def _send_notification(self, task, execution_log, success=True):
        """发送通知邮件"""
        try:
            import logging
            logger = logging.getLogger(__name__)
            from django.core.mail import send_mail
            from django.conf import settings

            logger.info("=== _send_notification 方法被调用 ===")
            logger.info(f"任务ID: {task.id}, 任务名称: {task.name}, 执行状态: {success}")

            # 检查任务是否有通知设置
            notification_setting = None
            if hasattr(task, 'notification_settings'):
                try:
                    notification_setting = task.notification_settings.first()
                    logger.info(f"获取到通知设置: {notification_setting}")
                except Exception as e:
                    logger.error(f"获取任务通知设置时出错: {e}")
                    import traceback
                    traceback.print_exc()

            # 检查是否应该发送通知
            if notification_setting:
                logger.info(f"通知设置详情 - ID: {notification_setting.id}, 是否启用: {notification_setting.is_enabled}")
                
                if not notification_setting.is_enabled:
                    logger.info(f"任务 {task.id} 的通知设置未启用")
                    # 检查是否有任务表单中的通知邮箱
                    if not (hasattr(task, 'notify_emails') and task.notify_emails):
                        return
                    logger.info("但任务表单中指定了通知邮箱，继续发送通知")
                else:
                    # 检查是否应该发送通知
                    execution_status = 'success' if success else 'failed'
                    should_notify = notification_setting.should_notify(execution_status)
                    logger.info(f"执行状态: {execution_status}, should_notify结果: {should_notify}")
                    if not should_notify:
                        logger.info(f"根据执行状态 {execution_status}，不应该发送通知")
                        return
            else:
                logger.warning(f"任务 {task.id} 没有通知设置")
                # 如果没有通知设置，检查是否有任务表单中的通知邮箱
                if not (hasattr(task, 'notify_emails') and task.notify_emails):
                    logger.warning("任务也没有设置通知邮箱，跳过发送")
                    return
                logger.info("任务表单中指定了通知邮箱，继续发送通知")

            logger.info("通过了通知条件检查")

            # 获取通知配置
            notification_config = None
            if notification_setting:
                notification_config = notification_setting.get_notification_config()
            
            # 检查是否有通知配置或自定义配置
            has_config = notification_config is not None
            has_custom_bots = notification_setting and bool(notification_setting.custom_webhook_bots)
            has_custom_recipients = notification_setting and notification_setting.custom_recipients.exists()
            has_task_emails = hasattr(task, 'notify_emails') and task.notify_emails
            
            if not (has_config or has_custom_bots or has_custom_recipients or has_task_emails):
                logger.warning("没有找到通知配置且无自定义设置")
                return

            if notification_config:
                logger.info(f"找到了通知配置: {notification_config.name}")
            else:
                logger.info("使用自定义通知设置")

            # 根据通知类型发送不同类型的通知
            if notification_setting:
                logger.info(f"通知类型: {notification_setting.notification_type}")
                notification_type = notification_setting.notification_type
            else:
                logger.info("没有通知设置，默认使用邮件通知")
                notification_type = 'email'

            if notification_type in ['email', 'both']:
                logger.info("发送邮件通知")
                self._send_email_notification(task, execution_log, notification_setting, notification_config, success)

            if notification_setting and notification_type in ['webhook', 'both']:
                logger.info("发送Webhook通知")
                self._send_webhook_notification(task, execution_log, notification_setting, notification_config, success)

        except Exception as e:
            logger.error(f"发送通知失败: {str(e)}", exc_info=True)

    def _send_email_notification(self, task, execution_log, notification_setting, notification_config, success):
        """发送邮件通知"""
        try:
            import logging
            logger = logging.getLogger(__name__)
            from django.core.mail import send_mail
            from django.conf import settings

            logger.info("=== 开始发送邮件通知 ===")

            # 准备邮件内容
            subject = f"定时任务执行{'成功' if success else '失败'}: {task.name}"

            # 构建执行概要
            summary_info = '无详细信息'
            detailed_results = ''
            failed_requests_detail = ''
            report_url = ''
            
            if execution_log.result:
                result_data = execution_log.result
                
                # 执行概要
                summary_fields = {
                    '执行ID': result_data.get('execution_id'),
                    '执行状态': '成功' if result_data.get('success') else '失败',
                    '总请求数': result_data.get('total_count'),
                    '通过数': result_data.get('passed_count'),
                    '失败数': result_data.get('failed_count'),
                    '通过率': f"{result_data.get('passed_count', 0) / result_data.get('total_count', 1) * 100:.1f}%" if result_data.get('total_count') else 'N/A'
                }
                summary_info = '\n'.join([f'{k}: {v}' for k, v in summary_fields.items() if v is not None])
                
                # 详细请求结果
                results = result_data.get('results', [])
                if results:
                    detailed_results_list = []
                    failed_list = []
                    
                    for idx, result in enumerate(results, 1):
                        status_icon = '✅' if result.get('passed') else '❌'
                        method = result.get('method', 'N/A')
                        name = result.get('name', f'请求{idx}')
                        status_code = result.get('status_code', 'N/A')
                        response_time = f"{result.get('response_time', 0):.0f}ms" if result.get('response_time') else 'N/A'
                        
                        detail_line = f"{status_icon} [{method}] {name} - 状态码:{status_code} 耗时:{response_time}"
                        detailed_results_list.append(detail_line)
                        
                        # 收集失败请求
                        if not result.get('passed'):
                            error_msg = result.get('error', '无错误信息')
                            url = result.get('url', 'N/A')
                            failed_detail = f"❌ [{method}] {name}\nURL: {url}\n状态码: {status_code}\n错误: {error_msg}"
                            failed_list.append(failed_detail)
                    
                    detailed_results = '\n'.join(detailed_results_list)
                    
                    if failed_list:
                        failed_requests_detail = '\n'.join(failed_list)
                
                # 报告链接 - 直接指向 HTML 报告文件
                execution_id = result_data.get('execution_id')
                if execution_id:
                    local_ip = self._get_local_ip()
                    site_url = getattr(settings, 'SITE_URL', f"http://{local_ip}:8000")
                    if 'localhost' in site_url or '127.0.0.1' in site_url:
                        site_url = f"http://{local_ip}:8000"
                    report_url = f"{site_url}/api-testing/allure-reports/execution_{execution_id}/summary.html"

            # 构建完整邮件内容
            # 将UTC时间转换为本地时间
            local_execution_time = timezone.localtime(execution_log.created_at).strftime('%Y-%m-%d %H:%M:%S')
            message_parts = [
                f"任务名称: {task.name}",
                f"执行状态: {'成功' if success else '失败'}",
                f"执行时间: {local_execution_time}",
                f"任务类型: {'测试场景执行' if task.task_type == 'TEST_SUITE' else 'API请求执行'}",
                "",
                "═══════════ 执行概要 ═══════════",
                summary_info,
            ]
            
            # 添加详细结果
            if detailed_results:
                message_parts.extend([
                    "",
                    "═══════════ 详细结果 ═══════════",
                    detailed_results,
                ])
            
            # 添加失败详情
            if failed_requests_detail:
                message_parts.extend([
                    "",
                    "═══════════ 失败详情 ═══════════",
                    failed_requests_detail,
                ])
            
            # 添加错误信息
            if execution_log.error_message:
                message_parts.extend([
                    "",
                    "═══════════ 错误信息 ═══════════",
                    execution_log.error_message,
                ])
            
            # 添加报告链接
            if report_url:
                message_parts.extend([
                    "",
                    "═══════════ 查看报告 ═══════════",
                    f"请访问: {report_url}",
                ])
            
            message = '\n'.join(message_parts)

            # 获取收件人列表
            recipients = []
            # 首先检查自定义收件人
            if notification_setting and notification_setting.custom_recipients.exists():
                recipients = [user.email for user in notification_setting.custom_recipients.all() if user.email]
                logger.info(f"使用自定义收件人: {recipients}")

            # 如果定时任务表单中指定了通知邮箱，也添加到收件人列表
            if hasattr(task, 'notify_emails') and task.notify_emails:
                if isinstance(task.notify_emails, list):
                    recipients.extend(task.notify_emails)
                else:
                    recipients.append(task.notify_emails)
                logger.info(f"添加任务表单中的通知邮箱: {task.notify_emails}")

            # 去重收件人
            recipients = list(set(recipients))
            logger.info(f"最终收件人列表: {recipients}")

            if not recipients:
                logger.warning("没有找到任何邮件收件人")
                return

            # 发送邮件
            from_email = settings.DEFAULT_FROM_EMAIL
            logger.info(f"准备发送邮件，发件人: {from_email}, 收件人: {recipients}")
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=recipients,
                fail_silently=False,
            )
            logger.info("邮件发送成功")

            # 记录通知日志
            from .models import NotificationLog
            NotificationLog.objects.create(
                task=task,
                task_name=task.name,
                task_type=task.task_type,
                notification_type='task_execution',
                sender_name='系统邮件通知',
                sender_email=from_email,
                recipient_info=[{'email': email} for email in recipients],
                notification_content=message,
                status='success',
                sent_at=timezone.now()
            )

        except Exception as e:
            logger.error(f"发送邮件通知失败: {str(e)}", exc_info=True)
            # 记录通知发送失败的日志
            try:
                from .models import NotificationLog
                NotificationLog.objects.create(
                    task=task,
                    task_name=task.name,
                    task_type=task.task_type,
                    notification_type='task_execution',
                    sender_name='系统邮件通知',
                    sender_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_info=[{'email': email} for email in recipients] if 'recipients' in locals() else [],
                    notification_content=f"发送邮件通知失败: {str(e)}",
                    status='failed',
                    error_message=str(e)
                )
            except:
                pass

    def _get_local_ip(self):
        """获取本机局域网IP地址"""
        try:
            import socket
            # 创建一个UDP连接来获取本机IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            return "127.0.0.1"

    def _send_webhook_notification(self, task, execution_log, notification_setting, notification_config, success):
        """发送Webhook通知"""
        try:
            import logging
            import requests
            import json
            logger = logging.getLogger(__name__)

            logger.info("=== 开始发送Webhook通知 ===")

            all_webhook_bots = []

            # 使用统一的通知配置
            try:
                from apps.core.models import UnifiedNotificationConfig
                all_webhook_configs = UnifiedNotificationConfig.objects.filter(
                    config_type__in=['webhook_wechat', 'webhook_feishu', 'webhook_dingtalk'],
                    is_active=True
                )
                logger.info("使用统一通知配置 (UnifiedNotificationConfig)")

                for config in all_webhook_configs:
                    bots = config.get_webhook_bots()
                    for bot in bots:
                        # 只添加启用了"接口测试"的机器人
                        if bot.get('enabled', True) and bot.get('enable_api_testing', True):
                            all_webhook_bots.append(bot)
                            logger.info(f"从统一配置获取机器人: {bot.get('name')} (接口测试已启用)")
                        elif bot.get('enabled', True):
                            logger.info(f"统一配置机器人 {bot.get('name')} 未启用接口测试，跳过")

            except ImportError:
                logger.warning("无法导入统一配置，尝试使用 API 测试模块配置")
                # 回退到旧的逻辑
                if notification_config:
                    bots = notification_config.get_webhook_bots()
                    for bot in bots:
                        if bot.get('enabled', True):
                            all_webhook_bots.append(bot)
                            logger.info(f"从 API 测试配置获取机器人: {bot.get('name')}")
            except Exception as e:
                logger.error(f"获取统一配置时出错: {e}")

            # 获取自定义机器人配置 (覆盖同名/同类型或者是累加，这里选择累加)
            if notification_setting.custom_webhook_bots:
                logger.info(f"发现自定义Webhook机器人配置: {len(notification_setting.custom_webhook_bots)}个")
                for bot_type, bot_config in notification_setting.custom_webhook_bots.items():
                    # 构造统一的bot结构
                    bot_data = {
                        'type': bot_type,
                        'name': bot_config.get('name', f'自定义{bot_type}机器人'),
                        'webhook_url': bot_config.get('webhook_url'),
                        'enabled': bot_config.get('enabled', True)
                    }
                    if bot_type == 'dingtalk' and bot_config.get('secret'):
                        bot_data['secret'] = bot_config.get('secret')

                    if bot_data.get('enabled', True) and bot_data.get('webhook_url'):
                        all_webhook_bots.append(bot_data)

            if not all_webhook_bots:
                logger.warning("没有找到任何启用的webhook机器人配置")
                return

            logger.info(f"总共找到 {len(all_webhook_bots)} 个待发送的webhook机器人")

            # 准备通知内容
            status_text = '成功' if success else '失败'
            status_color = 'green' if success else 'red'

            # 获取执行结果统计 - 从 result 中获取 TestExecution 相关信息
            result = execution_log.result or {}
            total_requests = result.get('total_count', 0)
            passed_requests = result.get('passed_count', 0)
            failed_requests = result.get('failed_count', 0)
            pass_rate = f"{(passed_requests / total_requests * 100):.1f}%" if total_requests > 0 else "0.0%"

            # 将UTC时间转换为本地时间
            local_execution_time = timezone.localtime(execution_log.created_at).strftime('%Y-%m-%d %H:%M:%S')

            # 获取 TestExecution ID（用于生成报告 URL）
            test_execution_id = result.get('execution_id')

            # 构建报告和截图链接
            # 优先使用配置的 SITE_URL，如果没有则自动获取本地 IP
            local_ip = self._get_local_ip()
            default_site_url = f"http://{local_ip}:8000"
            site_url = getattr(settings, 'SITE_URL', default_site_url)

            # 如果 site_url 包含 localhost，替换为本地 IP
            if 'localhost' in site_url or '127.0.0.1' in site_url:
                site_url = f"http://{local_ip}:8000"

            # 使用 TestExecution ID 构建报告 URL（如果存在）
            # 优先使用 execution_log.result 中保存的报告链接和截图链接
            if test_execution_id:
                # 从 result 中获取已生成的报告链接
                saved_report_url = result.get('report_url')
                if saved_report_url and saved_report_url.startswith('/'):
                    report_url = f"{site_url}{saved_report_url}"
                else:
                    report_url = saved_report_url or f"{site_url}/api-testing/allure-reports/execution_{test_execution_id}/summary.html"
            else:
                report_url = f"{site_url}/api-testing/reports"

            # 为不同的机器人平台准备消息格式
            for bot in all_webhook_bots:
                if not bot.get('enabled', True) or not bot.get('webhook_url'):
                    logger.info(f"跳过未启用或无URL的机器人: {bot.get('name', 'Unknown')}")
                    continue

                bot_type = bot.get('type', 'unknown')
                webhook_url = bot['webhook_url']
                logger.info(f"发送通知到 {bot_type} 机器人: {bot.get('name', 'Unknown')}")

                # 根据机器人类型构造消息格式
                if bot_type == 'wechat':  # 企业微信
                    wechat_content = f"""**定时任务执行{status_text}**

**任务名称:** {task.name}

**执行状态:** {status_text}

**执行统计:**
> 总请求数: {total_requests}
> 通过: {passed_requests}
> 失败: {failed_requests}
> 通过率: {pass_rate}

**执行时间:** {local_execution_time}

**任务类型:** {'测试场景执行' if task.task_type == 'TEST_SUITE' else 'API请求执行'}

**查看报告:** [点击查看完整报告]({report_url})"""

                    message_data = {
                        "msgtype": "markdown",
                        "markdown": {
                            "content": wechat_content
                        }
                    }
                elif bot_type == 'feishu':  # 飞书
                    # 构建飞书卡片内容
                    feishu_content = f"**任务名称:** {task.name}\n**执行状态:** {status_text}\n**执行时间:** {local_execution_time}\n**任务类型:** {'测试场景执行' if task.task_type == 'TEST_SUITE' else 'API请求执行'}\n\n**执行统计**\n总请求数: {total_requests}\n通过: {passed_requests}\n失败: {failed_requests}\n通过率: {pass_rate}"

                    message_data = {
                        "msg_type": "interactive",
                        "card": {
                            "elements": [
                                {
                                    "tag": "div",
                                    "text": {
                                        "content": feishu_content,
                                        "tag": "lark_md"
                                    }
                                },
                                {
                                    "tag": "action",
                                    "actions": [
                                        {
                                            "tag": "button",
                                            "text": {
                                                "tag": "plain_text",
                                                "content": "查看完整报告"
                                            },
                                            "type": "primary",
                                            "url": report_url
                                        }
                                    ]
                                }
                            ],
                            "header": {
                                "title": {
                                    "content": f"定时任务执行{status_text}",
                                    "tag": "plain_text"
                                },
                                "template": "green" if success else "red"
                            }
                        }
                    }
                elif bot_type == 'dingtalk':  # 钉钉
                    dingtalk_text = f"""**定时任务执行{status_text}**

**任务名称:** {task.name}

**执行状态:** {status_text}

**执行统计:**
- 总请求数: {total_requests}
- 通过: {passed_requests}
- 失败: {failed_requests}
- 通过率: {pass_rate}

**执行时间:** {local_execution_time}

**任务类型:** {'测试场景执行' if task.task_type == 'TEST_SUITE' else 'API请求执行'}

**查看报告:** [点击查看完整报告]({report_url})"""

                    message_data = {
                        "msgtype": "markdown",
                        "markdown": {
                            "title": f"定时任务执行{status_text}",
                            "text": dingtalk_text
                        }
                    }

                    # 钉钉机器人签名验证
                    secret = bot.get('secret')
                    if secret:
                        import time
                        import hmac
                        import hashlib
                        import base64
                        import urllib.parse

                        timestamp = str(round(time.time() * 1000))
                        string_to_sign = f'{timestamp}\n{secret}'
                        string_to_sign_enc = string_to_sign.encode('utf-8')
                        secret_enc = secret.encode('utf-8')
                        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
                        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))

                        # 在URL中添加签名参数
                        if '?' in webhook_url:
                            webhook_url += f'&timestamp={timestamp}&sign={sign}'
                        else:
                            webhook_url += f'?timestamp={timestamp}&sign={sign}'

                        logger.info(f"钉钉机器人签名验证 - 时间戳: {timestamp}")
                        logger.info(f"签名字符串: {string_to_sign}")
                        logger.info(f"生成的签名: {sign}")
                        logger.info(f"最终URL: {webhook_url}")
                    else:
                        logger.info("钉钉机器人未配置签名密钥，使用无签名模式")
                else:  # 通用格式
                    message_data = {
                        "text": f"定时任务执行{status_text}\n任务名称: {task.name}\n执行状态: {status_text}\n执行时间: {local_execution_time}\n任务类型: {'测试场景执行' if task.task_type == 'TEST_SUITE' else 'API请求执行'}"
                    }

                # 发送webhook请求
                try:
                    response = requests.post(
                        webhook_url,
                        json=message_data,
                        headers={'Content-Type': 'application/json'},
                        timeout=10
                    )
                    response.raise_for_status()
                    logger.info(f"Webhook通知发送成功 - {bot_type}: {response.status_code}")

                    # 记录成功的通知日志
                    from .models import NotificationLog
                    NotificationLog.objects.create(
                        task=task,
                        task_name=task.name,
                        task_type=task.task_type,
                        notification_type='task_execution',
                        sender_name=f'系统Webhook通知-{bot_type}',
                        sender_email='',
                        recipient_info=[],
                        webhook_bot_info={
                            'bot_type': bot_type,
                            'bot_name': bot.get('name', 'Unknown'),
                            'webhook_url': webhook_url[:50] + '...' if len(webhook_url) > 50 else webhook_url
                        },
                        notification_content=json.dumps(message_data, ensure_ascii=False),
                        status='success',
                        sent_at=timezone.now(),
                        response_info={
                            'status_code': response.status_code,
                            'response_text': response.text[:500]
                        }
                    )

                except requests.exceptions.RequestException as e:
                    logger.error(f"Webhook通知发送失败 - {bot_type}: {str(e)}")

                    # 记录失败的通知日志
                    try:
                        from .models import NotificationLog
                        NotificationLog.objects.create(
                            task=task,
                            task_name=task.name,
                            task_type=task.task_type,
                            notification_type='task_execution',
                            sender_name=f'系统Webhook通知-{bot_type}',
                            sender_email='',
                            recipient_info=[],
                            webhook_bot_info={
                                'bot_type': bot_type,
                                'bot_name': bot.get('name', 'Unknown'),
                                'webhook_url': webhook_url[:50] + '...' if len(webhook_url) > 50 else webhook_url
                            },
                            notification_content=json.dumps(message_data, ensure_ascii=False),
                            status='failed',
                            error_message=str(e),
                            sent_at=timezone.now()
                        )
                    except:
                        pass

            logger.info("=== 结束发送Webhook通知 ===")

        except Exception as e:
            logger.error(f"发送Webhook通知失败: {str(e)}", exc_info=True)


class TaskExecutionLogViewSet(viewsets.ReadOnlyModelViewSet):
    """任务执行日志视图集"""
    queryset = TaskExecutionLog.objects.all()
    serializer_class = TaskExecutionLogSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['task', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        # 返回所有任务执行日志，不进行权限过滤
        return TaskExecutionLog.objects.all().select_related('task', 'executed_by')




# ================ 通知管理相关视图集 ================


class NotificationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """通知日志视图集"""
    queryset = NotificationLog.objects.all()
    serializer_class = NotificationLogSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'notification_type']
    ordering = ['-created_at']
    
    def get_queryset(self):
        # 返回所有通知日志，不进行权限过滤
        return NotificationLog.objects.all()
    
    @action(detail=True, methods=['get'], url_path='detail')
    def get_notification_detail(self, request, pk=None):
        """获取通知详情"""
        notification = self.get_object()
        serializer = NotificationLogDetailSerializer(notification)
        return Response(serializer.data)


class TaskNotificationSettingViewSet(viewsets.ModelViewSet):
    """定时任务通知设置视图集"""
    queryset = TaskNotificationSetting.objects.all()
    serializer_class = TaskNotificationSettingSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['task', 'is_enabled']
    ordering = ['-created_at']
    
    def get_queryset(self):
        # 返回所有任务通知设置，不进行权限过滤
        return TaskNotificationSetting.objects.all()
    
    @action(detail=True, methods=['post'], url_path='update-settings')
    def update_notification_settings(self, request, pk=None):
        """更新通知设置"""
        setting = self.get_object()
        serializer = TaskNotificationSettingDetailSerializer(setting, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data)


# ================ 通知管理相关模型 ================




class OperationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """操作日志视图集"""
    queryset = OperationLog.objects.all()
    serializer_class = OperationLogSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['operation_type', 'resource_type', 'user']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """只返回当前用户相关的操作日志"""
        user = self.request.user
        # 可以根据需要调整权限逻辑，这里返回所有日志
        return OperationLog.objects.all().order_by('-created_at')


class ApiDashboardViewSet(viewsets.ViewSet):
    """API测试仪表盘视图集"""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """获取仪表盘统计数据"""
        # 统计数据（不进行权限过滤）
        project_count = ApiProject.objects.count()
        interface_count = ApiRequest.objects.count()
        suite_count = TestSuite.objects.count()
        history_count = RequestHistory.objects.count()

        return Response({
            'project_count': project_count,
            'interface_count': interface_count,
            'suite_count': suite_count,
            'history_count': history_count
        })

    @action(detail=False, methods=['get'])
    def team_stats(self, request):
        """获取团队月度统计"""
        from django.db.models import Count, Sum, Q
        from django.contrib.auth import get_user_model
        import datetime

        User = get_user_model()

        # 获取查询月份，默认为当前月
        month_str = request.query_params.get('month')
        if month_str:
            try:
                year, month = map(int, month_str.split('-'))
                query_date = datetime.date(year, month, 1)
            except (ValueError, IndexError):
                return Response({'error': '月份格式错误，应为 YYYY-MM'}, status=400)
        else:
            query_date = datetime.date.today().replace(day=1)

        # 计算月份范围
        if query_date.month == 12:
            next_month = query_date.replace(year=query_date.year + 1, month=1)
        else:
            next_month = query_date.replace(month=query_date.month + 1)

        # 团队成员执行统计排行（只统计已完成的执行）
        execution_rank = TestExecution.objects.filter(
            created_at__gte=query_date,
            created_at__lt=next_month,
            status='COMPLETED'
        ).values('executed_by__id', 'executed_by__username').annotate(
            execution_count=Count('id'),
            passed_cases=Sum('passed_requests'),
            failed_cases=Sum('failed_requests')
        ).order_by('-execution_count')[:10]

        execution_rank_list = []
        for item in execution_rank:
            total = (item['passed_cases'] or 0) + (item['failed_cases'] or 0)
            pass_rate = round((item['passed_cases'] or 0) / total * 100, 2) if total > 0 else 0
            execution_rank_list.append({
                'user_id': item['executed_by__id'],
                'username': item['executed_by__username'],
                'execution_count': item['execution_count'],
                'passed_cases': item['passed_cases'] or 0,
                'failed_cases': item['failed_cases'] or 0,
                'pass_rate': pass_rate
            })

        # 团队成员评审统计排行（按创建人统计测试套件的评审通过情况）
        from django.db.models import OuterRef, Subquery

        # 获取本月创建的测试套件，按创建人分组统计
        review_rank = TestSuite.objects.filter(
            created_at__gte=query_date,
            created_at__lt=next_month
        ).values('created_by__id', 'created_by__username').annotate(
            total_count=Count('id'),
            approved_count=Count(
                'id',
                filter=Q(review_records__status='approved')
            ),
            pending_count=Count(
                'id',
                filter=~Q(review_records__status='approved') & ~Q(review_records__status='rejected')
            ),
            rejected_count=Count(
                'id',
                filter=Q(review_records__status='rejected')
            )
        ).order_by('-approved_count')[:10]

        review_rank_list = []
        for item in review_rank:
            total = item['total_count']
            approved = item['approved_count']
            pass_rate = round(approved / total * 100, 2) if total > 0 else 0
            review_rank_list.append({
                'user_id': item['created_by__id'],
                'username': item['created_by__username'],
                'total_count': total,
                'approved_count': approved,
                'pending_count': item['pending_count'],
                'rejected_count': item['rejected_count'],
                'pass_rate': pass_rate
            })

        # 团队总体统计 - TestExecution 统计
        team_execution_count = TestExecution.objects.filter(
            created_at__gte=query_date,
            created_at__lt=next_month
        ).count()

        team_passed_cases = TestExecution.objects.filter(
            created_at__gte=query_date,
            created_at__lt=next_month,
            status='COMPLETED'
        ).aggregate(total=Sum('passed_requests'))['total'] or 0

        team_failed_cases = TestExecution.objects.filter(
            created_at__gte=query_date,
            created_at__lt=next_month,
            status='COMPLETED'
        ).aggregate(total=Sum('failed_requests'))['total'] or 0

        # 统计 RequestHistory 中的单接口执行记录
        # 获取当月的所有请求历史
        request_histories = RequestHistory.objects.filter(
            executed_at__gte=query_date,
            executed_at__lt=next_month
        )

        # 单接口执行次数
        history_execution_count = request_histories.count()

        # 计算请求历史中的成功/失败数量
        history_passed = 0
        history_failed = 0
        for history in request_histories:
            # 判断逻辑与前端保持一致
            status_code = history.status_code
            if not status_code:
                history_failed += 1
            elif status_code >= 400:
                history_failed += 1
            elif history.assertions_results and isinstance(history.assertions_results, list):
                # 检查断言是否失败
                has_failed_assertion = any(
                    result.get('passed') is False for result in history.assertions_results
                )
                if has_failed_assertion:
                    history_failed += 1
                else:
                    history_passed += 1
            else:
                # 状态码 200-399 且无断言失败，视为成功
                history_passed += 1

        # 合并统计结果
        total_passed_cases = team_passed_cases + history_passed
        total_failed_cases = team_failed_cases + history_failed

        team_total_cases = total_passed_cases + total_failed_cases
        team_pass_rate = round(total_passed_cases / team_total_cases * 100, 2) if team_total_cases > 0 else 0

        # 合并总执行次数（测试套件执行 + 单接口执行）
        total_execution_count = team_execution_count + history_execution_count

        return Response({
            'month': query_date.strftime('%Y-%m'),
            'team_summary': {
                'total_execution_count': total_execution_count,
                'total_passed_cases': total_passed_cases,
                'total_failed_cases': total_failed_cases,
                'total_pass_rate': team_pass_rate
            },
            'execution_rank': execution_rank_list,
            'review_rank': review_rank_list
        })

    @action(detail=False, methods=['get'])
    def monthly_trend(self, request):
        """获取月度趋势数据"""
        from django.db.models import Count, Sum
        import datetime

        # 获取月份数量，默认6个月
        try:
            months = int(request.query_params.get('months', 6))
        except ValueError:
            months = 6

        months = min(max(months, 1), 12)  # 限制1-12个月

        end_date = datetime.date.today().replace(day=1)
        trends = []

        for i in range(months - 1, -1, -1):
            # 计算当前月份
            if end_date.month - i <= 0:
                year = end_date.year - 1
                month = end_date.month - i + 12
            else:
                year = end_date.year
                month = end_date.month - i

            query_date = datetime.date(year, month, 1)
            if month == 12:
                next_month = datetime.date(year + 1, 1, 1)
            else:
                next_month = datetime.date(year, month + 1, 1)

            # 统计该月数据
            execution_count = TestExecution.objects.filter(
                created_at__gte=query_date,
                created_at__lt=next_month
            ).count()

            passed_cases = TestExecution.objects.filter(
                created_at__gte=query_date,
                created_at__lt=next_month,
                status='COMPLETED'
            ).aggregate(total=Sum('passed_requests'))['total'] or 0

            failed_cases = TestExecution.objects.filter(
                created_at__gte=query_date,
                created_at__lt=next_month,
                status='COMPLETED'
            ).aggregate(total=Sum('failed_requests'))['total'] or 0

            total_cases = passed_cases + failed_cases
            pass_rate = round(passed_cases / total_cases * 100, 2) if total_cases > 0 else 0

            review_count = TestSuiteReviewRecord.objects.filter(
                reviewed_at__gte=query_date,
                reviewed_at__lt=next_month
            ).count()

            trends.append({
                'month': query_date.strftime('%Y-%m'),
                'execution_count': execution_count,
                'passed_cases': passed_cases,
                'failed_cases': failed_cases,
                'pass_rate': pass_rate,
                'review_count': review_count
            })

        return Response({
            'months': months,
            'trends': trends
        })


class AIServiceConfigViewSet(viewsets.ModelViewSet):
    """AI服务配置视图集"""
    queryset = AIServiceConfig.objects.all()
    serializer_class = AIServiceConfigSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['service_type', 'role', 'is_active']
    search_fields = ['name', 'model_name']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        # 返回所有AI配置，不进行权限过滤
        return AIServiceConfig.objects.all()

    @action(detail=False, methods=['post'])
    def test_connection(self, request):
        """测试AI服务连接"""
        config_id = request.data.get('config_id')
        if not config_id:
            return Response({'error': '请提供配置ID'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            config = AIServiceConfig.objects.get(id=config_id)
        except AIServiceConfig.DoesNotExist:
            return Response({'error': '配置不存在'}, status=status.HTTP_404_NOT_FOUND)

        try:
            headers = {
                'Authorization': f'Bearer {config.api_key}',
                'Content-Type': 'application/json'
            }

            test_data = {
                'model': config.model_name,
                'messages': [{'role': 'user', 'content': 'Hello'}],
                'max_tokens': 10
            }

            response = requests.post(
                f"{config.base_url}/chat/completions",
                headers=headers,
                json=test_data,
                timeout=10
            )

            if response.status_code == 200:
                return Response({'message': '连接测试成功', 'status': 'success'})
            else:
                return Response({
                    'error': f'连接测试失败: {response.status_code}',
                    'details': response.text
                }, status=status.HTTP_400_BAD_REQUEST)

        except requests.exceptions.Timeout:
            return Response({'error': '连接超时'}, status=status.HTTP_408_REQUEST_TIMEOUT)
        except requests.exceptions.RequestException as e:
            return Response({'error': f'连接失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({'error': f'未知错误: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def complete_parameter_descriptions(self, request):
        """使用AI自动补全参数描述"""
        request_id = request.data.get('request_id')
        if not request_id:
            return Response({'error': '请提供请求ID'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            api_request = ApiRequest.objects.get(id=request_id)
        except ApiRequest.DoesNotExist:
            return Response({'error': '请求不存在'}, status=status.HTTP_404_NOT_FOUND)

        try:
            config = AIServiceConfig.objects.filter(
                role='description',
                is_active=True
            ).first()

            if not config:
                return Response({'error': '未找到可用的参数描述补全AI配置'}, status=status.HTTP_400_BAD_REQUEST)

            headers = {
                'Authorization': f'Bearer {config.api_key}',
                'Content-Type': 'application/json'
            }

            request_info = {
                'name': api_request.name,
                'description': api_request.description,
                'method': effective_method,
                'url': api_request.url,
                'headers': api_request.headers,
                'params': api_request.params,
                'body': api_request.body
            }

            prompt = f"""请为以下API请求的参数生成详细的描述说明：

接口名称: {request_info['name']}
接口描述: {request_info['description']}
请求方法: {request_info['method']}
请求URL: {request_info['url']}

请求头参数:
{json.dumps(request_info['headers'], ensure_ascii=False, indent=2)}

URL参数:
{json.dumps(request_info['params'], ensure_ascii=False, indent=2)}

请求体参数:
{json.dumps(request_info['body'], ensure_ascii=False, indent=2)}

请为每个参数生成详细的描述说明，包括：
1. 参数用途
2. 数据类型
3. 是否必填
4. 取值范围或示例值
5. 其他注意事项

请返回JSON格式的结果，格式如下：
{{
  "headers": {{
    "参数名": "参数描述"
  }},
  "params": {{
    "参数名": "参数描述"
  }},
  "body": {{
    "参数名": "参数描述"
  }}
}}"""

            ai_data = {
                'model': config.model_name,
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': config.max_tokens,
                'temperature': config.temperature
            }

            response = requests.post(
                f"{config.base_url}/chat/completions",
                headers=headers,
                json=ai_data,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                try:
                    descriptions = json.loads(content)
                    return Response({'descriptions': descriptions})
                except json.JSONDecodeError:
                    return Response({'descriptions': {}, 'raw_content': content})
            else:
                return Response({
                    'error': f'AI服务调用失败: {response.status_code}',
                    'details': response.text
                }, status=status.HTTP_400_BAD_REQUEST)

        except requests.exceptions.Timeout:
            return Response({'error': 'AI服务调用超时'}, status=status.HTTP_408_REQUEST_TIMEOUT)
        except requests.exceptions.RequestException as e:
            return Response({'error': f'AI服务调用失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({'error': f'未知错误: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== API Fox CLI 导入 API ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apifox_import_validate(request):
    """
    验证 API Fox CLI JSON 文件
    
    请求参数:
    - file: 上传的 JSON 文件
    
    返回:
    - valid: 是否可导入
    - unsupported_functions: 不支持的函数列表
    - total_requests: 请求总数
    - warnings: 警告信息
    """
    from .apifox_importer import validate_apifox_file
    
    if 'file' not in request.FILES:
        return Response(
            {'error': '请上传文件'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    uploaded_file = request.FILES['file']
    
    # 调试: 记录文件信息
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"收到上传文件: name={uploaded_file.name}, size={uploaded_file.size}")
    
    # 保存临时文件
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.json') as tmp:
        for chunk in uploaded_file.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name
    
    # 调试: 读取临时文件验证内容
    try:
        with open(tmp_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"文件解析成功, top-level item count: {len(data.get('item', []))}")
    except Exception as e:
        logger.error(f"文件解析失败: {e}")
    
    try:
        result = validate_apifox_file(tmp_path)
        logger.info(f"验证结果: {result}")
        return Response(result)
    except Exception as e:
        return Response(
            {'error': f'验证失败: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    finally:
        os.unlink(tmp_path)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apifox_import_execute(request):
    """
    执行 API Fox CLI JSON 文件导入
    
    请求参数:
    - file: 上传的 JSON 文件 (必需)
    - project_id: 项目ID (必需)
    - collection_id: 目标集合ID (可选，默认新建)
    - import_env: 是否导入环境变量 (可选，默认false)
    
    返回:
    - success: 是否成功
    - collection_id: 创建的集合ID
    - suite_id: 创建的测试套件ID
    - stats: 导入统计
    - warnings: 警告信息
    """
    from .apifox_importer import import_apifox_cli
    
    # 获取参数
    project_id = request.data.get('project_id')
    collection_id = request.data.get('collection_id')
    import_env = request.data.get('import_env', False)
    
    if 'file' not in request.FILES:
        return Response(
            {'error': '请上传文件'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not project_id:
        return Response(
            {'error': '请提供项目ID'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 验证项目
    try:
        project = ApiProject.objects.get(id=project_id)
    except ApiProject.DoesNotExist:
        return Response(
            {'error': '项目不存在'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # 验证集合（如果指定了）
    target_collection = None
    if collection_id:
        try:
            target_collection = ApiCollection.objects.get(id=collection_id)
        except ApiCollection.DoesNotExist:
            return Response(
                {'error': '集合不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    # 保存临时文件
    uploaded_file = request.FILES['file']
    
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.json') as tmp:
        for chunk in uploaded_file.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name
    
    try:
        # 执行导入
        result = import_apifox_cli(
            file_path=tmp_path,
            user=request.user,
            project=project,
            import_env=import_env
        )
        
        # 如果指定了目标集合，需要更新请求所属集合
        if target_collection and result.get('success'):
            # 获取导入时创建的集合
            imported_collection = ApiCollection.objects.get(
                id=result['collection_id']
            )
            
            # 将请求移动到目标集合
            ApiRequest.objects.filter(
                collection=imported_collection
            ).update(collection=target_collection)
            
            # 更新测试套件所属集合
            TestSuite.objects.filter(
                id=result.get('suite_id')
            ).update(description=f"从 {imported_collection.name} 导入")
            
            # 删除临时创建的集合
            imported_collection.delete()
            
            result['collection_id'] = target_collection.id
        
        return Response(result)
        
    except Exception as e:
        logger.exception("API Fox 导入失败")
        return Response(
            {'error': f'导入失败: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    finally:
        os.unlink(tmp_path)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def apifox_function_list(request):
    """
    获取支持的 API Fox 动态变量函数列表
    
    返回:
    - functions: 按分类的函数列表
    """
    from .apifox_function_mapper import ApifoxFunctionMapper
    
    mapper = ApifoxFunctionMapper()
    functions = mapper.get_supported_functions()
    
    # 按分类组织
    categories = {
        '基础变量': [],
        '文本/数字': [],
        '互联网': [],
        '名称': [],
        '职业': [],
        '电话/地址': [],
        '商业': [],
        '金融': [],
        '日期时间': [],
        '数据库': [],
        '黑客': [],
        '图片': [],
        '音乐': [],
        '动物': [],
        '食物': [],
        '科学': [],
        '航空': [],
        '车辆': [],
        'Git': [],
        '系统': []
    }
    
    for func in functions:
        if func in ['$guid', '$timestamp', '$isoTimestamp', '$randomUUID']:
            categories['基础变量'].append(func)
        elif any(x in func for x in ['randomAlpha', 'randomBoolean', 'randomInt', 'randomFloat', 'randomColor', 'randomHex']):
            categories['文本/数字'].append(func)
        elif any(x in func for x in ['randomIP', 'randomMAC', 'randomPassword', 'randomProtocol', 'randomSemver', 'randomUserAgent', 'randomLocale']):
            categories['互联网'].append(func)
        elif any(x in func for x in ['randomFirstName', 'randomLastName', 'randomFullName', 'randomName']):
            categories['名称'].append(func)
        elif 'randomJob' in func:
            categories['职业'].append(func)
        elif any(x in func for x in ['randomPhone', 'randomCity', 'randomStreet', 'randomCountry', 'randomLatitude', 'randomLongitude']):
            categories['电话/地址'].append(func)
        elif any(x in func for x in ['randomCompany', 'randomCatch', 'randomBs', 'randomProduct']):
            categories['商业'].append(func)
        elif any(x in func for x in ['randomCredit', 'randomIBAN', 'randomBIC', 'randomBitcoin', 'randomCurrency', 'randomTransaction']):
            categories['金融'].append(func)
        elif func.startswith('$date'):
            categories['日期时间'].append(func)
        elif func.startswith('$database'):
            categories['数据库'].append(func)
        elif func.startswith('$hacker'):
            categories['黑客'].append(func)
        elif func.startswith('$image'):
            categories['图片'].append(func)
        elif func.startswith('$music'):
            categories['音乐'].append(func)
        elif func.startswith('$animal'):
            categories['动物'].append(func)
        elif func.startswith('$food'):
            categories['食物'].append(func)
        elif func.startswith('$science'):
            categories['科学'].append(func)
        elif func.startswith('$airline'):
            categories['航空'].append(func)
        elif func.startswith('$vehicle'):
            categories['车辆'].append(func)
        elif func.startswith('$git'):
            categories['Git'].append(func)
        elif func.startswith('$system'):
            categories['系统'].append(func)
    
    # 过滤空分类
    categories = {k: v for k, v in categories.items() if v}
    
    return Response({
        'total': len(functions),
        'categories': categories
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def import_interfaces(request):
    """
    导入接口
    支持格式: openapi (API Fox 导出的 OpenAPI 3.0 JSON)
    """
    import_format = request.data.get('format', 'openapi')
    project_id = request.data.get('project_id')
    collection_id = request.data.get('collection_id')
    auto_create_collections = request.data.get('auto_create_collections', True)
    interfaces = request.data.get('interfaces', [])
    global_headers = request.data.get('global_headers', [])
    global_params = request.data.get('global_params', [])

    if not interfaces:
        return Response(
            {'error': '请提供要导入的接口数据'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 验证项目存在
    if project_id:
        try:
            project = ApiProject.objects.get(id=project_id)
        except ApiProject.DoesNotExist:
            return Response(
                {'error': '项目不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
    else:
        project = None

    # 验证或创建集合
    collection = None
    if collection_id:
        try:
            collection = ApiCollection.objects.get(id=collection_id)
        except ApiCollection.DoesNotExist:
            return Response(
                {'error': '集合不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

    imported_count = 0
    skipped_count = 0
    failed_count = 0
    details = []

    for interface_data in interfaces:
        try:
            name = interface_data.get('name', '')
            method = interface_data.get('method', 'GET')
            url = interface_data.get('url', '')

            if not name or not url:
                failed_count += 1
                details.append({
                    'name': name or '未命名',
                    'status': 'failed',
                    'error': '接口名称或URL为空'
                })
                continue

            # 检查是否已存在相同接口（按名称+方法+URL匹配）
            existing = ApiRequest.objects.filter(
                name=name,
                method=method,
                url=url,
                created_by=request.user
            ).first()

            if existing:
                skipped_count += 1
                details.append({
                    'name': name,
                    'status': 'skipped',
                    'id': existing.id,
                    'error': '接口已存在'
                })
                continue

            # 处理 headers - 分离全局 headers 和接口特定 headers
            raw_headers = interface_data.get('headers', [])
            interface_headers = []
            
            # 兼容字典格式（cURL 导入）和数组格式（API Fox 导入）
            if isinstance(raw_headers, dict):
                # 字典格式: {key: value}
                for key, value in raw_headers.items():
                    interface_headers.append({
                        'key': key,
                        'value': value,
                        'description': '',
                        'enabled': True
                    })
            elif isinstance(raw_headers, list):
                # 数组格式
                for header in raw_headers:
                    if isinstance(header, dict):
                        # 只保留非全局的 headers
                        if not header.get('is_global', False):
                            interface_headers.append({
                                'key': header.get('key', ''),
                                'value': header.get('value', ''),
                                'description': header.get('description', ''),
                                'enabled': True
                            })

            # 处理 params - 分离全局 params 和接口特定 params
            raw_params = interface_data.get('params', [])
            interface_params = []
            for param in raw_params:
                if isinstance(param, dict):
                    # 只保留非全局的 params
                    if not param.get('is_global', False):
                        interface_params.append({
                            'key': param.get('key', ''),
                            'value': param.get('value', ''),
                            'description': param.get('description', ''),
                            'type': param.get('type', 'string'),
                            'enabled': True
                        })

            # 处理 body - 转换为 {type, data} 格式
            raw_body = interface_data.get('body')
            request_type = interface_data.get('request_type', 'json')
            if raw_body:
                # 将 request_type 映射为后端期望的类型
                body_type_mapping = {
                    'json': 'json',
                    'form': 'x-www-form-urlencoded',
                    'raw': 'raw',
                    'none': 'none'
                }
                body_type = body_type_mapping.get(request_type, 'json')
                body = {
                    'type': body_type,
                    'data': raw_body
                }
            else:
                body = {'type': 'none', 'data': None}

            # 创建新接口
            api_request = ApiRequest.objects.create(
                name=name,
                method=method,
                url=url,
                description=interface_data.get('description', ''),
                headers=interface_headers,
                params=interface_params,
                path_params=interface_data.get('path_params', []),
                body=body,
                collection=collection,
                request_type=interface_data.get('request_type', 'HTTP'),
                variable_extractors=interface_data.get('variable_extractors', []),
                assertions=interface_data.get('assertions', []),
                created_by=request.user
            )

            imported_count += 1
            details.append({
                'name': name,
                'status': 'success',
                'id': api_request.id
            })

        except Exception as e:
            failed_count += 1
            details.append({
                'name': interface_data.get('name', '未命名'),
                'status': 'failed',
                'error': str(e)
            })

    return Response({
        'success': True,
        'imported_count': imported_count,
        'skipped_count': skipped_count,
        'failed_count': failed_count,
        'details': details,
        'global_headers': global_headers,
        'global_params': global_params
    })

    @action(detail=False, methods=['post'])
    def generate_mock_data(self, request):
        """使用AI生成模拟数据"""
        schema = request.data.get('schema', {})
        count = request.data.get('count', 1)
        if not schema:
            return Response({'error': '请提供数据结构定义'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            config = AIServiceConfig.objects.filter(
                role='mock_data',
                is_active=True
            ).first()

            if not config:
                return Response({'error': '未找到可用的模拟数据生成AI配置'}, status=status.HTTP_400_BAD_REQUEST)

            headers = {
                'Authorization': f'Bearer {config.api_key}',
                'Content-Type': 'application/json'
            }

            prompt = f"""请根据以下数据结构定义，生成{count}条符合该结构的模拟数据：

数据结构定义：
{json.dumps(schema, ensure_ascii=False, indent=2)}

要求：
1. 数据必须符合给定的结构定义
2. 字符串字段生成有意义的中文内容
3. 数值字段生成合理的数值
4. 日期字段生成有效的日期时间
5. 布尔字段随机生成true/false
6. 数组字段生成适当数量的元素

请返回JSON数组格式的结果。"""

            ai_data = {
                'model': config.model_name,
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': config.max_tokens,
                'temperature': config.temperature
            }

            response = requests.post(
                f"{config.base_url}/chat/completions",
                headers=headers,
                json=ai_data,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                try:
                    mock_data = json.loads(content)
                    return Response({'data': mock_data})
                except json.JSONDecodeError:
                    return Response({'data': [], 'raw_content': content})
            else:
                return Response({
                    'error': f'AI服务调用失败: {response.status_code}',
                    'details': response.text
                }, status=status.HTTP_400_BAD_REQUEST)

        except requests.exceptions.Timeout:
            return Response({'error': 'AI服务调用超时'}, status=status.HTTP_408_REQUEST_TIMEOUT)
        except requests.exceptions.RequestException as e:
            return Response({'error': f'AI服务调用失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({'error': f'未知错误: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def normalize_parameter_names(self, request):
        """使用AI规范化参数名称"""
        parameters = request.data.get('parameters', [])
        if not parameters:
            return Response({'error': '请提供参数列表'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            config = AIServiceConfig.objects.filter(
                role='naming',
                is_active=True
            ).first()

            if not config:
                return Response({'error': '未找到可用的参数命名规范化AI配置'}, status=status.HTTP_400_BAD_REQUEST)

            headers = {
                'Authorization': f'Bearer {config.api_key}',
                'Content-Type': 'application/json'
            }

            params_info = '\n'.join([f"- {param.get('key', '')}: {param.get('value', '')}" for param in parameters])

            prompt = f"""请对以下API参数名称进行规范化处理，使其符合RESTful API命名规范：

{params_info}

请返回JSON格式的结果，包含：
1. 原始参数名
2. 建议的规范化参数名（使用小写字母、下划线分隔、语义清晰）
3. 修改原因

返回格式示例：
[
  {{
    "original": "userName",
    "suggested": "user_name",
    "reason": "使用下划线分隔单词，符合Python命名规范"
  }}
]"""

            ai_data = {
                'model': config.model_name,
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': config.max_tokens,
                'temperature': config.temperature
            }

            response = requests.post(
                f"{config.base_url}/chat/completions",
                headers=headers,
                json=ai_data,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                try:
                    suggestions = json.loads(content)
                    return Response({'suggestions': suggestions})
                except json.JSONDecodeError:
                    return Response({'suggestions': [], 'raw_content': content})
            else:
                return Response({
                    'error': f'AI服务调用失败: {response.status_code}',
                    'details': response.text
                }, status=status.HTTP_400_BAD_REQUEST)

        except requests.exceptions.Timeout:
            return Response({'error': 'AI服务调用超时'}, status=status.HTTP_408_REQUEST_TIMEOUT)
        except requests.exceptions.RequestException as e:
            return Response({'error': f'AI服务调用失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({'error': f'未知错误: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def extract_documentation(self, request):
        """使用AI提取API文档"""
        request_id = request.data.get('request_id')
        if not request_id:
            return Response({'error': '请提供请求ID'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            api_request = ApiRequest.objects.get(id=request_id)
        except ApiRequest.DoesNotExist:
            return Response({'error': '请求不存在'}, status=status.HTTP_404_NOT_FOUND)

        try:
            config = AIServiceConfig.objects.filter(
                role='doc_extractor',
                is_active=True
            ).first()

            if not config:
                return Response({'error': '未找到可用的API文档提取AI配置'}, status=status.HTTP_400_BAD_REQUEST)

            request_data = {
                'method': effective_method,
                'url': api_request.url,
                'headers': api_request.headers,
                'params': api_request.params,
                'body': api_request.body,
                'description': api_request.description
            }

            headers = {
                'Authorization': f'Bearer {config.api_key}',
                'Content-Type': 'application/json'
            }

            prompt = f"""请根据以下API请求信息，生成详细的API文档：

请求方法: {request_data['method']}
请求URL: {request_data['url']}
请求头: {json.dumps(request_data['headers'], ensure_ascii=False)}
URL参数: {json.dumps(request_data['params'], ensure_ascii=False)}
请求体: {json.dumps(request_data['body'], ensure_ascii=False)}
描述: {request_data['description']}

请生成包含以下内容的API文档：
1. 接口概述
2. 请求参数说明（包括路径参数、查询参数、请求头、请求体）
3. 响应示例
4. 错误码说明

请以Markdown格式返回文档内容。"""

            ai_data = {
                'model': config.model_name,
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': config.max_tokens,
                'temperature': config.temperature
            }

            response = requests.post(
                f"{config.base_url}/chat/completions",
                headers=headers,
                json=ai_data,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                documentation = result['choices'][0]['message']['content']
                return Response({'documentation': documentation})
            else:
                return Response({
                    'error': f'AI服务调用失败: {response.status_code}',
                    'details': response.text
                }, status=status.HTTP_400_BAD_REQUEST)

        except requests.exceptions.Timeout:
            return Response({'error': 'AI服务调用超时'}, status=status.HTTP_408_REQUEST_TIMEOUT)
        except requests.exceptions.RequestException as e:
            return Response({'error': f'AI服务调用失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({'error': f'未知错误: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
