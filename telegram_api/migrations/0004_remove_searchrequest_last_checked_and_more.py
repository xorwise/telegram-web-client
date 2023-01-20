# Generated by Django 4.1.5 on 2023-01-16 00:56

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('telegram_api', '0003_alter_channel_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='searchrequest',
            name='last_checked',
        ),
        migrations.AddField(
            model_name='searchrequest',
            name='added_messages',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.IntegerField(), blank=True, default=[0], size=None),
            preserve_default=False,
        ),
    ]
