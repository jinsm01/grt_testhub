# -*- coding: utf-8 -*-
"""
阿里云云效 (Yunxiao) API 客户端

封装云效 OpenAPI 调用，支持:
- 获取项目列表
- 获取迭代列表
- 搜索工作项 (Bug)

认证方式: 个人访问令牌 (PAT) 通过 x-yunxiao-token header 传递
文档: https://help.aliyun.com/zh/yunxiao/developer-reference/
"""

import json
import logging
from typing import List, Dict, Optional, Any

import requests

logger = logging.getLogger(__name__)

# 云效 API 接入点
# 中心版统一接入点: openapi-rdc.aliyuncs.com
# Region版使用实例域名，如 https://your-org.devops.aliyuncs.com
YUNXIAO_DOMAIN = "https://openapi-rdc.aliyuncs.com"

# 工作项类型: 缺陷
CATEGORY_BUG = "Bug"

# 默认分页大小
DEFAULT_PAGE_SIZE = 50


class YunxiaoAPIError(Exception):
    """云效 API 错误"""
    pass


class YunxiaoClient:
    """云效 API 客户端"""

    def __init__(self, token: str, organization_id: str = "", domain: str = YUNXIAO_DOMAIN):
        """
        初始化客户端

        Args:
            token: 云效个人访问令牌 (PAT)
            organization_id: 组织 ID (中心版必填)
            domain: API 域名，默认 https://devops.aliyun.com
        """
        self.token = token
        self.organization_id = organization_id
        self.domain = domain.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "x-yunxiao-token": self.token,
        })

    def _get_base_url(self, api_path: str) -> str:
        """构建完整 API URL (中心版带 organizations)"""
        if self.organization_id:
            return f"{self.domain}/oapi/v1/projex/organizations/{self.organization_id}{api_path}"
        return f"{self.domain}/oapi/v1/projex{api_path}"

    def _request(self, method: str, api_path: str, **kwargs) -> Dict[str, Any]:
        """发送 HTTP 请求并处理响应"""
        url = self._get_base_url(api_path)
        logger.info(f"[YunxiaoClient] {method} {url} | payload={kwargs.get('json')} | params={kwargs.get('params')}")
        try:
            resp = self.session.request(method, url, timeout=60, **kwargs)
            logger.info(f"[YunxiaoClient] response status={resp.status_code} | body={resp.text[:800]}")
            resp.raise_for_status()
            text = resp.text.strip()
            if not text:
                return {}
            data = resp.json()
            # 某些接口直接返回数组
            if isinstance(data, list):
                return data
            # 云效错误响应格式: {"errorCode":"InvalidToken","errorMessage":"..."}
            if isinstance(data, dict) and "errorCode" in data:
                raise YunxiaoAPIError(f"云效 API 错误 [{data.get('errorCode')}]: {data.get('errorMessage', '')}")
            # 兼容旧版错误格式
            if isinstance(data, dict) and not data.get("success", True):
                error_msg = data.get("errorMsg") or data.get("message") or json.dumps(data)
                raise YunxiaoAPIError(f"云效 API 返回错误: {error_msg}")
            return data
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else 0
            text = e.response.text if e.response else str(e)
            logger.warning(f"云效 API HTTP 错误 [{status_code}]: {text}")
            raise YunxiaoAPIError(f"云效 API 请求失败 (HTTP {status_code}): {text}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"云效 API 请求异常: {e}")
            raise YunxiaoAPIError(f"云效 API 请求异常: {e}")

    # ============================================================
    # 项目相关
    # ============================================================

    def search_projects(self, keyword: str = "", page: int = 1, per_page: int = 50) -> List[Dict]:
        """
        搜索项目列表

        云效接口: POST /oapi/v1/projex/organizations/{organizationId}/projects:search
        """
        if not self.organization_id:
            raise YunxiaoAPIError("搜索项目需要提供组织 ID (organization_id)")

        url_path = "/projects:search"
        payload: Dict[str, Any] = {
            "page": page,
            "perPage": min(per_page, 200),
        }
        if keyword:
            payload["conditions"] = json.dumps({
                "conditionGroups": [[{
                    "className": "string",
                    "fieldIdentifier": "name",
                    "format": "input",
                    "operator": "CONTAINS",
                    "value": [keyword],
                }]]
            })

        data = self._request("POST", url_path, json=payload)
        if isinstance(data, list):
            return data
        return data.get("projects") or data.get("data", {}).get("projects", []) or data.get("result", []) or []

    # ============================================================
    # 迭代相关
    # ============================================================

    def list_sprints(self, space_id: str, page: int = 1, per_page: int = 50) -> List[Dict]:
        """
        获取指定项目的迭代列表

        云效接口: GET /oapi/v1/projex/organizations/{organizationId}/projects/{id}/sprints
        """
        if not self.organization_id:
            raise YunxiaoAPIError("获取迭代列表需要提供组织 ID (organization_id)")

        url_path = f"/projects/{space_id}/sprints"
        params = {
            "page": page,
            "perPage": min(per_page, 200),
        }
        data = self._request("GET", url_path, params=params)
        if isinstance(data, list):
            return data
        return data.get("sprints") or data.get("data", {}).get("sprints", []) or data.get("result", []) or []

    # ============================================================
    # 工作项 (Bug) 相关
    # ============================================================

    def search_workitems(
        self,
        space_id: str,
        space_type: str = "Project",
        category: Optional[str] = None,
        sprint_id: Optional[str] = None,
        page: int = 1,
        per_page: int = 100,
        extra_conditions: Optional[List[Dict]] = None,
    ) -> Union[Dict[str, Any], List[Dict]]:
        """
        搜索工作项

        云效接口: POST /oapi/v1/projex/organizations/{organizationId}/workitems:search
        注意: 某些版本直接返回数组
        """
        if not self.organization_id:
            raise YunxiaoAPIError("搜索工作项需要提供组织 ID (organization_id)")

        url_path = "/workitems:search"
        payload: Dict[str, Any] = {
            "spaceId": space_id,
            "spaceType": space_type,
            "page": page,
            "perPage": min(per_page, 200),
        }
        if category:
            payload["category"] = category
        if sprint_id:
            payload["sprintId"] = sprint_id
        if extra_conditions:
            payload["conditions"] = json.dumps({"conditionGroups": [extra_conditions]})

        return self._request("POST", url_path, json=payload)

    def search_bugs(
        self,
        space_id: str,
        sprint_id: Optional[str] = None,
        page: int = 1,
        per_page: int = 100,
    ) -> Dict[str, Any]:
        """
        搜索 Bug (缺陷)

        封装 search_workitems，固定 category=Bug
        """
        return self.search_workitems(
            space_id=space_id,
            category=CATEGORY_BUG,
            sprint_id=sprint_id,
            page=page,
            per_page=per_page,
        )

    def fetch_all_bugs(self, space_id: str, sprint_id: Optional[str] = None, max_bugs: int = 1000) -> List[Dict]:
        """
        分页拉取所有 Bug

        Args:
            space_id: 项目 ID
            sprint_id: 迭代 ID (可选)
            max_bugs: 最大拉取数量

        Returns:
            list[dict]: 原始 Bug 工作项列表
        """
        all_bugs: List[Dict] = []
        page = 1
        per_page = 100

        while len(all_bugs) < max_bugs:
            result = self.search_bugs(space_id, sprint_id, page=page, per_page=per_page)
            # 某些版本直接返回数组
            if isinstance(result, list):
                bugs = result
                # 当返回数组且数量等于 per_page 时，认为可能还有更多
                has_more = len(bugs) == per_page
            else:
                bugs = result.get("workitems") or result.get("data", {}).get("workitems", []) or result.get("result", []) or []
                total = result.get("totalCount") or result.get("total") or result.get("data", {}).get("totalCount", 0)
                has_more = len(all_bugs) + len(bugs) < total
            if not bugs:
                break

            # 手动按 sprint 过滤（云效 sprintId 参数可能不精确）
            if sprint_id:
                filtered = []
                for bug in bugs:
                    sprints = bug.get("sprints") or bug.get("sprint") or []
                    if isinstance(sprints, dict):
                        sprints = [sprints]
                    if not isinstance(sprints, list):
                        sprints = [sprints]
                    sprint_ids = [s.get("id") if isinstance(s, dict) else str(s) for s in sprints]
                    if sprint_id in sprint_ids:
                        filtered.append(bug)
                # 调试日志：打印过滤前后数量，以及首个 bug 的 sprint 字段
                if page == 1:
                    logger.info(f"[YunxiaoClient] sprint过滤前 {len(bugs)} 条，过滤后 {len(filtered)} 条。首个bug sprints={bugs[0].get('sprints') or bugs[0].get('sprint') if bugs else None}")
                bugs = filtered

            all_bugs.extend(bugs)
            if not has_more:
                break
            page += 1

        return all_bugs[:max_bugs]


# ============================================================
# 数据转换
# ============================================================

def _extract_name(obj):
    """从云效对象中提取名称（支持 dict / list / str）"""
    if isinstance(obj, dict):
        return obj.get("displayName") or obj.get("name") or obj.get("nickName") or obj.get("realName") or str(obj)
    if isinstance(obj, list) and obj:
        return _extract_name(obj[0])
    return obj or ""


# 状态/类型类关键词（用于过滤 label，挑出最像模块名的那个）
_NON_MODULE_KEYWORDS = [
    "测试", "记录", "修复", "已修复", "已完成", "关闭", "打开", "待处理",
    "同步", "标签", "跟踪", "需求", "任务", "缺陷", "排查", "跟进", "复盘", "回归",
]


def _pick_module_name_from_labels(label_names: List[str]) -> str:
    """
    从多个 label 中挑选最像模块名的那个
    - 优先选不含状态/类型类关键词的 label
    - 都包含则回退到第一个（保持原行为）
    - 空列表返回空串
    """
    if not label_names:
        return ""
    for name in label_names:
        if name and not any(kw in name for kw in _NON_MODULE_KEYWORDS):
            return name
    return label_names[0]


def _extract_custom_field_values(custom_field_values: List[Dict]) -> Dict[str, Any]:
    """将云效 customFieldValues 数组解析为字典"""
    result = {}
    for field in custom_field_values or []:
        field_name = field.get("fieldName") or field.get("fieldId", "")
        field_format = field.get("fieldFormat", "")
        values = field.get("values", [])

        if field_format in ("list", "multiList") and isinstance(values, list):
            # 列表类型取 displayValue
            display_values = []
            for v in values:
                if isinstance(v, dict):
                    display_values.append(v.get("displayValue") or v.get("value") or v.get("identifier", ""))
                else:
                    display_values.append(str(v))
            result[field_name] = display_values[0] if field_format == "list" and len(display_values) == 1 else display_values
        elif field_format in ("date", "datetime") and values:
            result[field_name] = values[0] if isinstance(values, list) else values
        elif field_format in ("user", "multiUser") and values:
            # 统一处理单用户和多选用户
            if isinstance(values, list):
                names = [_extract_name(v) for v in values]
                result[field_name] = names[0] if field_format == "user" and len(names) == 1 else names
            else:
                result[field_name] = _extract_name(values)
        else:
            # 其他类型：尝试从字典中提取显示值
            if isinstance(values, list):
                parsed = []
                for v in values:
                    if isinstance(v, dict):
                        parsed.append(v.get("displayValue") or v.get("displayName") or v.get("value") or v.get("name") or str(v))
                    else:
                        parsed.append(str(v))
                result[field_name] = parsed[0] if len(parsed) == 1 else parsed
            elif isinstance(values, dict):
                result[field_name] = values.get("displayValue") or values.get("displayName") or values.get("value") or values.get("name") or str(values)
            else:
                result[field_name] = values
    return result


def convert_yunxiao_bugs(raw_workitems: List[Dict]) -> List[Dict]:
    """
    将云效原始工作项转换为系统内部格式

    Args:
        raw_workitems: 云效 API 返回的原始工作项列表

    Returns:
        list[dict]: 转换后的 Bug 字典列表
    """
    logger.info(f"[convert_yunxiao_bugs] 开始转换 {len(raw_workitems)} 条原始工作项")

    # 打印第一条原始数据的所有字段名和值（用于诊断字段名匹配问题）
    if raw_workitems:
        first_item = raw_workitems[0]
        all_keys = list(first_item.keys())
        logger.info(f"[convert_yunxiao_bugs] 第一条原始数据所有字段名: {all_keys}")
        # 打印与时间相关的字段
        time_keys = [k for k in all_keys if 'create' in k.lower() or 'modify' in k.lower() or 'update' in k.lower() or 'close' in k.lower() or 'gmt' in k.lower() or 'time' in k.lower()]
        logger.info(f"[convert_yunxiao_bugs] 可能的时间相关字段: {time_keys}")
        for tk in time_keys[:5]:
            logger.info(f"[convert_yunxiao_bugs] 时间字段 {tk} = {first_item.get(tk)}")
        # 打印与自定义字段相关的字段
        cf_keys = [k for k in all_keys if 'custom' in k.lower() or 'field' in k.lower() or 'extra' in k.lower()]
        logger.info(f"[convert_yunxiao_bugs] 可能的自定义字段相关字段: {cf_keys}")
        for ck in cf_keys[:5]:
            val = first_item.get(ck)
            logger.info(f"[convert_yunxiao_bugs] 自定义字段 {ck} = {str(val)[:200]}")

    bugs = []
    for idx, item in enumerate(raw_workitems):
        # 解析自定义字段：尝试多种可能的字段名
        cf_map = {}
        # 云效新版格式
        custom_field_values = item.get("customFieldValues") or item.get("customFieldValueList") or []
        if custom_field_values:
            cf_map = _extract_custom_field_values(custom_field_values)
        # 兼容其他格式
        custom_fields_legacy = item.get("customFields") or item.get("fieldValueMap") or item.get("extraFields") or item.get("custom_field_values") or {}
        if isinstance(custom_fields_legacy, dict):
            cf_map.update(custom_fields_legacy)
        if isinstance(custom_fields_legacy, list) and custom_fields_legacy:
            cf_map.update(_extract_custom_field_values(custom_fields_legacy))

        # 提取标准字段中的参与者（participants 是云效标准字段，不是自定义字段）
        participants_raw = item.get("participants") or item.get("participant") or []
        if participants_raw:
            if isinstance(participants_raw, list):
                participant_names = [_extract_name(p) for p in participants_raw if p]
                participant_names = [n for n in participant_names if n]
                if participant_names:
                    cf_map["参与者"] = participant_names if len(participant_names) > 1 else participant_names[0]
            else:
                participant_name = _extract_name(participants_raw)
                if participant_name:
                    cf_map["参与者"] = participant_name

        # 解析顶层 labels 字段（云效原生标签，每个元素含 id/name/color）
        # 用于模块归类：labels[0].name 优先作为 module 来源
        labels_raw = item.get("labels") or item.get("label") or []
        label_names = []
        if isinstance(labels_raw, list):
            for lb in labels_raw:
                if isinstance(lb, dict):
                    name = lb.get("name") or lb.get("displayName")
                    if name:
                        label_names.append(str(name).strip())
                elif isinstance(lb, str) and lb.strip():
                    label_names.append(lb.strip())
        if label_names:
            cf_map["labels"] = label_names

        # 提取时间字段：尝试多种可能的字段名（camelCase / snake_case / 其他变体）
        created_raw = (item.get("gmtCreate") or item.get("gmt_create") or
                       item.get("createdAt") or item.get("created_at") or
                       item.get("createTime") or item.get("create_time") or
                       item.get("createdTime") or item.get("created_time") or
                       item.get("gmtCreateTime") or item.get("gmt_create_time") or "")
        updated_raw = (item.get("gmtModified") or item.get("gmt_modified") or
                       item.get("modifiedAt") or item.get("modified_at") or
                       item.get("updateTime") or item.get("update_time") or
                       item.get("updatedTime") or item.get("updated_time") or
                       item.get("gmtModifyTime") or item.get("gmt_modify_time") or
                       item.get("gmtClosed") or item.get("gmt_closed") or
                       item.get("closedAt") or item.get("closed_at") or
                       item.get("closeTime") or item.get("close_time") or "")

        bug = {
            "id": item.get("id") or item.get("serialNumber") or item.get("identifier"),
            "serialNumber": item.get("serialNumber") or "",
            "title": item.get("subject") or item.get("title") or item.get("name", ""),
            "desc": item.get("description") or item.get("content", ""),
            "status": _extract_name(item.get("status")),
            "severity": cf_map.get("严重程度") or cf_map.get("seriousLevel") or item.get("severity") or item.get("severityName", ""),
            "priority": cf_map.get("优先级") or cf_map.get("priority") or item.get("priority") or item.get("priorityName", ""),
            "module": (_pick_module_name_from_labels(label_names) or
                       cf_map.get("所属模块") or cf_map.get("功能模块") or
                       cf_map.get("module") or item.get("module") or item.get("moduleName", "")),
            "creator": _extract_name(item.get("creator")),
            "reporter": _extract_name(item.get("creator")),
            "assignee": _extract_name(item.get("assignedTo")),
            "type": _extract_name(item.get("workitemType")) or item.get("category") or item.get("type", CATEGORY_BUG),
            "created": created_raw,
            "updated": updated_raw,
            "solution": "",
            "remark": "",
            "custom_fields": cf_map,
        }

        # 额外保留原始数据（用于前端展示所有字段）
        bug["_raw"] = item

        # 每10条打印一次详细日志（避免日志过多）
        if idx < 5 or (idx + 1) % 10 == 0:
            logger.info(f"[convert_yunxiao_bugs] Bug#{idx+1}: id={bug['id']}, title={bug['title'][:30]}..., "
                        f"created={created_raw}, updated={updated_raw}, "
                        f"creator={bug['creator']}, custom_fields keys={list(cf_map.keys())}")
            # 如果有参与者类字段，单独打印
            participant_keys = ['参与者', '参与人', '相关人员', '协同人', '参与人员', 'participant', 'participants']
            for pk in participant_keys:
                if pk in cf_map and cf_map[pk]:
                    logger.info(f"[convert_yunxiao_bugs] Bug#{idx+1} 发现参与者字段 '{pk}': {cf_map[pk]}")

        bugs.append(bug)

    logger.info(f"[convert_yunxiao_bugs] 转换完成: {len(bugs)} 条")
    return bugs
