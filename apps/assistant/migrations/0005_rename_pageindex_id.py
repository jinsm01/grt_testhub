# 重命名 pageindex_id 字段为 vector_collection_id

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('assistant', '0004_add_pageindex_id'),
    ]

    operations = [
        migrations.RenameField(
            model_name='knowledgebasedocument',
            old_name='pageindex_id',
            new_name='vector_collection_id',
        ),
    ]
