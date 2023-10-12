# Generated by Django 4.1 on 2023-10-12 09:18

from django.db import migrations, models
import django.db.models.deletion


def migrate_data(apps, schema_editor):
    SummaryReport = apps.get_model('app', 'SummaryReport')
    Driver = apps.get_model('app', 'Driver')

    for obj in SummaryReport.objects.all():
        name, second_name = obj.full_name.split()
        driver, _ = Driver.objects.get_or_create(name=name, second_name=second_name)
        obj.driver = driver
        obj.save()


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0057_fleetorder_payment_fleetorder_price_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='carefficiency',
            name='clean_kasa',
        ),
        migrations.AddField(
            model_name='summaryreport',
            name='driver',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='app.driver',
                                    verbose_name='Водій'),
        ),
        migrations.RunPython(migrate_data),
        migrations.RemoveField(
            model_name='summaryreport',
            name='full_name',
        ),
        migrations.AddField(
            model_name='payments',
            name='vehicle',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='app.vehicle', verbose_name='Автомобіль'),
        ),
        migrations.AddField(
            model_name='schema',
            name='limit_distance',
            field=models.IntegerField(default=400, verbose_name='Ліміт пробігу за період'),
        ),
        migrations.AddField(
            model_name='schema',
            name='rent_price',
            field=models.IntegerField(default=6, verbose_name='Вартість холостого пробігу'),
        ),
        migrations.AddField(
            model_name='summaryreport',
            name='vehicle',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='app.vehicle', verbose_name='Автомобіль'),
        ),
        migrations.AlterField(
            model_name='driver',
            name='schema',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='app.schema', verbose_name='Схема роботи'),
        ),
    ]
