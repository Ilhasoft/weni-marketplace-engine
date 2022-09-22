# Generated by Django 3.2.4 on 2022-09-22 20:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wpp_templates', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='templatebutton',
            name='translation',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='buttons', to='wpp_templates.templatetranslation'),
        ),
        migrations.AlterField(
            model_name='templateheader',
            name='translation',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='headers', to='wpp_templates.templatetranslation'),
        ),
        migrations.AlterField(
            model_name='templatetranslation',
            name='template',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='translations', to='wpp_templates.templatemessage'),
        ),
    ]
