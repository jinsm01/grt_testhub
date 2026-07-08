# -*- coding: utf-8 -*-
"""
场景执行引擎 - 支持跨步骤引用、循环、条件
"""
import json
import time
from typing import Dict, Any, List, Optional
from django.utils import timezone
from django.db import transaction

from .context import ScenarioContext
from ..models import (
    AutomationScenario, ScenarioStep, ScenarioExecution,
    ApiRequest, Environment, RequestHistory
)
from ..utils import (
    execute_assertions
)


class StepResult:
    """步骤执行结果"""
    def __init__(self):
        self.step_number: int = 0
        self.step_name: str = ''
        self.status: str = 'pending'  # pending, running, passed, failed, skipped
        self.duration: float = 0.0
        self.request: Dict = {}
        self.response: Dict = {}
        self.variables: Dict = {}
        self.assertions: List[Dict] = []
        self.error_message: str = ''


class ScenarioExecutor:
    """
    自动化场景执行器
    
    执行流程：
    1. 初始化上下文，注册所有步骤
    2. 执行场景前置脚本
    3. 按顺序执行步骤：
       a. 解析变量
       b. 发送请求
       c. 执行后置脚本
       d. 提取变量
       e. 执行断言
    4. 执行场景后置脚本
    5. 返回执行结果
    """
    
    def __init__(self, scenario: AutomationScenario, 
                 environment: Optional[Environment] = None,
                 executed_by=None):
        self.scenario = scenario
        self.environment = environment or scenario.environment
        self.executed_by = executed_by
        self.context = ScenarioContext()
        self.execution_record: Optional[ScenarioExecution] = None
        self.step_results: List[StepResult] = []
        
        # 加载环境变量
        if self.environment:
            self.context.environment_variables = self.environment.variables or {}
        
        # 加载全局变量
        self.context.global_variables = self.scenario.global_variables or {}
    
    def execute(self) -> Dict[str, Any]:
        """
        执行整个场景
        
        Returns:
            {
                'success': bool,
                'execution_id': int,
                'total_steps': int,
                'passed_steps': int,
                'failed_steps': int,
                'duration': float,
                'step_results': List[StepResult],
                'error': str
            }
        """
        try:
            # 1. 获取所有启用的步骤
            steps = list(self.scenario.steps.filter(
                override_enabled=True
            ).order_by('step_number'))
            
            # 2. 创建执行记录
            with transaction.atomic():
                self.execution_record = ScenarioExecution.objects.create(
                    scenario=self.scenario,
                    status='running',
                    start_time=timezone.now(),
                    executed_by=self.executed_by,
                    total_steps=len(steps)
                )
            
            # 3. 注册所有步骤到上下文
            for step in steps:
                self.context.register_step(
                    step_number=step.step_number,
                    alias=step.step_alias,
                    name=step.name
                )
            
            # 4. 执行场景前置脚本
            if self.scenario.pre_script:
                self._execute_pre_script()
            
            # 5. 按顺序执行步骤
            passed = 0
            failed = 0
            
            for step in steps:
                result = self._execute_step(step)
                self.step_results.append(result)
                
                if result.status == 'passed':
                    passed += 1
                elif result.status == 'failed':
                    failed += 1
                    # 失败是否继续？先继续所有步骤
                    # TODO: 添加 "失败停止" 选项
            
            # 6. 执行场景后置脚本
            if self.scenario.post_script:
                self._execute_post_script()
            
            # 7. 更新执行记录
            end_time = timezone.now()
            duration = (end_time - self.execution_record.start_time).total_seconds()
            
            self.execution_record.status = 'completed' if failed == 0 else 'failed'
            self.execution_record.end_time = end_time
            self.execution_record.passed_steps = passed
            self.execution_record.failed_steps = failed
            self.execution_record.execution_context = self.context.to_dict()
            self.execution_record.step_results = [self._step_result_to_dict(r) for r in self.step_results]
            self.execution_record.save()
            
            return {
                'success': failed == 0,
                'execution_id': self.execution_record.id,
                'total_steps': len(steps),
                'passed_steps': passed,
                'failed_steps': failed,
                'duration': duration,
                'step_results': [self._step_result_to_dict(r) for r in self.step_results],
                'error': ''
            }
            
        except Exception as e:
            # 执行异常
            if self.execution_record:
                self.execution_record.status = 'failed'
                self.execution_record.end_time = timezone.now()
                self.execution_record.save()
            
            return {
                'success': False,
                'execution_id': self.execution_record.id if self.execution_record else None,
                'total_steps': 0,
                'passed_steps': 0,
                'failed_steps': 0,
                'duration': 0,
                'step_results': [],
                'error': str(e)
            }
    
    def _execute_step(self, step: ScenarioStep) -> StepResult:
        """
        执行单个步骤
        """
        result = StepResult()
        result.step_number = step.step_number
        result.step_name = step.name
        result.status = 'running'
        
        # 设置当前步骤（用于 prev 引用）
        self.context.set_current_step(step.step_number)
        
        start_time = time.time()
        
        try:
            if step.step_type == 'request':
                self._execute_request_step(step, result)
            elif step.step_type == 'group':
                # 分组只是容器，不需要执行
                result.status = 'passed'
            elif step.step_type == 'wait':
                # 等待步骤
                wait_time = step.control_config.get('wait_time', 1)
                time.sleep(wait_time)
                result.status = 'passed'
            elif step.step_type == 'script':
                # 自定义脚本步骤
                self._execute_script_step(step, result)
            elif step.step_type == 'scenario_ref':
                # 引用场景步骤
                self._execute_scenario_ref_step(step, result)
            else:
                # 暂不支持其他类型
                result.status = 'skipped'
                result.error_message = f'不支持的步骤类型: {step.step_type}'
        
        except Exception as e:
            result.status = 'failed'
            result.error_message = str(e)
        
        result.duration = time.time() - start_time
        
        return result
    
    def _execute_request_step(self, step: ScenarioStep, result: StepResult):
        """执行接口请求步骤"""
        # 1. 获取请求配置（包含覆盖）
        request_data = step.get_effective_request_data()
        
        # 2. 解析变量引用
        resolved_data = self.context.resolve_in_dict(request_data)
        result.request = resolved_data
        
        # 记录请求到上下文
        self.context.set_step_request(
            step.step_number,
            resolved_data.get('method', 'GET'),
            resolved_data.get('url', ''),
            resolved_data.get('headers', {}),
            resolved_data.get('body', {}),
            resolved_data.get('params', {})
        )
        
        # 3. 执行前置脚本
        if step.pre_script:
            self._execute_step_pre_script(step, result)
        
        # 4. 发送请求
        response_data = self._send_request(resolved_data)
        result.response = response_data
        
        # 记录响应到上下文
        self.context.set_step_response(
            step.step_number,
            response_data.get('status_code', 0),
            response_data.get('headers', {}),
            response_data.get('body', {}),
            response_data.get('response_time', 0)
        )
        
        # 5. 执行后置脚本
        if step.post_script:
            self._execute_step_post_script(step, result)
        
        # 6. 提取变量
        self._extract_variables(step, result)
        
        # 7. 执行断言
        self._execute_assertions(step, result)
        
        # 8. 记录请求历史
        self._record_request_history(step, result, resolved_data, response_data)
    
    def _record_request_history(self, step: ScenarioStep, result: StepResult, 
                                request_data: Dict, response_data: Dict):
        """记录请求历史"""
        try:
            # 获取请求体和响应体
            body = request_data.get('body')
            response_body = response_data.get('body', '')
            
            # 尝试解析JSON
            response_json = None
            if isinstance(response_body, str):
                try:
                    response_json = json.loads(response_body)
                except:
                    pass
            elif isinstance(response_body, dict):
                response_json = response_body
            
            # 使用 response_data 中的完整 URL（已拼接 base_url）
            full_url = response_data.get('url', request_data.get('url', ''))
            RequestHistory.objects.create(
                request=step.api_request,
                environment=self.environment,
                request_data={
                    'url': full_url,
                    'method': request_data.get('method', 'GET'),
                    'headers': request_data.get('headers', {}),
                    'params': request_data.get('params', {}),
                    'body': body
                },
                response_data={
                    'headers': response_data.get('headers', {}),
                    'body': response_body,
                    'json': response_json
                },
                status_code=response_data.get('status_code', 0),
                response_time=response_data.get('response_time', 0),
                assertions_results=result.assertions,
                executed_by=self.executed_by
            )
        except Exception as e:
            # 记录历史失败不应该影响主流程
            print(f"记录请求历史失败: {e}")
    
    def _send_request(self, request_data: Dict) -> Dict:
        """发送 HTTP 请求"""
        import requests
        import time

        method = request_data.get('method', 'GET')
        url = request_data.get('url', '')
        headers = request_data.get('headers', {}) or {}
        body = request_data.get('body', {})
        params = request_data.get('params', {}) or {}

        # 处理新的 body 格式 {type: 'json', data: {...}}
        if isinstance(body, dict) and 'type' in body and 'data' in body:
            body = body['data']

        # 拼接 base_url（如果 URL 是相对路径）
        if url.startswith('/') and self.environment:
            env_vars = self.environment.variables or {}
            base_url_raw = env_vars.get('base_url') or env_vars.get('baseUrl')
            if base_url_raw:
                # 处理对象格式 {initialValue, currentValue, initial_value, current_value}
                if isinstance(base_url_raw, dict):
                    base_url = str(
                        base_url_raw.get('current_value', '') or
                        base_url_raw.get('currentValue', '') or
                        base_url_raw.get('initial_value', '') or
                        base_url_raw.get('initialValue', '')
                    )
                else:
                    base_url = str(base_url_raw)
                if base_url:
                    url = base_url.rstrip('/') + url

        # 转换 headers 格式
        headers_dict = {}
        if isinstance(headers, list):
            for h in headers:
                if isinstance(h, dict) and h.get('key'):
                    headers_dict[h['key']] = h.get('value', '')
        elif isinstance(headers, dict):
            headers_dict = headers

        # 转换 params 格式
        params_dict = {}
        if isinstance(params, list):
            for p in params:
                if isinstance(p, dict) and p.get('key'):
                    params_dict[p['key']] = p.get('value', '')
        elif isinstance(params, dict):
            params_dict = params

        start_time = time.time()

        try:
            # 准备请求参数
            request_kwargs = {
                'url': url,
                'headers': headers_dict,
                'params': params_dict if params_dict else None,
                'timeout': 30
            }

            # 处理请求体
            if method.upper() in ['POST', 'PUT', 'PATCH'] and body:
                if isinstance(body, dict):
                    if headers_dict.get('Content-Type') == 'application/x-www-form-urlencoded':
                        request_kwargs['data'] = body
                    else:
                        request_kwargs['json'] = body
                else:
                    request_kwargs['data'] = body

            response = requests.request(method.upper(), **request_kwargs)
            response_time = time.time() - start_time

            # 解析响应体
            try:
                response_body = response.json()
            except:
                response_body = response.text

            return {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'body': response_body,
                'response_time': round(response_time, 3),
                'url': url  # 返回完整的 URL
            }

        except requests.exceptions.Timeout:
            return {
                'status_code': 0,
                'headers': {},
                'body': {'error': '请求超时'},
                'response_time': time.time() - start_time,
                'error': '请求超时'
            }
        except requests.exceptions.RequestException as e:
            return {
                'status_code': 0,
                'headers': {},
                'body': {'error': str(e)},
                'response_time': time.time() - start_time,
                'error': str(e)
            }
        except Exception as e:
            return {
                'status_code': 0,
                'headers': {},
                'body': {'error': str(e)},
                'response_time': time.time() - start_time,
                'error': str(e)
            }
    
    def _extract_variables(self, step: ScenarioStep, result: StepResult):
        """从响应中提取变量"""
        extractors = step.get_effective_extractors()
        
        for extractor in extractors:
            var_name = extractor.get('variable_name')
            json_path = extractor.get('json_path')
            
            if not var_name or not json_path:
                continue
            
            try:
                from jsonpath_ng import parse
                
                response_body = result.response.get('body', {})
                if isinstance(response_body, str):
                    try:
                        response_body = json.loads(response_body)
                    except:
                        continue
                
                jsonpath_expr = parse(json_path)
                matches = jsonpath_expr.find(response_body)
                
                if matches:
                    value = matches[0].value
                    self.context.set_step_variable(step.step_number, var_name, value)
                    result.variables[var_name] = value
            except Exception as e:
                # 提取失败不中断执行
                pass
    
    def _execute_assertions(self, step: ScenarioStep, result: StepResult):
        """执行断言"""
        assertions = step.get_effective_assertions()
        all_passed = True
        
        for assertion in assertions:
            assertion_result = self._execute_single_assertion(assertion, result.response)
            result.assertions.append(assertion_result)
            
            if not assertion_result['passed']:
                all_passed = False
        
        result.status = 'passed' if all_passed else 'failed'
    
    def _execute_single_assertion(self, assertion: Dict, response: Dict) -> Dict:
        """执行单个断言"""
        assertion_type = assertion.get('type', 'status_code')
        expected = assertion.get('expected', '')
        actual = ''
        
        try:
            if assertion_type == 'status_code':
                actual = str(response.get('status_code', ''))
            elif assertion_type == 'json_path':
                json_path = assertion.get('json_path', '')
                body = response.get('body', {})
                
                if isinstance(body, str):
                    try:
                        body = json.loads(body)
                    except:
                        body = {}
                
                from jsonpath_ng import parse
                jsonpath_expr = parse(json_path)
                matches = jsonpath_expr.find(body)
                actual = str(matches[0].value) if matches else ''
            elif assertion_type == 'header':
                header_name = assertion.get('header_name', '')
                actual = str(response.get('headers', {}).get(header_name, ''))
            elif assertion_type == 'contains':
                # 包含文本
                body_str = json.dumps(response.get('body', {}))
                actual = assertion.get('contains', '') in body_str
                passed = bool(actual) == bool(expected)
                return {
                    'type': assertion_type,
                    'expected': expected,
                    'actual': actual,
                    'passed': passed,
                    'message': '' if passed else f'包含检查失败'
                }
            else:
                actual = ''
            
            # 比较
            operator = assertion.get('operator', 'equals')
            passed = self._compare_values(actual, expected, operator)
            
            return {
                'type': assertion_type,
                'expected': expected,
                'actual': actual,
                'passed': passed,
                'message': '' if passed else f'期望 {operator} {expected}，实际 {actual}'
            }
            
        except Exception as e:
            return {
                'type': assertion_type,
                'expected': expected,
                'actual': str(e),
                'passed': False,
                'message': str(e)
            }
    
    def _compare_values(self, actual: str, expected: str, operator: str) -> bool:
        """比较值"""
        if operator == 'equals':
            return actual == expected
        elif operator == 'not_equals':
            return actual != expected
        elif operator == 'contains':
            return expected in actual
        elif operator == 'not_contains':
            return expected not in actual
        elif operator == 'gt':
            try:
                return float(actual) > float(expected)
            except:
                return False
        elif operator == 'gte':
            try:
                return float(actual) >= float(expected)
            except:
                return False
        elif operator == 'lt':
            try:
                return float(actual) < float(expected)
            except:
                return False
        elif operator == 'lte':
            try:
                return float(actual) <= float(expected)
            except:
                return False
        return False
    
    def _execute_pre_script(self):
        """执行场景前置脚本（简化版，实际可扩展）"""
        # TODO: 实现脚本执行（可选择 Python/JS 解释器）
        pass
    
    def _execute_post_script(self):
        """执行场景后置脚本"""
        pass
    
    def _execute_step_pre_script(self, step: ScenarioStep, result: StepResult):
        """执行步骤前置脚本"""
        pass
    
    def _execute_step_post_script(self, step: ScenarioStep, result: StepResult):
        """执行步骤后置脚本"""
        pass
    
    def _execute_script_step(self, step: ScenarioStep, result: StepResult):
        """执行自定义脚本步骤"""
        # TODO: 实现脚本步骤
        result.status = 'skipped'
        result.error_message = '脚本步骤暂未实现'

    def _execute_scenario_ref_step(self, step: ScenarioStep, result: StepResult):
        """
        执行场景引用步骤

        功能：
        1. 递归执行被引用的场景
        2. 变量传递（继承父场景变量、导出变量到父场景）
        3. 记录子场景执行结果

        变量作用域规则：
        - 被引用场景可以访问父场景的全局变量
        - 被引用场景的变量提取会合并到父场景（可选）
        - 支持指定要传递的变量列表
        """
        from ..models import ScenarioExecution

        if not step.referenced_scenario:
            result.status = 'failed'
            result.error_message = '未指定引用的场景'
            return

        referenced_scenario = step.referenced_scenario
        ref_config = step.scenario_ref_config or {}

        try:
            # 1. 准备传递给子场景的变量
            inherited_vars = {}

            # 是否继承父场景的所有全局变量
            if ref_config.get('inherit_variables', True):
                inherited_vars.update(self.context.global_variables)

            # 特定变量覆盖
            pass_variables = ref_config.get('pass_variables', {})
            if isinstance(pass_variables, dict):
                # 解析变量值（支持变量引用）
                for var_name, var_value in pass_variables.items():
                    inherited_vars[var_name] = self.context.resolve_variables(var_value)

            # 2. 创建子执行器
            child_executor = ScenarioExecutor(
                scenario=referenced_scenario,
                environment=self.environment,
                executed_by=self.executed_by
            )

            # 3. 将继承的变量设置到子场景上下文
            child_executor.context.global_variables.update(inherited_vars)

            # 4. 创建子执行记录（关联到父执行记录）
            child_execution = ScenarioExecution.objects.create(
                scenario=referenced_scenario,
                status='running',
                start_time=timezone.now(),
                executed_by=self.executed_by,
                parent_execution=self.execution_record,
                parent_step_number=step.step_number,
                inherited_variables=inherited_vars
            )
            child_executor.execution_record = child_execution

            # 5. 执行子场景
            child_result = child_executor._execute_nested()

            # 6. 处理子场景导出的变量
            exported_vars = {}
            export_config = ref_config.get('export_variables', [])

            if export_config == 'all':
                # 导出所有子场景变量
                exported_vars = child_executor.context.global_variables.copy()
            elif isinstance(export_config, list):
                # 导出指定变量
                for var_name in export_config:
                    if var_name in child_executor.context.global_variables:
                        exported_vars[var_name] = child_executor.context.global_variables[var_name]

            # 合并到父场景上下文
            self.context.global_variables.update(exported_vars)

            # 更新子执行记录
            child_execution.exported_variables = exported_vars
            child_execution.save()

            # 7. 设置当前步骤结果
            result.status = 'passed' if child_result['success'] else 'failed'
            result.variables = exported_vars
            result.response = {
                'child_execution_id': child_execution.id,
                'child_scenario_name': referenced_scenario.name,
                'child_total_steps': child_result.get('total_steps', 0),
                'child_passed_steps': child_result.get('passed_steps', 0),
                'child_failed_steps': child_result.get('failed_steps', 0),
                'exported_variables': exported_vars
            }

        except Exception as e:
            result.status = 'failed'
            result.error_message = f'场景引用执行失败: {str(e)}'

    def _execute_nested(self) -> Dict[str, Any]:
        """
        嵌套执行场景（供场景引用使用）
        与 execute() 类似，但不创建新的顶级执行记录
        """
        try:
            steps = list(self.scenario.steps.filter(
                override_enabled=True
            ).order_by('step_number'))

            # 注册所有步骤到上下文
            for step in steps:
                self.context.register_step(
                    step_number=step.step_number,
                    alias=step.step_alias,
                    name=step.name
                )

            # 执行场景前置脚本
            if self.scenario.pre_script:
                self._execute_pre_script()

            # 按顺序执行步骤
            passed = 0
            failed = 0
            step_results = []

            for step in steps:
                result = self._execute_step(step)
                step_results.append(result)

                if result.status == 'passed':
                    passed += 1
                elif result.status == 'failed':
                    failed += 1

            # 执行场景后置脚本
            if self.scenario.post_script:
                self._execute_post_script()

            # 更新执行记录
            end_time = timezone.now()
            duration = (end_time - self.execution_record.start_time).total_seconds()

            self.execution_record.status = 'completed' if failed == 0 else 'failed'
            self.execution_record.end_time = end_time
            self.execution_record.passed_steps = passed
            self.execution_record.failed_steps = failed
            self.execution_record.total_steps = len(steps)
            self.execution_record.execution_context = self.context.to_dict()
            self.execution_record.step_results = [self._step_result_to_dict(r) for r in step_results]
            self.execution_record.save()

            return {
                'success': failed == 0,
                'execution_id': self.execution_record.id,
                'total_steps': len(steps),
                'passed_steps': passed,
                'failed_steps': failed,
                'duration': duration,
                'step_results': step_results,
                'error': ''
            }

        except Exception as e:
            if self.execution_record:
                self.execution_record.status = 'failed'
                self.execution_record.end_time = timezone.now()
                self.execution_record.save()

            return {
                'success': False,
                'execution_id': self.execution_record.id if self.execution_record else None,
                'total_steps': 0,
                'passed_steps': 0,
                'failed_steps': 0,
                'duration': 0,
                'step_results': [],
                'error': str(e)
            }

    def _step_result_to_dict(self, result: StepResult) -> Dict:
        """转换步骤结果为字典"""
        return {
            'step_number': result.step_number,
            'step_name': result.step_name,
            'status': result.status,
            'duration': result.duration,
            'request': result.request,
            'response': result.response,
            'variables': result.variables,
            'assertions': result.assertions,
            'error_message': result.error_message
        }
