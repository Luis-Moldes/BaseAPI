# Generated by Django 3.0.4 on 2020-03-26 16:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('snippets', '0011_auto_20200326_1743'),
    ]

    operations = [
        migrations.AddField(
            model_name='file',
            name='title',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
    ]