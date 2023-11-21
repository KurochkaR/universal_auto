# Generated by Django 4.1 on 2023-11-21 11:32

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0062_boltrequest_gpsnumber_uagpssynchronizer_uberrequest_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='InvestorPayments',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('report_from', models.DateField(verbose_name='Виплата за')),
                ('sum_before_transaction', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Сума в гривні')),
                ('currency', models.CharField(max_length=4, verbose_name='Валюта покупки')),
                ('currency_rate', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Курс валюти')),
                ('sum_after_transaction', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Сума у валюті')),
                ('investor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='app.investor', verbose_name='Інвестор')),
            ],
            options={
                'verbose_name': 'Виплату інвестору',
                'verbose_name_plural': 'Виплати інвестору',
            },
        ),
        migrations.CreateModel(
            name='PartnerEarnings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('report_from', models.DateField(verbose_name='Дохід з')),
                ('report_to', models.DateField(verbose_name='Дохід по')),
                ('earning', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Сума доходу')),
                ('driver', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='app.driver', verbose_name='Водій')),
                ('partner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='app.partner', verbose_name='Партнер')),
            ],
            options={
                'verbose_name': 'Дохід',
                'verbose_name_plural': 'Доходи',
            },
        ),
        migrations.AddField(
            model_name='driverreshuffle',
            name='partner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='app.partner', verbose_name='Партнер'),
        ),
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(blank=True, max_length=254, null=True, validators=[django.core.validators.EmailValidator()], verbose_name='Електронна пошта'),
        ),
        migrations.AlterField(
            model_name='user',
            name='name',
            field=models.CharField(blank=True, max_length=255, null=True, validators=[django.core.validators.MaxLengthValidator(255)], verbose_name="Ім'я"),
        ),
        migrations.AlterField(
            model_name='user',
            name='phone_number',
            field=models.CharField(blank=True, max_length=13, null=True, validators=[django.core.validators.RegexValidator('^(\\+380|380|80|0)+\\d{9}$')], verbose_name='Номер телефона'),
        ),
        migrations.AlterField(
            model_name='user',
            name='second_name',
            field=models.CharField(blank=True, max_length=255, null=True, validators=[django.core.validators.MaxLengthValidator(255)], verbose_name='Прізвище'),
        ),
        migrations.AlterField(
            model_name='vehicle',
            name='gps_imei',
            field=models.CharField(blank=True, default='', max_length=50, validators=[django.core.validators.MaxLengthValidator(50)]),
        ),
        migrations.AlterField(
            model_name='vehicle',
            name='licence_plate',
            field=models.CharField(max_length=24, unique=True, validators=[django.core.validators.MaxLengthValidator(24)], verbose_name='Номерний знак'),
        ),
        migrations.AlterField(
            model_name='vehicle',
            name='name',
            field=models.CharField(max_length=200, validators=[django.core.validators.MaxLengthValidator(200)], verbose_name='Назва'),
        ),
        migrations.AlterField(
            model_name='vehicle',
            name='vin_code',
            field=models.CharField(blank=True, max_length=17, validators=[django.core.validators.MaxLengthValidator(17)]),
        ),
        migrations.DeleteModel(
            name='TransactionsConversation',
        ),
        migrations.AddField(
            model_name='partnerearnings',
            name='vehicle',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='app.vehicle', verbose_name='Автомобіль'),
        ),
        migrations.AddField(
            model_name='investorpayments',
            name='vehicle',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='app.vehicle', verbose_name='Автомобіль'),
        ),
    ]
