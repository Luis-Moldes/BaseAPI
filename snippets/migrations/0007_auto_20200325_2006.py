# Generated by Django 3.0.4 on 2020-03-25 19:06

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('snippets', '0006_remove_number_itle'),
    ]

    operations = [
        migrations.AlterField(
            model_name='number',
            name='owner',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='numbers', to=settings.AUTH_USER_MODEL),
        ),
    ]
