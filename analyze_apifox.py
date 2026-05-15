import json
import re

data = json.load(open('智能体_添加标注.apifox-cli (2).json'))
items = data.get('item', [])

# 构建索引映射
def build_index_map(items):
    index_map = {}
    counter = 0
    
    def process(items):
        nonlocal counter
        for item in items:
            item_type = item.get('type', '')
            meta = item.get('metaInfo', {})
            scope_type = meta.get('scopeType', '')
            
            if item_type == 'group':
                if scope_type == 'start':
                    counter += 1
                elif scope_type == 'end':
                    counter += 1
            elif 'request' in item:
                counter += 1
                index_map[counter - 1] = item.get('name', '')  # Apifox 使用 0-based 索引
            else:
                counter += 1
                
            if 'item' in item:
                process(item['item'])
    
    process(items)
    return index_map

index_map = build_index_map(items)
print("Apifox 索引映射:")
for idx, name in sorted(index_map.items()):
    print(f"  [{idx}]: {name}")

print("\n步骤9是:", index_map.get(9, '不存在'))
