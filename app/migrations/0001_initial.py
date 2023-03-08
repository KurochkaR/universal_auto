# Generated by Django 4.0.5 on 2022-12-19 11:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='FileNameProcessed',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filename_weekly', models.CharField(max_length=150, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Fleet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('fees', models.DecimalField(decimal_places=2, default=0, max_digits=3)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('min_fee', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('polymorphic_ctype', models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='polymorphic_%(app_label)s.%(class)s_set+', to='contenttypes.contenttype')),
            ],
            options={
                'abstract': False,
                'base_manager_name': 'objects',
            },
        ),
        migrations.CreateModel(
            name='GPS',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_time', models.DateTimeField()),
                ('lat', models.DecimalField(decimal_places=4, default=0, max_digits=10)),
                ('lat_zone', models.CharField(max_length=1)),
                ('lon', models.DecimalField(decimal_places=4, default=0, max_digits=10)),
                ('lon_zone', models.CharField(max_length=1)),
                ('speed', models.IntegerField(default=0)),
                ('course', models.IntegerField(default=0)),
                ('height', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('polymorphic_ctype', models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='polymorphic_%(app_label)s.%(class)s_set+', to='contenttypes.contenttype')),
            ],
            options={
                'abstract': False,
                'base_manager_name': 'objects',
            },
        ),
        migrations.CreateModel(
            name='PaymentsOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transaction_uuid', models.UUIDField()),
                ('driver_uuid', models.UUIDField()),
                ('driver_name', models.CharField(max_length=30)),
                ('driver_second_name', models.CharField(max_length=30)),
                ('trip_uuid', models.CharField(max_length=255)),
                ('trip_description', models.CharField(max_length=50)),
                ('organization_name', models.CharField(max_length=50)),
                ('organization_nickname', models.CharField(max_length=50)),
                ('transaction_time', models.DateTimeField()),
                ('paid_to_you', models.DecimalField(decimal_places=2, max_digits=10)),
                ('your_earnings', models.DecimalField(decimal_places=2, max_digits=10)),
                ('cash', models.DecimalField(decimal_places=2, max_digits=10)),
                ('fare', models.DecimalField(decimal_places=2, max_digits=10)),
                ('tax', models.DecimalField(decimal_places=2, max_digits=10)),
                ('fare2', models.DecimalField(decimal_places=2, max_digits=10)),
                ('service_tax', models.DecimalField(decimal_places=2, max_digits=10)),
                ('wait_time', models.DecimalField(decimal_places=2, max_digits=10)),
                ('out_of_city', models.DecimalField(decimal_places=2, max_digits=10)),
                ('tips', models.DecimalField(decimal_places=2, max_digits=10)),
                ('transfered_to_bank', models.DecimalField(decimal_places=2, max_digits=10)),
                ('ajustment_payment', models.DecimalField(decimal_places=2, max_digits=10)),
                ('cancel_payment', models.DecimalField(decimal_places=2, max_digits=10)),
            ],
            options={
                'verbose_name': 'Payments order',
                'verbose_name_plural': 'Payments order',
            },
        ),
        migrations.CreateModel(
            name='RawGPS',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('imei', models.CharField(max_length=100)),
                ('client_ip', models.CharField(max_length=100)),
                ('client_port', models.IntegerField()),
                ('data', models.CharField(max_length=1024)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'GPS Raw',
                'verbose_name_plural': 'GPS Raw',
            },
        ),
        migrations.CreateModel(
            name='ServiceStation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('owner', models.CharField(max_length=150)),
                ('lat', models.DecimalField(decimal_places=4, default=0, max_digits=10)),
                ('lat_zone', models.CharField(max_length=1)),
                ('lon', models.DecimalField(decimal_places=4, default=0, max_digits=10)),
                ('lon_zone', models.CharField(max_length=1)),
                ('description', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='UberTransactions',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transaction_uuid', models.UUIDField(unique=True)),
                ('driver_uuid', models.UUIDField()),
                ('driver_name', models.CharField(max_length=50)),
                ('driver_second_name', models.CharField(max_length=50)),
                ('trip_uuid', models.UUIDField()),
                ('trip_description', models.CharField(max_length=50)),
                ('organization_name', models.CharField(max_length=50)),
                ('organization_nickname', models.CharField(max_length=50)),
                ('transaction_time', models.CharField(max_length=50)),
                ('paid_to_you', models.DecimalField(decimal_places=2, max_digits=10)),
                ('your_earnings', models.DecimalField(decimal_places=2, max_digits=10)),
                ('cash', models.DecimalField(decimal_places=2, max_digits=10)),
                ('fare', models.DecimalField(decimal_places=2, max_digits=10)),
                ('tax', models.DecimalField(decimal_places=2, max_digits=10)),
                ('fare2', models.DecimalField(decimal_places=2, max_digits=10)),
                ('service_tax', models.DecimalField(decimal_places=2, max_digits=10)),
                ('wait_time', models.DecimalField(decimal_places=2, max_digits=10)),
                ('transfered_to_bank', models.DecimalField(decimal_places=2, max_digits=10)),
                ('peak_rate', models.DecimalField(decimal_places=2, max_digits=10)),
                ('tips', models.DecimalField(decimal_places=2, max_digits=10)),
                ('cancel_payment', models.DecimalField(decimal_places=2, max_digits=10)),
            ],
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(blank=True, max_length=255, null=True)),
                ('second_name', models.CharField(blank=True, max_length=255, null=True)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('phone_number', models.CharField(blank=True, max_length=13)),
                ('chat_id', models.CharField(blank=True, max_length=9)),
                ('created_at', models.DateTimeField(auto_now=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Vehicle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('model', models.CharField(max_length=50)),
                ('type', models.CharField(max_length=20)),
                ('licence_plate', models.CharField(max_length=24, unique=True)),
                ('vin_code', models.CharField(max_length=17)),
                ('gps_imei', models.CharField(default='', max_length=100)),
                ('car_status', models.CharField(default='Serviceable', max_length=18)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='WeeklyReportFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('organization_name', models.CharField(max_length=20)),
                ('report_file_name', models.CharField(max_length=255, unique=True)),
                ('report_from', models.CharField(max_length=10)),
                ('report_to', models.CharField(max_length=10)),
                ('file', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='BoltFleet',
            fields=[
                ('fleet_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='app.fleet')),
            ],
            options={
                'abstract': False,
                'base_manager_name': 'objects',
            },
            bases=('app.fleet',),
        ),
        migrations.CreateModel(
            name='Client',
            fields=[
                ('user_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='app.user')),
                ('role', models.CharField(choices=[('CLIENT', 'Client'), ('PARTNER', 'Partner'), ('DRIVER', 'Driver'), ('DRIVER_MANAGER', 'Driver manager'), ('SERVICE_STATION_MANAGER', 'Service station manager'), ('SUPPORT_MANAGER', 'Support manager')], default='CLIENT', max_length=50)),
            ],
            bases=('app.user',),
        ),
        migrations.CreateModel(
            name='Driver',
            fields=[
                ('user_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='app.user')),
                ('role', models.CharField(choices=[('CLIENT', 'Client'), ('PARTNER', 'Partner'), ('DRIVER', 'Driver'), ('DRIVER_MANAGER', 'Driver manager'), ('SERVICE_STATION_MANAGER', 'Service station manager'), ('SUPPORT_MANAGER', 'Support manager')], default='DRIVER', max_length=50)),
                ('driver_status', models.CharField(default='Offline', max_length=35)),
            ],
            bases=('app.user',),
        ),
        migrations.CreateModel(
            name='NewUklonFleet',
            fields=[
                ('fleet_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='app.fleet')),
            ],
            options={
                'abstract': False,
                'base_manager_name': 'objects',
            },
            bases=('app.fleet',),
        ),
        migrations.CreateModel(
            name='UberFleet',
            fields=[
                ('fleet_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='app.fleet')),
            ],
            options={
                'abstract': False,
                'base_manager_name': 'objects',
            },
            bases=('app.fleet',),
        ),
        migrations.CreateModel(
            name='UklonFleet',
            fields=[
                ('fleet_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='app.fleet')),
            ],
            options={
                'abstract': False,
                'base_manager_name': 'objects',
            },
            bases=('app.fleet',),
        ),
        migrations.CreateModel(
            name='UklonPaymentsOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('report_from', models.DateTimeField()),
                ('report_to', models.DateTimeField()),
                ('report_file_name', models.CharField(max_length=255)),
                ('signal', models.CharField(max_length=8)),
                ('licence_plate', models.CharField(max_length=8)),
                ('total_rides', models.PositiveIntegerField()),
                ('total_distance', models.PositiveIntegerField()),
                ('total_amount_cach', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total_amount_cach_less', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total_amount_without_comission', models.DecimalField(decimal_places=2, max_digits=10)),
                ('bonuses', models.DecimalField(decimal_places=2, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'unique_together': {('report_from', 'report_to', 'licence_plate', 'signal')},
            },
        ),
        migrations.CreateModel(
            name='UberPaymentsOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('report_from', models.DateTimeField()),
                ('report_to', models.DateTimeField()),
                ('report_file_name', models.CharField(max_length=255)),
                ('driver_uuid', models.UUIDField()),
                ('first_name', models.CharField(max_length=24)),
                ('last_name', models.CharField(max_length=24)),
                ('total_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total_clean_amout', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total_amount_cach', models.DecimalField(decimal_places=2, max_digits=10)),
                ('transfered_to_bank', models.DecimalField(decimal_places=2, max_digits=10)),
                ('returns', models.DecimalField(decimal_places=2, max_digits=10)),
                ('tips', models.DecimalField(decimal_places=2, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'unique_together': {('report_from', 'report_to', 'driver_uuid')},
            },
        ),
        migrations.CreateModel(
            name='NewUklonPaymentsOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('report_from', models.DateTimeField()),
                ('report_to', models.DateTimeField()),
                ('report_file_name', models.CharField(max_length=255)),
                ('full_name', models.CharField(max_length=255)),
                ('signal', models.CharField(max_length=8)),
                ('total_rides', models.PositiveIntegerField()),
                ('total_distance', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total_amount_cach', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total_amount_cach_less', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total_amount_on_card', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('tips', models.DecimalField(decimal_places=2, max_digits=10)),
                ('bonuses', models.DecimalField(decimal_places=2, max_digits=10)),
                ('fares', models.DecimalField(decimal_places=2, max_digits=10)),
                ('comission', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total_amount_without_comission', models.DecimalField(decimal_places=2, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'unique_together': {('report_from', 'report_to', 'full_name', 'signal')},
            },
        ),
        migrations.CreateModel(
            name='DriverRateLevels',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('threshold_value', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('rate_delta', models.DecimalField(decimal_places=2, default=0, max_digits=3)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('fleet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.fleet')),
            ],
        ),
        migrations.CreateModel(
            name='BoltTransactions',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('driver_name', models.CharField(max_length=50)),
                ('driver_number', models.CharField(max_length=13)),
                ('trip_date', models.CharField(max_length=50)),
                ('payment_confirmed', models.CharField(max_length=50)),
                ('boarding', models.CharField(max_length=255)),
                ('payment_method', models.CharField(max_length=30)),
                ('requsted_time', models.CharField(max_length=5)),
                ('fare', models.DecimalField(decimal_places=2, max_digits=10)),
                ('payment_authorization', models.DecimalField(decimal_places=2, max_digits=10)),
                ('service_tax', models.DecimalField(decimal_places=2, max_digits=10)),
                ('cancel_payment', models.DecimalField(decimal_places=2, max_digits=10)),
                ('tips', models.DecimalField(decimal_places=2, max_digits=10)),
                ('order_status', models.CharField(max_length=50)),
                ('car', models.CharField(max_length=50)),
                ('license_plate', models.CharField(max_length=30)),
            ],
            options={
                'unique_together': {('driver_name', 'driver_number', 'trip_date', 'payment_confirmed', 'boarding')},
            },
        ),
        migrations.CreateModel(
            name='BoltPaymentsOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('report_from', models.DateTimeField()),
                ('report_to', models.DateTimeField()),
                ('report_file_name', models.CharField(max_length=255)),
                ('driver_full_name', models.CharField(max_length=24)),
                ('mobile_number', models.CharField(max_length=24)),
                ('range_string', models.CharField(max_length=50)),
                ('total_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('cancels_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('autorization_payment', models.DecimalField(decimal_places=2, max_digits=10)),
                ('autorization_deduction', models.DecimalField(decimal_places=2, max_digits=10)),
                ('additional_fee', models.DecimalField(decimal_places=2, max_digits=10)),
                ('fee', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total_amount_cach', models.DecimalField(decimal_places=2, max_digits=10)),
                ('discount_cash_trips', models.DecimalField(decimal_places=2, max_digits=10)),
                ('driver_bonus', models.DecimalField(decimal_places=2, max_digits=10)),
                ('compensation', models.DecimalField(decimal_places=2, max_digits=10)),
                ('refunds', models.DecimalField(decimal_places=2, max_digits=10)),
                ('tips', models.DecimalField(decimal_places=2, max_digits=10)),
                ('weekly_balance', models.DecimalField(decimal_places=2, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'unique_together': {('report_from', 'report_to', 'driver_full_name', 'mobile_number')},
            },
        ),
        migrations.CreateModel(
            name='VehicleGPS',
            fields=[
                ('gps_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='app.gps')),
                ('raw_data', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='app.rawgps')),
                ('vehicle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.vehicle')),
            ],
            options={
                'verbose_name': 'GPS Vehicle',
                'verbose_name_plural': 'GPS Vehicle',
            },
            bases=('app.gps',),
        ),
        migrations.AddField(
            model_name='vehicle',
            name='driver',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.RESTRICT, to='app.driver'),
        ),
        migrations.CreateModel(
            name='SupportManager',
            fields=[
                ('user_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='app.user')),
                ('role', models.CharField(choices=[('CLIENT', 'Client'), ('PARTNER', 'Partner'), ('DRIVER', 'Driver'), ('DRIVER_MANAGER', 'Driver manager'), ('SERVICE_STATION_MANAGER', 'Service station manager'), ('SUPPORT_MANAGER', 'Support manager')], default='SUPPORT_MANAGER', max_length=50)),
                ('client_id', models.ManyToManyField(blank=True, to='app.client')),
                ('driver_id', models.ManyToManyField(blank=True, to='app.driver')),
            ],
            bases=('app.user',),
        ),
        migrations.CreateModel(
            name='ServiceStationManager',
            fields=[
                ('user_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='app.user')),
                ('role', models.CharField(choices=[('CLIENT', 'Client'), ('PARTNER', 'Partner'), ('DRIVER', 'Driver'), ('DRIVER_MANAGER', 'Driver manager'), ('SERVICE_STATION_MANAGER', 'Service station manager'), ('SUPPORT_MANAGER', 'Support manager')], default='SERVICE_STATION_MANAGER', max_length=50)),
                ('car_id', models.ManyToManyField(blank=True, to='app.vehicle')),
                ('fleet_id', models.ManyToManyField(blank=True, to='app.fleet')),
                ('service_station', models.OneToOneField(on_delete=django.db.models.deletion.RESTRICT, to='app.servicestation')),
            ],
            bases=('app.user',),
        ),
        migrations.CreateModel(
            name='RepairReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('repair', models.CharField(max_length=255)),
                ('numberplate', models.CharField(max_length=12, unique=True)),
                ('start_of_repair', models.DateTimeField(blank=True)),
                ('end_of_repair', models.DateTimeField(blank=True)),
                ('status_of_payment_repair', models.CharField(default='Unpaid', max_length=6)),
                ('driver', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='app.driver')),
            ],
        ),
        migrations.CreateModel(
            name='Fleets_drivers_vehicles_rate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('driver_external_id', models.CharField(max_length=255)),
                ('rate', models.DecimalField(decimal_places=2, default=0, max_digits=3)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('fleet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.fleet')),
                ('vehicle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.vehicle')),
                ('driver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.driver')),
            ],
        ),
        migrations.CreateModel(
            name='DriverManager',
            fields=[
                ('user_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='app.user')),
                ('role', models.CharField(choices=[('CLIENT', 'Client'), ('PARTNER', 'Partner'), ('DRIVER', 'Driver'), ('DRIVER_MANAGER', 'Driver manager'), ('SERVICE_STATION_MANAGER', 'Service station manager'), ('SUPPORT_MANAGER', 'Support manager')], default='DRIVER_MANAGER', max_length=50)),
                ('driver_id', models.ManyToManyField(blank=True, to='app.driver', verbose_name='Driver')),
            ],
            bases=('app.user',),
        ),
        migrations.AddField(
            model_name='driver',
            name='driver_manager_id',
            field=models.ManyToManyField(blank=True, to='app.drivermanager'),
        ),
        migrations.AddField(
            model_name='driver',
            name='fleet',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='app.fleet'),
        ),
        migrations.AddField(
            model_name='client',
            name='support_manager_id',
            field=models.ManyToManyField(blank=True, to='app.supportmanager'),
        ),
    ]
