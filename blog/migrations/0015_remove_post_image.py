# Generated by Django 3.1.7 on 2021-04-29 13:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0014_postimage'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='post',
            name='image',
        ),
    ]
