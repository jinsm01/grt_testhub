# Generated manually for knowledge base feature

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('assistant', '0002_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='KnowledgeBaseDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=500, verbose_name='文档名称')),
                ('file', models.FileField(upload_to='knowledge_base/%Y/%m/', verbose_name='文档文件')),
                ('file_type', models.CharField(choices=[('pdf', 'PDF'), ('md', 'Markdown'), ('txt', 'Text'), ('doc', 'Word'), ('docx', 'Word')], max_length=10, verbose_name='文件类型')),
                ('file_size', models.BigIntegerField(verbose_name='文件大小(字节)')),
                ('status', models.CharField(choices=[('pending', '待索引'), ('indexing', '索引中'), ('indexed', '已索引'), ('failed', '索引失败')], default='pending', max_length=20, verbose_name='索引状态')),
                ('index_data', models.JSONField(blank=True, null=True, verbose_name='索引数据(PageIndex树结构)')),
                ('index_error', models.TextField(blank=True, verbose_name='索引错误信息')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='kb_documents', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
            ],
            options={
                'verbose_name': '知识库文档',
                'verbose_name_plural': '知识库文档',
                'db_table': 'knowledge_base_documents',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='KnowledgeBaseChat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.TextField(verbose_name='问题')),
                ('answer', models.TextField(verbose_name='回答')),
                ('retrieved_pages', models.JSONField(blank=True, null=True, verbose_name='检索到的页面')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='创建时间')),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chats', to='assistant.knowledgebasedocument', verbose_name='文档')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='kb_chats', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
            ],
            options={
                'verbose_name': '知识库对话',
                'verbose_name_plural': '知识库对话',
                'db_table': 'knowledge_base_chats',
                'ordering': ['-created_at'],
            },
        ),
    ]
