from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0007_create_creator_support_setting')]

    operations = [
        migrations.CreateModel(
            name='ContactSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('visible', models.BooleanField(default=True, verbose_name='Widoczna dla użytkowników')),
            ],
            options={
                'verbose_name': 'Ustawienie kontaktu',
                'verbose_name_plural': 'Kontakt',
            },
        ),
    ]
