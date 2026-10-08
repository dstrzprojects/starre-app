from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0008_contactsettings')]

    operations = [
        migrations.CreateModel(
            name='NavigationTab',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(choices=[('home', 'Start'), ('announcements', 'Ogłoszenia'), ('events', 'Spotkania'), ('finance', 'Finanse'), ('tasks', 'Grafik')], max_length=24, unique=True)),
                ('visible', models.BooleanField(default=True, verbose_name='Widoczna dla użytkowników')),
            ],
            options={
                'verbose_name': 'Ustawienie zakładki',
                'verbose_name_plural': 'Pozostałe zakładki',
                'ordering': ['key'],
            },
        ),
    ]
