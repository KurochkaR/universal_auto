# Generated by Django 4.1 on 2024-02-15 09:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0083_rawgps_app_rawgps_created_a3530a_idx'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fleetorder',
            name='date_order',
            field=models.DateTimeField(null=True, verbose_name='Дата замовлення'),
        ),
    ]