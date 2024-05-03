import os
from contextlib import contextmanager
from datetime import datetime, timedelta, time
import time as tm
from functools import wraps

import requests
from _decimal import Decimal, ROUND_HALF_UP
from celery import chain
from celery.exceptions import MaxRetriesExceededError
from celery.utils.log import get_task_logger
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.utils import timezone
from celery.schedules import crontab
from django_celery_beat.models import IntervalSchedule, PeriodicTask
from telegram import ParseMode
from telegram.error import BadRequest
from app.models import (RawGPS, Vehicle, Order, Driver, JobApplication, ParkSettings, UseOfCars, CarEfficiency,
                        Payments, SummaryReport, Manager, Partner, DriverEfficiency, FleetOrder, ReportTelegramPayments,
                        InvestorPayments, VehicleSpending, DriverReshuffle, DriverPayments,
                        TaskScheduler, DriverEffVehicleKasa, Schema, CustomReport, Fleet,
                        VehicleGPS, PartnerEarnings, Investor, Bonus, Penalty, PaymentsStatus,
                        FleetsDriversVehiclesRate, DriverEfficiencyFleet, WeeklyReport, SalaryCalculation, Category,
                        PenaltyCategory, ChargeTransactions, PenaltyBonus)
from django.db.models import Sum, IntegerField, FloatField, DecimalField, Q
from django.db.models.functions import Cast, Coalesce
from app.utils import get_schedule, create_task
from auto.utils import payment_24hours_create, summary_report_create, compare_reports, get_corrections, \
    get_currency_rate, polymorphic_efficiency_create, calendar_weekly_report, create_share_investor_earn, \
    create_proportional_investor_earn, create_investor_payments, create_charge_penalty, generate_cash_text
from auto_bot.handlers.driver.keyboards import inline_bolt_report_keyboard
from auto_bot.handlers.driver_manager.utils import get_daily_report, get_efficiency, generate_message_report, \
    get_driver_efficiency_report, calculate_rent, get_vehicle_income, get_time_for_task, \
    create_driver_payments, calculate_income_partner, get_failed_income, find_reshuffle_period, get_today_statistic, \
    calculate_bolt_kasa, send_notify_to_check_car, add_bonus_earnings, get_start_week_time
from auto_bot.handlers.order.keyboards import inline_markup_accept, inline_search_kb, inline_client_spot, \
    inline_spot_keyboard, inline_second_payment_kb, inline_reject_order, personal_order_end_kb, \
    personal_driver_end_kb
from auto_bot.handlers.order.static_text import decline_order, order_info, search_driver_1, \
    search_driver_2, no_driver_in_radius, driver_arrived, driver_complete_text, \
    order_customer_text, search_driver, personal_time_route_end, personal_order_info, \
    pd_order_not_accepted, driver_text_personal_end, client_text_personal_end, payment_text
from auto_bot.handlers.order.utils import text_to_client, check_vehicle, check_reshuffle
from auto_bot.main import bot
from scripts.conversion import convertion, haversine, get_location_from_db
from auto.celery import app

from scripts.redis_conn import redis_instance
from app.bolt_sync import BoltRequest
from selenium_ninja.ecofactor import EcoFactorRequest
from selenium_ninja.synchronizer import AuthenticationError
from app.uagps_sync import UaGpsSynchronizer
from app.uber_sync import UberRequest
from app.uklon_sync import UklonRequest
from taxi_service.utils import login_in, get_start_end

logger = get_task_logger(__name__)


def retry_logic(exc, retries):
    retry_delay = 30 * (retries + 1)
    logger.warning(f"Retry attempt {retries + 1} in {retry_delay} seconds. Exception: {exc}")
    return retry_delay


@contextmanager
def memcache_lock(lock_id, task_kwargs, oid, lock_time, finish_lock_time=10):
    timeout_at = tm.monotonic() + lock_time - 3
    task_hash = hash(frozenset(task_kwargs.items()))
    lock_key = f'task_lock:{lock_id}:{task_hash}'
    status = cache.add(lock_key, oid, lock_time)
    try:
        yield status
    finally:
        # memcache delete is very slow, but we have to use it to take
        # advantage of using add() for atomic locking
        if tm.monotonic() < timeout_at and status:
            cache.set(lock_key, oid, finish_lock_time)
            # don't release the lock if we exceeded the timeout
            # to lessen the chance of releasing an expired lock
            # owned by someone else
            # also don't release the lock if we didn't acquire it


# def lock_task(func):
#     @wraps(func)
#     def wrapper(*args, **kwargs):
#         partner_pk = kwargs.get("partner_pk")
#         print(partner_pk)
#         if not partner_pk:
#             schemas = Schema.objects.filter(pk__in=kwargs.get("schemas", set()))
#             payment = DriverPayments.objects.filter(pk=kwargs.get("payment_id"))
#             if schemas.exists():
#                 partner_pk = schemas.first().partner_id
#             elif payment.exists():
#                 partner_pk = payment.first().partner_id
#             else:
#                 return func(*args, **kwargs)
#         lock_key = f'lock:{partner_pk}'
#         # Attempt to acquire the lock
#         lock_acquired = redis_instance().set(lock_key, 'locked', nx=True, ex=450)
#         if not lock_acquired:
#
#             from celery import current_task
#             bot.send_message(chat_id=515224934, text=f"{current_task.name} locked")
#             current_task.retry(countdown=30 * (current_task.request.retries + 1))
#
#         # Lock acquired, execute the task
#         try:
#             return func(*args, **kwargs)
#         finally:
#             # Release the lock after task execution
#             redis_instance().delete(lock_key)
#
#     return wrapper


@app.task()
def raw_gps_handler():
    raw_list = RawGPS.objects.filter(vehiclegps__isnull=True).order_by('created_at')[:1000]
    count = 0
    for raw in raw_list:
        data = raw.data.split(';')
        try:
            lat, lon = convertion(data[2]), convertion(data[4])
        except ValueError:
            lat, lon = 0, 0
        try:
            date_time = timezone.datetime.strptime(data[0] + data[1], '%d%m%y%H%M%S')
            date_time = timezone.make_aware(date_time)
        except ValueError as err:
            logger.error(f'Error converting date and time: {err}')
            continue
        vehicle = Vehicle.objects.filter(gps_imei=raw.imei)
        kwa = {
            'date_time': date_time,
            'lat': lat,
            'vehicle': vehicle.first(),
            'lat_zone': data[3],
            'lon': lon,
            'lon_zone': data[5],
            'speed': float(data[6]) if data[6] != 'NA' else 0,
            'course': float(data[7]) if data[7] != 'NA' else 0,
            'height': float(data[8]) if data[8] != 'NA' else 0,
            'raw_data': raw
        }
        try:
            VehicleGPS.objects.create(**kwa)
            count += 1
        except IntegrityError as e:
            logger.error(e)
        # vehicle.update(lat=lat, lon=lon, coord_time=date_time)
    logger.warning(f"GPS created {count}")


@app.task(bind=True, ignore_result=False)
def get_session(self, **kwargs):
    aggregator = kwargs.get("aggregator")
    partner_pk = kwargs.get("partner_pk")
    password = kwargs.get("password")
    login = kwargs.get("login")
    try:
        fleet = Fleet.objects.get(name=aggregator, partner=partner_pk, deleted_at__isnull=False)
    except ObjectDoesNotExist:
        fleet = Fleet.objects.get(name=aggregator, partner=None)
    token = fleet.create_session(partner_pk, password, login)
    if token:
        login_in(aggregator=aggregator, partner_id=partner_pk,
                 login_name=login, password=password, token=token)
        obj, created = fleet.objects.get_or_create(name=aggregator, partner_id=partner_pk)
        if not created:
            obj.deleted_at = None
            obj.save(update_fields=['deleted_at'])


@app.task(bind=True, queue='bot_tasks')
def remove_gps_partner(self, partner_pk):
    if redis_instance().exists(f"{partner_pk}_remove_gps"):
        bot.send_message(chat_id=ParkSettings.get_value("DEVELOPER_CHAT_ID"),
                         text="Не вдалося отримати дані по Gps, будь ласка, перевірте оплату послуги")
        redis_instance().delete(f"{partner_pk}_remove_gps")


@app.task(bind=True, retry_backoff=30, max_retries=3)
def get_today_orders(self, **kwargs):
    partner = kwargs.get("partner_pk")
    wrong_cars = {}
    try:
        fleets = Fleet.objects.filter(partner=partner, deleted_at=None).exclude(name__in=['Gps', 'Ninja'])
        start_day, end = get_start_end('today', kwargs.get("day"))[:2]
        start = start_day - timedelta(hours=1)
        for fleet in fleets:
            if isinstance(fleet, UberRequest):
                drivers = Driver.objects.get_active(partner=partner, fleetsdriversvehiclesrate__fleet=fleet)
                driver_ids = drivers.values_list('fleetsdriversvehiclesrate__driver_external_id', flat=True)
                wrong_cars.update(fleet.get_fleet_orders(start, end, driver_ids=driver_ids))
            else:
                wrong_cars.update(fleet.get_fleet_orders(start, end))
        send_notify_to_check_car(wrong_cars, partner)
    except Exception as e:
        logger.error(e)
        retry_delay = retry_logic(e, self.request.retries + 1)
        raise self.retry(exc=e, countdown=retry_delay)


@app.task(bind=True)
def null_vehicle_orders(self, **kwargs):
    partner_pk = kwargs.get("partner_pk")
    start, end = get_start_end('today', kwargs.get("day"))[:2]
    active_drivers = Driver.objects.get_active(partner=partner_pk)
    filter_query = Q(partner=partner_pk, vehicle__isnull=True,
                     state__in=[FleetOrder.COMPLETED, FleetOrder.CLIENT_CANCEL, FleetOrder.SYSTEM_CANCEL],
                     date_order__range=(start - timedelta(hours=end.hour), end),
                     driver__in=active_drivers)
    orders = FleetOrder.objects.filter(filter_query)
    for order in orders:
        vehicle = check_vehicle(order.driver, order.date_order)
        if vehicle:
            order.vehicle = vehicle
            order.save(update_fields=['vehicle'])


@app.task(bind=True, retry_backoff=30, max_retries=3)
def add_distance_for_order(self, **kwargs):
    partner = kwargs.get("partner_pk")
    driver = kwargs.get("driver")
    gps_query = UaGpsSynchronizer.objects.filter(partner=partner)
    if gps_query.exists():
        start, end = get_start_end('today', kwargs.get("day"))[:2]
        filter_query = Q(partner=partner, vehicle__isnull=False,
                         state=FleetOrder.COMPLETED, distance__isnull=True, finish_time__isnull=False,
                         vehicle__gps__isnull=False, date_order__range=(start - timedelta(hours=end.hour), end))
        if driver:
            filter_query &= Q(driver=driver)
        orders = FleetOrder.objects.filter(filter_query)
        gps = gps_query.first()
        gps.get_order_distance(orders)


@app.task(bind=True, retry_backoff=30, max_retries=4)
def check_card_cash_value(self, **kwargs):
    partner_pk = kwargs.get("partner_pk")
    try:
        start_week, today = get_start_end('current_week')[:2]
        for driver in Driver.objects.get_active(partner=partner_pk, schema__isnull=False, cash_control=True):
            if driver.schema.is_weekly():
                start = start_week
            else:
                start_time = get_time_for_task(driver.schema_id)[2]
                today_start = timezone.make_aware(datetime.combine(timezone.localtime(), driver.schema.shift_time))
                start = today_start if timezone.localtime() > today_start else start_time
            rent = calculate_rent(start_week, today, driver) if driver.schema.is_weekly() else 0
            penalties = driver.get_penalties()
            rent_payment = rent * driver.schema.rent_price
            kasa, card = get_today_statistic(start, today, driver)[:2]
            if kasa > driver.schema.cash:
                ratio = (card - rent_payment - penalties) / kasa
                without_rent = (card - penalties) / kasa
                rate = driver.cash_rate if driver.cash_rate else driver.schema.rate
                enable = int(ratio > (1 - rate))
                rent_enable = int(without_rent > (1 - rate))
                fleets = Fleet.objects.filter(
                    fleetsdriversvehiclesrate__driver=driver, deleted_at__isnull=True).exclude(name="Ninja").distinct()
                disabled = []
                for fleet in fleets:
                    driver_rate = FleetsDriversVehiclesRate.objects.filter(
                        driver=driver, fleet=fleet, deleted_at__isnull=True).first()
                    if int(driver_rate.pay_cash) != enable:
                        result = fleet.disable_cash(driver_rate.driver_external_id, enable)
                        disabled.append(result)
                if disabled:
                    text = generate_cash_text(driver, kasa, card, penalties, rent,
                                              rent_payment, ratio, rate, enable, rent_enable)
                    bot.send_message(chat_id=ParkSettings.get_value("CASH_CHAT", partner=partner_pk),
                                     text=text)
    except Exception as e:
        logger.error(e)
        retry_delay = retry_logic(e, self.request.retries + 1)
        raise self.retry(exc=e, countdown=retry_delay)


@app.task(bind=True, retry_backoff=30, max_retries=4)
def download_daily_report(self, **kwargs):
    try:
        schemas = kwargs.get("schemas")
        schema_obj = Schema.objects.filter(pk__in=schemas).first()
        if schema_obj.is_weekly() or schema_obj.shift_time == time.min:
            return
        start, end = get_time_for_task(schema_obj.pk, kwargs.get("day"))[:2]
        drivers = Driver.objects.get_active(schema__in=schemas)
        fleets = Fleet.objects.filter(fleetsdriversvehiclesrate__driver__in=drivers,
                                      deleted_at__isnull=True).exclude(name="Ninja").distinct()
        for fleet in fleets:
            driver_ids = drivers.filter(fleetsdriversvehiclesrate__fleet=fleet).values_list(
                'fleetsdriversvehiclesrate__driver_external_id', flat=True)
            fleet.save_daily_custom(start, end, driver_ids)
    except Exception as e:
        logger.error(e)
        retry_delay = retry_logic(e, self.request.retries + 1)
        raise self.retry(exc=e, countdown=retry_delay)


@app.task(bind=True, retry_backoff=30, max_retries=4)
def download_nightly_report(self, **kwargs):
    partner_pk = kwargs.get("partner_pk")
    schemas = Schema.objects.filter(partner=partner_pk)
    try:
        start, end = get_start_end('yesterday', kwargs.get("day"))[:2]
        drivers = Driver.objects.get_active(schema__in=schemas)
        fleets = Fleet.objects.filter(partner=partner_pk, deleted_at=None).exclude(name='Gps')
        for fleet in fleets:
            driver_ids = drivers.filter(fleetsdriversvehiclesrate__fleet=fleet).values_list(
                'fleetsdriversvehiclesrate__driver_external_id', flat=True)
            fleet.save_custom_report(start, end, driver_ids)
    except Exception as e:
        logger.error(e)
        retry_delay = retry_logic(e, self.request.retries + 1)
        raise self.retry(exc=e, countdown=retry_delay)
    # save_report_to_ninja_payment(start, end, partner_pk, schema)


@app.task(bind=True, retry_backoff=30, max_retries=4)
def download_weekly_report(self, **kwargs):
    try:
        start, end = get_start_end('last_week')[:2]
        fleets = Fleet.objects.filter(partner=kwargs.get("partner_pk"), deleted_at=None).exclude(name='Gps')
        for fleet in fleets:
            driver_ids = Driver.objects.get_active(fleetsdriversvehiclesrate__fleet=fleet).values_list(
                'fleetsdriversvehiclesrate__driver_external_id', flat=True)
            fleet.save_weekly_report(start, end, driver_ids)
        #     for report in reports:
        #         compare_reports(fleet, start, end, report.driver, report, CustomReport, partner_pk)
        # for driver in Driver.objects.get_active(partner=partner_pk):
        #     get_corrections(start, end, driver)
    except Exception as e:
        logger.error(e)
        retry_delay = retry_logic(e, self.request.retries + 1)
        raise self.retry(exc=e, countdown=retry_delay)


@app.task(bind=True, retry_backoff=30, max_retries=1)
def check_daily_report(self, partner_pk, start=None, end=None):
    try:
        if not start and not end:
            today = timezone.localtime()
            start = timezone.make_aware(datetime.combine(today - timedelta(days=2), time.min))
            end = timezone.make_aware(datetime.combine(start, time.max))
        while start <= end:
            if redis_instance().exists(f"check_daily_report_error_{partner_pk}"):
                start_str = redis_instance().get(f"check_daily_report_error_{partner_pk}")
                redis_instance().delete(f"check_daily_report_error_{partner_pk}")
                start = timezone.make_aware(datetime.strptime(start_str, '%Y-%m-%d %H:%M:%S'))
            fleets = Fleet.objects.filter(partner=partner_pk, deleted_at=None).exclude(name='Gps')
            for fleet in fleets:
                reports = fleet.save_daily_report(start, end)
                for report in reports:
                    compare_reports(fleet, start, end, report.driver, report, CustomReport, partner_pk)
            for driver in Driver.objects.get_active(partner=partner_pk):
                get_corrections(start, end, driver)
            start += timedelta(days=1)
    except Exception as e:
        str_start = start.strftime('%Y-%m-%d %H:%M:%S')
        redis_instance().set(f"check_daily_report_error_{partner_pk}", str_start, ex=1200)
        logger.error(e)
        retry_delay = retry_logic(e, self.request.retries + 1)
        raise self.retry(exc=e, countdown=retry_delay)


@app.task(bind=True)
def generate_payments(self, **kwargs):
    for driver in Driver.objects.get_active(schema__in=kwargs.get("schemas")):
        end, start_time = get_time_for_task(driver.schema.pk, kwargs.get("day"))[1:3]
        start = timezone.make_aware(datetime.combine(start_time, time.max.replace(microsecond=0)))
        fleets = Fleet.objects.filter(fleetsdriversvehiclesrate__driver=driver, deleted_at=None).exclude(
            name="Ninja").distinct()
        for fleet in fleets:
            payment_24hours_create(start, end, fleet, driver, driver.partner)


@app.task(bind=True)
def generate_summary_report(self, **kwargs):
    for driver in Driver.objects.get_active(schema__in=kwargs.get("schemas")):
        end, start = get_time_for_task(driver.schema.pk, kwargs.get("day"))[1:3]
        summary_report_create(start, end, driver, driver.partner)


@app.task(bind=True)
def get_car_efficiency(self, **kwargs):
    partner_pk = kwargs.get("partner_pk")
    start, end = get_start_end("yesterday", kwargs.get("day"))[:2]
    if Fleet.objects.filter(partner=partner_pk, deleted_at=None, name="Gps").exists():
        for vehicle in Vehicle.objects.get_active(
                partner=partner_pk, gps__isnull=False).select_related('gps', 'branding'):
            efficiency = CarEfficiency.objects.filter(report_from=start,
                                                      partner=partner_pk,
                                                      vehicle=vehicle)
            if efficiency.exists():
                continue
            if vehicle.branding:
                orders_count = FleetOrder.objects.filter(
                    date_order__range=(start, end),
                    vehicle=vehicle, fleet=vehicle.branding.name, state=FleetOrder.COMPLETED).count()
            else:
                orders_count = 0

            vehicle_drivers = {}
            total_spending = VehicleSpending.objects.filter(
                vehicle=vehicle, created_at__range=(start, end)).aggregate(
                spending=Coalesce(Sum('amount'), Decimal(0)))['spending']
            drivers = DriverReshuffle.objects.filter(end_time__lte=end,
                                                     swap_time__gte=start,
                                                     swap_vehicle=vehicle,
                                                     partner=partner_pk,
                                                     driver_start__isnull=False).values_list('driver_start', flat=True)
            total_kasa = 0

            total_km = UaGpsSynchronizer.objects.get(partner=partner_pk).total_per_day(vehicle.gps.gps_id, start, end)
            if total_km:
                for driver in drivers:
                    fleets = Fleet.objects.filter(fleetsdriversvehiclesrate__driver=driver, deleted_at=None).distinct()
                    driver_kasa = 0
                    for fleet in fleets:
                        if isinstance(fleet, UberRequest):
                            result = fleet.generate_vehicle_report(start, end, [vehicle])
                            driver_kasa += Decimal(result[0]['totalEarnings']) if result else 0
                        else:
                            filter_request = Q(Q(driver=driver, fleet=fleet.name, vehicle=vehicle) &
                                               Q(Q(state=FleetOrder.COMPLETED, finish_time__range=(start, end)) |
                                                 Q(state__in=[FleetOrder.CLIENT_CANCEL, FleetOrder.SYSTEM_CANCEL],
                                                   accepted_time__range=(start, end)))
                                               )
                            orders = FleetOrder.objects.filter(filter_request).aggregate(
                                total_price=Coalesce(Sum('price'), 0),
                                total_tips=Coalesce(Sum('tips'), 0))
                            driver_kasa += orders['total_price'] * (1 - fleet.fees) + orders['total_tips']
                    vehicle_drivers[driver] = driver_kasa
                    total_kasa += driver_kasa
            result = max(
                Decimal(total_kasa) - Decimal(total_spending), Decimal(0)) / Decimal(total_km) if total_km else 0
            car = CarEfficiency.objects.create(report_from=start,
                                               report_to=end,
                                               vehicle=vehicle,
                                               total_kasa=total_kasa,
                                               total_spending=total_spending,
                                               mileage=total_km,
                                               efficiency=result,
                                               total_brand_trips=orders_count,
                                               partner_id=partner_pk,
                                               investor=vehicle.investor_car)
            for driver, kasa in vehicle_drivers.items():
                DriverEffVehicleKasa.objects.create(driver_id=driver, efficiency_car=car, kasa=kasa)


@app.task(bind=True)
def get_driver_efficiency(self, **kwargs):
    partner_pk = kwargs.get("partner_pk")
    start, end = get_start_end("yesterday", kwargs.get("day"))[:2]
    if Fleet.objects.filter(partner=partner_pk, deleted_at=None, name="Gps").exists():
        road_mileage = UaGpsSynchronizer.objects.get(
            partner=partner_pk).get_road_distance(start, end, payment=True)
        for driver in Driver.objects.get_active(partner=partner_pk):
            polymorphic_efficiency_create(DriverEfficiency, partner_pk, driver,
                                          start, end, CustomReport, road_mileage=road_mileage)


@app.task(bind=True)
def get_driver_efficiency_fleet(self, **kwargs):
    partner_pk = kwargs.get("partner_pk")
    start, end = get_start_end("yesterday", kwargs.get("day"))[:2]
    if Fleet.objects.filter(partner=partner_pk, deleted_at=None, name="Gps").exists():
        for driver in Driver.objects.get_active(partner=partner_pk):
            fleets = Fleet.objects.filter(
                fleetsdriversvehiclesrate__driver=driver, deleted_at=None).exclude(name="Ninja").distinct()
            for fleet in fleets:
                polymorphic_efficiency_create(DriverEfficiencyFleet, partner_pk, driver,
                                              start, end, CustomReport, fleet)


@app.task(bind=True)
def update_driver_status(self, **kwargs):
    partner_pk = kwargs.get("partner_pk")
    with memcache_lock(self.name, self.request.kwargs, self.app.oid, 600) as acquired:
        if acquired:
            status_online = set()
            status_with_client = set()
            fleets = Fleet.objects.filter(partner=partner_pk, deleted_at=None).exclude(name='Gps')
            for fleet in fleets:
                statuses = fleet.get_drivers_status(kwargs.get('photo')) if isinstance(fleet,
                                                                         BoltRequest) else fleet.get_drivers_status()
                status_online = status_online.union(set(statuses['wait']))
                status_with_client = status_with_client.union(set(statuses['with_client']))
            drivers = Driver.objects.get_active(partner=partner_pk)
            for driver in drivers:
                active_order = Order.objects.filter(driver=driver, status_order=Order.IN_PROGRESS)
                # work_ninja = UseOfCars.objects.filter(user_vehicle=driver, partner=partner_pk,
                #                                       created_at__date=timezone.localtime().date(), end_at=None).first()
                if active_order or (driver.name, driver.second_name) in status_with_client:
                    current_status = Driver.WITH_CLIENT
                elif (driver.name, driver.second_name) in status_online:
                    current_status = Driver.ACTIVE
                else:
                    current_status = Driver.OFFLINE
                driver.driver_status = current_status
                driver.save(update_fields=['driver_status'])
                # if current_status != Driver.OFFLINE:
                #     vehicle = check_vehicle(driver)
                #     if not work_ninja and vehicle and driver.chat_id:
                #         UseOfCars.objects.create(user_vehicle=driver,
                #                                  partner_id=partner_pk,
                #                                  licence_plate=vehicle.licence_plate,
                #                                  chat_id=driver.chat_id)
                # else:
                #     if work_ninja:
                #         work_ninja.end_at = timezone.localtime()
                #         work_ninja.save()
        else:
            logger.info(f'{self.name}: passed')


@app.task(bind=True, ignore_result=False)
def update_driver_data(self, **kwargs):
    fleets = Fleet.objects.filter(partner=kwargs.get("partner_pk"), deleted_at=None)
    for synchronization_class in fleets:
        synchronization_class.synchronize()
    return kwargs.get("manager_id")


@app.task(bind=True, queue='bot_tasks', retry_backoff=30, max_retries=4)
def send_on_job_application_on_driver(self, job_id):
    try:
        candidate = JobApplication.objects.get(id=job_id)
        UklonRequest.add_driver(candidate)
        BoltRequest.add_driver(candidate)
        logger.info('The job application has been sent')
    except Exception as e:
        logger.error(e)
        retry_delay = retry_logic(e, self.request.retries + 1)
        raise self.retry(exc=e, countdown=retry_delay)


@app.task(bind=True)
def schedule_for_detaching_uklon(self, **kwargs):
    partner_pk = kwargs.get("partner_pk")
    today = timezone.localtime()
    desired_time = today + timedelta(hours=1)
    for vehicle in Vehicle.objects.get_active(partner=partner_pk):
        reshuffle = DriverReshuffle.objects.filter(~Q(end_time__time=time(23, 59, 59)),
                                                   swap_time__date=today.date(),
                                                   swap_vehicle=vehicle,
                                                   end_time__range=(today, desired_time),
                                                   partner=partner_pk,
                                                   driver_start__isnull=False).first()
        if reshuffle:
            eta = timezone.localtime(reshuffle.end_time)
            detaching_the_driver_from_the_car.apply_async(kwargs={"partner_pk": partner_pk,
                                                                  "licence_plate":reshuffle.swap_vehicle.licence_plate,
                                                                  "eta":eta}, eta=eta)


@app.task(bind=True, retry_backoff=30, max_retries=1)
def detaching_the_driver_from_the_car(self, **kwargs):
    try:
        with memcache_lock(self.name, self.request.kwargs, self.app.oid, 600, 60) as acquired:
            if acquired:
                bot.send_message(chat_id=ParkSettings.get_value('DEVELOPER_CHAT_ID'),
                                 text=f'Авто {kwargs.get("licence_plate")} відключено {kwargs.get("eta")}')
                # fleet = UklonRequest.objects.get(partner=partner_pk)
                # fleet.detaching_the_driver_from_the_car(licence_plate)
                # logger.info(f'Car {licence_plate} was detached')
    except Exception as e:
        logger.error(e)
        retry_delay = retry_logic(e, self.request.retries + 1)
        raise self.retry(exc=e, countdown=retry_delay)


@app.task(bind=True, retry_backoff=30, max_retries=4)
def get_rent_information(self, **kwargs):
    driver = kwargs.get("driver_pk")
    payment = kwargs.get("payment_id")
    try:
        if driver:
            drivers = Driver.objects.filter(pk=driver)
            end = timezone.localtime()
            start_schema = timezone.make_aware(datetime.combine(timezone.localtime() - timedelta(days=1),
                                                                drivers.first().schema.shift_time))
            last_payment = DriverPayments.objects.filter(
                driver=driver,
                report_to__date=start_schema).order_by("-report_from").last()
            if last_payment and last_payment.report_to > start_schema:
                start = timezone.localtime(last_payment.report_to)
            else:
                start = start_schema
        elif payment:
            driver_payment = DriverPayments.objects.get(pk=payment)
            drivers = Driver.objects.filter(pk=driver_payment.driver_id)
            start = driver_payment.report_from
            end = driver_payment.report_to
        else:
            schemas = kwargs.get("schemas")
            day = kwargs.get("day")
            schema_obj = Schema.objects.filter(pk__in=schemas).first()
            if schema_obj.is_weekly():
                start, end = get_start_end("yesterday", day)[:2]
            else:
                end, start = get_time_for_task(schema_obj.pk, day)[1:3]
            drivers = Driver.objects.get_active(schema__in=schemas)
        gps = UaGpsSynchronizer.objects.get(partner=drivers.first().partner, deleted_at=None)
        gps.save_daily_rent(start, end, drivers, payment=payment)
        logger.info('write rent report')
    except ObjectDoesNotExist:
        return
    except Exception as e:
        logger.error(e)
        retry_delay = retry_logic(e, self.request.retries + 1)
        raise self.retry(exc=e, countdown=retry_delay)


@app.task(bind=True)
def generate_rent_message_driver(self, driver_id, manager_chat_id, message_id, payment=None):
    if payment:
        payment_obj = DriverPayments.objects.get(pk=payment)
        end, start, driver = payment_obj.report_to, payment_obj.report_from, payment_obj.driver
    else:
        driver = Driver.objects.get(pk=driver_id)
        end, start = get_time_for_task(driver.schema_id)[1:3]

    gps = UaGpsSynchronizer.objects.get(partner=driver.partner, deleted_at=None)
    message = gps.get_non_order_message(start, end, driver_id)
    return manager_chat_id, message, message_id, payment


@app.task(bind=True, retry_backoff=30, max_retries=3)
def get_today_rent(self, **kwargs):
    try:
        gps = UaGpsSynchronizer.objects.get(partner=kwargs.get("partner_pk"), deleted_at=None)
        gps.check_today_rent()
    except ObjectDoesNotExist:
        return
    except Exception as e:
        logger.error(e)
        retry_delay = retry_logic(e, self.request.retries + 1)
        raise self.retry(exc=e, countdown=retry_delay)


@app.task(bind=True, ignore_result=False, retry_backoff=30, max_retries=4)
def fleets_cash_trips(self, **kwargs):
    driver = Driver.objects.get(pk=kwargs.get('driver_id'))
    fleets = Fleet.objects.filter(partner=kwargs.get("partner_pk"), deleted_at=None).exclude(name='Gps')

    for fleet in fleets:
        driver_rate = FleetsDriversVehiclesRate.objects.filter(
            driver=driver, fleet=fleet, deleted_at__isnull=True).first()
        if driver_rate:
            fleet.disable_cash(driver_rate.driver_external_id, kwargs.get("enable"))


@app.task(bind=True, retry_backoff=30, max_retries=4)
def withdraw_uklon(self, **kwargs):
    try:
        fleet = UklonRequest.objects.get(partner=kwargs.get("partner_pk"), deleted_at=None)
        fleet.withdraw_money()
    except ObjectDoesNotExist:
        return
    except Exception as exc:
        logger.error(exc)
        retry_delay = retry_logic(exc, self.request.retries + 1)
        raise self.retry(exc=exc, countdown=retry_delay)


@app.task(bind=True)
def manager_paid_weekly(self, partner_pk):
    logger.info('send message to manager')
    return partner_pk


@app.task(bind=True)
def send_efficiency_report(self, **kwargs):
    partner = Partner.objects.filter(pk=kwargs.get('partner_pk')).first()
    message = ''
    dict_msg = {}
    managers = list(partner.manager_set.values_list('chat_id', flat=True))
    if not managers and partner.chat_id:
        managers = [partner.chat_id]
    for manager in managers:
        result = get_efficiency(manager_id=manager)
        if result:
            for k, v in result.items():
                message += f"{k}\n" + "".join(v) + "\n"
            if partner.pk in dict_msg:
                dict_msg[partner.pk] += message
            else:
                dict_msg[partner.pk] = message
    return dict_msg


@app.task(bind=True)
def send_driver_efficiency(self, **kwargs):
    partner = Partner.objects.filter(pk=kwargs.get('partner_pk')).first()
    driver_dict_msg = {}
    dict_msg = {}
    managers = list(partner.manager_set.values_list('chat_id', flat=True))
    if not managers and partner.chat_id:
        managers = [partner.chat_id]
    for manager in managers:
        result, start, end = get_driver_efficiency_report(manager_id=manager)
        if result:
            date_msg = f"Статистика з {start.strftime('%d.%m %H:%M')} по {end.strftime('%d.%m %H:%M')}\n"
            message = date_msg
            for k, v in result.items():
                driver_msg = f"{k}\n" + "".join(v)
                driver_dict_msg[k.pk] = date_msg + driver_msg
                message += driver_msg + "\n"
            if partner.pk in dict_msg:
                dict_msg[partner.pk] += message
            else:
                dict_msg[partner.pk] = message
    return dict_msg, driver_dict_msg


@app.task(bind=True)
def check_time_order(self, order_id):
    try:
        instance = Order.objects.get(pk=order_id)
    except ObjectDoesNotExist:
        return
    text = order_info(instance, time=True) if instance.type_order == Order.STANDARD_TYPE \
        else personal_order_info(instance)
    group_msg = bot.send_message(chat_id=ParkSettings.get_value('ORDER_CHAT'),
                                 text=text,
                                 reply_markup=inline_markup_accept(instance.pk),
                                 parse_mode=ParseMode.HTML)
    redis_instance().hset('group_msg', order_id, group_msg.message_id, ex=6048000)
    instance.checked = True
    instance.save()


@app.task(bind=True)
def check_personal_orders(self):
    for order in Order.objects.filter(status_order=Order.IN_PROGRESS, type_order=Order.PERSONAL_TYPE):
        finish_time = timezone.localtime(order.order_time) + timedelta(hours=order.payment_hours)
        distance = int(order.payment_hours) * int(ParkSettings.get_value('AVERAGE_DISTANCE_PER_HOUR'))
        notify_min = int(ParkSettings.get_value('PERSONAL_CLIENT_NOTIFY_MIN'))
        notify_km = int(ParkSettings.get_value('PERSONAL_CLIENT_NOTIFY_KM'))
        vehicle = check_vehicle(order.driver)
        gps = UaGpsSynchronizer.objects.get(partner=order.driver.partner)
        route = gps.generate_report(gps.get_timestamp(order.order_time),
                                    gps.get_timestamp(finish_time), vehicle.gps.gps_id)[0]
        pc_message = redis_instance().hget(str(order.chat_id_client), "client_msg")
        pd_message = redis_instance().hget(str(order.driver.chat_id), "driver_msg")
        if timezone.localtime() > finish_time or distance < route:
            if redis_instance().hget(str(order.chat_id_client), "finish") == order.id:
                bot.edit_message_text(chat_id=order.driver.chat_id,
                                      message_id=pd_message, text=driver_complete_text(order.sum))
                order.status_order = Order.COMPLETED
                order.partner = order.driver.partner
                order.save()
            else:
                client_msg = text_to_client(order, text=client_text_personal_end,
                                            button=personal_order_end_kb(order.id), delete_id=pc_message)
                driver_msg = bot.edit_message_text(chat_id=order.driver.chat_id,
                                                   message_id=pd_message,
                                                   text=driver_text_personal_end,
                                                   reply_markup=personal_driver_end_kb(order.id))
                redis_instance().hset(str(order.driver.chat_id), "driver_msg", driver_msg.message_id)
                redis_instance().hset(str(order.chat_id_client), "client_msg", client_msg)
        elif timezone.localtime() + timedelta(minutes=notify_min) > finish_time or distance < route - notify_km:
            pre_finish_text = personal_time_route_end(finish_time, distance - route)
            pc_message = bot.send_message(chat_id=order.chat_id_client,
                                          text=pre_finish_text,
                                          reply_markup=personal_order_end_kb(order.id, pre_finish=True))
            pd_message = bot.send_message(chat_id=order.driver.chat_id,
                                          text=pre_finish_text)
            redis_instance().hset(str(order.driver.chat_id), "driver_msg", pd_message.message_id)
            redis_instance().hset(str(order.chat_id_client), "client_msg", pc_message.message_id)


@app.task(bind=True)
def add_money_to_vehicle_weekly(self, **kwargs):
    partner_pk = kwargs.get('partner_pk')
    start, end = get_start_end('last_week')[:2]
    investors = Investor.filter_by_weekly_payment(partner_pk)
    create_investor_payments(start, end, partner_pk, investors)


@app.task(bind=True)
def add_money_to_vehicle_monthly(self, **kwargs):
    partner_pk = kwargs.get('partner_pk')
    start, end = get_start_end('last_month')[:2]
    investors = Investor.filter_by_monthly_payment(partner_pk)
    create_investor_payments(start, end, partner_pk, investors)


@app.task(bind=True, queue='beat_tasks')
def order_not_accepted(self):
    instances = Order.objects.filter(status_order=Order.ON_TIME, driver__isnull=True)
    for order in instances:
        if order.order_time < (timezone.localtime() + timedelta(
                minutes=int(ParkSettings.get_value('SEND_TIME_ORDER_MIN')))):
            group_msg = redis_instance().hget('group_msg', order.id)
            if order.type_order == Order.STANDARD_TYPE:
                if group_msg:
                    bot.delete_message(chat_id=ParkSettings.get_value("ORDER_CHAT"), message_id=group_msg)
                    redis_instance().hdel('group_msg', order.id)
                bot.edit_message_reply_markup(chat_id=order.chat_id_client,
                                              message_id=redis_instance().hget(order.chat_id_client, 'client_msg'))

                search_driver_for_order.delay(order.id)
            else:
                for manager in Manager.objects.exclude(chat_id__isnull=True):
                    if not redis_instance().hexists(str(manager.chat_id), f'personal {order.id}'):
                        redis_instance().hset(str(manager.chat_id), f'personal {order.id}', order.id)
                        bot.send_message(chat_id=manager.chat_id, text=pd_order_not_accepted)
                        bot.forward_message(chat_id=manager.chat_id,
                                            from_chat_id=ParkSettings.get_value("ORDER_CHAT"),
                                            message_id=group_msg)


@app.task(bind=True, queue='beat_tasks')
def send_time_order(self):
    accepted_orders = Order.objects.filter(status_order=Order.ON_TIME, driver__isnull=False)
    for order in accepted_orders:
        if timezone.localtime() < order.order_time < (timezone.localtime() + timedelta(minutes=int(
                ParkSettings.get_value('SEND_TIME_ORDER_MIN', 10)))):
            if order.type_order == Order.STANDARD_TYPE:
                text = order_info(order, time=True)
                reply_markup = inline_spot_keyboard(order.latitude, order.longitude, order.id)
            else:
                text = personal_order_info(order)
                reply_markup = inline_spot_keyboard(order.latitude, order.longitude)
            driver_msg = bot.send_message(chat_id=order.driver.chat_id, text=text,
                                          reply_markup=reply_markup,
                                          parse_mode=ParseMode.HTML)
            driver = order.driver
            message_info = redis_instance().hget(str(order.chat_id_client), 'client_msg')
            client_msg = text_to_client(order, order_customer_text, delete_id=message_info)
            redis_instance().hset(str(order.chat_id_client), 'client_msg', client_msg)
            redis_instance().hset(str(order.driver.chat_id), 'driver_msg', driver_msg.message_id)
            order.status_order, order.accepted_time = Order.IN_PROGRESS, timezone.localtime()
            order.save()
            if order.chat_id_client:
                vehicle = check_vehicle(driver)
                lat, long = get_location_from_db(vehicle.licence_plate)
                message = bot.sendLocation(order.chat_id_client, latitude=lat, longitude=long, live_period=1800)
                send_map_to_client.delay(order.id, vehicle.licence_plate, message.message_id, message.chat_id)


@app.task(bind=True, max_retries=3, queue='bot_tasks')
def order_create_task(self, order_data, report=None):
    try:
        order = Order.objects.create(**order_data)
        if report is not None:
            response = ReportTelegramPayments.objects.filter(pk=report).first()
            response.order = order
            response.save()
    except Exception as e:
        if self.request.retries <= self.max_retries:
            self.retry(exc=e, countdown=5)
        else:
            raise MaxRetriesExceededError("Max retries exceeded for task.")


@app.task(bind=True, max_retries=3, queue='bot_tasks')
def search_driver_for_order(self, order_pk):
    try:
        order = Order.objects.get(id=order_pk)
        client_msg = redis_instance().hget(str(order.chat_id_client), 'client_msg')
        if order.status_order == Order.CANCELED:
            return
        if order.status_order == Order.ON_TIME:
            order.status_order = Order.WAITING
            order.order_time = None
            order.save()
            if order.chat_id_client:
                msg = text_to_client(order,
                                     text=no_driver_in_radius,
                                     button=inline_search_kb(order.pk),
                                     delete_id=client_msg)
                redis_instance().hset(str(order.chat_id_client), 'client_msg', msg)
            return
        if self.request.retries == self.max_retries:
            if order.chat_id_client:
                bot.edit_message_text(chat_id=order.chat_id_client,
                                      text=no_driver_in_radius,
                                      reply_markup=inline_search_kb(order.pk),
                                      message_id=client_msg)
            return
        if self.request.retries == 0:
            text_to_client(order, search_driver, message_id=client_msg, button=inline_reject_order(order.pk))
        elif self.request.retries == 1:
            text_to_client(order, search_driver_1, message_id=client_msg,
                           button=inline_reject_order(order.pk))
        else:
            text_to_client(order, search_driver_2, message_id=client_msg,
                           button=inline_reject_order(order.pk))
        drivers = Driver.objects.get_active(chat_id__isnull=False)
        for driver in drivers:
            vehicle = check_vehicle(driver)
            if driver.driver_status == Driver.ACTIVE and vehicle:
                driver_lat, driver_long = get_location_from_db(vehicle.licence_plate)
                distance = haversine(float(driver_lat), float(driver_long),
                                     float(order.latitude), float(order.longitude))
                radius = int(ParkSettings.get_value('FREE_CAR_SENDING_DISTANCE')) + \
                         order.car_delivery_price / int(ParkSettings.get_value('TARIFF_CAR_DISPATCH'))
                if distance <= radius:
                    accept_message = bot.send_message(chat_id=driver.chat_id,
                                                      text=order_info(order),
                                                      reply_markup=inline_markup_accept(order.pk))
                    end_time = tm.time() + int(ParkSettings.get_value("MESSAGE_APPEAR"))
                    while tm.time() < end_time:
                        Driver.objects.filter(id=driver.id).update(driver_status=Driver.GET_ORDER)
                        upd_driver = Driver.objects.get(id=driver.id)
                        instance = Order.objects.get(id=order.id)
                        if instance.status_order == Order.CANCELED:
                            bot.delete_message(chat_id=driver.chat_id,
                                               message_id=accept_message.message_id)
                            return
                        if instance.driver == upd_driver:
                            return
                    bot.delete_message(chat_id=driver.chat_id,
                                       message_id=accept_message.message_id)
                    bot.send_message(chat_id=driver.chat_id,
                                     text=decline_order)
            else:
                continue
        self.retry(args=[order_pk], countdown=30)
    except ObjectDoesNotExist as e:
        logger.error(e)


@app.task(bind=True, max_retries=90, queue='bot_tasks')
def send_map_to_client(self, order_pk, licence, message, chat):
    order = Order.objects.get(id=order_pk)
    if order.chat_id_client:
        try:
            latitude, longitude = get_location_from_db(licence)
            distance = haversine(float(latitude), float(longitude), float(order.latitude), float(order.longitude))
            if order.status_order in (Order.CANCELED, Order.WAITING):
                bot.stopMessageLiveLocation(chat, message)
                return
            elif distance < float(ParkSettings.get_value('SEND_DISPATCH_MESSAGE')):
                bot.stopMessageLiveLocation(chat, message)
                client_msg = redis_instance().hget(str(order.chat_id_client), 'client_msg')
                driver_msg = redis_instance().hget(str(order.driver.chat_id), 'driver_msg')
                text_to_client(order, driver_arrived, delete_id=client_msg)
                redis_instance().hset(str(order.driver.chat_id), 'start_route', int(timezone.localtime().timestamp()))
                reply_markup = inline_client_spot(order_pk, message) if \
                    order.type_order == Order.STANDARD_TYPE else None
                bot.edit_message_reply_markup(chat_id=order.driver.chat_id,
                                              message_id=driver_msg,
                                              reply_markup=reply_markup)
            else:
                bot.editMessageLiveLocation(chat, message, latitude=latitude, longitude=longitude)
                self.retry(args=[order_pk, licence, message, chat], countdown=20)
        except BadRequest as e:
            if "Message can't be edited" in str(e) or order.status_order in (Order.CANCELED, Order.WAITING):
                pass
            else:
                raise self.retry(args=[order_pk, licence, message, chat], countdown=30) from e
        except StopIteration:
            pass
        except Exception as e:
            logger.error(msg=str(e))
            self.retry(args=[order_pk, licence, message, chat], countdown=30)
        if self.request.retries >= self.max_retries:
            bot.stopMessageLiveLocation(chat, message)
        return message


def fleet_order(instance, state=FleetOrder.COMPLETED):
    FleetOrder.objects.create(order_id=instance.pk, driver=instance.driver,
                              from_address=instance.from_address, destination=instance.to_the_address,
                              accepted_time=instance.accepted_time, finish_time=timezone.localtime(),
                              state=state,
                              partner=instance.driver.partner,
                              fleet='Ninja')


@app.task(bind=True, queue='bot_tasks')
def get_distance_trip(self, order, start_trip_with_client, end, gps_id):
    start = datetime.fromtimestamp(start_trip_with_client)
    format_end = datetime.fromtimestamp(end)
    delta = format_end - start
    try:
        instance = Order.objects.filter(pk=order).first()
        result = UaGpsSynchronizer.objects.get(
            partner=instance.driver.partner).generate_report(start_trip_with_client, end, gps_id)
        minutes = delta.total_seconds() // 60
        instance.distance_gps = result[0]
        price_per_minute = (int(ParkSettings.get_value('AVERAGE_DISTANCE_PER_HOUR')) *
                            int(ParkSettings.get_value('COST_PER_KM'))) / 60
        price_per_minute = price_per_minute * minutes
        price_per_distance = round(int(ParkSettings.get_value('COST_PER_KM')) * result[0])
        if price_per_distance > price_per_minute:
            total_sum = int(price_per_distance) + int(instance.car_delivery_price)
        else:
            total_sum = int(price_per_minute) + int(instance.car_delivery_price)

        instance.sum = total_sum if total_sum > int(ParkSettings.get_value('MINIMUM_PRICE_FOR_ORDER')) else \
            int(ParkSettings.get_value('MINIMUM_PRICE_FOR_ORDER'))
        instance.save()
        bot.send_message(chat_id=instance.chat_id_client,
                         text=payment_text,
                         reply_markup=inline_second_payment_kb(instance.pk))
    except Exception as e:
        logger.info(e)


@app.task(bind=True)
def get_calendar_weekly_report(self, **kwargs):
    start, end, format_start, format_end = get_start_end('last_week')
    message = calendar_weekly_report(kwargs.get('partner_pk'), start, end, format_start, format_end)
    bot.send_message(chat_id=ParkSettings.get_value('DRIVERS_CHAT', partner=kwargs.get('partner_pk')), text=message)


def save_report_to_ninja_payment(start, end, partner_pk, schema, fleet_name='Ninja'):
    reports = Payments.objects.filter(report_from=start, vendor_name=fleet_name, partner=partner_pk)
    if not reports:
        for driver in Driver.objects.get_active(partner=partner_pk, schema=schema).exclude(chat_id=''):
            records = Order.objects.filter(driver__chat_id=driver.chat_id,
                                           status_order=Order.COMPLETED,
                                           created_at__range=(start, end),
                                           partner=partner_pk)
            total_rides = records.count()
            result = records.aggregate(
                total=Sum(Coalesce(Cast('distance_gps', FloatField()),
                                   Cast('distance_google', FloatField()),
                                   output_field=FloatField())))
            total_distance = result['total'] if result['total'] is not None else 0.0
            total_amount_cash = records.filter(payment_method='Готівка').aggregate(
                total=Coalesce(Sum(Cast('sum', output_field=IntegerField())), 0))['total']
            total_amount_card = records.filter(payment_method='Картка').aggregate(
                total=Coalesce(Sum(Cast('sum', output_field=IntegerField())), 0))['total']
            total_amount = total_amount_cash + total_amount_card
            report = Payments(
                report_from=start,
                report_to=end,
                full_name=str(driver),
                driver_id=driver.chat_id,
                total_rides=total_rides,
                total_distance=total_distance,
                total_amount_cash=total_amount_cash,
                total_amount_on_card=total_amount_card,
                total_amount_without_fee=total_amount,
                partner_id=partner_pk)
            try:
                report.save()
            except IntegrityError:
                pass


@app.task(bind=True)
def calculate_driver_reports(self, **kwargs):
    today = timezone.localtime()
    start_week, end_week = get_start_end('last_week')[:2]
    partner = kwargs.get('partner_pk')
    weekly_drivers_id = Schema.get_weekly_drivers(partner)
    driver_list = []
    created = False
    weekly_drivers = Driver.objects.get_active(pk__in=weekly_drivers_id)
    drivers = Driver.objects.get_active(schema__in=kwargs.get("schemas"))
    for driver in drivers:
        bolt_weekly = WeeklyReport.objects.filter(report_from=start_week, report_to=end_week,
                                                  driver=driver, fleet__name="Bolt").aggregate(
            bonuses=Coalesce(Sum('bonuses'), 0, output_field=DecimalField()),
            kasa=Coalesce(Sum('total_amount_without_fee'), 0, output_field=DecimalField()),
            compensations=Coalesce(Sum('compensations'), 0, output_field=DecimalField()),
        )

        if driver in weekly_drivers:
            start_day, end_day = get_start_end('yesterday')[:2]
            create_charge_penalty(driver, start_day, end_day)
            if today.weekday():
                continue
            start, end = start_week, end_week
            bonus = bolt_weekly['bonuses']
        else:
            bonus = None
            if not today.weekday() and bolt_weekly and bolt_weekly['bonuses']:
                add_bonus_earnings(start_week, end_week, driver, bolt_weekly)
            end, start = get_time_for_task(driver.schema_id, kwargs.get('day'))[1:3]
            create_charge_penalty(driver, start, end)
        reshuffles = check_reshuffle(driver, start, end)
        if reshuffles:
            data = create_driver_payments(start, end, driver, driver.schema, bonuses=bonus)[0]
            if driver not in weekly_drivers:
                try:
                    if data['status'] == PaymentsStatus.INCORRECT or BoltRequest.objects.get(
                            partner=driver.partner).check_driver_status(driver):
                        driver_list.append(driver)
                except ObjectDoesNotExist:
                    pass
                if driver.driver_status == Driver.WITH_CLIENT or EcoFactorRequest().check_active_transaction(driver):
                    data['status'] = PaymentsStatus.INCORRECT
            if data['kasa'] or data['rent']:
                payment, created = DriverPayments.objects.get_or_create(report_to__date=end,
                                                                        driver=driver,
                                                                        defaults=data)
                if created:
                    PenaltyBonus.objects.filter(driver=driver, driver_payments__isnull=True).update(driver_payments=payment)
                    payment.earning = Decimal(payment.earning) + payment.get_bonuses() - payment.get_penalties()
                    payment.save(update_fields=['earning'])
    for driver in driver_list:
        keyboard = inline_bolt_report_keyboard()
        bot.send_message(chat_id=ParkSettings.get_value("DEVELOPER_CHAT_ID"),
                         text=f"{driver} Не вдалося отримати всі дані Bolt."
                              f" Натисніть кнопку нижче, щоб відправити звіт Вашому менеджеру.",
                         reply_markup=keyboard)
    if created:
        managers = Manager.objects.filter(driver__in=drivers, chat_id__isnull=False).exclude(chat_id='').distinct()
        for manager in managers:
            bot.send_message(chat_id=manager.chat_id,
                             text=f"Додано нові платежі водіів на перевірку."
                             )


@app.task(bind=True)
def add_screen_to_payment(self, filename, driver_pk):
    payment = DriverPayments.objects.filter(driver=driver_pk).order_by("-report_to").first()
    payment.bolt_screen = filename
    payment.save(update_fields=['bolt_screen'])


@app.task(bind=True, ignore_result=False)
def create_daily_payment(self, **kwargs):
    kw_driver = kwargs.get("driver_pk")
    if kw_driver:
        driver = Driver.objects.get(pk=kw_driver)
        start, end = get_start_end('today')[:2]
    else:
        payment = DriverPayments.objects.get(pk=kwargs.get("payment_id"))
        driver = payment.driver
        start = timezone.make_aware(datetime.combine(payment.report_to, time.min))
        end = payment.report_to
    fleets = Fleet.objects.filter(fleetsdriversvehiclesrate__driver=driver, deleted_at=None).exclude(
        name="Ninja").distinct()
    for fleet in fleets:
        driver_ids = [driver.get_driver_external_id(fleet)]
        fleet.get_fleet_orders(start, end, driver)
        fleet.save_daily_custom(start, end, driver_ids)
        payment_24hours_create(start - timedelta(minutes=1), end, fleet, driver, driver.partner)
    add_distance_for_order(partner_pk=driver.partner, driver=driver.id)
    report = summary_report_create(start, end, driver, driver.partner)
    get_rent_information(**kwargs)
    create_charging_transactions()
    if report:
        data, no_price = create_driver_payments(start, end, driver, driver.schema)
        payment, created = DriverPayments.objects.get_or_create(report_to__date=end,
                                                                driver=driver,
                                                                defaults=data)
        create_charge_penalty(driver, payment.report_from, payment.report_to)
        if not created:
            for key, value in data.items():
                setattr(payment, key, value)
            payment.earning = Decimal(payment.earning) + Decimal(payment.get_bonuses() - payment.get_penalties())
            payment.save()
        response = {"status": payment.status, "id": payment.id, "order": no_price}
    else:
        response = {"status": "error"}
    return response


@app.task(bind=True)
def calculate_vehicle_earnings(self, **kwargs):
    payment = DriverPayments.objects.get(pk=kwargs.get('payment_id'))
    driver = payment.driver
    start = timezone.localtime(payment.report_from)
    end = timezone.localtime(payment.report_to)
    driver_value = payment.earning + payment.cash + payment.rent - payment.get_bonuses() + payment.get_penalties()
    if payment.kasa:
        spending_rate = 1 - round(driver_value / payment.kasa, 6) if driver_value > 0 else 1
        if payment.is_weekly():
            vehicles_income = get_vehicle_income(driver, start, end, spending_rate, payment.rent)
        else:
            vehicles_income = calculate_income_partner(driver, start, end, spending_rate, payment.rent)
    else:
        reshuffles_income = {}
        total_reshuffles = 0
        driver_payment = -payment.earning
        total_duration = (payment.report_to - payment.report_from).total_seconds()
        reshuffles = check_reshuffle(driver, start, end)
        for reshuffle in reshuffles:
            vehicle = reshuffle.swap_vehicle.pk
            start_period, end_period = find_reshuffle_period(reshuffle, start, end)
            reshuffle_duration = (end_period - start_period).total_seconds()
            total_reshuffles += reshuffle_duration
            vehicle_earn = Decimal(reshuffle_duration / total_duration) * driver_payment
            if not reshuffles_income.get(vehicle):
                reshuffles_income[vehicle] = vehicle_earn
            else:
                reshuffles_income[vehicle] += vehicle_earn
        if total_reshuffles != total_duration and reshuffles_income:
            duration_without_car = total_duration - total_reshuffles
            no_car_income = Decimal(duration_without_car / total_duration) * driver_payment
            vehicle_bonus = Decimal(no_car_income / len(reshuffles_income))
            vehicles_income = {key: value + vehicle_bonus for key, value in reshuffles_income.items()}
        else:
            vehicles_income = reshuffles_income
    for vehicle, income in vehicles_income.items():
        vehicle_bonus = Penalty.objects.filter(vehicle=vehicle, driver_payments=payment).exclude(
                category__title="Зарядка").aggregate(
            total_amount=Coalesce(Sum('amount'), Decimal(0)))['total_amount']
        vehicle_penalty = \
            Bonus.objects.filter(vehicle=vehicle, driver_payments=payment).exclude(
                category__title="Бонуси Bolt").aggregate(
                total_amount=Coalesce(Sum('amount'), Decimal(0)))['total_amount']
        earning = income + vehicle_bonus - vehicle_penalty
        PartnerEarnings.objects.update_or_create(
            report_from=payment.report_from,
            report_to=payment.report_to,
            vehicle_id=vehicle,
            driver=driver,
            partner=driver.partner,
            defaults={
                "status": PaymentsStatus.COMPLETED,
                "earning": earning,
            }
        )


@app.task(bind=True)
def calculate_vehicle_spending(self, **kwargs):
    payment = InvestorPayments.objects.get(pk=kwargs.get("payment_id"))
    spending = -payment.earning
    PartnerEarnings.objects.update_or_create(
        report_from=payment.report_from,
        report_to=payment.report_to,
        vehicle_id=payment.vehicle.id,
        partner=payment.partner,
        defaults={
            "earning": spending,
        }
    )


@app.task(bind=True)
def calculate_failed_earnings(self, **kwargs):
    payment = DriverPayments.objects.get(pk=kwargs.get("payment_id"))
    vehicle_income, total_income = get_failed_income(payment)
    charging_penalties = Penalty.objects.filter(driver_payments=payment, category__title="Зарядка")
    charging = charging_penalties.aggregate(total_amount=Coalesce(Sum('amount'), Decimal(0)))['total_amount']
    earning_exclude_charging = abs(payment.earning) - charging

    if earning_exclude_charging > 0:
        for vehicle, income in vehicle_income.items():
            debt = Decimal(round((income / total_income) * abs(earning_exclude_charging), 2))

            format_start = payment.report_from.strftime("%d.%m")
            format_end = payment.report_to.strftime("%d.%m")
            description = f"Борг з {format_start} по {format_end}"
            category, _ = PenaltyCategory.objects.get_or_create(title="Борг по виплаті")
            Penalty.objects.create(vehicle_id=vehicle, driver=payment.driver,
                                   amount=debt, description=description,
                                   category=category)
            charging_penalties.update(driver_payments=None, description=description)
    else:
        for vehicle, income in vehicle_income.items():
            vehicle_income[vehicle] -= Decimal(round((income / total_income) * (charging - abs(payment.earning)), 2))
        charge_vehicles = charging_penalties.values('vehicle').annotate(total_amount=Sum('amount'))
        for item in charge_vehicles:
            charge_amount = (item['total_amount'] / charging) * abs(payment.earning)
            category, _ = Category.objects.get_or_create(title="Зарядка")
            Penalty.objects.create(vehicle_id=item['vehicle'], driver=payment.driver,
                                   amount=charge_amount,
                                   category_id=category.pk)
    for vehicle, income in vehicle_income.items():
        PartnerEarnings.objects.update_or_create(
            report_from=payment.report_from,
            report_to=payment.report_to,
            vehicle_id=vehicle,
            driver=payment.driver,
            partner=payment.partner,
            defaults={
                "status": PaymentsStatus.COMPLETED,
                "earning": income,
            }
        )


@app.task(bind=True)
def create_charging_transactions(self, **kwargs):
    day = kwargs.get('day')
    date = datetime.strptime(day, "%Y-%m-%d") if day else timezone.localtime()
    start_day = timezone.make_aware(datetime.combine(date, time.min))
    start = start_day - timedelta(hours=1)
    end = timezone.make_aware(datetime.combine(start_day, time.max)) if day else date
    EcoFactorRequest().get_driver_transactions(start, end)


@app.task(bind=True)
def check_cash_and_vehicle(self, **kwargs):
    tasks = chain(get_today_orders.si(**kwargs),
                  null_vehicle_orders.si(**kwargs),
                  add_distance_for_order.si(**kwargs),
                  check_card_cash_value.si(**kwargs),
                  create_charging_transactions.si(**kwargs)
                  )
    tasks()


@app.task(bind=True)
def get_information_from_fleets(self, **kwargs):

    task_chain = chain(
        download_daily_report.si(**kwargs),
        get_today_orders.si(**kwargs),
        add_distance_for_order.si(**kwargs),
        generate_payments.si(**kwargs),
        generate_summary_report.si(**kwargs),
        get_rent_information.si(**kwargs),
        create_charging_transactions.si(**kwargs),
        calculate_driver_reports.si(**kwargs),
    )
    task_chain()


@app.task(bind=True)
def update_schedule(self):
    tasks = TaskScheduler.objects.all()
    partners = Partner.objects.all()
    work_schemas = Schema.objects.all()
    for db_task in tasks:
        if db_task.interval:
            next_execution_datetime = datetime.now() + timedelta(days=db_task.interval)
            interval_schedule, _ = IntervalSchedule.objects.get_or_create(
                every=db_task.interval,
                period=IntervalSchedule.DAYS,
            )
            for partner in partners:
                PeriodicTask.objects.get_or_create(
                    name=f'auto.tasks.{db_task.name}([{partner.pk}])',
                    task=f'auto.tasks.{db_task.name}',
                    defaults={
                        'interval': interval_schedule,
                        'start_time': next_execution_datetime,
                        'kwargs': {"partner_pk": partner.pk}
                    }
                )
        else:
            day = '1' if db_task.weekly else '*'
            schedule = get_schedule(db_task.task_time, day, periodic=db_task.periodic)
            for partner in partners:
                create_task(db_task.name, partner.pk, schedule, db_task.arguments)
    for schema in work_schemas:
        if schema.shift_time != time.min:
            schedule = get_schedule(schema.shift_time)
        else:
            schedule = get_schedule(time(9, 00))
        create_task('get_information_from_fleets', schema.partner.pk, schedule, schema.pk)

# @app.on_after_finalize.connect
# def run_periodic_tasks(sender, **kwargs):
# sender.add_periodic_task(crontab(minute="*/2"), send_time_order.s())
# sender.add_periodic_task(crontab(minute='*/20'), raw_gps_handler.s(queue='beat_tasks_1'))
# sender.add_periodic_task(crontab(minute="*/2"), order_not_accepted.s())
# sender.add_periodic_task(crontab(minute="*/4"), check_personal_orders.s())
