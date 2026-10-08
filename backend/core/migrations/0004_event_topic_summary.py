from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0003_creatorsupport_address')]

    operations = [
        migrations.AddField(
            model_name='event',
            name='topic_summary',
            field=models.TextField(blank=True, max_length=4000),
        ),
    ]
