# -*- coding: utf-8 -*-
"""
场景执行上下文 - 管理所有步骤数据，支持跨步骤引用
"""
import json
import re
from typing import Any, Dict, Optional, List, Union
from jsonpath_ng import parse


class StepData:
    """单步骤数据封装"""
    
    def __init__(self, step_number: int, alias: str, name: str):
        self.step_number = step_number
        self.alias = alias
        self.name = name
        self.request: Optional[Dict] = None
        self.response: Optional[Dict] = None
        self.variables: Dict[str, Any] = {}  # 步骤级变量
    
    def to_dict(self) -> Dict:
        return {
            'step_number': self.step_number,
            'alias': self.alias,
            'name': self.name,
            'request': self.request,
            'response': self.response,
            'variables': self.variables
        }


class ScenarioContext:
    """
    场景执行上下文 - 管理所有步骤数据
    支持 Apifox 语法的跨步骤引用：{{$.N.request.body.xxx}}, {{$.alias.response.body.xxx}}
    """
    
    def __init__(self):
        self.steps: Dict[int, StepData] = {}  # step_number -> StepData
        self.step_aliases: Dict[str, int] = {}  # alias -> step_number
        self.global_variables: Dict[str, Any] = {}
        self.environment_variables: Dict[str, Any] = {}
        self._current_step: int = 0  # 当前正在执行的步骤
    
    def register_step(self, step_number: int, alias: str, name: str) -> StepData:
        """注册步骤"""
        step_data = StepData(step_number, alias, name)
        self.steps[step_number] = step_data
        if alias:
            self.step_aliases[alias] = step_number
        return step_data
    
    def set_current_step(self, step_number: int):
        """设置当前步骤（用于 prev 引用）"""
        self._current_step = step_number
    
    def set_step_request(self, step_number: int, method: str, url: str, 
                         headers: dict, body: Any, params: dict):
        """记录步骤请求数据"""
        if step_number in self.steps:
            self.steps[step_number].request = {
                'method': method,
                'url': url,
                'headers': headers,
                'body': body,
                'params': params
            }
    
    def set_step_response(self, step_number: int, status_code: int,
                          headers: dict, body: Any, response_time: float):
        """记录步骤响应数据"""
        if step_number in self.steps:
            self.steps[step_number].response = {
                'status_code': status_code,
                'headers': headers,
                'body': body,
                'response_time': response_time
            }
    
    def set_step_variable(self, step_number: int, var_name: str, value: Any):
        """设置步骤级变量"""
        if step_number in self.steps:
            self.steps[step_number].variables[var_name] = value
    
    def set_global_variable(self, var_name: str, value: Any):
        """设置全局变量"""
        self.global_variables[var_name] = value
    
    def get_variable(self, var_name: str) -> Any:
        """获取变量（优先从全局，然后环境）"""
        if var_name in self.global_variables:
            return self.global_variables[var_name]
        if var_name in self.environment_variables:
            return self.environment_variables[var_name]
        return None
    
    def extract(self, reference: str) -> Any:
        """
        从引用路径提取数据
        
        支持的引用格式：
        - $.1.request.body.xxx           # 数字编号 + request
        - $.1.response.body.xxx          # 数字编号 + response  
        - $.login.response.body.token    # 别名 + response
        - $.prev.request.body.xxx        # 上一步
        - $.1.variables.token            # 步骤变量
        
        Args:
            reference: 引用路径，如 "$.1.response.body.data.id"
        
        Returns:
            提取的数据，找不到返回 None
        """
        # 解析引用路径
        # 格式: $.{step_ref}.{data_type}.{json_path}
        # step_ref: 数字、别名或 prev
        # data_type: request, response, variables
        match = re.match(r'^\$\.(\w+)\.(request|response|variables)(?:\.(.+))?$', reference)
        if not match:
            return None
        
        step_ref = match.group(1)  # 1, login, prev
        data_type = match.group(2)  # request, response, variables
        json_path = match.group(3) or ''  # body.xxx, status_code, etc.
        
        # 解析步骤引用
        step_number = self._resolve_step_reference(step_ref)
        if step_number is None or step_number not in self.steps:
            return None
        
        step_data = self.steps[step_number]
        
        # 获取数据源
        if data_type == 'variables':
            data_source = step_data.variables
        elif data_type == 'request':
            data_source = step_data.request
        else:  # response
            data_source = step_data.response
        
        if data_source is None:
            return None
        
        # 如果没有进一步的路径，返回整个数据源
        if not json_path:
            return data_source
        
        # 解析具体路径
        return self._extract_by_path(data_source, json_path)
    
    def _resolve_step_reference(self, step_ref: str) -> Optional[int]:
        """解析步骤引用为步骤编号"""
        if step_ref == 'prev':
            # 上一步
            return self._current_step - 1 if self._current_step > 1 else None
        elif step_ref.isdigit():
            # 数字编号
            return int(step_ref)
        else:
            # 别名
            return self.step_aliases.get(step_ref)
    
    def _extract_by_path(self, data_source: Dict, json_path: str) -> Any:
        """
        根据路径从数据源提取数据
        
        支持的路径格式：
        - body.xxx.yyy        # JSON body 字段
        - body.data[0].id     # 数组索引
        - status_code         # 直接字段
        - headers.Content-Type # Headers
        """
        # 处理 body.xxx 路径
        if json_path.startswith('body.'):
            body_path = json_path[5:]  # 去掉 "body."
            body_data = data_source.get('body')
            
            if body_data is None:
                return None
            
            # 如果 body 是字符串，尝试解析为 JSON
            if isinstance(body_data, str):
                try:
                    body_data = json.loads(body_data)
                except:
                    return body_data
            
            # 如果没有进一步路径，返回整个 body
            if not body_path:
                return body_data
            
            # 使用 JSONPath 提取
            try:
                jsonpath_expr = parse(body_path)
                matches = jsonpath_expr.find(body_data)
                return matches[0].value if matches else None
            except:
                # JSONPath 失败，尝试简单点号路径
                return self._get_nested_value(body_data, body_path)
        
        # 处理 headers.xxx
        elif json_path.startswith('headers.'):
            header_name = json_path[8:]
            headers = data_source.get('headers', {})
            return headers.get(header_name)
        
        # 其他直接字段（如 status_code, response_time）
        else:
            return data_source.get(json_path)
    
    def _get_nested_value(self, data: Any, path: str) -> Any:
        """
        使用点号路径获取嵌套值
        例如: "data[0].name" -> data['data'][0]['name']
        """
        parts = self._parse_path_parts(path)
        result = data
        
        for part in parts:
            if result is None:
                return None
            
            if isinstance(result, dict):
                result = result.get(part)
            elif isinstance(result, list):
                try:
                    index = int(part)
                    result = result[index] if 0 <= index < len(result) else None
                except (ValueError, IndexError):
                    return None
            else:
                return None
        
        return result
    
    def _parse_path_parts(self, path: str) -> List[str]:
        """解析路径为部分列表，支持数组索引"""
        # 将 "data[0].name" 解析为 ["data", "0", "name"]
        parts = []
        current = ''
        i = 0
        
        while i < len(path):
            char = path[i]
            if char == '.':
                if current:
                    parts.append(current)
                    current = ''
            elif char == '[':
                if current:
                    parts.append(current)
                    current = ''
                # 读取索引直到 ]
                i += 1
                index_str = ''
                while i < len(path) and path[i] != ']':
                    index_str += path[i]
                    i += 1
                parts.append(index_str)
            else:
                current += char
            i += 1
        
        if current:
            parts.append(current)
        
        return parts
    
    def resolve_variables(self, text: Any) -> Any:
        """
        解析文本中的所有变量引用
        
        支持：
        - {{$.1.response.body.xxx}}     # 跨步骤引用
        - {{$.login.response.body.xxx}} # 别名引用
        - {{$.prev.request.body.xxx}}   # 上一步引用
        - {{$globals.varName}}          # 全局变量
        - {{$env.varName}}              # 环境变量
        - {{varName}}                   # 变量（优先全局，再环境）
        - {{$function()}}               # 动态函数（保留原样）
        """
        if not isinstance(text, str):
            return text
        
        result = text
        
        # 1. 解析跨步骤引用 {{$.N.xxx}} 或 {{$.alias.xxx}}
        # 使用 [^\}]+ 匹配除了 } 之外的任何字符，避免匹配到变量结束符
        step_ref_pattern = r'\{\{\$\.(\w+)\.(request|response|variables)(?:\.([^\}]+))?\}\}'
        
        def replace_step_ref(match):
            step_ref = match.group(1)
            data_type = match.group(2)
            json_path = match.group(3) or ''
            
            full_path = f'$.{step_ref}.{data_type}'
            if json_path:
                full_path += f'.{json_path}'
            
            value = self.extract(full_path)
            
            if value is None:
                return match.group(0)  # 保持原样
            
            # 转换为字符串
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False)
            return str(value)
        
        result = re.sub(step_ref_pattern, replace_step_ref, result)
        
        # 2. 解析全局变量 {{$globals.xxx}}
        global_pattern = r'\{\{\$globals\.([\w_]+)\}\}'
        
        def replace_global(match):
            var_name = match.group(1)
            value = self.global_variables.get(var_name)
            return str(value) if value is not None else match.group(0)
        
        result = re.sub(global_pattern, replace_global, result)
        
        # 3. 解析环境变量 {{$env.xxx}}
        env_pattern = r'\{\{\$env\.([\w_]+)\}\}'
        
        def replace_env(match):
            var_name = match.group(1)
            value = self.environment_variables.get(var_name)
            return str(value) if value is not None else match.group(0)
        
        result = re.sub(env_pattern, replace_env, result)
        
        # 4. 解析普通变量 {{varName}}（不包括 $ 开头的特殊变量）
        var_pattern = r'\{\{([\w_][\w_]*)\}\}'
        
        def replace_var(match):
            var_name = match.group(1)
            value = self.get_variable(var_name)
            return str(value) if value is not None else match.group(0)
        
        result = re.sub(var_pattern, replace_var, result)
        
        return result
    
    def resolve_in_dict(self, data: Any) -> Any:
        """递归解析字典/列表中的所有变量"""
        if isinstance(data, dict):
            return {k: self.resolve_in_dict(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.resolve_in_dict(item) for item in data]
        elif isinstance(data, str):
            return self.resolve_variables(data)
        return data
    
    def to_dict(self) -> Dict:
        """导出为字典（用于存储执行记录）"""
        return {
            'steps': {k: v.to_dict() for k, v in self.steps.items()},
            'global_variables': self.global_variables,
            'environment_variables': self.environment_variables
        }
