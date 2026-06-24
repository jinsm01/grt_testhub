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
                                  version_tag=''):
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

    Returns:
        dict: 完整的分析结果
    """
    start_time = time.time()

    # 如果未指定 config_id 且使用 qwen，自动获取 Bug 分析配置
    if ai_provider_name == 'qwen' and ai_config_id is None:
        ai_config_id = _get_bug_analyzer_config_id()

    # Step 1: 规则引擎核心分析
    logger.info(f"[BugAnalysis] 开始分析: 文件={filename}, Bug数={len(bugs)}, AI={ai_provider_name}, config_id={ai_config_id}")
    analysis_result = analyze_bugs(list(bugs), filename)  # copy 避免副作用

    # Step 2: AI 增强 (异步调用 - 并发优化)
    ai_stats = {'calls': 0, 'errors': 0}
    if ai_provider_name and ai_provider_name != 'none':
        try:
            from .bug_analysis_ai import get_ai_provider
            ai = get_ai_provider(provider_name=ai_provider_name, config_id=ai_config_id)

            # 对每个 TOP 模块生成测试建议和根因假设
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
                except Exception as e:
                    return mod, None, e

            focus_tasks = [fetch_test_focus(mod) for mod in top_modules]
            focus_results = await asyncio.gather(*focus_tasks)

            for mod, focus_text, error in focus_results:
                if error:
                    logger.warning(f"AI测试建议[{mod}]失败: {error}")
                    ai_stats['errors'] += 1
                else:
                    enhanced_focus[mod] = focus_text
                    ai_stats['calls'] += 1

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

    # Step 3: 保存记录
    record = None
    if save_record and _DB_RECORDS_AVAILABLE:
        try:
            # 序列化 raw_bugs 以处理 datetime 等特殊类型
            serialized_bugs = [_serialize_for_json(dict(b)) for b in bugs]
            record = BugAnalysisRecord.objects.create(
                version_tag=version_tag,
                source_type='excel',
                file_name=_sanitize_filename(filename),
                total_bugs=len(bugs),
                raw_bugs=serialized_bugs,
                analysis_result=analysis_result,
                created_by=getattr(getattr(request, 'user', None), 'username', 'system')
                if hasattr(request, 'user') and request.user.is_authenticated else 'system'
            )
            analysis_result['record_id'] = record.id
            logger.info(f"[BugAnalysis] 记录已保存: id={record.id}")
        except Exception as e:
            logger.error(f"[BugAnalysis] 保存分析记录失败: {e}", exc_info=True)

    return analysis_result


# 全局 request 引擎（用于 _run_enhanced_analysis 内部访问）
request = None


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
            version_tag=version_tag
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
            from .bug_analysis_ai import get_ai_provider
            ai = get_ai_provider(provider_name=ai_provider, config_id=ai_config_id)

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
                except Exception as e:
                    return mod, None, e

            # 使用 async_to_sync 在同步视图中运行异步代码
            async def run_focus_tasks():
                tasks = [fetch_test_focus(mod) for mod in top_modules]
                return await asyncio.gather(*tasks)
            
            focus_results = async_to_sync(run_focus_tasks)()

            for mod, focus_text, error in focus_results:
                if error:
                    logger.warning(f"AI测试建议[{mod}]失败: {error}")
                    ai_stats['errors'] += 1
                else:
                    enhanced_focus[mod] = focus_text
                    ai_stats['calls'] += 1

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
            items.append({
                'id': r.id,
                'version_tag': r.version_tag,
                'source_type': r.source_type,
                'file_name': r.file_name,
                'total_bugs': r.total_bugs,
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

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def yunxiao_projects(request):
    """
    获取云效项目列表 (代理接口)

    POST参数:
        - token: 云效个人访问令牌 (必填)
        - organization_id: 组织 ID (中心版必填)
        - domain: API 域名 (可选)
        - keyword: 搜索关键词 (可选)
        - page: 页码 (默认1)
        - per_page: 每页数量 (默认50)
    """
    try:
        token = request.data.get('token', '').strip()
        organization_id = request.data.get('organization_id', '').strip()
        domain = request.data.get('domain', '').strip()
        keyword = request.data.get('keyword', '').strip()
        page = int(request.data.get('page', 1))
        per_page = min(int(request.data.get('per_page', 50)), 200)

        if not token:
            return _build_error_response('请提供云效访问令牌 (token)')

        from .yunxiao_client import YunxiaoClient, YunxiaoAPIError
        client_kwargs = {"token": token, "organization_id": organization_id}
        if domain:
            client_kwargs["domain"] = domain
        client = YunxiaoClient(**client_kwargs)

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
        - token: 云效个人访问令牌 (必填)
        - organization_id: 组织 ID (中心版必填)
        - domain: API 域名 (可选)
        - space_id: 项目 ID (必填)
        - page: 页码 (默认1)
        - per_page: 每页数量 (默认50)
    """
    try:
        token = request.data.get('token', '').strip()
        organization_id = request.data.get('organization_id', '').strip()
        domain = request.data.get('domain', '').strip()
        space_id = request.data.get('space_id', '').strip()
        page = int(request.data.get('page', 1))
        per_page = min(int(request.data.get('per_page', 50)), 200)

        if not token:
            return _build_error_response('请提供云效访问令牌 (token)')
        if not space_id:
            return _build_error_response('请提供项目 ID (space_id)')

        from .yunxiao_client import YunxiaoClient, YunxiaoAPIError
        client_kwargs = {"token": token, "organization_id": organization_id}
        if domain:
            client_kwargs["domain"] = domain
        client = YunxiaoClient(**client_kwargs)

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
def sync_from_yunxiao(request):
    """
    从云效同步 Bug 数据并进行分析

    POST参数:
        - token: 云效个人访问令牌 (必填)
        - organization_id: 组织 ID (中心版必填)
        - domain: API 域名 (可选)
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
        token = request.data.get('token', '').strip()
        organization_id = request.data.get('organization_id', '').strip()
        domain = request.data.get('domain', '').strip()
        space_id = request.data.get('space_id', '').strip()
        sprint_id = request.data.get('sprint_id', '').strip() or None
        version_tag = request.data.get('version_tag', '').strip()
        ai_provider = request.data.get('ai_provider', 'qwen').lower()
        ai_config_id_str = request.data.get('ai_config_id') or ''
        ai_config_id = int(ai_config_id_str) if ai_config_id_str and ai_config_id_str.isdigit() else None
        skip_ai_raw = request.data.get('skip_ai', 'false')
        skip_ai = str(skip_ai_raw).lower() in ('true', '1', 'yes')
        max_bugs = int(request.data.get('max_bugs', 1000))

        if not token:
            return _build_error_response('请提供云效访问令牌 (token)')
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

        # 构建文件名标识
        file_name = f"云效_{space_id}"
        if sprint_id:
            file_name += f"_{sprint_id}"
        file_name += f"_{len(bugs)}条"

        # 执行基础分析
        analysis_result = analyze_bugs(bugs, file_name)

        # 保存记录
        record_id = None
        save_record = True  # 云效同步默认保存
        if save_record and _DB_RECORDS_AVAILABLE:
            try:
                serialized_bugs = [_serialize_for_json(dict(b)) for b in bugs]
                record = BugAnalysisRecord.objects.create(
                    version_tag=version_tag,
                    source_type='yunxiao_api',
                    file_name=file_name,
                    total_bugs=len(bugs),
                    raw_bugs=serialized_bugs,
                    analysis_result=analysis_result,
                    created_by=request.user.username if request.user.is_authenticated else 'system'
                )
                record_id = record.id
                analysis_result['record_id'] = record.id
                logger.info(f"[API:sync_from_yunxiao] 记录已保存: id={record_id}")
            except Exception as e:
                logger.error(f"保存分析记录失败: {e}")
                if not skip_ai and ai_provider != 'none':
                    analysis_result['ai_pending'] = False
                    analysis_result['ai_error'] = '保存记录失败,无法启用AI分析'
        elif save_record and not _DB_RECORDS_AVAILABLE:
            logger.warning("[API:sync_from_yunxiao] 数据库模型不可用")
            if not skip_ai and ai_provider != 'none':
                analysis_result['ai_pending'] = False
                analysis_result['ai_error'] = '数据库模型不可用,请执行迁移'

        # 标记AI分析状态
        if 'ai_pending' not in analysis_result:
            analysis_result['ai_pending'] = not skip_ai and ai_provider != 'none'
        if 'ai_provider' not in analysis_result:
            analysis_result['ai_provider'] = ai_provider if not skip_ai else None
        if 'ai_config_id' not in analysis_result:
            analysis_result['ai_config_id'] = ai_config_id

        # 响应
        elapsed = round((time.time() - start_time) * 1000)
        analysis_result['success'] = True
        analysis_result['message'] = f'云效同步成功: {len(bugs)} 条Bug (耗时{elapsed}ms)'
        if 'record_id' not in analysis_result:
            analysis_result['record_id'] = record_id

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
