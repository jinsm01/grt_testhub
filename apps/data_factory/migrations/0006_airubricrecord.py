# Generated manually for AIRubricRecord model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('data_factory', '0005_buganalysissummaryrecord'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AIRubricRecord',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='任务名称')),
                ('status', models.CharField(choices=[('running', '生成中'), ('done', '已完成'), ('error', '失败')], default='running', max_length=20, verbose_name='状态')),
                ('source_file', models.FileField(blank=True, null=True, upload_to='rubric/sources/%Y/%m/', verbose_name='源文件')),
                ('source_file_name', models.CharField(blank=True, default='', max_length=255, verbose_name='源文件名')),
                ('note_count', models.IntegerField(default=20, verbose_name='心得数量')),
                ('pass_ratio', models.FloatField(default=0.6, verbose_name='得分心得比例')),
                ('rubric_file', models.FileField(blank=True, null=True, upload_to='rubric/output/%Y/%m/', verbose_name='量表文件(XLSX)')),
                ('notes_file', models.FileField(blank=True, null=True, upload_to='rubric/notes/%Y/%m/', verbose_name='心得文件(DOCX)')),
                ('rubric_data', models.JSONField(default=list, verbose_name='量表数据')),
                ('notes_data', models.JSONField(default=list, verbose_name='心得数据')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='用户')),
            ],
            options={
                'verbose_name': 'AI量表生成记录',
                'verbose_name_plural': 'AI量表生成记录',
                'db_table': 'df_ai_rubric_record',
                'ordering': ['-created_at'],
            },
        ),
    ]