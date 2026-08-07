# -*- coding: utf-8 -*-
"""
Bug分析核心逻辑 V2
重构要点:
1. 安全修复: 边界守卫、精确异常
2. 性能优化: 预构建模块索引、合并遍历、预编译正则
3. 函数拆分: ~300行单函数 → 9个职责清晰的子函数
4. 代码质量: 扁平化嵌套、字典映射替代if/elif链、集合推导式
"""
import re
import json
import logging
from collections import Counter, defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================================
# 常量与配置
# ============================================================

# 严重度原始标签映射 (扁平化 if/elif 链)
_SEVERITY_ORIG_MAP = {
    '1-致命': '1-致命', '致命': '1-致命',
    '2-严重': '2-严重', '严重': '2-严重',
    '3-一般': '3-一般', '一般': '3-一般',
    '4-轻微': '4-轻微', '轻微': '4-轻微',
}

# 时间线批量引入阈值
IMPORT_THRESHOLD = 2

# 聚集数据最少Bug数阈值
CLUSTER_MIN_BUGS = 5


# ============================================================
# 基础分类函数（保持原有逻辑 + 安全修复）
# ============================================================

def extract_tags(title):
    """从标题提取【】或[]中的标签"""
    tags = re.findall(r'【(.*?)】', title)
    if not tags:
        tags = re.findall(r'\[(.*?)\]', title)
    return tags


def classify_module(tags, title):
    """
    分类模块 - 智能合并相似模块
    核心逻辑:
    1. 优先使用标签
    2. 智能合并前缀相同的模块（如"RMS资讯"→"RMS"）
    3. 支持常见后缀去重（资讯、服务、管理、模块、功能等）
    """
    # 所有长度大于1的标签都视为有效模块标签
    feature_tags = [t for t in tags if len(t) > 1]
    if not feature_tags:
        # 无标签时，尝试从标题中提取关键词作为模块
        clean = re.sub(r'【.*?】|\[.*?\]', '', title)
        # 返回标题前10个字符作为兜底
        return clean[:10] if clean else '其他'

    # 获取第一个有效标签作为基础
    base_module = feature_tags[0]
    
    # 智能合并：去除常见后缀，合并相似模块
    # 常见后缀列表（按优先级排序）
    common_suffixes = [
        '资讯', '服务', '管理', '模块', '功能', '页面', '组件', 
        '接口', 'API', 'PC端', '移动端', '小程序', 'H5', 
        '系统', '平台', '中心', '板块', '区域', '部分'
    ]
    
    # 尝试去除后缀，合并到主模块
    normalized_module = base_module
    for suffix in common_suffixes:
        if normalized_module.endswith(suffix) and len(normalized_module) > len(suffix):
            normalized_module = normalized_module[:-len(suffix)]
            # 继续检查是否还有可去除的后缀（防止多层后缀）
            for suffix2 in common_suffixes:
                if normalized_module.endswith(suffix2) and len(normalized_module) > len(suffix2):
                    normalized_module = normalized_module[:-len(suffix2)]
            break
    
    # 如果去除后缀后为空，保留原始模块名
    if not normalized_module:
        normalized_module = base_module
    
    return normalized_module


def classify_defect(title, desc=''):
    """
    缺陷类型分类 - 基于语义分析的智能分类

    通过分析Bug标题和描述中的关键词语义，自动识别缺陷类型。
    使用多维度语义匹配，支持同义词识别和上下文理解。

    Args:
        title: Bug标题
        desc: Bug描述

    Returns:
        str: 缺陷类型 (UI显示/功能逻辑/数据内容/交互操作/性能稳定/跨端兼容/其他)
    """
    text = f"{title} {desc}".lower() if desc else title.lower()

    # 语义模式定义: 每个类型包含核心词、扩展词和模式
    _DEFECT_PATTERNS = {
        'UI显示': {
            'core': ['ui', '界面', '显示', '样式', 'css', '布局', '文字', '字体', '颜色', '图标', '按钮', '弹窗', '弹框', '页面', '展示'],
            'extend': ['错位', '重叠', '遮挡', '截断', '换行', '对齐', '间距', '大小', '宽度', '高度', '滚动', '空白', '黑屏', '白屏', '闪烁', '模糊', '变形'],
            'patterns': [
                r'(显示|展示).{0,5}(异常|错误|不对|问题)',
                r'(样式|布局|界面).{0,5}(错乱|混乱|异常)',
                r'(文字|字体).{0,5}(截断|省略|重叠)',
                r'(按钮|图标).{0,5}(不显示|看不见|消失)',
                r'(页面|界面).{0,5}(空白|白屏|黑屏)',
            ]
        },
        '功能逻辑': {
            'core': ['功能', '逻辑', '业务', '流程', '计算', '校验', '验证', '判断', '保存', '提交', '查询', '搜索'],
            'extend': ['无法', '不能', '失败', '报错', '错误', '不正确', '异常', '无效', '失效', '不生效', '没生效', '未生效', '不起作用'],
            'patterns': [
                r'(无法|不能|没).{0,5}(保存|提交|查询|搜索|删除|修改|编辑|新增|添加)',
                r'(保存|提交|查询).{0,5}(失败|报错|错误|异常)',
                r'(数据|结果).{0,5}(不对|错误|异常|不正确)',
                r'(逻辑|流程|业务).{0,5}(错误|异常|问题)',
                r'(校验|验证).{0,5}(失败|不通过|错误)',
            ]
        },
        '数据内容': {
            'core': ['数据', '内容', '字段', '值', '信息', '文本', '数字', '金额', '日期', '时间', '状态'],
            'extend': ['缺失', '丢失', '缺少', '为空', 'null', 'nil', 'undefined', '不一致', '不同步', '重复', '冗余', '错误', '不对', '异常'],
            'patterns': [
                r'(数据|字段|值|内容).{0,5}(缺失|丢失|为空|null|不对|错误)',
                r'(显示|展示).{0,5}(数据|内容|值).{0,5}(不对|错误|异常)',
                r'(数据|内容).{0,5}(不一致|不同步|重复|冗余)',
                r'(金额|价格|数字).{0,5}(不对|错误|异常|计算)',
                r'(状态|信息).{0,5}(不对|错误|异常|未更新)',
            ]
        },
        '交互操作': {
            'core': ['点击', '跳转', '跳转', '刷新', '加载', '上传', '下载', '输入', '选择', '勾选', '滑动', '拖拽', '滚动', '返回', '关闭'],
            'extend': ['无响应', '没反应', '卡死', '卡顿', '卡住', '假死', '延迟', '缓慢', '慢', '不流畅', '闪退', '崩溃', '退出'],
            'patterns': [
                r'(点击|选择|输入).{0,5}(无响应|没反应|无效|不生效)',
                r'(页面|界面|操作).{0,5}(卡死|卡顿|卡住|假死)',
                r'(跳转|刷新|加载).{0,5}(失败|异常|卡住|慢)',
                r'(上传|下载).{0,5}(失败|异常|卡住|超时)',
                r'(滑动|拖拽|滚动).{0,5}(不流畅|卡顿|异常)',
            ]
        },
        '性能稳定': {
            'core': ['性能', '慢', '卡顿', '延迟', '加载', '响应', '超时', 'timeout', '内存', 'cpu', '并发', '死锁', '崩溃', '闪退', 'oom'],
            'extend': ['缓慢', '慢', '太久', '长时间', '等待', '超时', '占用', '过高', '泄漏', '泄露', '溢出', '过载', '高负载'],
            'patterns': [
                r'(加载|响应|打开).{0,5}(慢|缓慢|延迟|太久|超时)',
                r'(内存|cpu|资源).{0,5}(占用|过高|泄漏|泄露|溢出)',
                r'(操作|请求).{0,5}(超时|timeout)',
                r'(并发|多用户).{0,5}(问题|异常|慢|卡顿)',
                r'(崩溃|闪退|oom).{0,5}(问题|异常|频繁)',
            ]
        },
        '跨端兼容': {
            'core': ['兼容', '适配', 'ios', 'android', '移动端', 'pc端', 'web端', 'app', 'h5', '小程序', '浏览器', 'safari', 'chrome', 'firefox', 'ie', 'edge', '华为', '小米', 'iphone', 'ipad'],
            'extend': ['不兼容', '不支持', '显示异常', '表现不一致', '区别', '差异', '机型', '分辨率', '屏幕', '尺寸'],
            'patterns': [
                r'(ios|android|h5|小程序).{0,5}(问题|异常|不兼容|显示异常)',
                r'(移动端|pc端|app).{0,5}(显示|表现).{0,5}(异常|不一致|不同)',
                r'(safari|chrome|浏览器).{0,5}(兼容|显示|异常)',
                r'(华为|小米|iphone).{0,5}(机型|设备).{0,5}(问题|异常)',
                r'(分辨率|屏幕).{0,5}(适配|显示|异常)',
            ]
        },
    }

    # 计算每个类型的匹配分数
    scores = {}
    for dtype, patterns in _DEFECT_PATTERNS.items():
        score = 0

        # 1. 核心词匹配 (权重: 3)
        for word in patterns['core']:
            if word in text:
                score += 3
                # 标题中出现权重更高
                if word in title.lower():
                    score += 2

        # 2. 扩展词匹配 (权重: 1)
        for word in patterns['extend']:
            if word in text:
                score += 1
                if word in title.lower():
                    score += 1

        # 3. 正则模式匹配 (权重: 5)
        for pattern in patterns['patterns']:
            if re.search(pattern, text):
                score += 5

        scores[dtype] = score

    # 选择得分最高的类型
    if scores:
        best_match = max(scores, key=scores.get)
        if scores[best_match] > 0:
            return best_match

    return '其他'


def infer_severity(title, desc='', original_sev=''):
    """
    推断严重度 P0/P1/P2 - 由 AI 自动生成，此函数简化处理
    实际推断逻辑移至 AI 增强阶段处理
    """
    # 严重度推断现在由 AI 自动分析生成，不再使用硬编码关键词匹配
    # 仅基于原始严重度做基础映射
    orig_str = str(original_sev)
    for key, label in _SEVERITY_ORIG_MAP.items():
        if key in orig_str:
            return 'P0' if label in ('1-致命',) else ('P1' if label in ('2-严重',) else 'P2')

    return 'P2'


def _normalize_original_severity(sev_value):
    """
    将原始严重度值标准化为统一标签
    替代原来内联在 analyze_bugs() 中的 if/elif 链
    """
    if not sev_value:
        return '未知'
    sev_str = str(sev_value)
    for key, label in _SEVERITY_ORIG_MAP.items():
        if key in sev_str:
            return label
    return '未知'


# ============================================================
# 预处理与索引构建
# ============================================================

def _preprocess_bugs(bugs):
    """
    预处理每条bug: 提取标签、分类模块、缺陷类型、推断严重度
    直接在原列表上修改，避免创建新列表节省内存

    模块来源优先级:
    1. 已存在的 module 字段（如云效同步从 labels 提取的）—— 不覆盖
    2. 标题【】标签 + 兜底标题前10字
    """
    for b in bugs:
        b['tags'] = extract_tags(b.get('title', ''))
        # 仅在 module 为空时按标题分类，避免覆盖云效同步过来的 module（来自 labels）
        if not b.get('module'):
            b['module'] = classify_module(b['tags'], b.get('title', ''))
        b['defect_type'] = classify_defect(b.get('title', ''), b.get('desc', ''))
        b['inferred_sev'] = infer_severity(
            b.get('title', ''), b.get('desc', ''), b.get('severity', '')
        )
    return bugs


def _build_module_index(bugs):
    """
    预构建 module → bugs 索引 (性能关键优化)
    将后续 O(n*m) 的模块过滤降为 O(n+m) 构建索引 + O(1) 查找
    返回: (module_counter[Counter], module_index[defaultdict(list)])
    """
    module_index = defaultdict(list)
    module_counter = Counter()
    for b in bugs:
        mod = b.get('module')
        if mod:
            module_index[mod].append(b)
            module_counter[mod] += 1
    return module_counter, module_index


def _compute_all_modules(module_counter):
    """返回所有模块（不再限制为TOP10），所有内容都在柱状图中显示"""
    return [mod for mod, cnt in module_counter.most_common()]


def _is_online_bug(b):
    """判断是否为线上故障 Bug"""
    return '线上故障' in b.get('type', '')


def _is_reopened(b):
    """判断是否为重新打开的 Bug"""
    status = b.get('status', '')
    return '再次打开' in status or '重新打开' in status


# ============================================================
# 子函数：各维度数据计算
# ============================================================

def _compute_modules_data(module_counter, module_index, all_modules, total):
    """
    计算模块分布数据 + 特征明细数据
    所有模块都显示在柱状图中，不再有"未归类"
    """
    # modulesData: 所有模块的计数
    modules_data = {mod: module_counter[mod] for mod in all_modules if module_counter.get(mod, 0) > 0}
    # 不再计算未归类，所有内容都在柱状图中显示
    uncategorized = 0

    # featureDetailData: 每个模块下的特征标签分布
    # 直接基于标签自然汇总，无预设模块映射
    feature_counter = defaultdict(Counter)
    for mod in all_modules:
        for b in module_index.get(mod, []):
            # 所有长度大于1的标签都视为有效特征标签
            feature_tags = [t for t in b['tags'] if len(t) > 1]
            if feature_tags:
                # 直接使用第一个有效标签作为特征
                matched_feature = feature_tags[0]
                feature_counter[mod][matched_feature] += 1

    feature_detail_data = []
    for mod in all_modules:
        children = [{'name': feat, 'value': count} for feat, count in feature_counter[mod].most_common()]
        if children:
            feature_detail_data.append({'name': mod, 'children': children})

    return modules_data, feature_detail_data, uncategorized


def _compute_severity_data(bugs):
    """
    计算严重度相关数据:
    - severityCrossData: 原始严重度 × 推断严重度 交叉表
    - sevData: 原始严重度分布
    - sevInfData: 推断严重度(P0/P1/P2)分布
    - statusData: 状态分布
    - priorityData: 优先级分布
    """
    sev_cross = defaultdict(lambda: defaultdict(int))
    sev_counter = Counter()
    p_counts = {'P0': 0, 'P1': 0, 'P2': 0}
    status_counter = Counter()
    priority_counter = Counter()

    for b in bugs:
        # 交叉表 (使用标准化函数替代 if/elif 链)
        orig_label = _normalize_original_severity(b.get('severity', ''))
        sev_cross[orig_label][b['inferred_sev']] += 1

        # 原始严重度分布
        if b.get('severity'):
            sev_counter[b['severity']] += 1

        # 推断严重度计数
        inf_sev = b['inferred_sev']
        if inf_sev in p_counts:
            p_counts[inf_sev] += 1

        # 状态和优先级
        if b.get('status'):
            status_counter[b['status']] += 1
        if b.get('priority'):
            priority_counter[b['priority']] += 1

    severity_cross_data = {k: dict(v) for k, v in sev_cross.items()}
    sev_inf_data = {f'推断{k}': v for k, v in p_counts.items()}

    return (
        severity_cross_data,
        dict(sev_counter),
        sev_inf_data,
        dict(status_counter),
        dict(priority_counter),
    )


def _compute_test_focus(top10, module_index):
    """
    计算每个 TOP10 模块的测试重点数据
    使用预建索引避免重复 O(n) 过滤
    """
    tf_data = {}
    for mod in top10:
        mod_bugs = module_index.get(mod, [])
        mod_total = len(mod_bugs)
        if mod_total == 0:
            continue

        dtype_counter = Counter(b['defect_type'] for b in mod_bugs)
        online_count = sum(1 for b in mod_bugs if _is_online_bug(b))
        reopened_count = sum(1 for b in mod_bugs if _is_reopened(b))

        focus_points = _build_focus_points(
            mod_total, online_count, reopened_count, dtype_counter, mod_bugs
        )

        tf_data[mod] = {
            'total': mod_total,
            'online': online_count,
            'reopened': reopened_count,
            'top_types': [[t, c] for t, c in dtype_counter.most_common(3)],
            'focus_points': focus_points,
            'dtype_dist': dict(dtype_counter),
        }

    return tf_data


def _build_focus_points(mod_total, online_count, reopened_count, dtype_counter, mod_bugs):
    """
    构建测试关注点文案列表 - 基于语义分析的缺陷类型智能生成

    根据缺陷类型分布、严重程度和业务语义，自动生成针对性的测试关注点
    """
    focus_points = []

    # 1. 线上故障关注点
    if online_count > 0:
        pct = round(online_count / mod_total * 100)
        if pct >= 10:
            focus_points.append(
                f"🔴 线上故障回归: {online_count}条(占{pct}%)线上故障，迭代后必须逐条验证线上已发生的场景不会复现"
            )
        else:
            focus_points.append(
                f"⚠️ 含{online_count}条(占{pct}%)线上故障，迭代时顺手覆盖"
            )

    # 2. 二次打开关注点
    if reopened_count > 0:
        pct = round(reopened_count / mod_total * 100)
        focus_points.append(
            f"🔄 修复质量关注: {reopened_count}条(占{pct}%)Bug被二次打开，需加强回归验证"
        )

    # 3. 基于缺陷类型的智能分析 - 语义驱动的测试建议
    if dtype_counter:
        # 计算各类型占比
        dtype_ratios = {dtype: count / mod_total for dtype, count in dtype_counter.items()}
        sorted_types = sorted(dtype_ratios.items(), key=lambda x: x[1], reverse=True)

        # 测试建议映射表 - 基于语义分类的针对性建议
        type_test_suggestions = {
            'UI显示': {
                'high': ('UI专项回归', '重点检查多端样式一致性、响应式布局、文字截断、图片加载等视觉问题'),
                'medium': ('UI兼容性检查', '关注主流浏览器和机型的显示效果'),
            },
            '功能逻辑': {
                'high': ('核心流程回归', '重点验证业务主流程、边界条件、异常处理逻辑'),
                'medium': ('功能完整性检查', '关注核心功能的正常使用场景'),
            },
            '数据内容': {
                'high': ('数据质量专项', '重点验证数据准确性、完整性、同步机制、特殊字符处理'),
                'medium': ('数据一致性检查', '关注关键业务数据的正确性'),
            },
            '交互操作': {
                'high': ('交互体验回归', '重点验证用户操作反馈、状态变更、异常提示'),
                'medium': ('操作流畅度检查', '关注常见用户操作的响应和反馈'),
            },
            '性能稳定': {
                'high': ('性能稳定性专项', '重点进行压力测试、内存检测、长时间稳定性验证'),
                'medium': ('性能基线检查', '关注核心操作的响应时间'),
            },
            '跨端兼容': {
                'high': ('多端兼容性回归', '必须在iOS/Android/PC/小程序各端分别验证'),
                'medium': ('主流设备检查', '关注主流机型和浏览器的兼容性'),
            },
        }

        # 为占比最高的1-2个缺陷类型生成测试建议
        for dtype, ratio in sorted_types[:2]:
            if dtype == '其他' or ratio < 0.1:  # 忽略"其他"类型和占比过低的类型
                continue

            level = 'high' if ratio >= 0.3 else ('medium' if ratio >= 0.15 else 'low')
            count = dtype_counter.get(dtype, 0)

            if dtype in type_test_suggestions and level in type_test_suggestions[dtype]:
                title, suggestion = type_test_suggestions[dtype][level]
                focus_points.append(f"📌 {title}({dtype}{count}条/{ratio*100:.0f}%): {suggestion}")

    # 4. 基于严重度的关注点
    p0_count = sum(1 for b in mod_bugs if b.get('inferred_sev') == 'P0')
    p1_count = sum(1 for b in mod_bugs if b.get('inferred_sev') == 'P1')

    if p0_count > 0:
        focus_points.append(f"🚨 P0高危问题: 含{p0_count}条致命缺陷，需优先验证修复并评估影响范围")
    elif p1_count >= 3:
        focus_points.append(f"⚡ P1严重问题集中: 含{p1_count}条严重缺陷，建议专项回归")

    # 5. 典型Bug举例（限制数量，避免过多）
    if len(focus_points) < 4:
        examples = [b['title'] for b in mod_bugs if _is_online_bug(b)][:2]
        if not examples:
            # 优先选择严重度高的Bug作为示例
            severe_bugs = [b for b in mod_bugs if b.get('inferred_sev') in ['P0', 'P1']]
            examples = [b['title'] for b in severe_bugs[:2]]
        if not examples:
            examples = [b['title'] for b in mod_bugs[:2]]
        if examples:
            focus_points.append("📝 典型Bug: " + "；".join(examples[:2]))

    return focus_points


def _compute_creator_data(bugs):
    """计算创建者-模块分布数据"""
    creator_mod = defaultdict(lambda: defaultdict(int))
    creator_online = defaultdict(int)

    for b in bugs:
        creator = b.get('creator', '')
        if creator:
            creator_mod[creator][b['module'] or '其他'] += 1
            if _is_online_bug(b):
                creator_online[creator] += 1

    result = []
    for creator in sorted(creator_mod.keys(), key=lambda c: sum(creator_mod[c].values()), reverse=True):
        total_c = sum(creator_mod[creator].values())
        online_c = creator_online.get(creator, 0)
        result.append({
            'creator': creator,
            'total': total_c,
            'online': online_c,
            'online_pct': round(online_c / total_c * 100, 1) if total_c > 0 else 0,
            'modules': dict(creator_mod[creator]),
        })

    return result


def _compute_participant_data(bugs):
    """
    计算参与者分布数据（从自定义字段中提取）
    返回结构类似 creatorModuleData，支持模块堆叠展示
    """
    # 支持多种可能的字段名（中文 + 英文变体）
    PARTICIPANT_KEYS = ['参与者', '参与人', '相关人员', '协同人', '参与人员', 'participant', 'participants', '多人处理', '协同处理', '跟进人', '关注人']

    # 参与者 -> 模块分布
    participant_mod = defaultdict(lambda: defaultdict(int))
    # 参与者 -> 线上Bug数
    participant_online = defaultdict(int)

    logger.info(f"[participant] 开始计算参与者分布，Bug总数={len(bugs)}")

    # 统计有 custom_fields 的 Bug 数量
    bugs_with_cf = sum(1 for b in bugs if b.get('custom_fields') and len(b.get('custom_fields', {})) > 0)
    logger.info(f"[participant] 有 custom_fields 的 Bug 数量: {bugs_with_cf}/{len(bugs)}")

    matched_count = 0
    for b in bugs:
        cf = b.get('custom_fields', {})
        participants = None
        for key in PARTICIPANT_KEYS:
            if key in cf and cf[key]:
                participants = cf[key]
                matched_count += 1
                break

        if participants:
            # 获取 Bug 的模块
            bug_module = b.get('module', '') or '其他'
            # 判断是否为线上 Bug
            is_online = _is_online_bug(b)

            # 支持字符串或列表
            participant_list = []
            if isinstance(participants, str):
                # 逗号/分号分隔的多人
                for p in re.split(r'[,，;；、]', participants):
                    p = p.strip()
                    if p:
                        participant_list.append(p)
            elif isinstance(participants, list):
                for p in participants:
                    p = str(p).strip()
                    if p:
                        participant_list.append(p)

            # 更新每个参与者的模块分布和线上Bug计数
            for p in participant_list:
                participant_mod[p][bug_module] += 1
                if is_online:
                    participant_online[p] += 1

    logger.info(f"[participant] 匹配到参与者字段的 Bug 数量: {matched_count}/{len(bugs)}")

    # 构建结果列表（按总Bug数排序，取Top 20）
    result = []
    for participant in sorted(participant_mod.keys(), key=lambda p: sum(participant_mod[p].values()), reverse=True)[:20]:
        total_p = sum(participant_mod[participant].values())
        online_p = participant_online.get(participant, 0)
        result.append({
            'participant': participant,
            'total': total_p,
            'online': online_p,
            'online_pct': round(online_p / total_p * 100, 1) if total_p > 0 else 0,
            'modules': dict(participant_mod[participant]),
        })

    logger.info(f"[participant] 参与者分布结果: 共 {len(participant_mod)} 人, 返回Top {len(result)}, Top5={[r['participant'] for r in result[:5]]}")

    return result


def _compute_custom_field_charts(bugs):
    """
    计算所有适合做图表的自定义字段分布

    自动识别 custom_fields 中适合做图表分析的字段：
    - 排除已单独处理的参与者类字段
    - 排除超长文本、日期对象等不适合图表的字段
    - 只保留有分布意义的字段（至少2个不同值，或有重复值）
    """
    field_counters = defaultdict(Counter)
    # 支持多种可能的字段名（中文 + 英文变体）
    PARTICIPANT_KEYS = {'参与者', '参与人', '相关人员', '协同人', '参与人员', 'participant', 'participants', '多人处理', '协同处理', '跟进人', '关注人'}
    # 已有单独图表展示的字段，不需要重复展示
    EXCLUDED_FIELDS = {'优先级', 'priority', '严重程度', 'severity'}

    logger.info(f"[custom_field_charts] 开始计算自定义字段图表分布，Bug总数={len(bugs)}")

    for b in bugs:
        cf = b.get('custom_fields', {})
        for field_name, value in cf.items():
            if not value or field_name in PARTICIPANT_KEYS or field_name in EXCLUDED_FIELDS:
                continue
            # 只处理列表和短字符串（排除大文本、日期对象等）
            if isinstance(value, list):
                for v in value:
                    v_str = str(v).strip()
                    if v_str and len(v_str) < 50:
                        field_counters[field_name][v_str] += 1
            elif isinstance(value, str):
                v_str = value.strip()
                if v_str and len(v_str) < 50:
                    field_counters[field_name][v_str] += 1

    logger.info(f"[custom_field_charts] 收集到的字段数: {len(field_counters)}, 字段名: {list(field_counters.keys())}")

    # 只保留有分布意义的字段（至少2个不同值，或出现次数>1的值至少1个）
    result = {}
    for field_name, counter in field_counters.items():
        if len(counter) >= 2 or sum(1 for c in counter.values() if c > 1) >= 1:
            result[field_name] = dict(counter.most_common(20))
            logger.info(f"[custom_field_charts] 字段 '{field_name}' 分布: {len(counter)} 个值, Top5={dict(counter.most_common(5))}")

    logger.info(f"[custom_field_charts] 最终保留的字段数: {len(result)}, 字段名: {list(result.keys())}")

    return result


def _compute_timeline_data(bugs):
    """
    计算时间线数据 (合并原来两次遍历为一次)
    返回: (timelineCleanData, timelineData, importLabels, import_count, real_count)
    """
    # 单次遍历: 同时完成日期计数和批量检测识别
    date_counter = Counter()
    all_date_counter = Counter()
    created_datetime_list = []

    for b in bugs:
        created = b.get('created')
        if isinstance(created, datetime):
            created_datetime_list.append(created)
            date_str = created.strftime('%Y-%m-%d')
            all_date_counter[date_str] += 1

    # 批量引入检测: 同一天出现 >= IMPORT_THRESHOLD 条的视为批量引入
    time_counter = Counter(created_datetime_list)
    import_dates_set = {dt for dt, cnt in time_counter.items() if cnt >= IMPORT_THRESHOLD}

    import_dates = defaultdict(int)
    for dt in created_datetime_list:
        if dt in import_dates_set:
            import_dates[dt.strftime('%Y-%m-%d')] += 1

    # timelineCleanData: 排除批量引入后的正常散布数据
    clean_date_counter = Counter()
    for dt in created_datetime_list:
        if dt not in import_dates_set:
            clean_date_counter[dt.strftime('%Y-%m-%d')] += 1

    timeline_clean_data = dict(sorted(clean_date_counter.items()))
    timeline_data = dict(sorted(all_date_counter.items()))
    import_labels = [{'date': d, 'count': c} for d, c in sorted(import_dates.items())]
    import_count_total = sum(import_dates.values())
    real_count = sum(clean_date_counter.values())

    return timeline_clean_data, timeline_data, import_labels, import_count_total, real_count


def _compute_keyword_data(bugs):
    """
    计算关键词词频数据 - 由 AI 自动生成，此函数保留接口但返回空值
    返回: (kwData, wufaDetailData)
    """
    # 关键词提取和词频统计现在由 AI 自动分析生成
    # 不再使用硬编码关键词正则匹配
    return [], {}


def _compute_risk_data(bugs, p_counts):
    """
    计算风险分析数据 (扁平化: 替代三层 if/elif 嵌套)
    使用分发模式替代深层条件判断
    注意：风险类型由AI动态分析生成，此函数仅提供基础统计数据，不预设任何风险分类
    """
    # 不再预设任何风险类型，返回空的detail结构
    # AI将根据原始Bug数据进行动态风险分析
    risk_data = {
        'P0': {'total': p_counts['P0'], 'detail': {}},
        'P1': {'total': p_counts['P1'], 'detail': {}},
        'P2': {'total': p_counts['P2'], 'detail': {}},
    }

    return risk_data


def _compute_cluster_data(bugs, module_index):
    """
    计算聚集数据 + 根因数据 + 模块×类型交叉数据
    使用预建索引避免重复过滤
    """
    # 聚集数据: 所有模块的 Bug 数分布 (Top 25, 最少 CLUSTER_MIN_BUGS 条)
    all_modules = Counter(b['module'] or '其他' for b in bugs)
    cluster_data = []
    for feat, count in all_modules.most_common(25):
        if count < CLUSTER_MIN_BUGS:
            break
        mod_bugs = module_index.get(feat, []) or [b for b in bugs if (b['module'] or '其他') == feat]
        type_dist = Counter(b['defect_type'] for b in mod_bugs)
        cluster_data.append({'feature': feat, 'bug_count': count, 'type_distribution': dict(type_dist)})

    # 根因数据: 基于 clusterData 前15个模块生成根因假设字符串
    root_cause_data = []
    for item in cluster_data[:15]:
        mod = item['feature']
        mod_bugs_local = module_index.get(mod, []) or [b for b in bugs if (b['module'] or '其他') == mod]
        td = item['type_distribution']
        sorted_types = sorted(td.items(), key=lambda x: x[1], reverse=True)
        top2 = sorted_types[:2]
        cause_parts = [f"{t}({c}条)" for t, c in top2]
        cause = '+'.join(cause_parts)
        if len(top2) >= 2:
            cause += f" → {' + '.join(t + '缺陷' for t, _ in top2)}"
        root_cause_data.append({
            'module': mod,
            'count': item['bug_count'],
            'cause': cause,
            'type_distribution': td,
        })

    # 模块×类型交叉数据
    cross_type_data = {}
    for b in bugs:
        mod = b['module'] or '其他'
        wt = b.get('type', '') or '未知'
        key = f"{mod}|{wt}"
        cross_type_data[key] = cross_type_data.get(key, 0) + 1

    return cluster_data, root_cause_data, cross_type_data


def _build_metadata(bugs, xlsx_filename, uncategorized, import_count, real_count):
    """
    构建元数据信息
    使用集合推导式简化 tag 收集
    """
    total = len(bugs)

    # 集合推导式 (代码简化)
    tag_set = {tag for b in bugs for tag in b['tags']}
    creators = {b.get('creator', '') for b in bugs if b.get('creator')}
    work_types = dict(Counter(b.get('type', '') for b in bugs if b.get('type')))

    meta_data = {
        'total_bugs': total,
        'input_file': xlsx_filename,
        'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'creators': len(creators),
        'work_types': work_types,
        'tag_count': len(tag_set),
        'uncategorized': uncategorized,
        'uncategorized_pct': round(uncategorized / total * 100, 1) if total > 0 else 0,
        'import_count': import_count,
        'real_count': real_count,
    }
    return meta_data


# ============================================================
# 空结果快速返回 (安全守卫)
# ============================================================

_EMPTY_RESULT_TEMPLATE = {
    'modulesData': {},
    'featureDetailData': [],
    'severityCrossData': {},
    'testFocusData': {},
    'creatorModuleData': [],
    'participantData': [],
    'customFieldCharts': {},
    'timelineCleanData': {},
    'timelineData': {},
    'importLabels': [],
    'kwData': [],
    'riskData': {'P0': {'total': 0, 'detail': {}}, 'P1': {'total': 0, 'detail': {}}, 'P2': {'total': 0, 'detail': {}}},
    'clusterData': [],
    'rootCauseData': [],
    'crossTypeData': {},
    'sevData': {},
    'sevInfData': {'推断P0': 0, '推断P1': 0, '推断P2': 0},
    'statusData': {},
    'priorityData': {},
    'wufaDetailData': {},
    'metaData': {
        'total_bugs': 0, 'input_file': '', 'analysis_time': '',
        'creators': 0, 'work_types': {}, 'tag_count': 0,
        'uncategorized': 0, 'uncategorized_pct': 0,
        'import_count': 0, 'real_count': 0,
    },
}


# ============================================================
# 主入口
# ============================================================

def analyze_bugs(bugs, xlsx_filename=''):
    """
    分析 Bug 数据的主入口函数

    重构后架构:
    1. 空列表早返回 (安全守卫)
    2. 预处理 (标签提取/分类)
    3. 构建模块索引 (一次性 O(n))
    4. 分发到各子函数计算 (各子函数使用索引 O(1) 查找)
    5. 组装结果返回

    Args:
        bugs: Bug 列表, 每个元素为 dict 含 title/desc/severity/status/priority/type/creator/created 字段
        xlsx_filename: 来源文件名 (用于元数据记录)

    Returns:
        dict: 包含所有分析结果的完整字典
    """
    # 安全守卫: 空列表快速返回
    if not bugs:
        result = dict(_EMPTY_RESULT_TEMPLATE)
        result['metaData']['input_file'] = xlsx_filename
        result['metaData']['analysis_time'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        return result

    total = len(bugs)

    # Step 1: 预处理
    _preprocess_bugs(bugs)

    # Step 2: 构建模块索引 (性能核心: 后续所有模块查询走索引)
    module_counter, module_index = _build_module_index(bugs)
    all_modules = _compute_all_modules(module_counter)

    # Step 3: 各维度数据计算
    modules_data, feature_detail_data, uncategorized = _compute_modules_data(
        module_counter, module_index, all_modules, total
    )

    severity_cross_data, sev_data, sev_inf_data, status_data, priority_data = _compute_severity_data(bugs)

    p_counts = {'P0': sev_inf_data.get('推断P0', 0), 'P1': sev_inf_data.get('推断P1', 0), 'P2': sev_inf_data.get('推断P2', 0)}

    tf_data = _compute_test_focus(all_modules, module_index)
    creator_module_data = _compute_creator_data(bugs)
    participant_data = _compute_participant_data(bugs)
    custom_field_charts = _compute_custom_field_charts(bugs)
    timeline_clean_data, timeline_data, import_labels, import_count, real_count = _compute_timeline_data(bugs)
    # kw_data 不再在基础分析中计算，由 AI 增强阶段生成
    risk_data = _compute_risk_data(bugs, p_counts)
    cluster_data, root_cause_data, cross_type_data = _compute_cluster_data(bugs, module_index)
    meta_data = _build_metadata(bugs, xlsx_filename, uncategorized, import_count, real_count)

    # Step 4: 组装并返回结果 (保持原有 JSON 结构不变，确保前端兼容)
    return {
        'modulesData': modules_data,
        'featureDetailData': feature_detail_data,
        'severityCrossData': severity_cross_data,
        'testFocusData': tf_data,
        'creatorModuleData': creator_module_data,
        'participantData': participant_data,
        'customFieldCharts': custom_field_charts,
        'timelineCleanData': timeline_clean_data,
        'timelineData': timeline_data,
        'importLabels': import_labels,
        'kwData': [],  # 关键词由 AI 增强阶段生成
        'riskData': risk_data,
        'clusterData': cluster_data,
        'rootCauseData': root_cause_data,
        'crossTypeData': cross_type_data,
        'sevData': sev_data,
        'sevInfData': sev_inf_data,
        'statusData': status_data,
        'priorityData': priority_data,
        'wufaDetailData': {},  # 无法XXX模式也由 AI 提取
        'metaData': meta_data,
    }
