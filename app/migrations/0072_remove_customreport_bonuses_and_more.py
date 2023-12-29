# Generated by Django 4.1 on 2023-12-22 12:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0071_remove_customreport_bonuses_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='customreport',
            name='bonuses',
        ),
        migrations.RemoveField(
            model_name='customreport',
            name='cancels',
        ),
        migrations.RemoveField(
            model_name='customreport',
            name='compensations',
        ),
        migrations.RemoveField(
            model_name='customreport',
            name='driver',
        ),
        migrations.RemoveField(
            model_name='customreport',
            name='fares',
        ),
        migrations.RemoveField(
            model_name='customreport',
            name='fee',
        ),
        migrations.RemoveField(
            model_name='customreport',
            name='full_name',
        ),
        migrations.RemoveField(
            model_name='customreport',
            name='id',
        ),
        migrations.RemoveField(
            model_name='customreport',
            name='partner',
        ),
        migrations.RemoveField(
            model_name='customreport',
            name='refunds',
        ),
        migrations.RemoveField(
            model_name='customreport',
            name='report_from',
        ),
        migrations.RemoveField(
            model_name='customreport',
            name='report_to',
        ),
        migrations.RemoveField(
            model_name='customreport',
            name='rider_id',
        ),
        migrations.RemoveField(
            model_name='customreport',
            name='tips',
        ),
        migrations.RemoveField(
            model_name='customreport',
            name='total_amount',
        ),
        migrations.RemoveField(
            model_name='customreport',
            name='total_amount_cash',
        ),
        migrations.RemoveField(
            model_name='customreport',
            name='total_amount_on_card',
        ),
        migrations.RemoveField(
            model_name='customreport',
            name='total_amount_without_fee',
        ),
        migrations.RemoveField(
            model_name='customreport',
            name='total_distance',
        ),
        migrations.RemoveField(
            model_name='customreport',
            name='total_rides',
        ),
        migrations.RemoveField(
            model_name='customreport',
            name='vehicle',
        ),
        migrations.RemoveField(
            model_name='customreport',
            name='vendor_name',
        ),
        migrations.RemoveField(
            model_name='customuser',
            name='phone_number',
        ),
        migrations.RemoveField(
            model_name='payments',
            name='bonuses',
        ),
        migrations.RemoveField(
            model_name='payments',
            name='cancels',
        ),
        migrations.RemoveField(
            model_name='payments',
            name='compensations',
        ),
        migrations.RemoveField(
            model_name='payments',
            name='created_at',
        ),
        migrations.RemoveField(
            model_name='payments',
            name='driver',
        ),
        migrations.RemoveField(
            model_name='payments',
            name='fares',
        ),
        migrations.RemoveField(
            model_name='payments',
            name='fee',
        ),
        migrations.RemoveField(
            model_name='payments',
            name='full_name',
        ),
        migrations.RemoveField(
            model_name='payments',
            name='id',
        ),
        migrations.RemoveField(
            model_name='payments',
            name='partner',
        ),
        migrations.RemoveField(
            model_name='payments',
            name='refunds',
        ),
        migrations.RemoveField(
            model_name='payments',
            name='report_from',
        ),
        migrations.RemoveField(
            model_name='payments',
            name='report_to',
        ),
        migrations.RemoveField(
            model_name='payments',
            name='rider_id',
        ),
        migrations.RemoveField(
            model_name='payments',
            name='tips',
        ),
        migrations.RemoveField(
            model_name='payments',
            name='total_amount',
        ),
        migrations.RemoveField(
            model_name='payments',
            name='total_amount_cash',
        ),
        migrations.RemoveField(
            model_name='payments',
            name='total_amount_on_card',
        ),
        migrations.RemoveField(
            model_name='payments',
            name='total_amount_without_fee',
        ),
        migrations.RemoveField(
            model_name='payments',
            name='total_distance',
        ),
        migrations.RemoveField(
            model_name='payments',
            name='total_rides',
        ),
        migrations.RemoveField(
            model_name='payments',
            name='updated_at',
        ),
        migrations.RemoveField(
            model_name='payments',
            name='vehicle',
        ),
        migrations.RemoveField(
            model_name='payments',
            name='vendor_name',
        ),
        migrations.RemoveField(
            model_name='summaryreport',
            name='bonuses',
        ),
        migrations.RemoveField(
            model_name='summaryreport',
            name='cancels',
        ),
        migrations.RemoveField(
            model_name='summaryreport',
            name='compensations',
        ),
        migrations.RemoveField(
            model_name='summaryreport',
            name='created_at',
        ),
        migrations.RemoveField(
            model_name='summaryreport',
            name='driver',
        ),
        migrations.RemoveField(
            model_name='summaryreport',
            name='fares',
        ),
        migrations.RemoveField(
            model_name='summaryreport',
            name='fee',
        ),
        migrations.RemoveField(
            model_name='summaryreport',
            name='id',
        ),
        migrations.RemoveField(
            model_name='summaryreport',
            name='partner',
        ),
        migrations.RemoveField(
            model_name='summaryreport',
            name='refunds',
        ),
        migrations.RemoveField(
            model_name='summaryreport',
            name='report_from',
        ),
        migrations.RemoveField(
            model_name='summaryreport',
            name='report_to',
        ),
        migrations.RemoveField(
            model_name='summaryreport',
            name='tips',
        ),
        migrations.RemoveField(
            model_name='summaryreport',
            name='total_amount',
        ),
        migrations.RemoveField(
            model_name='summaryreport',
            name='total_amount_cash',
        ),
        migrations.RemoveField(
            model_name='summaryreport',
            name='total_amount_on_card',
        ),
        migrations.RemoveField(
            model_name='summaryreport',
            name='total_amount_without_fee',
        ),
        migrations.RemoveField(
            model_name='summaryreport',
            name='total_distance',
        ),
        migrations.RemoveField(
            model_name='summaryreport',
            name='total_rides',
        ),
        migrations.RemoveField(
            model_name='summaryreport',
            name='updated_at',
        ),
        migrations.RemoveField(
            model_name='summaryreport',
            name='vehicle',
        ),
        migrations.AlterField(
            model_name='customreport',
            name='driverreport_ptr',
            field=models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='app.driverreport'),
        ),
        migrations.AlterField(
            model_name='customreport',
            name='vendor',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.fleet', verbose_name='Агрегатор'),
        ),
        migrations.AlterField(
            model_name='driverreshuffle',
            name='partner',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='app.partner', verbose_name='Партнер'),
        ),
        migrations.AlterField(
            model_name='payments',
            name='driverreport_ptr',
            field=models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='app.driverreport'),
        ),
        migrations.AlterField(
            model_name='payments',
            name='vendor',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.fleet', verbose_name='Агрегатор'),
        ),
        migrations.AlterField(
            model_name='summaryreport',
            name='driverreport_ptr',
            field=models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='app.driverreport'),
        ),
        migrations.CreateModel(
            name='DailyReport',
            fields=[
                ('driverreport_ptr',
                 models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True,
                                      primary_key=True, serialize=False, to='app.driverreport')),
                ('vendor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.fleet',
                                             verbose_name='Агрегатор')),
            ],
            options={
                'abstract': False,
                'base_manager_name': 'objects',
            },
            bases=('app.driverreport',),
        ),
    ]
