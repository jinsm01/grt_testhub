#!/usr/bin/env python
import os
import sys

# 添加项目路径
sys.path.insert(0, '/Users/jinshaomin/Documents/jinsm/test_hub/grt_testhub')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

import django
django.setup()

from apps.requirement_analysis.models import KnowledgeGraph
from pathlib import Path

graphs = KnowledgeGraph.objects.order_by('-created_at')[:3]
for g in graphs:
    print(f"ID: {g.id}, Name: {g.name}")
    print(f"Status: {g.status}")
    print(f"Nodes: {g.node_count}, Edges: {g.edge_count}")
    print(f"Working Dir: {g.working_dir}")
    print(f"Error: {g.build_error_message}")
    print(f"Docs: {g.documents.count()}")
    for doc in g.documents.all():
        text_len = len(doc.extracted_text) if doc.extracted_text else 0
        print(f"  - {doc.title}: {text_len} chars")
    
    # 检查工作目录中的文件
    if g.working_dir:
        working_dir = Path(g.working_dir)
        if working_dir.exists():
            print(f"  Working dir exists: {working_dir}")
            files = list(working_dir.glob('*.json'))
            print(f"  JSON files: {[f.name for f in files]}")
        else:
            print(f"  Working dir NOT exists: {working_dir}")
    print("---")
