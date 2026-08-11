#!/usr/bin/env python
"""
修复 BugSyncItem 缺少 token_id 的问题
用法: python fix_token_id.py
"""
import os
import sys
import django

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'grt_testhub.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apps.data_factory.models import BugSyncItem, YunxiaoTokenConfig

def fix_token_id():
    """
    为 BugSyncItem 补充 token_id

    策略:
    1. 如果用户只有一个令牌，使用该令牌
    2. 否则跳过，手动处理
    """
    items = BugSyncItem.objects.filter(local_data__token_id__isnull=True)
    total = items.count()
    print(f"找到 {total} 条缺少 token_id 的记录")

    # 获取所有可用的令牌
    tokens = YunxiaoTokenConfig.objects.filter(is_active=True)
    token_count = tokens.count()

    if token_count == 0:
        print("❌ 没有可用的令牌配置")
        return

    if token_count == 1:
        token = tokens.first()
        print(f"✓ 使用唯一令牌: {token.label} (ID: {token.id})")

        updated = 0
        for item in items:
            local_data = item.local_data or {}
            local_data['token_id'] = token.id
            item.local_data = local_data
            item.save(update_fields=['local_data'])
            updated += 1
            if updated % 10 == 0:
                print(f"已更新 {updated}/{total} 条...")

        print(f"✅ 成功更新 {updated} 条记录")
    else:
        print(f"⚠️  发现 {token_count} 个令牌，无法自动推断:")
        for token in tokens:
            print(f"  - {token.label} (ID: {token.id})")
        print("\n请手动更新 local_data 中的 token_id 字段")

if __name__ == '__main__':
    fix_token_id()