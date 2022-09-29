# Generated by Django 3.2.4 on 2022-09-29 14:27

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('wpp_templates', '0007_auto_20220929_1118'),
    ]

    operations = [
        migrations.AlterField(
            model_name='templatemessage',
            name='created_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='created_templatemessages', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='templatemessage',
            name='created_on',
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name='Created on'),
        ),
    ]
