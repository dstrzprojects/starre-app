from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('core', '0010_seed_navigation_settings')]

    operations = [
        migrations.AlterModelOptions(
            name='creatorsupport',
            options={'verbose_name': 'Ustawienie wsparcia', 'verbose_name_plural': 'Wsparcie'},
        ),
    ]
