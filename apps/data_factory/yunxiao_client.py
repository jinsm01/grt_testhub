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
            resp = self.session.request(method, url, timeout=30, **kwargs)
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
        elif field_format == "user" and values:
            result[field_name] = _extract_name(values)
        else:
            # 其他类型直接取值
            if isinstance(values, list):
                result[field_name] = values[0] if len(values) == 1 else values
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
    bugs = []
    for item in raw_workitems:
        # 解析 customFieldValues 数组（云效新版格式）
        custom_field_values = item.get("customFieldValues", [])
        cf_map = _extract_custom_field_values(custom_field_values)

        # 兼容旧版格式
        custom_fields_legacy = item.get("customFields") or item.get("fieldValueMap") or item.get("extraFields", {})
        if isinstance(custom_fields_legacy, dict):
            cf_map.update(custom_fields_legacy)

        bug = {
            "id": item.get("id") or item.get("serialNumber") or item.get("identifier"),
            "title": item.get("subject") or item.get("title") or item.get("name", ""),
            "description": item.get("description") or item.get("content", ""),
            "status": _extract_name(item.get("status")),
            "severity": cf_map.get("严重程度") or cf_map.get("seriousLevel") or item.get("severity") or item.get("severityName", ""),
            "priority": cf_map.get("优先级") or cf_map.get("priority") or item.get("priority") or item.get("priorityName", ""),
            "module": cf_map.get("所属模块") or cf_map.get("功能模块") or cf_map.get("module") or item.get("module") or item.get("moduleName", ""),
            "creator": _extract_name(item.get("creator")),
            "reporter": _extract_name(item.get("creator")),
            "assignee": _extract_name(item.get("assignedTo")),
            "type": _extract_name(item.get("workitemType")) or item.get("category") or item.get("type", CATEGORY_BUG),
            "created_at": item.get("gmtCreate") or item.get("createdAt") or item.get("createTime", ""),
            "closed_at": item.get("gmtClosed") or item.get("closedAt") or item.get("closeTime", ""),
            "custom_fields": cf_map,
        }

        # 额外保留原始数据（用于前端展示所有字段）
        bug["_raw"] = item

        bugs.append(bug)

    return bugs
