#!/usr/bin/env python
"""
场景编排数据问题快速诊断脚本
用于快速检查 override_body 数据是否正确
"""

import os
import sys
import django

# 设置 Django 环境
sys.path.insert(0, '/Users/jinshaomin/Documents/jinsm/test_hub/grt_testhub')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.api_testing.models import ScenarioStep
import json

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
        print(f"关联接口: {step.api_request}")
        
        if step.api_request:
            print(f"\n[原始接口信息]")
            print(f"接口名称: {step.api_request.name}")
            print(f"接口方法: {step.api_request.method}")
            print(f"接口 URL: {step.api_request.url}")
            print(f"接口 body: {json.dumps(step.api_request.body, indent=2, ensure_ascii=False)}")
        
        print(f"\n[覆盖配置信息]")
        print(f"override_enabled: {step.override_enabled}")
        print(f"override_body: {json.dumps(step.override_body, indent=2, ensure_ascii=False)}")
        
        # 检查 override_body
        print(f"\n[override_body 详细检查]")
        
        if not step.override_body:
            print("❌❌❌ override_body 为空或 None!")
            return
        
        if isinstance(step.override_body, dict):
            if 'type' in step.override_body:
                body_type = step.override_body.get('type')
                body_data = step.override_body.get('data')
                
                print(f"body_type: {body_type}")
                print(f"body_data type: {type(body_data)}")
                
                if body_type == 'form-data':
                    print(f"\n[form-data 字段检查]")
                    
                    if isinstance(body_data, list):
                        print(f"字段数量: {len(body_data)}")
                        
                        for idx, item in enumerate(body_data):
                            print(f"\n字段 [{idx}]:")
                            print(f"  key: {item.get('key')}")
                            print(f"  value: {item.get('value')}")
                            print(f"  type: {item.get('type')}")
                            print(f"  enabled: {item.get('enabled')} ← 关键检查点")
                            
                            if item.get('key') == 'kb_id':
                                print(f"✅✅✅ 找到 kb_id!")
                                print(f"  kb_id value: {item.get('value')}")
                                print(f"  kb_id enabled: {item.get('enabled')}")
                        
                        # 总结
                        kb_id_items = [i for i in body_data if i.get('key') == 'kb_id']
                        if kb_id_items:
                            print(f"\n✅✅✅ kb_id 存在于 override_body 中")
                        else:
                            print(f"\n❌❌❌ kb_id 不存在于 override_body 中!")
                            print(f"所有字段: {[i.get('key') for i in body_data]}")
                    else:
                        print(f"❌ body_data 不是 list: {type(body_data)}")
                        print(f"内容: {body_data}")
                
                elif body_type == 'json':
                    print(f"\n[JSON 数据检查]")
                    if isinstance(body_data, dict):
                        kb_id = body_data.get('kb_id')
                        if kb_id:
                            print(f"✅✅✅ kb_id 在 JSON 中: {kb_id}")
                        else:
                            print(f"❌❌❌ kb_id 不在 JSON 中")
                            print(f"JSON 字段: {list(body_data.keys())}")
        else:
            print(f"❌ override_body 不是 dict: {type(step.override_body)}")
        
        # 检查 effective_request_data
        print(f"\n[effective_request_data 检查]")
        effective_data = step.get_effective_request_data()
        print(f"method: {effective_data.get('method')}")
        print(f"url: {effective_data.get('url')}")
        
        body = effective_data.get('body', {})
        print(f"body: {json.dumps(body, indent=2, ensure_ascii=False)}")
        
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
        
    except ScenarioStep.DoesNotExist:
        print(f"❌ 步骤 ID {step_id} 不存在!")
    except Exception as e:
        print(f"❌ 诊断出错: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        step_id = int(sys.argv[1])
        diagnose_scenario_step(step_id)
    else:
        print("使用方法: python diagnostic_script.py <step_id>")
        print("示例: python diagnostic_script.py 123")
