# Simplified migration - only creates TestSuiteReviewRecord model
# Other field changes already exist in database

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('api_testing', '0002_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TestSuiteReviewRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False, verbose_name='是否已删除')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='删除时间')),
                ('status', models.CharField(choices=[('pending', '待评审'), ('approved', '已通过'), ('rejected', '已拒绝')], default='pending', max_length=20, verbose_name='评审状态')),
                ('comment', models.TextField(blank=True, verbose_name='评审意见')),
                ('reviewed_at', models.DateTimeField(blank=True, null=True, verbose_name='评审时间')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('reviewer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='suite_review_records', to=settings.AUTH_USER_MODEL, verbose_name='评审人')),
                ('test_suite', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='review_records', to='api_testing.testsuite', verbose_name='测试套件')),
            ],
            options={
                'verbose_name': '测试套件评审记录',
                'verbose_name_plural': '测试套件评审记录',
                'db_table': 'api_test_suite_review_records',
                'ordering': ['-created_at'],
                'unique_together': {('test_suite', 'reviewer')},
            },
        ),
    ]
