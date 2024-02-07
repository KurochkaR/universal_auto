# Generated by Django 4.1 on 2024-02-05 09:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0081_bonus_vehicle_fleetorder_date_order_and_more'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='vehiclegps',
            index=models.Index(fields=['raw_data'], name='app_vehicle_raw_dat_54650d_idx'),
        ),
        migrations.AddIndex(
            model_name='vehiclegps',
            index=models.Index(condition=models.Q(('raw_data__isnull', True)), fields=['raw_data'], name='raw_data_null'),
        ),
    ]
