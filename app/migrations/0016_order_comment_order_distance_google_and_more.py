# Generated by Django 4.1 on 2023-04-12 11:26

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0015_alter_gps_lat_alter_gps_lon'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='comment',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, to='app.comment'),
        ),
        migrations.AddField(
            model_name='order',
            name='distance_google',
            field=models.CharField(default=0, max_length=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='order',
            name='distance_gps',
            field=models.CharField(default=0, max_length=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='order',
            name='order_time',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Час подачі'),
        ),
        migrations.AddField(
            model_name='order',
            name='to_latitude',
            field=models.CharField(max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='to_longitude',
            field=models.CharField(max_length=10, null=True),
        ),
    ]