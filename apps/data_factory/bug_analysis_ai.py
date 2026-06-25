# -*- coding: utf-8 -*-
"""
Bug 分析 AI 增强层

提供两种实现:
1. MockBugAnalysisAI: 基于规则的 Mock 实现（默认，用于开发和测试）
2. QwenBugAnalysisAI: 通义千问真实 AI 实现（复用项目 AIModelService）

通过配置切换: 在 settings 或环境变量中设置 BUG_ANALYSIS_AI_PROVIDER
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class BugAnalysisAIProvider(ABC):
    """
    Bug 分析 AI 增强提供者基类

    定义 6 个 AI 增强接口:
    1. classify_defect - AI 辅助缺陷分类
    2. infer_severity - 上下文感知严重度推断
    3. classify_module - 模块归类 fallback
    4. generate_root_cause - 根因假设生成
    5. generate_test_focus - 个性化测试建议
    6. generate_summary - 总结报告生成
    """

    @abstractmethod
    async def classify_defect(self, title: str, desc: str = '') -> str:
        """AI 辅助缺陷分类"""
        pass

    @abstractmethod
    async def infer_severity(self, title: str, desc: str = '', original_sev: str = '') -> str:
        """AI 上下文感知严重度推断"""
        pass

    @abstractmethod
    async def classify_module_fallback(self, tags: List[str], title: str) -> str:
        """AI 模块归类 fallback (规则未命中时)"""
        pass

    @abstractmethod
    async def generate_root_cause(self, module_name: str, bug_list: List[Dict]) -> str:
        """AI 根因假设生成"""
        pass

    @abstractmethod
    async def generate_test_focus(self, module_name: str, mod_stats: Dict) -> str:
        """AI 个性化测试建议"""
        pass

    @abstractmethod
    async def generate_summary(self, analysis_result: Dict) -> str:
        """AI 总结报告生成"""
        pass

    @abstractmethod
    async def analyze_risks(self, bugs: List[Dict], analysis_result: Dict) -> Dict:
        """
        AI 动态风险类型分析

        根据 Bug 数据智能识别风险类型，替代固定的 P0/P1/P2 风险分类

        Returns:
            Dict: {
                'P0': [{'type': '风险类型名', 'count': 数量, 'rule': '识别规则', 'desc': '说明', 'tagType': '标签样式'}, ...],
                'P1': [...],
                'P2': [...]
            }
        """
        pass

    @abstractmethod
    async def extract_keywords(self, bugs: List[Dict]) -> List[List]:
        """
        AI 语义提取关键词

        基于 Bug 标题语义分析，智能提炼关键词（非预定义匹配）

        Args:
            bugs: Bug 列表

        Returns:
            List[List]: [[keyword, count], ...] 按重要性排序的关键词列表
        """
        pass


# ============================================================
# Mock 实现 - 基于规则的结果，用于开发和测试
# ============================================================

class MockBugAnalysisAI(BugAnalysisAIProvider):
    """
    Mock AI 实现器

    返回基于规则引擎的合理结果，不调用任何外部 API。
    用于:
    - 开发和测试环境
    - 验证整体流程跑通
    - 无网络/无 API Key 时降级使用
    """

    async def classify_defect(self, title: str, desc: str = '') -> str:
        """
        Mock 缺陷分类: 基于简单关键词回退到规则引擎
        实际项目中会导入 bug_analysis.classify_defect 作为后备
        """
        from .bug_analysis import classify_defect
        return classify_defect(title, desc)

    async def infer_severity(self, title: str, desc: str = '', original_sev: str = '') -> str:
        """
        Mock 严重度推断: 使用规则引擎结果
        """
        from .bug_analysis import infer_severity
        return infer_severity(title, desc, original_sev)

    async def classify_module_fallback(self, tags: List[str], title: str) -> str:
        """
        Mock 模块归类 fallback: 返回"其他模块"
        """
        logger.info(f"[Mock AI] 模块归类fallback: tags={tags}, title={title[:30]}")
        return '其他'

    async def generate_root_cause(self, module_name: str, bug_list: List[Dict]) -> str:
        """
        Mock 根因假设: 基于缺陷类型分布生成模板化结论
        """
        from collections import Counter
        type_dist = Counter(b.get('defect_type', '未知') for b in bug_list)
        top_types = type_dist.most_common(3)
        type_str = '、'.join(f"{t}({c}条)" for t, c in top_types)

        # 简单的模板化根因 (后续被真实 AI 替代)
        if type_dist.get('UI显示', 0) > len(bug_list) * 0.3:
            cause = f"该模块 UI 显示类问题占比最高({type_dist['UI显示']}/{len(bug_list)})，推测前端组件渲染或样式兼容性存在系统性问题，建议重点回归 Safari 和移动端浏览器。"
        elif type_dist.get('功能逻辑', 0) > len(bug_list) * 0.3:
            cause = f"该模块功能逻辑类问题占比最高({type_dist['功能逻辑']}/{len(bug_list)})，推测后端业务逻辑或接口数据处理存在问题，建议加强边界条件和异常流程测试。"
        elif type_dist.get('数据内容', 0) > len(bug_list) * 0.25:
            cause = f"该模块数据内容类问题较突出({type_dist.get('数据内容', 0)}/{len(bug_list)})，可能涉及数据迁移、脏数据或字段映射问题。"
        else:
            cause = f"主要问题类型为 {type_str}，建议针对性加强相关场景回归测试覆盖。"

        logger.info(f"[Mock AI] 根因假设[{module_name}]: {cause[:80]}...")
        return cause

    async def generate_test_focus(self, module_name: str, mod_stats: Dict) -> str:
        """
        Mock 测试建议: 基于统计数据生成模板化建议
        """
        total = mod_stats.get('total', 0)
        online = mod_stats.get('online', 0)
        reopened = mod_stats.get('reopened', 0)
        dtype_dist = mod_stats.get('dtype_dist', {})
        top_types = mod_stats.get('top_types', [])

        suggestions = []

        # 线上故障关注
        if online > 0:
            pct = round(online / total * 100, 1) if total > 0 else 0
            suggestions.append(f"**线上故障优先验证**: 该模块有 {online} 条线上故障({pct}%)，迭代后必须逐条回归验证已修复的场景不再复现。")

        # 二次打开关注
        if reopened > 0:
            suggestions.append(f"**防止回归不彻底**: 存在 {reopened} 条二次打开的 Bug，说明修复方案可能不够彻底或验证范围不足，需扩大回归范围。")

        # 基于缺陷类型的专项建议
        type_suggestions = {
            'UI显示': "重点检查页面布局、文字截断、样式错乱、Safari 兼容性问题",
            '功能逻辑': "重点验证核心业务流程、边界条件、异常输入处理、数据提交完整性",
            '数据内容': "重点关注特殊字符、空数据、大数据量、字段截断、格式转换等场景",
            '交互操作': "重点验证按钮响应、表单联动、筛选排序、拖拽操作、键盘交互",
            '跨端兼容': "必须在 PC + H5 + APP(如有) 三端分别验证，特别关注 Safari/华为/小米浏览器",
            '性能稳定': "关注加载性能、长时间操作稳定性、内存泄漏、并发操作场景",
        }

        for dtype_name, _ in top_types[:3]:
            suggestion = type_suggestions.get(dtype_name)
            if suggestion:
                suggestions.append(f"**{dtype_name}专项**: {suggestion}")

        result = "\n".join(f"{i+1}. {s}" for i, s in enumerate(suggestions)) if suggestions else "暂无特殊建议，按常规回归流程执行即可。"

        logger.info(f"[Mock AI] 测试建议[{module_name}]: {len(suggestions)}条建议")
        return result

    async def generate_summary(self, analysis_result: Dict) -> str:
        """
        Mock 总结报告: 基于统计数据的模板化总结（使用数字列表格式）
        """
        meta = analysis_result.get('metaData', {})
        total = meta.get('total_bugs', 0)
        sev_inf = analysis_result.get('sevInfData', {})
        modules = analysis_result.get('modulesData', {})
        risk = analysis_result.get('riskData', {})

        p0_count = sev_inf.get('推断P0', 0)
        p1_count = sev_inf.get('推断P1', 0)
        p2_count = sev_inf.get('推断P2', 0)

        top_modules = sorted(modules.items(), key=lambda x: x[1], reverse=True)[:3]
        top_modules_str = '、'.join(f"{m}({c}条)" for m, c in top_modules)

        p0_detail = risk.get('P0', {}).get('detail', {})
        p0_items = [f"{k}({v}条)" for k, v in p0_detail.items() if v > 0]

        online_total = sum(
            v.get('detail', {}).get('线上故障P1', 0) + v.get('detail', {}).get('线上故障P2', 0)
            for v in risk.values()
        )

        # 收集风险点（使用数字列表格式）
        risk_items = []
        risk_idx = 1
        if p0_items:
            risk_items.append(f"{risk_idx}. **P0 高危问题**: {'，'.join(p0_items)}，需要最高优先级处理")
            risk_idx += 1
        if top_modules:
            risk_items.append(f"{risk_idx}. **高发模块 Top3**: {top_modules_str}，应作为迭代回归的重点区域")
            risk_idx += 1
        if online_total > 0:
            risk_items.append(f"{risk_idx}. **线上故障共 {online_total} 条**: 需逐条确认修复状态并纳入回归范围")
            risk_idx += 1

        # 如果风险点不足，补充通用风险
        if len(risk_items) < 2:
            risk_items.append(f"{risk_idx}. **需关注 P1/P2 问题**: 共 {p1_count + p2_count} 条中低危问题需按计划修复")

        lines = [
            f"本次分析共收录 **{total}** 条 Bug，其中推断 P0 有 **{p0_count}** 条、P1 有 **{p1_count}** 条、P2 有 **{p2_count}** 条。",
            f"",
        ]

        # 关键风险点（数字列表）
        lines.extend(risk_items)
        lines.append("")

        # 行动建议（数字列表）
        lines.extend([
            f"1. **P0/P1 问题优先修复**: 共 {p0_count + p1_count} 条高危问题需在本次迭代内解决",
            f"2. **Top 模块深度回归**: 对 {top_modules_str} 进行全面回归测试",
            f"3. **线上故障专项验证**: 确保所有线上故障已修复并验证通过",
        ])

        result = "\n".join(lines)
        logger.info(f"[Mock AI] 总结报告: {total}条Bug, P0={p0_count}, P1={p1_count}")
        return result

    async def analyze_risks(self, bugs: List[Dict], analysis_result: Dict) -> Dict:
        """
        Mock 风险类型分析: 基于规则识别常见的风险模式
        """
        from collections import Counter

        total = len(bugs)
        if total == 0:
            return {'P0': [], 'P1': [], 'P2': []}

        # 风险计数器
        risk_patterns = {
            'P0': [],
            'P1': [],
            'P2': []
        }

        # P0 风险 - 服务中断/应用崩溃
        p0_patterns = [
            {'type': '白屏/黑屏', 'keywords': ['白屏', '黑屏', '页面空白', '无法加载'], 'desc': '页面完全不可用'},
            {'type': '504/超时', 'keywords': ['504', '超时', 'timeout', '连接超时'], 'desc': '服务端超时中断'},
            {'type': '闪退/崩溃', 'keywords': ['闪退', '崩溃', 'crash', '退出', '卡死'], 'desc': '应用崩溃退出'},
            {'type': '核心功能不可用', 'keywords': ['无法登录', '无法提交', '无法保存', '核心功能'], 'desc': '核心业务流程阻断'},
        ]

        # P1 风险 - 功能阻塞/修复质量存疑
        p1_patterns = [
            {'type': '线上故障P1', 'keywords': ['线上故障', '生产环境'], 'condition': lambda b: 'P1' in str(b.get('title', '')) + str(b.get('description', '')), 'desc': '线上已发生+功能阻塞'},
            {'type': '严重UI异常', 'keywords': ['样式错乱', '布局混乱', '显示异常'], 'desc': '影响用户体验的严重UI问题'},
            {'type': '数据异常', 'keywords': ['数据丢失', '数据错误', '数据不一致'], 'desc': '数据处理异常'},
            {'type': '二次打开', 'keywords': ['再次打开', 'reopened'], 'desc': '修复后又复现'},
        ]

        # P2 风险 - 影响较轻/边界场景
        p2_patterns = [
            {'type': '跨端兼容', 'keywords': ['iOS', 'Android', 'Safari', 'Chrome', 'Firefox', 'IE', '移动端', 'PC端'], 'desc': '涉及多端需逐一验证'},
            {'type': '边界场景', 'keywords': ['边界', '极限', '空值', 'null', 'undefined'], 'desc': '边界条件处理异常'},
            {'type': '性能问题', 'keywords': ['慢', '卡顿', '加载慢', '性能'], 'desc': '性能体验问题'},
            {'type': '交互优化', 'keywords': ['提示不明确', '操作繁琐', '体验'], 'desc': '交互体验优化项'},
        ]

        # 统计各风险类型
        for pattern in p0_patterns:
            count = sum(1 for b in bugs if any(kw in str(b.get('title', '')) + str(b.get('description', '')) for kw in pattern['keywords']))
            if count > 0:
                risk_patterns['P0'].append({
                    'type': pattern['type'],
                    'count': count,
                    'rule': f"文本含{pattern['keywords'][:2]}",
                    'desc': pattern['desc'],
                    'tagType': 'danger'
                })

        for pattern in p1_patterns:
            count = sum(1 for b in bugs if any(kw in str(b.get('title', '')) + str(b.get('description', '')) for kw in pattern['keywords']))
            if count > 0:
                risk_patterns['P1'].append({
                    'type': pattern['type'],
                    'count': count,
                    'rule': f"文本含{pattern['keywords'][:2]}",
                    'desc': pattern['desc'],
                    'tagType': 'warning'
                })

        for pattern in p2_patterns:
            count = sum(1 for b in bugs if any(kw in str(b.get('title', '')) + str(b.get('description', '')) for kw in pattern['keywords']))
            if count > 0:
                risk_patterns['P2'].append({
                    'type': pattern['type'],
                    'count': count,
                    'rule': f"文本含{pattern['keywords'][:2]}",
                    'desc': pattern['desc'],
                    'tagType': 'info'
                })

        # 如果某级别没有风险，添加一个默认的
        if not risk_patterns['P0']:
            risk_patterns['P0'].append({'type': '暂无P0风险', 'count': 0, 'rule': '-', 'desc': '未发现高危风险', 'tagType': 'danger'})
        if not risk_patterns['P1']:
            risk_patterns['P1'].append({'type': '暂无P1风险', 'count': 0, 'rule': '-', 'desc': '未发现中危风险', 'tagType': 'warning'})
        if not risk_patterns['P2']:
            risk_patterns['P2'].append({'type': '暂无P2风险', 'count': 0, 'rule': '-', 'desc': '未发现低危风险', 'tagType': 'info'})

        logger.info(f"[Mock AI] 风险分析完成: P0={len(risk_patterns['P0'])}类, P1={len(risk_patterns['P1'])}类, P2={len(risk_patterns['P2'])}类")
        return risk_patterns

    async def extract_keywords(self, bugs: List[Dict]) -> List[List]:
        """
        Mock 关键词提取: 基于简单规则从标题中提取高频词汇
        用于开发和测试环境
        """
        from collections import Counter
        import re

        # 提取所有标题中的词汇（简单分词）
        word_counter = Counter()

        for b in bugs:
            title = b.get('title', '')
            # 去除方括号标签
            clean_title = re.sub(r'【.*?】|\[.*?\]', '', title)
            # 简单分词：提取2-4个字的词组
            words = re.findall(r'[\u4e00-\u9fa5]{2,4}', clean_title)
            for w in words:
                # 过滤常见停用词
                if w not in ['无法', '不能', '没有', '一个', '进行', '需要', '问题', '错误']:
                    word_counter[w] += 1

        # 返回 Top 20
        return [[word, count] for word, count in word_counter.most_common(20)]


# ============================================================
# 通义千问真实 AI 实现
# ============================================================

class QwenBugAnalysisAI(BugAnalysisAIProvider):
    """
    通义千问 AI 实现器

    调用阿里百炼通义千问 API (OpenAI 兼容格式)
    复用项目现有的 AIModelService 基础设施

    使用前确保:
    1. 在系统中已配置 AIModelConfig (类型选择 qwen/openai_compatible)
    2. base_url 指向阿里百炼 API 地址
    3. api_key 已正确填入
    """

    # 默认模型配置 ID (可通过参数覆盖或在数据库中配置)
    DEFAULT_CONFIG_ID = None  # 从数据库读取或通过参数传入

    def __init__(self, config_id: int = None):
        """
        初始化通义千问 AI 提供者

        Args:
            config_id: AIModelConfig 数据库记录 ID。如果为 None，将自动查找可用的千问配置。
        """
        self.config_id = config_id or self.DEFAULT_CONFIG_ID
        self._config = None

    async def _get_config(self):
        """懒加载 AI 配置 (异步)"""
        if self._config is None:
            try:
                from apps.requirement_analysis.models import AIModelConfig as AMC

                # 使用 sync_to_async 包装 ORM 查询
                if self.config_id:
                    get_config = sync_to_async(AMC.objects.get)
                    self._config = await get_config(id=self.config_id)
                else:
                    # 自动查找第一个可用的大语言模型配置
                    filter_configs = sync_to_async(lambda: list(AMC.objects.filter(
                        model_type__in=['qwen', 'openai_compatible', 'deepseek']
                    ).order_by('-updated_at')[:1]))
                    configs = await filter_configs()
                    self._config = configs[0] if configs else None

                if not self._config:
                    raise ValueError("未找到可用的 AI 模型配置，请在系统中添加通义千问或其他大语言模型配置")
            except Exception as e:
                logger.error(f"获取 AI 模型配置失败: {e}")
                raise

        return self._config

    async def _call_llm(self, messages: List[Dict], temperature: float = 0.1) -> str:
        """
        调用 LLM API 的统一入口

        Args:
            messages: OpenAI 格式的消息列表 [{"role": "system/user", "content": "..."}]
            temperature: 温度参数，低值更确定性

        Returns:
            str: LLM 返回的文本内容
        """
        from ..requirement_analysis.ai_models import AIModelService
        config = await self._get_config()

        try:
            response = await AIModelService.call_openai_compatible_api(config, messages)
            content = response['choices'][0]['message']['content']
            return content.strip()
        except Exception as e:
            logger.error(f"调用 AI API 失败: {e}")
            raise

    async def classify_defect(self, title: str, desc: str = '') -> str:
        """AI 辅助缺陷分类"""
        prompt = f"""你是一个资深软件测试分析师。请将以下 Bug 归类到一种缺陷类型。

可选类型: UI显示 / 功能逻辑 / 数据内容 / 交互操作 / 性能稳定 / 跨端兼容 / 其他

Bug标题: {title}
{'Bug描述: ' + desc[:200] if desc else ''}

要求:
1. 只返回类型名称，不要解释
2. 如果难以判断，返回"其他"
"""

        messages = [
            {"role": "system", "content": "你是资深软件测试分析师，擅长对Bug进行准确分类。只输出分类结果，不要多余解释。"},
            {"role": "user", "content": prompt},
        ]

        result = await self._call_llm(messages, temperature=0.1)
        # 清理结果: 确保是有效类型
        valid_types = ['UI显示', '功能逻辑', '数据内容', '交互操作', '性能稳定', '跨端兼容', '其他']
        for vt in valid_types:
            if vt in result:
                return vt
        return '其他'

    async def infer_severity(self, title: str, desc: str = '', original_sev: str = '') -> str:
        """AI 上下文感知严重度推断"""
        prompt = f"""判断此 Bug 的真实严重程度。

判断标准:
- P0 (致命): 白屏/崩溃/死循环/数据丢失/阻塞核心全量用户流程
- P1 (严重): 无法完成关键操作/影响大量用户/无 workaround
- P2 (一般): 非核心功能问题/有 workaround/影响少数用户

考虑因素:
- 影响用户范围（全部/部分/单个）
- 是否阻塞核心流程
- 是否有 workaround（替代方案）
- 是否偶现 vs 必现
- 是否线上已发生

Bug标题: {title}
{'描述: ' + desc[:150] if desc else ''}
原始标注严重度: {original_sev or '无'}

严格只返回 P0 / P1 / P2 其中之一，不要解释。
"""

        messages = [
            {"role": "system", "content": "你是资深测试专家，擅长判断Bug的真实严重程度。严格按标准输出P0/P1/P2。"},
            {"role": "user", "content": prompt},
        ]

        result = await self._call_llm(messages, temperature=0.1)
        result = result.upper().strip()
        if result in ('P0', 'P1', 'P2'):
            return result
        return 'P2'  # 默认值

    async def classify_module_fallback(self, tags: List[str], title: str) -> str:
        """AI 模块归类 fallback"""
        from .bug_analysis import MODULE_MAP
        available_modules = ', '.join(MODULE_MAP.keys())

        prompt = f"""将以下 Bug 归类到最接近的功能模块。

可选模块: {available_modules}

如果都不匹配，返回"新模块-<你认为合适的名称>"。

Bug标题: {title}
标签: {', '.join(tags) if tags else '无'}

只返回模块名称或"新模块-xxx"，不要解释。
"""

        messages = [
            {"role": "system", "content": "你是项目架构师，熟悉各功能模块的划分。只输出最接近的模块名称。"},
            {"role": "user", "content": prompt},
        ]

        result = await self._call_llm(messages, temperature=0)

        # 检查是否为新模块建议
        if result.startswith('新模块-'):
            logger.info(f"[Qwen AI] 建议新模块: {result}, title: {title[:30]}")

        # 尝试匹配已知模块
        for mod in MODULE_MAP.keys():
            if mod in result or result in mod:
                return mod

        return result

    async def generate_root_cause(self, module_name: str, bug_list: List[Dict]) -> str:
        """AI 根因假设生成"""
        # 按 inferred_sev 排序，取 Top 10
        sorted_bugs = sorted(bug_list, key=lambda b: b.get('inferred_sev', 'P2'))[:10]
        titles = '\n'.join(
            f"- [{b.get('inferred_sev', '?')}] {b.get('title', '')}"
            for b in sorted_bugs
        )

        prompt = f"""以下是【{module_name}】模块收集到的 Top Bug：

{titles}

请分析可能的根本原因（选1-2个最可能）:
1. 前端问题（组件库/样式/兼容性）
2. 后端接口问题（逻辑/数据/性能）
3. 数据问题（迁移/配置/脏数据）
4. 测试覆盖不足
5. 其他原因

用简洁语言输出根因假设，不超过100字。直接给出结论，不要列举所有可能性。
"""

        messages = [
            {"role": "system", "content": "你是资深技术专家，善于从Bug模式中推断根本原因。给出简洁有力的结论。"},
            {"role": "user", "content": prompt},
        ]

        result = await self._call_llm(messages, temperature=0.3)
        logger.info(f"[Qwen AI] 根因假设[{module_name}]: {result[:60]}...")
        return result

    async def generate_test_focus(self, module_name: str, mod_stats: Dict) -> str:
        """AI 个性化测试建议"""
        total = mod_stats.get('total', 0)
        online = mod_stats.get('online', 0)
        reopened = mod_stats.get('reopened', 0)
        dtype_dist = mod_stats.get('dtype_dist', {})
        top_examples_raw = mod_stats.get('examples', []) or []  # 从模块统计数据获取示例

        prompt = f"""你是资深测试专家。针对【{module_name}】模块生成迭代测试重点：

统计数据：
- 总Bug数: {total}
- 线上故障数: {online}
- 二次打开数: {reopened}
- 缺陷类型分布: {json.dumps(dtype_dist, ensure_ascii=False)}

要求：
1. 按优先级排列 3-5 个测试关注点
2. 每个点注明 回归范围 + 验证方法
3. 如果某类问题特别突出，给出具体测试用例方向
4. 语言简洁专业，每条不超过50字
5. 直接输出编号列表，不要开场白
"""

        messages = [
            {"role": "system", "content": "你是资深测试专家，擅长根据历史Bug数据制定精准的回归测试策略。"},
            {"role": "user", "content": prompt},
        ]

        result = await self._call_llm(messages, temperature=0.2)
        logger.info(f"[Qwen AI] 测试建议[{module_name}]: 已生成")
        return result

    async def generate_summary(self, analysis_result: Dict) -> str:
        """AI 总结报告生成"""
        meta = analysis_result.get('metaData', {})
        sev_inf = analysis_result.get('sevInfData', {})
        modules = analysis_result.get('modulesData', {})
        risk = analysis_result.get('riskData', {})

        top_modules = sorted(modules.items(), key=lambda x: x[1], reverse=True)[:5]

        prompt = f"""基于以下 Bug 分析数据，生成一份给技术管理者的简报：

## 基础数据
- 总Bug数: {meta.get('total_bugs', 0)}
- P0/P1/P2 分布: {json.dumps(sev_inf, ensure_ascii=False)}
- Top5模块: {json.dumps(top_modules, ensure_ascii=False)}

## 风险概况
- P0详情: {json.dumps(risk.get('P0', {}).get('detail', {}), ensure_ascii=False)}
- P1详情: {json.dumps(risk.get('P1', {}).get('detail', {}), ensure_ascii=False)}

【格式要求 - 必须严格遵守】
1. 第一行：整体态势（一句话概括严重程度）
2. 空一行
3. 关键风险点：必须使用 "1. " "2. " "3. " 这样的数字列表格式（2-4条），示例：
   1. **风险标题**: 风险描述
   2. **风险标题**: 风险描述
4. 空一行
5. 行动建议：必须使用 "1. " "2. " "3. " 这样的数字列表格式（2-3条），示例：
   1. **行动标题**: 行动描述
   2. **行动标题**: 行动描述
6. 禁止使用任何 Markdown 标题符号（如 ### 或 ##）
7. 禁止使用 - 或 * 作为列表符号，只能用数字列表格式

【输出示例】
本次分析共收录 100 条 Bug，其中推断 P0 有 5 条、P1 有 20 条、P2 有 75 条。

1. **P0 高危问题**: 登录功能不可用等 5 条，需要最高优先级处理
2. **高发模块 Top3**: 用户中心(25条)、订单模块(18条)、支付模块(12条)，应作为回归重点区域
3. **线上故障**: 共 3 条需逐条确认修复状态

1. **P0/P1 问题优先修复**: 共 25 条高危问题需在本次迭代内解决
2. **Top 模块深度回归**: 对用户中心、订单模块、支付模块进行全面回归测试
3. **线上故障专项验证**: 3 条线上故障需逐一验证不再复现
"""

        messages = [
            {"role": "system", "content": "你是测试团队负责人，擅长向技术管理者汇报Bug分析结果。语言简洁有力，突出风险和行动项。严格遵守输出格式要求。"},
            {"role": "user", "content": prompt},
        ]

        result = await self._call_llm(messages, temperature=0.3)
        logger.info("[Qwen AI] 总结报告: 已生成")
        return result

    async def analyze_risks(self, bugs: List[Dict], analysis_result: Dict) -> Dict:
        """
        AI 动态风险类型分析 - 真实 AI 实现

        让 AI 根据 Bug 数据智能识别风险类型，而非固定规则
        """
        total = len(bugs)
        if total == 0:
            return {'P0': [], 'P1': [], 'P2': []}

        # 准备样本数据（取前50条避免prompt过长）
        sample_bugs = bugs[:50]
        bug_samples = []
        for b in sample_bugs:
            bug_samples.append({
                'title': b.get('title', ''),
                'module': b.get('module', ''),
                'defect_type': b.get('defect_type', ''),
                'severity': b.get('severity', '')
            })

        prompt = f"""你是资深质量工程师。请基于以下 {total} 条 Bug 数据（展示前{len(bug_samples)}条样本），
用纯中文分析回归风险，输出可直接阅读的报告段落。

## Bug 样本数据
```
{json.dumps(bug_samples, ensure_ascii=False, indent=2)}
```

## 分析要求
请用流畅的中文段落，分别描述三个风险级别：

1. **P0 高风险**（服务中断/应用崩溃）：列出具体的风险场景，每个场景说明影响和回归建议
2. **P1 中风险**（功能阻塞/修复质量存疑）：列出需要重点回归的问题类型
3. **P2 低风险**（影响较轻/边界场景）：列出低优先级但需要关注的风险

## 输出格式
请按以下格式输出（纯文本，不要JSON）：

【P0 高风险】
- 白屏问题：共约15条，多涉及首页加载，需优先验证各入口跳转流程
- 504超时：共约8条，集中在接口调用场景，需重点回归高频接口
（继续列举其他高风险...）

【P1 中风险】
- 二次回归Bug：共约12条，历史修复后重现的问题，需对照历史验证
- 线上故障：共约5条，线上已发生的问题必须回归
（继续列举其他中风险...）

【P2 低风险】
- 边界场景：如异常输入、极端值处理等，按需回归
- 偶现问题：复现难度高，可酌情回归
（继续列举其他低风险...）

要求：
- 每个风险类型要具体，避免泛泛而谈
- 说明预估数量和回归建议
- 只输出纯文本报告，不要任何JSON或其他格式"""

        messages = [
            {"role": "system", "content": "你是资深质量工程师，擅长从Bug数据中提炼风险模式。用流畅的中文输出分析报告。"},
            {"role": "user", "content": prompt},
        ]

        try:
            result = await self._call_llm(messages, temperature=0.3)
            logger.info(f"[Qwen AI] 风险分析完成(纯文本): 长度={len(result)}")
            
            # 解析文本段落，转换为前端可用格式
            risks = {'P0': [], 'P1': [], 'P2': []}
            
            # 按段落标记提取内容
            import re
            p0_match = re.search(r'【P0 高风险】\s*(.+?)(?=【P1|$)', result, re.DOTALL)
            p1_match = re.search(r'【P1 中风险】\s*(.+?)(?=【P2|$)', result, re.DOTALL)
            p2_match = re.search(r'【P2 低风险】\s*(.+?)$', result, re.DOTALL)
            
            if p0_match:
                p0_text = p0_match.group(1).strip()
                # 按行拆分，每行作为一条风险项
                for line in p0_text.split('\n'):
                    line = line.strip()
                    if line and line.startswith('-'):
                        risks['P0'].append({'description': line[1:].strip(), 'type': '高风险'})
            if p1_match:
                p1_text = p1_match.group(1).strip()
                for line in p1_text.split('\n'):
                    line = line.strip()
                    if line and line.startswith('-'):
                        risks['P1'].append({'description': line[1:].strip(), 'type': '中风险'})
            if p2_match:
                p2_text = p2_match.group(1).strip()
                for line in p2_text.split('\n'):
                    line = line.strip()
                    if line and line.startswith('-'):
                        risks['P2'].append({'description': line[1:].strip(), 'type': '低风险'})
            
            # 如果解析失败，将整段文本作为一条
            if not risks['P0'] and p0_match:
                risks['P0'].append({'description': p0_text, 'type': '高风险'})
            if not risks['P1'] and p1_match:
                risks['P1'].append({'description': p1_text, 'type': '中风险'})
            if not risks['P2'] and p2_match:
                risks['P2'].append({'description': p2_text, 'type': '低风险'})

            logger.info(f"[Qwen AI] 风险分析完成: P0={len(risks['P0'])}类, P1={len(risks['P1'])}类, P2={len(risks['P2'])}类")
            return risks

        except Exception as e:
            logger.error(f"[Qwen AI] 风险分析失败: {e}")
            # 回退到 Mock 实现
            logger.info("[Qwen AI] 回退到 Mock 风险分析")
            mock_ai = MockBugAnalysisAI()
            return await mock_ai.analyze_risks(bugs, analysis_result)

    async def extract_keywords(self, bugs: List[Dict]) -> List[List]:
        """
        AI 语义提取关键词 - 真实 AI 实现

        基于 Bug 标题语义分析，智能提炼关键词
        """
        total = len(bugs)
        if total == 0:
            return []

        # 准备样本数据（取前50条避免prompt过长）
        sample_bugs = bugs[:50]
        bug_titles = [b.get('title', '') for b in sample_bugs]

        prompt = f"""你是资深产品经理。请基于以下 {total} 条 Bug 标题（展示前{len(bug_titles)}条），
语义分析并提炼出 10-15 个最核心的关键词/主题。

## Bug 标题数据
```
{chr(10).join(f"- {t}" for t in bug_titles)}
```

## 分析要求
1. **基于语义理解**：不要只是提取原文词汇，要理解标题含义后提炼主题
2. **合并同义词**：如"样式"和"CSS"合并为"UI样式"
3. **概括抽象**：将具体问题上升为领域概念，如"无法登录"→"登录功能"
4. **按重要性排序**：Bug 数量越多的主题越靠前

## 输出格式
必须是合法的 JSON 数组：
[
  ["关键词1", 预估出现次数],
  ["关键词2", 预估出现次数],
  ...
]

要求：
- 提供 10-15 个关键词
- 关键词要简洁，2-6个字为宜
- count 是预估数量，根据样本推断
- 只输出 JSON，不要任何其他文字"""

        messages = [
            {"role": "system", "content": "你是资深产品经理，擅长从Bug标题中提炼核心问题主题。只输出JSON格式结果。"},
            {"role": "user", "content": prompt},
        ]

        try:
            result = await self._call_llm(messages, temperature=0.3)

            # 解析 JSON
            import re
            json_match = re.search(r'\[.*\]', result, re.DOTALL)
            if json_match:
                keywords = json.loads(json_match.group())
                # 确保格式正确
                valid_keywords = []
                for item in keywords:
                    if isinstance(item, list) and len(item) == 2:
                        valid_keywords.append([str(item[0]), int(item[1])])
                    elif isinstance(item, dict) and 'keyword' in item and 'count' in item:
                        valid_keywords.append([str(item['keyword']), int(item['count'])])
                logger.info(f"[Qwen AI] 关键词提取完成: {len(valid_keywords)}个关键词")
                return valid_keywords[:20]  # 最多返回20个
            else:
                raise ValueError("未找到JSON格式的关键词数据")

        except Exception as e:
            logger.error(f"[Qwen AI] 关键词提取失败: {e}")
            # 回退到 Mock 实现
            logger.info("[Qwen AI] 回退到 Mock 关键词提取")
            mock_ai = MockBugAnalysisAI()
            return await mock_ai.extract_keywords(bugs)

    async def analyze_module_focus_intelligent(self, module_name: str, bugs: List[Dict]) -> Dict:
        """
        智能模块测试重点分析 - 三层架构
        
        第一层: 快速统计分析 (规则驱动)
        第二层: 深度语义分析 (AI大模型)
        第三层: 跨模块关联分析 (AI关联)
        
        Returns:
            Dict: 结构化分析结果
        """
        if not bugs:
            return self._empty_module_analysis(module_name)
        
        # ===== 第一层: 快速统计分析 =====
        layer1_result = self._layer1_statistical_analysis(module_name, bugs)
        
        # ===== 第二层: 深度语义分析 (采样优化) =====
        # 选取有代表性的Bug样本（线上故障+严重问题优先）
        sample_bugs = self._select_representative_bugs(bugs, max_samples=25)
        layer2_result = await self._layer2_semantic_analysis(module_name, sample_bugs, layer1_result)
        
        # ===== 第三层: 关联分析 (如果数据足够) =====
        if len(bugs) >= 10:
            layer3_result = await self._layer3_correlation_analysis(module_name, bugs, layer1_result, layer2_result)
        else:
            layer3_result = {"cross_module_patterns": [], "similar_issues": []}
        
        # 合并三层结果
        return {
            "module_name": module_name,
            "total_count": len(bugs),
            "layer1_stats": layer1_result,
            "layer2_insights": layer2_result,
            "layer3_correlations": layer3_result,
            "focus_points": self._merge_focus_points(layer1_result, layer2_result, layer3_result),
            "risk_level": self._calculate_risk_level(layer1_result, layer2_result),
            "test_strategy": self._generate_test_strategy(layer1_result, layer2_result),
            "ai_generated_at": datetime.now().isoformat()
        }
    
    def _layer1_statistical_analysis(self, module_name: str, bugs: List[Dict]) -> Dict:
        """第一层: 快速统计分析 - 规则驱动"""
        from collections import Counter
        
        # 基础统计
        total = len(bugs)
        online_count = sum(1 for b in bugs if '线上' in str(b.get('工作项类型', '')))
        reopened_count = sum(1 for b in bugs if '重新打开' in str(b.get('状态', '')) or 'Reopen' in str(b.get('状态', '')))
        
        # 严重程度分布
        severity_counter = Counter()
        for b in bugs:
            sev = str(b.get('严重程度', ''))
            if '致命' in sev or 'P0' in sev:
                severity_counter['致命'] += 1
            elif '严重' in sev or 'P1' in sev:
                severity_counter['严重'] += 1
            else:
                severity_counter['一般'] += 1
        
        # 缺陷类型分布
        dtype_counter = Counter(str(b.get('工作项类型', '其他')) for b in bugs)
        
        # 高频问题模式识别 (基于标题关键词)
        title_keywords = []
        for b in bugs:
            title = str(b.get('标题', ''))
            # 提取方括号中的功能点
            if '[' in title and ']' in title:
                feature = title[title.find('[')+1:title.find(']')]
                title_keywords.append(feature)
        
        feature_counter = Counter(title_keywords)
        
        return {
            "total": total,
            "online_count": online_count,
            "reopened_count": reopened_count,
            "severity_dist": dict(severity_counter),
            "defect_type_dist": dict(dtype_counter),
            "feature_dist": dict(feature_counter.most_common(5)),
            "status_dist": dict(Counter(str(b.get('状态', '未知')) for b in bugs)),
            "high_risk_indicators": self._identify_risk_indicators(bugs)
        }
    
    def _select_representative_bugs(self, bugs: List[Dict], max_samples: int = 25) -> List[Dict]:
        """智能采样: 优先选择有代表性的Bug"""
        # 优先级排序: 线上故障 > 致命 > 严重 > 有描述 > 其他
        def priority_score(bug):
            score = 0
            if '线上' in str(bug.get('工作项类型', '')):
                score += 1000
            if '致命' in str(bug.get('严重程度', '')) or 'P0' in str(bug.get('严重程度', '')):
                score += 100
            elif '严重' in str(bug.get('严重程度', '')) or 'P1' in str(bug.get('严重程度', '')):
                score += 50
            if bug.get('描述') and len(str(bug.get('描述', ''))) > 50:
                score += 20
            return score
        
        sorted_bugs = sorted(bugs, key=priority_score, reverse=True)
        return sorted_bugs[:max_samples]
    
    async def _layer2_semantic_analysis(self, module_name: str, bugs: List[Dict], stats: Dict) -> Dict:
        """第二层: 深度语义分析 - AI大模型"""
        
        # 构建Bug样本数据
        bug_samples = []
        for b in bugs:
            bug_samples.append({
                "title": str(b.get('标题', '')),
                "type": str(b.get('工作项类型', '')),
                "severity": str(b.get('严重程度', '')),
                "status": str(b.get('状态', '')),
                "desc_preview": str(b.get('描述', ''))[:150] if b.get('描述') else ""
            })
        
        prompt = f"""作为资深测试架构师，深度分析【{module_name}】模块的 Bug 数据，提取测试重点指标。

基础统计数据:
- 总Bug数: {stats['total']}
- 线上故障: {stats['online_count']}条
- 二次打开: {stats['reopened_count']}条
- 严重程度分布: {json.dumps(stats['severity_dist'], ensure_ascii=False)}
- 功能点分布: {json.dumps(stats['feature_dist'], ensure_ascii=False)}

Bug样本数据(已按优先级排序):
```json
{json.dumps(bug_samples, ensure_ascii=False, indent=2)}
```

请进行深度分析:

1. **问题模式识别**: 从Bug标题和描述中识别出3-5个核心问题模式
   - 例如: 数据缺失问题、权限控制问题、UI兼容性问题等

2. **根因推断**: 分析这些问题最可能的技术根因
   - 前端/后端/数据/配置/第三方依赖等

3. **高频场景**: 提取最容易出问题的用户场景或功能点

4. **测试建议**: 针对每个问题模式给出具体的测试验证策略

5. **风险评级**: 综合判断该模块的整体质量风险等级

输出必须为标准JSON格式:
```json
{{
  "core_issue_patterns": [
    {{
      "pattern_name": "问题模式名称",
      "evidence": ["相关Bug标题1", "相关Bug标题2"],
      "frequency": "high/medium/low",
      "root_cause": "推断的技术根因",
      "test_strategy": "具体测试策略"
    }}
  ],
  "high_risk_scenarios": ["场景1", "场景2", "场景3"],
  "technical_insights": {{
    "primary_domain": "主要问题域(前端/后端/数据/接口)",
    "architecture_concern": "架构层面关注点",
    "integration_risks": ["集成风险1", "集成风险2"]
  }},
  "actionable_recommendations": [
    {{
      "priority": "P0/P1/P2",
      "action": "具体行动项",
      "rationale": "原因说明"
    }}
  ]
}}
"""

        messages = [
            {"role": "system", "content": "你是资深测试架构师，擅长从Bug数据中提炼质量风险和测试策略。输出必须是合法JSON格式，不要有任何额外说明文字。"},
            {"role": "user", "content": prompt}
        ]
        
        try:
            result = await self._call_llm(messages, temperature=0.2)
            
            # 解析JSON
            import re
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                logger.info(f"[Qwen AI] 模块深度分析[{module_name}]: 识别 {len(analysis.get('core_issue_patterns', []))} 个问题模式")
                return analysis
            else:
                raise ValueError("未找到JSON格式的分析结果")
                
        except Exception as e:
            logger.error(f"[Qwen AI] 深度分析失败[{module_name}]: {e}")
            return self._fallback_layer2_analysis(stats)
    
    async def _layer3_correlation_analysis(self, module_name: str, bugs: List[Dict], stats: Dict, insights: Dict) -> Dict:
        """第三层: 关联分析 - 发现跨模块/跨时间模式"""
        # 分析Bug的创建时间分布，识别时间模式
        from collections import Counter
        from datetime import datetime
        
        time_patterns = []
        creators = Counter()
        
        for b in bugs:
            # 统计创建者
            creator = b.get('创建者') or b.get('creator')
            if creator:
                creators[creator] += 1
            
            # 提取创建时间（如果有）
            created = b.get('创建时间') or b.get('created')
            if created:
                try:
                    if isinstance(created, str):
                        dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        time_patterns.append(dt.strftime('%Y-%m'))
                except:
                    pass
        
        # 识别集中爆发期
        time_counter = Counter(time_patterns)
        peak_periods = [p for p, c in time_counter.most_common(2) if c >= 5]
        
        return {
            "cross_module_patterns": [],  # 预留：跨模块分析
            "time_patterns": {
                "peak_periods": peak_periods,
                "monthly_dist": dict(time_counter)
            },
            "creator_concentration": {
                "top_creators": dict(creators.most_common(3)),
                "concentration_risk": creators.most_common(1)[0][1] / len(bugs) > 0.5 if creators else False
            },
            "similar_issues": []  # 预留：相似问题聚类
        }
    
    def _merge_focus_points(self, layer1: Dict, layer2: Dict, layer3: Dict) -> List[Dict]:
        """合并三层分析结果，生成最终的测试关注点列表"""
        focus_points = []
        
        # 从第一层提取统计类关注点
        if layer1.get('online_count', 0) > 0:
            focus_points.append({
                "type": "线上故障",
                "level": "high" if layer1['online_count'] >= 5 else "medium",
                "description": f"含{layer1['online_count']}条线上故障，占比{round(layer1['online_count']/layer1['total']*100)}%",
                "test_suggestion": "重点验证线上已发生场景，确保修复彻底",
                "source": "layer1"
            })
        
        if layer1.get('reopened_count', 0) > 0:
            focus_points.append({
                "type": "二次打开",
                "level": "high",
                "description": f"{layer1['reopened_count']}条Bug被重新打开，修复质量需关注",
                "test_suggestion": "加强回归验证，确保问题彻底解决",
                "source": "layer1"
            })
        
        # 从第二层提取AI洞察
        for pattern in layer2.get('core_issue_patterns', []):
            focus_points.append({
                "type": pattern.get('pattern_name', '问题模式'),
                "level": pattern.get('frequency', 'medium'),
                "description": f"{pattern.get('pattern_name')}: {', '.join(pattern.get('evidence', [])[:2])}",
                "test_suggestion": pattern.get('test_strategy', '建议专项测试'),
                "root_cause": pattern.get('root_cause', ''),
                "source": "layer2"
            })
        
        # 从第三层提取关联洞察
        if layer3.get('time_patterns', {}).get('peak_periods'):
            focus_points.append({
                "type": "时间模式",
                "level": "medium",
                "description": f"Bug集中在{'、'.join(layer3['time_patterns']['peak_periods'])}爆发",
                "test_suggestion": "关注同期发布的功能，可能存在系统性问题",
                "source": "layer3"
            })
        
        # 按优先级排序
        level_order = {"high": 0, "medium": 1, "low": 2}
        focus_points.sort(key=lambda x: level_order.get(x.get('level', 'medium'), 1))
        
        return focus_points[:6]  # 最多返回6条
    
    def _calculate_risk_level(self, layer1: Dict, layer2: Dict) -> str:
        """综合计算风险等级"""
        score = 0
        
        # 第一层评分
        if layer1.get('online_count', 0) > 0:
            score += 30
        if layer1.get('reopened_count', 0) > 0:
            score += 20
        if layer1.get('severity_dist', {}).get('致命', 0) > 0:
            score += 40
        if layer1.get('severity_dist', {}).get('严重', 0) > 3:
            score += 20
        
        # 第二层评分
        high_freq_patterns = sum(1 for p in layer2.get('core_issue_patterns', []) if p.get('frequency') == 'high')
        score += high_freq_patterns * 10
        
        if score >= 60:
            return "high"
        elif score >= 30:
            return "medium"
        return "low"
    
    def _generate_test_strategy(self, layer1: Dict, layer2: Dict) -> Dict:
        """生成整体测试策略"""
        return {
            "primary_focus": layer2.get('technical_insights', {}).get('primary_domain', '功能回归'),
            "priority_areas": layer2.get('high_risk_scenarios', []),
            "recommended_approach": "全面回归" if layer1.get('total', 0) > 20 else "重点场景验证",
            "special_attention": layer2.get('technical_insights', {}).get('integration_risks', [])
        }
    
    def _identify_risk_indicators(self, bugs: List[Dict]) -> List[str]:
        """识别高风险指标"""
        indicators = []
        
        for b in bugs:
            title = str(b.get('标题', '')).lower()
            desc = str(b.get('描述', '')).lower()
            
            # 关键词风险识别
            risk_keywords = {
                'crash': '应用崩溃',
                '白屏': '页面白屏',
                '死循环': '死循环',
                '数据丢失': '数据丢失',
                '无法登录': '登录阻塞',
                '504': '服务端超时',
                'timeout': '超时问题'
            }
            
            for keyword, risk in risk_keywords.items():
                if keyword in title or keyword in desc:
                    indicators.append(risk)
        
        return list(set(indicators))  # 去重
    
    def _fallback_layer2_analysis(self, stats: Dict) -> Dict:
        """第二层分析失败时的降级处理"""
        return {
            "core_issue_patterns": [],
            "high_risk_scenarios": [],
            "technical_insights": {
                "primary_domain": "未知",
                "architecture_concern": "AI分析失败，使用基础统计",
                "integration_risks": []
            },
            "actionable_recommendations": [
                {
                    "priority": "P1",
                    "action": "基于统计数据进行常规回归测试",
                    "rationale": "AI分析服务暂时不可用"
                }
            ]
        }
    
    def _empty_module_analysis(self, module_name: str) -> Dict:
        """空模块的默认返回"""
        return {
            "module_name": module_name,
            "total_count": 0,
            "layer1_stats": {},
            "layer2_insights": {},
            "layer3_correlations": {},
            "focus_points": [],
            "risk_level": "low",
            "test_strategy": {},
            "ai_generated_at": datetime.now().isoformat()
        }


# ============================================================
# 工厂函数: 根据 provider 名称创建对应实例
# ============================================================

def get_ai_provider(provider_name: str = 'qwen', config_id: int = None) -> BugAnalysisAIProvider:
    """
    工厂函数: 创建 AI 提供者实例

    Args:
        provider_name: AI 提供者名称（仅支持 'qwen'）
        config_id: AIModelConfig ID

    Returns:
        BugAnalysisAIProvider 实例 (QwenBugAnalysisAI)

    Raises:
        ValueError: 不支持的 provider 名称
    """
    # 强制使用 qwen，忽略 mock 请求
    actual_provider = provider_name.lower()
    if actual_provider == 'mock':
        logger.warning("Mock AI 已禁用，强制使用 Qwen AI")
        actual_provider = 'qwen'

    if actual_provider != 'qwen':
        raise ValueError(f"不支持的 AI 提供者: {provider_name}，仅支持: qwen")

    instance = QwenBugAnalysisAI(config_id=config_id)
    logger.info(f"初始化 AI 提供者: qwen → QwenBugAnalysisAI")
    return instance
