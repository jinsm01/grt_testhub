import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection
from django.apps import apps

# 手动添加 AutomationScenario.mainline_test_case 字段到数据库
with connection.schema_editor() as schema_editor:
    AutomationScenario = apps.get_model('api_testing', 'AutomationScenario')
    field = AutomationScenario._meta.get_field('mainline_test_case')
    schema_editor.add_field(AutomationScenario, field)

# 记录迁移已应用
with connection.cursor() as cursor:
    cursor.execute(
        "INSERT INTO django_migrations (app, name, applied) VALUES ('api_testing', '0004_automationscenario_mainline_test_case', NOW())"
    )

print('Added mainline_test_case column and recorded migration')

