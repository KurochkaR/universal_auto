# Generated by Django 4.1 on 2024-03-22 07:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0091_driverreshuffle_dtp_or_maintenance'),
    ]

    operations = [
        migrations.AddField(
            model_name='carefficiency',
            name='investor',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='app.investor', verbose_name='Інвестор'),
        ),
        migrations.AddField(
            model_name='driverefficiency',
            name='rent_distance',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Холостий пробіг'),
        ),
    ]