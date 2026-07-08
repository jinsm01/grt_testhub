import re

with open('apps/api_testing/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find class TestSuite
idx = content.find('class TestSuite')
if idx >= 0:
    end = content.find('\n\nclass ', idx + 1)
    print(content[idx:end])
else:
    print('TestSuite not found')

# Find class AutomationSuite
idx = content.find('class AutomationSuite')
if idx >= 0:
    end = content.find('\n\nclass ', idx + 1)
    print('\n--- AutomationSuite ---')
    print(content[idx:end])
