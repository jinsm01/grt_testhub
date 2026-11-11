"""
账号激活功能视图 - 对应前端「账号激活」菜单

功能:
1. API 配置 CRUD (ActivationConfig)
2. 批量代理激活 (调用外部接口, 逐个手机号, 带重试/间隔)
3. 激活日志查询 (ActivationLog)
4. 手机号历史 (从数据工厂手机号生成记录中获取, 供一键导入)
"""
import json
import logging
import re
import time
from collections import OrderedDict

import requests
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ActivationConfig, ActivationLog, DataFactoryRecord

logger = logging.getLogger(__name__)
User = get_user_model()


# ===================== 配置管理 =====================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def activation_config(request):
    """
    获取或保存当前用户的激活 API 配置

    GET:  返回当前用户的配置 (没有则创建默认配置并返回)
    POST: 保存/更新当前用户的配置
    """
    user = request.user

    if request.method == "GET":
        config, created = ActivationConfig.objects.get_or_create(
            user=user,
            defaults={},
        )
        if created:
            logger.info(f"[Activation] 为用户 {user.username} 创建默认配置")
        return JsonResponse(_config_to_dict(config))

    # POST - 保存配置
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, Exception) as e:
        return JsonResponse({"error": f"请求体解析失败: {e}"}, status=400)

    config, _ = ActivationConfig.objects.get_or_create(user=user, defaults={})

    # 更新字段
    config.api_url = data.get("api_url", config.api_url)
    config.api_method = data.get("api_method", config.api_method)
    config.api_headers = data.get("api_headers") or {}
    config.body_template = data.get("body_template", config.body_template)
    config.interval_sec = float(data.get("interval_sec", config.interval_sec))
    config.max_retry = int(data.get("max_retry", config.max_retry))
    config.timeout = int(data.get("timeout", config.timeout))
    config.save()

    return JsonResponse(_config_to_dict(config))


def _fmt_time(dt):
    """把 UTC datetime 转成本地时间字符串"""
    return timezone.localtime(dt).strftime("%Y-%m-%d %H:%M:%S")


def _config_to_dict(config: ActivationConfig) -> dict:
    return {
        "id": config.id,
        "api_url": config.api_url,
        "api_method": config.api_method,
        "api_headers": config.api_headers,
        "body_template": config.body_template,
        "interval_sec": config.interval_sec,
        "max_retry": config.max_retry,
        "timeout": config.timeout,
        "created_at": _fmt_time(config.created_at),
        "updated_at": _fmt_time(config.updated_at),
    }


# ===================== 核心: 批量激活(代理) =====================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def batch_activate(request):
    """
    批量激活 - 后端代理调用外部接口

    请求体:
    {
        "authorization": "平台管理员token(每次手动输入)",
        "mobiles": ["138...", "139..."],     // 手机号列表
        "api_url": "...",                     // 可选, 覆盖保存的配置
        "api_method": "POST",
        "api_headers": {...},                 // 可选, 会与 Authorization 合并
        "body_template": "...",               // 可选
        "interval_sec": 0.5,
        "max_retry": 2,
        "timeout": 15,
        "per_batch": 1                        // 每批几个手机号, 默认1(逐个)
    }

    返回:
    {
        "success_count": 5,
        "fail_count": 2,
        "results": [ {"mobile": "...", "status": "SUCCESS|FAILED", "userId": "...", "msg": "..."} ]
    }
    """
    user = request.user
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, Exception) as e:
        return JsonResponse({"error": f"请求体解析失败: {e}"}, status=400)

    # --- 参数校验 ---
    authorization = (data.get("authorization") or "").strip()
    if not authorization:
        return JsonResponse({"error": "Authorization Token 不能为空"}, status=400)

    tenant_id = (data.get("tenant_id") or "").strip()

    raw_mobiles = data.get("mobiles", []) or []
    # 去重保序 + 格式校验
    seen = set()
    mobiles = []
    invalid = []
    for m in raw_mobiles:
        m = str(m).strip()
        if not m or m in seen:
            continue
        if re.fullmatch(r"1\d{10}", m):
            seen.add(m)
            mobiles.append(m)
        else:
            invalid.append(m)

    if not mobiles:
        return JsonResponse({"error": "没有有效的手机号", "invalid": invalid}, status=400)

    # --- 获取/合并 API 配置 ---
    try:
        saved_config, _ = ActivationConfig.objects.get_or_create(user=user, defaults={})
    except Exception:
        saved_config = None

    api_url = data.get("api_url") or (saved_config.api_url if saved_config else "")
    api_method = (data.get("api_method") or (saved_config.api_method if saved_config else "POST")).upper()
    api_headers = data.get("api_headers") or (saved_config.api_headers if saved_config else {}) or {}
    body_template = data.get("body_template") or (saved_config.body_template if saved_config else "")
    interval_sec = float(data.get("interval_sec", saved_config.interval_sec if saved_config else 0.5))
    max_retry = int(data.get("max_retry", saved_config.max_retry if saved_config else 2))
    timeout = int(data.get("timeout", saved_config.timeout if saved_config else 15))
    per_batch = int(data.get("per_batch", 1))

    if not api_url:
        return JsonResponse({"error": "接口URL未配置"}, status=400)

    # --- 组装 Headers ---
    headers = {"Content-Type": "application/json"}
    headers.update(api_headers or {})
    headers["Authorization"] = authorization

    # --- 逐个调用 ---
    results = []
    success_count = 0
    fail_count = 0
    session = requests.Session()

    # 分组: 每 per_batch 个手机号为一批
    batches = [mobiles[i:i + per_batch] for i in range(0, len(mobiles), per_batch)]

    for batch in batches:
        if len(batch) == 1:
            # 逐个模式 - 保持与脚本一致的行为
            single_mobile = batch[0]
            detail = _activate_one(
                session, api_url, api_method, headers, body_template,
                single_mobile, max_retry, timeout, tenant_id,
            )
            if detail.get("status") == "SUCCESS":
                success_count += 1
            else:
                fail_count += 1
            results.append(detail)
            time.sleep(interval_sec)
        else:
            # 批量模式 - 一次传多个手机号
            batch_detail = _activate_batch(
                session, api_url, api_method, headers, body_template,
                batch, max_retry, timeout, tenant_id,
            )
            for d in batch_detail:
                if d.get("status") == "SUCCESS":
                    success_count += 1
                else:
                    fail_count += 1
                results.append(d)
            time.sleep(interval_sec)

    # --- 保存执行日志 ---
    try:
        ActivationLog.objects.create(
            user=user,
            api_url=api_url[:500],
            api_method=api_method,
            interval_sec=interval_sec,
            mobiles=mobiles,
            success_count=success_count,
            fail_count=fail_count,
            results=results,
        )
    except Exception as e:
        logger.error(f"[Activation] 保存执行日志失败: {e}")

    return JsonResponse({
        "total": len(mobiles),
        "success_count": success_count,
        "fail_count": fail_count,
        "invalid_mobiles": invalid,
        "results": results,
    })


def _render_body(body_template: str, mobiles: list, tenant_id: str = "") -> str:
    """将 Body 模板中的 {{tenant_id}} 和 {{mobiles}} 替换为实际值"""
    mobiles_json = json.dumps(mobiles, ensure_ascii=False)
    tenant_id_json = json.dumps(tenant_id or "", ensure_ascii=False)

    if not body_template:
        return json.dumps({"tenant_id": tenant_id or "", "mobiles": mobiles}, ensure_ascii=False)

    body = body_template.replace("{{tenant_id}}", tenant_id_json).replace("{{mobiles}}", mobiles_json)
    return body


def _activate_one(session, api_url, api_method, headers, body_template, mobile, max_retry, timeout, tenant_id=""):
    """激活单个手机号, 返回明细 dict"""
    payload = _render_body(body_template, [mobile], tenant_id)
    last_err = None

    for attempt in range(1, max_retry + 1):
        try:
            resp = session.request(
                method=api_method, url=api_url,
                headers=headers, data=payload, timeout=timeout,
            )
            # 鉴权错误直接返回, 不重试
            if resp.status_code in (401, 403):
                return {
                    "mobile": mobile,
                    "status": "FAILED",
                    "userId": None,
                    "msg": f"HTTP {resp.status_code} 鉴权失败",
                }
            if resp.status_code != 200:
                last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
                if attempt >= max_retry:
                    break
                time.sleep(1)
                continue

            # 解析响应 - 兼容脚本里的逻辑
            try:
                body = resp.json()
            except Exception:
                body = {}

            data = body.get("data")
            if not data:
                return {
                    "mobile": mobile,
                    "status": "FAILED",
                    "userId": None,
                    "msg": f"业务响应异常: {json.dumps(body, ensure_ascii=False)[:300]}",
                }

            # data 可能是 list, 取第一个
            item = data[0] if isinstance(data, list) else data
            # 脚本里返回的字段: status / userId / user_id / msg
            status_val = (
                item.get("status") or
                item.get("Status") or
                item.get("success") or
                "SUCCESS"
            )
            user_id = (
                item.get("userId") or
                item.get("user_id") or
                item.get("UserId") or
                ""
            )
            msg = item.get("msg") or item.get("message") or item.get("Message") or ""

            return {
                "mobile": mobile,
                "status": "SUCCESS" if str(status_val).upper() == "SUCCESS" else str(status_val),
                "userId": str(user_id) if user_id else None,
                "msg": msg,
                "raw": item if attempt == max_retry else None,
            }

        except requests.Timeout:
            last_err = f"请求超时({timeout}s)"
        except requests.ConnectionError as e:
            last_err = f"连接失败: {e}"
        except Exception as e:
            last_err = str(e)

        if attempt >= max_retry:
            break
        time.sleep(1)

    return {
        "mobile": mobile,
        "status": "FAILED",
        "userId": None,
        "msg": f"请求失败(共尝试{max_retry}次): {last_err}",
    }


def _activate_batch(session, api_url, api_method, headers, body_template, mobiles, max_retry, timeout, tenant_id=""):
    """一次激活一批手机号, 返回明细 list"""
    payload = _render_body(body_template, mobiles, tenant_id)
    last_err = None

    for attempt in range(1, max_retry + 1):
        try:
            resp = session.request(
                method=api_method, url=api_url,
                headers=headers, data=payload, timeout=timeout,
            )
            if resp.status_code in (401, 403):
                return [{
                    "mobile": m, "status": "FAILED", "userId": None,
                    "msg": f"HTTP {resp.status_code} 鉴权失败",
                } for m in mobiles]
            if resp.status_code != 200:
                last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
                if attempt >= max_retry:
                    break
                time.sleep(1)
                continue

            try:
                body = resp.json()
            except Exception:
                body = {}

            data = body.get("data", [])
            # 如果返回的是 list, 直接使用; 否则包装一下
            if isinstance(data, list):
                items = data
            else:
                items = [data] if data else []

            # 如果返回条数和请求条数不匹配, 逐个兜底
            if len(items) == len(mobiles):
                results = []
                for mobile, item in zip(mobiles, items):
                    status_val = item.get("status", "SUCCESS")
                    results.append({
                        "mobile": mobile,
                        "status": "SUCCESS" if str(status_val).upper() == "SUCCESS" else str(status_val),
                        "userId": item.get("userId") or item.get("user_id") or None,
                        "msg": item.get("msg") or item.get("message") or "",
                    })
                return results
            else:
                # 不匹配, 按顺序兜底, 多余的算 FAILED
                results = []
                for i, mobile in enumerate(mobiles):
                    if i < len(items):
                        item = items[i]
                        status_val = item.get("status", "SUCCESS")
                        results.append({
                            "mobile": mobile,
                            "status": "SUCCESS" if str(status_val).upper() == "SUCCESS" else str(status_val),
                            "userId": item.get("userId") or item.get("user_id") or None,
                            "msg": item.get("msg") or item.get("message") or "",
                        })
                    else:
                        results.append({
                            "mobile": mobile, "status": "FAILED", "userId": None,
                            "msg": f"响应条数不匹配(响应{len(items)}/请求{len(mobiles)})",
                        })
                return results

        except requests.Timeout:
            last_err = f"请求超时({timeout}s)"
        except requests.ConnectionError as e:
            last_err = f"连接失败: {e}"
        except Exception as e:
            last_err = str(e)

        if attempt >= max_retry:
            break
        time.sleep(1)

    return [{
        "mobile": m, "status": "FAILED", "userId": None,
        "msg": f"请求失败(共尝试{max_retry}次): {last_err}",
    } for m in mobiles]


# ===================== 激活日志 =====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def activation_logs(request):
    """获取当前用户的激活日志列表"""
    user = request.user
    limit = int(request.GET.get("limit", 50))
    logs = list(ActivationLog.objects.filter(user=user).order_by("-created_at")[:limit])
    return JsonResponse({
        "total": len(logs),
        "results": [l.to_list_dict() for l in logs],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def activation_log_detail(request, log_id):
    """获取单条激活日志详情 (含逐条结果)"""
    user = request.user
    try:
        log = ActivationLog.objects.get(id=log_id, user=user)
    except ActivationLog.DoesNotExist:
        return JsonResponse({"error": "日志不存在"}, status=404)

    return JsonResponse({
        "id": log.id,
        "api_url": log.api_url,
        "api_method": log.api_method,
        "interval_sec": log.interval_sec,
        "mobiles": log.mobiles,
        "success_count": log.success_count,
        "fail_count": log.fail_count,
        "results": log.results,
        "created_at": _fmt_time(log.created_at),
    })


# ===================== 手机号历史 =====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def phone_history(request):
    """
    获取数据工厂中生成的手机号历史记录 (用于「一键导入」)

    查询 DataFactoryRecord 中 tool_name=generate_chinese_phone 的记录,
    返回每条的 output_data + custom_name + 创建时间,
    output_data 里的 result 就是手机号列表
    """
    user = request.user
    limit = int(request.GET.get("limit", 20))

    records = DataFactoryRecord.objects.filter(
        user=user,
        tool_name="generate_chinese_phone",
    ).order_by("-created_at")[:limit]

    results = []
    for r in records:
        output = r.output_data or {}
        mobiles_list = output.get("result", [])
        # 如果是单字符串也包装成 list
        if isinstance(mobiles_list, str):
            mobiles_list = [mobiles_list]

        results.append({
            "id": r.id,
            "custom_name": r.custom_name or f"手机号生成-{r.id}",
            "mobile_count": len(mobiles_list),
            "preview": mobiles_list[:3],  # 预览前3个
            "mobiles": mobiles_list,      # 完整列表, 前端选中后拉取
            "created_at": _fmt_time(r.created_at),
        })

    return JsonResponse({
        "total": len(results),
        "results": results,
    })


# ===================== 恢复默认配置 =====================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def activation_config_reset(request):
    """恢复默认配置"""
    user = request.user
    config, _ = ActivationConfig.objects.get_or_create(user=user, defaults={})

    config.api_url = "https://apaas.grtcloud.net/api/grt-user-service/user/v1/user/batchActivateStudents"
    config.api_method = "POST"
    config.api_headers = {"TenantId": "1752528309909528578"}
    config.body_template = '{"tenant_id": {{tenant_id}}, "mobiles": {{mobiles}}}'
    config.interval_sec = 0.5
    config.max_retry = 2
    config.timeout = 15
    config.save()

    return JsonResponse(_config_to_dict(config))
