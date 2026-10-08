from django.db import migrations


def seed_settings(apps, schema_editor):
    db = schema_editor.connection.alias
    ContactSettings = apps.get_model('core', 'ContactSettings')
    NavigationTab = apps.get_model('core', 'NavigationTab')
    if not ContactSettings.objects.using(db).exists():
        ContactSettings.objects.using(db).create(visible=True)
    for key, _label in [
        ('home', 'Start'),
        ('announcements', 'Ogłoszenia'),
        ('events', 'Spotkania'),
        ('finance', 'Finanse'),
        ('tasks', 'Grafik'),
    ]:
        NavigationTab.objects.using(db).get_or_create(key=key, defaults={'visible': True})


class Migration(migrations.Migration):
    dependencies = [('core', '0009_navigationtab')]

    operations = [migrations.RunPython(seed_settings, migrations.RunPython.noop)]
