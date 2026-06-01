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
    print(f"\n=== Graph ID: {g.id}, Name: {g.name} ===")
    print(f"Working Dir: {g.working_dir}")
    
    working_dir = Path(g.working_dir)
    if working_dir.exists():
        print(f"目录存在: {working_dir}")
        files = list(working_dir.glob('*'))
        print(f"文件列表:")
        for f in files:
            size = f.stat().st_size if f.is_file() else 0
            print(f"  - {f.name} ({size} bytes)")
    else:
        print(f"目录不存在: {working_dir}")
