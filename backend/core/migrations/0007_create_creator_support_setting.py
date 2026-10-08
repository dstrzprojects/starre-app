from django.db import migrations


def ensure_creator_support(apps, schema_editor):
    CreatorSupport = apps.get_model('core', 'CreatorSupport')
    database = schema_editor.connection.alias
    if not CreatorSupport.objects.using(database).exists():
        CreatorSupport.objects.using(database).create(visible=True)


class Migration(migrations.Migration):
    dependencies = [('core', '0006_creatorsupport_visible')]

    operations = [migrations.RunPython(ensure_creator_support, migrations.RunPython.noop)]
