import json
import time
from django.utils import timezone
from .models import RequestHistory
from .variable_resolver import VariableResolver


def _extract_variables(response, extractors):
    """从响应中提取变量

    Args:
        response: HTTP 响应对象
        extractors: 变量提取规则列表

    Returns:
        dict: 提取的变量字典 {variable_name: value}
    """
    extracted = {}

    if not extractors:
        return extracted

    for extractor in extractors:
        try:
            source = extractor.get('source', 'json_body')
            json_path = extractor.get('json_path', '')
            var_name = extractor.get('variable_name') or extractor.get('name', '')

            if not var_name:
                continue

            if source == 'json_body':
                # 从 JSON 响应中提取
                try:
                    response_json = response.json()
                    from jsonpath_ng import parse
                    matches = parse(json_path).find(response_json)
                    if matches:
                        value = matches[0].value
                        extracted[var_name] = value
                except Exception as e:
                    print(f"[变量提取失败] {var_name}: {e}")
            elif source == 'header':
                # 从响应头中提取
                header_name = extractor.get('header_name', '')
                if header_name and header_name in response.headers:
                    extracted[var_name] = response.headers[header_name]

        except Exception as e:
            print(f"[变量提取错误] {extractor}: {e}")
            continue

    return extracted


def _smart_compare(actual, expected):
    """智能比较函数，处理布尔值、数字和字符串的等价比较"""
    # 如果类型相同，直接比较
    if type(actual) == type(expected):
        return actual == expected

    # 处理布尔值比较
    if isinstance(actual, bool):
        # 将期望值转换为布尔值
        if isinstance(expected, str):
            expected_lower = expected.lower()
            if expected_lower in ('true', '1', 'yes', 'on'):
                return actual is True
            elif expected_lower in ('false', '0', 'no', 'off'):
                return actual is False
    elif isinstance(expected, bool):
        # 将实际值转换为布尔值
        if isinstance(actual, str):
            actual_lower = actual.lower()
            if actual_lower in ('true', '1', 'yes', 'on'):
                return expected is True
            elif actual_lower in ('false', '0', 'no', 'off'):
                return expected is False

    # 处理数字比较
    try:
        # 尝试将两者都转为浮点数比较
        return float(actual) == float(expected)
    except (ValueError, TypeError):
        pass

    # 默认使用字符串比较（不区分大小写）
    return str(actual).lower() == str(expected).lower()


def _convert_null_strings(obj):
    """递归地将字符串 'null' 转换为 None"""
    if obj is None:
        return None
    if isinstance(obj, str) and obj.lower() == 'null':
        return None
    if isinstance(obj, dict):
        return {k: _convert_null_strings(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_null_strings(item) for item in obj]
    return obj


def _resolve_step_variable(text, step_context):
    """解析跨步骤变量引用格式: {{$.N.request.body.xxx}} 或 {{$.N.response.body.xxx}}"""
    if not isinstance(text, str) or not step_context:
        return text

    import re
    # 匹配跨步骤引用: {{$.数字.request.xxx}} 或 {{$.数字.response.xxx}}
    pattern = r'\{\{\$\.(\d+)\.(request|response)\.(body|headers|params)(?:\.(.*))?\}\}'

    def replace_step_var(match):
        step_num = int(match.group(1))
        data_type = match.group(2)  # request or response
        data_part = match.group(3)  # body, headers, or params
        json_path = match.group(4) or ''

        if step_num not in step_context:
            print(f"[步骤变量] 步骤 {step_num} 不存在于上下文中")
            return match.group(0)  # 返回原始字符串

        data_source = step_context[step_num].get(data_type)
        if not data_source:
            print(f"[步骤变量] 步骤 {step_num} 没有 {data_type} 数据")
            return match.group(0)

        # 获取数据部分 (body, headers, params)
        if data_part == 'body':
            data = data_source.get('body')
            # 如果 body 是字符串，尝试解析为 JSON
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except:
                    pass
        elif data_part == 'headers':
            data = data_source.get('headers', {})
        elif data_part == 'params':
            data = data_source.get('params', {})
        else:
            return match.group(0)

        # 使用 JSONPath 提取值
        if json_path:
            try:
                from jsonpath_ng import parse
                matches = parse(json_path).find(data)
                if matches:
                    value = matches[0].value
                    print(f"[步骤变量] 成功提取: {match.group(0)} -> {value}")
                    return str(value) if value is not None else ''
            except Exception as e:
                print(f"[步骤变量] JSONPath 提取失败: {json_path}, 错误: {e}")
                return match.group(0)
        else:
            # 没有 JSONPath，返回整个数据
            return str(data) if data is not None else ''

    return re.sub(pattern, replace_step_var, text)


def execute_assertions(response, assertions, resolver=None, step_context=None):
    """执行断言验证"""
    # 处理断言数据，将字符串 'null' 转换为 None
    assertions = _convert_null_strings(assertions)

    results = []

    for assertion in assertions:
        # 保留原始断言的所有字段
        result = dict(assertion)
        result.update({
            'passed': False,
            'actual': None,
            'error': None
        })

        try:
            assertion_type = assertion.get('type')
            expected = assertion.get('expected')

            # 第一步：处理跨步骤变量引用 {{$.N.request.body.xxx}}
            if isinstance(expected, str) and step_context:
                original_expected = expected
                expected = _resolve_step_variable(expected, step_context)
                if original_expected != expected:
                    print(f"[断言调试] 步骤变量替换: '{original_expected}' -> '{expected}'")

            # 第二步：使用 resolver 处理普通变量 {{variable_name}} 和动态函数 ${function()}
            resolver_context = resolver.context if resolver else None
            print(f"[断言调试] assertion_type={assertion_type}, expected={expected}, resolver_id={id(resolver)}, context={resolver_context}")
            if resolver and isinstance(expected, str):
                original_expected = expected
                expected = resolver.resolve(expected)
                print(f"[断言调试] 变量替换: '{original_expected}' -> '{expected}'")

            # 更新 result 中的 expected 为替换后的值
            result['expected'] = expected

            actual = None
            passed = False
            
            if assertion_type == 'status_code':
                actual = response.status_code
                passed = actual == expected
                
            elif assertion_type == 'response_time':
                # 响应时间断言在调用方处理
                actual = assertion.get('actual_time')
                passed = actual <= expected if actual else False
                
            elif assertion_type == 'contains':
                text = response.text or ''
                pattern = str(expected)
                actual = text[:200] + '...' if len(text) > 200 else text
                passed = pattern in str(text)
                
            elif assertion_type == 'json_path':
                json_path = assertion.get('json_path', '')
                expected_value = expected  # 使用替换后的 expected 值
                actual = None
                passed = False

                try:
                    # 检查响应是否为JSON格式
                    content_type = response.headers.get('content-type', '').lower()
                    if 'application/json' not in content_type:
                        raise ValueError(f"响应不是JSON格式，Content-Type: {content_type}")

                    response_json = json.loads(response.text)

                    # 检查JSONPath表达式是否为空
                    if not json_path:
                        raise ValueError("JSON路径表达式不能为空")

                    from jsonpath_ng import parse
                    matches = parse(json_path).find(response_json)
                    actual = matches[0].value if matches else None

                    # 处理特殊期望值：not_null, not_empty, null, empty
                    if expected_value is not None and isinstance(expected_value, str) and expected_value.lower() in ('not_null', 'notnull', 'not_none', 'notnone'):
                        # 检查字段存在且不为null
                        passed = actual is not None
                        result['expected_desc'] = '不为null'
                    elif expected_value is not None and isinstance(expected_value, str) and expected_value.lower() in ('not_empty', 'notempty'):
                        # 检查字段存在且不为空（非None、非空字符串、非空列表、非空字典）
                        if actual is None:
                            passed = False
                        elif isinstance(actual, str) and actual.strip() == '':
                            passed = False
                        elif isinstance(actual, (list, dict)) and len(actual) == 0:
                            passed = False
                        else:
                            passed = True
                        result['expected_desc'] = '不为空'
                    elif expected_value is None:
                        # 期望值是 None (JSON null)，检查字段是否为 null
                        passed = actual is None
                        result['expected_desc'] = '为null'
                    elif expected_value is not None and isinstance(expected_value, str) and expected_value.lower() in ('null', 'none'):
                        # 字符串 "null" 或 "none"，检查字段是否为 null
                        passed = actual is None
                        result['expected_desc'] = '为null'
                    elif expected_value is not None and isinstance(expected_value, str) and expected_value.lower() in ('empty', 'isempty'):
                        # 检查字段为空
                        if actual is None:
                            passed = True
                        elif isinstance(actual, str) and actual.strip() == '':
                            passed = True
                        elif isinstance(actual, (list, dict)) and len(actual) == 0:
                            passed = True
                        else:
                            passed = False
                        result['expected_desc'] = '为空'
                    elif expected_value is not None and isinstance(expected_value, str) and expected_value.lower() in ('exist', 'exists', '存在'):
                        # 检查字段存在（包括null值）
                        passed = len(matches) > 0
                        result['expected_desc'] = '存在'
                    else:
                        # 智能比较：处理布尔值、数字和字符串
                        passed = _smart_compare(actual, expected_value)

                    # 确保actual值被正确设置到result中
                    result['actual'] = actual
                except json.JSONDecodeError as e:
                    actual = None
                    passed = False
                    result['error'] = f"JSON解析失败: {str(e)}"
                    result['actual'] = actual
                except ImportError as e:
                    actual = None
                    passed = False
                    result['error'] = f"缺少依赖库: {str(e)}，请安装jsonpath-ng"
                    result['actual'] = actual
                except Exception as e:
                    actual = None
                    passed = False
                    result['error'] = f"执行错误: {str(e)}"
                    result['actual'] = actual
                    
            elif assertion_type == 'header':
                header_name = assertion.get('header_name', '')
                expected_value = assertion.get('expected_value')
                actual = response.headers.get(header_name)
                passed = actual == expected_value
                
            elif assertion_type == 'equals':
                actual = response.text.strip()
                passed = actual == str(expected).strip()
            
            # ==================== API Fox 断言类型支持 ====================
            elif assertion_type == 'equal':
                # 使用 json_path 提取的值进行比较
                json_path = assertion.get('json_path', '')
                expected_value = expected  # 使用替换后的 expected 值
                actual = None
                passed = False

                try:
                    response_json = json.loads(response.text)
                    from jsonpath_ng import parse
                    matches = parse(json_path).find(response_json)
                    actual = matches[0].value if matches else None
                    # 智能比较：处理布尔值、数字和字符串
                    passed = _smart_compare(actual, expected_value)
                    result['actual'] = actual
                except Exception as e:
                    result['error'] = f"JSON提取失败: {str(e)}"
                    passed = False

            elif assertion_type == 'not_equal':
                json_path = assertion.get('json_path', '')
                expected_value = expected  # 使用替换后的 expected 值
                actual = None
                passed = False

                try:
                    response_json = json.loads(response.text)
                    from jsonpath_ng import parse
                    matches = parse(json_path).find(response_json)
                    actual = matches[0].value if matches else None
                    # 智能比较：处理布尔值、数字和字符串
                    passed = not _smart_compare(actual, expected_value)
                    result['actual'] = actual
                except Exception as e:
                    result['error'] = f"JSON提取失败: {str(e)}"
                    passed = False

            elif assertion_type == 'not_empty':
                # 不为空断言
                json_path = assertion.get('json_path', '')
                actual = None
                passed = False
                
                try:
                    response_json = json.loads(response.text)
                    from jsonpath_ng import parse
                    matches = parse(json_path).find(response_json)
                    actual = matches[0].value if matches else None
                    # 检查是否不为空（None、空字符串、空列表、空字典都视为空）
                    if actual is None:
                        passed = False
                    elif isinstance(actual, str) and actual.strip() == '':
                        passed = False
                    elif isinstance(actual, (list, dict)) and len(actual) == 0:
                        passed = False
                    else:
                        passed = True
                    result['actual'] = actual
                except Exception as e:
                    result['error'] = f"JSON提取失败: {str(e)}"
                    passed = False
            
            elif assertion_type == 'empty':
                # 为空断言
                json_path = assertion.get('json_path', '')
                actual = None
                passed = False
                
                try:
                    response_json = json.loads(response.text)
                    from jsonpath_ng import parse
                    matches = parse(json_path).find(response_json)
                    actual = matches[0].value if matches else None
                    # 检查是否为空
                    if actual is None:
                        passed = True
                    elif isinstance(actual, str) and actual.strip() == '':
                        passed = True
                    elif isinstance(actual, (list, dict)) and len(actual) == 0:
                        passed = True
                    else:
                        passed = False
                    result['actual'] = actual
                except Exception as e:
                    result['error'] = f"JSON提取失败: {str(e)}"
                    passed = False
            
            elif assertion_type == 'not_contains':
                # 不包含断言
                text = response.text or ''
                pattern = str(expected)
                actual = text[:200] + '...' if len(text) > 200 else text
                passed = pattern not in str(text)
            
            elif assertion_type == 'greater_than':
                # 大于断言
                json_path = assertion.get('json_path', '')
                expected_value = expected  # 使用替换后的 expected 值
                actual = None
                passed = False
                
                try:
                    response_json = json.loads(response.text)
                    from jsonpath_ng import parse
                    matches = parse(json_path).find(response_json)
                    actual = matches[0].value if matches else None
                    # 尝试数值比较
                    try:
                        passed = float(actual) > float(expected_value)
                    except (ValueError, TypeError):
                        passed = str(actual) > str(expected_value)
                    result['actual'] = actual
                except Exception as e:
                    result['error'] = f"JSON提取失败: {str(e)}"
                    passed = False
            
            elif assertion_type == 'greater_than_or_equal':
                # 大于等于断言
                json_path = assertion.get('json_path', '')
                expected_value = expected  # 使用替换后的 expected 值
                actual = None
                passed = False
                
                try:
                    response_json = json.loads(response.text)
                    from jsonpath_ng import parse
                    matches = parse(json_path).find(response_json)
                    actual = matches[0].value if matches else None
                    try:
                        passed = float(actual) >= float(expected_value)
                    except (ValueError, TypeError):
                        passed = str(actual) >= str(expected_value)
                    result['actual'] = actual
                except Exception as e:
                    result['error'] = f"JSON提取失败: {str(e)}"
                    passed = False
            
            elif assertion_type == 'less_than':
                # 小于断言
                json_path = assertion.get('json_path', '')
                expected_value = expected  # 使用替换后的 expected 值
                actual = None
                passed = False
                
                try:
                    response_json = json.loads(response.text)
                    from jsonpath_ng import parse
                    matches = parse(json_path).find(response_json)
                    actual = matches[0].value if matches else None
                    try:
                        passed = float(actual) < float(expected_value)
                    except (ValueError, TypeError):
                        passed = str(actual) < str(expected_value)
                    result['actual'] = actual
                except Exception as e:
                    result['error'] = f"JSON提取失败: {str(e)}"
                    passed = False
            
            elif assertion_type == 'less_than_or_equal':
                # 小于等于断言
                json_path = assertion.get('json_path', '')
                expected_value = expected  # 使用替换后的 expected 值
                actual = None
                passed = False
                
                try:
                    response_json = json.loads(response.text)
                    from jsonpath_ng import parse
                    matches = parse(json_path).find(response_json)
                    actual = matches[0].value if matches else None
                    try:
                        passed = float(actual) <= float(expected_value)
                    except (ValueError, TypeError):
                        passed = str(actual) <= str(expected_value)
                    result['actual'] = actual
                except Exception as e:
                    result['error'] = f"JSON提取失败: {str(e)}"
                    passed = False
            
            elif assertion_type == 'regex_match':
                # 正则匹配断言
                json_path = assertion.get('json_path', '')
                expected_value = expected  # 使用替换后的 expected 值
                actual = None
                passed = False
                
                try:
                    response_json = json.loads(response.text)
                    from jsonpath_ng import parse
                    matches = parse(json_path).find(response_json)
                    actual = matches[0].value if matches else None
                    import re
                    pattern = str(expected_value)
                    passed = re.match(pattern, str(actual)) is not None
                    result['actual'] = actual
                except Exception as e:
                    result['error'] = f"正则匹配失败: {str(e)}"
                    passed = False
            
            elif assertion_type == 'starts_with':
                # 开头是断言
                json_path = assertion.get('json_path', '')
                expected_value = expected  # 使用替换后的 expected 值
                actual = None
                passed = False
                
                try:
                    response_json = json.loads(response.text)
                    from jsonpath_ng import parse
                    matches = parse(json_path).find(response_json)
                    actual = matches[0].value if matches else None
                    passed = str(actual).startswith(str(expected_value))
                    result['actual'] = actual
                except Exception as e:
                    result['error'] = f"JSON提取失败: {str(e)}"
                    passed = False
            
            elif assertion_type == 'ends_with':
                # 结尾是断言
                json_path = assertion.get('json_path', '')
                expected_value = expected  # 使用替换后的 expected 值
                actual = None
                passed = False
                
                try:
                    response_json = json.loads(response.text)
                    from jsonpath_ng import parse
                    matches = parse(json_path).find(response_json)
                    actual = matches[0].value if matches else None
                    passed = str(actual).endswith(str(expected_value))
                    result['actual'] = actual
                except Exception as e:
                    result['error'] = f"JSON提取失败: {str(e)}"
                    passed = False
            
            # ==================== 长度比较断言 ====================
            elif assertion_type == 'length_equal':
                json_path = assertion.get('json_path', '')
                expected_value = expected  # 使用替换后的 expected 值
                actual = None
                passed = False
                
                try:
                    response_json = json.loads(response.text)
                    from jsonpath_ng import parse
                    matches = parse(json_path).find(response_json)
                    actual = matches[0].value if matches else None
                    passed = len(str(actual)) == int(expected_value)
                    result['actual'] = f"长度: {len(str(actual))}"
                except Exception as e:
                    result['error'] = f"长度比较失败: {str(e)}"
                    passed = False
            
            elif assertion_type == 'length_greater_than':
                json_path = assertion.get('json_path', '')
                expected_value = expected  # 使用替换后的 expected 值
                actual = None
                passed = False
                
                try:
                    response_json = json.loads(response.text)
                    from jsonpath_ng import parse
                    matches = parse(json_path).find(response_json)
                    actual = matches[0].value if matches else None
                    passed = len(str(actual)) > int(expected_value)
                    result['actual'] = f"长度: {len(str(actual))}"
                except Exception as e:
                    result['error'] = f"长度比较失败: {str(e)}"
                    passed = False
            
            elif assertion_type == 'length_less_than':
                json_path = assertion.get('json_path', '')
                expected_value = expected  # 使用替换后的 expected 值
                actual = None
                passed = False
                
                try:
                    response_json = json.loads(response.text)
                    from jsonpath_ng import parse
                    matches = parse(json_path).find(response_json)
                    actual = matches[0].value if matches else None
                    passed = len(str(actual)) < int(expected_value)
                    result['actual'] = f"长度: {len(str(actual))}"
                except Exception as e:
                    result['error'] = f"长度比较失败: {str(e)}"
                    passed = False
            
            # 确保在所有情况下都设置actual值
            if 'actual' not in result or result['actual'] is None:
                result['actual'] = actual
            result['passed'] = passed

        except Exception as e:
            result['error'] = str(e)
            result['passed'] = False
        
        results.append(result)
    
    return results


def execute_test_suite(test_suite, environment, executed_by):
    """执行测试套件并返回结果"""
    from .models import TestExecution, RequestHistory
    import requests
    import time
    
    execution = None
    
    try:
        # 创建变量解析器
        resolver = VariableResolver()
        
        # 创建执行记录
        execution = TestExecution.objects.create(
            test_suite=test_suite,
            status='RUNNING',
            start_time=timezone.now(),
            executed_by=executed_by
        )
        
        # 获取套件中的请求
        suite_requests = test_suite.testsuiterequest_set.filter(enabled=True).order_by('order')

        # 统计实际请求数（排除分组类型）
        actual_request_count = sum(1 for sr in suite_requests if sr.step_type != 'group' and sr.request is not None)
        execution.total_requests = actual_request_count
        execution.save()
        
        results = []
        passed_count = 0
        failed_count = 0
        
        # 执行每个请求
        for suite_request in suite_requests:
            api_request = suite_request.request
            
            # 跳过分组类型步骤（group 只是容器，不是真正的接口请求）
            if suite_request.step_type == 'group' or api_request is None:
                continue
            
            try:
                # 解析环境变量
                variables = {}
                if environment:
                    variables.update(environment.variables)
                
                # 替换URL中的变量（先解析动态函数，再替换环境变量）
                url = _replace_variables(api_request.url, variables)
                url = resolver.resolve(url)
                
                # 如果URL是相对路径，拼接base_url
                if url.startswith('/') and environment:
                    base_url_raw = variables.get('base_url') or variables.get('baseUrl')
                    # 处理对象格式 {initialValue, currentValue, initial_value, current_value}
                    if isinstance(base_url_raw, dict):
                        base_url = str(
                            base_url_raw.get('current_value', '') or
                            base_url_raw.get('currentValue', '') or
                            base_url_raw.get('initial_value', '') or
                            base_url_raw.get('initialValue', '')
                        )
                    elif base_url_raw:
                        base_url = str(base_url_raw)
                    else:
                        base_url = ''
                    if base_url:
                        url = base_url.rstrip('/') + url
                
                # 准备请求头
                headers = {}
                if isinstance(api_request.headers, list):
                    for header_item in api_request.headers:
                        if header_item.get('enabled', True) and header_item.get('key'):
                            key = header_item['key']
                            value = _replace_variables(str(header_item.get('value', '')), variables)
                            value = resolver.resolve(value)
                            headers[key] = value
                else:
                    headers = api_request.headers.copy()
                    for key, value in headers.items():
                        headers[key] = _replace_variables(str(value), variables)
                        headers[key] = resolver.resolve(headers[key])
                
                # 准备请求参数
                params = api_request.params.copy() if api_request.params else {}
                for key, value in params.items():
                    params[key] = _replace_variables(str(value), variables)
                    params[key] = resolver.resolve(params[key])
                
                # 准备请求体
                body_data = None
                request_kwargs = {
                    'method': api_request.method,
                    'url': url,
                    'headers': headers,
                    'params': params,
                    'timeout': 30
                }
                
                if api_request.body and api_request.method in ['POST', 'PUT', 'PATCH']:
                    body_type = api_request.body.get('type', '')
                    
                    if body_type == 'json':
                        body_data = api_request.body.get('data', {})
                        body_data = _replace_variables_in_dict(body_data, variables)
                        body_data = _resolve_variables_in_dict(body_data, resolver)
                        request_kwargs['json'] = body_data
                    
                    elif body_type in ('form-data', 'formdata'):
                        # 处理 form-data 类型
                        form_items = api_request.body.get('data', [])
                        multipart_data = {}
                        has_files = False
                        
                        print(f"[DEBUG utils.py] form-data 字段数量: {len(form_items)}")
                        
                        if isinstance(form_items, list):
                            for item in form_items:
                                if isinstance(item, dict) and item.get('key'):
                                    item_key = item.get('key')
                                    item_value = item.get('value', '')
                                    item_type = item.get('type', 'string')
                                    
                                    print(f"[DEBUG utils.py] 处理字段: {item_key}={item_value}, type={item_type}")
                                    
                                    # 变量替换
                                    item_value = _replace_variables(str(item_value), variables)
                                    item_value = resolver.resolve(item_value)
                                    
                                    print(f"[DEBUG utils.py] 替换后: {item_key}={item_value}")
                                    
                                    if item_type == 'file':
                                        # 文件字段
                                        file_path = item.get('file_path')
                                        has_files = True
                                        
                                        if file_path:
                                            from django.conf import settings
                                            import os
                                            full_file_path = os.path.join(settings.MEDIA_ROOT, file_path)
                                            
                                            if os.path.exists(full_file_path):
                                                try:
                                                    with open(full_file_path, 'rb') as f:
                                                        file_content = f.read()
                                                    
                                                    file_name = os.path.basename(full_file_path)
                                                    if '_' in file_name and len(file_name.split('_')[0]) == 8:
                                                        original_name = file_name.split('_', 1)[1]
                                                    else:
                                                        original_name = file_name
                                                    
                                                    multipart_data[item_key] = (
                                                        original_name,
                                                        file_content,
                                                        item.get('content_type') or 'application/octet-stream'
                                                    )
                                                except Exception as e:
                                                    logger.error(f"读取文件失败: {e}")
                                                    multipart_data[item_key] = (item_value, b'', 'application/octet-stream')
                                            else:
                                                logger.warning(f"文件不存在: {full_file_path}")
                                                multipart_data[item_key] = (item_value, b'', 'application/octet-stream')
                                        else:
                                            multipart_data[item_key] = (item_value, b'', 'application/octet-stream')
                                    else:
                                        # 普通字段 - 使用 MultipartEncoder 格式
                                        multipart_data[item_key] = (None, str(item_value))
                        
                        print(f"[DEBUG utils.py] 最终 multipart_data: {multipart_data}")
                        print(f"[DEBUG utils.py] has_files: {has_files}")
                        
                        if has_files:
                            # 使用 MultipartEncoder
                            try:
                                from requests_toolbelt.multipart.encoder import MultipartEncoder
                                encoder = MultipartEncoder(fields=multipart_data)
                                request_kwargs['headers'] = headers.copy()
                                request_kwargs['headers']['Content-Type'] = encoder.content_type
                                request_kwargs['data'] = encoder
                            except ImportError:
                                logger.warning("requests_toolbelt 未安装，使用普通 form 数据")
                                form_dict = {}
                                for key, value in multipart_data.items():
                                    if isinstance(value, tuple):
                                        if value[0] is None:
                                            form_dict[key] = value[1]
                                        else:
                                            form_dict[key] = value[0]
                                    else:
                                        form_dict[key] = value
                                request_kwargs['data'] = form_dict
                        else:
                            # 没有文件，转换为普通 form 数据
                            form_dict = {}
                            for key, value in multipart_data.items():
                                if isinstance(value, tuple):
                                    if value[0] is None:
                                        form_dict[key] = value[1]
                                    else:
                                        form_dict[key] = value[0]
                                else:
                                    form_dict[key] = value
                            request_kwargs['data'] = form_dict
                    
                    elif body_type == 'x-www-form-urlencoded':
                        form_items = api_request.body.get('data', [])
                        form_dict = {}
                        if isinstance(form_items, list):
                            for item in form_items:
                                if isinstance(item, dict) and item.get('key'):
                                    item_value = item.get('value', '')
                                    item_value = _replace_variables(str(item_value), variables)
                                    item_value = resolver.resolve(item_value)
                                    form_dict[item['key']] = item_value
                        request_kwargs['data'] = form_dict
                    
                    elif body_type == 'raw':
                        raw_data = api_request.body.get('data', '')
                        raw_data = _replace_variables(str(raw_data), variables)
                        raw_data = resolver.resolve(raw_data)
                        request_kwargs['data'] = raw_data
                
                # 执行请求
                start_time = time.time()
                response = requests.request(**request_kwargs)
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                
                # 执行断言验证 - 优先使用套件请求的断言，如果没有则使用接口的断言
                # 强制刷新从数据库获取最新的断言数据
                suite_request.refresh_from_db()
                
                # 调试日志
                print(f"[断言来源调试] suite_request.assertions: {suite_request.assertions}")
                print(f"[断言来源调试] api_request.assertions: {api_request.assertions}")
                
                assertions = suite_request.assertions or api_request.assertions or []
                
                print(f"[断言来源调试] 最终使用的assertions: {assertions}")
                
                # 转换字符串 'null' 为 None
                assertions = _convert_null_strings(assertions)
                
                for assertion in assertions:
                    if assertion.get('type') == 'response_time':
                        assertion['actual_time'] = response_time
                
                assertions_results = execute_assertions(response, assertions, resolver)

                # 执行变量提取
                extracted_vars = _extract_variables(response, api_request.variable_extractors or [])
                # 将提取的变量保存到 resolver 上下文，供后续请求使用
                for var_name, var_value in extracted_vars.items():
                    resolver.context[var_name] = var_value
                    print(f"[变量提取] {var_name} = {var_value}")

                # 检查所有断言是否通过
                passed = True
                error_message = ''

                # 检查断言结果
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

                if passed:
                    passed_count += 1
                else:
                    failed_count += 1
                
                results.append({
                    'name': api_request.name,
                    'method': api_request.method,
                    'url': url,
                    'status_code': response.status_code,
                    'response_time': response_time,
                    'passed': passed,
                    'error': error_message,
                    'assertions_results': assertions_results
                })
                
                # 保存请求历史
                RequestHistory.objects.create(
                    request=api_request,
                    environment=environment,
                    request_data={
                        'url': url,
                        'method': api_request.method,
                        'headers': headers,
                        '极速版params': params,
                        'body': body_data
                    },
                    response_data={
                        'headers': dict(response.headers),
                        'body': response.text,
                        'json': response.json() if response.headers.get('content-type', '').startswith('application/json') else None
                    },
                    status_code=response.status_code,
                    response_time=response_time,
                    assertions_results=assertions_results,
                    executed_by=executed_by
                )
                
            except Exception as e:
                failed_count += 1
                results.append({
                    'name': api_request.name,
                    'method': api_request.method,
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
        
        return {
            'success': True,
            'execution_id': execution.id,
            'passed_count': passed_count,
            'failed_count': failed_count,
            'total_count': execution.total_requests,
            'results': results
        }

    except Exception as e:
        # 即使失败也返回 execution_id（如果已创建）
        if execution:
            execution.status = 'FAILED'
            execution.end_time = timezone.now()
            execution.save()
            return {
                'success': False,
                'execution_id': execution.id,
                'error': str(e)
            }
        return {
            'success': False,
            'error': str(e)
        }


def execute_api_request(api_request, environment, executed_by):
    """执行单个API请求并返回结果"""
    import requests
    import time
    
    try:
        # 创建变量解析器
        resolver = VariableResolver()
        
        # 解析环境变量
        variables = {}
        if environment:
            variables.update(environment.variables)
        
        # 替换URL中的变量（先解析动态函数，再替换环境变量）
        url = _replace_variables(api_request.url, variables)
        url = resolver.resolve(url)
        
        # 如果URL是相对路径，拼接base_url
        if url.startswith('/') and environment:
            base_url_raw = variables.get('base_url') or variables.get('baseUrl')
            # 处理对象格式 {initialValue, currentValue, initial_value, current_value}
            if isinstance(base_url_raw, dict):
                base_url = str(
                    base_url_raw.get('current_value', '') or
                    base_url_raw.get('currentValue', '') or
                    base_url_raw.get('initial_value', '') or
                    base_url_raw.get('initialValue', '')
                )
            elif base_url_raw:
                base_url = str(base_url_raw)
            else:
                base_url = ''
            if base_url:
                url = base_url.rstrip('/') + url
        
        # 准备请求头
        headers = {}
        if isinstance(api_request.headers, list):
            for header_item in api_request.headers:
                if header_item.get('enabled', True) and header_item.get('key'):
                    key = header_item['key']
                    value = _replace_variables(str(header_item.get('value', '')), variables)
                    value = resolver.resolve(value)
                    headers[key] = value
        else:
            headers = api_request.headers.copy()
            for key, value in headers.items():
                headers[key] = _replace_variables(str(value), variables)
                headers[key] = resolver.resolve(headers[key])
        
        # 准备请求参数
        params = api_request.params.copy() if api_request.params else {}
        for key, value in params.items():
            params[key] = _replace_variables(str(value), variables)
            params[key] = resolver.resolve(params[key])
        
        # 准备请求体
        body_data = None
        if api_request.body and api_request.method in ['POST', 'PUT', 'PATCH']:
            if api_request.body.get('type') == 'json':
                body_data = api_request.body.get('data', {})
                body_data = _replace_variables_in_dict(body_data, variables)
                body_data = _resolve_variables_in_dict(body_data, resolver)
        
        # 执行请求
        start_time = time.time()
        response = requests.request(
            method=api_request.method,
            url=url,
            headers=headers,
            params=params,
            json=body_data,
            timeout=30
        )
        end_time = time.time()
        response_time = (end_time - start_time) * 1000
        
        # 执行断言验证
        assertions = api_request.assertions or []
        for assertion in assertions:
            if assertion.get('type') == 'response_time':
                assertion['actual_time'] = response_time
        
        assertions_results = execute_assertions(response, assertions, resolver)

        # 保存请求历史
        history = RequestHistory.objects.create(
            request=api_request,
            environment=environment,
            request_data={
                'url': url,
                'method': api_request.method,
                'headers': headers,
                'params': params,
                'body': body_data
            },
            response_data={
                'headers': dict(response.headers),
                'body': response.text,
                'json': response.json() if response.headers.get('content-type', '').startswith('application/json') else None
            },
            status_code=response.status_code,
            response_time=response_time,
            assertions_results=assertions_results,
            executed_by=executed_by
        )
        
        return {
            'success': True,
            'history_id': history.id,
            'status_code': response.status_code,
            'response_time': response_time,
            'assertions_results': assertions_results,
            'response_data': {
                'headers': dict(response.headers),
                'body': response.text,
                'json': response.json() if response.headers.get('content-type', '').startswith('application/json') else None
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def _replace_variables(text, variables):
    """替换文本中的变量"""
    if not isinstance(text, str):
        return text
    
    result = text
    for key, value in (variables or {}).items():
        if isinstance(value, dict):
            replacement = str(value.get('currentValue', '') or value.get('initialValue', ''))
        else:
            replacement = str(value) if value is not None else ''
        result = result.replace(f'{{{{{key}}}}}', replacement)
    return result

def _replace_variables_in_dict(data, variables):
    """递归替换字典中的变量"""
    if isinstance(data, dict):
        return {k: _replace_variables_in_dict(v, variables) for k, v in data.items()}
    elif isinstance(data, list):
        return [_replace_variables_in_dict(item, variables) for item in data]
    elif isinstance(data, str):
        return _replace_variables(data, variables)
    else:
        return data

def _resolve_variables_in_dict(data, resolver):
    """递归解析字典中的动态函数占位符"""
    if isinstance(data, dict):
        return {k: _resolve_variables_in_dict(v, resolver) for k, v in data.items()}
    elif isinstance(data, list):
        return [_resolve_variables_in_dict(item, resolver) for item in data]
    elif isinstance(data, str):
        return resolver.resolve(data)
    else:
        return data
