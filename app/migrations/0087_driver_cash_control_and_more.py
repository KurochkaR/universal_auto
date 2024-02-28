# Generated by Django 4.1 on 2024-02-28 12:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0086_deletedvehicle_penaltybonus_created_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='driver',
            name='cash_control',
            field=models.BooleanField(default=True, verbose_name='Контроль готівки'),
        ),
        migrations.AlterField(
            model_name='fleetsdriversvehiclesrate',
            name='pay_cash',
            field=models.BooleanField(default=True, verbose_name='Оплата готівкою'),
        ),
    ]
