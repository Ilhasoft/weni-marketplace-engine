# Generated by Django 3.2.4 on 2023-05-29 18:08

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("wpp_templates", "0005_alter_templatemessage_category"),
    ]

    operations = [
        migrations.AddField(
            model_name="templatetranslation",
            name="message_template_id",
            field=models.CharField(blank=True, max_length=20, null=True, unique=True),
        ),
    ]
