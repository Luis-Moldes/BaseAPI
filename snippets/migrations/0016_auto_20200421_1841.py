# Generated by Django 3.0.5 on 2020-04-21 16:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('snippets', '0015_auto_20200420_1924'),
    ]

    operations = [
        migrations.AlterField(
            model_name='warp',
            name='meanCOG',
            field=models.FloatField(default='WarpRetrieve(boat_id, event)[1]'),
        ),
        migrations.AlterField(
            model_name='warp',
            name='meanSOG',
            field=models.FloatField(default='WarpRetrieve(boat_id, event)[0]'),
        ),
    ]
