from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0011_alter_creatorsupport_options')]

    operations = [
        migrations.AddField('contactsettings', 'name', models.CharField(blank=True, max_length=180)),
        migrations.AddField('contactsettings', 'email', models.EmailField(blank=True, max_length=254)),
        migrations.AddField('contactsettings', 'phone', models.CharField(blank=True, max_length=30)),
        migrations.AddField('contactsettings', 'address', models.CharField(blank=True, max_length=250)),
    ]
