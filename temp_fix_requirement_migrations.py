import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute(
        "INSERT INTO django_migrations (app, name, applied) VALUES ('requirement_analysis', '0002_aimodelconfig_businessrequirement_generationconfig_and_more', NOW())"
    )
    cursor.execute(
        "INSERT INTO django_migrations (app, name, applied) VALUES ('requirement_analysis', '0003_knowledgegraphversion', NOW())"
    )

print('requirement_analysis migrations 0002/0003 marked as applied')
