from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0004_event_topic_summary')]

    operations = [
        migrations.CreateModel(
            name='RateLimit',
            fields=[
                ('key', models.CharField(max_length=64, primary_key=True, serialize=False)),
                ('hits', models.PositiveIntegerField(default=0)),
                ('expires_at', models.DateTimeField(db_index=True)),
            ],
        ),
    ]
