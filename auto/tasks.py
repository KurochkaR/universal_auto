import os
import socket
from datetime import datetime, timedelta, time
import time as tm
import requests
from _decimal import Decimal
from celery import current_app, chain
from celery.exceptions import MaxRetriesExceededError
from celery.utils.log import get_task_logger
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.utils import timezone
from celery.schedules import crontab
from django_celery_beat.models import IntervalSchedule, PeriodicTask
from telegram import ParseMode
from telegram.error import BadRequest
from app.models import RawGPS, Vehicle, Order, Driver, JobApplication, ParkSettings, UseOfCars, CarEfficiency, \
    Payments, SummaryReport, Manager, Partner, DriverEfficiency, FleetOrder, ReportTelegramPayments, \
    InvestorPayments, VehicleSpending, DriverReshuffle, DriverPayments, SalaryCalculation, \
    PaymentTypes, TaskScheduler, DriverEffVehicleKasa, Schema, CustomReport, FleetsDriversVehiclesRate, Fleet, \
    VehicleGPS, PartnerEarnings
from django.db.models import Sum, IntegerField, FloatField, Q, Value
from django.db.models.functions import Cast, Coalesce
from app.utils import get_schedule, create_task
from auto_bot.handlers.driver_manager.utils import get_daily_report, get_efficiency, generate_message_report, \
    get_driver_efficiency_report, calculate_rent, get_vehicle_income, get_time_for_task, \
    create_driver_payments
from auto_bot.handlers.order.keyboards import inline_markup_accept, inline_search_kb, inline_client_spot, \
    inline_spot_keyboard, inline_second_payment_kb, inline_reject_order, personal_order_end_kb, \
    personal_driver_end_kb
from auto_bot.handlers.order.static_text import decline_order, order_info, search_driver_1, \
    search_driver_2, no_driver_in_radius, driver_arrived, driver_complete_text, \
    order_customer_text, search_driver, personal_time_route_end, personal_order_info, \
    pd_order_not_accepted, driver_text_personal_end, client_text_personal_end, payment_text
from auto_bot.handlers.order.utils import text_to_client, check_reshuffle, check_vehicle
from auto_bot.main import bot
from scripts.conversion import convertion, haversine, get_location_from_db
from auto.celery import app
from scripts.google_calendar import GoogleCalendar
from scripts.redis_conn import redis_instance
from app.bolt_sync import BoltRequest
from selenium_ninja.synchronizer import AuthenticationError
from app.uagps_sync import UaGpsSynchronizer
from app.uber_sync import UberRequest
from app.uklon_sync import UklonRequest
from scripts.nbu_conversion import convert_to_currency
from taxi_service.utils import login_in

logger = get_task_logger(__name__)


@app.task(queue='bot_tasks')
def raw_gps_handler(pk):
    try:
        raw = RawGPS.objects.get(id=pk)
        vehicle = Vehicle.objects.filter(gps_imei=raw.imei)
    except ObjectDoesNotExist:
        return f'{ObjectDoesNotExist}: id={pk}'
    data = raw.data.split(';')
    try:
        lat, lon = convertion(data[2]), convertion(data[4])
    except ValueError:
        lat, lon = 0, 0
    try:
        date_time = timezone.datetime.strptime(data[0] + data[1], '%d%m%y%H%M%S')
        date_time = timezone.make_aware(date_time)
    except ValueError as err:
        return f'Error converting date and time: {err}'
    try:
        kwa = {
            'date_time': date_time,
            'vehicle': vehicle.first(),
            'lat': lat,
            'lat_zone': data[3],
            'lon': lon,
            'lon_zone': data[5],
            'speed': float(data[6]),
            'course': float(data[7]),
            'height': float(data[8]),
            'raw_data': raw,
        }
    except ValueError as err:
        return f'{ValueError} {err}'
    VehicleGPS.objects.create(**kwa)
    vehicle.update(lat=lat, lon=lon, coord_time=date_time)


@app.task(bind=True, queue='bot_tasks')
def health_check(self):
    logger.info("Celery OK")


@app.task(bind=True, queue='beat_tasks')
def auto_send_task_bot(self):
    webhook_url = f'{os.environ["WEBHOOK_URL"]}/webhook/'
    message_data = {"update_id": 523456789,
                    "message": {"message_id": 6993, "chat": {"id": 515224934, "type": "private"},
                                "text": "/test_celery",
                                "from": {"id": 515224934, "first_name": "Родіон", "is_bot": False},
                                "date": int(tm.time()),
                                "entities": [{"offset": 0, "length": 12, "type": "bot_command"}]}}
    requests.post(webhook_url, json=message_data)


@app.task(bind=True, queue='bot_tasks')
def get_session(self, partner_pk, aggregator='Uber', login=None, password=None):
    fleet = Fleet.objects.get(name=aggregator, partner=None)
    try:
        token = fleet.create_session(partner_pk, login=login, password=password)
        success = login_in(aggregator=aggregator, partner_id=partner_pk,
                           login_name=login, password=password, token=token)
    except AuthenticationError as e:
        logger.error(e)
        success = False
    return partner_pk, success


@app.task(bind=True, queue='beat_tasks')
def get_orders_from_fleets(self, partner_pk, schema=None, day=None):
    fleets = Fleet.objects.filter(partner=partner_pk).exclude(name='Gps')
    end, start = get_time_for_task(schema, day)[1:3]
    drivers = Driver.objects.get_active(partner=partner_pk)
    for fleet in fleets:
        if isinstance(fleet, UberRequest):
            try:
                fleet.get_fleet_orders(start, end)
            except Exception as e:
                logger.error(e)
        else:
            for driver in drivers:
                driver_id = driver.get_driver_external_id(fleet.name)
                if driver_id:
                    fleet.get_fleet_orders(start, end, driver.pk, driver_id)


@app.task(bind=True, queue='beat_tasks')
def check_orders_for_vehicle(self, partner_pk, schema):
    end, start = get_time_for_task(schema)[1:3]
    orders = FleetOrder.objects.filter(accepted_time__range=(start, end), partner=partner_pk)
    for driver in Driver.objects.get_active(partner=partner_pk).filter(schema=schema):
        driver_orders = orders.filter(driver=driver)
        vehicles = check_reshuffle(driver, start, end)
        for vehicle, reshuffle in vehicles.items():
            if not reshuffle:
                vehicle_orders = orders.filter(vehicle=vehicle)
                if not driver_orders and vehicle_orders:
                    driver.vehicle = None
                    driver.save()


@app.task(bind=True, queue='beat_tasks')
def get_today_orders(self, partner_pk):
    fleets = Fleet.objects.filter(partner=partner_pk).exclude(name__in=('Gps', 'Uber'))
    end = timezone.localtime()
    start = timezone.make_aware(datetime.combine(end, time.min))
    drivers = Driver.objects.get_active(partner=partner_pk)
    for fleet in fleets:
        if isinstance(fleet, UklonRequest) and end <= start:
            continue
        for driver in drivers:
            driver_id = driver.get_driver_external_id(fleet.name)
            if driver_id:
                fleet.get_fleet_orders(start, end, driver.pk, driver_id)


@app.task(bind=True, queue='beat_tasks')
def check_card_cash_value(self, partner_pk):
    today = timezone.localtime().date()
    start_week = today - timedelta(days=today.weekday())
    for driver in Driver.objects.get_active(partner=partner_pk, schema__isnull=False):
        if driver.schema.is_weekly():
            orders = FleetOrder.objects.filter(accepted_time__range=(start_week, today),
                                               state=FleetOrder.COMPLETED,
                                               driver=driver)
            rent = calculate_rent(start_week, today, driver)
        else:
            yesterday = today - timedelta(days=1)
            orders = FleetOrder.objects.filter(accepted_time__date=timezone.localtime().date(),
                                               state=FleetOrder.COMPLETED,
                                               driver=driver)
            rent = calculate_rent(yesterday, today, driver)
        kasa = orders.aggregate(kasa=Coalesce(Sum('price'), Value(1)))['kasa']
        rent_payment = rent * driver.schema.rent_price
        if kasa > int(ParkSettings.get_value("START_CHECK_CASH", partner=partner_pk)):
            card = orders.filter(payment=PaymentTypes.CARD,
                                 driver=driver).aggregate(card_kasa=Sum('price'))['card_kasa']
            ratio = (card - rent_payment) / kasa
            if driver.schema.is_rent():
                rate = float(ParkSettings.get_value("RENT_CASH_RATE", partner=partner_pk))
            else:
                rate = driver.schema.rate
            enable = 'false' if ratio < rate else 'true'
            bot.send_message(chat_id=ParkSettings.get_value("DEVELOPER_CHAT_ID"),
                             text=f"Готівка {enable} у {driver}")
            fleets_cash_trips.delay(partner_pk, driver.pk, enable)


@app.task(bind=True, queue='beat_tasks')
def send_notify_to_check_car(self, partner_pk):
    if redis_instance().exists(f"wrong_vehicle_{partner_pk}"):
        wrong_cars = redis_instance().hgetall(f"wrong_vehicle_{partner_pk}")
        for driver, car in wrong_cars.items():
            driver_obj = Driver.objects.get(pk=int(driver))
            vehicle = check_vehicle(driver_obj)[0]
            if not vehicle or vehicle.licence_plate != car:
                chat_id = driver_obj.manager.chat_id if driver_obj.manager else driver_obj.partner.chat_id
                try:
                    bot.send_message(chat_id=chat_id, text=f"Водій {driver_obj} працює на {car},"
                                                           f" перевірте машину яка закріплена за водієм")
                except BadRequest:
                    bot.send_message(chat_id=ParkSettings.get_value("DEVELOPER_CHAT_ID"),
                                     text=f"Не відправилось повідомлення про зміну авто для водія {driver_obj},"
                                          f" партнер {driver_obj.partner}(неправильний чат ід?)")
        redis_instance().delete(f"wrong_vehicle_{partner_pk}")


@app.task(bind=True, queue='beat_tasks')
def download_daily_report(self, partner_pk, schema, day=None):
    start, end = get_time_for_task(schema, day)[:2]
    fleets = Fleet.objects.filter(partner=partner_pk).exclude(name='Gps')
    for fleet in fleets:
        for driver in Driver.objects.get_active(schema=schema):
            driver_id = driver.get_driver_external_id(fleet.name)
            if driver_id:
                fleet.save_report(start, end, driver)


@app.task(bind=True, queue='beat_tasks')
def download_nightly_report(self, partner_pk, schema, day=None):
    start, end = get_time_for_task(schema, day)[2:]
    fleets = Fleet.objects.filter(partner=partner_pk).exclude(name='Gps')
    for fleet in fleets:
        for driver in Driver.objects.get_active(schema=schema):
            driver_id = driver.get_driver_external_id(fleet.name)
            if driver_id:
                if isinstance(fleet, UberRequest):
                    fleet.save_report(start, end, driver)
                else:
                    fleet.save_report(start, end, driver, custom=True)
    # save_report_to_ninja_payment(start, end, partner_pk, schema)


@app.task(bind=True, queue='beat_tasks')
def generate_payments(self, partner_pk, schema, day=None):
    fleets = Fleet.objects.filter(partner=partner_pk).exclude(name='Gps')
    for fleet in fleets:
        for driver in Driver.objects.get_active(schema=schema):
            end, start = get_time_for_task(schema, day)[1:3]
            driver_id = driver.get_driver_external_id(fleet.name)
            reports = CustomReport.objects.filter(
                report_from__range=(start, end),
                driver_id=driver_id).values('full_name', 'vehicle').annotate(
                without_fee=Sum('total_amount_without_fee'),
                cash=Sum('total_amount_cash'),
                amount=Sum('total_amount'),
                card=Sum('total_amount_on_card') or 0,
                tips=Sum('tips') or 0,
                bonuses=Sum('bonuses') or 0,
                fee=Sum('fee') or 0,
                fares=Sum('fares') or 0,
                cancels=Sum('cancels') or 0,
                compensations=Sum('compensations'),
                refunds=Sum('refunds') or 0,
                distance=Sum('total_distance') or 0,
                rides=Sum('total_rides'))
            for report in reports:
                auto = Vehicle.objects.get(pk=report["vehicle"]) if report["vehicle"] else None
                data = {
                    "total_rides": report["rides"],
                    "total_distance": report["distance"],
                    "total_amount_cash": report["cash"],
                    "total_amount_on_card": report["card"],
                    "total_amount": report["amount"],
                    "tips": report["tips"],
                    "bonuses": report["bonuses"],
                    "fares": report["fares"],
                    "fee": report["fee"],
                    "total_amount_without_fee": report["without_fee"],
                    "partner": Partner.get_partner(partner_pk),
                    "vehicle": auto
                }
                Payments.objects.get_or_create(report_from=start,
                                               report_to=end,
                                               vendor_name=fleet.name,
                                               driver_id=driver_id,
                                               full_name=report["full_name"],
                                               partner=partner_pk,
                                               defaults={**data})


@app.task(bind=True, queue='beat_tasks')
def generate_summary_report(self, partner_pk, schema, day=None):
    end, start = get_time_for_task(schema, day)[1:3]
    fleet_reports = Payments.objects.filter(report_from=start, report_to=end, partner=partner_pk)
    for driver in Driver.objects.get_active(partner=partner_pk):
        payments = [r for r in fleet_reports if r.driver_id == driver.get_driver_external_id(r.vendor_name)]
        if payments:
            if not SummaryReport.objects.filter(report_from=start, driver=driver, partner=partner_pk):
                report = SummaryReport(report_from=start,
                                       report_to=end,
                                       driver=driver,
                                       vehicle=driver.vehicle,
                                       partner=Partner.get_partner(partner_pk))
                fields = ("total_rides", "total_distance", "total_amount_cash",
                          "total_amount_on_card", "total_amount", "tips",
                          "bonuses", "fee", "total_amount_without_fee", "fares",
                          "cancels", "compensations", "refunds"
                          )

                for field in fields:
                    setattr(report, field, sum(getattr(payment, field, 0) or 0 for payment in payments))
                report.save()


@app.task(bind=True, queue='beat_tasks')
def get_car_efficiency(self, partner_pk):
    end = timezone.make_aware(datetime.combine(timezone.localtime().date(), time.min))
    start = end - timedelta(days=1)
    for vehicle in Vehicle.objects.filter(partner=partner_pk):
        efficiency = CarEfficiency.objects.filter(report_from=start,
                                                  partner=partner_pk,
                                                  vehicle=vehicle)
        if efficiency:
            continue
        vehicle_drivers = {}
        total_spending = VehicleSpending.objects.filter(
            vehicle=vehicle,  created_at__range=(start, end)).aggregate(Sum('amount'))['amount__sum'] or 0
        reshuffles = DriverReshuffle.objects.filter(Q(end_time=end) | Q(swap_time=start), swap_vehicle=vehicle)
        drivers = [reshuffle.driver_start for reshuffle in reshuffles] if reshuffles \
            else Driver.objects.filter(vehicle=vehicle)
        total_kasa = 0
        try:
            total_km = UaGpsSynchronizer.objects.get(partner=partner_pk).total_per_day(vehicle.gps.gps_id, start, end)
        except AttributeError as e:
            logger.error(e)
            continue
        if total_km:
            for driver in drivers:
                driver_ids = FleetsDriversVehiclesRate.objects.filter(
                    driver=driver,
                    partner=partner_pk).values_list('driver_external_id', flat=True)
                reports = CustomReport.objects.filter(
                    report_from__date=start,
                    driver_id__in=driver_ids)
                driver_kasa = reports.aggregate(
                    kasa=Coalesce(Sum("total_amount_without_fee"), Decimal(0)))['kasa']
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
                                           partner_id=partner_pk)
        for driver, kasa in vehicle_drivers.items():
            DriverEffVehicleKasa.objects.create(driver=driver, efficiency_car=car, kasa=kasa)


@app.task(bind=True, queue='beat_tasks')
def get_driver_efficiency(self, partner_pk, schema, day=None):
    end, start = get_time_for_task(schema, day)[1:3]
    for driver in Driver.objects.get_active(partner=partner_pk, schema=schema):
        efficiency = DriverEfficiency.objects.filter(report_from=start,
                                                     partner=partner_pk,
                                                     driver=driver)
        if not efficiency:
            accept = 0
            avg_price = 0
            total_km, driver_vehicles = UaGpsSynchronizer.objects.get(
                                partner=partner_pk).calc_total_km(driver, start, end)
            if driver_vehicles:
                report = SummaryReport.objects.filter(report_from=start, driver=driver).first()
                total_kasa = report.total_amount_without_fee if report else 0
                result = Decimal(total_kasa) / Decimal(total_km) if total_km else 0
                orders = FleetOrder.objects.filter(driver=driver, accepted_time__range=(start, end))
                total_orders = orders.count()
                if total_orders:
                    canceled = orders.filter(state=FleetOrder.DRIVER_CANCEL).count()
                    accepted_orders = total_orders - canceled
                    accept = accepted_orders / total_orders * 100
                    avg_price = Decimal(total_kasa) / Decimal(accepted_orders)
                hours_online = timedelta()
                using_info = UseOfCars.objects.filter(created_at__range=(start, end), user_vehicle=driver)
                for report in using_info:
                    if report.end_at:
                        if report.end_at < end:
                            hours_online += report.end_at - report.created_at
                    else:
                        hours_online += end - report.created_at
                if start.time() == time.min:
                    yesterday = start - timedelta(days=1)
                    last_using = UseOfCars.objects.filter(created_at__date=yesterday,
                                                          user_vehicle=driver,
                                                          end_at__date=start).first()
                    if last_using:
                        hours_online += last_using.end_at - start

                driver_efficiency = DriverEfficiency.objects.create(report_from=start,
                                                                    report_to=end,
                                                                    driver=driver,
                                                                    total_kasa=total_kasa,
                                                                    total_orders=total_orders,
                                                                    accept_percent=accept,
                                                                    average_price=avg_price,
                                                                    mileage=total_km or 0,
                                                                    online_time=hours_online,
                                                                    efficiency=result,
                                                                    partner_id=partner_pk)
                driver_efficiency.vehicles.add(*driver_vehicles)


@app.task(bind=True, queue='beat_tasks')
def update_driver_status(self, partner_pk):
    try:
        status_online = set()
        status_with_client = set()
        fleets = Fleet.objects.filter(partner=partner_pk).exclude(name='Gps')
        for fleet in fleets:
            statuses = fleet.get_drivers_status()
            logger.info(f"{fleet} {statuses}")
            status_online = status_online.union(set(statuses['wait']))
            status_with_client = status_with_client.union(set(statuses['with_client']))
        drivers = Driver.objects.get_active(partner=partner_pk)
        for driver in drivers:
            active_order = Order.objects.filter(driver=driver, status_order=Order.IN_PROGRESS)
            work_ninja = UseOfCars.objects.filter(user_vehicle=driver, partner=partner_pk,
                                                  created_at__date=timezone.localtime().date(), end_at=None).first()
            if active_order or (driver.name, driver.second_name) in status_with_client:
                current_status = Driver.WITH_CLIENT
            elif (driver.name, driver.second_name) in status_online:
                current_status = Driver.ACTIVE
            else:
                current_status = Driver.OFFLINE
            driver.driver_status = current_status
            driver.save()
            if current_status != Driver.OFFLINE:
                vehicle = check_vehicle(driver)[0]
                if not work_ninja and vehicle and driver.chat_id:
                    UseOfCars.objects.create(user_vehicle=driver,
                                             partner_id=partner_pk,
                                             licence_plate=vehicle.licence_plate,
                                             chat_id=driver.chat_id)
                logger.info(f'{driver}: {current_status}')
            else:
                if work_ninja:
                    work_ninja.end_at = timezone.localtime()
                    work_ninja.save()
    except Exception as e:
        logger.error(e)


@app.task(bind=True, queue='bot_tasks')
def update_driver_data(self, partner_pk, manager_id=None):
    try:
        fleets = Fleet.objects.filter(partner=partner_pk)
        for synchronization_class in fleets:
            synchronization_class.synchronize()
        success = True
    except Exception as e:
        logger.error(e)
        success = False
    return manager_id, success


@app.task(bind=True, queue='bot_tasks')
def send_on_job_application_on_driver(self, job_id):
    try:
        candidate = JobApplication.objects.get(id=job_id)
        UklonRequest.add_driver(candidate)
        BoltRequest.add_driver(candidate)
        logger.info('The job application has been sent')
    except Exception as e:
        logger.error(e)


@app.task(bind=True, queue='bot_tasks')
def schedule_for_detaching_uklon(self, partner_pk):
    today = timezone.localtime().date()
    reshuffles = DriverReshuffle.objects.filter(
                    end_time__date=today,
                    end_time__lt=timezone.make_aware(datetime.combine(today, time.max)),
                    partner=partner_pk
                    )
    for reshuffle in reshuffles:
        eta = reshuffle.end_time
        detaching_the_driver_from_the_car.apply_async((partner_pk, reshuffle.swap_vehicle.licence_plate), eta=eta)


@app.task(bind=True, queue='bot_tasks')
def detaching_the_driver_from_the_car(self, partner_pk, licence_plate):
    try:
        fleet = UklonRequest.objects.get(partner=partner_pk)
        fleet.detaching_the_driver_from_the_car(licence_plate)
        logger.info(f'Car {licence_plate} was detached')
    except Exception as e:
        logger.error(e)


@app.task(bind=True, queue='beat_tasks')
def get_rent_information(self, partner_pk, schema, day=None):
    try:
        end, start = get_time_for_task(schema, day)[1:3]
        gps = UaGpsSynchronizer.objects.get(partner=partner_pk)
        gps.save_daily_rent(start, end, schema)
        logger.info('write rent report')
    except Exception as e:
        logger.error(e)


@app.task(bind=True, queue='beat_tasks')
def get_today_rent(self, partner_pk):
    try:
        gps = UaGpsSynchronizer.objects.get(partner=partner_pk)
        gps.check_today_rent()
    except Exception as e:
        logger.error(e)


@app.task(bind=True, queue='bot_tasks')
def fleets_cash_trips(self, partner_pk, pk, enable):
    try:
        driver = Driver.objects.get(pk=pk)
        fleets = Fleet.objects.filter(partner=partner_pk).exclude(name='Gps')
        for fleet in fleets:
            driver_id = driver.get_driver_external_id(fleet.name)
            if driver_id:
                fleet.disable_cash(driver_id, enable)
        message = f"Cash enabled for {driver}" if enable == 'true' else f"Cash disabled for {driver}"
        logger.info(message)
    except Exception as e:
        logger.error(e)


@app.task(bind=True, queue='beat_tasks')
def withdraw_uklon(self, partner_pk):
    try:
        fleet = UklonRequest.objects.get(partner=partner_pk)
        fleet.withdraw_money()
    except Exception as e:
        logger.error(e)


@app.task(bind=True, queue='beat_tasks')
def manager_paid_weekly(self, partner_pk):
    logger.info('send message to manager')
    return partner_pk


@app.task(bind=True, queue='beat_tasks')
def send_driver_report(self, partner_pk, schema):
    result = []
    managers = list(Manager.objects.filter(
        partner=partner_pk, chat_id__isnull=False).exclude(chat_id='').values_list('chat_id', flat=True))
    managers.extend(list(Partner.objects.filter(
        pk=partner_pk, chat_id__isnull=False).exclude(chat_id='').values_list('chat_id', flat=True)))
    for manager in managers:
        result.append(generate_message_report(manager, schema))
    return result


@app.task(bind=True, queue='beat_tasks')
def send_daily_statistic(self, partner_pk, schema):
    message = ''
    driver_dict_msg = {}
    dict_msg = {}
    driver_schema = Schema.objects.get(pk=schema)
    managers = list(Manager.objects.filter(
        partner=partner_pk, chat_id__isnull=False).exclude(chat_id='').values('chat_id') or Partner.objects.filter(
        pk=partner_pk, chat_id__isnull=False).exclude(chat_id='').values('chat_id'))
    for manager in managers:
        result = get_daily_report(manager['chat_id'], driver_schema)
        if result:
            for num, key in enumerate(result[0], 1):
                if result[0][key]:
                    driver_msg = "{}\nКаса: {:.2f} (+{:.2f})\n Оренда: {:.2f}км (+{:.2f})\n\n".format(
                        key, result[0][key], result[1].get(key, 0), result[2].get(key, 0), result[3].get(key, 0))
                    driver_dict_msg[key.pk] = driver_msg
                    message += f"{num}.{driver_msg}"
            if partner_pk in dict_msg:
                dict_msg[partner_pk] += message
            else:
                dict_msg[partner_pk] = message
    return dict_msg, driver_dict_msg


@app.task(bind=True, queue='beat_tasks')
def send_efficiency_report(self, partner_pk):
    message = ''
    dict_msg = {}
    managers = list(Manager.objects.filter(partner=partner_pk).values('chat_id'))
    if not managers:
        managers = [Partner.objects.filter(pk=partner_pk).values('chat_id').first()]
    for manager in managers:
        result = get_efficiency(manager_id=manager['chat_id'])
        if result:
            for k, v in result.items():
                message += f"{k}\n" + "".join(v) + "\n"
            if partner_pk in dict_msg:
                dict_msg[partner_pk] += message
            else:
                dict_msg[partner_pk] = message
    return dict_msg


@app.task(bind=True, queue='beat_tasks')
def send_driver_efficiency(self, partner_pk, schema):
    message = ''
    driver_dict_msg = {}
    dict_msg = {}
    driver_schema = Schema.objects.get(pk=schema)
    managers = list(Manager.objects.filter(partner=partner_pk).values_list('chat_id', flat=True))
    if not managers:
        managers = [Partner.objects.filter(pk=partner_pk).values_list('chat_id', flat=True).first()]
    for manager in managers:
        result = get_driver_efficiency_report(manager_id=manager, schema=driver_schema)
        if result:
            for k, v in result.items():
                driver_msg = f"{k}\n" + "".join(v)
                driver_dict_msg[k.pk] = driver_msg
                message += driver_msg + "\n"
            if partner_pk in dict_msg:
                dict_msg[partner_pk] += message
            else:
                dict_msg[partner_pk] = message
    return dict_msg, driver_dict_msg


@app.task(bind=True, queue='bot_tasks')
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
    redis_instance().hset('group_msg', order_id, group_msg.message_id)
    instance.checked = True
    instance.save()


@app.task(bind=True, queue='beat_tasks')
def check_personal_orders(self):
    for order in Order.objects.filter(status_order=Order.IN_PROGRESS, type_order=Order.PERSONAL_TYPE):
        finish_time = timezone.localtime(order.order_time) + timedelta(hours=order.payment_hours)
        distance = int(order.payment_hours) * int(ParkSettings.get_value('AVERAGE_DISTANCE_PER_HOUR'))
        notify_min = int(ParkSettings.get_value('PERSONAL_CLIENT_NOTIFY_MIN'))
        notify_km = int(ParkSettings.get_value('PERSONAL_CLIENT_NOTIFY_KM'))
        vehicle = check_vehicle(order.driver)[0]
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


@app.task(bind=True, queue='beat_tasks')
def add_money_to_vehicle(self, partner_pk):
    day = timezone.localtime() - timedelta(days=1)
    for vehicle in Vehicle.objects.filter(partner=partner_pk, investor_car__isnull=False):
        efficiency = CarEfficiency.objects.filter(report_from=day.date(), vehicle=vehicle).first()
        kasa = efficiency.total_kasa if efficiency else 0
        currency = vehicle.currency_back
        total_kasa = kasa * vehicle.investor_percentage
        if currency != Vehicle.Currency.UAH:
            car_earnings, rate = convert_to_currency(float(total_kasa), currency)
        else:
            car_earnings = total_kasa
            rate = 0.00
        InvestorPayments.objects.get_or_create(
            report_from=day.date(),
            vehicle=vehicle,
            investor=vehicle.investor_car,
            partner_id=partner_pk,
            defaults={
                "sum_before_transaction": total_kasa,
                "currency": currency,
                "currency_rate": rate,
                "sum_after_transaction": car_earnings})


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
                vehicle = check_vehicle(driver)[0]
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
            vehicle = check_vehicle(driver)[0]
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


@app.task(bind=True, max_retries=10, queue='beat_tasks')
def get_driver_reshuffles(self, partner, delta=0):
    day = timezone.localtime().date() - timedelta(days=delta)
    start = timezone.make_aware(datetime.combine(day, time.min))
    end = timezone.make_aware(datetime.combine(day, time.max))
    obj_partner = list(Partner.objects.filter(pk=partner))
    managers = list(Manager.objects.filter(partner=partner))
    users = obj_partner + managers
    for user in users:
        try:
            events = GoogleCalendar().get_list_events(user.calendar, start, end)
            list_events = []
            for event in events['items']:
                calendar_event_id = event['id']
                list_events.append(calendar_event_id)
                event_summary = event['summary'].split(',')
                licence_plate, driver = event_summary
                name, second_name = driver.split()
                driver_start = Driver.objects.filter(Q(name=name, second_name=second_name) |
                                                     Q(name=second_name, second_name=name)).first()
                vehicle = Vehicle.objects.filter(licence_plate=licence_plate.split()[0]).first()
                try:
                    swap_time = timezone.make_aware(datetime.strptime(event['start']['date'], "%Y-%m-%d"))
                    end_time = timezone.make_aware(datetime.combine(swap_time, time.max))
                except KeyError:
                    swap_time = datetime.strptime(event['start']['dateTime'], "%Y-%m-%dT%H:%M:%S%z")
                    end_time = datetime.strptime(event['end']['dateTime'], "%Y-%m-%dT%H:%M:%S%z")
                obj_data = {
                    "calendar_event_id": calendar_event_id,
                    "swap_vehicle": vehicle,
                    "driver_start": driver_start,
                    "swap_time": swap_time,
                    "end_time": end_time,
                    "partner_id": partner
                }
                reshuffle = DriverReshuffle.objects.filter(calendar_event_id=calendar_event_id)
                reshuffle.update(**obj_data) if reshuffle else DriverReshuffle.objects.create(**obj_data)
            if delta:
                deleted_reshuffles = DriverReshuffle.objects.filter(
                    partner=partner,
                    swap_time__date=day).exclude(calendar_event_id__in=list_events)
                for reshuffle in deleted_reshuffles:
                    reshuffle.delete()
        except socket.timeout:
            self.retry(args=[partner, delta], countdown=600)


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


@app.task(bind=True, queue='beat_tasks')
def calculate_driver_reports(self, partner_pk, schema, day=None):
    schema_obj = Schema.objects.get(pk=schema)
    if schema_obj.salary_calculation == SalaryCalculation.WEEK:
        if not timezone.localtime().weekday():
            start = timezone.localtime().date() - timedelta(weeks=1)
            end = timezone.localtime().date() - timedelta(days=1)
        else:
            return
    else:
        end, start = get_time_for_task(schema, day)[1:3]
    for driver in Driver.objects.get_active(partner=partner_pk, schema=schema):
        if DriverPayments.objects.filter(report_from=start,
                                         report_to=end,
                                         driver=driver).exists():
            continue
        create_driver_payments(start, end, driver, schema_obj)


@app.task(bind=True, queue='beat_tasks')
def calculate_vehicle_earnings(self, partner_pk, day=None):
    if not day:
        day = timezone.localtime() - timedelta(days=1)
    drivers = Driver.objects.get_active(partner=partner_pk, schema__isnull=False).select_related('partner')
    for driver in drivers:
        payment = DriverPayments.objects.filter(report_to=day, driver=driver, partner=driver.partner).first()
        if payment:
            spending_rate = 1 - round((payment.salary + payment.cash + payment.rent) / payment.kasa, 6)
            print(spending_rate)
            print(payment)
            vehicles_income = get_vehicle_income(driver, payment.report_from, payment.report_to,
                                                 spending_rate, payment.rent_price)
            print(vehicles_income)
            for vehicle, income in vehicles_income.items():
                PartnerEarnings.objects.get_or_create(
                    report_from=payment.report_from,
                    report_to=payment.report_to,
                    vehicle_id=vehicle.id,
                    driver=driver,
                    partner=driver.partner,
                    defaults={
                        "earning": income,
                    }
                )


@app.task(bind=True, queue='beat_tasks')
def check_cash_and_vehicle(self, partner_pk):
    tasks = chain(get_today_orders.si(partner_pk),
                  send_notify_to_check_car.si(partner_pk),
                  check_card_cash_value.si(partner_pk)
                  )
    tasks()


@app.task(bind=True, queue='beat_tasks')
def get_information_from_fleets(self, partner_pk, schema, day=None):
    task_chain = chain(
        download_daily_report.si(partner_pk, schema, day),
        get_orders_from_fleets.si(partner_pk, schema, day),
        check_orders_for_vehicle.si(partner_pk, schema),
        generate_payments.si(partner_pk, schema, day),
        generate_summary_report.si(partner_pk, schema, day),
        calculate_driver_reports.si(partner_pk, schema, day),
        get_driver_efficiency.si(partner_pk, schema, day),
        get_rent_information.si(partner_pk, schema, day),
        send_daily_statistic.si(partner_pk, schema),
        send_driver_efficiency.si(partner_pk, schema),
        send_driver_report.si(partner_pk, schema),
    )
    task_chain()


@app.task(bind=True, queue='beat_tasks')
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
                    name=f'auto.tasks.{db_task.name}({partner.pk})',
                    task=f'auto.tasks.{db_task.name}',
                    defaults={
                        'interval': interval_schedule,
                        'start_time': next_execution_datetime,
                        'args': partner.pk
                    }
                )
        else:
            day = '1' if db_task.weekly else '*'
            hours = f"*/{db_task.task_time.strftime('%H')}" if db_task.periodic else db_task.task_time.strftime('%H')
            minutes = db_task.task_time.strftime('%M')
            schedule = get_schedule(hours, minutes, day)

            for partner in partners:
                create_task(db_task.name, partner.pk, schedule, db_task.arguments)
    for schema in work_schemas:
        if schema.shift_time != time.min:
            schedule = get_schedule(schema.shift_time.hour, schema.shift_time.minute)
        else:
            schedule = get_schedule("08", "00")
        create_task('get_information_from_fleets', schema.partner.pk, schedule, schema.pk)
        night_schedule = get_schedule("05", "59")
        create_task("download_nightly_report", schema.partner.pk, night_schedule, schema.pk)


@app.on_after_finalize.connect
def run_periodic_tasks(sender, **kwargs):
    # sender.add_periodic_task(crontab(minute="*/2"), send_time_order.s())
    sender.add_periodic_task(crontab(minute='*/15'), auto_send_task_bot.s())
    # sender.add_periodic_task(crontab(minute="*/2"), order_not_accepted.s())
    # sender.add_periodic_task(crontab(minute="*/4"), check_personal_orders.s())
    sender.add_periodic_task(crontab(minute="0", hour="*/1"), update_schedule.s())


def setup_periodic_tasks(driver, sender=None):
    if sender is None:
        sender = current_app
#     partner_id = partner.pk
#     sender.add_periodic_task(20, update_driver_status.s(partner_id))
#     sender.add_periodic_task(crontab(minute="0", hour="*/3"), update_driver_data.s(partner_id))
#     sender.add_periodic_task(crontab(minute="0", hour="4"), download_daily_report.s(partner_id))
#     # repeat
#     sender.add_periodic_task(crontab(minute="0", hour='*/2'), withdraw_uklon.s(partner_id))
#     sender.add_periodic_task(crontab(minute="40", hour='4'), get_rent_information.s(partner_id))
#     sender.add_periodic_task(crontab(minute="10", hour='*/4'), get_today_rent.s(partner_id))
#     sender.add_periodic_task(crontab(minute="30", hour='1'), get_driver_reshuffles.s(partner_id, delta=1))
#     sender.add_periodic_task(crontab(minute="2", hour='*/2'), get_driver_reshuffles.s(partner_id))
#     sender.add_periodic_task(crontab(minute="15", hour='4'), get_orders_from_fleets.s(partner_id))
#     sender.add_periodic_task(crontab(minute='20', hour='4'), check_orders_for_vehicle.s(partner_id))
#     sender.add_periodic_task(crontab(minute="0", hour='*/2'), get_today_orders.s(partner_id))
#     sender.add_periodic_task(crontab(minute="5", hour='*/2'), send_notify_to_check_car.s(partner_id))
#     sender.add_periodic_task(crontab(minute="5", hour='*/2'), check_card_cash_value.s(partner_id))
#     sender.add_periodic_task(crontab(minute="2", hour="9"), send_driver_efficiency.s(partner_id))
#     sender.add_periodic_task(crontab(minute="0", hour="9"), send_efficiency_report.s(partner_id))
#     sender.add_periodic_task(crontab(minute="30", hour="7"), get_car_efficiency.s(partner_id))
#     sender.add_periodic_task(crontab(minute="0", hour="5"), add_money_to_vehicle.s(partner_id))
#     sender.add_periodic_task(crontab(minute="25", hour="4"), get_driver_efficiency.s(partner_id))
#     sender.add_periodic_task(crontab(minute="1", hour="9"), send_daily_statistic.s(partner_id))
#     sender.add_periodic_task(crontab(minute="55", hour="4"), calculate_driver_reports.s(partner_id, daily=True))
#     sender.add_periodic_task(crontab(minute="55", hour="4", day_of_week="1"),
#                              calculate_driver_reports.s(partner_id))
#     sender.add_periodic_task(crontab(minute="55", hour="8", day_of_week="1"),
#                              send_driver_report.s(partner_id))
#     sender.add_periodic_task(crontab(minute="56", hour="8"), send_driver_report.s(partner_id, daily=True))
#     # sender.add_periodic_task(crontab(minute="55", hour="11", day_of_week="1"),
#     # manager_paid_weekly.s(partner_id))
#     sender.add_periodic_task(crontab(minute="55", hour="9", day_of_week="1"),
#                              get_session.s(partner_id))


def remove_periodic_tasks(partner, sender=None):
    if sender is None:
        sender = current_app
    partner_id = partner.pk
    sender.remove_periodic_task(f"update_driver_status.s({partner_id})")
    sender.remove_periodic_task(f"update_driver_data.s({partner_id})")
    sender.remove_periodic_task(f"download_daily_report.s({partner_id})")
    sender.remove_periodic_task(f"withdraw_uklon.s({partner_id})")
    sender.remove_periodic_task(f"get_rent_information.s({partner_id})")
    sender.remove_periodic_task(f"send_efficiency_report.s({partner_id})")
    sender.remove_periodic_task(f"get_car_efficiency.s({partner_id})")
    sender.remove_periodic_task(f"send_daily_report.s({partner_id})")
    sender.remove_periodic_task(f"send_weekly_report.s({partner_id})")
    sender.remove_periodic_task(f"manager_paid_weekly.s({partner_id})")
    sender.remove_periodic_task(f"get_uber_session.s({partner_id})")
