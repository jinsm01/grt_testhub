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
import re
from typing import List, Dict, Optional, Any

import requests

logger = logging.getLogger(__name__)

# 云效 API 接入点
# 中心版统一接入点: openapi-rdc.aliyuncs.com
# Region版使用实例域名，如 https://your-org.devops.aliyuncs.com
YUNXIAO_DOMAIN = "https://openapi-rdc.aliyuncs.com"

# 默认组织 ID (硬编码 - 团队统一组织)
DEFAULT_ORGANIZATION_ID = "68d8e1cb66aca23eccbd5e0a"

# 工作项类型: 缺陷
CATEGORY_BUG = "Bug"

# 自定义字段值映射 (displayValue -> identifier)
# 从实际云效项目中提取, 用于创建工作项时转换显示值为标识符
SEVERITY_VALUE_MAP = {
    # 云效数字编号格式（单横杠）
    "1-致命": "bb82d190a4a5a866eaea26c878",
    "2-严重": "ea83daaf913f8a287abe48b80d",
    "3-一般": "1e6094d49e58006000b29bab40",
    "4-轻微": "c3a209a534e6ea640ba71ee004",
    # 云效数字编号格式（双横杠，如 "3--一般"）
    "1--致命": "bb82d190a4a5a866eaea26c878",
    "2--严重": "ea83daaf913f8a287abe48b80d",
    "3--一般": "1e6094d49e58006000b29bab40",
    "4--轻微": "c3a209a534e6ea640ba71ee004",
    # P等级格式（本地使用）
    "P0": "bb82d190a4a5a866eaea26c878",
    "P1": "ea83daaf913f8a287abe48b80d",  # P1 ≈ 严重
    "P2": "1e6094d49e58006000b29bab40",  # P2 ≈ 一般
    "P3": "c3a209a534e6ea640ba71ee004",  # P3 ≈ 轻微
    "P4": "",
    # 纯中文格式
    "致命": "bb82d190a4a5a866eaea26c878",
    "严重": "ea83daaf913f8a287abe48b80d",
    "一般": "1e6094d49e58006000b29bab40",
    "轻微": "c3a209a534e6ea640ba71ee004",
    "建议": "",
}

# 严重程度反向映射: 云效显示值/identifier -> 本地P等级格式
# 用于从云效拉取数据后统一转换为 P0-P3 格式
SEVERITY_TO_P_MAP = {
    # 云效数字编号 -> P等级
    "1": "P0", "1-致命": "P0", "1--致命": "P0",
    "2": "P1", "2-严重": "P1", "2--严重": "P1",
    "3": "P2", "3-一般": "P2", "3--一般": "P2",
    "4": "P3", "4-轻微": "P3", "4--轻微": "P3",
    # identifier -> P等级
    "ea83daaf913f8a287abe48b80d": "P1",
    "1e6094d49e58006000b29bab40": "P2",
    "c3a209a534e6ea640ba71ee004": "P3",
    # 纯中文 -> P等级
    "致命": "P0", "严重": "P1", "一般": "P2", "轻微": "P3", "建议": "P4",
    # P等级自身映射
    "P0": "P0", "P1": "P1", "P2": "P2", "P3": "P3", "P4": "P4",
    # 带中文描述的P等级（如 "P2-一般"）
    "P0-致命": "P0", "P1-严重": "P1", "P2-一般": "P2", "P3-轻微": "P3", "P4-建议": "P4",
}

# 严重程度反向映射: identifier/P等级/各种格式 -> 云效标准显示格式
# 用于从云效拉取数据后统一转换为云效原生显示格式（与云效平台一致）
SEVERITY_TO_DISPLAY_MAP = {
    # identifier -> 云效显示格式
    "bb82d190a4a5a866eaea26c878": "1-致命",
    "ea83daaf913f8a287abe48b80d": "2-严重",
    "1e6094d49e58006000b29bab40": "3-一般",
    "c3a209a534e6ea640ba71ee004": "4-轻微",
    # P等级 -> 云效显示格式
    "P0": "1-致命", "P1": "2-严重", "P2": "3-一般", "P3": "4-轻微", "P4": "4-轻微",
    # 纯数字 -> 云效显示格式
    "1": "1-致命", "2": "2-严重", "3": "3-一般", "4": "4-轻微",
    # 单横杠格式（已是云效格式，保持不变）
    "1-致命": "1-致命", "2-严重": "2-严重", "3-一般": "3-一般", "4-轻微": "4-轻微",
    # 双横杠格式 -> 单横杠
    "1--致命": "1-致命", "2--严重": "2-严重", "3--一般": "3-一般", "4--轻微": "4-轻微",
    # 纯中文 -> 云效显示格式
    "致命": "1-致命", "严重": "2-严重", "一般": "3-一般", "轻微": "4-轻微", "建议": "4-轻微",
    # 带中文描述的P等级 -> 云效显示格式
    "P0-致命": "1-致命", "P1-严重": "2-严重", "P2-一般": "3-一般", "P3-轻微": "4-轻微", "P4-建议": "4-轻微",
}


PRIORITY_VALUE_MAP = {
    "紧急": "bbcfd59822418c4db9a0aee427",
    "高": "6cf54369e61c70354317af5331",
    "中": "4960b27f8aca5963455f767ff1",
    "低": "883c53c3d49b90bea1adccf684",
}

# 默认分页大小
DEFAULT_PAGE_SIZE = 50


class YunxiaoAPIError(Exception):
    """云效 API 错误"""
    pass


class YunxiaoClient:
    """云效 API 客户端"""

    def __init__(self, token: str, organization_id: str = DEFAULT_ORGANIZATION_ID, domain: str = YUNXIAO_DOMAIN):
        """
        初始化客户端

        Args:
            token: 云效个人访问令牌 (PAT)
            organization_id: 组织 ID (默认使用硬编码的团队组织ID)
            domain: API 域名，默认 https://devops.aliyun.com
        """
        self.token = token
        self.organization_id = organization_id or DEFAULT_ORGANIZATION_ID
        self.domain = domain.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "x-yunxiao-token": self.token,
        })
        # 状态缓存: {space_id: {status_name: status_id}}
        # 因为云效没有公开获取状态列表的API，我们从工作项数据中自动收集
        self._status_cache: Dict[str, Dict[str, str]] = {}

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
            status_code = resp.status_code
            response_body = resp.text
            logger.info(f"[YunxiaoClient] response status={status_code} | body={response_body[:800]}")
            
            if status_code >= 400:
                # 直接处理HTTP错误，避免raise_for_status()丢失response
                raise YunxiaoAPIError(f"云效 API 请求失败 (HTTP {status_code}): {response_body[:500]}")
            
            text = response_body.strip()
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
        except YunxiaoAPIError:
            raise
        except requests.exceptions.RequestException as e:
            logger.warning(f"云效 API 请求异常: {e}")
            raise YunxiaoAPIError(f"云效 API 请求异常: {e}")

    # ============================================================
    # 用户相关
    # ============================================================

    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """
        根据当前 Token 获取云效用户信息

        云效接口: GET /oapi/v1/platform/user
        返回: {id, name, nickName, username, email, ...}
        其中 id 即为云效用户ID (verifier/assignedTo 字段所需)
        """
        url = f"{self.domain}/oapi/v1/platform/user"
        try:
            resp = self.session.get(url, timeout=30)
            if resp.status_code >= 400:
                logger.warning(f"[get_current_user] HTTP {resp.status_code}: {resp.text[:300]}")
                return None
            data = resp.json()
            if isinstance(data, dict) and "errorCode" in data:
                logger.warning(f"[get_current_user] API error: {data}")
                return None
            logger.info(f"[get_current_user] user: id={data.get('id')}, name={data.get('name')}")
            return data
        except Exception as e:
            logger.warning(f"[get_current_user] 请求异常: {e}")
            return None

    # ============================================================
    # 项目相关
    # ============================================================

    def search_projects(self, keyword: str = "", page: int = 1, per_page: int = 50) -> List[Dict]:
        """
        搜索项目列表 (优先使用搜索接口，若失败则回退到列表接口)
        """
        # 先尝试搜索接口
        try:
            projects = self._search_projects_via_api(keyword, page, per_page)
            if projects:
                return projects
            logger.info("[search_projects] 搜索接口返回空，尝试回退到列表接口")
        except Exception as e:
            logger.warning(f"[search_projects] 搜索接口异常: {e}, 尝试回退到列表接口")

        # 回退: 使用列表接口
        return self._list_projects_via_api(page, per_page)

    def _search_projects_via_api(self, keyword: str = "", page: int = 1, per_page: int = 50) -> List[Dict]:
        """通过搜索接口获取项目"""
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
        logger.info(f"[search_projects_via_api] 原始响应: {json.dumps(data, ensure_ascii=False)[:500]}")

        if isinstance(data, list):
            return data

        # 尝试多种可能的响应结构
        result = (
            data.get("projects")
            or data.get("items")
            or data.get("result")
            or (data.get("data", {}).get("projects") if isinstance(data.get("data"), dict) else None)
            or (data.get("data") if isinstance(data.get("data"), list) else None)
            or []
        )
        logger.info(f"[search_projects_via_api] 解析后项目数: {len(result)}")
        return result

    def _list_projects_via_api(self, page: int = 1, per_page: int = 50) -> List[Dict]:
        """通过列表接口获取所有项目"""
        url_path = "/projects"
        params = {
            "page": page,
            "perPage": min(per_page, 200),
        }
        data = self._request("GET", url_path, params=params)
        logger.info(f"[list_projects_via_api] 原始响应: {json.dumps(data, ensure_ascii=False)[:500]}")

        if isinstance(data, list):
            return data

        result = (
            data.get("projects")
            or data.get("items")
            or data.get("result")
            or data.get("list")
            or (data.get("data", {}).get("projects") if isinstance(data.get("data"), dict) else None)
            or (data.get("data", {}).get("items") if isinstance(data.get("data"), dict) else None)
            or (data.get("data") if isinstance(data.get("data"), list) else None)
            or []
        )
        logger.info(f"[list_projects_via_api] 解析后项目数: {len(result)}")
        return result

    # ============================================================
    # 迭代相关
    # ============================================================

    def list_sprints(self, space_id: str, page: int = 1, per_page: int = 50) -> List[Dict]:
        """
        获取指定项目的迭代列表

        云效接口: GET /oapi/v1/projex/organizations/{organizationId}/projects/{id}/sprints
        """
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

        result = self._request("POST", url_path, json=payload)
        
        # 自动收集状态映射
        workitems = []
        if isinstance(result, list):
            workitems = result
        elif isinstance(result, dict):
            workitems = result.get("data") or result.get("workitems") or result.get("list") or []
        if workitems:
            self._collect_statuses_from_workitems(space_id, workitems)
        
        return result

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
    # 工作项写入相关 (Bug 创建/更新)
    # ============================================================

    def create_workitem(
        self,
        space_id: str,
        workitem_type_id: str,
        subject: str,
        description: str = "",
        sprint_id: Optional[str] = None,
        priority: Optional[str] = None,
        severity: Optional[str] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        创建工作项 (Bug)

        云效接口: POST /oapi/v1/projex/organizations/{organizationId}/workitems
        
        正确格式:
        - workitemTypeId: 工作项类型ID (如 "37da3a07df4d08aef2e3b393")
        - assignedTo: 指派人用户ID
        - verifier: 验证人用户ID
        - sprint: 迭代ID
        - labels: 标签名称数组
        - customFieldValues: 自定义字段 {fieldId: value}
        """
        url_path = "/workitems"
        payload: Dict[str, Any] = {
            "spaceId": space_id,
            "workitemTypeId": workitem_type_id,
            "subject": subject,
        }
        if description:
            payload["description"] = description
        if sprint_id:
            payload["sprint"] = sprint_id
        
        # 解析严重程度和优先级为标识符
        severity_id = self._resolve_severity_value(severity) if severity else None
        priority_id = self._resolve_priority_value(priority) if priority else None
        
        if severity_id:
            payload.setdefault("customFieldValues", {})["seriousLevel"] = severity_id
        if priority_id:
            payload.setdefault("customFieldValues", {})["priority"] = priority_id

        # Map kwargs to Yunxiao field names
        assignee = kwargs.pop('assignee', None)
        if assignee:
            payload["assignedTo"] = assignee

        verifier = kwargs.pop('verifier', None)
        if verifier:
            payload["verifier"] = verifier

        labels = kwargs.pop('labels', None)
        # 云效API要求labels字段必须存在，即使是空数组
        # labels需要解析为标签ID数组（名称会自动查找或创建标签）
        if labels:
            payload["labels"] = self._resolve_label_ids(space_id, labels)
        else:
            payload["labels"] = []

        # Merge custom_fields
        if custom_fields:
            cf = payload.get("customFieldValues", {})
            cf.update(custom_fields)
            payload["customFieldValues"] = cf

        for key, val in kwargs.items():
            if val is not None:
                payload[key] = val

        logger.info(f"[create_workitem] payload: {json.dumps(payload, ensure_ascii=False)[:500]}")
        return self._request("POST", url_path, json=payload)

    def update_workitem(
        self,
        workitem_id: str,
        subject: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        priority: Optional[str] = None,
        assignee: Optional[str] = None,
        verifier: Optional[str] = None,
        labels: Optional[List[str]] = None,
        space_id: Optional[str] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        更新工作项

        云效接口: PUT /oapi/v1/projex/organizations/{organizationId}/workitems/{id}
        
        Args:
            space_id: 项目空间ID，用于解析status/labels名称到ID。若传的是ID可不传。
        """
        url_path = f"/workitems/{workitem_id}"
        payload: Dict[str, Any] = {}
        if subject is not None:
            payload["subject"] = subject
        if description is not None:
            payload["description"] = description
        if status is not None:
            # status需要解析为状态ID（名称会自动查找对应ID）
            if space_id and status:
                payload["status"] = self._resolve_status_id(space_id, status)
            else:
                payload["status"] = status
        if assignee is not None:
            payload["assignedTo"] = assignee
        if verifier is not None:
            payload["verifier"] = verifier
        if labels is not None:
            # labels需要解析为标签ID数组（名称会自动查找或创建标签）
            if space_id and labels:
                payload["labels"] = self._resolve_label_ids(space_id, labels)
            else:
                payload["labels"] = labels if labels else []

        # 处理自定义字段 - 更新接口使用直接字段名
        if severity:
            payload["seriousLevel"] = self._resolve_severity_value(severity)
        if priority:
            payload["priority"] = self._resolve_priority_value(priority)

        # Merge custom_fields
        if custom_fields:
            cf = payload.get("customFieldValues", {})
            cf.update(custom_fields)
            payload["customFieldValues"] = cf

        for key, val in kwargs.items():
            if val is not None:
                payload[key] = val

        logger.info(f"[update_workitem] payload: {json.dumps(payload, ensure_ascii=False)[:500]}")
        return self._request("PUT", url_path, json=payload)

    def create_bug(
        self,
        space_id: str,
        subject: str,
        description: str = "",
        sprint_id: Optional[str] = None,
        priority: Optional[str] = None,
        severity: Optional[str] = None,
        workitem_type_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        创建 Bug (封装 create_workitem)
        
        Args:
            workitem_type_id: 工作项类型ID, 若不提供则自动查找Bug类型
        """
        if not workitem_type_id:
            workitem_type_id = self._resolve_workitem_type_id(space_id, CATEGORY_BUG)
        return self.create_workitem(
            space_id=space_id,
            workitem_type_id=workitem_type_id,
            subject=subject,
            description=description,
            sprint_id=sprint_id,
            priority=priority,
            severity=severity,
            **kwargs
        )

    def update_bug_status(self, workitem_id: str, status: str, space_id: Optional[str] = None) -> Dict[str, Any]:
        """
        单独更新 Bug 状态

        云效接口: PUT /oapi/v1/projex/organizations/{organizationId}/workitems/{id}
        
        Args:
            space_id: 项目空间ID，用于解析状态名称到ID
        """
        return self.update_workitem(workitem_id=workitem_id, status=status, space_id=space_id)

    def upload_attachment(self, workitem_id: str, file_content: bytes, filename: str, content_type: str = "") -> Dict[str, Any]:
        """
        上传附件到工作项

        云效接口: POST /oapi/v1/projex/organizations/{organizationId}/workitems/{id}/attachments
        Content-Type: multipart/form-data

        Args:
            workitem_id: 工作项ID
            file_content: 文件二进制内容
            filename: 原始文件名
            content_type: 文件MIME类型（可选）

        Returns:
            {
                "id": "文件ID",
                "name": "文件名",
                "size": 文件大小,
                "suffix": ".png",
                "url": "临时下载地址",
                "embedUrl": "永久嵌入地址（描述中用）",
                "embedHtml": "<img src='...'/>",
                "embedMarkdown": "![image](...)"
            }
        """
        url_path = f"/workitems/{workitem_id}/attachments"
        url = self._get_base_url(url_path)
        
        # multipart/form-data 请求不能预设 Content-Type，让 requests 自动生成 boundary
        headers = {
            "x-yunxiao-token": self.token,
        }
        
        files = {
            "file": (filename, file_content, content_type if content_type else "application/octet-stream")
        }
        
        logger.info(f"[upload_attachment] 上传附件 {filename} 到工作项 {workitem_id}, 大小: {len(file_content)} bytes")
        
        try:
            resp = requests.post(url, headers=headers, files=files, timeout=120)
            status_code = resp.status_code
            response_body = resp.text
            logger.info(f"[upload_attachment] response status={status_code} | body={response_body[:500]}")
            
            if status_code >= 400:
                raise YunxiaoAPIError(f"上传附件失败 (HTTP {status_code}): {response_body[:500]}")
            
            data = resp.json()
            if isinstance(data, dict) and not data.get("success", True) and "errorCode" in data:
                raise YunxiaoAPIError(f"上传附件错误 [{data.get('errorCode')}]: {data.get('errorMessage', '')}")
            
            return data
        except requests.exceptions.RequestException as e:
            logger.warning(f"上传附件请求异常: {e}")
            raise YunxiaoAPIError(f"上传附件请求异常: {e}")

    def list_workitem_attachments(self, workitem_id: str) -> List[Dict]:
        """
        获取工作项附件列表

        云效接口: GET /oapi/v1/projex/organizations/{organizationId}/workitems/{id}/attachments
        """
        url_path = f"/workitems/{workitem_id}/attachments"
        return self._request("GET", url_path)

    def add_comment(self, workitem_id: str, content: str) -> Dict[str, Any]:
        """
        给工作项添加评论

        云效接口: POST /oapi/v1/projex/organizations/{organizationId}/workitems/{id}/comments

        Args:
            workitem_id: 工作项ID
            content: 评论内容（支持Markdown格式，可嵌入图片）

        Returns:
            创建的评论对象
        """
        url_path = f"/workitems/{workitem_id}/comments"
        payload = {"content": content}
        logger.info(f"[add_comment] 给工作项 {workitem_id} 添加评论: {content[:100]}")
        return self._request("POST", url_path, json=payload)

    def get_workitem(self, workitem_id: str, space_id: str = None) -> Dict[str, Any]:
        """
        获取单个工作项详情

        云效接口: GET /oapi/v1/projex/organizations/{organizationId}/workitems/{id}
        
        Args:
            workitem_id: 工作项ID
            space_id: 项目ID（可选，用于状态缓存）
        """
        url_path = f"/workitems/{workitem_id}"
        result = self._request("GET", url_path)
        # 自动收集状态映射
        if space_id and isinstance(result, dict):
            self._collect_statuses_from_workitems(space_id, [result])
        return result

    def list_workitem_statuses(self, space_id: str) -> List[Dict]:
        """
        获取工作项状态列表（已废弃，云效该API返回404）
        
        改用_status_cache自动从工作项数据中收集状态映射
        """
        return []
    
    def _collect_statuses_from_workitems(self, space_id: str, workitems: List[Dict]) -> None:
        """
        从工作项列表中收集状态名称->ID映射，更新缓存
        
        Args:
            space_id: 项目ID
            workitems: 工作项列表，每个workitem的status字段包含id和name
        """
        if not space_id or not workitems:
            return
        if space_id not in self._status_cache:
            self._status_cache[space_id] = {}
        cache = self._status_cache[space_id]
        for w in workitems:
            if not isinstance(w, dict):
                continue
            st = w.get("status")
            if isinstance(st, dict):
                st_id = str(st.get("id") or st.get("statusId") or "").strip()
                st_name = str(st.get("name") or st.get("displayName") or "").strip()
                st_name_en = str(st.get("nameEn") or st.get("enName") or "").strip()
                if st_id and st_name:
                    cache[st_name] = st_id
                if st_id and st_name_en:
                    cache[st_name_en] = st_id
        logger.debug(f"[_collect_statuses] space={space_id} 缓存状态数: {len(cache)}")

    def _resolve_status_id(self, space_id: str, status: str) -> str:
        """
        将状态值（可能是ID或名称）解析为状态ID（identifier）。
        
        实现方案：
        - 如果传入值本身就是ID（非中文、短数字），直接返回
        - 从_status_cache查找名称对应的ID
        - 缓存未命中时，主动搜索一页Bug收集状态映射到缓存
        - 状态ID可能是24位hex，也可能是短数字（如"28"）
        
        Args:
            space_id: 项目ID
            status: 状态值（名称或ID）
        """
        if not status:
            return ""
        status = str(status).strip()
        if not status:
            return ""
        
        # 判断是否已经是ID格式（不包含中文字符，且不是空）
        has_chinese = any('\u4e00' <= c <= '\u9fff' for c in status)
        if not has_chinese:
            # 非中文，可能已经是ID，直接返回
            return status
        
        # 中文状态名，需要查找对应ID
        cache = self._status_cache.get(space_id, {})
        if status in cache:
            logger.info(f"[_resolve_status_id] 缓存命中: '{status}' -> {cache[status]}")
            return cache[status]
        
        # 缓存未命中，主动搜索Bug收集状态（低频状态如「再次打开」需要更多数据）
        logger.info(f"[_resolve_status_id] 缓存未命中，搜索Bug收集状态: space={space_id}, status='{status}'")
        try:
            for page in (1, 2):
                result = self.search_workitems(
                    space_id=space_id,
                    category=CATEGORY_BUG,
                    page=page,
                    per_page=200
                )
                # search_workitems会自动调用_collect_statuses_from_workitems更新缓存
                cache = self._status_cache.get(space_id, {})
                if status in cache:
                    logger.info(f"[_resolve_status_id] 收集后找到: '{status}' -> {cache[status]}")
                    return cache[status]

                # 如果中文名称没找到，试试nameEn（英文）匹配
                for name, sid in cache.items():
                    if name.lower() == status.lower():
                        logger.info(f"[_resolve_status_id] 通过nameEn匹配: '{status}' -> {sid}")
                        return sid

                # 检查搜索结果是否为空，为空则不需要翻页
                workitems = []
                if isinstance(result, list):
                    workitems = result
                elif isinstance(result, dict):
                    workitems = result.get("data") or result.get("workitems") or result.get("list") or []
                if not workitems:
                    break
        except Exception as e:
            logger.warning(f"[_resolve_status_id] 搜索Bug收集状态失败: {e}")
        
        # 最终找不到，记录警告并返回原值（期望云效API能处理，或给出明确错误）
        logger.warning(f"[_resolve_status_id] 未找到状态 '{status}' 对应的ID，缓存状态: {list(cache.keys())}")
        return status

    def get_workitem_types(self, space_id: str) -> List[Dict]:
        """
        获取项目的工作项类型列表

        云效接口: GET /oapi/v1/projex/organizations/{organizationId}/workitemTypes
        """
        url_path = "/workitemTypes"
        data = self._request("GET", url_path, params={"spaceId": space_id})
        if isinstance(data, list):
            return data
        return []

    def list_project_members(self, space_id: str) -> List[Dict]:
        """
        获取项目成员列表

        云效接口: GET /oapi/v1/projex/organizations/{organizationId}/projects/{spaceId}/members
        """
        url_path = f"/projects/{space_id}/members"
        data = self._request("GET", url_path)
        if isinstance(data, list):
            return data
        return data.get("members") or data.get("data", {}).get("members", []) or []

    def list_project_labels(self, space_id: str) -> List[Dict]:
        """
        获取项目标签列表 (用于模块选择)

        云效接口: GET /oapi/v1/projex/organizations/{organizationId}/projects/{spaceId}/labels
        """
        url_path = f"/projects/{space_id}/labels"
        data = self._request("GET", url_path)
        if isinstance(data, list):
            return data
        return data.get("labels") or data.get("data", {}).get("labels", []) or []

    def create_label(self, space_id: str, name: str, color: str = "#1890ff") -> Optional[Dict]:
        """
        创建项目标签

        云效接口: POST /oapi/v1/projex/organizations/{organizationId}/projects/{spaceId}/labels
        """
        url_path = f"/projects/{space_id}/labels"
        payload = {"name": name, "color": color}
        try:
            result = self._request("POST", url_path, json=payload)
            logger.info(f"[create_label] 创建标签 '{name}' 成功: {result}")
            if isinstance(result, dict):
                # 兼容多种返回结构
                label = result.get("label") or result.get("data") or result
                if isinstance(label, dict) and (label.get("id") or label.get("labelId")):
                    return label
            return None
        except YunxiaoAPIError as e:
            logger.warning(f"[create_label] 创建标签 '{name}' 失败: {e}")
            return None

    def _resolve_label_ids(self, space_id: str, labels: Optional[List[str]]) -> List[str]:
        """
        将标签值（可能是ID或名称混合）解析为纯标签ID数组。
        
        - 如果是24位hex格式，直接认为是ID
        - 如果是名称字符串，先查标签列表，找到对应ID
        - 如果是不存在的名称，尝试创建标签再获取ID
        - 最终只返回确认存在的ID列表
        """
        if not labels:
            return []
        
        resolved_ids = []
        try:
            all_labels = self.list_project_labels(space_id)
            # 构建 name -> id 映射
            name_to_id = {}
            for lb in all_labels:
                lb_name = lb.get("name") or lb.get("labelName") or ""
                lb_id = lb.get("id") or lb.get("labelId") or ""
                if lb_name and lb_id:
                    name_to_id[lb_name] = lb_id
        except Exception as e:
            logger.warning(f"[_resolve_label_ids] 获取标签列表失败: {e}")
            name_to_id = {}
        
        for label_val in labels:
            if not label_val or not isinstance(label_val, str):
                continue
            label_val = label_val.strip()
            if not label_val:
                continue
            
            # 已经是ID格式（24位hex）
            if len(label_val) == 24 and all(c in '0123456789abcdef' for c in label_val.lower()):
                resolved_ids.append(label_val)
                continue
            
            # 是名称，查找对应ID
            if label_val in name_to_id:
                resolved_ids.append(name_to_id[label_val])
                continue
            
            # 名称不存在，尝试创建标签
            logger.info(f"[_resolve_label_ids] 标签 '{label_val}' 不存在，尝试创建")
            new_label = self.create_label(space_id, label_val)
            if new_label:
                new_id = new_label.get("id") or new_label.get("labelId") or ""
                if new_id:
                    name_to_id[label_val] = new_id  # 缓存新标签
                    resolved_ids.append(new_id)
                    continue
            
            logger.warning(f"[_resolve_label_ids] 无法解析标签: '{label_val}'，将跳过")
        
        logger.info(f"[_resolve_label_ids] 原始labels={labels} -> 解析后IDs={resolved_ids}")
        return resolved_ids

    def _resolve_label_name(self, space_id: str, label_val: str) -> str:
        """
        将标签值（可能是ID或名称）解析为标签名称（用于本地存储/显示）。
        
        - 如果是24位hex格式（ID），查标签列表找对应名称
        - 如果已经是名称字符串（非ID），直接返回
        - 找不到时返回原值
        """
        if not label_val or not isinstance(label_val, str):
            return ""
        label_val = label_val.strip()
        if not label_val:
            return ""
        
        # 如果不是ID格式（24位hex），直接当作名称返回
        is_id_format = len(label_val) == 24 and all(c in '0123456789abcdef' for c in label_val.lower())
        if not is_id_format:
            return label_val
        
        # 是ID，查找对应名称
        try:
            all_labels = self.list_project_labels(space_id)
            id_to_name = {}
            for lb in all_labels:
                lb_id = lb.get("id") or lb.get("labelId") or ""
                lb_name = lb.get("name") or lb.get("labelName") or ""
                if lb_id and lb_name:
                    id_to_name[lb_id] = lb_name
            if label_val in id_to_name:
                return id_to_name[label_val]
        except Exception as e:
            logger.warning(f"[_resolve_label_name] 获取标签列表失败: {e}")
        
        # 找不到对应名称，返回原值
        return label_val

    def _resolve_workitem_type_id(self, space_id: str, category_id: str) -> str:
        """
        根据 categoryId 查找对应的工作项类型ID
        
        如 categoryId='Bug' -> 查找 categoryId='Bug' 的工作项类型
        优先使用 "缺陷" 类型 (nameEn=Bug)
        """
        try:
            types = self.get_workitem_types(space_id)
            # 优先选择 nameEn='Bug' 的类型 (标准缺陷)
            for t in types:
                if t.get("categoryId") == category_id and t.get("nameEn") == "Bug":
                    return t["id"]
            # 回退: 选择第一个匹配的类型
            for t in types:
                if t.get("categoryId") == category_id:
                    return t["id"]
        except Exception as e:
            logger.warning(f"[_resolve_workitem_type_id] 查找工作项类型失败: {e}")
        return "37da3a07df4d08aef2e3b393"  # 默认: 缺陷

    def _resolve_severity_value(self, severity: str) -> str:
        """将严重程度显示值转换为标识符（用于推送到云效）"""
        if not severity:
            return ""
        # 先标准化为P等级，再映射到identifier
        normalized = self.normalize_severity_from_yunxiao(severity)
        if normalized in SEVERITY_VALUE_MAP and SEVERITY_VALUE_MAP[normalized]:
            return SEVERITY_VALUE_MAP[normalized]
        # 直接匹配原始值
        if severity in SEVERITY_VALUE_MAP and SEVERITY_VALUE_MAP[severity]:
            return SEVERITY_VALUE_MAP[severity]
        # 尝试前缀匹配 (如 "P2-一般" -> "P2")
        prefix = severity.split("-")[0] if "-" in severity else severity
        if prefix in SEVERITY_VALUE_MAP and SEVERITY_VALUE_MAP[prefix]:
            return SEVERITY_VALUE_MAP[prefix]
        # 如果本身就是标识符格式
        if len(severity) == 24 and all(c in '0123456789abcdef' for c in severity):
            return severity
        return severity  # 返回原值，由API判断

    @staticmethod
    def normalize_severity_from_yunxiao(severity: str) -> str:
        """
        将各种严重程度格式统一转换为云效标准显示格式（与云效平台显示一致）
        
        输出格式: "1-致命", "2-严重", "3-一般", "4-轻微"
        
        支持的输入格式:
        - 云效数字编号: "1-致命", "2-严重", "3-一般", "3--一般", "4-轻微"
        - 纯数字: "1", "2", "3", "4"
        - 中文: "致命", "严重", "一般", "轻微"
        - identifier: "ea83daaf913f8a287abe48b80d" 等
        - P等级: "P0", "P1", "P2-一般" 等
        """
        if not severity:
            return ""
        severity = str(severity).strip()
        
        # 精确匹配
        if severity in SEVERITY_TO_DISPLAY_MAP:
            return SEVERITY_TO_DISPLAY_MAP[severity]
        
        # 尝试匹配前缀（如 "3--一般" 取 "3"）
        if "-" in severity:
            # 双横杠情况: "3--一般" -> 取 "3"
            if "--" in severity:
                prefix = severity.split("--")[0].strip()
                if prefix in SEVERITY_TO_DISPLAY_MAP:
                    return SEVERITY_TO_DISPLAY_MAP[prefix]
            # 单横杠: "P2-一般" 取 "P2"
            prefix = severity.split("-")[0].strip()
            if prefix in SEVERITY_TO_DISPLAY_MAP:
                return SEVERITY_TO_DISPLAY_MAP[prefix]
        
        # identifier格式（24位hex）
        if len(severity) == 24 and all(c in '0123456789abcdef' for c in severity.lower()):
            if severity in SEVERITY_TO_DISPLAY_MAP:
                return SEVERITY_TO_DISPLAY_MAP[severity]
        
        # 如果本身就是数字开头加横杠的云效格式，直接返回
        if len(severity) >= 3 and severity[0] in '1234' and severity[1] == '-':
            return severity
        
        # 无法识别时，尝试包含匹配
        for key, val in SEVERITY_TO_DISPLAY_MAP.items():
            if key in severity or severity in key:
                return val
        
        return severity  # 无法识别时返回原值

    def _resolve_priority_value(self, priority: str) -> str:
        """将优先级显示值转换为标识符"""
        if not priority:
            return ""
        if priority in PRIORITY_VALUE_MAP and PRIORITY_VALUE_MAP[priority]:
            return PRIORITY_VALUE_MAP[priority]
        if len(priority) == 24 and all(c in '0123456789abcdef' for c in priority):
            return priority
        return priority


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

# 中文字符正则
_CJK_RE = re.compile(r'[\u4e00-\u9fff]')


def _pick_module_name_from_labels(label_names: List[str]) -> str:
    """
    从多个 label 中挑选最像模块名的那个
    - 优先选包含中文字符的标签（排除ID/乱码）
    - 再优先选不含状态/类型类关键词的 label
    - 都包含则回退到第一个中文标签或第一个标签
    - 空列表返回空串
    """
    if not label_names:
        return ""
    
    # 第一步：过滤出包含中文字符的标签（排除24位hex ID和乱码）
    chinese_labels = [n for n in label_names if n and _CJK_RE.search(n)]
    candidates = chinese_labels if chinese_labels else label_names
    
    # 第二步：从候选中优先选不含状态关键词的
    for name in candidates:
        if name and not any(kw in name for kw in _NON_MODULE_KEYWORDS):
            return name
    
    # 都包含关键词，回退到第一个
    return candidates[0] if candidates else label_names[0]


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
            "severity": YunxiaoClient.normalize_severity_from_yunxiao(
                cf_map.get("严重程度") or cf_map.get("seriousLevel") or item.get("severity") or item.get("severityName", "")
            ),
            "priority": cf_map.get("优先级") or cf_map.get("priority") or item.get("priority") or item.get("priorityName", ""),
            "module": (_pick_module_name_from_labels(label_names) or
                       cf_map.get("所属模块") or cf_map.get("功能模块") or
                       cf_map.get("module") or item.get("module") or item.get("moduleName", "")),
            "labels": label_names,
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


def convert_to_yunxiao_format(bug: Dict[str, Any], space_id: str) -> Dict[str, Any]:
    """
    将内部 Bug 格式转换为云效 API 所需的创建/更新格式 (兼容旧版)
    
    注意: 新代码应直接使用 create_bug / update_bug 方法，此函数仅用于向后兼容
    """
    payload: Dict[str, Any] = {
        "spaceId": space_id,
        "workitemTypeId": CATEGORY_BUG,  # 需要通过 _resolve_workitem_type_id 解析
        "subject": bug.get("title") or bug.get("subject") or "",
    }

    description = bug.get("desc") or bug.get("description") or ""
    if description:
        payload["description"] = description

    sprint_id = bug.get("sprint_id") or bug.get("sprintId")
    if sprint_id:
        payload["sprint"] = sprint_id

    # 自定义字段使用对象格式
    custom_fields = {}
    cf = bug.get("custom_fields") or {}

    if cf.get("严重程度"):
        custom_fields["seriousLevel"] = cf["严重程度"]
    elif bug.get("severity"):
        custom_fields["seriousLevel"] = bug["severity"]

    if cf.get("优先级"):
        custom_fields["priority"] = cf["优先级"]
    elif bug.get("priority"):
        custom_fields["priority"] = bug["priority"]

    if custom_fields:
        payload["customFieldValues"] = custom_fields

    assignee = bug.get("assignee") or bug.get("assignedTo")
    if assignee:
        payload["assignedTo"] = assignee

    verifier = bug.get("verifier")
    if verifier:
        payload["verifier"] = verifier

    return payload
