# Generated by Django 3.0.5 on 2020-04-25 15:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('snippets', '0017_auto_20200421_1945'),
    ]

    operations = [
        migrations.AlterField(
            model_name='warp',
            name='meanCOG',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='warp',
            name='meanSOG',
            field=models.FloatField(default=0),
        ),
    ]
