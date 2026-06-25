# -*- coding: utf-8 -*-
"""
Bug 数据源适配器

统一不同来源的 Bug 数据格式:
1. Excel 文件上传（当前主要方式）
2. 云效 API（预留）
3. Tapd API（预留）
4. JSON 数据直接提交

所有数据源最终标准化为统一的内部 Bug 格式。
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any

import openpyxl
from openpyxl.utils import column_index_from_string

logger = logging.getLogger(__name__)

# ============================================================
# 标准化字段映射
# ============================================================

# Excel 列名 → 内部字段名 的映射表
# 支持多种常见列名变体
EXCEL_COLUMN_MAPPING = {
    # 标题/摘要 (必填)
    '标题': 'title', '摘要': 'title', 'subject': 'title', 'bug标题': 'title',
    '缺陷标题': 'title', '问题标题': 'title', 'bug标题(摘要)': 'title',
    # 描述
    '描述': 'desc', '详情': 'desc', 'description': 'desc', '描述信息': 'desc',
    '缺陷描述': 'desc',
    # 严重度
    '严重度': 'severity', '严重程度': 'severity', '严重等级': 'severity', 'severity': 'severity',
    '严重级别': 'severity', '缺陷等级': 'severity', '缺陷严重度': 'severity',
    # 状态
    '状态': 'status', '当前状态': 'status', '状态名': 'status',
    '解决状态': 'status', 'bug状态': 'status',
    # 优先级
    '优先级': 'priority', 'priority': 'priority',
    # 类型 (功能缺陷/线上故障等)
    '类型': 'type', '缺陷类型': 'type', '分类': 'type',
    '缺陷分类': 'type', '问题类型': 'type',
    # 创建者/报告人
    '创建人': 'creator', '报告人': 'creator', '提出人': 'creator',
    '发现人': 'creator', '创建者': 'creator', '报告者': 'creator',
    '处理人': 'assignee', '负责人': 'assignee', '解决人': 'assignee',
    # 创建时间
    '创建时间': 'created', '创建日期': 'created', '提出时间': 'created',
    '发现时间': 'created', 'created': 'created', '创建日期(创建时间)': 'created',
    # 更新时间
    '更新时间': 'updated', '修改时间': 'updated',
    # 解决方案/备注
    '解决方案': 'solution', '解决结果': 'solution', '备注': 'remark',
}

# 必填字段
REQUIRED_FIELDS = ['title']

# 可选但有分析价值的高优字段
RECOMMENDED_FIELDS = ['severity', 'status', 'creator', 'created', 'type']


class NormalizedBug(Dict):
    """标准化后的 Bug 字典，提供便捷访问"""

    @property
    def title(self) -> str:
        return self.get('title', '')

    @property
    def desc(self) -> str:
        return self.get('desc', '')

    @property
    def severity(self) -> str:
        return self.get('severity', '')

    @property
    def status(self) -> str:
        return self.get('status', '')

    @property
    def creator(self) -> str:
        return self.get('creator', '')

    @property
    def created(self) -> Optional[datetime]:
        return self.get('created')

    @property
    def bug_type(self) -> str:
        return self.get('type', '')

    @property
    def priority(self) -> str:
        return self.get('priority', '')


def _find_column_mapping(headers: List[str]) -> Dict[int, str]:
    """
    根据 Excel 表头行，建立 列索引 → 内部字段名 的映射

    Args:
        headers: Excel 第一行的表头列表

    Returns:
        dict: {col_index: field_name} 映射关系
    """
    mapping = {}
    for col_idx, header in enumerate(headers):
        if not header or not str(header).strip():
            continue
        header_str = str(header).strip()

        # 精确匹配
        if header_str in EXCEL_COLUMN_MAPPING:
            mapping[col_idx] = EXCEL_COLUMN_MAPPING[header_str]
        else:
            # 模糊匹配: 检查是否包含关键词
            for excel_name, field_name in EXCEL_COLUMN_MAPPING.items():
                if excel_name in header_str or header_str in excel_name:
                    mapping[col_idx] = field_name
                    break

    logger.info(f"Excel 列映射结果: {mapping}")
    return mapping


def _parse_date_value(value: Any) -> Optional[datetime]:
    """
    解析日期值，支持多种格式

    支持格式:
    - datetime 对象 (openpyxl 直接解析)
    - float (Excel 序列号日期)
    - int (Unix 时间戳，毫秒或秒)
    - str 常见日期格式字符串 / ISO 8601

    Returns:
        datetime 或 None
    """
    if value is None:
        return None

    # 已是 datetime 对象
    if isinstance(value, datetime):
        return value

    # Excel 序列号日期 (float)
    if isinstance(value, (int, float)):
        # 先尝试 Excel 序列号（通常小于 50000）
        try:
            if float(value) < 50000:
                from openpyxl.utils.datetime import from_excel
                return from_excel(float(value), epoch_mode='1900')
        except (ValueError, TypeError, OverflowError):
            pass
        # 再尝试 Unix 时间戳（毫秒 > 1000000000000，秒 > 1000000000）
        try:
            ts = int(value)
            if ts > 1000000000000:  # 毫秒时间戳
                return datetime.fromtimestamp(ts / 1000)
            elif ts > 1000000000:   # 秒时间戳
                return datetime.fromtimestamp(ts)
        except (ValueError, TypeError, OverflowError, OSError):
            pass
        return None

    # 字符串日期
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None

        # ISO 8601 格式（云效常用）
        if 'T' in value:
            try:
                # 处理带时区的 ISO 格式，如 2024-01-15T10:30:00+08:00
                from datetime import timezone
                # 去掉时区冒号（Python 3.6+ 的 fromisoformat 不支持 +08:00 中的冒号）
                iso_val = value
                if iso_val[-3] == ':' and (iso_val[-6] == '+' or iso_val[-6] == '-'):
                    iso_val = iso_val[:-3] + iso_val[-2:]
                return datetime.fromisoformat(iso_val)
            except (ValueError, TypeError):
                pass

        date_formats = [
            '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d',
            '%Y/%m/%d %H:%M:%S', '%Y/%m/%d %H:%M', '%Y/%m/%d',
            '%Y年%m月%d日', '%Y年%m月%d日 %H时%M分',
            '%m/%d/%Y', '%d/%m/%Y',
        ]
        for fmt in date_formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        logger.debug(f"无法解析日期字符串: {value}")
        return None

    return None


def _sanitize_filename(filename: str) -> str:
    """
    清洗文件名，防止路径穿越攻击

    Args:
        filename: 原始文件名

    Returns:
        str: 安全的文件名 (仅保留 basename)
    """
    if not filename:
        return 'unknown_file.xlsx'
    # 只取 basename，去掉路径部分
    safe = os.path.basename(filename)
    # 移除可能的路径穿越字符
    safe = safe.replace('..', '').replace('/', '').replace('\\', '')
    return safe or 'unknown_file.xlsx'


# ============================================================
# 数据源适配器实现
# ============================================================

class BugSourceAdapter:
    """
    Bug 数据源适配器基类

    所有数据源的统一入口，负责将不同格式的原始数据转换为标准化的内部格式。
    """

    @staticmethod
    def normalize_bug(raw_row: Dict[str, Any]) -> NormalizedBug:
        """
        将单条原始数据标准化为内部格式

        Args:
            raw_row: 原始键值对数据

        Returns:
            NormalizedBug: 标准化后的 Bug 对象
        """
        # 提取原始值用于日志
        created_raw = raw_row.get('created')
        updated_raw = raw_row.get('updated')
        custom_fields_raw = raw_row.get('custom_fields')

        bug = NormalizedBug({
            'title': str(raw_row.get('title', '') or ''),
            'desc': str(raw_row.get('desc', '') or ''),
            'severity': raw_row.get('severity') or '',
            'status': raw_row.get('status') or '',
            'priority': raw_row.get('priority') or '',
            'type': raw_row.get('type') or '',
            'creator': str(raw_row.get('creator', '') or ''),
            'assignee': str(raw_row.get('assignee', '') or ''),
            'created': _parse_date_value(created_raw),
            'updated': _parse_date_value(updated_raw),
            'solution': str(raw_row.get('solution', '') or ''),
            'remark': str(raw_row.get('remark', '') or ''),
            'custom_fields': custom_fields_raw or {},
        })

        # 详细日志：打印关键字段的转换情况
        logger.debug(f"[normalize_bug] 输入字段名: {list(raw_row.keys())}, "
                     f"title={raw_row.get('title', '')[:20]}..., "
                     f"created_raw={created_raw} -> created_parsed={bug['created']}, "
                     f"updated_raw={updated_raw} -> updated_parsed={bug['updated']}, "
                     f"custom_fields={list(custom_fields_raw.keys()) if custom_fields_raw else 'None'}")

        # 如果 created 或 updated 为空，打印警告
        if not bug['created']:
            logger.warning(f"[normalize_bug] created 字段为空! raw_row keys={list(raw_row.keys())}, "
                           f"created_raw={created_raw}, title={bug['title'][:30]}")
        if not bug['updated']:
            logger.warning(f"[normalize_bug] updated 字段为空! raw_row keys={list(raw_row.keys())}, "
                           f"updated_raw={updated_raw}, title={bug['title'][:30]}")

        # 如果 custom_fields 有数据，打印详细内容
        if custom_fields_raw and isinstance(custom_fields_raw, dict) and len(custom_fields_raw) > 0:
            logger.debug(f"[normalize_bug] custom_fields 内容: {custom_fields_raw}")

        return bug

    @staticmethod
    def validate_bugs(bugs: List[NormalizedBug]) -> tuple:
        """
        校验 Bug 列表的基本完整性

        Args:
            bugs: 标准化后的 Bug 列表

        Returns:
            tuple: (is_valid: bool, errors: list[str], warnings: list[str])
        """
        errors = []
        warnings = []

        if bugs is None:
            errors.append("Bug 数据为空 (None)")
            return False, errors, warnings

        if len(bugs) == 0:
            warnings.append("Bug 列表为空，没有可分析的数据")
            return True, [], warnings

        # 检查每条记录
        missing_title_count = 0
        for i, bug in enumerate(bugs):
            if not bug.title.strip():
                missing_title_count += 1

        if missing_title_count > 0:
            ratio = round(missing_title_count / len(bugs) * 100)
            if ratio > 50:
                errors.append(f"超过50% ({ratio}%) 的 Bug 缺少标题字段")
            else:
                warnings.append(f"{missing_title_count} 条 ({ratio}%) Bug 缺少标题字段")

        is_valid = len(errors) == 0
        return is_valid, errors, warnings

    @staticmethod
    def from_excel(file_path: str) -> List[NormalizedBug]:
        """
        从 Excel 文件解析 Bug 数据

        Args:
            file_path: xlsx 文件绝对路径

        Returns:
            list[NormalizedBug]: 解析并标准化后的 Bug 列表

        Raises:
            ValueError: 文件格式错误或无有效数据
            FileNotFoundError: 文件不存在
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Excel 文件不存在: {file_path}")

        # 策略1：优先用 pandas（兼容云效导出等特殊格式）
        try:
            import pandas as pd
            df = pd.read_excel(file_path)
            if df is not None and len(df) > 0:
                headers = [str(c).strip() for c in df.columns]
                col_mapping = _find_column_mapping(headers)
                if col_mapping:
                    bugs = []
                    for _, row in df.iterrows():
                        raw = {col: row.get(col, '') if hasattr(row, 'get') else row[col] for col in df.columns}
                        raw_dict = {}
                        for std_key, col_idx in col_mapping.items():
                            val = raw.get(headers[col_idx], '')
                            if pd.isna(val):
                                val = ''
                            raw_dict[std_key] = str(val).strip()
                        bug = BugSourceAdapter.normalize_bug(raw_dict)
                        bugs.append(bug)
                    if bugs:
                        return bugs
        except Exception:
            pass  # fallback to openpyxl

        # 策略2：openpyxl 兜底
        try:
            wb = openpyxl.load_workbook(file_path, data_only=True)
        except Exception as e:
            raise ValueError(f"无法读取 Excel 文件: {e}")

        ws = wb.active
        if ws is None:
            wb.close()
            raise ValueError("Excel 文件中没有工作表")

        rows = list(ws.iter_rows(values_only=True))
        wb.close()

        if len(rows) <= 1:
            raise ValueError(f"Excel 文件数据不足，只有 {len(rows)} 行 (需要至少2行：表头+数据)")

        # 解析表头，建立映射
        headers = [str(h or '').strip() for h in rows[0]]
        col_mapping = _find_column_mapping(headers)

        if not col_mapping:
            raise ValueError(
                f"无法识别 Excel 表头中的任何有效列。"
                f"检测到的表头: {headers[:10]}... "
                f"请确保包含 '标题'、'严重度'、'状态'、'创建人'、'创建时间' 等列"
            )

        # 检查必填字段
        has_title = any(field == 'title' for field in col_mapping.values())
        if not has_title:
            raise ValueError("Excel 中缺少必要的 '标题' 列")

        # 逐行解析数据
        bugs = []
        parse_errors = []

        for row_idx, row in enumerate(rows[1:], start=2):  # 跳过表头
            if not row or all(cell is None for cell in row):
                continue  # 跳过空行

            raw_data = {}
            for col_idx, field_name in col_mapping.items():
                if col_idx < len(row) and row[col_idx] is not None:
                    raw_data[field_name] = row[col_idx]

            # 跳过完全空的数据行
            if not raw_data:
                continue

            try:
                bug = BugSourceAdapter.normalize_bug(raw_data)

                # 如果有 created 但未成功解析，尝试用 updated
                if not bug.created and raw_data.get('updated'):
                    bug['created'] = _parse_date_value(raw_data['updated'])

                bugs.append(bug)

            except Exception as e:
                parse_errors.append(f"第{row_idx}行解析失败: {e}")
                continue

        if parse_errors:
            logger.warning(f"Excel 解析警告 ({len(parse_errors)}条): {parse_errors[:5]}")

        if len(bugs) == 0:
            raise ValueError(f"未能从 Excel 中解析出有效的 Bug 数据。共 {len(rows)-1} 行数据。")

        logger.info(f"Excel 解析完成: 文件={file_path}, 总行数={len(rows)}, 有效Bug数={len(bugs)}, 列映射={col_mapping}")
        return bugs

    @staticmethod
    def from_json_data(data_list: List[Dict]) -> List[NormalizedBug]:
        """
        从 JSON 格式的 Bug 数据列表转换

        Args:
            data_list: 前端或 API 提交的 JSON Bug 列表

        Returns:
            list[NormalizedBug]: 标准化后的 Bug 列表
        """
        if not isinstance(data_list, list):
            raise ValueError(f"期望 list 类型，收到 {type(data_list).__name__}")

        bugs = []
        for i, raw in enumerate(data_list):
            if not isinstance(raw, dict):
                logger.warning(f"跳过非字典元素 [{i}]: {type(raw).__name__}")
                continue

            bug = BugSourceAdapter.normalize_bug(raw)
            bugs.append(bug)

        logger.info(f"JSON 数据转换完成: 输入{len(data_list)}条 → 有效{len(bugs)}条")
        return bugs

    @staticmethod
    def from_yunxiao(params: Dict) -> List[NormalizedBug]:
        """
        从云效 API 拉取 Bug 数据并标准化

        Args:
            params: {
                "token": str,          # 云效个人访问令牌 (必填)
                "organization_id": str,# 组织 ID (中心版必填)
                "space_id": str,       # 项目 ID (必填)
                "sprint_id": str,      # 迭代 ID (可选)
                "domain": str,         # API 域名 (可选，默认 https://devops.aliyun.com)
                "max_bugs": int,       # 最大拉取数量 (可选，默认 1000)
            }

        Returns:
            list[NormalizedBug]: 标准化后的 Bug 列表

        Raises:
            ValueError: 参数缺失
            YunxiaoAPIError: 云效 API 调用失败
        """
        from .yunxiao_client import YunxiaoClient, convert_yunxiao_bugs, YunxiaoAPIError

        token = params.get("token", "").strip()
        organization_id = params.get("organization_id", "").strip()
        space_id = params.get("space_id", "").strip()
        sprint_id = params.get("sprint_id", "").strip() or None
        domain = params.get("domain", "")
        max_bugs = int(params.get("max_bugs", 1000))

        if not token:
            raise ValueError("缺少云效访问令牌 (token)")
        if not space_id:
            raise ValueError("缺少项目 ID (space_id)")

        client_kwargs = {"token": token, "organization_id": organization_id}
        if domain:
            client_kwargs["domain"] = domain

        client = YunxiaoClient(**client_kwargs)

        # 拉取全部 Bug (自动分页)
        raw_workitems = client.fetch_all_bugs(
            space_id=space_id,
            sprint_id=sprint_id,
            max_bugs=max_bugs,
        )

        if not raw_workitems:
            logger.warning(f"[from_yunxiao] 云效未返回任何 Bug 数据: project={space_id}, sprint={sprint_id}")
            return []

        logger.info(f"[from_yunxiao] 云效返回 {len(raw_workitems)} 条原始工作项，开始转换为标准化格式")

        # 转换为标准化格式
        bug_dicts = convert_yunxiao_bugs(raw_workitems)

        # 打印第一条转换后的数据结构（用于诊断）
        if bug_dicts:
            first_bug_dict = bug_dicts[0]
            logger.info(f"[from_yunxiao] 第一条转换后数据: keys={list(first_bug_dict.keys())}, "
                        f"title={first_bug_dict.get('title', '')[:30]}..., "
                        f"created={first_bug_dict.get('created')}, updated={first_bug_dict.get('updated')}, "
                        f"creator={first_bug_dict.get('creator')}, "
                        f"custom_fields keys={list(first_bug_dict.get('custom_fields', {}).keys())}")

        # 再经过 normalize_bug 统一处理
        bugs = []
        for idx, d in enumerate(bug_dicts):
            bug = BugSourceAdapter.normalize_bug(d)
            # 将云效原始数据保留在额外字段中，供后续分析使用
            bug["_raw_yunxiao"] = d.get("_raw", {})

            # 如果 normalize_bug 没有 module，使用转换时提取的 module
            if not bug.get("module") and d.get("module"):
                bug["module"] = d["module"]

            # 每10条打印一次详细日志
            if idx < 3 or (idx + 1) % 10 == 0:
                logger.info(f"[from_yunxiao] Bug#{idx+1} 标准化后: "
                            f"title={bug['title'][:30]}..., created={bug['created']}, "
                            f"updated={bug['updated']}, module={bug.get('module')}, "
                            f"custom_fields={list(bug.get('custom_fields', {}).keys())}")

            bugs.append(bug)

        logger.info(f"[from_yunxiao] 云效数据转换完成: 原始{len(raw_workitems)}条 → "
                    f"convert后{len(bug_dicts)}条 → 标准化{len(bugs)}条")

        # 统计关键字段的填充情况
        created_count = sum(1 for b in bugs if b.get('created'))
        updated_count = sum(1 for b in bugs if b.get('updated'))
        custom_field_count = sum(1 for b in bugs if b.get('custom_fields') and len(b.get('custom_fields', {})) > 0)
        logger.info(f"[from_yunxiao] 字段填充统计: created={created_count}/{len(bugs)}, "
                    f"updated={updated_count}/{len(bugs)}, custom_fields有数据={custom_field_count}/{len(bugs)}")

        return bugs

    @staticmethod
    def from_tapd(params: Dict) -> List[NormalizedBug]:
        """
        [预留接口] 从 TAPD API 拉取 Bug 数据

        TAPD (Tencent Agile Product Development) REST API 对接。

        Args:
            params: 包含 workspace_id、查询条件等参数

        Raises:
            NotImplementedError: 当前未实现
        """
        # TODO: 对接 TAPD REST API
        # 参考文档: https://www.tapd.cn/help/show#1120003271001000108
        # 关键接口:
        #   - GET /bugs (获取Bug列表)
        #   - 需要 API User / API Password 认证
        raise NotImplementedError("TAPD API 对接功能开发中，敬请期待")


# ============================================================
# 便捷函数
# ============================================================

def load_bugs_from_source(source_type: str = 'excel', **kwargs) -> List[NormalizedBug]:
    """
    统一的数据加载入口

    Args:
        source_type: 数据源类型 ('excel', 'json', 'yunxiao', 'tapd')
        **kwargs: 各数据源所需的参数
            - excel: file_path (str)
            - json: data_list (list)
            - yunxiao/tapd: params (dict)

    Returns:
        list[NormalizedBug]: 标准化后的 Bug 列表

    Raises:
        ValueError: 参数错误或数据源不支持
        FileNotFoundError: Excel 文件不存在
    """
    adapters = {
        'excel': lambda: BugSourceAdapter.from_excel(kwargs.get('file_path', '')),
        'json': lambda: BugSourceAdapter.from_json_data(kwargs.get('data_list', [])),
        'yunxiao': lambda: BugSourceAdapter.from_yunxiao(kwargs.get('params', {})),
        'tapd': lambda: BugSourceAdapter.from_tapd(kwargs.get('params', {})),
    }

    adapter = adapters.get(source_type.lower())
    if not adapter:
        raise ValueError(f"不支持的数据源类型: {source_type}，可选: {list(adapters.keys())}")

    return adapter()
