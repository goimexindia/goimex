# Generated by Django 3.1.7 on 2021-05-05 07:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0019_auto_20210505_1309'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='post',
            options={'ordering': ['created_on']},
        ),
    ]
