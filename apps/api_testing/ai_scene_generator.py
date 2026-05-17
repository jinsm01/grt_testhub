# -*- coding: utf-8 -*-
"""
AI场景生成器 - 极简版 MVP
通过调用接口获取响应，使用LLM分析依赖关系，自动生成场景步骤
"""
import json
import logging
import re
from typing import Dict, Any, List, Optional
import requests

from .models import ApiRequest, Environment
from .variable_resolver import VariableResolver
from apps.requirement_analysis.models import AIModelConfig

logger = logging.getLogger(__name__)


class AISceneGenerator:
    """AI场景生成器"""

    def __init__(self, environment: Optional[Environment] = None):
        self.environment = environment
        self.variable_resolver = VariableResolver()
        self.execution_results = []

    def generate_scene(self, request_ids: List[int], business_description: str = '') -> Dict[str, Any]:
        """
        生成场景步骤

        Args:
            request_ids: 接口ID列表
            business_description: 业务描述（用户提供的自然语言描述）

        Returns:
            {
                'success': bool,
                'scene_name': str,
                'steps': List[Dict],
                'error': str
            }
        """
        try:
            # 1. 获取接口信息
            requests_info = self._get_requests_info(request_ids)
            if not requests_info:
                return {'success': False, 'error': '未找到接口信息'}

            # 2. 使用简化模式：基于接口元数据 + 业务描述（如有）生成场景
            # 避免执行接口导致超时，支持任意数量的接口
            llm_result = self._call_llm_with_description(requests_info, business_description)

            if not llm_result:
                return {'success': False, 'error': 'LLM分析失败'}

            return {
                'success': True,
                'scene_name': llm_result.get('scene_name', 'AI生成场景'),
                'steps': llm_result.get('steps', [])
            }

        except Exception as e:
            logger.error(f"AI场景生成失败: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _get_requests_info(self, request_ids: List[int]) -> List[Dict]:
        """获取接口详细信息"""
        requests_info = []
        for req_id in request_ids:
            try:
                api_request = ApiRequest.objects.get(id=req_id, is_deleted=False)
                requests_info.append({
                    'id': api_request.id,
                    'name': api_request.name,
                    'method': api_request.method,
                    'url': api_request.url,
                    'headers': api_request.headers or {},
                    'params': api_request.params or {},
                    'body': api_request.body or {}
                })
            except ApiRequest.DoesNotExist:
                logger.warning(f"接口不存在: {req_id}")
                continue
        return requests_info

    def _execute_requests(self, requests_info: List[Dict]) -> List[Dict]:
        """执行接口获取响应"""
        results = []

        # 从环境变量中获取 base URL
        base_url = ''
        if self.environment:
            logger.info(f"环境对象: {self.environment.name}, ID: {self.environment.id}")
            logger.info(f"环境变量: {self.environment.variables}")
            if self.environment.variables:
                # 支持 baseUrl 和 base_url 两种命名
                base_url_var = self.environment.variables.get('baseUrl') or self.environment.variables.get('base_url', {})
                if isinstance(base_url_var, dict):
                    base_url = base_url_var.get('currentValue', '')
                else:
                    base_url = base_url_var
                logger.info(f"获取到的 baseUrl: {base_url}")
        else:
            logger.warning("未配置环境")

        for req in requests_info:
            try:
                # 解析变量
                url = self.variable_resolver.resolve(req['url'])
                # 如果 URL 是相对路径，拼接 base URL
                if url.startswith('/'):
                    url = base_url.rstrip('/') + url

                headers = {k: self.variable_resolver.resolve(v) for k, v in req['headers'].items()}
                params = {k: self.variable_resolver.resolve(v) for k, v in req['params'].items()}
                body = self._resolve_body(req['body'])

                # 发送请求
                response = self._send_request(
                    method=req['method'],
                    url=url,
                    headers=headers,
                    params=params,
                    body=body
                )

                results.append({
                    'request_id': req['id'],
                    'request_name': req['name'],
                    'method': req['method'],
                    'url': url,
                    'request_headers': headers,
                    'request_params': params,
                    'request_body': body,
                    'response_status': response.get('status_code'),
                    'response_headers': response.get('headers', {}),
                    'response_body': response.get('body', {})
                })

            except Exception as e:
                error_msg = f"执行接口失败 {req['name']}: {str(e)}"
                logger.error(error_msg)
                # 极简版：任一接口失败则中断，返回错误信息
                raise Exception(error_msg)

        return results

    def _resolve_body(self, body: Any) -> Any:
        """解析请求体中的变量"""
        if isinstance(body, dict):
            return {k: self.variable_resolver.resolve(v) if isinstance(v, str) else v
                    for k, v in body.items()}
        elif isinstance(body, list):
            return [self.variable_resolver.resolve(item) if isinstance(item, str) else item
                    for item in body]
        elif isinstance(body, str):
            return self.variable_resolver.resolve(body)
        return body

    def _send_request(self, method: str, url: str, headers: Dict, params: Dict, body: Any, request_name: str = '') -> Dict:
        """发送HTTP请求"""
        import time
        start_time = time.time()

        # 检查 URL 是否为空或无效
        if not url or url.startswith('/'):
            raise Exception(f"当前场景未配置执行环境，请先选择环境")

        try:
            if method.upper() == 'GET':
                resp = requests.get(url, headers=headers, params=params, timeout=30)
            elif method.upper() == 'POST':
                resp = requests.post(url, headers=headers, params=params, json=body, timeout=30)
            elif method.upper() == 'PUT':
                resp = requests.put(url, headers=headers, params=params, json=body, timeout=30)
            elif method.upper() == 'DELETE':
                resp = requests.delete(url, headers=headers, params=params, timeout=30)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")

            duration = time.time() - start_time

            # 解析响应体
            try:
                response_body = resp.json()
            except:
                response_body = {'text': resp.text}

            return {
                'status_code': resp.status_code,
                'headers': dict(resp.headers),
                'body': response_body,
                'duration': round(duration, 3)
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {str(e)}")
            raise

    def _call_llm(self, execution_results: List[Dict]) -> Optional[Dict]:
        """调用LLM分析依赖关系"""
        try:
            # 构建Prompt
            prompt = self._build_prompt(execution_results)

            # 调用通义千问
            response = self._call_qwen(prompt)

            # 解析响应
            result = self._parse_llm_response(response)

            # 修正 request_id - 使用实际的接口ID
            if result and 'steps' in result:
                for i, step in enumerate(result['steps']):
                    if i < len(execution_results):
                        step['request_id'] = execution_results[i]['request_id']
                        step['request_name'] = execution_results[i]['request_name']

            return result

        except Exception as e:
            logger.error(f"LLM调用失败: {str(e)}")
            return None

    def _call_llm_with_description(self, requests_info: List[Dict], business_description: str) -> Optional[Dict]:
        """使用业务描述调用LLM生成场景（混合模式）"""
        try:
            # 构建Prompt
            prompt = self._build_prompt_with_description(requests_info, business_description)

            # 调用通义千问
            response = self._call_qwen(prompt)

            # 解析响应
            result = self._parse_llm_response(response)

            # 修正 request_id - 使用实际的接口ID
            if result and 'steps' in result:
                for i, step in enumerate(result['steps']):
                    if i < len(requests_info):
                        step['request_id'] = requests_info[i]['id']
                        step['request_name'] = requests_info[i]['name']

            return result

        except Exception as e:
            logger.error(f"LLM调用失败: {str(e)}")
            return None

    def _build_prompt_with_description(self, requests_info: List[Dict], business_description: str) -> str:
        """构建带业务描述的Prompt"""
        if business_description:
            prompt = f"""你是一个API测试场景分析专家。根据用户提供的业务描述和接口列表，生成测试场景步骤。

## 业务描述
{business_description}

## 接口列表
"""
        else:
            prompt = """你是一个API测试场景分析专家。根据接口列表，分析接口间的依赖关系，生成测试场景步骤。

## 接口列表
"""

        for i, req in enumerate(requests_info, 1):
            prompt += f"\n### 接口{i}: {req['name']} (ID: {req['id']})\n"
            prompt += f"- 方法: {req['method']}\n"
            prompt += f"- URL: {req['url']}\n"
            # 简化输出，只保留关键信息
            if req.get('headers'):
                auth_header = {k: v for k, v in req['headers'].items() if 'auth' in k.lower() or 'token' in k.lower()}
                if auth_header:
                    prompt += f"- 认证相关Header: {list(auth_header.keys())}\n"

        if business_description:
            prompt += """
## 分析任务
根据业务描述，分析：
1. 接口的执行顺序（按业务逻辑排序）
2. 哪些接口需要提取变量（如token、id等）
3. 哪些接口需要使用前面提取的变量

## 变量引用格式
- 变量提取：使用JSONPath（如 $.data.token, $.data.id）
- 变量使用：使用 ${变量名}（如 ${token}, ${userId}）
- 变量名要简洁，只包含字母、数字、下划线

## 输出要求
输出JSON格式：
{
  "scene_name": "场景名称",
  "steps": [
    {
      "step_number": 1,
      "request_id": 接口ID,
      "request_name": "接口名称",
      "extract_vars": [{"var_name": "变量名", "json_path": "JSONPath"}],
      "use_vars": [{"param": "参数位置", "value": "${变量名}"}]
    }
  ]
}

## 示例
用户描述："先登录获取token，然后创建智能体获取agentId，最后查询智能体"
输出：
{
  "scene_name": "智能体创建查询流程",
  "steps": [
    {
      "step_number": 1,
      "request_id": 1001,
      "request_name": "登录",
      "extract_vars": [{"var_name": "token", "json_path": "$.data.token"}],
      "use_vars": []
    },
    {
      "step_number": 2,
      "request_id": 1002,
      "request_name": "创建智能体",
      "extract_vars": [{"var_name": "agentId", "json_path": "$.data.id"}],
      "use_vars": [{"param": "header.Authorization", "value": "Bearer ${token}"}]
    },
    {
      "step_number": 3,
      "request_id": 1003,
      "request_name": "查询智能体",
      "extract_vars": [],
      "use_vars": [
        {"param": "header.Authorization", "value": "Bearer ${token}"},
        {"param": "params.agentId", "value": "${agentId}"}
      ]
    }
  ]
}

请直接输出JSON，不要包含其他说明。"""
        else:
            prompt += """
## 分析任务
根据接口名称和URL，智能分析：
1. 接口间的依赖关系（如登录获取token用于后续接口）
2. 哪些接口需要提取变量（如token、id等）
3. 哪些接口需要使用前面提取的变量

## 变量引用格式
- 变量提取：使用JSONPath（如 $.data.token, $.data.id）
- 变量使用：使用 ${变量名}（如 ${token}, ${userId}）
- 变量名要简洁，只包含字母、数字、下划线

## 输出要求
输出JSON格式：
{
  "scene_name": "场景名称",
  "steps": [
    {
      "step_number": 1,
      "request_id": 接口ID,
      "request_name": "接口名称",
      "extract_vars": [{"var_name": "变量名", "json_path": "JSONPath"}],
      "use_vars": [{"param": "参数位置", "value": "${变量名}"}]
    }
  ]
}

请直接输出JSON，不要包含其他说明。"""

        return prompt

    def _build_prompt(self, execution_results: List[Dict]) -> str:
        """构建LLM Prompt"""
        prompt = """你是一个API测试场景分析专家。分析给定的接口执行结果，识别接口间的数据依赖关系，生成测试场景步骤。

## 分析规则
1. 分析每个接口的请求和响应
2. 识别响应中哪些字段被后续接口的请求参数使用（如ID、Token等）
3. 确定变量提取的JSONPath和变量引用的方式

## 关键：变量引用格式
- 变量提取：使用JSONPath从响应中提取（如 $.data.id, $.data.token）
- 变量使用：使用 ${变量名} 格式引用（如 ${userId}, ${token}）
- 不要在变量名中使用特殊字符如 $ . 等

## 接口执行结果
"""

        for i, result in enumerate(execution_results, 1):
            prompt += f"\n### 接口{i}: {result['request_name']} (ID: {result['request_id']})\n"
            prompt += f"- 方法: {result['method']}\n"
            prompt += f"- URL: {result['url']}\n"
            prompt += f"- 请求参数: {json.dumps(result['request_params'], ensure_ascii=False)}\n"
            prompt += f"- 请求体: {json.dumps(result['request_body'], ensure_ascii=False)}\n"
            prompt += f"- 响应状态码: {result['response_status']}\n"
            prompt += f"- 响应体: {json.dumps(result['response_body'], ensure_ascii=False)}\n"

        prompt += """
## 依赖关系分析任务
请分析上述接口执行结果，识别：
1. 哪些接口的响应字段被后续接口使用
2. 变量应该如何命名（简洁明了，如 userId, token, orderId）
3. 变量在后续接口的哪个位置使用（header, body, params, url）

## 输出要求
请输出JSON格式，包含以下字段：
- scene_name: 场景名称（根据接口功能自动生成，如"智能体创建标注流程"）
- steps: 步骤列表，每个步骤包含：
  - step_number: 步骤序号（从1开始）
  - request_id: 接口ID（使用上面括号中的ID）
  - request_name: 接口名称
  - extract_vars: 需要提取的变量列表（从当前接口的响应中提取）
    - var_name: 变量名（简洁，如 token, userId, labelId）
    - json_path: JSONPath表达式（如 $.data.token, $.data.id）
  - use_vars: 需要使用的变量列表（在当前接口的请求中使用）
    - param: 参数位置（如 header.Authorization, body.userId, params.id）
    - value: 变量引用格式（如 Bearer ${token}, ${userId}）

## 重要提示
1. 只提取真正有意义的字段（如ID、Token、关键业务数据）
2. 变量名要简洁，不要包含特殊字符
3. 如果某个接口的请求中使用了前面接口响应的数据，一定要在 use_vars 中体现
4. 如果响应中没有需要提取的数据，extract_vars 可以为空数组
5. 如果请求中没有使用变量，use_vars 可以为空数组

## 输出示例
{
  "scene_name": "用户登录创建订单流程",
  "steps": [
    {
      "step_number": 1,
      "request_id": 101,
      "request_name": "用户登录",
      "extract_vars": [
        {"var_name": "token", "json_path": "$.data.token"},
        {"var_name": "userId", "json_path": "$.data.user.id"}
      ],
      "use_vars": []
    },
    {
      "step_number": 2,
      "request_id": 102,
      "request_name": "创建订单",
      "extract_vars": [
        {"var_name": "orderId", "json_path": "$.data.orderId"}
      ],
      "use_vars": [
        {"param": "header.Authorization", "value": "Bearer ${token}"},
        {"param": "body.userId", "value": "${userId}"}
      ]
    },
    {
      "step_number": 3,
      "request_id": 103,
      "request_name": "查询订单",
      "extract_vars": [],
      "use_vars": [
        {"param": "params.orderId", "value": "${orderId}"}
      ]
    }
  ]
}

请直接输出JSON，不要包含其他说明文字。"""

        return prompt

    def _call_qwen(self, prompt: str) -> str:
        """调用通义千问API - 使用AIModelConfig配置"""
        # 获取AI模型配置（优先使用 scene_generator 角色，否则使用任意激活的配置）
        model_config = AIModelConfig.objects.filter(
            role='scene_generator',
            is_active=True
        ).first()

        if not model_config:
            # 如果没有场景生成专用配置，尝试使用 assertion_generator 或其他激活配置
            model_config = AIModelConfig.objects.filter(
                is_active=True
            ).first()

        if not model_config:
            raise ValueError("未找到可用的AI模型配置，请先在【配置中心-AI模型配置】中添加配置")

        logger.info(f"使用AI模型配置: {model_config.name}, 模型: {model_config.model_name}")

        # 构建请求
        headers = {
            "Authorization": f"Bearer {model_config.api_key}",
            "Content-Type": "application/json"
        }

        # 构建URL（与其他AI功能保持一致）
        base_url = model_config.base_url.rstrip('/')
        if not base_url.endswith('/chat/completions'):
            version_match = re.search(r'/v(\d+)/?$', base_url)
            if version_match:
                url = f"{base_url}/chat/completions"
            else:
                url = f"{base_url}/v1/chat/completions"
        else:
            url = base_url

        logger.info(f"API请求URL: {url}")

        # 使用OpenAI兼容格式（与 requirement_analysis 中的实现一致）
        payload = {
            "model": model_config.model_name,
            "messages": [
                {"role": "system", "content": "你是一个专业的API测试场景分析助手。"},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": model_config.max_tokens or 2000,
            "temperature": model_config.temperature or 0.3,
            "top_p": model_config.top_p or 0.9,
            "stream": False
        }

        response = requests.post(url, headers=headers, json=payload, timeout=180)
        response.raise_for_status()
        result = response.json()

        # 解析响应（OpenAI兼容格式）
        return result['choices'][0]['message']['content']

    def _parse_llm_response(self, response: str) -> Optional[Dict]:
        """解析LLM响应并验证数据格式"""
        try:
            # 尝试直接解析JSON
            data = json.loads(response)
        except json.JSONDecodeError:
            # 尝试从文本中提取JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
            else:
                return None

        # 验证和清理数据
        if 'steps' in data:
            for step in data['steps']:
                # 确保 extract_vars 格式正确
                if 'extract_vars' in step:
                    for var in step['extract_vars']:
                        # 清理变量名，移除特殊字符
                        if 'var_name' in var:
                            var['var_name'] = re.sub(r'[^a-zA-Z0-9_]', '', var['var_name'])

                # 确保 use_vars 格式正确
                if 'use_vars' in step:
                    for use_var in step['use_vars']:
                        # 确保 value 使用 ${} 格式
                        if 'value' in use_var:
                            value = use_var['value']
                            # 转换 {{$...}} 或 $.N.xxx 格式为 ${xxx}
                            if '{{$' in value or '$. ' in value:
                                # 提取变量名
                                var_match = re.search(r'\{\{\$\.?([^}]+)\}\}', value)
                                if var_match:
                                    var_name = var_match.group(1).split('.')[-1]
                                    use_var['value'] = f"${{{var_name}}}"

        return data
