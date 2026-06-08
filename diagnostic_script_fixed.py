#!/usr/bin/env python3
"""
场景编排数据问题快速诊断脚本
"""

import os
import sys
import json

# 设置正确的路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, 'grt_testhub'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

try:
    import django
    django.setup()
except Exception as e:
    print(f"❌ Django 设置失败: {e}")
    print("请确保在 grt_testhub 目录下运行")
    sys.exit(1)

from apps.api_testing.models import ScenarioStep

def diagnose_scenario_step(step_id):
    """诊断场景步骤数据"""
    
    print("=" * 80)
    print(f"诊断场景步骤 ID: {step_id}")
    print("=" * 80)
    
    try:
        step = ScenarioStep.objects.get(id=step_id)
        
        print(f"\n[基本信息]")
        print(f"步骤名称: {step.name}")
        print(f"步骤编号: {step.step_number}")
        print(f"步骤类型: {step.step_type}")
        print(f"步骤启用: {step.override_enabled}")
        print(f"关联接口: {step.api_request}")
        
        if step.api_request:
            print(f"\n[原始接口信息]")
            print(f"接口 ID: {step.api_request.id}")
            print(f"接口名称: {step.api_request.name}")
            print(f"接口方法: {step.api_request.method}")
            print(f"接口 URL: {step.api_request.url}")
            
            api_body = step.api_request.body
            print(f"接口 body:")
            print(json.dumps(api_body, indent=2, ensure_ascii=False))
        
        print(f"\n[覆盖配置信息 - 关键]")
        print(f"override_body:")
        override_body = step.override_body
        print(json.dumps(override_body, indent=2, ensure_ascii=False))
        
        # 详细检查 override_body
        print(f"\n[override_body 详细检查]")
        
        if not override_body:
            print("❌❌❌ override_body 为空或 None!")
            print("这是最可能的问题原因！")
            return
        
        if not isinstance(override_body, dict):
            print(f"❌ override_body 不是 dict: {type(override_body)}")
            return
        
        if 'type' not in override_body:
            print("❌ override_body 没有 type 字段")
            print(f"override_body 内容: {override_body}")
            return
        
        body_type = override_body.get('type')
        body_data = override_body.get('data')
        
        print(f"body_type: {body_type}")
        print(f"body_data type: {type(body_data)}")
        
        if body_type == 'form-data':
            print(f"\n[form-data 字段检查 - 关键]")
            
            if not isinstance(body_data, list):
                print(f"❌ body_data 不是 list: {type(body_data)}")
                print(f"内容: {body_data}")
                return
            
            print(f"字段数量: {len(body_data)}")
            
            if len(body_data) == 0:
                print("❌❌❌ form-data data 数组为空！")
                print("这是问题原因：没有字段数据")
                return
            
            for idx, item in enumerate(body_data):
                print(f"\n字段 [{idx}]:")
                print(f"  key: {item.get('key')}")
                print(f"  value: {item.get('value')}")
                print(f"  type: {item.get('type')}")
                print(f"  enabled: {item.get('enabled')} ← 检查这个值")
                
                if item.get('key') == 'kb_id':
                    print(f"✅✅✅ 找到 kb_id 字段!")
                    print(f"  kb_id value: {item.get('value')}")
                    print(f"  kb_id enabled: {item.get('enabled')}")
            
            # 总结检查
            kb_id_items = [i for i in body_data if i.get('key') == 'kb_id']
            if kb_id_items:
                print(f"\n✅✅✅ kb_id 存在于 override_body 中")
                print(f"kb_id 数量: {len(kb_id_items)}")
                for kb_item in kb_id_items:
                    kb_value = kb_item.get('value')
                    kb_enabled = kb_item.get('enabled')
                    print(f"kb_id 详情: value={kb_value}, enabled={kb_enabled}")
                    
                    if kb_enabled is False:
                        print("⚠️⚠️⚠️ kb_id enabled=False，会被过滤（但已修复）")
                    elif kb_enabled is None:
                        print("⚠️ kb_id enabled=None，修复后会默认为 True")
            else:
                print(f"\n❌❌❌ kb_id 不存在于 override_body 中!")
                print(f"所有字段 key: {[i.get('key') for i in body_data]}")
                print("这是问题原因：override_body 中没有 kb_id 字段")
        
        elif body_type == 'json':
            print(f"\n[JSON 数据检查]")
            if isinstance(body_data, dict):
                kb_id = body_data.get('kb_id')
                if kb_id:
                    print(f"✅✅✅ kb_id 在 JSON 中: {kb_id}")
                else:
                    print(f"❌❌❌ kb_id 不在 JSON 中")
                    print(f"JSON 所有字段: {list(body_data.keys())}")
        
        # 检查 effective_request_data
        print(f"\n[effective_request_data - 实际使用的数据]")
        try:
            effective_data = step.get_effective_request_data()
            print(f"method: {effective_data.get('method')}")
            print(f"url: {effective_data.get('url')}")
            
            body = effective_data.get('body', {})
            print(f"body:")
            print(json.dumps(body, indent=2, ensure_ascii=False))
            
            if isinstance(body, dict) and 'type' in body:
                if body.get('type') == 'form-data':
                    data_list = body.get('data', [])
                    kb_id_in_effective = [i for i in data_list if i.get('key') == 'kb_id']
                    
                    if kb_id_in_effective:
                        print(f"\n✅✅✅ kb_id 在 effective_request_data 中")
                        for item in kb_id_in_effective:
                            print(f"  kb_id: {item.get('value')}, enabled: {item.get('enabled')}")
                    else:
                        print(f"\n❌❌❌ kb_id 不在 effective_request_data 中!")
                        print(f"所有字段: {[i.get('key') for i in data_list]}")
        except Exception as e:
            print(f"❌ 获取 effective_request_data 失败: {e}")
        
    except ScenarioStep.DoesNotExist:
        print(f"❌ 步骤 ID {step_id} 不存在!")
        print("\n请检查步骤 ID 是否正确:")
        print("可以通过以下方式查找:")
        print("1. 前端界面查看步骤详情")
        print("2. 数据库查询: SELECT id, name FROM api_scenario_steps;")
    except Exception as e:
        print(f"❌ 诊断出错: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("场景编排数据诊断脚本")
    print("=" * 80)
    
    if len(sys.argv) > 1:
        try:
            step_id = int(sys.argv[1])
            diagnose_scenario_step(step_id)
        except ValueError:
            print("❌ 步骤 ID 必须是数字")
            print("使用方法: python3 diagnostic_script_fixed.py <步骤ID>")
    else:
        print("使用方法: python3 diagnostic_script_fixed.py <步骤ID>")
        print("示例: python3 diagnostic_script_fixed.py 4")
    
    print("\n" + "=" * 80)
