# Generated by Django 3.1.7 on 2021-09-19 04:07

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0013_subscriber'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='subscriber',
            name='user',
        ),
    ]
