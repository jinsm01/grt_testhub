import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute(
        "INSERT INTO django_migrations (app, name, applied) VALUES ('projects', '0003_projectmenu', NOW())"
    )

print('projects migration 0003 marked as applied')
