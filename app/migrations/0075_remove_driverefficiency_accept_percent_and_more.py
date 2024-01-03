# Generated by Django 4.1 on 2024-01-03 11:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0074_driverefficiencypolymorphic_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='driverefficiency',
            name='accept_percent',
        ),
        migrations.RemoveField(
            model_name='driverefficiency',
            name='average_price',
        ),
        migrations.RemoveField(
            model_name='driverefficiency',
            name='driver',
        ),
        migrations.RemoveField(
            model_name='driverefficiency',
            name='efficiency',
        ),
        migrations.RemoveField(
            model_name='driverefficiency',
            name='id',
        ),
        migrations.RemoveField(
            model_name='driverefficiency',
            name='mileage',
        ),
        migrations.RemoveField(
            model_name='driverefficiency',
            name='online_time',
        ),
        migrations.RemoveField(
            model_name='driverefficiency',
            name='partner',
        ),
        migrations.RemoveField(
            model_name='driverefficiency',
            name='report_from',
        ),
        migrations.RemoveField(
            model_name='driverefficiency',
            name='report_to',
        ),
        migrations.RemoveField(
            model_name='driverefficiency',
            name='road_time',
        ),
        migrations.RemoveField(
            model_name='driverefficiency',
            name='total_kasa',
        ),
        migrations.RemoveField(
            model_name='driverefficiency',
            name='total_orders',
        ),
        migrations.RemoveField(
            model_name='driverefficiency',
            name='vehicles',
        ),
        migrations.AlterField(
            model_name='driverefficiency',
            name='driverefficiencypolymorphic_ptr',
            field=models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='app.driverefficiencypolymorphic'),
        ),
    ]
