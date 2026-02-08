#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 ui_automation.js 中的 API URL，移除重复的 /api 前缀
"""

import re

file_path = r'd:\testhub\grt_testhub\frontend\src\api\ui_automation.js'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换 url: '/api/ui-automation/ 为 url: '/ui-automation/
content = re.sub(r"url: '/api/ui-automation/", "url: '/ui-automation/", content)

# 替换 url: `/api/ui-automation/ 为 url: `/ui-automation/
content = re.sub(r"url: `/api/ui-automation/", "url: `/ui-automation/", content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("修复完成！")
