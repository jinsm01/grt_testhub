#!/usr/bin/env python
import json
from pathlib import Path

working_dir = Path('/Users/jinshaomin/Documents/jinsm/test_hub/grt_testhub/media/lightrag/project_public/graph_92')

# 检查实体文件
entities_file = working_dir / 'kv_store_entity_chunks.json'
if entities_file.exists():
    with open(entities_file, 'r') as f:
        data = json.load(f)
    print(f'Entity chunks: {len(data)} items')
    print(f'Keys: {list(data.keys())[:5]}')
else:
    print('Entity chunks file not found')

# 检查完整实体文件
full_entities_file = working_dir / 'kv_store_full_entities.json'
if full_entities_file.exists():
    with open(full_entities_file, 'r') as f:
        data = json.load(f)
    print(f'Full entities: {len(data)} items')
    for k, v in list(data.items())[:2]:
        print(f'  {k}: {type(v)} - {len(v) if isinstance(v, (list, dict)) else v}')
else:
    print('Full entities file not found')
