import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db.models import Count
from apps.api_testing.models import TestSuite
from apps.testcases.models import TestCase

duplicates = (
    TestSuite.objects.filter(mainline_test_case__isnull=False)
    .values('mainline_test_case')
    .annotate(count=Count('id'))
    .filter(count__gt=1)
)
print('重复关联的用例数:', duplicates.count())
for d in duplicates[:5]:
    tc = TestCase.objects.get(id=d['mainline_test_case'])
    print(f'  用例 {tc.id}: {tc.title} 被 {d["count"]} 个套件关联')

linked = TestSuite.objects.filter(mainline_test_case__isnull=False).count()
print('已关联套件的用例数:', linked)
