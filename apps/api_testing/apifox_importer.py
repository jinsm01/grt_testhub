# -*- coding: utf-8 -*-
"""
API Fox 完整导入器 - 100% 兼容
支持 API Fox CLI JSON 格式导入
"""
import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union
from django.db import transaction

from apps.api_testing.models import ApiProject, ApiCollection, ApiRequest, TestSuite, TestSuiteRequest, Environment, AutomationScenario, ScenarioStep
from apps.users.models import User
from .apifox_function_mapper import ApifoxVariableResolver, validate_apifox_syntax


class ApifoxImportError(Exception):
    """API Fox 导入错误"""
    pass


class ApifoxCliImporter:
    """
    API Fox CLI JSON 文件导入器
    
    支持功能：
    1. 完整场景导入（包含所有请求、测试步骤）
    2. 100% 变量函数兼容（使用数据工厂）
    3. 环境变量提取（可选）
    4. 前置/后置脚本转换
    5. 变量提取规则转换
    """
    
    def __init__(self, user: User, project: ApiProject):
        self.user = user
        self.project = project
        self.resolver = ApifoxVariableResolver()
        self.import_stats = {
            'collections_created': 0,
            'requests_created': 0,
            'suites_created': 0,
            'variables_converted': 0,
            'warnings': [],
            'issues_by_request': {}  # 按请求分组的问题列表
        }
        self._apifox_to_request_index = {}  # Apifox全局索引 -> TestHub请求索引的映射
        self._structured_steps = []
    
    def _add_request_issue(self, request_name: str, issue_type: str, issue_detail: str, action: str = ""):
        """添加请求相关的问题到统计信息
        
        Args:
            request_name: 请求名称
            issue_type: 问题类型（如"断言跳过"、"变量引用"等）
            issue_detail: 问题详情
            action: 建议操作
        """
        if request_name not in self.import_stats['issues_by_request']:
            self.import_stats['issues_by_request'][request_name] = []
        
        issue = {
            'type': issue_type,
            'detail': issue_detail,
            'action': action or "请手动检查并修正"
        }
        self.import_stats['issues_by_request'][request_name].append(issue)
        
        # 同时添加到普通警告列表（用于兼容旧版UI）
        warning_text = f"【{request_name}】{issue_type}: {issue_detail}"
        if action:
            warning_text += f"（{action}）"
        self.import_stats['warnings'].append(warning_text)
    
    def import_from_file(self, file_path: str, 
                         import_env: bool = False,
                         target_collection: ApiCollection = None) -> Dict[str, Any]:
        """
        从 API Fox CLI JSON 文件导入
        
        Args:
            file_path: JSON 文件路径
            import_env: 是否导入环境变量
            target_collection: 指定导入到哪个集合（可选）
        
        Returns:
            导入结果统计
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            raise ApifoxImportError(f"文件读取失败: {str(e)}")
        
        return self.import_from_data(data, import_env, target_collection)
    
    def import_from_data(self, data: Dict[str, Any],
                        import_env: bool = False,
                        target_collection: ApiCollection = None) -> Dict[str, Any]:
        """从数据字典导入"""
        # 重置计数器和映射
        self._apifox_to_request_index = {}
        self._structured_steps = []

        with transaction.atomic():
            # 1. 预处理 - 提取环境变量
            if import_env:
                self._extract_environment(data)

            # 2. 创建或获取集合
            collection = target_collection or self._create_collection(data)
            
            # 3. 如果导入到现有合集，先清空该合集的现有接口
            if target_collection:
                deleted_count = self._clear_collection_requests(target_collection)
                if deleted_count > 0:
                    self.import_stats['warnings'].append(f'已清空合集中原有的 {deleted_count} 个接口')

            # 3. 递归处理所有 items，创建请求（同时构建索引映射）
            items = data.get('item', [])
            print(f"DEBUG - 原始 items 数量: {len(items)}")

            # 处理 wrapper 结构：如果 items[0] 有嵌套的 item 数组，提取它
            if items and isinstance(items[0], dict) and 'item' in items[0]:
                print(f"DEBUG - 检测到 wrapper 结构，提取嵌套 items")
                items = items[0].get('item', [])
                print(f"DEBUG - 提取后 items 数量: {len(items)}")

            # 统计原始请求数量
            def count_raw_requests(items_list):
                count = 0
                for item in items_list:
                    if 'request' in item:
                        count += 1
                    if 'item' in item:
                        count += count_raw_requests(item['item'])
                return count

            raw_request_count = count_raw_requests(items)
            print(f"DEBUG - 原始请求数量（递归统计）: {raw_request_count}")

            # 重置索引映射
            self._apifox_to_request_index = {}
            structured_steps = self._process_items_structured(items, collection, parent_path='')

            print(f"DEBUG - 创建的请求数: {self.import_stats['requests_created']}")
            print(f"DEBUG - 索引映射: {self._apifox_to_request_index}")
            print(f"DEBUG - structured_steps 数量: {len(structured_steps)}")

            # 5. 提取所有请求（用于创建测试套件）
            requests = self._extract_requests_from_steps(structured_steps)

            # 6. 统一转换所有请求中的变量
            self._convert_requests_variables(structured_steps)

            # 7. 创建测试套件（支持分组结构）
            suite = self._create_test_suite(data, collection, requests, structured_steps)

            # 8. 创建自动化场景（带层级结构）
            scenario = self._create_automation_scenario(data, collection, structured_steps, suite)

            # 构建导入的请求列表（包含层级结构）
            imported_requests_list = self._build_imported_requests_list(structured_steps)

            # 构建返回结果
            result = {
                'success': True,
                'collection_id': collection.id,
                'collection_name': collection.name,
                'suite_id': suite.id if suite else None,
                'suite_name': suite.name if suite else None,
                'scenario_id': scenario.id if scenario else None,
                'stats': {
                    'collections_created': self.import_stats['collections_created'],
                    'requests_created': self.import_stats['requests_created'],
                    'suites_created': self.import_stats['suites_created'],
                    'variables_converted': self.import_stats['variables_converted'],
                    'warnings_count': len(self.import_stats['warnings'])
                },
                'warnings': self.import_stats['warnings'],
                'issues_by_request': self.import_stats['issues_by_request'],
                'imported_requests': imported_requests_list
            }

            return result
    
    def _build_index_mapping(self, items: List[Dict]):
        """第一遍遍历：建立 Apifox 全局索引到 TestHub 请求索引的映射

        Apifox 使用全局索引（包含 group），TestHub 只给请求分配索引。
        对于 group，我们记录其内部的第一个请求索引，用于映射引用。

        支持两种结构：
        1. Apifox 平铺结构（带 scopeType start/end 标记）
        2. 传统嵌套结构（带 item 数组的 group）
        """
        # 检测结构类型
        has_scope_markers = any(
            item.get('type') == 'group' and item.get('metaInfo', {}).get('scopeType') in ['start', 'end']
            for item in items
        )

        if has_scope_markers:
            self._build_flat_index_mapping(items)
        else:
            self._build_nested_index_mapping(items)

    def _build_flat_index_mapping(self, items: List[Dict]):
        """处理 Apifox 平铺结构的索引映射"""
        apifox_global_idx = 0
        request_index_counter = 0
        group_stack = []  # 用于跟踪当前打开的分组及其第一个请求索引

        for item in items:
            item_type = item.get('type', '')
            meta = item.get('metaInfo', {})
            scope_type = meta.get('scopeType', '')

            if item_type == 'group':
                if scope_type == 'start':
                    # 分组开始，压入栈，等待第一个请求
                    group_stack.append({
                        'apifox_idx': apifox_global_idx,
                        'first_request_testhub_idx': None
                    })
                elif scope_type == 'end':
                    # 分组结束，弹出栈
                    if group_stack:
                        group_info = group_stack.pop()
                        # 如果该分组有请求，建立映射
                        if group_info['first_request_testhub_idx'] is not None:
                            self._apifox_to_request_index[group_info['apifox_idx']] = group_info['first_request_testhub_idx']
                            print(f"DEBUG - group Apifox[{group_info['apifox_idx']}] 映射到第一个请求 TestHub order={group_info['first_request_testhub_idx']}")

                apifox_global_idx += 1

            elif 'request' in item:
                # 这是一个请求
                request_index_counter += 1
                self._apifox_to_request_index[apifox_global_idx] = request_index_counter

                # 如果有打开的分组，记录第一个请求
                for group_info in group_stack:
                    if group_info['first_request_testhub_idx'] is None:
                        group_info['first_request_testhub_idx'] = request_index_counter

                print(f"DEBUG - 映射 Apifox[{apifox_global_idx}] -> TestHub order={request_index_counter} [REQ] {item.get('name', '')}")
                apifox_global_idx += 1
            else:
                # 其他类型
                print(f"DEBUG - 映射 Apifox[{apifox_global_idx}] -> [OTHER] {item.get('name', '')}")
                apifox_global_idx += 1

    def _build_nested_index_mapping(self, items: List[Dict]):
        """处理传统嵌套结构的索引映射"""
        apifox_global_idx = 0
        request_index_counter = 0
        group_first_request_map = {}  # group索引 -> 其内部第一个请求的索引

        def traverse(items, parent_group_idx=None):
            nonlocal apifox_global_idx, request_index_counter
            for item in items:
                if 'request' in item:
                    # 这是一个请求
                    request_index_counter += 1
                    self._apifox_to_request_index[apifox_global_idx] = request_index_counter

                    # 如果有父 group，记录这是该 group 的第一个请求
                    if parent_group_idx is not None and parent_group_idx not in group_first_request_map:
                        group_first_request_map[parent_group_idx] = apifox_global_idx

                    print(f"DEBUG - 映射 Apifox[{apifox_global_idx}] -> TestHub order={request_index_counter} [REQ] {item.get('name', '')}")
                    apifox_global_idx += 1

                elif 'item' in item:
                    # 这是一个 group，递归处理
                    current_group_idx = apifox_global_idx
                    print(f"DEBUG - 映射 Apifox[{apifox_global_idx}] -> [GROUP] {item.get('name', '')}")
                    apifox_global_idx += 1
                    traverse(item['item'], parent_group_idx=current_group_idx)
                else:
                    # 其他类型
                    print(f"DEBUG - 映射 Apifox[{apifox_global_idx}] -> [OTHER] {item.get('name', '')}")
                    apifox_global_idx += 1

        traverse(items)

        # 第二遍：为 group 索引建立映射（映射到其内部第一个请求）
        for group_idx, first_request_idx in group_first_request_map.items():
            if first_request_idx in self._apifox_to_request_index:
                # group 映射到其内部第一个请求的 TestHub 索引
                self._apifox_to_request_index[group_idx] = self._apifox_to_request_index[first_request_idx]
                print(f"DEBUG - group Apifox[{group_idx}] 映射到第一个请求 TestHub order={self._apifox_to_request_index[first_request_idx]}")
    
    def _create_collection(self, data: Dict[str, Any]) -> ApiCollection:
        """创建 API 集合"""
        name = data.get('info', {}).get('name', f"API Fox Import {datetime.now().strftime('%Y%m%d')}")

        collection = ApiCollection.objects.create(
            project=self.project,
            name=name,
            description=data.get('info', {}).get('description', ''),
            created_by=self.user
        )
        self.import_stats['collections_created'] += 1
        return collection

    def _clear_collection_requests(self, collection: ApiCollection) -> int:
        """清空合集中的所有接口（包括已软删除的）

        Args:
            collection: 目标合集

        Returns:
            删除的接口数量
        """
        # 获取该合集下的所有接口（包括已软删除的）
        requests = ApiRequest.all_objects.filter(collection=collection)
        count = requests.count()

        if count > 0:
            # 删除相关测试套件中的引用
            TestSuiteRequest.objects.filter(request__collection=collection).delete()
            # 删除自动化场景步骤中的引用
            ScenarioStep.objects.filter(api_request__collection=collection).delete()
            # 物理删除接口（避免软删除接口占用唯一约束）
            for req in requests:
                req.hard_delete()

        return count

    def _process_items_structured(self, items: List[Dict], collection: ApiCollection,
                                   parent_path: str = '') -> List[Dict]:
        """
        处理 items，支持两种结构：
        1. Apifox 平铺结构（带 scopeType start/end 标记）
        2. 传统嵌套结构（带 item 数组的 group）

        返回结构化步骤信息（支持分组层级）
        """
        # 首先检测结构类型
        has_scope_markers = any(
            item.get('type') == 'group' and item.get('metaInfo', {}).get('scopeType') in ['start', 'end']
            for item in items
        )

        print(f"DEBUG - has_scope_markers: {has_scope_markers}")

        if has_scope_markers:
            # 使用平铺结构转换
            print(f"DEBUG - 使用平铺结构处理")
            return self._process_flat_items(items, collection, parent_path)
        else:
            # 使用传统嵌套结构处理
            print(f"DEBUG - 使用嵌套结构处理")
            return self._process_nested_items(items, collection, parent_path)

    def _process_flat_items(self, items: List[Dict], collection: ApiCollection,
                           parent_path: str = '') -> List[Dict]:
        """
        处理 Apifox 平铺结构（带 scopeType start/end 标记）
        将平铺结构转换为嵌套结构
        """
        result = []
        stack = []  # 用于跟踪当前的分组层级 [(group_step_info, group_item), ...]
        apifox_global_idx = [0]  # 使用列表作为可变引用
        request_counter = [0]    # 请求计数器

        for item in items:
            item_type = item.get('type', '')
            meta = item.get('metaInfo', {})
            scope_type = meta.get('scopeType', '')
            item_name = item.get('name', '')
            full_path = f"{parent_path}/{item_name}" if parent_path else item_name

            if item_type == 'group':
                if scope_type == 'start':
                    # 分组开始
                    group_name = meta.get('extraData', {}).get('name', '')
                    group_step = {
                        'type': 'group',
                        'name': group_name,
                        'path': full_path,
                        'item_data': item,
                        'children': [],
                        'apifox_index': apifox_global_idx[0]
                    }

                    # 添加到当前层级的 children 中
                    if stack:
                        stack[-1][0]['children'].append(group_step)
                    else:
                        result.append(group_step)

                    # 将新分组压入栈，同时记录第一个请求索引（用于变量映射）
                    stack.append((group_step, item, apifox_global_idx[0], None))  # (step, item, apifox_idx, first_request_testhub_idx)

                elif scope_type == 'end':
                    # 分组结束，弹出栈顶
                    if stack:
                        group_step, group_item, group_apifox_idx, first_request_idx = stack.pop()
                        
                        print(f"DEBUG - 分组结束: {group_step['name']}, children数量: {len(group_step['children'])}")
                        
                        # 建立 group 到其第一个请求的映射（用于变量引用转换）
                        if first_request_idx is not None:
                            self._apifox_to_request_index[group_apifox_idx] = first_request_idx
                            print(f"DEBUG - group Apifox[{group_apifox_idx}] 映射到第一个请求 TestHub order={first_request_idx}")

                        # 处理空名称的顶层分组：将其 children 提升到父级或顶层
                        if not group_step['name'] or group_step['name'].strip() == '':
                            if not stack:  # 是顶层分组
                                # 从 result 中移除该空分组
                                result = [
                                    x for x in result
                                    if x.get('apifox_index') != group_step['apifox_index']
                                ]
                                # 将其 children 提升到顶层
                                if group_step['children']:
                                    result.extend(group_step['children'])
                            else:  # 有父分组
                                # 从父分组的 children 中移除
                                parent_children = stack[-1][0]['children']
                                stack[-1][0]['children'] = [
                                    x for x in parent_children
                                    if x.get('apifox_index') != group_step['apifox_index']
                                ]
                                # 将其 children 提升到父分组
                                if group_step['children']:
                                    stack[-1][0]['children'].extend(group_step['children'])
                        # 清理空的 children（非空名称分组）
                        elif not group_step['children']:
                            if stack:
                                stack[-1][0]['children'] = [
                                    x for x in stack[-1][0]['children']
                                    if x.get('apifox_index') != group_step['apifox_index']
                                ]
                            else:
                                result = [
                                    x for x in result
                                    if x.get('apifox_index') != group_step['apifox_index']
                                ]

                apifox_global_idx[0] += 1

            elif 'request' in item:
                # 这是一个请求
                print(f"DEBUG - 处理请求: {item_name}, index: {apifox_global_idx[0]}")
                request = self._create_request(item, collection, full_path, request_counter[0])

                if request:
                    request_counter[0] += 1
                    testhub_order = request_counter[0]
                    print(f"DEBUG - 请求创建成功: {item_name}, order: {testhub_order}")

                    # 更新映射（用于变量引用转换）
                    self._apifox_to_request_index[apifox_global_idx[0]] = testhub_order

                    # 如果有父分组，记录这是该分组的第一个请求（用于 group 变量映射）
                    for i, stack_item in enumerate(stack):
                        if len(stack_item) >= 4 and stack_item[3] is None:
                            # 更新第一个请求索引
                            stack[i] = (stack_item[0], stack_item[1], stack_item[2], testhub_order)

                    step_info = {
                        'type': 'request',
                        'name': item_name,
                        'index': testhub_order - 1,
                        'order': testhub_order,
                        'apifox_index': apifox_global_idx[0],
                        'path': full_path,
                        'request': request,
                        'item_data': item,
                        'children': []
                    }

                    # 添加到当前层级的 children 中
                    if stack:
                        stack[-1][0]['children'].append(step_info)
                    else:
                        result.append(step_info)
                else:
                    print(f"DEBUG - 请求创建失败: {item_name}")

                apifox_global_idx[0] += 1
            else:
                # 其他类型，只增加索引
                apifox_global_idx[0] += 1

        return result

    def _process_nested_items(self, items: List[Dict], collection: ApiCollection,
                              parent_path: str = '') -> List[Dict]:
        """递归处理传统嵌套结构 items"""
        steps = []
        apifox_global_idx = [0]  # 使用列表作为可变引用
        request_counter = [0]    # 请求计数器

        def process_single_item(item, current_path, level=0):
            """处理单个 item，返回 step_info 或 None"""
            nonlocal apifox_global_idx, request_counter
            item_name = item.get('name', '')
            full_path = f"{current_path}/{item_name}" if current_path else item_name

            if 'request' in item:
                # 这是一个请求
                print(f"DEBUG - [嵌套] 处理请求: {item_name}, index: {apifox_global_idx[0]}")
                request = self._create_request(item, collection, full_path, request_counter[0])

                if request:
                    request_counter[0] += 1
                    testhub_order = request_counter[0]
                    print(f"DEBUG - [嵌套] 请求创建成功: {item_name}, order: {testhub_order}")

                    # 更新映射（用于变量引用转换）
                    self._apifox_to_request_index[apifox_global_idx[0]] = testhub_order

                    step_info = {
                        'type': 'request',
                        'name': item_name,
                        'index': testhub_order - 1,
                        'order': testhub_order,
                        'apifox_index': apifox_global_idx[0],
                        'path': full_path,
                        'request': request,
                        'item_data': item,
                        'children': []
                    }
                    apifox_global_idx[0] += 1
                    return step_info
                else:
                    print(f"DEBUG - [嵌套] 请求创建失败: {item_name}")
                apifox_global_idx[0] += 1

            elif 'item' in item:
                # 这是一个 group/folder
                apifox_global_idx[0] += 1

                # 递归处理所有子项
                children = []
                for child_item in item['item']:
                    child_step = process_single_item(child_item, full_path, level + 1)
                    if child_step:
                        children.append(child_step)

                # 只有当 group 有子项时才创建 group step
                if children:
                    step_info = {
                        'type': 'group',
                        'name': item_name,
                        'path': full_path,
                        'item_data': item,
                        'children': children
                    }
                    return step_info
            else:
                # 其他类型，只增加索引
                apifox_global_idx[0] += 1

            return None

        # 处理顶层 items
        for item in items:
            step = process_single_item(item, parent_path)
            if step:
                steps.append(step)

        return steps
    
    def _extract_requests_from_steps(self, steps: List[Dict]) -> List[ApiRequest]:
        """从结构化步骤中递归提取所有请求"""
        requests = []
        for step in steps:
            if step['type'] == 'request' and step.get('request'):
                requests.append(step['request'])
            # 递归提取 children 中的请求
            if step.get('children'):
                requests.extend(self._extract_requests_from_steps(step['children']))
        return requests

    def _build_imported_requests_list(self, steps: List[Dict]) -> List[Dict]:
        """构建导入的请求列表（包含层级结构）用于前端展示"""
        result = []
        for step in steps:
            if step['type'] == 'request' and step.get('request'):
                request = step['request']
                request_info = {
                    'id': request.id,
                    'name': request.name,
                    'method': request.method,
                    'url': request.url,
                    'type': 'request'
                }
                result.append(request_info)
            elif step['type'] == 'group':
                group_info = {
                    'name': step['name'],
                    'type': 'group',
                    'children': self._build_imported_requests_list(step.get('children', []))
                }
                # 只添加有子项的分组
                if group_info['children']:
                    result.append(group_info)
        return result

    def _convert_requests_variables(self, steps: List[Dict]):
        """统一转换所有请求中的变量（递归处理 children）"""
        print(f"DEBUG - 索引映射表: {self._apifox_to_request_index}")
        
        for step in steps:
            if step['type'] == 'request' and step.get('request'):
                request = step['request']
                current_order = step.get('order', 0)
                updated = False
                
                # 转换 URL 中的变量，并检测向前引用
                if request.url:
                    print(f"DEBUG - 转换URL变量: 请求'{request.name}'")
                    print(f"DEBUG -   原始URL: {request.url}")
                    request.url, url_warning = self._convert_step_reference_with_warning(request.url, current_order)
                    print(f"DEBUG -   转换后URL: {request.url}")
                    if url_warning:
                        self._add_request_issue(
                            request.name, 
                            "URL变量引用问题", 
                            url_warning,
                            "请手动检查URL中的变量引用"
                        )
                        print(f"WARNING - URL向前引用: 请求'{request.name}' - {url_warning}")
                    request.url = self._convert_variables_with_context(request.url)
                    print(f"DEBUG -   最终URL: {request.url}")
                    updated = True
                
                # 转换 Headers 中的变量
                if request.headers:
                    new_headers = {}
                    for k, v in request.headers.items():
                        converted_v, header_warning = self._convert_step_reference_with_warning(v, current_order)
                        if header_warning:
                            self._add_request_issue(
                                request.name,
                                "Header变量引用问题",
                                f"Header '{k}': {header_warning}",
                                "请手动检查Header中的变量引用"
                            )
                        new_headers[k] = self._convert_variables_with_context(converted_v)
                    request.headers = new_headers
                    updated = True
                
                # 转换 Body 中的变量，并检测向前引用
                if request.body:
                    print(f"DEBUG - [_convert_requests_variables] 请求'{request.name}' 的 body: {request.body}")
                    if isinstance(request.body, dict):
                        if request.body.get('type') == 'json':
                            # JSON body 的 data 可能是 dict 或字符串，需要递归处理
                            body_data = request.body['data']
                            print(f"DEBUG - [_convert_requests_variables] body_data 类型: {type(body_data)}, 值: {body_data}")
                            # 创建一个新的 body 字典，确保 Django 能检测到变化
                            new_body = dict(request.body)
                            if isinstance(body_data, str):
                                body_data, body_warning = self._convert_step_reference_with_warning(body_data, current_order)
                                if body_warning:
                                    self._add_request_issue(
                                        request.name,
                                        "Body变量引用问题",
                                        body_warning,
                                        "请手动检查请求体中的变量引用"
                                    )
                                    print(f"WARNING - Body向前引用: 请求'{request.name}' - {body_warning}")
                                new_body['data'] = self._convert_variables_with_context(body_data)
                            else:
                                # dict 或 list，递归处理其中的字符串
                                new_body['data'] = self._deep_convert_body(body_data, request.name, current_order)
                            request.body = new_body
                            print(f"DEBUG - [_convert_requests_variables] 转换后的 body: {request.body}")
                            updated = True
                        elif request.body.get('type') == 'raw' and isinstance(request.body.get('data'), str):
                            body_data = request.body['data']
                            body_data, body_warning = self._convert_step_reference_with_warning(body_data, current_order)
                            if body_warning:
                                self._add_request_issue(
                                    request.name,
                                    "Body变量引用问题",
                                    body_warning,
                                    "请手动检查请求体中的变量引用"
                                )
                            new_body = dict(request.body)
                            new_body['data'] = self._convert_variables_with_context(body_data)
                            request.body = new_body
                            updated = True
                    elif isinstance(request.body, str):
                        body_data = request.body
                        body_data, body_warning = self._convert_step_reference_with_warning(body_data, current_order)
                        if body_warning:
                            self._add_request_issue(
                                request.name,
                                "Body变量引用问题",
                                body_warning,
                                "请手动检查请求体中的变量引用"
                            )
                        request.body = self._convert_variables_with_context(body_data)
                        updated = True
                
                # 转换断言中的跨步骤变量引用
                if request.assertions:
                    assertions = request.assertions if isinstance(request.assertions, list) else json.loads(request.assertions)
                    print(f"DEBUG - 处理请求 '{request.name}' 的断言, assertions={assertions}")
                    forward_ref_assertions = []
                    
                    for assertion in assertions:
                        has_forward_ref = False
                        assertion_name = assertion.get('name', '未命名断言')
                        
                        # 辅助函数：将 ${...} 格式转换为 {{...}} 格式（仅用于断言字段）
                        def convert_assertion_value(value):
                            if not isinstance(value, str):
                                return value
                            # 将 ${$.N.xxx} 或 ${$N.xxx} 转换为 {{$.N.xxx}}
                            # 支持 ${$.N.xxx}、${$N.xxx}、${.N.xxx} 等格式
                            original = value
                            result = re.sub(r'\$\{(\$[^}]+)\}', r'{{\1}}', value)
                            if original != result:
                                print(f"DEBUG - 断言值格式转换: '{original}' -> '{result}'")
                            return result
                        
                        # 转换所有字段，同时检测是否存在向前引用
                        print(f"DEBUG - 处理断言 '{assertion_name}' (current_order={current_order})")
                        
                        if 'expected' in assertion:
                            original = assertion['expected']
                            expected_value = convert_assertion_value(assertion['expected'])
                            print(f"DEBUG -   expected 原始值: '{original}' -> 格式转换后: '{expected_value}'")
                            expected_value, warning = self._convert_step_reference_with_warning(expected_value, current_order)
                            print(f"DEBUG -   expected 索引映射后: '{expected_value}'")
                            if warning:
                                has_forward_ref = True
                            assertion['expected'] = self._convert_variables_with_context(expected_value)
                            print(f"DEBUG -   expected 最终值: '{assertion['expected']}'")
                        
                        if 'expected_value' in assertion:
                            expected_val = convert_assertion_value(assertion['expected_value'])
                            expected_val, warning = self._convert_step_reference_with_warning(expected_val, current_order)
                            if warning:
                                has_forward_ref = True
                            assertion['expected_value'] = self._convert_variables_with_context(expected_val)
                        if 'expected_display' in assertion:
                            expected_disp = convert_assertion_value(assertion['expected_display'])
                            expected_disp, warning = self._convert_step_reference_with_warning(expected_disp, current_order)
                            if warning:
                                has_forward_ref = True
                            assertion['expected_display'] = self._convert_variables_with_context(expected_disp)
                        
                        # 记录存在向前引用的断言
                        if has_forward_ref:
                            forward_ref_assertions.append(assertion_name)
                            print(f"WARNING - 发现向前引用断言: 请求'{request.name}' - '{assertion_name}'")
                    
                    # 报告存在向前引用的断言（已导入但可能执行失败）
                    if forward_ref_assertions:
                        self._add_request_issue(
                            request.name,
                            f"向前引用警告（{len(forward_ref_assertions)}个断言）",
                            f"以下断言引用了后续步骤的数据: {', '.join(forward_ref_assertions)}",
                            "已导入但执行时可能失败，请检查执行顺序或手动调整"
                        )
                        print(f"INFO - 请求'{request.name}'共发现{len(forward_ref_assertions)}个向前引用的断言")
                    
                    request.assertions = assertions  # 保留所有断言（包括向前引用的）
                    print(f"DEBUG - 请求 '{request.name}' 断言已更新: {assertions}")
                    updated = True
                
                # 注意：提取器的 json_path 是普通的 JSON Path（如 $.data[0].id）
                # 用于从当前步骤的响应中提取数据，不需要进行跨步骤引用转换
                # 跨步骤引用应该只在 variable_name 或其他字段中出现
                # 因此这里不需要转换 json_path
                pass
                
                # 保存更新
                if updated:
                    request.save()
            
            # 递归处理 children
            if step.get('children'):
                self._convert_requests_variables(step['children'])
    
    def _deep_convert_body(self, data, request_name: str, current_order: int):
        """递归处理 body 中的 dict/list，转换所有字符串中的变量"""
        if isinstance(data, dict):
            return {k: self._deep_convert_body(v, request_name, current_order) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._deep_convert_body(item, request_name, current_order) for item in data]
        elif isinstance(data, str):
            print(f"DEBUG - [_deep_convert_body] 处理字符串: {data}")
            # 检测向前引用
            converted, warning = self._convert_step_reference_with_warning(data, current_order)
            if warning:
                self._add_request_issue(
                    request_name,
                    "Body变量引用问题",
                    warning,
                    "请手动检查请求体中的变量引用"
                )
            # 转换变量语法
            result = self._convert_variables_with_context(converted)
            print(f"DEBUG - [_deep_convert_body] 转换结果: {result}")
            return result
        else:
            return data
    
    def _convert_variables_with_context(self, text: str) -> str:
        """转换 API Fox 变量语法到 TestHub 语法
        
        使用 _apifox_to_request_index 映射表转换索引
        支持:
        - {{$...}} 格式 (Postman/Apifox 风格)
        - ${...} 格式 (JMeter/Apifox 动态变量风格)
        """
        if not isinstance(text, str):
            return text
        
        print(f"DEBUG - [_convert_variables_with_context] 输入: {text}")
        
        # 第一步：处理 ${...} 格式的 Apifox 动态变量
        text = self._convert_apifox_dollar_variables(text)
        
        print(f"DEBUG - [_convert_variables_with_context] 第一步后: {text}")
        
        # 第二步：处理 {{$...}} 格式
        def replace_func(match):
            func_expr = match.group(1).strip()
            
            # 处理跨步骤变量引用，如 {{$.9.request.body.xxx}} 或 {{$9.request.body.xxx}}
            parts = func_expr.split('.')
            
            # 检查是否为跨步骤引用格式：$.N.xxx 或 N.xxx（N为数字或*通配符）
            if len(parts) >= 2:
                # 情况1: $.N.xxx（parts[0]为空字符串，parts[1]为数字或*）
                # 情况2: N.xxx（parts[0]为数字或*）
                apifox_idx = None
                is_wildcard = False
                
                if parts[0] == '' and len(parts) >= 3:
                    # 格式: $.N.xxx，检查 parts[1] 是否为数字或 *
                    if parts[1].isdigit():
                        apifox_idx = int(parts[1])
                    elif parts[1] == '*':
                        is_wildcard = True
                    
                    # 保持原有的点号格式，只替换索引
                    if apifox_idx is not None and apifox_idx in self._apifox_to_request_index:
                        testhub_order = self._apifox_to_request_index[apifox_idx]
                        parts[1] = str(testhub_order)
                        return '{{$' + '.'.join(parts) + '}}'
                    elif is_wildcard:
                        # * 通配符保留原样，由调用方处理
                        return match.group(0)
                        
                elif parts[0].isdigit() or parts[0] == '*':
                    # 格式: N.xxx（Apifox格式，需要转换为 $.N.xxx）
                    if parts[0].isdigit():
                        apifox_idx = int(parts[0])
                        if apifox_idx in self._apifox_to_request_index:
                            testhub_order = self._apifox_to_request_index[apifox_idx]
                            parts[0] = str(testhub_order)
                            # 转换为 TestHub 格式：$.N.xxx
                            return '{{$.' + '.'.join(parts) + '}}'
                    elif parts[0] == '*':
                        # * 通配符保留原样，由调用方处理
                        return match.group(0)
                
                if apifox_idx is not None and apifox_idx not in self._apifox_to_request_index:
                    print(f"警告: 找不到 Apifox 索引 {apifox_idx} 的映射")
                    return match.group(0)
            
            # 处理动态函数（不区分大小写）
            if '(' in func_expr:
                func_name = func_expr[:func_expr.index('(')].lower()  # 转为小写
                args_str = func_expr[func_expr.index('(')+1:func_expr.rindex(')')]
                
                if func_name == 'string.alphanumeric':
                    length = 10
                    if 'length=' in args_str.lower():  # 参数名也转为小写
                        try:
                            length = int(args_str.lower().split('length=')[1].split(',')[0].strip())
                        except:
                            pass
                    return f'${{random_string({length}, "alphanumeric", 1)}}'
                elif func_name == 'timestamp':
                    return f'${{timestamp()}}'
                elif func_name == 'uuid':
                    return f'${{uuid()}}'
                else:
                    return f'${{{func_expr}}}'
            else:
                # 处理没有括号的动态变量，如 {{$date.timestamp}}
                # 需要调用 _convert_apifox_dollar_variables 来转换
                converted = self._convert_apifox_dollar_variables(f'${{{func_expr}}}')
                return converted
        
        pattern = r'\{\{\$(.+?)\}\}'
        result = re.sub(pattern, replace_func, text, flags=re.DOTALL)
        print(f"DEBUG - [_convert_variables_with_context] 最终输出: {result}")
        return result
    
    def _convert_apifox_dollar_variables(self, text: str) -> str:
        """转换 Apifox ${...} 格式的动态变量为 TestHub 格式
        
        Apifox 动态变量格式: ${category.function} 或 ${function}
        TestHub 格式: ${function()}
        
        支持的映射:
        - ${date.timestamp} -> ${timestamp()}
        - ${date.timestamp(ms)} -> ${timestamp()}
        - ${date.timestamp(s)} -> ${timestamp_sec()}
        - ${datetime} -> ${datetime()}
        - ${date} -> ${date()}
        - ${time} -> ${time()}
        - ${uuid} -> ${uuid()}
        - ${random} -> ${random_int(0, 1000)}
        - ${random.int} -> ${random_int(0, 1000)}
        - ${random.float} -> ${random_float(0, 1000)}
        - ${random.boolean} -> ${random_boolean()}
        - ${random.uuid} -> ${uuid()}
        - ${random.string} -> ${random_string(10, "alphanumeric", 1)}
        - ${random.email} -> ${random_email()}
        - ${random.phone} -> ${random_phone()}
        - ${random.ip} -> ${random_ip()}
        - ${random.mac} -> ${random_mac()}
        """
        if not isinstance(text, str):
            return text
        
        print(f"DEBUG - [_convert_apifox_dollar_variables] 输入: {text}")
        
        # 匹配 ${...} 格式，但不匹配 ${function()} 格式（已经是 TestHub 格式）
        pattern = r'\$\{([a-zA-Z_][a-zA-Z0-9_.]*)\}'
        
        def replace_func(match):
            var_expr = match.group(1).strip()
            
            # 映射表: Apifox 变量 -> TestHub 函数
            apifox_to_testhub_map = {
                # 日期时间
                'date.timestamp': 'timestamp()',
                'date.timestamp(ms)': 'timestamp()',
                'date.timestamp(s)': 'timestamp_sec()',
                'datetime': 'datetime()',
                'date': 'date()',
                'time': 'time()',
                'date.now': 'datetime()',
                'date.today': 'date()',
                
                # UUID
                'uuid': 'uuid()',
                'guid': 'uuid()',
                
                # 随机数
                'random': 'random_int(0, 1000)',
                'random.int': 'random_int(0, 1000)',
                'random.integer': 'random_int(0, 1000)',
                'random.float': 'random_float(0, 1000)',
                'random.boolean': 'random_boolean()',
                'random.bool': 'random_boolean()',
                'random.uuid': 'uuid()',
                'random.guid': 'uuid()',
                'random.string': 'random_string(10, "alphanumeric", 1)',
                'random.alphanumeric': 'random_string(10, "alphanumeric", 1)',
                'random.alpha': 'random_string(10, "letters", 1)',
                'random.numeric': 'random_string(10, "numeric", 1)',
                
                # 联系信息
                'random.email': 'random_email()',
                'random.mail': 'random_email()',
                'random.phone': 'random_phone()',
                'random.phoneNumber': 'random_phone()',
                'random.mobile': 'random_phone()',
                
                # 网络
                'random.ip': 'random_ip()',
                'random.ipAddress': 'random_ip()',
                'random.ipv4': 'random_ip()',
                'random.ipv6': 'random_ipv6()',
                'random.mac': 'random_mac()',
                'random.macAddress': 'random_mac()',
                
                # 名称
                'random.name': 'random_name()',
                'random.fullName': 'random_name()',
                'random.firstName': 'random_first_name()',
                'random.lastName': 'random_last_name()',
                'random.chineseName': 'random_chinese_name()',
                
                # 地址
                'random.address': 'random_address()',
                'random.city': 'random_city()',
                'random.province': 'random_province()',
                'random.street': 'random_street()',
                
                # 公司
                'random.company': 'random_company()',
                'random.companyName': 'random_company()',
                
                # 银行卡
                'random.bankCard': 'random_bank_card()',
                'random.creditCard': 'random_bank_card()',
                'random.idCard': 'random_id_card()',
            }
            
            # 转换为小写进行匹配（不区分大小写）
            var_expr_lower = var_expr.lower()
            
            print(f"DEBUG -   匹配到变量: {var_expr} (小写: {var_expr_lower})")
            
            if var_expr_lower in apifox_to_testhub_map:
                testhub_func = apifox_to_testhub_map[var_expr_lower]
                result = f'${{{testhub_func}}}'
                print(f"DEBUG -   转换结果: {result}")
                return result
            
            # 如果没有匹配，保留原样
            print(f"DEBUG -   未匹配，保留原样")
            return match.group(0)
        
        result = re.sub(pattern, replace_func, text)
        print(f"DEBUG - [_convert_apifox_dollar_variables] 输出: {result}")
        return result
    
    def _create_request(self, item: Dict, collection: ApiCollection,
                       path: str, index: int) -> Optional[ApiRequest]:
        """创建 API 请求"""
        request_data = item.get('request', {})
        request_name = item.get('name', f'Request_{index}')

        try:
            # 解析请求方法
            method = request_data.get('method', 'GET').upper()
            print(f"DEBUG - [_create_request] 方法: {method}, 名称: {request_name}")

            # 解析 URL（暂不转换变量）
            url = self._parse_url(request_data.get('url', {}))
            print(f"DEBUG - [_create_request] URL: {url}")

            # 解析 Headers（暂不转换变量）
            headers = self._parse_headers(request_data.get('header', []))

            # 解析 Body（暂不转换变量）
            body = self._parse_body(request_data.get('body', {}))

            # 解析变量提取规则
            extractors = self._parse_extractors(item)

            # 解析断言
            assertions = self._parse_assertions(item)

            # 解析前置脚本
            pre_script = self._parse_pre_script(item)

            # 解析后置脚本
            post_script = self._parse_post_script(item)

            # 创建请求
            request = ApiRequest.objects.create(
                collection=collection,
                name=request_name,
                description=item.get('description', ''),
                method=method,
                url=url,
                headers=headers,
                params=self._parse_params(request_data.get('url', {}).get('query', [])),
                body=body,
                variable_extractors=extractors,
                assertions=assertions,
                pre_request_script=pre_script,
                post_request_script=post_script,
                created_by=self.user
            )

            # 存储原始 item 数据供后续使用
            request._apifox_item = item

            self.import_stats['requests_created'] += 1
            print(f"DEBUG - [_create_request] 创建成功: {request_name}, ID: {request.id}")
            return request
        except Exception as e:
            # 记录错误但不中断导入流程
            print(f"DEBUG - [_create_request] 创建失败: {request_name}, 错误: {str(e)}")
            self._add_request_issue(
                request_name,
                "接口创建失败",
                str(e),
                "请检查接口数据格式或手动创建该接口"
            )
            return None
    
    def _parse_url(self, url_data: Union[Dict, str]) -> str:
        """解析 URL，只返回路径部分（去掉域名）
        
        域名将通过执行环境的 base_url 变量来替换
        查询参数由 _parse_params 单独处理，不在 URL 中包含
        """
        if isinstance(url_data, str):
            # 如果是字符串形式的完整 URL，尝试提取路径
            if url_data.startswith('http://') or url_data.startswith('https://'):
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(url_data)
                    path = parsed.path
                    return path if path else '/'
                except Exception:
                    pass
            return url_data
        
        if not isinstance(url_data, dict):
            return '/'
        
        # 只提取路径部分，忽略域名和查询参数
        path = '/'.join(url_data.get('path', []))
        
        # 确保路径以 / 开头
        if path and not path.startswith('/'):
            path = f"/{path}"
        
        return path if path else '/'
    
    def _parse_headers(self, headers: List[Dict]) -> Dict[str, str]:
        """解析 Headers"""
        result = {}
        for header in headers:
            key = header.get('key', '')
            value = header.get('value', '')
            if key and not header.get('disabled', False):
                result[key] = value
        return result
    
    def _parse_params(self, params: List[Dict]) -> Dict[str, str]:
        """解析 Query 参数"""
        result = {}
        for param in params:
            key = param.get('key', '')
            value = param.get('value', '')
            if key and not param.get('disabled', False):
                result[key] = value
        return result
    
    def _parse_body(self, body_data: Dict) -> Dict:
        """解析请求 Body"""
        if not body_data:
            return {}

        mode = body_data.get('mode', '')
        body_type = body_data.get('type', '')
        raw_data = body_data.get('raw', '')

        if mode == 'raw':
            # 检查是否是 JSON 类型
            if body_type == 'application/json' or 'json' in body_type.lower():
                try:
                    # 尝试解析为 JSON 对象
                    json_data = json.loads(raw_data) if raw_data else {}
                    return {
                        'type': 'json',
                        'data': json_data,
                        'content_type': 'json'
                    }
                except json.JSONDecodeError:
                    # 解析失败，保持原样
                    pass

            return {
                'type': 'raw',
                'data': raw_data,
                'content_type': body_data.get('options', {}).get('raw', {}).get('language', 'text')
            }
        elif mode == 'json':
            # JSON 模式也需要解析为对象
            try:
                json_data = json.loads(raw_data) if raw_data else {}
                return {
                    'type': 'json',
                    'data': json_data
                }
            except json.JSONDecodeError:
                # 解析失败，保持原样
                return {
                    'type': 'json',
                    'data': raw_data
                }
        elif mode == 'formdata':
            return {
                'type': 'formdata',
                'data': body_data.get('formdata', [])
            }
        elif mode == 'urlencoded':
            return {
                'type': 'urlencoded',
                'data': body_data.get('urlencoded', [])
            }

        return {}
    
    def _parse_extractors(self, item: Dict) -> List[Dict]:
        """解析变量提取规则
        
        从 Apifox 的 event/test 脚本中提取变量提取器。
        提取器格式：
        - const expression = await ____replaceIn(`$.data.access_token`);
        - const formattedName = await ____replaceIn(`auth_token`);pm.environment.set(...)
        
        注意：与断言不同，提取器必须有 pm.environment.set 或 pm.variables.set 来保存变量
        """
        extractors = []
        
        events = item.get('event', [])
        for event in events:
            if event.get('listen') == 'test':
                script = event.get('script', {}).get('exec', [])
                script_id = event.get('script', {}).get('id', '')
                
                # 跳过断言类型的脚本（避免将断言的 expression 误解析为提取器）
                if 'assertion' in script_id:
                    continue
                    
                if isinstance(script, list):
                    script_text = '\n'.join(script)
                    
                    # 只处理包含变量保存操作的脚本（真正的提取器）
                    # 提取器必须有 pm.environment.set 或 pm.variables.set
                    if 'pm.environment.set' not in script_text and 'pm.variables.set' not in script_text:
                        # 检查是否是 httpApiExtractor 类型（有 const extracts = [...]）
                        if 'const extracts =' not in script_text:
                            continue
                    
                    # 查找 JSONPath 表达式
                    # 格式: const expression = await ____replaceIn(`$.data.access_token`);
                    jsonpath_matches = re.findall(
                        r'const expression = await ____replaceIn\(`([^`]+)`\)',
                        script_text
                    )
                    
                    # 查找变量名
                    # 格式: const formattedName = await ____replaceIn(`auth_token`);
                    var_name_matches = re.findall(
                        r'const formattedName = await ____replaceIn\(`([^`]+)`\)',
                        script_text
                    )
                    
                    # 配对 JSONPath 和变量名
                    for i, json_path in enumerate(jsonpath_matches):
                        if i < len(var_name_matches):
                            var_name = var_name_matches[i]
                            # 注意：跨步骤变量引用转换在 _convert_requests_variables 中统一处理
                            extractors.append({
                                'name': var_name,
                                'source': 'json_body',
                                'json_path': json_path,
                                'variable_name': var_name
                            })
                    
                    # 也检查 httpApiExtractor 类型的提取器
                    # 格式: const extracts = [{"expression":"...","paths":[...]}];
                    http_api_matches = re.findall(
                        r'const extracts = (\[.*?\]);',
                        script_text,
                        re.DOTALL
                    )
                    for match in http_api_matches:
                        try:
                            extracts = json.loads(match)
                            for extract in extracts:
                                expression = extract.get('expression', '')
                                paths = extract.get('paths', [])
                                # 提取变量名（从 paths 最后一部分）
                                if paths:
                                    var_name = paths[-1]
                                    # 构建 JSONPath
                                    json_path = '.'.join(paths[1:]) if len(paths) > 1 else expression
                                    # 注意：跨步骤变量引用转换在 _convert_requests_variables 中统一处理
                                    extractors.append({
                                        'name': var_name,
                                        'source': 'json_body',
                                        'json_path': json_path,
                                        'variable_name': var_name
                                    })
                        except json.JSONDecodeError:
                            pass
        
        return extractors
    
    def _convert_step_reference(self, text: str) -> str:
        """转换跨步骤变量引用中的 Apifox 索引为 TestHub 顺序
        
        将 {{$.N.request.body.xxx}} 或 {{$.N.response.body.xxx}} 中的 N 
        从 Apifox 全局索引转换为 TestHub 请求顺序
        """
        result, _ = self._convert_step_reference_with_warning(text, None)
        return result
    
    def _convert_step_reference_with_warning(self, text: str, current_order: int = None) -> tuple:
        """转换跨步骤变量引用，并检测向前引用
        
        返回: (转换后的文本, 警告信息)
        """
        if not text or not isinstance(text, str):
            return text, None
        
        import re
        # 匹配跨步骤引用: {{$.数字.request.xxx}} 或 {{$..数字.request.xxx}} 或 {{$数字.request.xxx}}
        # 支持三种格式：$.N、$..N、$N
        # 同时支持 * 通配符表示上一个步骤
        pattern = r'\{\{\$\.?(\d+|\*)\.(request|response)\.(body|headers|params)(?:\.(.*))?\}\}'
        
        warning = None
        
        def replace_ref(match):
            nonlocal warning
            idx_str = match.group(1)
            rest = match.group(2) + '.' + match.group(3)
            if match.group(4):
                rest += '.' + match.group(4)
            
            # 处理 * 通配符（表示引用上一个步骤）
            if idx_str == '*':
                if current_order is not None and current_order > 1:
                    # 引用当前步骤的前一个步骤
                    prev_order = current_order - 1
                    result = f'{{{{$.{prev_order}.{rest}}}}}'
                    print(f"DEBUG - 转换通配符引用: * -> TestHub[{prev_order}]: {result}")
                    return result
                else:
                    warning_msg = "无法解析通配符 *（当前步骤未知或是第一个步骤）"
                    print(f"WARNING - {warning_msg}")
                    if warning is None:
                        warning = warning_msg
                    else:
                        warning += f"; {warning_msg}"
                    return match.group(0)
            
            # 处理数字索引
            apifox_idx = int(idx_str)
            
            # 查找映射
            if apifox_idx in self._apifox_to_request_index:
                testhub_order = self._apifox_to_request_index[apifox_idx]
                result = f'{{{{$.{testhub_order}.{rest}}}}}'
                print(f"DEBUG - 转换变量引用: Apifox[{apifox_idx}] -> TestHub[{testhub_order}]: {result}")
                
                # 检测向前引用（当前步骤引用了后续步骤）
                if current_order is not None and testhub_order > current_order:
                    warning = f"引用了步骤 {testhub_order}，但当前步骤是 {current_order}"
                    print(f"WARNING - {warning}")
                
                return result
            else:
                # 引用的步骤在映射表中不存在（可能是引用了错误的步骤或已删除的步骤）
                warning_msg = f"引用了不存在的步骤 {apifox_idx}"
                print(f"WARNING - {warning_msg}")
                # 累积警告信息
                if warning is None:
                    warning = warning_msg
                else:
                    warning += f"; {warning_msg}"
                return match.group(0)
        
        result = re.sub(pattern, replace_ref, text)
        return result, warning
    
    def _parse_assertions(self, item: Dict) -> List[Dict]:
        """解析断言规则
        
        从 Apifox 的 event/test 脚本中提取断言。
        断言格式：
        - const formattedName = await ____replaceIn(`check_notnull`);
        - const expression = await ____replaceIn(`$.data`);
        - pm.expect(value).to.not.be.null
        - pm.expect(formattedValues.value).to.eql(formattedValues.compareValue)
        """
        assertions = []
        
        events = item.get('event', [])
        for event in events:
            if event.get('listen') == 'test':
                script = event.get('script', {}).get('exec', [])
                script_id = event.get('script', {}).get('id', '')
                
                # 只处理断言类型的脚本
                if 'assertion' not in script_id:
                    continue
                    
                if isinstance(script, list):
                    script_text = '\n'.join(script)
                    
                    # 提取断言名称
                    name_matches = re.findall(
                        r'const formattedName = await ____replaceIn\(`([^`]+)`\)',
                        script_text
                    )
                    
                    # 提取 JSONPath 表达式
                    jsonpath_matches = re.findall(
                        r'const expression = await ____replaceIn\(`([^`]+)`\)',
                        script_text
                    )
                    
                    # 提取比较值（支持多种变量名格式）
                    # 格式1: const stringCompareValue = await ____replaceIn(`...`)
                    # 格式2: const compareValue = await ____replaceIn(`{{variable}}`)
                    compare_matches = re.findall(
                        r'const (?:stringCompareValue|compareValue) = await ____replaceIn\(`([^`]*)`\)',
                        script_text
                    )

                    # 确定断言类型和操作
                    # 映射到前端支持的类型: status_code, response_time, contains, json_path, header, equals
                    # 注意: 有 json_path 的断言都应该用 'json_path' 作为 type，用 operator 表示具体比较方式
                    assertion_type = 'json_path'  # 默认使用 json_path
                    operator = 'not_empty'
                    if 'to.not.be.null' in script_text:
                        assertion_type = 'json_path'
                        operator = 'not_null'
                    elif 'to.not.be.undefined' in script_text:
                        assertion_type = 'json_path'
                        operator = 'not_undefined'
                    elif 'to.not.be.empty' in script_text:
                        assertion_type = 'json_path'
                        operator = 'not_empty'
                    elif 'to.eql' in script_text:
                        assertion_type = 'json_path'  # 有 json_path，所以用 json_path 类型
                        operator = 'equals'  # 用 operator 表示等于比较
                    elif 'to.include' in script_text:
                        assertion_type = 'contains'
                        operator = 'contains'

                    # 配对断言信息
                    for i, name in enumerate(name_matches):
                        json_path = jsonpath_matches[i] if i < len(jsonpath_matches) else ''
                        expected = compare_matches[i] if i < len(compare_matches) else ''

                        # 注意：跨步骤变量引用转换在 _convert_requests_variables 中统一处理

                        # 将 not_null/not_empty 等特殊检查作为 expected 值存储
                        # 这样可以在前端显示为"不为空"，并且可以编辑
                        if operator == 'not_null':
                            expected = 'not_null'
                            expected_display = '不为空'
                        elif operator == 'not_undefined':
                            expected = 'not_undefined'
                            expected_display = '不为undefined'
                        elif operator == 'not_empty':
                            expected = 'not_empty'
                            expected_display = '不为空'
                        else:
                            expected_display = expected

                        assertions.append({
                            'name': name,
                            'type': assertion_type,
                            'assertion_type': 'response_body',
                            'source': 'response_body',
                            'json_path': json_path,
                            'expected': expected,
                            'expected_value': expected,
                            'expected_display': expected_display,
                            'operator': operator,  # 使用解析到的 operator
                            'operator_type': operator
                        })
        
        return assertions
    
    def _parse_pre_script(self, item: Dict) -> str:
        """解析前置脚本"""
        events = item.get('event', [])
        for event in events:
            if event.get('listen') == 'prerequest':
                script = event.get('script', {}).get('exec', [])
                if isinstance(script, list):
                    return '\n'.join(script)
                return script
        return ''
    
    def _parse_post_script(self, item: Dict) -> str:
        """解析后置脚本"""
        events = item.get('event', [])
        for event in events:
            if event.get('listen') == 'test':
                script = event.get('script', {}).get('exec', [])
                if isinstance(script, list):
                    return '\n'.join(script)
                return script
        return ''
    
    def _create_test_suite(self, data: Dict, collection: ApiCollection,
                          requests: List[ApiRequest],
                          structured_steps: List[Dict] = None) -> Optional[TestSuite]:
        """创建测试套件（支持分组结构）"""
        if not requests:
            return None

        suite_name = data.get('info', {}).get('name', 'API Fox Suite')

        # 删除同名的现有测试套件
        existing_suites = TestSuite.objects.filter(
            project=self.project,
            name=suite_name
        )
        for existing in existing_suites:
            existing.delete()

        suite = TestSuite.objects.create(
            project=self.project,
            name=suite_name,
            description='从 API Fox 导入的测试套件',
            created_by=self.user
        )
        
        # 如果有结构化步骤数据，使用递归方式创建（支持分组）
        if structured_steps:
            self._create_suite_requests_recursive(suite, structured_steps)
        else:
            # 向后兼容：扁平列表
            for idx, request in enumerate(requests):
                TestSuiteRequest.objects.create(
                    test_suite=suite,
                    request=request,
                    order=idx,
                    assertions=request.assertions,
                    extracted_variables=request.variable_extractors
                )
        
        self.import_stats['suites_created'] += 1
        return suite
    
    def _create_suite_requests_recursive(self, suite: TestSuite, steps: List[Dict], 
                                         parent_request=None, order_counter: list = None):
        """递归创建测试套件请求（支持分组）"""
        if order_counter is None:
            order_counter = [0]
        
        for step_info in steps:
            order_counter[0] += 1
            current_order = order_counter[0]
            
            if step_info['type'] == 'request':
                # 创建请求类型的 TestSuiteRequest
                api_request = step_info['request']
                suite_req = TestSuiteRequest.objects.create(
                    test_suite=suite,
                    request=api_request,
                    order=current_order,
                    step_type='request',
                    parent_id=parent_request.id if parent_request else None,
                    assertions=api_request.assertions,
                    extracted_variables=api_request.variable_extractors
                )
                
                # 递归处理子步骤（如果有）
                if step_info.get('children'):
                    self._create_suite_requests_recursive(
                        suite, step_info['children'], suite_req, order_counter
                    )
                    
            elif step_info['type'] == 'group':
                # 创建分组类型的 TestSuiteRequest（没有实际请求）
                suite_req = TestSuiteRequest.objects.create(
                    test_suite=suite,
                    request=None,
                    order=current_order,
                    step_type='group',
                    parent_id=parent_request.id if parent_request else None,
                    override_name=step_info.get('name', '')
                )
                
                # 递归处理子步骤
                if step_info.get('children'):
                    self._create_suite_requests_recursive(
                        suite, step_info['children'], suite_req, order_counter
                    )
    
    def _create_automation_scenario(self, data: Dict, collection: ApiCollection,
                                    steps: List[Dict], suite: TestSuite) -> Optional[AutomationScenario]:
        """创建自动化场景（带层级结构）"""
        if not steps:
            return None

        scenario_name = data.get('info', {}).get('name', 'API Fox Scenario')

        # 删除同名的现有自动化场景
        existing_scenarios = AutomationScenario.objects.filter(
            project=self.project,
            name=scenario_name
        )
        for existing in existing_scenarios:
            existing.delete()

        # 创建场景
        scenario = AutomationScenario.objects.create(
            project=self.project,
            name=scenario_name,
            description='从 API Fox 导入的自动化场景',
            collection=collection,
            legacy_test_suite=suite,
            created_by=self.user
        )
        
        # 保存当前场景引用，用于后续修正变量引用
        self._current_scenario = scenario

        # 递归创建步骤，并记录 order -> step_number 的映射
        order_to_step_number = {}
        self._create_scenario_steps(scenario, steps, order_to_step_number=order_to_step_number)

        # 修正变量引用中的序号（确保引用指向正确的step_number）
        self._fix_step_references_in_requests(order_to_step_number)
        
        # 修正场景步骤中的变量引用序号
        self._fix_step_references_in_scenario_steps(scenario, order_to_step_number)

        return scenario
    
    def _fix_step_references_in_requests(self, order_to_step_number: dict):
        """
        修正请求中变量引用的序号
        
        在导入时，变量引用如 {{$.N.response.body.xxx}} 中的 N 是基于请求顺序(order)的，
        但场景步骤的 step_number 包含了分组，导致序号不匹配。
        
        此方法将变量引用中的 order 序号替换为实际的 step_number。
        
        Args:
            order_to_step_number: order -> step_number 的映射字典
        """
        import re
        
        if not order_to_step_number:
            return
        
        # 找出所有需要修正的请求（通过之前记录的 _structured_steps）
        def fix_step_ref_in_text(text: str) -> str:
            """修正文本中的步骤引用"""
            if not isinstance(text, str):
                return text
            
            # 匹配跨步骤引用: {{$.N.request.body.xxx}} 或 {{$..N.request.body.xxx}} 或 {{$.N.response.body.xxx}}
            # 支持两种格式：$.N 和 $..N
            pattern = r'\{\{\$\.{1,2}(\d+)\.(request|response|variables)(?:\.(.*))?\}\}'
            
            def replace_ref(match):
                order = int(match.group(1))
                rest = match.group(2) + '.' + match.group(3) if match.group(3) else match.group(2)
                
                # 如果这个 order 有对应的 step_number，进行替换
                if order in order_to_step_number:
                    step_number = order_to_step_number[order]
                    return f'{{{{$.{step_number}.{rest}}}}}'
                return match.group(0)
            
            return re.sub(pattern, replace_ref, text)
        
        def fix_step_ref_in_dict(data):
            """递归修正字典中的步骤引用"""
            if isinstance(data, dict):
                return {k: fix_step_ref_in_dict(v) for k, v in data.items()}
            elif isinstance(data, list):
                return [fix_step_ref_in_dict(item) for item in data]
            elif isinstance(data, str):
                return fix_step_ref_in_text(data)
            return data
        
        # 获取当前导入的所有请求（从已创建的场景步骤中获取）
        current_requests = []
        if hasattr(self, '_current_scenario'):
            # 从场景步骤中获取关联的请求
            steps_with_requests = ScenarioStep.objects.filter(
                scenario=self._current_scenario,
                api_request__isnull=False
            ).select_related('api_request')
            
            current_requests = [step.api_request for step in steps_with_requests]
        
        # 修正当前导入请求中的变量引用
        for request in current_requests:
            updated = False
            
            # 修正 URL
            if request.url:
                new_url = fix_step_ref_in_text(request.url)
                if new_url != request.url:
                    request.url = new_url
                    updated = True
            
            # 修正 Headers
            if request.headers:
                new_headers = fix_step_ref_in_dict(request.headers)
                if new_headers != request.headers:
                    request.headers = new_headers
                    updated = True
            
            # 修正 Body
            if request.body:
                new_body = fix_step_ref_in_dict(request.body)
                if new_body != request.body:
                    request.body = new_body
                    updated = True
            
            # 修正断言
            if request.assertions:
                # assertions 可能是字符串或列表，需要先确保是列表
                assertions_data = request.assertions
                if isinstance(assertions_data, str):
                    try:
                        assertions_data = json.loads(assertions_data)
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                new_assertions = fix_step_ref_in_dict(assertions_data)
                # 将结果转换回与原始类型一致的格式
                if isinstance(request.assertions, str):
                    new_assertions = json.dumps(new_assertions)
                
                if new_assertions != request.assertions:
                    request.assertions = new_assertions
                    updated = True
            
            # 修正变量提取器
            if request.variable_extractors:
                new_extractors = fix_step_ref_in_dict(request.variable_extractors)
                if new_extractors != request.variable_extractors:
                    request.variable_extractors = new_extractors
                    updated = True
            
            if updated:
                request.save()
    
    def _fix_step_references_in_scenario_steps(self, scenario: AutomationScenario, order_to_step_number: dict):
        """
        修正场景步骤中的变量引用序号
        
        Args:
            scenario: 自动化场景对象
            order_to_step_number: order -> step_number 的映射字典
        """
        import re
        
        if not order_to_step_number:
            return
        
        def fix_step_ref_in_text(text: str) -> str:
            """修正文本中的步骤引用"""
            if not isinstance(text, str):
                return text
            
            # 匹配跨步骤引用: {{$.N.request.body.xxx}} 或 {{$..N.request.body.xxx}}
            # 支持两种格式：$.N 和 $..N
            pattern = r'\{\{\$\.{1,2}(\d+)\.(request|response|variables)(?:\.(.*))?\}\}'
            
            def replace_ref(match):
                order = int(match.group(1))
                rest = match.group(2) + '.' + match.group(3) if match.group(3) else match.group(2)
                
                if order in order_to_step_number:
                    step_number = order_to_step_number[order]
                    return f'{{{{$.{step_number}.{rest}}}}}'
                return match.group(0)
            
            return re.sub(pattern, replace_ref, text)
        
        def fix_step_ref_in_dict(data):
            """递归修正字典中的步骤引用"""
            if isinstance(data, dict):
                return {k: fix_step_ref_in_dict(v) for k, v in data.items()}
            elif isinstance(data, list):
                return [fix_step_ref_in_dict(item) for item in data]
            elif isinstance(data, str):
                return fix_step_ref_in_text(data)
            return data
        
        # 修正场景步骤中的变量引用
        for step in ScenarioStep.objects.filter(scenario=scenario):
            updated = False
            
            # 修正覆盖URL
            if step.override_url:
                new_url = fix_step_ref_in_text(step.override_url)
                if new_url != step.override_url:
                    step.override_url = new_url
                    updated = True
            
            # 修正覆盖Headers
            if step.override_headers:
                new_headers = fix_step_ref_in_dict(step.override_headers)
                if new_headers != step.override_headers:
                    step.override_headers = new_headers
                    updated = True
            
            # 修正覆盖Body
            if step.override_body:
                new_body = fix_step_ref_in_dict(step.override_body)
                if new_body != step.override_body:
                    step.override_body = new_body
                    updated = True
            
            # 修正覆盖断言
            if step.override_assertions:
                new_assertions = fix_step_ref_in_dict(step.override_assertions)
                if new_assertions != step.override_assertions:
                    step.override_assertions = new_assertions
                    updated = True
            
            # 修正覆盖变量提取器
            if step.override_extractors:
                new_extractors = fix_step_ref_in_dict(step.override_extractors)
                if new_extractors != step.override_extractors:
                    step.override_extractors = new_extractors
                    updated = True
            
            if updated:
                step.save()
    
    def _create_scenario_steps(self, scenario: AutomationScenario, steps: List[Dict], 
                               parent_step: ScenarioStep = None, step_counter: list = None,
                               order_to_step_number: dict = None):
        """递归创建场景步骤"""
        # 使用列表作为可变计数器，在递归调用中保持状态
        if step_counter is None:
            step_counter = [0]
        
        for step_info in steps:
            step_counter[0] += 1
            current_step_number = step_counter[0]
            
            if step_info['type'] == 'request':
                # 创建请求步骤
                api_request = step_info['request']
                step = ScenarioStep.objects.create(
                    scenario=scenario,
                    parent=parent_step,
                    name=step_info['name'],
                    step_type='request',
                    step_number=current_step_number,
                    order=step_info['order'],
                    api_request=api_request,
                    override_assertions=api_request.assertions if api_request else [],
                    override_extractors=api_request.variable_extractors if api_request else []
                )
                
                # 记录 order -> step_number 的映射（用于修正变量引用）
                if order_to_step_number is not None:
                    order_to_step_number[step_info['order']] = current_step_number
            elif step_info['type'] == 'group':
                # 创建分组步骤
                step = ScenarioStep.objects.create(
                    scenario=scenario,
                    parent=parent_step,
                    name=step_info['name'],
                    step_type='group',
                    step_number=current_step_number,
                    order=current_step_number
                )
                
                # 递归创建子步骤，传递相同的计数器
                if step_info.get('children'):
                    self._create_scenario_steps(scenario, step_info['children'], step, step_counter, order_to_step_number)
    
    def _extract_environment(self, data: Dict):
        """提取环境变量"""
        # 从变量定义中提取
        variables = data.get('variable', [])
        if not variables:
            return
        
        # 创建或更新环境
        env_name = data.get('info', {}).get('name', 'API Fox Environment')
        env, created = Environment.objects.get_or_create(
            project=self.project,
            name=env_name,
            defaults={
                'description': '从 API Fox 导入的环境',
                'created_by': self.user
            }
        )
        
        # 添加变量
        env_vars = env.variables or {}
        for var in variables:
            key = var.get('key', '')
            value = var.get('value', '')
            if key:
                env_vars[key] = value
        
        env.variables = env_vars
        env.save()


def import_apifox_cli(file_path: str, user, project, import_env: bool = False, target_collection=None):
    """
    API Fox CLI JSON 文件导入的便捷函数
    
    Args:
        file_path: JSON 文件路径
        user: 导入用户
        project: 目标项目
        import_env: 是否导入环境变量
        target_collection: 指定导入到哪个集合（可选）
    
    Returns:
        导入结果统计
    """
    importer = ApifoxCliImporter(user, project)
    return importer.import_from_file(file_path, import_env, target_collection)


def validate_apifox_file(file_path: str) -> Dict[str, Any]:
    """
    验证 API Fox CLI JSON 文件
    
    Args:
        file_path: JSON 文件路径
    
    Returns:
        验证结果
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return {'valid': False, 'error': f'JSON 解析失败: {str(e)}'}
    except Exception as e:
        return {'valid': False, 'error': f'文件读取失败: {str(e)}'}
    
    # 检查必要字段
    if 'item' not in data:
        return {'valid': False, 'error': '缺少必要的 item 字段'}
    
    # 统计请求数量
    total_requests = 0
    unsupported_functions = []
    
    def count_requests(items):
        nonlocal total_requests
        for item in items:
            if 'request' in item:
                total_requests += 1
                # 检查是否有不支持的函数
                item_str = json.dumps(item)
                # 检查动态函数
                func_matches = re.findall(r'\{\{\$([\w.]+)\(', item_str)
                for func in func_matches:
                    if func not in ['string.alphanumeric', 'timestamp', 'uuid', 'randomInt', 'randomFloat']:
                        unsupported_functions.append(func)
            elif 'item' in item:
                count_requests(item['item'])
    
    items = data.get('item', [])
    # 处理 wrapper 结构
    if items and isinstance(items[0], dict) and 'item' in items[0]:
        items = items[0].get('item', [])

    count_requests(items)

    # 提取场景名称
    scenario_name = ''
    if 'info' in data and 'name' in data['info']:
        scenario_name = data['info']['name']
    elif items and isinstance(items[0], dict) and 'name' in items[0]:
        # 如果只有一个文件夹，使用文件夹名称
        scenario_name = items[0].get('name', '')

    return {
        'valid': True,
        'total_requests': total_requests,
        'unsupported_functions': list(set(unsupported_functions)),
        'warnings': [],
        'scenario_name': scenario_name
    }
