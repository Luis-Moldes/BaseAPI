# Generated by Django 3.0.4 on 2020-03-26 18:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('snippets', '0012_file_title'),
    ]

    operations = [
        migrations.AddField(
            model_name='number',
            name='file',
            field=models.FileField(default='Files/None/No-img.pdf', upload_to='Files/'),
        ),
    ]
