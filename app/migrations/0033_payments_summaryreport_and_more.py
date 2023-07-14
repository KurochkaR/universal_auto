# Generated by Django 4.1 on 2023-07-14 12:30

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0032_dashboard_carefficiency_total_kasa_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Payments',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('report_from', models.DateField(verbose_name='Дата звіту')),
                ('vendor_name', models.CharField(default='Ninja', max_length=30, verbose_name='Агрегатор')),
                ('full_name', models.CharField(max_length=255, null=True, verbose_name='ПІ водія')),
                ('driver_id', models.CharField(max_length=50, null=True, verbose_name='Унікальний індифікатор водія')),
                ('total_amount_without_fee', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Чистий дохід')),
                ('total_amount_cash', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Готівкою')),
                ('total_amount_on_card', models.DecimalField(decimal_places=2, default=0, max_digits=10, null=True, verbose_name='На картку')),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10, null=True, verbose_name='Загальна сума')),
                ('tips', models.DecimalField(decimal_places=2, default=0, max_digits=10, null=True, verbose_name='Чайові')),
                ('total_rides', models.PositiveIntegerField(default=0, null=True, verbose_name='Кількість поїздок')),
                ('total_distance', models.DecimalField(decimal_places=2, default=0, max_digits=10, null=True, verbose_name='Пробіг під замовлення')),
                ('bonuses', models.DecimalField(decimal_places=2, default=0, max_digits=10, null=True, verbose_name='Бонуси')),
                ('fee', models.DecimalField(decimal_places=2, default=0, max_digits=10, null=True, verbose_name='Комісія')),
                ('fares', models.DecimalField(decimal_places=2, default=0, max_digits=10, null=True, verbose_name='Штрафи')),
                ('cancels', models.DecimalField(decimal_places=2, default=0, max_digits=10, null=True, verbose_name='Плата за скасування')),
                ('compensations', models.DecimalField(decimal_places=2, default=0, max_digits=10, null=True, verbose_name='Компенсації')),
                ('refunds', models.DecimalField(decimal_places=2, default=0, max_digits=10, null=True, verbose_name='Повернення коштів')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Створено')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
                ('partner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='app.partner', verbose_name='Партнер')),
            ],
            options={
                'verbose_name': 'Звіт',
                'verbose_name_plural': 'Звіти',
                'unique_together': {('report_from', 'driver_id')},
            },
        ),
        migrations.CreateModel(
            name='SummaryReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('report_from', models.DateField(verbose_name='Дата звіту')),
                ('full_name', models.CharField(max_length=255, null=True, verbose_name='ПІ водія')),
                ('total_amount_without_fee', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Чистий дохід')),
                ('total_amount_cash', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Готівкою')),
                ('total_amount_on_card', models.DecimalField(decimal_places=2, max_digits=10, null=True, verbose_name='На картку')),
                ('total_amount', models.DecimalField(decimal_places=2, max_digits=10, null=True, verbose_name='Загальна сума')),
                ('total_rides', models.PositiveIntegerField(null=True, verbose_name='Кількість поїздок')),
                ('total_distance', models.DecimalField(decimal_places=2, max_digits=10, null=True, verbose_name='Пробіг під замовлення')),
                ('tips', models.DecimalField(decimal_places=2, max_digits=10, null=True, verbose_name='Чайові')),
                ('bonuses', models.DecimalField(decimal_places=2, max_digits=10, null=True, verbose_name='Бонуси')),
                ('fee', models.DecimalField(decimal_places=2, max_digits=10, null=True, verbose_name='Комісія')),
                ('fares', models.DecimalField(decimal_places=2, max_digits=10, null=True, verbose_name='Штрафи')),
                ('cancels', models.DecimalField(decimal_places=2, max_digits=10, null=True, verbose_name='Плата за скасування')),
                ('compensations', models.DecimalField(decimal_places=2, max_digits=10, null=True, verbose_name='Компенсації')),
                ('refunds', models.DecimalField(decimal_places=2, max_digits=10, null=True, verbose_name='Повернення коштів')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Створено')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
                ('partner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='app.partner', verbose_name='Партнер')),
            ],
            options={
                'verbose_name': 'Зведений звіт',
                'verbose_name_plural': 'Зведені звіти',
            },
        ),
        migrations.AlterUniqueTogether(
            name='ninjapaymentsorder',
            unique_together=None,
        ),
        migrations.RemoveField(
            model_name='ninjapaymentsorder',
            name='partner',
        ),
        migrations.DeleteModel(
            name='PaymentsOrder',
        ),
        migrations.DeleteModel(
            name='UklonPaymentsOrder',
        ),
        migrations.AlterModelOptions(
            name='boltpaymentsorder',
            options={},
        ),
        migrations.AlterModelOptions(
            name='newuklonpaymentsorder',
            options={},
        ),
        migrations.AlterModelOptions(
            name='uberpaymentsorder',
            options={},
        ),
        migrations.AlterUniqueTogether(
            name='boltpaymentsorder',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='newuklonpaymentsorder',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='uberpaymentsorder',
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name='carefficiency',
            name='end_report',
        ),
        migrations.RemoveField(
            model_name='carefficiency',
            name='start_report',
        ),
        migrations.RemoveField(
            model_name='carefficiency',
            name='vehicle',
        ),
        migrations.RemoveField(
            model_name='ubertrips',
            name='report_file_name',
        ),
        migrations.RemoveField(
            model_name='vehicle',
            name='model',
        ),
        migrations.AddField(
            model_name='carefficiency',
            name='licence_plate',
            field=models.CharField(max_length=25, null=True, verbose_name='Номер автомобіля'),
        ),
        migrations.AddField(
            model_name='carefficiency',
            name='report_from',
            field=models.DateField(default=django.utils.timezone.now, verbose_name='Звіт за'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='jobapplication',
            name='chat_id',
            field=models.CharField(blank=True, max_length=10, verbose_name='Індетифікатор чата'),
        ),
        migrations.AddField(
            model_name='ubertrips',
            name='report_from',
            field=models.DateField(default=django.utils.timezone.now, verbose_name='Дата поїздки'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='vehicle',
            name='manager',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='app.drivermanager', verbose_name='Менеджер авто'),
        ),
        migrations.AlterField(
            model_name='boltpaymentsorder',
            name='driver_full_name',
            field=models.CharField(max_length=24, verbose_name='ПІ водія'),
        ),
        migrations.AlterField(
            model_name='carefficiency',
            name='driver',
            field=models.CharField(max_length=255, null=True, verbose_name='Водій авто'),
        ),
        migrations.AlterField(
            model_name='comment',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Створено'),
        ),
        migrations.AlterField(
            model_name='report_of_driver_debt',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Створено'),
        ),
        migrations.AlterField(
            model_name='uberpaymentsorder',
            name='first_name',
            field=models.CharField(max_length=24, verbose_name='Імя водія'),
        ),
        migrations.AlterField(
            model_name='uberpaymentsorder',
            name='last_name',
            field=models.CharField(max_length=24, verbose_name='Прізвище водія'),
        ),
        migrations.DeleteModel(
            name='NinjaPaymentsOrder',
        ),
    ]