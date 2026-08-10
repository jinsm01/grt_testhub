# -*- coding: utf-8 -*-
"""
Bug 分析 API 视图 V2

重构要点:
1. 安全修复: 裸 except → 精确异常; 文件名校验
2. 代码去重: 公共日期解析/校验/响应格式函数
3. 日志增强: 记录文件名/bug数量/处理耗时/AI调用信息
4. 新增 API: 分析记录 CRUD + 模块详情 + 跨版本对比 + 回归导出
5. AI 增强: 可选开启 Mock/Qwen AI 增强分析

数据解析已迁移到 bug_source_adapter.py，本模块仅保留视图层逻辑。
"""

import os
import time
import json
import asyncio
import tempfile
import logging
from datetime import datetime
from functools import wraps

from asgiref.sync import async_to_sync
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.db.models import Q
from django.utils.timezone import localtime
from django.utils import timezone
import openpyxl

from .bug_analysis import analyze_bugs
from .bug_source_adapter import BugSourceAdapter, _sanitize_filename, load_bugs_from_source

logger = logging.getLogger(__name__)

try:
    from .models import BugAnalysisRecord, BugAnalysisSummaryRecord
    _DB_RECORDS_AVAILABLE = True
except Exception:
    # 模型表尚未迁移时优雅降级，页面仍可正常使用分析功能
    BugAnalysisRecord = None
    BugAnalysisSummaryRecord = None
    _DB_RECORDS_AVAILABLE = False
    logger.warning("[BugAnalysis] BugAnalysisRecord 表不存在(未执行migrate)，历史记录功能暂时禁用")

# ============================================================
# 配置常量
# ============================================================

ALLOWED_EXTENSIONS = {'.xlsx', '.xls'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


# ============================================================
# 公共工具函数（代码去重）
# ============================================================

def _parse_date_value(value):
    """
    解析日期值 (公共函数，替代原来两处重复的日期解析)
    支持类型: datetime / str / float(Excel序列号) / None
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        try:
            from openpyxl.utils.datetime import from_excel
            return from_excel(float(value), epoch_mode='1900')
        except (ValueError, TypeError, OverflowError):
            return None
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
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
        return None
    return None


def _serialize_for_json(obj):
    """
    将对象序列化为JSON可序列化的格式
    处理 datetime/date 等特殊类型
    """
    if isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_serialize_for_json(item) for item in obj]
    elif isinstance(obj, datetime):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(obj, type(datetime.now().date())):  # date类型
        return obj.strftime('%Y-%m-%d')
    else:
        return obj


import re

def _clean_bug_description(desc):
    """
    清理Bug描述中的markdown图片/附件链接
    
    移除 ![alt](url) 格式的markdown图片语法，以及纯URL括号行。
    图片和附件已通过单独的附件字段管理，不需要在纯文本描述中保留链接。
    """
    if not desc:
        return ''
    # 移除markdown图片语法 ![...](url)
    cleaned = re.sub(r'!\[.*?\]\(https?://[^\s)]+\)', '', desc)
    # 移除单独的云效附件URL行：(https://...)
    cleaned = re.sub(r'^\s*\(https?://[^\s)]+\)\s*$', '', cleaned, flags=re.MULTILINE)
    # 清理多余空行（3个以上换行变成2个）
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


def _validate_bug_data(bugs):
    """
    校验输入 Bug 数据的基本完整性

    Args:
        bugs: list[dict] 待校验的Bug列表

    Returns:
        tuple: (is_valid, error_message or None)
    """
    if bugs is None:
        return False, "请提供有效的 Bug 数据 (None)"
    if not isinstance(bugs, list):
        return False, f"期望列表类型的 Bug 数据，收到 {type(bugs).__name__}"
    if len(bugs) == 0:
        return False, "Bug 列表为空"

    # 统计缺少标题的比例
    missing_title = sum(1 for b in bugs if not str(b.get('title', '')).strip())
    if missing_title > len(bugs) * 0.5:
        return False, f"超过50%的记录缺少标题字段 ({missing_title}/{len(bugs)})"

    return True, None


def _get_bug_analyzer_config_id():
    """
    自动获取 Bug 分析专家的 AI 配置 ID

    Returns:
        int or None: 配置 ID，如果没有找到则返回 None
    """
    try:
        from apps.requirement_analysis.models import AIModelConfig
        config = AIModelConfig.objects.filter(
            role='bug_analyzer',
            is_active=True
        ).order_by('-updated_at').first()

        if config:
            logger.info(f"[BugAnalysis] 自动获取 Bug 分析配置: ID={config.id}, 名称={config.name}")
            return config.id
        else:
            logger.warning("[BugAnalysis] 未找到活跃的 Bug 分析专家配置")
            return None
    except Exception as e:
        logger.error(f"[BugAnalysis] 获取 Bug 分析配置失败: {e}")
        return None


def _build_api_response(data, message='', success=True, code=status.HTTP_200_OK):
    """
    构建统一的 API 响应格式
    """
    response_data = dict(data) if data else {}
    response_data['success'] = success
    if message:
        response_data['message'] = message
    return Response(response_data, status=code)


def _build_error_response(message, code=status.HTTP_400_BAD_REQUEST, log_level='warning'):
    """
    构建统一的错误响应
    """
    getattr(logger, log_level)(f'API错误 [{code}]: {message}')
    return Response({'success': False, 'error': message}, status=code)


# ============================================================
# 核心分析流程（封装为可复用函数）
# ============================================================

async def _run_enhanced_analysis(bugs, filename='', save_record=True,
                                  ai_provider_name='qwen', ai_config_id=None,
                                  version_tag='', source_type='excel',
                                  skip_ai=False, ai_status='none', created_by='system'):
    """
    运行增强版 Bug 分析流程

    流程:
    1. 规则引擎分析 (analyze_bugs)
    2. [可选] AI 增强分析
    3. [可选] 保存分析记录到数据库

    Args:
        bugs: 标准 Bug 列表
        filename: 来源文件名
        save_record: 是否保存记录
        ai_provider_name: AI 提供者名称 ('mock' 或 'qwen')
        ai_config_id: AIModelConfig ID (qwen模式需要)
        version_tag: 版本标签 (用于历史管理)
        source_type: 数据来源类型 (默认 'excel')
        skip_ai: 是否跳过AI分析（用于异步模式，先保存基础分析，后台再执行AI）
        ai_status: 保存记录时的AI状态
        created_by: 创建者用户名 (默认 'system')

    Returns:
        dict: 完整的分析结果
    """
    start_time = time.time()

    # 如果未指定 config_id 且使用 qwen，自动获取 Bug 分析配置 (使用 sync_to_async 包装 Django ORM)
    if ai_provider_name == 'qwen' and ai_config_id is None:
        from asgiref.sync import sync_to_async
        ai_config_id = await sync_to_async(_get_bug_analyzer_config_id)()

    # Step 1: 规则引擎核心分析
    logger.info(f"[BugAnalysis] 开始分析: 文件={filename}, Bug数={len(bugs)}, AI={ai_provider_name}, config_id={ai_config_id}, skip_ai={skip_ai}")
    analysis_result = analyze_bugs(list(bugs), filename)  # copy 避免副作用

    # Step 2: AI 增强 (异步调用 - 并发优化)
    ai_stats = {'calls': 0, 'errors': 0}
    if not skip_ai and ai_provider_name and ai_provider_name != 'none':
        try:
            from .bug_analysis_ai import get_ai_provider, MockFallbackException, MockBugAnalysisAI
            
            ai = get_ai_provider(provider_name=ai_provider_name, config_id=ai_config_id)
            use_mock = False

            modules = analysis_result.get('modulesData', {})
            test_focus = analysis_result.get('testFocusData', {})
            top_modules = list(modules.keys())[:10]

            enhanced_focus = {}
            root_cause_list = []

            # 并发执行：所有测试建议调用同时进行
            async def fetch_test_focus(mod):
                try:
                    mod_stats = test_focus.get(mod, {})
                    return mod, await ai.generate_test_focus(mod, mod_stats), None
                except MockFallbackException:
                    return mod, None, MockFallbackException("Mock fallback needed")
                except Exception as e:
                    return mod, None, e

            focus_tasks = [fetch_test_focus(mod) for mod in top_modules]
            focus_results = await asyncio.gather(*focus_tasks)

            for mod, focus_text, error in focus_results:
                if isinstance(error, MockFallbackException):
                    use_mock = True
                    break
                elif error:
                    logger.warning(f"AI测试建议[{mod}]失败: {error}")
                    ai_stats['errors'] += 1
                else:
                    enhanced_focus[mod] = focus_text
                    ai_stats['calls'] += 1

            # 如果检测到 Mock 回退信号，切换到 Mock 实现
            if use_mock:
                logger.warning("检测到 AI 配置不可用，切换到 Mock AI 实现")
                ai = MockBugAnalysisAI()
                # 重新执行测试建议
                enhanced_focus = {}
                for mod in top_modules:
                    try:
                        mod_stats = test_focus.get(mod, {})
                        enhanced_focus[mod] = await ai.generate_test_focus(mod, mod_stats)
                        ai_stats['calls'] += 1
                    except Exception as e:
                        logger.warning(f"Mock AI测试建议[{mod}]失败: {e}")
                        ai_stats['errors'] += 1

            # 并发执行：Top5 模块的根因分析同时进行
            top5_modules = top_modules[:5]

            async def fetch_root_cause(mod):
                try:
                    mod_bugs = [b for b in bugs if b.get('module') == mod]
                    cause_text = await ai.generate_root_cause(mod, mod_bugs)
                    return mod, cause_text, None
                except Exception as e:
                    return mod, None, e

            cause_tasks = [fetch_root_cause(mod) for mod in top5_modules]
            cause_results = await asyncio.gather(*cause_tasks)

            for mod, cause_text, error in cause_results:
                if error:
                    logger.warning(f"AI根因分析[{mod}]失败: {error}")
                    ai_stats['errors'] += 1
                else:
                    root_cause_list.append({'module': mod, 'cause': cause_text})
                    ai_stats['calls'] += 1

            # 全局总结
            try:
                summary = await ai.generate_summary(analysis_result)
                analysis_result['aiSummary'] = summary
                ai_stats['calls'] += 1
            except Exception as e:
                logger.warning(f"AI总结生成失败: {e}")
                ai_stats['errors'] += 1

            # AI 关键词提取
            try:
                ai_keywords = await ai.extract_keywords(bugs)
                analysis_result['aiKeywords'] = ai_keywords
                ai_stats['calls'] += 1
                logger.info(f"AI关键词提取完成: {len(ai_keywords)}个关键词")
            except Exception as e:
                logger.warning(f"AI关键词提取失败: {e}")
                ai_stats['errors'] += 1

            # AI 风险分析
            try:
                ai_risks = await ai.analyze_risks(bugs, analysis_result)
                analysis_result['aiRisks'] = ai_risks
                ai_stats['calls'] += 1
                logger.info(f"AI风险分析完成: P0={len(ai_risks.get('P0', []))}类, P1={len(ai_risks.get('P1', []))}类, P2={len(ai_risks.get('P2', []))}类")
            except Exception as e:
                logger.warning(f"AI风险分析失败: {e}")
                ai_stats['errors'] += 1

            if enhanced_focus:
                analysis_result['aiTestFocus'] = enhanced_focus
            if root_cause_list:
                analysis_result['aiRootCause'] = root_cause_list

        except ImportError:
            logger.warning("AI增强模块不可用，跳过AI分析")
        except Exception as e:
            logger.error(f"AI增强分析失败: {e}", exc_info=True)

    elapsed = round((time.time() - start_time) * 1000)
    logger.info(f"[BugAnalysis] 分析完成: {len(bugs)}条Bug, 耗时{elapsed}ms, "
                f"AI调用={ai_stats['calls']}次, 失败={ai_stats['errors']}次")

    # 如果 AI 分析成功完成，更新状态为 completed
    final_ai_status = ai_status
    if not skip_ai and ai_provider_name and ai_provider_name != 'none':
        if ai_stats['calls'] > 0 and ai_stats['errors'] == 0:
            final_ai_status = 'completed'
        elif ai_stats['calls'] > 0:
            final_ai_status = 'completed'  # 部分成功也算完成

    # Step 3: 保存记录 (使用 sync_to_async 包装 Django ORM 操作)
    record = None
    if save_record and _DB_RECORDS_AVAILABLE:
        try:
            # 序列化 raw_bugs 以处理 datetime 等特殊类型
            serialized_bugs = [_serialize_for_json(dict(b)) for b in bugs]
            
            # 定义同步保存函数
            def _save_record_sync():
                return BugAnalysisRecord.objects.create(
                    version_tag=version_tag,
                    source_type=source_type,
                    file_name=_sanitize_filename(filename),
                    total_bugs=len(bugs),
                    raw_bugs=serialized_bugs,
                    analysis_result=analysis_result,
                    ai_status=final_ai_status,
                    ai_progress=100 if final_ai_status == 'completed' else 0,
                    created_by=created_by,
                )
            
            # 在异步上下文中调用同步函数
            from asgiref.sync import sync_to_async
            record = await sync_to_async(_save_record_sync)()
            analysis_result['record_id'] = record.id
            logger.info(f"[BugAnalysis] 记录已保存: id={record.id}, ai_status={ai_status}")
        except Exception as e:
            logger.error(f"[BugAnalysis] 保存分析记录失败: {e}", exc_info=True)

    # 返回原始Bug数据(前100条)，用于前端状态筛选
    analysis_result['raw_bugs'] = [_serialize_for_json(dict(b)) for b in bugs[:100]]
    return analysis_result


def _run_ai_analysis_background(record_id, bugs, analysis_result, ai_provider_name, ai_config_id):
    """
    后台执行 AI 分析（在线程中运行）

    注意：Django ORM 操作在线程中可直接使用（同步环境），
    AI 方法为 async，使用 asyncio.run() 在新事件循环中执行
    """
    import asyncio
    import atexit
    logger.info(f"[AI Background] 启动后台AI分析: record_id={record_id}, provider={ai_provider_name}")

    from asgiref.sync import sync_to_async

    # 注册进程退出清理：如果进程被重启/kill，自动标记为失败
    _cleanup_registered = True
    def _cleanup_on_exit():
        if _cleanup_registered:
            try:
                BugAnalysisRecord.objects.filter(id=record_id, ai_status='running').update(
                    ai_status='failed', ai_progress=0
                )
                logger.warning(f"[AI Background] 进程退出，AI分析标记为失败: record_id={record_id}")
            except Exception:
                pass
    atexit.register(_cleanup_on_exit)

    async def _update_status(status, progress=0):
        try:
            await sync_to_async(BugAnalysisRecord.objects.filter(id=record_id).update)(
                ai_status=status, ai_progress=progress
            )
        except Exception as e:
            logger.error(f"[AI Background] 更新状态失败: {e}")

    async def _do_ai_analysis():
        from .bug_analysis_ai import get_ai_provider
        ai = get_ai_provider(provider_name=ai_provider_name, config_id=ai_config_id)

        modules = analysis_result.get('modulesData', {})
        test_focus = analysis_result.get('testFocusData', {})
        top_modules = list(modules.keys())[:10]
        top5_modules = top_modules[:5]

        enhanced_focus = {}
        root_cause_list = []
        ai_stats = {'calls': 0, 'errors': 0}

        # 测试建议（并发执行）
        async def fetch_focus(mod):
            try:
                mod_stats = test_focus.get(mod, {})
                return mod, await ai.generate_test_focus(mod, mod_stats), None
            except Exception as e:
                return mod, None, e

        focus_tasks = [fetch_focus(mod) for mod in top_modules]
        focus_results = await asyncio.gather(*focus_tasks)
        for mod, text, err in focus_results:
            if err:
                logger.warning(f"[AI Background] 测试建议[{mod}]失败: {err}")
                ai_stats['errors'] += 1
            else:
                enhanced_focus[mod] = text
                ai_stats['calls'] += 1
        await _update_status('running', 35)

        # 根因分析（并发执行）
        async def fetch_cause(mod):
            try:
                mod_bugs = [b for b in bugs if b.get('module') == mod]
                return mod, await ai.generate_root_cause(mod, mod_bugs), None
            except Exception as e:
                return mod, None, e

        cause_tasks = [fetch_cause(mod) for mod in top5_modules]
        cause_results = await asyncio.gather(*cause_tasks)
        for mod, text, err in cause_results:
            if err:
                logger.warning(f"[AI Background] 根因分析[{mod}]失败: {err}")
                ai_stats['errors'] += 1
            else:
                root_cause_list.append({'module': mod, 'cause': text})
                ai_stats['calls'] += 1
        await _update_status('running', 55)

        # 全局总结
        try:
            summary = await ai.generate_summary(analysis_result)
            analysis_result['aiSummary'] = summary
            ai_stats['calls'] += 1
        except Exception as e:
            logger.warning(f"[AI Background] 总结生成失败: {e}")
            ai_stats['errors'] += 1
        await _update_status('running', 70)

        # 关键词提取
        try:
            ai_keywords = await ai.extract_keywords(bugs)
            analysis_result['aiKeywords'] = ai_keywords
            ai_stats['calls'] += 1
            logger.info(f"[AI Background] 关键词提取完成: {len(ai_keywords)}个关键词")
        except Exception as e:
            logger.warning(f"[AI Background] 关键词提取失败: {e}")
            ai_stats['errors'] += 1
        await _update_status('running', 85)

        # 风险分析
        try:
            ai_risks = await ai.analyze_risks(bugs, analysis_result)
            analysis_result['aiRisks'] = ai_risks
            ai_stats['calls'] += 1
            logger.info(f"[AI Background] 风险分析完成")
        except Exception as e:
            logger.warning(f"[AI Background] 风险分析失败: {e}")
            ai_stats['errors'] += 1
        await _update_status('running', 95)

        # 合并结果
        if enhanced_focus:
            analysis_result['aiTestFocus'] = enhanced_focus
        if root_cause_list:
            analysis_result['aiRootCause'] = root_cause_list

        # 保存到数据库
        await sync_to_async(BugAnalysisRecord.objects.filter(id=record_id).update)(
            analysis_result=analysis_result,
            ai_status='completed',
            ai_progress=100
        )
        logger.info(f"[AI Background] AI分析完成: record_id={record_id}, AI调用={ai_stats['calls']}次")

    try:
        asyncio.run(_do_ai_analysis())
    except Exception as e:
        logger.error(f"[AI Background] AI分析异常: {e}", exc_info=True)
        # 同步更新失败状态（异常处理不在 async 中）
        try:
            BugAnalysisRecord.objects.filter(id=record_id).update(ai_status='failed', ai_progress=0)
        except Exception as e2:
            logger.error(f"[AI Background] 更新失败状态也失败: {e2}")
    finally:
        # 正常完成或异常后，禁用清理函数，避免误标记
        _cleanup_registered = False


# 全局 request 引擎（用于 _run_enhanced_analysis 内部访问）
request = None


def _recover_ai_analysis(record_id):
    """
    恢复被中断的 AI 分析任务（进程启动时调用）
    """
    import threading
    try:
        record = BugAnalysisRecord.objects.filter(id=record_id).first()
        if not record:
            logger.warning(f"[AI Recovery] 记录不存在: record_id={record_id}")
            return
        if record.ai_status != 'running':
            logger.info(f"[AI Recovery] 记录状态不是running，无需恢复: record_id={record_id}, status={record.ai_status}")
            return

        bugs = record.raw_bugs or []
        analysis_result = record.analysis_result or {}
        ai_provider = analysis_result.get('ai_provider', 'qwen')
        ai_config_id = analysis_result.get('ai_config_id')

        logger.info(f"[AI Recovery] 恢复AI分析任务: record_id={record_id}, bugs={len(bugs)}, provider={ai_provider}")

        # 启动后台线程重新执行AI分析
        t = threading.Thread(
            target=_run_ai_analysis_background,
            args=(record_id, bugs, analysis_result, ai_provider, ai_config_id),
            daemon=True
        )
        t.start()
    except Exception as e:
        logger.error(f"[AI Recovery] 恢复AI分析失败: record_id={record_id}, error={e}")


# ============================================================
# API 端点：原有接口（保持向后兼容）
# ============================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_bug_excel(request):
    """
    上传并分析 Bug Excel 文件 (V2 增强 - 渐进式加载)

    POST参数:
        - file: Excel文件 (.xlsx/.xls)
        - save: 是否保存记录 (默认 true)
        - ai_provider: AI提供者 ('mock'|'qwen'|'none', 默认 'mock')
        - version_tag: 版本标签 (可选，用于历史管理)
        - ai_config_id: AI模型配置ID (可选)
        - skip_ai: 是否跳过AI分析直接返回基础结果 (默认 false, 用于渐进式加载)

    返回:
        - 基础分析结果 (立即返回，约2-3秒)
        - 如需AI增强，请调用 /enhance-ai/ 接口
    """
    start_time = time.time()

    try:
        # === 输入校验 ===
        if 'file' not in request.FILES:
            return _build_error_response('请上传Excel文件')

        uploaded_file = request.FILES['file']
        original_filename = uploaded_file.name or ''

        # 文件名校验 (安全修复: 防止路径穿越)
        safe_filename = _sanitize_filename(original_filename)
        if not safe_filename.endswith(tuple(ALLOWED_EXTENSIONS)):
            ext = os.path.splitext(safe_filename)[1].lower()
            return _build_error_response(
                f'不支持的文件类型: {ext or "无扩展名"}，请上传 .xlsx 或 .xls 文件'
            )

        # 大小校验
        if uploaded_file.size > MAX_FILE_SIZE:
            return _build_error_response(
                f'文件大小 ({uploaded_file.size / 1024 / 1024:.1f}MB) 超过10MB限制'
            )

        # 参数提取
        save_record = request.data.get('save', 'true').lower() in ('true', '1', 'yes')
        ai_provider = request.data.get('ai_provider', 'qwen').lower()
        version_tag = request.data.get('version_tag', '')
        ai_config_id_str = request.data.get('ai_config_id') or ''
        ai_config_id = int(ai_config_id_str) if ai_config_id_str and ai_config_id_str.isdigit() else None
        
        # 调试: 打印所有收到的参数
        logger.info(f"[API:analyze_bug_excel] 收到参数: {dict(request.data)}")
        
        skip_ai_raw = request.data.get('skip_ai', 'false')
        skip_ai = str(skip_ai_raw).lower() in ('true', '1', 'yes')
        
        logger.info(f"[API:analyze_bug_excel] skip_ai_raw={skip_ai_raw}, skip_ai={skip_ai}")

        # 渐进式加载: 如果启用AI分析,强制保存记录(后续AI增强需要record_id)
        if not skip_ai and ai_provider != 'none':
            save_record = True
            logger.info(f"[API:analyze_bug_excel] 启用AI分析,强制保存记录")

        logger.info(f"[API:analyze_bug_excel] 文件={safe_filename}, "
                     f"大小={uploaded_file.size}, save={save_record}, skip_ai={skip_ai}")

        # === 临时文件处理 ===
        file_ext = os.path.splitext(safe_filename)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            for chunk in uploaded_file.chunks():
                tmp_file.write(chunk)
            tmp_path = tmp_file.name

        try:
            # 使用新的适配器解析 Excel
            bugs = BugSourceAdapter.from_excel(tmp_path)

            # 数据校验
            is_valid, err_msg = _validate_bug_data(bugs)
            if not is_valid:
                return _build_error_response(err_msg)

            logger.info(f"[API:analyze_bug_excel] 解析完成: {len(bugs)} 条有效Bug")

            # === 执行基础分析 (快速返回) ===
            analysis_result = analyze_bugs(bugs, safe_filename)

            # === 保存记录 ===
            record_id = None
            if save_record and _DB_RECORDS_AVAILABLE:
                try:
                    # 序列化 raw_bugs 以处理 datetime 等特殊类型
                    serialized_bugs = [_serialize_for_json(dict(b)) for b in bugs]
                    record = BugAnalysisRecord.objects.create(
                        version_tag=version_tag,
                        source_type='excel',
                        file_name=safe_filename,
                        total_bugs=len(bugs),
                        raw_bugs=serialized_bugs,
                        analysis_result=analysis_result,
                        created_by=request.user.username if request.user.is_authenticated else 'system'
                    )
                    record_id = record.id
                    analysis_result['record_id'] = record.id
                    logger.info(f"[API:analyze_bug_excel] 记录已保存: id={record_id}")
                except Exception as e:
                    logger.error(f"保存分析记录失败: {e}")
                    # 如果启用AI但保存失败,标记AI为不可用
                    if not skip_ai and ai_provider != 'none':
                        analysis_result['ai_pending'] = False
                        analysis_result['ai_error'] = '保存记录失败,无法启用AI分析'
            elif save_record and not _DB_RECORDS_AVAILABLE:
                logger.warning("[API:analyze_bug_excel] 数据库模型不可用,无法保存记录")
                if not skip_ai and ai_provider != 'none':
                    analysis_result['ai_pending'] = False
                    analysis_result['ai_error'] = '数据库模型不可用,请执行迁移: python manage.py migrate'

            # 标记AI分析状态 (只在未设置时设置，避免覆盖保存失败时的错误标记)
            if 'ai_pending' not in analysis_result:
                analysis_result['ai_pending'] = not skip_ai and ai_provider != 'none'
            if 'ai_provider' not in analysis_result:
                analysis_result['ai_provider'] = ai_provider if not skip_ai else None
            if 'ai_config_id' not in analysis_result:
                analysis_result['ai_config_id'] = ai_config_id

            # === 响应 ===
            elapsed = round((time.time() - start_time) * 1000)
            analysis_result['success'] = True
            analysis_result['message'] = f'成功分析 {len(bugs)} 条Bug数据 (基础分析耗时{elapsed}ms)'
            # 确保record_id在响应中
            if 'record_id' not in analysis_result:
                analysis_result['record_id'] = record_id
            # 返回原始Bug数据(前100条)，用于前端状态筛选
            analysis_result['raw_bugs'] = [_serialize_for_json(dict(b)) for b in bugs[:100]]
            logger.info(f"[API:analyze_bug_excel] 成功: {len(bugs)}条, {elapsed}ms, record_id={record_id}, ai_pending={analysis_result.get('ai_pending')}")

            return _build_api_response(analysis_result, analysis_result['message'])

        finally:
            try:
                os.unlink(tmp_path)
            except OSError as e:
                logger.debug(f'清理临时文件失败: {e}')

    except ValueError as ve:
        # 数据格式/内容相关的错误
        logger.warning(f'[API:analyze_bug_excel] 数据验证错误: {ve}')
        return _build_error_response(str(ve))
    except openpyxl.utils.exceptions.InvalidFileException:
        return _build_error_response('无效的Excel文件，请检查文件是否损坏或格式是否正确')
    except FileNotFoundError as fe:
        return _build_error_response(str(fe))
    except Exception as e:
        logger.error(f'[API:analyze_bug_excel] 未预期错误: {e}', exc_info=True)
        return _build_error_response(f'分析失败: {str(e)}', code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                     log_level='error')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_bug_data(request):
    """
    直接分析传入的 Bug 数据 (V2 增强)

    POST参数:
        - bugs: Bug数据列表 (JSON array)
        - filename: 文件名 (可选)
        - save: 是否保存记录 (默认 false)
        - ai_provider: AI提供者 ('mock'|'qwen'|'none', 默认 'none')
        - version_tag: 版本标签 (可选)
        - ai_config_id: AI模型配置ID (可选)

    返回:
        - 完整分析结果
    """
    start_time = time.time()

    try:
        raw_bugs = request.data.get('bugs', [])
        filename = request.data.get('filename', 'unknown')
        save_record = request.data.get('save', 'false').lower() in ('true', '1', 'yes')
        ai_provider = request.data.get('ai_provider', 'qwen').lower()
        version_tag = request.data.get('version_tag', '')
        ai_config_id_str = request.data.get('ai_config_id') or ''
        ai_config_id = int(ai_config_id_str) if ai_config_id_str and ai_config_id_str.isdigit() else None

        # 如果未指定 config_id，自动获取 Bug 分析配置
        if ai_config_id is None:
            ai_config_id = _get_bug_analyzer_config_id()

        # 输入校验
        is_valid, err_msg = _validate_bug_data(raw_bugs)
        if not is_valid:
            return _build_error_response(err_msg)

        # 使用适配器标准化数据
        bugs = BugSourceAdapter.from_json_data(raw_bugs)

        logger.info(f"[API:analyze_bug_data] 开始分析: {len(bugs)}条Bug, ai_provider={ai_provider}")

        # 使用新的统一流程执行分析
        analysis_result = async_to_sync(_run_enhanced_analysis)(
            bugs,
            filename=filename,
            save_record=save_record,
            ai_provider_name=ai_provider,
            ai_config_id=ai_config_id,
            version_tag=version_tag,
            created_by=request.user.username if request.user.is_authenticated else 'system',
        )

        # === 响应 ===
        elapsed = round((time.time() - start_time) * 1000)
        analysis_result['success'] = True
        analysis_result['message'] = f'成功分析 {len(bugs)} 条Bug数据 (耗时{elapsed}ms)'
        logger.info(f"[API:analyze_bug_data] 成功: {len(bugs)}条, {elapsed}ms")

        return _build_api_response(analysis_result, analysis_result['message'])

    except ValueError as ve:
        logger.warning(f'[API:analyze_bug_data] 数据验证错误: {ve}')
        return _build_error_response(str(ve))
    except Exception as e:
        logger.error(f'[API:analyze_bug_data] 未预期错误: {e}', exc_info=True)
        return _build_error_response(f'分析失败: {str(e)}', code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                     log_level='error')


# ============================================================
# API 端点：AI 增强分析 (渐进式加载)
# ============================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enhance_with_ai(request):
    """
    为已存在的分析记录添加 AI 增强分析 (渐进式加载)

    POST参数:
        - record_id: 分析记录ID (必填)
        - ai_provider: AI提供者 ('mock'|'qwen', 默认 'qwen')
        - ai_config_id: AI模型配置ID (可选)

    返回:
        - aiSummary: AI 智能摘要
        - aiTestFocus: 各模块测试建议 {module: text}
        - aiRootCause: 根因分析列表 [{module, cause}, ...]
        - progress: 完成进度信息
    """
    start_time = time.time()

    try:
        # 参数提取
        record_id = request.data.get('record_id')
        if not record_id:
            return _build_error_response('请提供 record_id 参数')

        ai_provider = request.data.get('ai_provider', 'qwen').lower()
        ai_config_id_str = request.data.get('ai_config_id') or ''
        ai_config_id = int(ai_config_id_str) if ai_config_id_str and ai_config_id_str.isdigit() else None

        # 如果未指定 config_id，自动获取
        if ai_config_id is None:
            ai_config_id = _get_bug_analyzer_config_id()

        logger.info(f"[API:enhance_with_ai] record_id={record_id}, ai_provider={ai_provider}, config_id={ai_config_id}")

        # 获取记录
        if not _DB_RECORDS_AVAILABLE:
            return _build_error_response('历史记录功能暂不可用', code=status.HTTP_503_SERVICE_UNAVAILABLE)

        record = BugAnalysisRecord.objects.filter(id=record_id).first()
        if not record:
            return _build_error_response(f'记录不存在: id={record_id}', code=status.HTTP_404_NOT_FOUND)

        # 获取基础分析结果和原始Bug数据
        analysis_result = record.analysis_result or {}
        raw_bugs = record.raw_bugs or []

        if not raw_bugs:
            return _build_error_response('该记录没有原始Bug数据，无法进行AI增强')

        # 检查是否已有AI结果
        existing_ai = bool(
            analysis_result.get('aiSummary') or
            analysis_result.get('aiTestFocus') or
            analysis_result.get('aiRootCause')
        )
        if existing_ai:
            logger.info(f"[API:enhance_with_ai] 记录 {record_id} 已有AI结果，将重新生成")

        # 执行AI增强
        try:
            from .bug_analysis_ai import get_ai_provider, MockFallbackException, MockBugAnalysisAI
            ai = get_ai_provider(provider_name=ai_provider, config_id=ai_config_id)
            use_mock = False

            modules = analysis_result.get('modulesData', {})
            test_focus = analysis_result.get('testFocusData', {})
            top_modules = list(modules.keys())[:10]

            enhanced_focus = {}
            root_cause_list = []
            ai_stats = {'calls': 0, 'errors': 0}

            # 并发执行：所有测试建议调用同时进行
            async def fetch_test_focus(mod):
                try:
                    mod_stats = test_focus.get(mod, {})
                    return mod, await ai.generate_test_focus(mod, mod_stats), None
                except MockFallbackException:
                    return mod, None, MockFallbackException("Mock fallback needed")
                except Exception as e:
                    return mod, None, e

            # 使用 async_to_sync 在同步视图中运行异步代码
            async def run_focus_tasks():
                tasks = [fetch_test_focus(mod) for mod in top_modules]
                return await asyncio.gather(*tasks)
            
            focus_results = async_to_sync(run_focus_tasks)()

            for mod, focus_text, error in focus_results:
                if isinstance(error, MockFallbackException):
                    use_mock = True
                    break
                elif error:
                    logger.warning(f"AI测试建议[{mod}]失败: {error}")
                    ai_stats['errors'] += 1
                else:
                    enhanced_focus[mod] = focus_text
                    ai_stats['calls'] += 1

            # 如果检测到 Mock 回退信号，切换到 Mock 实现
            if use_mock:
                logger.warning("检测到 AI 配置不可用，切换到 Mock AI 实现")
                ai = MockBugAnalysisAI()
                # 重新执行测试建议
                enhanced_focus = {}
                for mod in top_modules:
                    try:
                        mod_stats = test_focus.get(mod, {})
                        enhanced_focus[mod] = async_to_sync(ai.generate_test_focus)(mod, mod_stats)
                        ai_stats['calls'] += 1
                    except Exception as e:
                        logger.warning(f"Mock AI测试建议[{mod}]失败: {e}")
                        ai_stats['errors'] += 1

            # 并发执行：Top5 模块的根因分析同时进行
            top5_modules = top_modules[:5]

            async def fetch_root_cause(mod):
                try:
                    mod_bugs = [b for b in raw_bugs if b.get('module') == mod]
                    cause_text = await ai.generate_root_cause(mod, mod_bugs)
                    return mod, cause_text, None
                except Exception as e:
                    return mod, None, e

            # 使用 async_to_sync 运行根因分析
            async def run_cause_tasks():
                tasks = [fetch_root_cause(mod) for mod in top5_modules]
                return await asyncio.gather(*tasks)
            
            cause_results = async_to_sync(run_cause_tasks)()

            for mod, cause_text, error in cause_results:
                if error:
                    logger.warning(f"AI根因分析[{mod}]失败: {error}")
                    ai_stats['errors'] += 1
                else:
                    root_cause_list.append({'module': mod, 'cause': cause_text})
                    ai_stats['calls'] += 1

            # AI 风险分析
            ai_risks = {}
            try:
                ai_risks = async_to_sync(ai.analyze_risks)(raw_bugs, analysis_result)
                ai_stats['calls'] += 1
                logger.info(f"AI风险分析完成: P0={len(ai_risks.get('P0', []))}类, P1={len(ai_risks.get('P1', []))}类, P2={len(ai_risks.get('P2', []))}类")
            except Exception as e:
                logger.warning(f"AI风险分析失败: {e}")
                ai_stats['errors'] += 1
                # 使用基础分析结果中的风险数据作为 fallback
                ai_risks = analysis_result.get('riskData', {})

            # 全局总结
            summary = ''
            try:
                summary = async_to_sync(ai.generate_summary)(analysis_result)
                ai_stats['calls'] += 1
            except Exception as e:
                logger.warning(f"AI总结生成失败: {e}")
                ai_stats['errors'] += 1

            # AI 关键词提取
            ai_keywords = []
            try:
                ai_keywords = async_to_sync(ai.extract_keywords)(raw_bugs)
                ai_stats['calls'] += 1
                logger.info(f"AI关键词提取完成: {len(ai_keywords)}个关键词")
            except Exception as e:
                logger.warning(f"AI关键词提取失败: {e}")
                ai_stats['errors'] += 1

            # 更新记录中的AI结果
            ai_result = {
                'aiSummary': summary,
                'aiTestFocus': enhanced_focus,
                'aiRootCause': root_cause_list,
                'aiRisks': ai_risks,
                'aiKeywords': ai_keywords,
            }

            # 保存到数据库
            record.analysis_result.update(ai_result)
            record.save(update_fields=['analysis_result'])

            elapsed = round((time.time() - start_time) * 1000)
            logger.info(f"[API:enhance_with_ai] 成功: record_id={record_id}, "
                        f"AI调用={ai_stats['calls']}次, 失败={ai_stats['errors']}次, 耗时={elapsed}ms")

            return _build_api_response({
                **ai_result,
                'record_id': record_id,
                'ai_calls': ai_stats['calls'],
                'ai_errors': ai_stats['errors'],
                'elapsed_ms': elapsed,
            }, f'AI增强分析完成 (耗时{elapsed}ms)')

        except ImportError:
            logger.warning("AI增强模块不可用")
            return _build_error_response('AI增强模块不可用，请检查依赖安装')
        except Exception as e:
            logger.error(f"AI增强分析失败: {e}", exc_info=True)
            return _build_error_response(f'AI增强分析失败: {str(e)}',
                                         code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')

    except Exception as e:
        logger.error(f'[API:enhance_with_ai] 未预期错误: {e}', exc_info=True)
        return _build_error_response(f'处理失败: {str(e)}',
                                     code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')


# ============================================================
# API 端点：分析记录 CRUD
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def bug_analysis_records(request):
    """
    获取Bug分析历史记录列表 (V2新增)

    GET参数:
        - page: 页码 (默认1)
        - page_size: 每页数量 (默认10, 最大50)
        - search: 搜索关键词 (匹配 version_tag 或 file_name)
        - sort: 排序字段 (-created_at | created_at, 默认 -created_at)
    """
    try:
        if not _DB_RECORDS_AVAILABLE:
            return Response({'data': {'items': [], 'total': 0}, 'message': '历史记录功能暂不可用(请执行数据库迁移)'})
        page = int(request.query_params.get('page', 1))
        page_size = min(int(request.query_params.get('page_size', 10)), 50)
        search = request.query_params.get('search', '').strip()
        sort = request.query_params.get('sort', '-created_at')

        queryset = BugAnalysisRecord.objects.all()

        # 搜索过滤
        if search:
            queryset = queryset.filter(
                Q(version_tag__icontains=search) |
                Q(file_name__icontains=search)
            )

        # 排序
        allowed_sorts = ['created_at', '-created_at', 'total_bugs', '-total_bugs']
        if sort not in allowed_sorts:
            sort = '-created_at'
        queryset = queryset.order_by(sort)

        # 分页
        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        records = queryset[start:end]

        items = []
        for r in records:
            # 计算高发模块：从 modulesData 中找到 Bug 数量最多的模块
            modules_data = (r.analysis_result or {}).get('modulesData', {})
            if modules_data:
                top_module = max(modules_data.items(), key=lambda x: x[1])[0]
            else:
                top_module = ''
            # 计算 display_name（去掉 _数字条 后缀）
            display_name = r.file_name
            if display_name:
                import re
                display_name = re.sub(r'_\d+条$', '', display_name)
            items.append({
                'id': r.id,
                'version_tag': r.version_tag,
                'source_type': r.source_type,
                'file_name': r.file_name,
                'display_name': display_name or r.file_name,
                'total_bugs': r.total_bugs,
                'ai_status': r.ai_status,
                'ai_progress': r.ai_progress,
                'meta_data': {
                    'total_bugs': (r.analysis_result or {}).get('metaData', {}).get('total_bugs', 0),
                    'p0_count': (r.analysis_result or {}).get('sevInfData', {}).get('推断P0', 0),
                    'p1_count': (r.analysis_result or {}).get('sevInfData', {}).get('推断P1', 0),
                    'top_module': top_module,
                },
                'created_at': localtime(r.created_at).strftime('%Y-%m-%d %H:%M:%S'),
                'created_by': r.created_by,
            })

        return Response({
            'success': True,
            'data': {
                'items': items,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size,
            }
        })

    except Exception as e:
        logger.error(f'[API:records] 错误: {e}', exc_info=True)
        return _build_error_response(f'获取记录列表失败: {str(e)}',
                                     code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def bug_analysis_record_detail(request, record_id):
    """获取单条分析记录详情"""
    try:
        if not _DB_RECORDS_AVAILABLE:
            return _build_error_response('历史记录功能暂不可用', code=status.HTTP_503_SERVICE_UNAVAILABLE)
        record = BugAnalysisRecord.objects.filter(id=record_id).first()
        if not record:
            return _build_error_response(f'记录不存在: id={record_id}', code=status.HTTP_404_NOT_FOUND)
        
        # 调试日志
        analysis_result = record.analysis_result or {}
        ai_module_focus = analysis_result.get('aiModuleFocus')
        logger.info(f"[API:record_detail] record_id={record_id}")
        logger.info(f"[API:record_detail] analysis_result keys: {list(analysis_result.keys())}")
        logger.info(f"[API:record_detail] aiModuleFocus: {ai_module_focus}")
        if ai_module_focus:
            logger.info(f"[API:record_detail] aiModuleFocus keys: {list(ai_module_focus.keys())}")

        return _build_api_response({
            'id': record.id,
            'version_tag': record.version_tag,
            'source_type': record.source_type,
            'file_name': record.file_name,
            'total_bugs': record.total_bugs,
            'raw_bugs': record.raw_bugs[:100] if record.raw_bugs else [],  # 最多返回前100条原始Bug
            'analysis_result': analysis_result,
            'ai_status': record.ai_status,
            'ai_progress': record.ai_progress,
            'created_at': localtime(record.created_at).strftime('%Y-%m-%d %H:%M:%S'),
            'created_by': record.created_by,
        })

    except Exception as e:
        logger.error(f'[API:record_detail] 错误: {e}', exc_info=True)
        return _build_error_response(f'获取记录详情失败: {str(e)}',
                                     code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def bug_analysis_record_delete(request, record_id):
    """删除一条分析记录"""
    try:
        if not _DB_RECORDS_AVAILABLE:
            return _build_error_response('历史记录功能暂不可用', code=status.HTTP_503_SERVICE_UNAVAILABLE)
        record = BugAnalysisRecord.objects.filter(id=record_id).first()
        if not record:
            return _build_error_response(f'记录不存在: id={record_id}', code=status.HTTP_404_NOT_FOUND)

        record.delete()
        return _build_api_response({}, f'记录 id={record_id} 已删除')

    except Exception as e:
        logger.error(f'[API:record_delete] 错误: {e}', exc_info=True)
        return _build_error_response(f'删除失败: {str(e)}',
                                     code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')


# ============================================================
# API 端点：跨版本对比
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def bug_analysis_compare(request):
    """
    跨版本对比两次分析记录的变化

    GET参数:
        - ids: 逗号分隔的记录 ID (如 "1,2"，最多2个)

    返回:
        - 变化报告: 各维度数据的增减变化
    """
    try:
        ids_param = request.query_params.get('ids', '')
        ids = [int(i.strip()) for i in ids_param.split(',') if i.strip().isdigit()]

        if len(ids) < 2:
            return _build_error_response('请提供至少2个记录ID进行对比 (如 ?ids=1,2)')
        if len(ids) > 2:
            ids = ids[:2]

        if not _DB_RECORDS_AVAILABLE:
            return _build_error_response('历史记录功能暂不可用', code=status.HTTP_503_SERVICE_UNAVAILABLE)
        records = list(BugAnalysisRecord.objects.filter(id__in=ids))
        if len(records) < 2:
            found_ids = [r.id for r in records]
            missing = set(ids) - set(found_ids)
            return _build_error_response(f'以下记录不存在: {missing}')

        # 排序: 旧的在前
        records.sort(key=lambda r: r.created_at)
        old_rec, new_rec = records
        old_res = old_rec.analysis_result or {}
        new_res = new_rec.analysis_result or {}

        # 对比各维度
        comparison = {
            'baseline': {
                'id': old_rec.id,
                'tag': old_rec.version_tag,
                'file': old_rec.file_name,
                'date': localtime(old_rec.created_at).strftime('%Y-%m-%d'),
                'total_bugs': old_rec.total_bugs,
            },
            'current': {
                'id': new_rec.id,
                'tag': new_rec.version_tag,
                'file': new_rec.file_name,
                'date': localtime(new_rec.created_at).strftime('%Y-%m-%d'),
                'total_bugs': new_rec.total_bugs,
            },
            'changes': {},
        }

        # 严重度对比
        changes = comparison['changes']
        for sev_key in ['推断P0', '推断P1', '推断P2']:
            old_val = (old_res.get('sevInfData') or {}).get(sev_key, 0)
            new_val = (new_res.get('sevInfData') or {}).get(sev_key, 0)
            diff = new_val - old_val
            changes[f'sev_{sev_key}'] = {'old': old_val, 'new': new_val, 'diff': diff}

        # 模块排名变化
        old_modules = old_res.get('modulesData', {})
        new_modules = new_res.get('modulesData', {})
        all_mods = set(list(old_modules.keys()) + list(new_modules.keys()))
        module_changes = []
        for m in all_mods:
            oc = old_modules.get(m, 0)
            nc = new_modules.get(m, 0)
            if oc != nc:
                module_changes.append({
                    'module': m, 'old_count': oc, 'new_count': nc, 'diff': nc - oc
                })
        module_changes.sort(key=lambda x: abs(x['diff']), reverse=True)
        changes['module_ranking'] = module_changes[:15]

        # 新出现的模块
        new_appeared = [m for m in new_modules if m not in old_modules]
        disappeared = [m for m in old_modules if m not in new_modules]
        changes['new_modules'] = new_appeared
        changes['disappeared_modules'] = disappeared

        # 总数变化
        changes['total_diff'] = new_rec.total_bugs - old_rec.total_bugs

        return _build_api_response(comparison)

    except Exception as e:
        logger.error(f'[API:compare] 错误: {e}', exc_info=True)
        return _build_error_response(f'对比分析失败: {str(e)}',
                                     code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')


# ============================================================
# API 端点：模块详情 (含 Bug 明细)
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def bug_analysis_module_detail(request, record_id):
    """
    获取指定分析记录中某个模块的详细信息和 Bug 明细

    GET参数:
        - record_id: 分析记录 ID (URL路径)
        - module: 模块名称 (查询参数, 必填)
        - page: Bug明细页码 (默认1)
        - page_size: 每页数量 (默认20, 最大100)
        - sort: 排序方式 (severity_asc|severity_desc|date_desc, 默认 date_desc)
    """
    try:
        if not _DB_RECORDS_AVAILABLE:
            return _build_error_response('历史记录功能暂不可用', code=status.HTTP_503_SERVICE_UNAVAILABLE)
        record = BugAnalysisRecord.objects.filter(id=record_id).first()
        if not record:
            return _build_error_response(f'记录不存在: id={record_id}', code=status.HTTP_404_NOT_FOUND)

        module_name = request.query_params.get('module', '').strip()
        if not module_name:
            return _build_error_response('请指定 module 参数')

        page = int(request.query_params.get('page', 1))
        page_size = min(int(request.query_params.get('page_size', 20)), 100)
        sort = request.query_params.get('sort', 'date_desc')

        result = record.analysis_result or {}
        raw_bugs = record.raw_bugs or []

        # 过滤该模块的所有 Bug
        mod_bugs = [b for b in raw_bugs if b.get('module') == module_name]
        total_in_module = len(mod_bugs)

        # 从分析结果中提取该模块的统计信息
        tf = result.get('testFocusData', {}).get(module_name, {})
        cluster_item = next(
            (c for c in result.get('clusterData', []) if c.get('feature') == module_name),
            None
        )

        # 排序
        if sort == 'severity_asc':
            sev_order = {'P0': 0, 'P1': 1, 'P2': 2}
            mod_bugs.sort(key=lambda b: sev_order.get(b.get('inferred_sev', 'P2'), 3))
        elif sort == 'severity_desc':
            sev_order = {'P0': 0, 'P1': 1, 'P2': 2}
            mod_bugs.sort(key=lambda b: sev_order.get(b.get('inferred_sev', 'P2'), 3), reverse=True)
        else:
            # 按 created 降序
            mod_bugs.sort(
                key=lambda b: b.get('created') or datetime.min,
                reverse=True
            )

        # 分页
        start = (page - 1) * page_size
        end = start + page_size
        paged_bugs = mod_bugs[start:end]

        # 格式化 Bug 明细
        bug_items = []
        for b in paged_bugs:
            bug_items.append({
                'title': b.get('title', ''),
                'desc': b.get('desc', ''),
                'severity': b.get('severity', ''),
                'status': b.get('status', ''),
                'inferred_sev': b.get('inferred_sev', ''),
                'defect_type': b.get('defect_type', ''),
                'creator': b.get('creator', ''),
                'type': b.get('type', ''),
                'created': b.get('created').strftime('%Y-%m-%d') if isinstance(b.get('created'), datetime) else str(b.get('created', '')),
                'tags': b.get('tags', []),
            })

        detail = {
            'record_id': record_id,
            'module': module_name,
            'total_in_module': total_in_module,
            'stats': {
                'total': tf.get('total', total_in_module),
                'online': tf.get('online', 0),
                'reopened': tf.get('reopened', 0),
                'top_types': tf.get('top_types', []),
                'dtype_dist': tf.get('dtype_dist', {}),
                'focus_points': tf.get('focus_points', []),
            },
            'type_distribution': cluster_item.get('type_distribution', {}) if cluster_item else {},
            # AI 增强数据
            'ai_test_focus': (result.get('aiTestFocus', {}) or {}).get(module_name, ''),
            'ai_root_cause': next(
                (rc.get('cause', '') for rc in (result.get('aiRootCause', []) or [])
                 if rc.get('module') == module_name),
                ''
            ),
            'bugs': bug_items,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': total_in_module,
                'total_pages': max(1, (total_in_module + page_size - 1) // page_size),
            },
        }

        return _build_api_response(detail)

    except Exception as e:
        logger.error(f'[API:module_detail] 错误: {e}', exc_info=True)
        return _build_error_response(f'获取模块详情失败: {str(e)}',
                                     code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')


# ============================================================
# API 端点：智能模块测试重点分析 (三层架构)
# ============================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_module_focus_intelligent(request):
    """
    智能模块测试重点分析 - 三层架构 AI 分析
    
    第一层: 快速统计分析 (规则驱动)
    第二层: 深度语义分析 (AI大模型)
    第三层: 关联分析 (时间模式、创建者集中度等)
    
    POST参数:
        - record_id: 分析记录ID (必填)
        - module: 模块名称 (必填)
        - ai_config_id: AI模型配置ID (可选)
        
    返回:
        - module_name: 模块名称
        - total_count: Bug总数
        - layer1_stats: 第一层统计结果
        - layer2_insights: 第二层AI洞察
        - layer3_correlations: 第三层关联分析
        - focus_points: 合并后的测试关注点列表
        - risk_level: 综合风险等级 (high/medium/low)
        - test_strategy: 整体测试策略建议
    """
    start_time = time.time()
    
    try:
        # 参数验证
        record_id = request.data.get('record_id')
        module_name = request.data.get('module', '').strip()
        ai_config_id_str = request.data.get('ai_config_id') or ''
        ai_config_id = int(ai_config_id_str) if ai_config_id_str and ai_config_id_str.isdigit() else None
        
        if not record_id:
            return _build_error_response('请提供 record_id 参数')
        if not module_name:
            return _build_error_response('请提供 module 参数')
        
        # 自动获取AI配置
        if ai_config_id is None:
            ai_config_id = _get_bug_analyzer_config_id()
        
        logger.info(f"[API:analyze_module_focus] record_id={record_id}, module={module_name}")
        
        # 获取记录
        if not _DB_RECORDS_AVAILABLE:
            return _build_error_response('历史记录功能暂不可用', code=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        record = BugAnalysisRecord.objects.filter(id=record_id).first()
        if not record:
            return _build_error_response(f'记录不存在: id={record_id}', code=status.HTTP_404_NOT_FOUND)
        
        # 获取该模块的所有Bug
        raw_bugs = record.raw_bugs or []
        module_bugs = [b for b in raw_bugs if b.get('module') == module_name]
        
        if not module_bugs:
            return _build_error_response(f'模块 {module_name} 在该记录中无Bug数据')
        
        # 检查是否有缓存的智能分析结果
        analysis_result = record.analysis_result or {}
        ai_module_focus = analysis_result.get('aiModuleFocus', {})
        cached_result = ai_module_focus.get(module_name)
        
        # 如果缓存存在且未过期(24小时内)，直接返回
        if cached_result:
            generated_at = cached_result.get('ai_generated_at', '')
            if generated_at:
                try:
                    from datetime import datetime, timedelta
                    gen_time = datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
                    if datetime.now() - gen_time < timedelta(hours=24):
                        logger.info(f"[API:analyze_module_focus] 返回缓存结果: {module_name}")
                        return _build_api_response({
                            **cached_result,
                            'cached': True,
                            'record_id': record_id
                        }, '返回缓存的智能分析结果')
                except:
                    pass
        
        # 执行智能分析
        try:
            from .bug_analysis_ai import get_ai_provider
            ai = get_ai_provider(provider_name='qwen', config_id=ai_config_id)
            
            # 调用三层架构分析方法
            intelligent_result = async_to_sync(ai.analyze_module_focus_intelligent)(module_name, module_bugs)
            
            # 保存到缓存 - 使用重新读取记录避免并发覆盖问题
            from django.db import transaction
            from datetime import datetime
            with transaction.atomic():
                # 重新读取记录以获取最新的 analysis_result
                record = BugAnalysisRecord.objects.select_for_update().get(id=record_id)
                analysis_result = record.analysis_result or {}
                if 'aiModuleFocus' not in analysis_result:
                    analysis_result['aiModuleFocus'] = {}
                
                # 确保可序列化，添加时间戳
                intelligent_result['ai_generated_at'] = datetime.now().isoformat()
                analysis_result['aiModuleFocus'][module_name] = intelligent_result
                
                record.analysis_result = analysis_result
                record.save(update_fields=['analysis_result'])
                logger.info(f"[API:analyze_module_focus] 已保存模块 {module_name} 到 aiModuleFocus")
                logger.info(f"[API:analyze_module_focus] 当前 aiModuleFocus 模块列表: {list(analysis_result['aiModuleFocus'].keys())}")
            
            elapsed = round((time.time() - start_time) * 1000)
            logger.info(f"[API:analyze_module_focus] 成功: {module_name}, 耗时={elapsed}ms")
            
            return _build_api_response({
                **intelligent_result,
                'cached': False,
                'record_id': record_id,
                'elapsed_ms': elapsed
            }, f'智能分析完成 (耗时{elapsed}ms)')
            
        except Exception as e:
            logger.error(f"[API:analyze_module_focus] AI分析失败: {e}", exc_info=True)
            # 降级返回基础统计
            return _build_api_response({
                'module_name': module_name,
                'total_count': len(module_bugs),
                'focus_points': [{
                    'type': '基础统计',
                    'level': 'medium',
                    'description': f'共{len(module_bugs)}条Bug',
                    'test_suggestion': '建议进行全面回归测试',
                    'source': 'fallback'
                }],
                'risk_level': 'medium',
                'fallback': True,
                'error': str(e),
                'record_id': record_id
            }, 'AI分析失败，返回基础统计')
            
    except Exception as e:
        logger.error(f'[API:analyze_module_focus] 未预期错误: {e}', exc_info=True)
        return _build_error_response(f'分析失败: {str(e)}',
                                     code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')


# ============================================================
# Bug 分析汇总统计 (新增)
# ============================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bug_analysis_summary(request):
    """
    Bug 分析汇总统计
    
    请求体:
    {
        "record_ids": [1, 2, 3],
        "group_by": "week" | "month" | "quarter" | "half_year" | "year"
    }
    
    响应:
    {
        "metrics": {
            "total_bugs": 1234,
            "total_modules": 28,
            "record_count": 12,
            "online_bugs": 156,
            "defect_bugs": 1078
        },
        "trends": [
            {"date": "2026-Q1", "total": 172, "online": 12, "defect": 160}
        ],
        "module_ranking": [
            {"module": "用户中心", "count": 45, "trend": "up"}
        ],
        "risk_modules": [
            {"module": "支付系统", "growth_rate": 2.5, "current": 25, "trend_data": [...]}
        ]
    }
    """
    try:
        record_ids = request.data.get('record_ids', [])
        group_by = request.data.get('group_by', 'month')
        
        if not record_ids:
            return _build_error_response('请选择至少一个分析记录')
        
        if not _DB_RECORDS_AVAILABLE:
            return _build_error_response('历史记录功能暂不可用', code=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # 获取选中的记录（不使用order_by避免大数据排序内存问题）
        records = BugAnalysisRecord.objects.filter(id__in=record_ids)
        if not records.exists():
            return _build_error_response('未找到指定的分析记录')
        
        # 在Python中按时间排序
        records = sorted(records, key=lambda r: r.created_at)
        
        logger.info(f"[API:bug_analysis_summary] 用户={request.user.username}, 记录数={len(record_ids)}, 聚合维度={group_by}")
        
        # 计算基础指标
        total_bugs = sum(r.total_bugs for r in records)
        record_count = len(records)
        
        # 收集所有模块
        all_modules = set()
        online_bugs = 0
        defect_bugs = 0
        
        for record in records:
            analysis_result = record.analysis_result or {}
            modules_data = analysis_result.get('modulesData', {})
            all_modules.update(modules_data.keys())
            
            # 统计 Bug 类型
            work_types = analysis_result.get('metaData', {}).get('work_types', {})
            online_bugs += work_types.get('线上故障', 0) + work_types.get('线上', 0)
            defect_bugs += work_types.get('缺陷', 0) + work_types.get('缺陷Bug', 0)
        
        # 按时间聚合趋势数据
        trends = _aggregate_trends(records, group_by)
        
        # 模块排名统计
        module_stats = _calculate_module_stats(records)
        module_ranking = sorted(module_stats.items(), key=lambda x: x[1]['count'], reverse=True)[:10]
        module_ranking = [
            {
                'module': name,
                'count': stats['count'],
                'trend': stats['trend']
            }
            for name, stats in module_ranking
        ]
        
        # 风险预警模块（复杂方案：计算增长率趋势）
        risk_modules = _calculate_risk_modules(records, module_stats)
        
        result = {
            'metrics': {
                'total_bugs': total_bugs,
                'total_modules': len(all_modules),
                'record_count': record_count,
                'online_bugs': online_bugs,
                'defect_bugs': defect_bugs
            },
            'trends': trends,
            'module_ranking': module_ranking,
            'risk_modules': risk_modules
        }

        # 保存汇总分析记录
        if _DB_RECORDS_AVAILABLE and BugAnalysisSummaryRecord is not None:
            try:
                # 生成默认名称
                from datetime import datetime
                default_name = f"汇总分析 {datetime.now().strftime('%Y%m%d')}"

                summary_record = BugAnalysisSummaryRecord.objects.create(
                    name=default_name,
                    group_by=group_by,
                    record_ids=record_ids,
                    total_bugs=total_bugs,
                    total_modules=len(all_modules),
                    record_count=record_count,
                    online_bugs=online_bugs,
                    defect_bugs=defect_bugs,
                    summary_data={
                        'trends': trends,
                        'module_ranking': module_ranking,
                        'risk_modules': risk_modules,
                    },
                    created_by=request.user.username if request.user.is_authenticated else 'system'
                )
                result['summary_id'] = summary_record.id
                logger.info(f"[API:bug_analysis_summary] 汇总分析已保存: id={summary_record.id}")
            except Exception as e:
                logger.error(f"[API:bug_analysis_summary] 保存汇总分析记录失败: {e}", exc_info=True)

        logger.info(f"[API:bug_analysis_summary] 汇总完成: 总Bug={total_bugs}, 模块数={len(all_modules)}, 风险模块={len(risk_modules)}")

        return _build_api_response(result, '汇总分析完成')
        
    except Exception as e:
        logger.error(f'[API:bug_analysis_summary] 未预期错误: {e}', exc_info=True)
        return _build_error_response(f'汇总分析失败: {str(e)}',
                                     code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')


def _aggregate_trends(records, group_by):
    """按时间维度聚合趋势数据 - 基于Bug创建时间"""
    from collections import defaultdict
    from datetime import datetime
    
    # 按时间分组
    groups = defaultdict(lambda: {'total': 0, 'online': 0, 'defect': 0, 'count': 0})
    
    for record in records:
        raw_bugs = record.raw_bugs or []
        
        for bug in raw_bugs:
            # 获取Bug创建时间
            created = bug.get('created')
            if not created:
                continue
                
            # 解析日期
            if isinstance(created, str):
                try:
                    created = datetime.fromisoformat(created.replace('Z', '+00:00'))
                except:
                    continue
            elif isinstance(created, datetime):
                pass
            else:
                continue
            
            date_key = _get_date_key(created, group_by)
            
            groups[date_key]['total'] += 1
            groups[date_key]['count'] += 1
            
            # 统计类型 - 根据Bug的type字段
            bug_type = bug.get('type', '')
            if bug_type in ['线上故障', '线上']:
                groups[date_key]['online'] += 1
            elif bug_type in ['缺陷', '缺陷Bug']:
                groups[date_key]['defect'] += 1
    
    # 转换为列表并排序
    trends = [
        {
            'date': key,
            'total': data['total'],
            'online': data['online'],
            'defect': data['defect'],
            'record_count': data['count']
        }
        for key, data in sorted(groups.items())
    ]
    
    return trends


def _get_date_key(dt, group_by):
    """根据聚合维度生成日期键"""
    year = dt.year
    month = dt.month
    
    if group_by == 'week':
        # 返回周标识：2026-W15
        week = dt.isocalendar()[1]
        return f"{year}-W{week:02d}"
    elif group_by == 'month':
        # 返回月份：2026-04
        return f"{year}-{month:02d}"
    elif group_by == 'quarter':
        # 返回季度：2026-Q1
        quarter = (month - 1) // 3 + 1
        return f"{year}-Q{quarter}"
    elif group_by == 'half_year':
        # 返回半年：2026-H1
        half = 1 if month <= 6 else 2
        return f"{year}-H{half}"
    elif group_by == 'year':
        # 返回年份：2026
        return str(year)
    else:
        return f"{year}-{month:02d}"


def _calculate_module_stats(records):
    """计算各模块的统计数据"""
    from collections import defaultdict
    
    # 模块 -> 各时间点的数量
    module_timeline = defaultdict(lambda: [])
    
    for record in records:
        analysis_result = record.analysis_result or {}
        modules_data = analysis_result.get('modulesData', {})
        date_str = record.created_at.strftime('%Y-%m-%d')
        
        for module, count in modules_data.items():
            module_timeline[module].append({
                'date': date_str,
                'count': count
            })
    
    # 计算趋势
    stats = {}
    for module, timeline in module_timeline.items():
        total = sum(t['count'] for t in timeline)
        
        # 判断趋势
        trend = 'stable'
        if len(timeline) >= 2:
            first = timeline[0]['count']
            last = timeline[-1]['count']
            if last > first * 1.2:
                trend = 'up'
            elif last < first * 0.8:
                trend = 'down'
        
        stats[module] = {
            'count': total,
            'trend': trend,
            'timeline': timeline
        }
    
    return stats


def _calculate_risk_modules(records, module_stats):
    """计算风险预警模块（复杂方案：增长率趋势分析）"""
    risk_modules = []
    
    for module, stats in module_stats.items():
        timeline = stats['timeline']
        if len(timeline) < 2:
            continue
        
        # 复杂方案：计算加权增长率
        # 最近的数据权重更高
        weights = []
        counts = []
        for i, t in enumerate(timeline):
            weight = (i + 1) / len(timeline)  # 线性递增权重
            weights.append(weight)
            counts.append(t['count'])
        
        # 计算加权平均增长率
        if len(counts) >= 2:
            growth_rates = []
            for i in range(1, len(counts)):
                if counts[i-1] > 0:
                    rate = (counts[i] - counts[i-1]) / counts[i-1]
                    growth_rates.append(rate * weights[i])
            
            if growth_rates:
                avg_growth = sum(growth_rates) / sum(weights[1:])
                
                # 增长超过 30% 且当前数量 >= 5 标记为风险
                if avg_growth > 0.3 and counts[-1] >= 5:
                    risk_modules.append({
                        'module': module,
                        'growth_rate': round(avg_growth, 2),
                        'current': counts[-1],
                        'previous': counts[0],
                        'trend_data': timeline
                    })
    
    # 按增长率排序，取前10
    risk_modules.sort(key=lambda x: x['growth_rate'], reverse=True)
    return risk_modules[:10]


# ============================================================
# API 端点：直接调用 AI 生成汇总洞察报告
# ============================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_summary_insight(request):
    """
    直接调用 AI 生成 Bug 汇总洞察报告
    
    请求体:
    {
        "summary_data": {
            "metrics": {...},
            "trends": [...],
            "module_ranking": [...],
            "risk_modules": [...]
        },
        "summary_id": 123  // 可选，用于保存洞察到指定汇总分析记录
    }
    
    响应:
    {
        "insight": "AI 生成的洞察报告 (Markdown 格式)"
    }
    """
    try:
        summary_data = request.data.get('summary_data', {})
        summary_id = request.data.get('summary_id')
        
        if not summary_data:
            return _build_error_response('请提供汇总数据')
        
        # 构造分析提示词
        metrics = summary_data.get('metrics', {})
        risk_modules = summary_data.get('risk_modules', [])
        module_ranking = summary_data.get('module_ranking', [])
        top_modules = module_ranking[:5]
        
        prompt = f"""请作为测试质量分析师，基于以下 Bug 汇总数据生成专业的质量洞察报告：

【汇总概览】
- 总 Bug 数：{metrics.get('total_bugs', 0)}
- 涉及模块：{metrics.get('total_modules', 0)} 个
- 分析记录：{metrics.get('record_count', 0)} 条
- 线上故障：{metrics.get('online_bugs', 0)} 个
- 缺陷数量：{metrics.get('defect_bugs', 0)} 个

【热点模块 Top5】
"""
        for i, m in enumerate(top_modules, 1):
            trend_text = '上升趋势' if m.get('trend') == 'up' else '下降趋势' if m.get('trend') == 'down' else '稳定'
            prompt += f"{i}. {m.get('module', '')}: {m.get('count', 0)} 个 ({trend_text})\n"
        
        prompt += "\n【风险预警】\n"
        if risk_modules:
            for i, m in enumerate(risk_modules[:5], 1):
                prompt += f"{i}. {m.get('module', '')}: 增长率 {m.get('growth_rate', 0) * 100:.0f}%\n"
        else:
            prompt += "无明显风险模块\n"
        
        prompt += """
请从以下维度进行分析并给出建议：
1. 整体质量趋势评估
2. 高风险模块分析
3. 改进建议和行动项

请以 Markdown 格式输出，包含表格和列表，便于阅读。"""

        # 调用 AI
        try:
            # 导入 AIModelService
            from apps.requirement_analysis.ai_models import AIModelService
            from apps.requirement_analysis.models import AIModelConfig
            
            # 获取 Bug 分析专家的 AI 配置
            config = AIModelConfig.objects.filter(
                role='bug_analyzer',
                is_active=True
            ).first()
            
            if not config:
                # 如果没有专门的 bug_analyzer 配置，使用任意活跃配置
                config = AIModelConfig.objects.filter(is_active=True).first()
            
            if not config:
                return _build_error_response('未找到可用的 AI 模型配置，请先在配置中心配置 AI 模型')
            
            logger.info(f"[API:generate_summary_insight] 使用 AI 配置: {config.model_type} - {config.model_name}")
            
            # 调用 AI API
            messages = [
                {'role': 'system', 'content': '你是专业的测试质量分析师，擅长分析 Bug 数据并提供改进建议。'},
                {'role': 'user', 'content': prompt}
            ]
            
            response_data = async_to_sync(AIModelService.call_openai_compatible_api)(config, messages)
            
            # 提取 AI 回复
            insight = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            if not insight:
                return _build_error_response('AI 未返回有效内容')
            
            logger.info(f"[API:generate_summary_insight] AI 洞察生成成功，长度: {len(insight)} 字符")

            # 如果提供了 summary_id，保存洞察到数据库
            if summary_id and _DB_RECORDS_AVAILABLE and BugAnalysisSummaryRecord is not None:
                try:
                    record = BugAnalysisSummaryRecord.objects.get(id=summary_id)
                    record.ai_insight = insight
                    record.save(update_fields=['ai_insight'])
                    logger.info(f"[API:generate_summary_insight] 洞察已保存到汇总分析记录 {summary_id}")
                except BugAnalysisSummaryRecord.DoesNotExist:
                    logger.warning(f"[API:generate_summary_insight] 汇总分析记录 {summary_id} 不存在，洞察未保存")
                except Exception as save_error:
                    logger.error(f"[API:generate_summary_insight] 保存洞察失败: {save_error}")

            return Response({
                'success': True,
                'data': {
                    'insight': insight
                },
                'message': 'AI 洞察生成成功'
            })
            
        except Exception as e:
            logger.error(f"AI 调用失败: {e}", exc_info=True)
            return _build_error_response(f'AI 调用失败: {str(e)}')

    except Exception as e:
        logger.error(f'[API:generate_summary_insight] 错误: {e}', exc_info=True)
        return _build_error_response(f'生成洞察失败: {str(e)}',
                                     code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')


# ============================================================
# API 端点：汇总分析记录管理
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def bug_analysis_summaries(request):
    """
    获取汇总分析列表

    GET参数:
        - page: 页码 (默认1)
        - page_size: 每页数量 (默认20)
        - search: 搜索关键词 (按名称搜索)

    响应:
        {
            "success": true,
            "data": {
                "items": [...],
                "total": 100,
                "page": 1,
                "page_size": 20
            }
        }
    """
    try:
        if not _DB_RECORDS_AVAILABLE or BugAnalysisSummaryRecord is None:
            return _build_error_response('汇总分析功能暂不可用', code=status.HTTP_503_SERVICE_UNAVAILABLE)

        page = int(request.query_params.get('page', 1))
        page_size = min(int(request.query_params.get('page_size', 20)), 100)
        search = request.query_params.get('search', '').strip()

        # 构建查询
        queryset = BugAnalysisSummaryRecord.objects.all()

        # 搜索过滤
        if search:
            queryset = queryset.filter(name__icontains=search)

        # 统计总数
        total = queryset.count()

        # 分页
        start = (page - 1) * page_size
        end = start + page_size
        records = queryset[start:end]

        # 序列化并添加关联文件名
        items = []
        for r in records:
            item = r.to_list_dict()
            # 查询关联的文件名
            if r.record_ids:
                related_records = BugAnalysisRecord.objects.filter(
                    id__in=r.record_ids
                ).values('id', 'file_name')
                item['related_files'] = [
                    {'id': rec['id'], 'file_name': rec['file_name'] or f'记录{rec["id"]}'}
                    for rec in related_records
                ]
            else:
                item['related_files'] = []
            items.append(item)

        return _build_api_response({
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size
        }, '获取汇总分析列表成功')

    except Exception as e:
        logger.error(f'[API:bug_analysis_summaries] 错误: {e}', exc_info=True)
        return _build_error_response(f'获取汇总分析列表失败: {str(e)}',
                                     code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def bug_analysis_summary_detail(request, summary_id):
    """
    获取汇总分析详情

    响应:
        {
            "success": true,
            "data": {
                "id": 1,
                "name": "汇总分析",
                "metrics": {...},
                "trends": [...],
                ...
            }
        }
    """
    try:
        if not _DB_RECORDS_AVAILABLE or BugAnalysisSummaryRecord is None:
            return _build_error_response('汇总分析功能暂不可用', code=status.HTTP_503_SERVICE_UNAVAILABLE)

        record = BugAnalysisSummaryRecord.objects.filter(id=summary_id).first()
        if not record:
            return _build_error_response(f'汇总分析记录不存在: id={summary_id}', code=status.HTTP_404_NOT_FOUND)

        return _build_api_response(record.to_detail_dict(), '获取汇总分析详情成功')

    except Exception as e:
        logger.error(f'[API:bug_analysis_summary_detail] 错误: {e}', exc_info=True)
        return _build_error_response(f'获取汇总分析详情失败: {str(e)}',
                                     code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def bug_analysis_summary_delete(request, summary_id):
    """
    删除汇总分析记录
    """
    try:
        if not _DB_RECORDS_AVAILABLE or BugAnalysisSummaryRecord is None:
            return _build_error_response('汇总分析功能暂不可用', code=status.HTTP_503_SERVICE_UNAVAILABLE)

        record = BugAnalysisSummaryRecord.objects.filter(id=summary_id).first()
        if not record:
            return _build_error_response(f'汇总分析记录不存在: id={summary_id}', code=status.HTTP_404_NOT_FOUND)

        record.delete()
        logger.info(f"[API:bug_analysis_summary_delete] 用户={request.user.username}, 删除汇总分析 id={summary_id}")

        return _build_api_response({}, '删除成功')

    except Exception as e:
        logger.error(f'[API:bug_analysis_summary_delete] 错误: {e}', exc_info=True)
        return _build_error_response(f'删除失败: {str(e)}',
                                     code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')


# ============================================================
# API 端点：云效同步 (新增)
# ============================================================

def _resolve_yunxiao_client(request):
    """
    从请求中解析 token_id, 查询 YunxiaoToken 表, 返回 YunxiaoClient 实例。
    若 token_id 未提供或 token 记录不存在, 返回 (None, error_response) 元组。
    """
    from .models import YunxiaoToken
    from .yunxiao_client import YunxiaoClient, YunxiaoAPIError, DEFAULT_ORGANIZATION_ID

    token_id = request.data.get('token_id') or request.query_params.get('token_id')
    if token_id is not None:
        try:
            token_id = int(token_id)
        except (ValueError, TypeError):
            return None, _build_error_response('无效的 Token ID')

        try:
            token_obj = YunxiaoToken.objects.get(id=token_id, is_active=True)
        except YunxiaoToken.DoesNotExist:
            return None, _build_error_response('指定的 Token 不存在或已禁用')

        if not token_obj.token:
            return None, _build_error_response('指定的 Token 值为空')

        return YunxiaoClient(
            token=token_obj.token,
            organization_id=DEFAULT_ORGANIZATION_ID,
        ), None

    # 兼容旧接口: 直接传 token (用于 token 管理接口自身的测试)
    token = (request.data.get('token') or request.query_params.get('token') or '').strip()
    if token:
        org_id = (request.data.get('organization_id') or request.query_params.get('organization_id') or '').strip()
        return YunxiaoClient(
            token=token,
            organization_id=org_id or DEFAULT_ORGANIZATION_ID,
        ), None

    return None, _build_error_response('请选择访问令牌')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def yunxiao_projects(request):
    """
    获取云效项目列表 (代理接口)

    POST参数:
        - token_id: 云效Token配置ID (推荐, 替代 token + organization_id)
        - keyword: 搜索关键词 (可选)
        - page: 页码 (默认1)
        - per_page: 每页数量 (默认50)
    """
    try:
        client, err = _resolve_yunxiao_client(request)
        if err:
            return err

        keyword = request.data.get('keyword', '').strip()
        page = int(request.data.get('page', 1))
        per_page = min(int(request.data.get('per_page', 50)), 200)

        projects = client.search_projects(keyword=keyword, page=page, per_page=per_page)

        # 统一返回格式
        items = []
        for p in projects:
            items.append({
                'id': p.get('identifier') or p.get('id') or p.get('spaceIdentifier'),
                'name': p.get('name') or p.get('spaceName') or '未命名',
                'description': p.get('description', ''),
            })

        return _build_api_response({
            'items': items,
            'total': len(items),
        }, f'获取 {len(items)} 个项目')

    except YunxiaoAPIError as e:
        return _build_error_response(f'云效 API 错误: {e}')
    except Exception as e:
        logger.error(f'[API:yunxiao_projects] 错误: {e}', exc_info=True)
        return _build_error_response(f'获取项目列表失败: {str(e)}',
                                     code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def yunxiao_sprints(request):
    """
    获取云效迭代列表 (代理接口)

    POST参数:
        - token_id: 云效Token配置ID (推荐, 替代 token + organization_id)
        - space_id: 项目 ID (必填)
        - page: 页码 (默认1)
        - per_page: 每页数量 (默认50)
    """
    try:
        client, err = _resolve_yunxiao_client(request)
        if err:
            return err

        space_id = request.data.get('space_id', '').strip()
        page = int(request.data.get('page', 1))
        per_page = min(int(request.data.get('per_page', 50)), 200)

        if not space_id:
            return _build_error_response('请提供项目 ID (space_id)')

        sprints = client.list_sprints(space_id=space_id, page=page, per_page=per_page)

        items = []
        for s in sprints:
            items.append({
                'id': s.get('identifier') or s.get('id') or s.get('sprintIdentifier'),
                'name': s.get('name') or s.get('sprintName') or '未命名',
                'start_date': s.get('startDate') or s.get('plannedStartDate', ''),
                'end_date': s.get('endDate') or s.get('plannedEndDate', ''),
                'status': s.get('status') or s.get('sprintStatus', ''),
            })

        return _build_api_response({
            'items': items,
            'total': len(items),
        }, f'获取 {len(items)} 个迭代')

    except YunxiaoAPIError as e:
        return _build_error_response(f'云效 API 错误: {e}')
    except Exception as e:
        logger.error(f'[API:yunxiao_sprints] 错误: {e}', exc_info=True)
        return _build_error_response(f'获取迭代列表失败: {str(e)}',
                                     code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def yunxiao_members(request):
    """
    获取云效项目成员列表 (代理接口)

    POST参数:
        - token_id: 云效Token配置ID (推荐)
        - space_id: 项目 ID (必填)

    返回:
        - members: 成员列表, 每个成员包含 userId, userName, email 等字段
    """
    try:
        client, err = _resolve_yunxiao_client(request)
        if err:
            return err

        space_id = request.data.get('space_id', '').strip()

        if not space_id:
            return _build_error_response('请提供项目 ID (space_id)')

        members = client.list_project_members(space_id=space_id)

        items = []
        for m in members:
            items.append({
                'userId': m.get('userId') or m.get('id') or '',
                'userName': m.get('userName') or m.get('name') or '',
                'email': m.get('email') or '',
                'avatar': m.get('avatar') or m.get('avatarUrl') or '',
                'displayName': m.get('displayName') or m.get('userName') or '',
            })

        return _build_api_response({
            'items': items,
            'total': len(items),
        }, f'获取 {len(items)} 个成员')

    except YunxiaoAPIError as e:
        return _build_error_response(f'云效 API 错误: {e}')
    except Exception as e:
        logger.error(f'[API:yunxiao_members] 错误: {e}', exc_info=True)
        return _build_error_response(f'获取项目成员列表失败: {str(e)}',
                                     code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def yunxiao_labels(request):
    """
    获取云效项目标签列表 (用于模块选择)

    POST参数:
        - token_id: 云效Token配置ID (推荐)
        - space_id: 项目 ID (必填)

    返回:
        - items: 标签列表, 每个标签包含 id, name, color 等字段
    """
    try:
        client, err = _resolve_yunxiao_client(request)
        if err:
            return err

        space_id = request.data.get('space_id', '').strip()

        if not space_id:
            return _build_error_response('请提供项目 ID (space_id)')

        labels = client.list_project_labels(space_id=space_id)

        items = []
        for lb in labels:
            items.append({
                'id': lb.get('id') or lb.get('labelId') or '',
                'name': lb.get('name') or lb.get('labelName') or '',
                'color': lb.get('color') or '',
            })

        return _build_api_response({
            'items': items,
            'total': len(items),
        }, f'获取 {len(items)} 个标签')

    except YunxiaoAPIError as e:
        return _build_error_response(f'云效 API 错误: {e}')
    except Exception as e:
        logger.error(f'[API:yunxiao_labels] 错误: {e}', exc_info=True)
        return _build_error_response(f'获取项目标签列表失败: {str(e)}',
                                     code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_from_yunxiao(request):
    """
    从云效同步 Bug 数据并进行分析

    POST参数:
        - token_id: 云效Token配置ID (推荐, 替代 token + organization_id)
        - space_id: 项目 ID (必填)
        - sprint_id: 迭代 ID (可选)
        - version_tag: 版本标签 (可选)
        - ai_provider: AI提供者 ('mock'|'qwen'|'none', 默认 'qwen')
        - ai_config_id: AI模型配置ID (可选)
        - skip_ai: 是否跳过AI分析 (默认 false)
        - max_bugs: 最大拉取数量 (默认 1000)

    返回:
        - 同 analyze_bug_excel 接口的分析结果
    """
    start_time = time.time()

    try:
        # 参数提取
        client, err = _resolve_yunxiao_client(request)
        if err:
            return err

        from .yunxiao_client import DEFAULT_ORGANIZATION_ID
        # 从 client 中提取 token (client.token 属性)
        token = client.token
        organization_id = DEFAULT_ORGANIZATION_ID
        domain = request.data.get('domain', '').strip()
        space_id = request.data.get('space_id', '').strip()
        sprint_id = request.data.get('sprint_id', '').strip() or None
        sprint_name = request.data.get('sprint_name', '').strip() or None
        version_tag = request.data.get('version_tag', '').strip()
        ai_provider = request.data.get('ai_provider', 'qwen').lower()
        ai_config_id_str = request.data.get('ai_config_id') or ''
        ai_config_id = int(ai_config_id_str) if ai_config_id_str and ai_config_id_str.isdigit() else None
        skip_ai_raw = request.data.get('skip_ai', 'false')
        skip_ai = str(skip_ai_raw).lower() in ('true', '1', 'yes')
        max_bugs = int(request.data.get('max_bugs', 1000))

        if not space_id:
            return _build_error_response('请提供项目 ID (space_id)')

        logger.info(f"[API:sync_from_yunxiao] 项目={space_id}, 迭代={sprint_id}, AI={ai_provider}")

        # 从云效拉取 Bug 数据
        try:
            bugs = BugSourceAdapter.from_yunxiao({
                "token": token,
                "organization_id": organization_id,
                "domain": domain,
                "space_id": space_id,
                "sprint_id": sprint_id,
                "max_bugs": max_bugs,
            })
        except Exception as e:
            logger.error(f"[API:sync_from_yunxiao] 拉取云效数据失败: {e}", exc_info=True)
            return _build_error_response(f'从云效拉取数据失败: {e}')

        # 数据校验
        is_valid, err_msg = _validate_bug_data(bugs)
        if not is_valid:
            return _build_error_response(err_msg)

        logger.info(f"[API:sync_from_yunxiao] 拉取完成: {len(bugs)} 条有效Bug")

        # 构建文件名标识（优先使用迭代名称）
        if sprint_name:
            file_name = f"{sprint_name}_{len(bugs)}条"
        elif sprint_id:
            file_name = f"{sprint_id}_{len(bugs)}条"
        else:
            file_name = f"云效_{space_id}_{len(bugs)}条"

        # Step 1: 执行基础分析（跳过AI，快速返回）
        analysis_result = async_to_sync(_run_enhanced_analysis)(
            bugs,
            filename=file_name,
            save_record=True,
            ai_provider_name='none',  # 先跳过AI
            version_tag=version_tag,
            source_type='yunxiao_api',
            skip_ai=True,
            ai_status='pending' if not skip_ai else 'none',
            created_by=request.user.username if request.user.is_authenticated else 'system',
        )

        record_id = analysis_result.get('record_id')

        # Step 2: 启动后台线程执行 AI 分析（不阻塞响应）
        if not skip_ai and record_id:
            import threading
            thread = threading.Thread(
                target=_run_ai_analysis_background,
                args=(record_id, bugs, analysis_result, ai_provider, ai_config_id),
                daemon=True,
                name=f"ai-analysis-{record_id}"
            )
            thread.start()
            logger.info(f"[API:sync_from_yunxiao] 后台AI分析已启动: record_id={record_id}")

        # 响应（立即返回，不等待AI）
        elapsed = round((time.time() - start_time) * 1000)
        analysis_result['success'] = True
        analysis_result['record_id'] = record_id
        analysis_result['ai_status'] = 'pending' if not skip_ai else 'none'
        analysis_result['message'] = f'云效同步成功: {len(bugs)} 条Bug (耗时{elapsed}ms)，AI分析后台进行中...'

        return _build_api_response(analysis_result, analysis_result['message'])

    except YunxiaoAPIError as e:
        return _build_error_response(f'云效 API 错误: {e}')
    except ValueError as ve:
        logger.warning(f'[API:sync_from_yunxiao] 数据验证错误: {ve}')
        return _build_error_response(str(ve))
    except Exception as e:
        logger.error(f'[API:sync_from_yunxiao] 未预期错误: {e}', exc_info=True)
        return _build_error_response(f'同步失败: {str(e)}',
                                     code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')


# ============================================================
# API 端点：Bug 双向同步 (云效 ↔ 本地)
# ============================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_bug_to_yunxiao(request):
    """
    创建 Bug 并推送到云效指定迭代

    POST参数:
        - token_id: 云效Token配置ID (推荐, 替代 token + organization_id)
        - space_id: 项目 ID (必填)
        - sprint_id: 迭代 ID (必填)
        - title: Bug 标题 (必填)
        - desc: Bug 描述 (可选)
        - severity: 严重程度 (可选)
        - priority: 优先级 (可选)
        - module: 所属模块 (可选)
        - assignee: 处理人 (可选)
        - analysis_record_id: 关联分析记录ID (可选)

    返回:
        - 创建结果 + BugSyncItem 记录
    """
    start_time = time.time()
    try:
        client, err = _resolve_yunxiao_client(request)
        if err:
            return err

        from .yunxiao_client import DEFAULT_ORGANIZATION_ID
        token = client.token
        organization_id = DEFAULT_ORGANIZATION_ID
        domain = request.data.get('domain', '').strip()
        space_id = request.data.get('space_id', '').strip()
        sprint_id = request.data.get('sprint_id', '').strip()
        title = request.data.get('title', '').strip()
        desc = request.data.get('desc', '').strip()
        severity = request.data.get('severity', '').strip()
        priority = request.data.get('priority', '').strip()
        status_val = request.data.get('status', '').strip()
        module = request.data.get('module', '').strip()
        assignee = request.data.get('assignee', '').strip()
        analysis_record_id = request.data.get('analysis_record_id')

        if not space_id:
            return _build_error_response('请提供项目 ID (space_id)')
        if not sprint_id:
            return _build_error_response('请提供迭代 ID (sprint_id)')
        if not title:
            return _build_error_response('请提供 Bug 标题 (title)')

        from .yunxiao_client import YunxiaoClient, YunxiaoAPIError
        client_kwargs = {"token": token, "organization_id": organization_id}
        if domain:
            client_kwargs["domain"] = domain
        client = YunxiaoClient(**client_kwargs)

        # 解析指派人ID (支持直接传递userId或用户名)
        resolved_assignee = None
        resolved_verifier = None
        members_cache = None
        
        def is_user_id_format(value):
            """检查是否为云效用户ID格式 (24位十六进制)"""
            if not value:
                return False
            value = str(value)
            return len(value) == 24 and all(c in '0123456789abcdef' for c in value.lower())
        
        def get_members():
            nonlocal members_cache
            if members_cache is None:
                members_cache = client.list_project_members(space_id)
            return members_cache
        
        if assignee:
            # 如果已经是userId格式，直接使用
            if is_user_id_format(assignee):
                resolved_assignee = assignee
            else:
                # 否则查找对应的用户ID
                try:
                    members = get_members()
                    for m in members:
                        if m.get("userName") == assignee or m.get("userId") == assignee:
                            resolved_assignee = m["userId"]
                            break
                    if not resolved_assignee:
                        logger.warning(f"[create_bug_to_yunxiao] 未找到指派人 '{assignee}', 使用默认值")
                except Exception as e:
                    logger.warning(f"[create_bug_to_yunxiao] 解析指派人失败: {e}")
        
        # 通过云效API获取当前Token对应的用户ID，作为验证者 (verifier)
        if not resolved_verifier:
            try:
                current_user = client.get_current_user()
                if current_user and current_user.get("id"):
                    resolved_verifier = str(current_user["id"])
                    logger.info(f"[create_bug_to_yunxiao] 根据Token获取到验证者userId: {resolved_verifier}, name: {current_user.get('name')}")
                else:
                    logger.warning("[create_bug_to_yunxiao] 无法通过Token获取当前用户信息，验证者将使用fallback")
            except Exception as e:
                logger.warning(f"[create_bug_to_yunxiao] 获取Token当前用户异常: {e}")

        # 验证者fallback: Token无法获取用户时，取项目第一个成员
        if not resolved_verifier:
            try:
                members = get_members()
                if members:
                    resolved_verifier = members[0]["userId"]
                    logger.info(f"[create_bug_to_yunxiao] 验证者fallback到项目第一个成员: {resolved_verifier}")
            except Exception:
                pass

        # 确保至少有一个指派人 (assignee fallback)
        if not resolved_assignee:
            try:
                members = get_members()
                if members:
                    resolved_assignee = members[0]["userId"]
            except Exception:
                pass

        # 构建自定义字段 (仅附加非严重程度/优先级的自定义字段，因为这两个已通过severity/priority参数处理)
        custom_fields = {}

        # 调试日志：查看标签参数
        logger.info(f"[create_bug_to_yunxiao] module参数: '{module}', 长度: {len(module)}")
        
        # 推送到云效 (severity/priority 会自动解析为标识符)
        result = client.create_bug(
            space_id=space_id,
            subject=title,
            description=desc,
            sprint_id=sprint_id,
            severity=severity,
            priority=priority,
            assignee=resolved_assignee,
            verifier=resolved_verifier,
            custom_fields=custom_fields,
            labels=[module] if module else None,
        )

        # 从响应中提取 workitem ID 和序列号
        # 云效API可能返回 {data: {...}} 或直接返回 {...}
        workitem_id = ""
        serial_number = ""
        logger.info(f"[API:create_bug_to_yunxiao] 云效原始返回结果: {json.dumps(result, ensure_ascii=False)[:1500]}")
        
        def _extract_value_recursive(data_dict, target_keys, depth=0):
            """递归从数据字典中提取目标字段值，处理嵌套的data/result等结构"""
            if depth > 5 or not isinstance(data_dict, dict):
                return ""
            # 打印键名帮助调试（仅第一层）
            if depth == 0:
                logger.info(f"[API:create_bug_to_yunxiao] 返回数据字段列表: {list(data_dict.keys())}")
            # 直接在当前层级查找
            for key in target_keys:
                val = data_dict.get(key)
                if val:
                    val_str = str(val).strip()
                    if val_str:
                        logger.info(f"[API:create_bug_to_yunxiao] 从字段 '{key}' (depth={depth}) 提取到值: {val_str}")
                        return val_str
            # 递归查找嵌套的data/result/value字段
            for nested_key in ["data", "result", "value", "workitem", "item"]:
                nested_val = data_dict.get(nested_key)
                if isinstance(nested_val, dict):
                    found = _extract_value_recursive(nested_val, target_keys, depth + 1)
                    if found:
                        return found
            return ""
        
        if isinstance(result, dict):
            # 提取workitem ID
            workitem_id = _extract_value_recursive(result, ["id", "identifier", "workitemId", "workitem_id"])
            # 提取serialNumber（优先取这个字段！）
            serial_number = _extract_value_recursive(result, ["serialNumber", "serial_number", "serial", "showName", "key"])

        # 如果创建成功但serialNumber为空，尝试调用get_workitem获取详情来提取serialNumber
        if workitem_id and not serial_number:
            try:
                logger.info(f"[API:create_bug_to_yunxiao] 创建响应中无serialNumber，尝试查询workitem详情: workitem_id={workitem_id}")
                workitem_detail = client.get_workitem(workitem_id, space_id=space_id)
                logger.info(f"[API:create_bug_to_yunxiao] workitem详情: {json.dumps(workitem_detail, ensure_ascii=False)[:1500]}")
                serial_number = _extract_value_recursive(workitem_detail, ["serialNumber", "serial_number", "serial", "showName", "key"])
            except Exception as e:
                logger.warning(f"[API:create_bug_to_yunxiao] 获取workitem详情失败: {e}")

        # 如果序列号为空但有ID，使用ID作为备选显示
        if not serial_number and workitem_id:
            serial_number = workitem_id

        logger.info(f"[API:create_bug_to_yunxiao] 提取结果: workitem_id={workitem_id}, serial_number={serial_number}")

        # 上传附件（如果有）
        uploaded_attachments = []
        if workitem_id and request.FILES:
            logger.info(f"[API:create_bug_to_yunxiao] 开始上传 {len(request.FILES)} 个附件")
            for file_key in request.FILES:
                uploaded_file = request.FILES[file_key]
                try:
                    file_content = uploaded_file.read()
                    filename = uploaded_file.name
                    content_type = uploaded_file.content_type or "application/octet-stream"
                    
                    logger.info(f"[API:create_bug_to_yunxiao] 上传附件: {filename}, 大小: {len(file_content)} bytes, 类型: {content_type}")
                    attach_result = client.upload_attachment(
                        workitem_id=workitem_id,
                        file_content=file_content,
                        filename=filename,
                        content_type=content_type
                    )
                    uploaded_attachments.append({
                        "name": filename,
                        "size": len(file_content),
                        "id": attach_result.get("id", ""),
                        "url": attach_result.get("url", ""),
                        "is_image": content_type.startswith("image/"),
                    })
                    
                    logger.info(f"[API:create_bug_to_yunxiao] 附件 {filename} 上传成功: id={attach_result.get('id')}")
                except Exception as e:
                    logger.error(f"[API:create_bug_to_yunxiao] 上传附件 {uploaded_file.name} 失败: {e}")
                    # 单个附件上传失败不影响主流程，继续上传其他附件
        
        # 描述使用用户原始输入（图片/视频/文档都已作为附件上传，无需在描述中追加链接）
        final_desc = _clean_bug_description(desc)

        # 构建本地存储数据
        # 直接从 request 获取 token_id
        request_token_id = request.data.get('token_id')
        # 如果module是标签ID（24位hex），反查标签名称用于本地存储显示
        module_name = module
        if module and space_id:
            module_name = client._resolve_label_name(space_id, module)
        # 获取当前用户名作为创建人
        creator_name = request.user.username if request.user.is_authenticated else 'system'
        bug_data = {
            "token_id": request_token_id,
            "title": title,
            "desc": final_desc,
            "severity": severity,
            "priority": priority,
            "status": status_val,
            "module": module_name,  # 存储标签名称用于显示
            "assignee": assignee,
            "space_id": space_id,
            "sprint_id": sprint_id,
            "creator": creator_name,
            "attachments": uploaded_attachments,
        }

        # 创建 BugSyncItem 记录
        from .models import BugSyncItem
        sync_item = BugSyncItem.objects.create(
            analysis_record_id=analysis_record_id if analysis_record_id else None,
            yunxiao_workitem_id=workitem_id,
            yunxiao_serial_number=serial_number,
            local_data=bug_data,
            sync_status='synced' if workitem_id else 'pending',
            last_synced_at=timezone.now() if workitem_id else None,
        )

        elapsed = round((time.time() - start_time) * 1000)
        logger.info(f"[API:create_bug_to_yunxiao] 成功: workitem_id={workitem_id}, 耗时{elapsed}ms")

        return _build_api_response({
            'sync_item': sync_item.to_list_dict(),
            'workitem_id': workitem_id,
            'serial_number': serial_number,
            'yunxiao_result': result if not isinstance(result, (list, dict)) or len(str(result)) < 500 else str(result)[:500],
        }, f'Bug 创建成功并同步到云效 (耗时{elapsed}ms)')

    except YunxiaoAPIError as e:
        logger.error(f'[API:create_bug_to_yunxiao] 云效API错误: {e}')
        return _build_error_response(f'云效 API 错误: {str(e)[:300]}')
    except Exception as e:
        logger.error(f'[API:create_bug_to_yunxiao] 错误: {e}', exc_info=True)
        return _build_error_response(f'创建 Bug 失败: {str(e)[:300]}',
                                     code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_bug_to_yunxiao(request, sync_item_id):
    """
    更新 Bug 并同步到云效

    PUT参数:
        - token_id: 云效Token配置ID (推荐, 替代 token + organization_id)
        - title: Bug 标题
        - desc: Bug 描述
        - status: 状态
        - severity: 严重程度
        - priority: 优先级
        - module: 所属模块
        - assignee: 处理人

    返回:
        - 更新结果
    """
    start_time = time.time()
    try:
        client, err = _resolve_yunxiao_client(request)
        if err:
            return err

        from .yunxiao_client import DEFAULT_ORGANIZATION_ID
        token = client.token
        organization_id = DEFAULT_ORGANIZATION_ID
        domain = request.data.get('domain', '').strip()

        from .models import BugSyncItem
        sync_item = BugSyncItem.objects.filter(id=sync_item_id).first()
        if not sync_item:
            return _build_error_response(f'同步项不存在: id={sync_item_id}', code=status.HTTP_404_NOT_FOUND)

        workitem_id = sync_item.yunxiao_workitem_id
        if not workitem_id:
            return _build_error_response('该 Bug 尚未同步到云效，无法更新', code=status.HTTP_400_BAD_REQUEST)

        # 获取space_id用于标签解析
        local_data = sync_item.local_data or {}
        space_id = local_data.get('space_id', '')

        from .yunxiao_client import YunxiaoClient, YunxiaoAPIError
        client_kwargs = {"token": token, "organization_id": organization_id}
        if domain:
            client_kwargs["domain"] = domain
        client = YunxiaoClient(**client_kwargs)

        # 构建更新数据
        update_data = {}
        for field in ['title', 'desc', 'status', 'severity', 'priority', 'module', 'assignee']:
            val = request.data.get(field)
            if val is not None:
                update_data[field] = val

        # 解析指派人ID (支持直接传递userId或用户名)
        resolved_assignee = None
        assignee_val = update_data.get('assignee')
        
        def is_user_id_format(value):
            """检查是否为云效用户ID格式 (24位十六进制)"""
            if not value:
                return False
            value = str(value)
            return len(value) == 24 and all(c in '0123456789abcdef' for c in value.lower())
        
        if assignee_val:
            # 如果已经是userId格式，直接使用
            if is_user_id_format(assignee_val):
                resolved_assignee = assignee_val
            else:
                space_id = sync_item.local_data.get('space_id') if sync_item.local_data else None
                if space_id:
                    try:
                        members = client.list_project_members(space_id)
                        for m in members:
                            if m.get("userName") == assignee_val or m.get("userId") == assignee_val:
                                resolved_assignee = m["userId"]
                                break
                    except Exception:
                        pass

        # 构建自定义字段 (severity/priority 已通过参数传递，不需重复添加)
        custom_fields = {}

        # 状态直接传递，yunxiao_client会自动将中文名称解析为状态ID
        status_val = update_data.get('status')

        # 标签(labels)处理: module字段对应云效标签
        module_val = update_data.get('module', '').strip() if update_data.get('module') else ''
        # 如果传入的是标签ID（24位hex），反查标签名称用于本地存储显示
        module_name_for_storage = module_val
        if module_val and space_id:
            module_name_for_storage = client._resolve_label_name(space_id, module_val)
        labels_param = [module_val] if module_val else None

        # 转换为云效格式
        payload = client.update_workitem(
            workitem_id=workitem_id,
            subject=update_data.get('title'),
            description=update_data.get('desc'),
            status=status_val,  # 状态名称会自动解析为ID
            severity=update_data.get('severity'),
            priority=update_data.get('priority'),
            assignee=resolved_assignee,
            labels=labels_param,
            space_id=space_id if space_id else None,
            custom_fields=custom_fields if custom_fields else None,
        )

        # 更新本地记录
        if 'title' in update_data:
            local_data['title'] = update_data['title']
        if 'desc' in update_data:
            local_data['desc'] = _clean_bug_description(update_data['desc'])
        if 'status' in update_data:
            local_data['status'] = update_data['status']
        if 'severity' in update_data:
            local_data['severity'] = update_data['severity']
        if 'priority' in update_data:
            local_data['priority'] = update_data['priority']
        if 'module' in update_data:
            local_data['module'] = module_name_for_storage  # 存储名称而非ID，用于列表显示
            # 同步更新labels数组
            if module_val:
                local_data['labels'] = [module_val]

        sync_item.local_data = local_data
        sync_item.sync_status = 'synced'
        sync_item.last_synced_at = timezone.now()
        sync_item.save(update_fields=['local_data', 'sync_status', 'last_synced_at', 'updated_at'])

        elapsed = round((time.time() - start_time) * 1000)
        logger.info(f"[API:update_bug_to_yunxiao] 成功: workitem_id={workitem_id}, 耗时{elapsed}ms")

        return _build_api_response({
            'sync_item': sync_item.to_list_dict(),
            'yunxiao_result': str(payload)[:500] if payload else {},
        }, f'Bug 更新成功并同步到云效 (耗时{elapsed}ms)')

    except YunxiaoAPIError as e:
        # 标记为失败
        try:
            from .models import BugSyncItem
            sync_item = BugSyncItem.objects.filter(id=sync_item_id).first()
            if sync_item:
                sync_item.sync_status = 'failed'
                sync_item.save(update_fields=['sync_status', 'updated_at'])
        except Exception:
            pass
        return _build_error_response(f'云效 API 错误: {e}')
    except Exception as e:
        logger.error(f'[API:update_bug_to_yunxiao] 错误: {e}', exc_info=True)
        return _build_error_response(f'更新 Bug 失败: {str(e)}',
                                     code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def quick_change_bug_status(request, sync_item_id):
    """
    快捷修改Bug状态，支持上传截图作为评论

    POST参数:
        - token_id: 云效Token配置ID
        - status: 新状态（已验证/已关闭/再次打开）
        - screenshot: 截图文件（可选，multipart/form-data）
        - comment: 评论文本（可选）

    返回:
        - 更新结果
    """
    start_time = time.time()
    try:
        client, err = _resolve_yunxiao_client(request)
        if err:
            return err

        from .yunxiao_client import DEFAULT_ORGANIZATION_ID, YunxiaoClient, YunxiaoAPIError
        token = client.token
        organization_id = DEFAULT_ORGANIZATION_ID
        domain = request.data.get('domain', '').strip()

        from .models import BugSyncItem
        sync_item = BugSyncItem.objects.filter(id=sync_item_id).first()
        if not sync_item:
            return _build_error_response(f'同步项不存在: id={sync_item_id}', code=status.HTTP_404_NOT_FOUND)

        workitem_id = sync_item.yunxiao_workitem_id
        if not workitem_id:
            return _build_error_response('该 Bug 尚未同步到云效，无法更新', code=status.HTTP_400_BAD_REQUEST)

        local_data = sync_item.local_data or {}
        space_id = local_data.get('space_id', '')

        client_kwargs = {"token": token, "organization_id": organization_id}
        if domain:
            client_kwargs["domain"] = domain
        client = YunxiaoClient(**client_kwargs)

        # 1. 更新状态
        new_status = request.data.get('status', '').strip()
        if not new_status:
            return _build_error_response('状态不能为空', code=status.HTTP_400_BAD_REQUEST)

        client.update_bug_status(workitem_id=workitem_id, status=new_status, space_id=space_id if space_id else None)

        # 2. 如果有截图，上传附件并添加评论
        screenshot = request.FILES.get('screenshot')
        comment_text = request.data.get('comment', '').strip()

        if screenshot:
            # 读取文件内容
            file_content = screenshot.read()
            filename = screenshot.name
            content_type = screenshot.content_type or 'image/png'

            # 上传附件
            attach_result = client.upload_attachment(
                workitem_id=workitem_id,
                file_content=file_content,
                filename=filename,
                content_type=content_type,
            )

            # 构建评论内容，用HTML嵌入图片（云效评论支持HTML不支持markdown图片）
            embed_html = attach_result.get('embedHtml', '')
            embed_url = attach_result.get('embedUrl', '')
            comment_parts = []
            if comment_text:
                comment_parts.append(comment_text)
            if embed_html:
                comment_parts.append(embed_html)
            elif embed_url:
                comment_parts.append(f'<img src="{embed_url}"/>')

            full_comment = '<br/><br/>'.join(comment_parts)
            try:
                client.add_comment(workitem_id=workitem_id, content=full_comment)
            except Exception as e:
                logger.warning(f'[quick_change_bug_status] 添加评论失败（不影响状态更新）: {e}')
        elif comment_text:
            # 没有截图但有评论
            full_comment = comment_text
            try:
                client.add_comment(workitem_id=workitem_id, content=full_comment)
            except Exception as e:
                logger.warning(f'[quick_change_bug_status] 添加评论失败（不影响状态更新）: {e}')

        # 3. 更新本地记录
        local_data['status'] = new_status
        sync_item.local_data = local_data
        sync_item.sync_status = 'synced'
        sync_item.last_synced_at = timezone.now()
        sync_item.save(update_fields=['local_data', 'sync_status', 'last_synced_at', 'updated_at'])

        elapsed = round((time.time() - start_time) * 1000)
        logger.info(f"[API:quick_change_bug_status] 成功: workitem_id={workitem_id}, status={new_status}, 截图={'有' if screenshot else '无'}, 耗时{elapsed}ms")

        return _build_api_response({
            'sync_item': sync_item.to_list_dict(),
        }, f'状态已更新为「{new_status}」{"并上传截图" if screenshot else ""} (耗时{elapsed}ms)')

    except YunxiaoAPIError as e:
        try:
            from .models import BugSyncItem
            sync_item = BugSyncItem.objects.filter(id=sync_item_id).first()
            if sync_item:
                sync_item.sync_status = 'failed'
                sync_item.save(update_fields=['sync_status', 'updated_at'])
        except Exception:
            pass
        return _build_error_response(f'云效 API 错误: {e}')
    except Exception as e:
        logger.error(f'[API:quick_change_bug_status] 错误: {e}', exc_info=True)
        return _build_error_response(f'快捷改状态失败: {str(e)}',
                                     code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def resync_bug_item(request, sync_item_id):
    """
    重新同步单个Bug项：从云效获取最新信息，补全serialNumber等字段
    
    POST参数: (通过token_id自动选择token)
    """
    start_time = time.time()
    try:
        from .models import BugSyncItem, YunxiaoToken
        
        sync_item = BugSyncItem.objects.filter(id=sync_item_id).first()
        if not sync_item:
            return _build_error_response(f'同步项不存在 (id={sync_item_id})', code=status.HTTP_404_NOT_FOUND)
        
        workitem_id = sync_item.yunxiao_workitem_id
        if not workitem_id:
            return _build_error_response('该记录尚未同步到云效，无workitem_id')
        
        # 直接使用任意一个启用的token（BugSyncItem不存储token_id）
        token_obj = YunxiaoToken.objects.filter(is_active=True).first()
        
        if not token_obj:
            return _build_error_response('没有可用的云效Token配置，请先在Token管理中添加')
        
        from .yunxiao_client import YunxiaoClient
        client = YunxiaoClient(
            token=token_obj.token,
            organization_id='68d8e1cb66aca23eccbd5e0a'
        )
        
        # 获取workitem详情
        workitem_detail = client.get_workitem(workitem_id)
        logger.info(f"[API:resync_bug_item] workitem详情: {json.dumps(workitem_detail, ensure_ascii=False)[:1500]}")
        
        # 引入严重程度标准化函数和标签提取工具
        from .yunxiao_client import YunxiaoClient as YC, _pick_module_name_from_labels
        
        def _extract_value_recursive(data_dict, target_keys, depth=0):
            """递归提取简单字符串值"""
            if depth > 8 or not isinstance(data_dict, dict):
                return ""
            
            def _try_extract(val):
                """尝试从值中提取字符串"""
                if val is None:
                    return ""
                if isinstance(val, (str, int, float)):
                    val_str = str(val).strip()
                    if val_str:
                        return val_str
                elif isinstance(val, dict):
                    # 如果是对象，尝试从中提取name/value/displayName等
                    for sub_key in ["name", "value", "displayName", "label", "id", "identifier", "key"]:
                        sub_val = val.get(sub_key)
                        if sub_val is not None:
                            sub_str = str(sub_val).strip()
                            if sub_str and len(sub_str) < 100:
                                return sub_str
                elif isinstance(val, list) and len(val) > 0:
                    for item in val:
                        result = _try_extract(item)
                        if result:
                            return result
                return ""
            
            def _extract_from_field_arrays(data, keys):
                """从fieldValues数组中提取值"""
                if not isinstance(data, dict):
                    return ""
                for arr_key in ["fieldValues", "customFieldValues", "fields", "workitemFields"]:
                    fields_arr = data.get(arr_key)
                    if isinstance(fields_arr, list):
                        for field in fields_arr:
                            if not isinstance(field, dict):
                                continue
                            field_key = str(field.get("fieldKey") or field.get("key") or field.get("fieldIdentifier") or "").lower()
                            for target_key in keys:
                                if target_key.lower() in field_key:
                                    val = field.get("value") or field.get("fieldValue") or field.get("name") or field.get("displayValue")
                                    result = _try_extract(val)
                                    if result:
                                        return result
                return ""
            
            # 0. 先从字段数组中提取
            result = _extract_from_field_arrays(data_dict, target_keys)
            if result:
                return result
            
            # 1. 直接在当前层级查找
            for key in target_keys:
                val = data_dict.get(key)
                result = _try_extract(val)
                if result:
                    return result
            
            # 2. 查找常见的嵌套字段
            common_nested = ["data", "result", "value", "workitem", "item", "field", "fields", "workItem"]
            for nested_key in common_nested:
                nested_val = data_dict.get(nested_key)
                if isinstance(nested_val, dict):
                    result = _extract_from_field_arrays(nested_val, target_keys)
                    if result:
                        return result
                    found = _extract_value_recursive(nested_val, target_keys, depth + 1)
                    if found:
                        return found
                elif isinstance(nested_val, list):
                    for item in nested_val:
                        if isinstance(item, dict):
                            result = _extract_from_field_arrays(item, target_keys)
                            if result:
                                return result
                            found = _extract_value_recursive(item, target_keys, depth + 1)
                            if found:
                                return found
            
            # 3. 深度搜索（限制层级）
            if depth < 4:
                for key, val in data_dict.items():
                    if isinstance(val, dict):
                        result = _extract_from_field_arrays(val, target_keys)
                        if result:
                            return result
                        found = _extract_value_recursive(val, target_keys, depth + 1)
                        if found and len(found) < 100:
                            return found
            
            return ""
        
        def _extract_user_display(data_dict, target_keys, depth=0):
            """递归提取用户显示名称（处理人等），支持多种字段名和嵌套结构"""
            if depth > 8 or not isinstance(data_dict, dict):
                return ""
            
            def _try_extract_user(val):
                """尝试从各种格式的值中提取用户显示名"""
                if val is None:
                    return ""
                if isinstance(val, dict):
                    # 用户对象，优先提取displayName，然后name/userName
                    for name_key in ["displayName", "name", "userName", "nickName", "realName", "cnName", "email"]:
                        name_val = val.get(name_key)
                        if name_val and isinstance(name_val, str) and name_val.strip():
                            return name_val.strip()
                    # 如果没有显示名，尝试提取ID
                    for id_key in ["id", "userId", "identifier", "uniqueId"]:
                        id_val = val.get(id_key)
                        if id_val and str(id_val).strip():
                            return str(id_val).strip()
                elif isinstance(val, str) and val.strip():
                    return val.strip()
                elif isinstance(val, list) and len(val) > 0:
                    # 数组，取第一个用户
                    for item in val:
                        result = _try_extract_user(item)
                        if result:
                            return result
                return ""
            
            def _extract_from_field_arrays(data):
                """从fieldValues/customFieldValues数组中提取处理人"""
                if not isinstance(data, dict):
                    return ""
                # 查找字段数组
                for arr_key in ["fieldValues", "customFieldValues", "fields", "workitemFields"]:
                    fields_arr = data.get(arr_key)
                    if isinstance(fields_arr, list):
                        for field in fields_arr:
                            if not isinstance(field, dict):
                                continue
                            field_key = field.get("fieldKey") or field.get("key") or field.get("fieldIdentifier") or ""
                            # 匹配处理人相关的fieldKey
                            assignee_keys = ["assignee", "assignTo", "assignedTo", "handler", "executor", "responsible", "owner",
                                          "currentHandler", "processingPerson", "worker", "dealPerson"]
                            if any(ak.lower() in str(field_key).lower() for ak in assignee_keys):
                                val = field.get("value") or field.get("fieldValue") or field.get("userValue")
                                result = _try_extract_user(val)
                                if result:
                                    logger.info(f"[resync] 从字段数组 '{arr_key}' 的 '{field_key}' 提取到用户: {result}")
                                    return result
                return ""
            
            # 0. 先尝试从字段数组中提取（云效常用格式）
            result = _extract_from_field_arrays(data_dict)
            if result:
                return result
            
            # 1. 直接在当前层级查找目标字段
            for key in target_keys:
                val = data_dict.get(key)
                result = _try_extract_user(val)
                if result:
                    logger.info(f"[resync] 从字段 '{key}' (depth={depth}) 提取到用户: {result}")
                    return result
            
            # 2. 查找常见的嵌套字段
            common_nested = ["data", "result", "value", "workitem", "item", "field", "fields", "workItem"]
            for nested_key in common_nested:
                nested_val = data_dict.get(nested_key)
                if isinstance(nested_val, dict):
                    # 先尝试从嵌套的dict中提取字段数组
                    result = _extract_from_field_arrays(nested_val)
                    if result:
                        return result
                    result = _extract_user_display(nested_val, target_keys, depth + 1)
                    if result:
                        return result
                elif isinstance(nested_val, list):
                    for item in nested_val:
                        if isinstance(item, dict):
                            result = _extract_from_field_arrays(item)
                            if result:
                                return result
                            result = _extract_user_display(item, target_keys, depth + 1)
                            if result:
                                return result
            
            # 3. 递归遍历所有dict类型的值（深度搜索）
            if depth < 5:
                for key, val in data_dict.items():
                    if isinstance(val, dict):
                        result = _extract_from_field_arrays(val)
                        if result:
                            return result
                        result = _extract_user_display(val, target_keys, depth + 1)
                        if result and len(result) < 100:  # 避免返回过长的非用户名字符串
                            return result
                    elif isinstance(val, list) and len(val) > 0 and len(val) < 20:
                        for item in val:
                            if isinstance(item, dict):
                                result = _extract_from_field_arrays(item)
                                if result:
                                    return result
                                result = _extract_user_display(item, target_keys, depth + 1)
                                if result and len(result) < 100:
                                    return result
            
            return ""
        
        # 提取各字段 - 使用直接结构解析，更可靠
        serial_number = workitem_detail.get("serialNumber") or ""
        
        # 状态：从status对象取name
        status_obj = workitem_detail.get("status") or {}
        if isinstance(status_obj, dict):
            remote_status = status_obj.get("name") or status_obj.get("displayName") or ""
        else:
            remote_status = str(status_obj).strip() if status_obj else ""
        
        # space_id：从space对象取id（不是name！）
        space_obj = workitem_detail.get("space") or {}
        if isinstance(space_obj, dict):
            remote_space_id = space_obj.get("id") or space_obj.get("spaceId") or ""
        else:
            remote_space_id = str(space_obj).strip() if space_obj else ""
        
        # 手动收集状态映射到客户端缓存
        if remote_space_id:
            client._collect_statuses_from_workitems(remote_space_id, [workitem_detail])
        
        # 处理人：从assignedTo对象取userId（与创建时保持一致）
        assignee_obj = workitem_detail.get("assignedTo") or {}
        if isinstance(assignee_obj, dict):
            remote_assignee = assignee_obj.get("id") or assignee_obj.get("userId") or assignee_obj.get("name") or assignee_obj.get("displayName") or assignee_obj.get("userName") or ""
        else:
            remote_assignee = str(assignee_obj).strip() if assignee_obj else ""
        
        # 从customFieldValues数组中提取优先级和严重程度
        remote_priority = ""
        remote_severity_raw = ""
        custom_fields_arr = workitem_detail.get("customFieldValues") or []
        if isinstance(custom_fields_arr, list):
            for cf in custom_fields_arr:
                if not isinstance(cf, dict):
                    continue
                field_id = str(cf.get("fieldId") or cf.get("fieldKey") or "").lower()
                field_name = str(cf.get("fieldName") or "").lower()
                values_arr = cf.get("values") or []
                display_val = ""
                identifier_val = ""
                if isinstance(values_arr, list) and len(values_arr) > 0:
                    first_val = values_arr[0]
                    if isinstance(first_val, dict):
                        display_val = first_val.get("displayValue") or first_val.get("name") or ""
                        identifier_val = first_val.get("identifier") or first_val.get("id") or ""
                    elif isinstance(first_val, (str, int)):
                        display_val = str(first_val)
                
                if "priority" in field_id or "优先级" in field_name:
                    remote_priority = display_val or identifier_val
                elif "serious" in field_id or "severity" in field_id or "严重程度" in field_name:
                    remote_severity_raw = display_val or identifier_val
        
        # 备用：如果customFieldValues没取到，用通用递归
        if not remote_priority:
            remote_priority = _extract_value_recursive(workitem_detail, ["priority", "priorityName", "priorityLabel"])
        if not remote_severity_raw:
            remote_severity_raw = _extract_value_recursive(workitem_detail, ["seriousLevel", "severity", "severityName"])
        
        # 标准化严重程度为本地P等级格式
        remote_severity = YC.normalize_severity_from_yunxiao(remote_severity_raw) if remote_severity_raw else ""
        
        # 提取云效标签(labels)用于更新所属模块
        remote_labels = []  # 标签名称列表（用于显示）
        remote_label_ids = []  # 标签ID列表
        try:
            raw_labels = workitem_detail.get("labels") or []
            if isinstance(raw_labels, list):
                for item in raw_labels:
                    if isinstance(item, dict):
                        lb_id = item.get("id") or item.get("labelId") or ""
                        lb_name = item.get("name") or item.get("displayName") or item.get("labelName") or ""
                        if lb_id:
                            remote_label_ids.append(str(lb_id))
                        if lb_name:
                            remote_labels.append(str(lb_name).strip())
                    elif isinstance(item, str) and item.strip():
                        remote_labels.append(item.strip())
        except Exception as e:
            logger.warning(f"[API:resync_bug_item] 提取labels异常: {e}")
        
        # 通过标签列表API，用ID反查正确的标签名称（修正历史错误数据）
        remote_module = ""
        if remote_space_id:
            try:
                # 构建ID->名称映射，优先用标签列表API返回的名称
                all_labels = client.list_project_labels(remote_space_id)
                id_to_name = {}
                for lb in all_labels:
                    lb_id = str(lb.get("id") or lb.get("labelId") or "")
                    lb_name = str(lb.get("name") or lb.get("labelName") or "")
                    if lb_id and lb_name:
                        id_to_name[lb_id] = lb_name
                
                # 用标签ID反查正确名称，修正remote_labels
                corrected_labels = []
                for lb_id in remote_label_ids:
                    if lb_id in id_to_name:
                        corrected_labels.append(id_to_name[lb_id])
                    else:
                        # ID在列表中找不到，保留原始name
                        pass
                # 如果通过ID找到了名称，优先使用修正后的列表
                if corrected_labels:
                    remote_labels = corrected_labels
                
                remote_module = _pick_module_name_from_labels(remote_labels) if remote_labels else ""
            except Exception as e:
                logger.warning(f"[API:resync_bug_item] 标签ID反查名称异常: {e}")
                remote_module = _pick_module_name_from_labels(remote_labels) if remote_labels else ""
        else:
            remote_module = _pick_module_name_from_labels(remote_labels) if remote_labels else ""
        
        logger.info(f"[API:resync_bug_item] 提取字段: serial={serial_number}, status={remote_status}, priority={remote_priority}, "
                    f"severity_raw={remote_severity_raw} -> severity={remote_severity}, assignee={remote_assignee}, "
                    f"space_id={remote_space_id}, labels={remote_labels}, module={remote_module}")
        
        # 更新local_data（保留原有数据，只更新有值的字段）
        local_data = sync_item.local_data or {}
        updated_fields_count = 0
        if serial_number and not sync_item.yunxiao_serial_number:
            sync_item.yunxiao_serial_number = serial_number
            updated_fields_count += 1
        if remote_status and remote_status != local_data.get("status"):
            local_data["status"] = remote_status
            updated_fields_count += 1
        if remote_priority and remote_priority != local_data.get("priority"):
            local_data["priority"] = remote_priority
            updated_fields_count += 1
        if remote_severity and remote_severity != local_data.get("severity"):
            local_data["severity"] = remote_severity
            updated_fields_count += 1
        if remote_assignee and remote_assignee != local_data.get("assignee"):
            local_data["assignee"] = remote_assignee
            updated_fields_count += 1
        if remote_module and remote_module != local_data.get("module"):
            local_data["module"] = remote_module
            updated_fields_count += 1
        if remote_labels:
            local_data["labels"] = remote_labels
        # 补全space_id（针对历史数据可能缺失的情况）
        if remote_space_id and not local_data.get("space_id"):
            local_data["space_id"] = remote_space_id
            updated_fields_count += 1
        
        # 更新记录
        update_fields = ['updated_at', 'local_data']
        if serial_number:
            update_fields.append('yunxiao_serial_number')
            sync_item.yunxiao_serial_number = serial_number
        
        # 更新状态为已同步
        if sync_item.sync_status != 'synced':
            sync_item.sync_status = 'synced'
            update_fields.append('sync_status')
        
        sync_item.local_data = local_data
        sync_item.last_synced_at = timezone.now()
        update_fields.append('last_synced_at')
        sync_item.remote_data_cache = workitem_detail
        update_fields.append('remote_data_cache')
        
        sync_item.save(update_fields=update_fields)
        
        elapsed = round((time.time() - start_time) * 1000)
        update_msg_parts = []
        if serial_number:
            update_msg_parts.append(f"编号:{serial_number}")
        if remote_status:
            update_msg_parts.append(f"状态:{remote_status}")
        if remote_severity:
            update_msg_parts.append(f"严重程度:{remote_severity}")
        if remote_module:
            update_msg_parts.append(f"模块:{remote_module}")
        if remote_assignee:
            update_msg_parts.append(f"处理人:{remote_assignee}")
        logger.info(f"[API:resync_bug_item] 成功: workitem_id={workitem_id}, 更新字段: {update_msg_parts}, 耗时{elapsed}ms")
        
        msg = f'重新同步成功 (耗时{elapsed}ms)'
        if update_msg_parts:
            msg += '，更新: ' + ', '.join(update_msg_parts)
        
        return _build_api_response({
            'sync_item': sync_item.to_list_dict(),
            'serial_number': serial_number,
            'updated_fields': {
                'status': remote_status,
                'assignee': remote_assignee,
                'priority': remote_priority,
                'severity': remote_severity,
                'module': remote_module,
                'labels': remote_labels,
            }
        }, msg)
        
    except Exception as e:
        logger.error(f'[API:resync_bug_item] 错误: {e}', exc_info=True)
        return _build_error_response(f'重新同步失败: {str(e)}',
                                     code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def bug_sync_items(request):
    """
    获取 Bug 同步项列表

    GET参数:
        - analysis_record_id: 关联分析记录ID (可选)
        - sync_status: 同步状态过滤 (可选)
        - page: 页码 (默认1)
        - page_size: 每页数量 (默认20)
    """
    try:
        from .models import BugSyncItem
        queryset = BugSyncItem.objects.all().order_by('-created_at')

        analysis_record_id = request.query_params.get('analysis_record_id')
        if analysis_record_id:
            queryset = queryset.filter(analysis_record_id=analysis_record_id)

        sync_status = request.query_params.get('sync_status')
        if sync_status:
            queryset = queryset.filter(sync_status=sync_status)

        page = max(int(request.query_params.get('page', 1)), 1)
        page_size = min(int(request.query_params.get('page_size', 20)), 100)
        start = (page - 1) * page_size
        end = start + page_size

        total = queryset.count()
        items = queryset[start:end]

        items_data = [item.to_list_dict() for item in items]

        return _build_api_response({
            'items': items_data,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': max((total + page_size - 1) // page_size, 1),
        })

    except Exception as e:
        logger.error(f'[API:bug_sync_items] 错误: {e}', exc_info=True)
        return _build_error_response(f'获取同步项列表失败: {str(e)}',
                                     code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def poll_remote_status(request):
    """
    轮询云效 Bug 状态变更并更新本地 (反向同步)

    GET参数:
        - token: 云效个人访问令牌 (必填)
        - organization_id: 组织 ID (中心版必填)
        - domain: API 域名 (可选)
        - sync_item_id: 单个同步项ID (可选，不填则批量检查)
        - analysis_record_id: 关联分析记录ID (可选)

    返回:
        - 变更列表 + 更新统计
    """
    try:
        token = request.query_params.get('token', '').strip()
        organization_id = request.query_params.get('organization_id', '').strip()
        domain = request.query_params.get('domain', '').strip()
        sync_item_id = request.query_params.get('sync_item_id')
        analysis_record_id = request.query_params.get('analysis_record_id')

        if not token:
            return _build_error_response('请提供云效访问令牌 (token)')

        from .yunxiao_client import YunxiaoClient, YunxiaoAPIError
        from .models import BugSyncItem
        client_kwargs = {"token": token, "organization_id": organization_id}
        if domain:
            client_kwargs["domain"] = domain
        client = YunxiaoClient(**client_kwargs)

        # 确定要检查的同步项
        if sync_item_id:
            sync_items = BugSyncItem.objects.filter(id=sync_item_id).exclude(yunxiao_workitem_id='')
        elif analysis_record_id:
            sync_items = BugSyncItem.objects.filter(analysis_record_id=analysis_record_id).exclude(yunxiao_workitem_id='')
        else:
            sync_items = BugSyncItem.objects.exclude(yunxiao_workitem_id='').order_by('-updated_at')[:100]

        changes = []
        update_count = 0
        error_count = 0

        for item in sync_items:
            try:
                remote_data = client.get_workitem(item.yunxiao_workitem_id)
                if not remote_data or isinstance(remote_data, list):
                    remote_data = remote_data[0] if isinstance(remote_data, list) and remote_data else {}

                # 提取远端状态和space_id，收集状态映射
                remote_status = ""
                if isinstance(remote_data, dict):
                    remote_status = str(remote_data.get("status", "") or "")
                    # 提取space_id收集状态缓存
                    space_obj = remote_data.get("space") or {}
                    if isinstance(space_obj, dict):
                        rid = space_obj.get("id") or space_obj.get("spaceId") or ""
                        if rid:
                            client._collect_statuses_from_workitems(rid, [remote_data])

                # 对比本地
                local_data = item.local_data or {}
                local_status = str(local_data.get("status", "") or "")

                if remote_status and remote_status != local_status:
                    # 检测到状态变更
                    local_data['status'] = remote_status
                    item.local_data = local_data
                    item.remote_data_cache = remote_data
                    item.sync_status = 'synced'
                    item.last_synced_at = timezone.now()
                    item.last_remote_check_at = timezone.now()
                    item.save()

                    changes.append({
                        'id': item.id,
                        'yunxiao_workitem_id': item.yunxiao_workitem_id,
                        'title': local_data.get('title', ''),
                        'old_status': local_status,
                        'new_status': remote_status,
                    })
                    update_count += 1
                else:
                    # 无变更，只更新检查时间
                    item.last_remote_check_at = timezone.now()
                    item.remote_data_cache = remote_data
                    item.save(update_fields=['last_remote_check_at', 'remote_data_cache'])

            except YunxiaoAPIError as e:
                logger.warning(f"[API:poll_remote_status] workitem_id={item.yunxiao_workitem_id} 获取失败: {e}")
                error_count += 1
            except Exception as e:
                logger.warning(f"[API:poll_remote_status] workitem_id={item.yunxiao_workitem_id} 异常: {e}")
                error_count += 1

        logger.info(f"[API:poll_remote_status] 检查完成: 共{len(list(sync_items))}项, 更新{update_count}项, 错误{error_count}项")

        return _build_api_response({
            'total_checked': len(list(sync_items)),
            'updated_count': update_count,
            'error_count': error_count,
            'changes': changes,
        }, f'远程状态检查完成: {update_count} 项更新')

    except YunxiaoAPIError as e:
        return _build_error_response(f'云效 API 错误: {e}')
    except Exception as e:
        logger.error(f'[API:poll_remote_status] 错误: {e}', exc_info=True)
        return _build_error_response(f'轮询远程状态失败: {str(e)}',
                                     code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_bug_sync_item(request, sync_item_id):
    """
    删除 Bug 同步项 (本地删除，不影响云效数据)
    """
    try:
        from .models import BugSyncItem
        sync_item = BugSyncItem.objects.filter(id=sync_item_id).first()
        if not sync_item:
            return _build_error_response(f'同步项不存在: id={sync_item_id}', code=status.HTTP_404_NOT_FOUND)

        sync_item.delete()
        return _build_api_response({}, f'同步项 id={sync_item_id} 已删除')

    except Exception as e:
        logger.error(f'[API:delete_bug_sync_item] 错误: {e}', exc_info=True)
        return _build_error_response(f'删除失败: {str(e)}',
                                     code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def yunxiao_sync_log(request, record_id):
    """
    获取云效同步数据的详细字段信息（用于诊断）

    返回:
        - first_bug_fields: 第一条Bug的所有字段名和值
        - all_custom_field_keys: 所有Bug的custom_fields字段名合集
        - sample_bugs: 前10条Bug的关键字段信息（id, title, created, custom_fields）
        - field_stats: 各字段的填充率统计
    """
    try:
        if not _DB_RECORDS_AVAILABLE:
            return _build_error_response('历史记录功能暂不可用', code=status.HTTP_503_SERVICE_UNAVAILABLE)

        # 支持所有记录类型，不再限制只查询云效同步记录
        record = BugAnalysisRecord.objects.filter(id=record_id).first()
        if not record:
            return _build_error_response(f'分析记录不存在: id={record_id}', code=status.HTTP_404_NOT_FOUND)

        raw_bugs = record.raw_bugs or []
        if not raw_bugs:
            return _build_api_response({
                'message': '该记录无原始Bug数据',
                'first_bug_fields': {},
                'all_custom_field_keys': [],
                'sample_bugs': [],
                'field_stats': {},
            })

        # 第一条Bug的所有字段名和值
        first_bug = raw_bugs[0] if raw_bugs else {}
        # 复制并截断 _raw_yunxiao 避免过大
        first_bug_fields = dict(first_bug)
        if '_raw_yunxiao' in first_bug_fields:
            raw_yunxiao = first_bug_fields['_raw_yunxiao']
            if isinstance(raw_yunxiao, dict):
                first_bug_fields['_raw_yunxiao'] = {k: str(v)[:500] for k, v in list(raw_yunxiao.items())[:30]}

        # 提取第一条Bug原始数据中的所有字段名（用于诊断字段名匹配）
        first_bug_raw_keys = []
        raw_yunxiao_data = first_bug.get('_raw_yunxiao', {})
        if isinstance(raw_yunxiao_data, dict):
            first_bug_raw_keys = sorted(list(raw_yunxiao_data.keys()))

        # 所有Bug的custom_fields字段名合集
        all_custom_field_keys = set()
        for bug in raw_bugs:
            cf = bug.get('custom_fields', {})
            if cf and isinstance(cf, dict):
                all_custom_field_keys.update(cf.keys())
        all_custom_field_keys = sorted(list(all_custom_field_keys))

        # 前10条Bug的关键字段信息
        sample_bugs = []
        for i, bug in enumerate(raw_bugs[:10]):
            # 优先使用 serialNumber（云效编号），兼容历史数据回退到 _raw_yunxiao
            bug_sn = bug.get('serialNumber')
            if not bug_sn:
                raw = bug.get('_raw_yunxiao', {})
                bug_sn = raw.get('serialNumber') or raw.get('identifier') or raw.get('id')
            sample_bugs.append({
                'index': i + 1,
                'serialNumber': bug_sn,
                'title': bug.get('title', '')[:50],
                'created': bug.get('created'),
                'updated': bug.get('updated'),
                'creator': bug.get('creator'),
                'status': bug.get('status'),
                'severity': bug.get('severity'),
                'priority': bug.get('priority'),
                'module': bug.get('module'),
                'custom_fields': bug.get('custom_fields', {}),
            })

        # 各字段的填充率统计
        field_names = ['title', 'created', 'updated', 'creator', 'status', 'severity', 'priority', 'module', 'custom_fields']
        field_stats = {}
        total = len(raw_bugs)
        for field in field_names:
            if field == 'custom_fields':
                filled = sum(1 for b in raw_bugs if b.get('custom_fields') and len(b.get('custom_fields', {})) > 0)
            else:
                filled = sum(1 for b in raw_bugs if b.get(field))
            field_stats[field] = {
                'filled': filled,
                'total': total,
                'rate': round(filled / total * 100, 1) if total > 0 else 0,
            }

        logger.info(f"[API:yunxiao_sync_log] record_id={record_id}, bugs={len(raw_bugs)}, "
                    f"custom_fields_keys={all_custom_field_keys}, first_bug_raw_keys={first_bug_raw_keys[:20]}")

        return _build_api_response({
            'record_id': record_id,
            'file_name': record.file_name,
            'total_bugs': len(raw_bugs),
            'first_bug_fields': first_bug_fields,
            'first_bug_raw_keys': first_bug_raw_keys,
            'all_custom_field_keys': all_custom_field_keys,
            'sample_bugs': sample_bugs,
            'field_stats': field_stats,
            'sync_time': localtime(record.created_at).strftime('%Y-%m-%d %H:%M:%S'),
        })

    except Exception as e:
        logger.error(f'[API:yunxiao_sync_log] 错误: {e}', exc_info=True)
        return _build_error_response(f'获取同步日志失败: {str(e)}',
                                     code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def bug_analysis_ai_status(request, record_id):
    """
    查询 Bug 分析记录的 AI 分析状态（用于异步轮询）

    GET /data-factory/bug-analysis/records/<id>/ai-status/

    返回:
        - ai_status: none/pending/running/completed/failed
        - ai_progress: 0-100
        - has_ai_data: 是否有AI分析数据
    """
    try:
        if not _DB_RECORDS_AVAILABLE:
            return _build_error_response('历史记录功能暂不可用', code=status.HTTP_503_SERVICE_UNAVAILABLE)

        record = BugAnalysisRecord.objects.filter(id=record_id).first()
        if not record:
            return _build_error_response(f'分析记录不存在: id={record_id}', code=status.HTTP_404_NOT_FOUND)

        analysis_result = record.analysis_result or {}
        has_ai_data = bool(
            analysis_result.get('aiSummary') or
            analysis_result.get('aiKeywords') or
            analysis_result.get('aiRisks')
        )

        return _build_api_response({
            'record_id': record_id,
            'ai_status': record.ai_status,
            'ai_progress': record.ai_progress,
            'has_ai_data': has_ai_data,
            'file_name': record.file_name,
            'total_bugs': record.total_bugs,
        })

    except Exception as e:
        logger.error(f'[API:bug_analysis_ai_status] 错误: {e}', exc_info=True)
        return _build_error_response(f'查询AI状态失败: {str(e)}',
                                     code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')


# ============================================================
# 云效 Token 配置管理 API
# ============================================================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def yunxiao_token_list(request):
    """
    云效 Token 配置列表 (GET) + 新建 (POST)

    GET参数:
        - keyword: 搜索标签/创建者 (可选)
        - is_active: 过滤启用状态 (可选)
        - page: 页码 (默认1)
        - page_size: 每页数量 (默认20)

    POST参数:
        - label: 标签/备注 (必填)
        - token: 云效PAT令牌 (必填)
        - is_active: 是否启用 (默认True)
    """
    from .models import YunxiaoToken

    if request.method == 'POST':
        try:
            label = request.data.get('label', '').strip()
            token_val = request.data.get('token', '').strip()
            is_active = request.data.get('is_active', True)

            if not label:
                return _build_error_response('请输入标签/备注')
            if not token_val:
                return _build_error_response('请输入云效访问令牌')

            # 获取当前用户
            user = request.user
            created_by = user.username if user and user.is_authenticated else 'system'

            item = YunxiaoToken.objects.create(
                label=label,
                token=token_val,
                is_active=is_active,
                created_by=created_by,
            )

            logger.info(f'[API:yunxiao_token_list] 创建Token: id={item.id}, label={label}, by={created_by}')
            return _build_api_response({'token': item.to_list_dict()}, 'Token 创建成功')

        except Exception as e:
            logger.error(f'[API:yunxiao_token_list] 创建错误: {e}', exc_info=True)
            return _build_error_response(f'创建Token失败: {str(e)}',
                                         code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')

    # GET 请求
    try:
        queryset = YunxiaoToken.objects.all()

        keyword = request.query_params.get('keyword', '').strip()
        if keyword:
            queryset = queryset.filter(
                Q(label__icontains=keyword) | Q(created_by__icontains=keyword)
            )

        is_active = request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() in ('true', '1', 'yes'))

        page = max(int(request.query_params.get('page', 1)), 1)
        page_size = min(int(request.query_params.get('page_size', 20)), 100)
        start = (page - 1) * page_size
        end = start + page_size

        total = queryset.count()
        items = queryset[start:end]
        items_data = [item.to_list_dict() for item in items]

        return _build_api_response({
            'items': items_data,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': max((total + page_size - 1) // page_size, 1),
        })

    except Exception as e:
        logger.error(f'[API:yunxiao_token_list] 列表错误: {e}', exc_info=True)
        return _build_error_response(f'获取Token列表失败: {str(e)}',
                                     code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def yunxiao_token_detail(request, token_id):
    """
    云效 Token 详情 (GET/更新 (PUT) / 删除 (DELETE)

    PUT参数:
        - label: 标签/备注
        - token: 云效PAT令牌
        - is_active: 是否启用
    """
    from .models import YunxiaoToken

    item = YunxiaoToken.objects.filter(id=token_id).first()
    if not item:
        return _build_error_response(f'Token不存在: id={token_id}', code=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        item.delete()
        logger.info(f'[API:yunxiao_token_detail] 删除Token: id={token_id}')
        return _build_api_response({}, f'Token id={token_id} 已删除')

    if request.method == 'PUT':
        try:
            label = request.data.get('label', '').strip()
            token_val = request.data.get('token', '').strip()
            is_active = request.data.get('is_active')

            if label:
                item.label = label
            if token_val:
                item.token = token_val
            if is_active is not None:
                item.is_active = is_active

            item.save()
            logger.info(f'[API:yunxiao_token_detail] 更新Token: id={token_id}')
            return _build_api_response({'token': item.to_list_dict()}, 'Token 更新成功')

        except Exception as e:
            logger.error(f'[API:yunxiao_token_detail] 更新错误: {e}', exc_info=True)
            return _build_error_response(f'更新Token失败: {str(e)}',
                                         code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')

    # GET
    return _build_api_response({'token': item.to_list_dict()})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def yunxiao_token_options(request):
    """
    获取启用的Token列表 (用于下拉选择)

    仅返回启用状态的Token，供前端下拉选择使用
    """
    from .models import YunxiaoToken

    try:
        items = YunxiaoToken.objects.filter(is_active=True).order_by('-created_at')
        options = [item.to_select_dict() for item in items]
        return _build_api_response({'options': options})

    except Exception as e:
        logger.error(f'[API:yunxiao_token_options] 错误: {e}', exc_info=True)
        return _build_error_response(f'获取Token选项失败: {str(e)}',
                                     code=status.HTTP_500_INTERNAL_SERVER_ERROR, log_level='error')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def yunxiao_token_test(request, token_id):
    """
    测试Token是否有效 (调用云效API验证)

    POST参数:
        - test_space_id: 测试项目ID (可选)
    """
    from .models import YunxiaoToken
    from .yunxiao_client import YunxiaoClient, DEFAULT_ORGANIZATION_ID

    item = YunxiaoToken.objects.filter(id=token_id).first()
    if not item:
        return _build_error_response(f'Token不存在: id={token_id}', code=status.HTTP_404_NOT_FOUND)

    try:
        client = YunxiaoClient(token=item.token, organization_id=DEFAULT_ORGANIZATION_ID)

        # 尝试搜索项目来验证Token有效性
        test_space_id = request.data.get('test_space_id', '').strip()
        if test_space_id:
            projects = client.search_projects()
            return _build_api_response({
                'valid': True,
                'message': f'Token有效，可访问 {len(projects)} 个项目',
            }, 'Token 验证成功')
        else:
            # 简单测试: 搜索项目列表
            projects = client.search_projects()
            return _build_api_response({
                'valid': True,
                'message': f'Token有效，可访问 {len(projects)} 个项目',
            }, 'Token 验证成功')

    except YunxiaoAPIError as e:
        return _build_api_response({
            'valid': False,
            'message': f'Token无效: {str(e)}',
        }, 'Token 验证失败')
    except Exception as e:
        return _build_api_response({
            'valid': False,
            'message': f'验证异常: {str(e)}',
        }, 'Token 验证失败')
