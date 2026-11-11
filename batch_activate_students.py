# -*- coding: utf-8 -*-
"""
批量预激活租户学员脚本(运维专用)
对应临时接口: POST /user/v1/user/batchActivateStudents
鉴权要求: Authorization 必须是【平台管理员】的登录凭证, 否则接口会拒绝

用法:
1. F12 打开浏览器开发者工具 -> Network -> 随便挑一个已登录请求,
   把 Request Headers 里的 Authorization 值整段复制到下面 AUTHORIZATION
2. 手机号写入同目录 mobiles.txt(每行一个), 或填到下方 MOBILES 内置列表
   (可同时指定多个手机号传入一次调用, 本脚本默认逐个调用便于观察明细)
3. 执行: python batch_activate_students.py
4. 跑完后控制台输出汇总, 失败的手机号会写入 failed_mobiles.txt 方便修正后重跑
"""
import json
import re
import time
from collections import OrderedDict

import requests

# ==================== 配置区 ====================
BASE_URL = "https://apaas.grtcloud.net/api/grt-user-service"
# 需要激活学员的租户ID
TENANT_ID = "1752528309909528578"
# 请求头里的租户ID, 默认与TENANT_ID一致
HEADER_TENANT_ID = "1752528309909528578"

# 平台管理员的登录凭证
AUTHORIZATION = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJsb2dpblR5cGUiOiJsb2dpbiIsImxvZ2luSWQiOjE3NjA5MzE5MTc4Nzk5MTQ0OTYsInJuU3RyIjoienZtakx6TkRNMmlaeGFQNHdYSEp6SVNRRWlUZ1hnWkwiLCJsb2dpbk5hbWUiOiIxMzAxMTA5MTUzNiJ9.K67K5QrgMcalAHG455g0C15s1jYhjFuTcGX3K9arZAs"
# 若凭证为JWT且需要前缀, 请自行改为: AUTHORIZATION = "Bearer " + 你的token

MOBILES_FILE = "mobiles.txt"   # 优先读取文件; 文件不存在时使用下方内置列表
# 内置手机号列表(与 mobiles.txt 二选一即可)
MOBILES = [
    # "15835023401"
]
OUTPUT_FAILED_FILE = "failed_mobiles.txt"
REQUEST_INTERVAL = 0.5         # 相邻两次请求间隔(秒), 保护生产环境
TIMEOUT = 15                   # 单次请求超时(秒)
MAX_RETRY = 2                  # 单个手机号的最大尝试次数
# ===============================================

API = f"{BASE_URL}/user/v1/user/batchActivateStudents"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": AUTHORIZATION,
    "TenantId": HEADER_TENANT_ID
}



def load_mobiles():
    """优先读 mobiles.txt(每行一个手机号), 不存在则用内置 MOBILES"""
    try:
        with open(MOBILES_FILE, "r", encoding="utf-8") as f:
            from_file = [line.strip() for line in f if line.strip()]
        if from_file:
            print(f"[i] 从 {MOBILES_FILE} 读取到 {len(from_file)} 个手机号")
            return from_file
    except FileNotFoundError:
        pass
    print(f"[i] 未找到 {MOBILES_FILE}, 使用脚本内置手机号列表({len(MOBILES)}个)")
    return list(MOBILES)


def activate_one(session, mobile):
    """调接口激活单个手机号, 返回明细dict: {mobile, userId, status, msg}"""
    payload = {"tenant_id": TENANT_ID, "mobiles": [mobile]}
    last_err = None
    for attempt in range(1, MAX_RETRY + 1):
        try:
            resp = session.post(API, json=payload, headers=HEADERS, timeout=TIMEOUT)
            if resp.status_code == 401 or resp.status_code == 403:
                raise PermissionError(
                    f"HTTP {resp.status_code} 鉴权失败, 请确认 Authorization 为平台管理员的有效登录凭证")
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
            body = resp.json()
            data = body.get("data")
            if not data:
                raise RuntimeError(f"业务响应异常: {json.dumps(body, ensure_ascii=False)[:300]}")
            return data[0]
        except Exception as e:
            last_err = e
            # 鉴权错误没有重试意义, 直接终止该手机号
            if isinstance(e, PermissionError) or attempt >= MAX_RETRY:
                break
            time.sleep(1)
    return {
        "mobile": mobile,
        "userId": None,
        "status": "FAILED",
        "msg": f"请求失败(共尝试{MAX_RETRY}次): {last_err}",
    }


def main():
    if not AUTHORIZATION or "粘贴" in AUTHORIZATION:
        print("[x] 请先在脚本配置区填写平台管理员的 AUTHORIZATION")
        return

    # 去重(保序) + 格式校验
    mobiles = list(OrderedDict.fromkeys(load_mobiles()))
    invalid = [m for m in mobiles if not re.fullmatch(r"1\d{10}", m)]
    valid = [m for m in mobiles if m not in invalid]
    if invalid:
        print(f"[!] 跳过{len(invalid)}个格式非法的手机号: {invalid}")

    print(f"[i] 目标租户: {TENANT_ID}, 待处理手机号共 {len(valid)} 个\n")

    success_list, fail_list = [], []
    with requests.Session() as session:
        for idx, mobile in enumerate(valid, 1):
            detail = activate_one(session, mobile)
            ok = detail.get("status") == "SUCCESS"
            (success_list if ok else fail_list).append(detail)
            print(f"[{idx}/{len(valid)}] {detail.get('mobile')} -> "
                  f"{detail.get('status')} userId={detail.get('user_id')} | {detail.get('msg')}")
            time.sleep(REQUEST_INTERVAL)

    print("\n========== 汇总 ==========")
    print(f"成功: {len(success_list)}  失败: {len(fail_list)}")
    if fail_list:
        with open(OUTPUT_FAILED_FILE, "w", encoding="utf-8") as f:
            for d in fail_list:
                f.write(d["mobile"] + "\n")
        print(f"[!] 失败手机号已写入 {OUTPUT_FAILED_FILE}, 修正问题后可直接重跑该文件:")
        for d in fail_list:
            print(f"    {d['mobile']}: {d['msg']}")


if __name__ == "__main__":
    main()
