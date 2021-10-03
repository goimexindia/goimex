# Generated by Django 3.1.7 on 2021-09-19 05:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0015_remove_subscriber_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='whatyouwant',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=60)),
                ('product_want', models.EmailField(max_length=260)),
                ('full_name', models.EmailField(max_length=70)),
                ('company_name', models.EmailField(max_length=120)),
                ('phone_number', models.EmailField(max_length=30)),
                ('type', models.EmailField(max_length=60)),
            ],
        ),
    ]