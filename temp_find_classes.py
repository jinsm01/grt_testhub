with open('apps/api_testing/serializers.py', 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
for i, line in enumerate(lines, 1):
    if 'class TestCaseBriefSerializer' in line or 'class AutomationSuiteSerializer' in line:
        print(i, line)
