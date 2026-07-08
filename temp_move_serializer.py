import re

with open('apps/api_testing/serializers.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find TestCaseBriefSerializer class
match = re.search(r'class TestCaseBriefSerializer\(serializers\.ModelSerializer\):.*?(?=\n\nclass |\Z)', content, re.DOTALL)
if not match:
    print('TestCaseBriefSerializer not found')
    exit(1)

serializer_class = match.group(0)

# Remove it from current position
content = content[:match.start()] + content[match.end():]

# Find AutomationSuiteSerializer and insert before it
insert_pos = content.find('class AutomationSuiteSerializer(serializers.ModelSerializer):')
if insert_pos == -1:
    print('AutomationSuiteSerializer not found')
    exit(1)

content = content[:insert_pos] + serializer_class + '\n\n\n' + content[insert_pos:]

with open('apps/api_testing/serializers.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Moved TestCaseBriefSerializer before AutomationSuiteSerializer')
