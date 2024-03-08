# Generated by Django 4.1 on 2024-03-04 09:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0087_driver_cash_control_driver_cash_rate_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='driverefficiencypolymorphic',
            name='total_orders_accepted',
            field=models.IntegerField(default=0, verbose_name='Прийнято замовлень'),
        ),
        migrations.AlterField(
            model_name='carefficiency',
            name='mileage',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Пробіг, км'),
        ),
        migrations.AlterField(
            model_name='driver',
            name='driver_status',
            field=models.CharField(default='Оффлайн', max_length=35, verbose_name='Статус водія'),
        ),
        migrations.AlterField(
            model_name='driverefficiencypolymorphic',
            name='mileage',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Пробіг, км'),
        ),
        migrations.AlterField(
            model_name='driverefficiencypolymorphic',
            name='total_orders_rejected',
            field=models.IntegerField(default=0, verbose_name='Відмов в замовленнях'),
        ),
    ]