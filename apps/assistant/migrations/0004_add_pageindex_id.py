# Generated manually for PageIndex integration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assistant', '0003_knowledgebasedocument_knowledgebasechat'),
    ]

    operations = [
        migrations.AddField(
            model_name='knowledgebasedocument',
            name='pageindex_id',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='PageIndex索引ID'),
        ),
    ]
