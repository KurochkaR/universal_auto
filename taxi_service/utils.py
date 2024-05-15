import json
import os
import random
from datetime import timedelta, date, datetime, time

import requests
from django.db.models import Q
from django.utils import timezone
from django.core.mail import send_mail
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import ObjectDoesNotExist

from app.models import Driver, UseOfCars, VehicleGPS, Order, ParkSettings, CredentialPartner, Fleet, \
    Vehicle, DriverReshuffle
from auto_bot.main import bot
from scripts.redis_conn import get_logger


def active_vehicles_gps():
    vehicles_gps = []
    active_drivers = Driver.objects.filter(driver_status=Driver.ACTIVE, vehicle__isnull=False)
    for driver in active_drivers:
        vehicle = {'licence_plate': driver.vehicle.licence_plate,
                   'lat': driver.vehicle.lat,
                   'lon': driver.vehicle.lon
                   }
        vehicles_gps.append(vehicle)
    json_data = json.dumps(vehicles_gps, cls=DjangoJSONEncoder)
    return json_data


def order_confirm(id_order):
    order = Order.objects.get(id=id_order)
    car_delivery_price = order.car_delivery_price
    driver = order.driver
    vehicle = UseOfCars.objects.filter(user_vehicle=driver).first()
    if vehicle is not None:
        vehicle_gps = VehicleGPS.objects.filter(
            vehicle__licence_plate=vehicle.licence_plate
        ).values('vehicle__licence_plate', 'lat', 'lon')
        data = {
            'vehicle_gps': list(vehicle_gps),
            'car_delivery_price': car_delivery_price
        }
        json_data = json.dumps(data, cls=DjangoJSONEncoder)
        return json_data
    else:
        return "[]"


def update_order_sum_or_status(id_order, action):
    if action == 'user_opt_out':
        order = Order.objects.get(id=id_order)
        order.status_order = Order.CANCELED
        order.save()


def restart_order(id_order, car_delivery_price, action):
    if action == 'increase_price':
        order = Order.objects.get(id=id_order)
        order.car_delivery_price = car_delivery_price
        order.checked = False
        order.save()

    if action == 'continue_search':
        order = Order.objects.get(id=id_order)
        order.checked = False
        order.save()


# Робота з dashboard.html


def get_dates(period, day=None):
    current_date = timezone.localtime() if not day else datetime.strptime(day, "%Y-%m-%d")
    previous_date = current_date - timedelta(days=1)
    start_current_week = current_date - timedelta(days=current_date.weekday())
    start_current_month = current_date.replace(day=1)
    current_quarter = (current_date.month - 1) // 3 + 1
    start_last_week = start_current_week - timedelta(days=7)
    end_last_month = start_current_month - timedelta(days=1)

    quarters = {0: (date(current_date.year - 1, 10, 1), date(current_date.year - 1, 12, 31)),
                1: (date(current_date.year, 1, 1), date(current_date.year, 3, 31)),
                2: (date(current_date.year, 4, 1), date(current_date.year, 6, 30)),
                3: (date(current_date.year, 7, 1), date(current_date.year, 9, 30)),
                4: (date(current_date.year, 10, 1), date(current_date.year, 12, 31)),}

    periods = {'today': (current_date, current_date),
               'yesterday': (previous_date, previous_date),
               'current_week': (start_current_week, current_date),
               'current_month': (start_current_month, current_date),
               'current_quarter': (quarters.get(current_quarter)[0], current_date),
               'last_week': (start_last_week, start_last_week + timedelta(days=6)),
               'last_month': (end_last_month.replace(day=1), end_last_month),
               'last_quarter': quarters.get(current_quarter - 1),
               }

    start_date, end_date = periods.get(period)
    start_date = timezone.make_aware(datetime.combine(start_date, time.min))
    end_date = timezone.localtime() if period == "today" and not day else (
        timezone.make_aware(datetime.combine(end_date, time.max.replace(microsecond=0))))
    return start_date, end_date


def get_start_end(period, day=None):
    if period in ('today', 'yesterday', 'current_week', 'current_month', 'current_quarter',
                  'last_week', 'last_month', 'last_quarter'):
        start, end = get_dates(period, day)
    elif period != 'all_period':
        start_str, end_str = period.split('&')
        start = timezone.make_aware(datetime.combine(datetime.strptime(start_str, "%Y-%m-%d"), time.min))
        end = timezone.make_aware(datetime.combine(datetime.strptime(end_str, "%Y-%m-%d"),
                                                   time.max.replace(microsecond=0)))
    else:
        return None, None, None, None
    format_start = start.strftime("%d.%m.%Y")
    format_end = end.strftime("%d.%m.%Y")
    return start, end, format_start, format_end


def update_park_set(partner, key, park_value, description=None, check_value=True, park=True):
    data = {"description": description,
            "value": park_value if park else CredentialPartner.encrypt_credential(park_value)
            }
    if park:
        setting, created = ParkSettings.objects.get_or_create(key=key, partner_id=partner, defaults=data)
    else:
        setting, created = CredentialPartner.objects.get_or_create(key=key, partner_id=partner,
                                                                   defaults={'value': data['value']})
    if all([not created, setting.value != data['value'], check_value]):
        setting.value = data['value']
        setting.save(update_fields=['value'])


def login_in(aggregator=None, partner_id=None, login_name=None, password=None, token=None):
    credential_dict = {
        'Uber': (('UBER_NAME', login_name), ('UBER_PASSWORD', password)),
        'Bolt': (('BOLT_NAME', login_name), ('BOLT_PASSWORD', password)),
        'Uklon': (('UKLON_NAME', login_name), ('UKLON_PASSWORD', password)),
        'Gps': (('UAGPS_TOKEN', token),)
    }
    settings = credential_dict.get(aggregator)
    for setting in settings:
        update_park_set(partner_id, setting[0], setting[1], park=False)
    if aggregator == 'Uklon':
        update_park_set(partner_id, 'WITHDRAW_UKLON', '150000', description='Залишок грн на карті водія Uklon')


def partner_logout(aggregator, partner_pk):
    settings = ParkSettings.objects.filter(partner=partner_pk)
    Fleet.objects.filter(name=aggregator, partner=partner_pk).update(deleted_at=timezone.localtime())
    credentials = CredentialPartner.objects.filter(partner=partner_pk)
    if aggregator == 'Uklon':
        settings.filter(key='WITHDRAW_UKLON').delete()

    credential_dict = {
        'Uber': ('UBER_NAME', 'UBER_PASSWORD'),
        'Bolt': ('BOLT_NAME', 'BOLT_PASSWORD'),
        'Uklon': ('UKLON_NAME', 'UKLON_PASSWORD'),
        'Gps': ('UAGPS_TOKEN',)
    }

    credential_action = credential_dict.get(aggregator)
    if credential_action:
        credentials.filter(key__in=credential_action).delete()
    return True


def login_in_investor(request, login_name, password):
    user = authenticate(username=login_name, password=password)
    if user is not None:
        if user.is_active:
            login(request, user)
            if user.is_superuser:
                return {'success': True}
            user_name = user.username

            return {'success': True, 'user_name': user_name}
        else:
            return {'success': False, 'message': 'User is not active'}
    else:
        return {'success': False, 'message': 'User is not found'}


def send_reset_code(email, user_login):
    try:
        reset_code = str(random.randint(100000, 999999))

        subject = 'Код скидання пароля'
        message = (
            f'Вас вітає Ninja-Taxi!\nВи запросили відновлення пароля.'
            f'\nЯкщо ви цього не робили просто проігноруйте це повідомлення.'
            f'\nЯкщо все таки це ви то ось ваші данні для відновлення.\n'
            f'Ваш код скидання пароля: {reset_code}\n'
            f'Ваш логін: {user_login}\n'
        )
        from_email = 'Ninja-Taxi@gmail.com'
        recipient_list = [email]
        send_mail(subject, message, from_email, recipient_list)
        return email, reset_code
    except Exception as error:
        get_logger().error(error)


def check_aggregators(user_pk):
    aggregators = Fleet.objects.filter(partner=user_pk, deleted_at=None).values_list('name', flat=True)
    fleets = Fleet.objects.all().values_list('name', flat=True).distinct()
    return list(aggregators), list(fleets)


def get_overlapping_query(start_time, end_time):
    overlapping_shifts = Q(
        (Q(swap_time__lte=start_time) & Q(end_time__gt=start_time)) |
        (Q(swap_time__lt=end_time) & Q(end_time__gte=end_time)) |
        (Q(swap_time__gte=start_time) & Q(end_time__lte=end_time))
    )
    return overlapping_shifts


def is_conflict(driver, vehicle, overlapping_shifts, reshuffle_upd=()):
    filter_query = Q(swap_vehicle=vehicle)
    if driver:
        filter_query |= Q(driver_start=driver)
    reshuffles = DriverReshuffle.objects.filter(filter_query, overlapping_shifts).exclude(id__in=reshuffle_upd)
    conflict_list = []
    conflict_dates = reshuffles.values_list("swap_time__date", flat=True)
    for reshuffle in reshuffles:
        conflicting_time = (f"{timezone.localtime(reshuffle.swap_time).strftime('%d.%m %H:%M')} "
                            f"{timezone.localtime(reshuffle.end_time).strftime('%H:%M')}")
        conflicting_vehicle_data = {
                'licence_plate': reshuffle.swap_vehicle.licence_plate,
                'conflicting_time': conflicting_time
            }
        conflict_list.append(conflicting_vehicle_data)

    return conflict_list, conflict_dates


def add_shift(licence_plate, shift_date, start_time, end_time, driver_id, recurrence, partner):
    instances = []
    vehicle = Vehicle.objects.filter(licence_plate=licence_plate).first()
    driver = Driver.objects.get(id=driver_id) if driver_id not in ['accident', 'maintenance'] else None
    start_datetime = datetime.strptime(f"{shift_date} {start_time}", "%Y-%m-%d %H:%M:%S")
    end_datetime = datetime.strptime(f"{shift_date} {end_time}", "%Y-%m-%d %H:%M:%S")


    today_reshuffle = DriverReshuffle.objects.filter(
        swap_time__date=shift_date,
        swap_vehicle=vehicle
    ).count()

    if today_reshuffle > 3:
        return False, f"Авто {licence_plate} не може мати більше 4 змін на день"
    calendar_range = int(ParkSettings.get_value("CALENDAR_RANGE", 10, partner=partner))
    reshuffle_ranges = calendar_range if calendar_range <= 30 else 10
    recurrence_map = {
        'daily': range(0, reshuffle_ranges),
        'everyOtherDay': range(0, reshuffle_ranges, 2),
        'every2Days': range(0, reshuffle_ranges, 4),
        'every3Days': range(0, reshuffle_ranges, 6)
    }
    interval = recurrence_map.get(recurrence, range(1))
    overlapping_query = None
    time_dict = {}
    for day_offset in interval:
        current_date = start_datetime + timedelta(days=day_offset)
        current_swap_time = timezone.make_aware(datetime.combine(current_date, start_datetime.time()))
        current_end_time = timezone.make_aware(datetime.combine(current_date, end_datetime.time()))
        time_dict[current_date.date()] = (current_swap_time, current_end_time)
        if overlapping_query:
            overlapping_query |= get_overlapping_query(current_swap_time, current_end_time)
        else:
            overlapping_query = get_overlapping_query(current_swap_time, current_end_time)

    messages, conflict_times = is_conflict(driver, vehicle, overlapping_query)

    for key_date, (start, end) in time_dict.items():
        if key_date not in conflict_times:
            reshuffle = DriverReshuffle(
                swap_vehicle=vehicle,
                driver_start=driver,
                swap_time=start,
                end_time=end,
                partner_id=partner.pk,
                dtp_or_maintenance=driver_id
            )
            instances.append(reshuffle)

    DriverReshuffle.objects.bulk_create(instances)
    return (False, messages) if messages else (True, "Зміна успішно додана")


def delete_shift(action, reshuffle_id):
    try:
        reshuffle = DriverReshuffle.objects.get(id=reshuffle_id)
        if action == 'delete_shift':
            reshuffle.delete()
            text = "Зміна успішно видалена"
        else:
            reshuffle_count, _ = DriverReshuffle.objects.filter(
                swap_time__gte=timezone.localtime(reshuffle.swap_time),
                swap_time__time=timezone.localtime(reshuffle.swap_time).time(),
                end_time__time=timezone.localtime(reshuffle.end_time).time(),
                driver_start=reshuffle.driver_start,
                swap_vehicle=reshuffle.swap_vehicle
            ).delete()
            text = f"Видалено {reshuffle_count} змін"
    except ObjectDoesNotExist:
        text = "Виникла помилка, спробуйте ще раз"
        bot.send_message(chat_id=ParkSettings.get_value("DEVELOPER_CHAT_ID"), text="Reshuffle Does not exist")
    return True, text


def upd_shift(action, licence_id, start_time, end_time, shift_date, driver_id, reshuffle_id):
    start_datetime = datetime.strptime(shift_date + ' ' + start_time, '%Y-%m-%d %H:%M:%S')
    end_datetime = datetime.strptime(shift_date + ' ' + end_time, '%Y-%m-%d %H:%M:%S')
    driver = driver_id if driver_id not in ['accident', 'maintenance'] else None
    if action == 'update_shift':
        overlapping = get_overlapping_query(start_datetime, end_datetime)
        conflicting_message, conflict_time = is_conflict(driver, licence_id, overlapping, [reshuffle_id])
        if conflicting_message:
            return False, conflicting_message

        DriverReshuffle.objects.filter(id=reshuffle_id).update(
            swap_time=start_datetime,
            end_time=end_datetime,
            driver_start=driver,
            swap_vehicle=licence_id,
            dtp_or_maintenance=driver_id if not driver else None
        )
        return True, "Зміна успішно оновлена"

    elif action == 'update_all_shift':
        selected_reshuffle = DriverReshuffle.objects.get(id=reshuffle_id)
        reshuffle_upd = DriverReshuffle.objects.filter(
            swap_time__gte=timezone.localtime(selected_reshuffle.swap_time),
            swap_time__time=timezone.localtime(selected_reshuffle.swap_time).time(),
            end_time__time=timezone.localtime(selected_reshuffle.end_time).time(),
            driver_start=selected_reshuffle.driver_start,
            swap_vehicle=selected_reshuffle.swap_vehicle
        ).order_by('id')
        overlapping_query = None
        updated_reshuffles = []
        time_dict = {}
        for reshuffle in reshuffle_upd:
            start = timezone.make_aware(datetime.combine(timezone.localtime(reshuffle.swap_time).date(), start_datetime.time()))
            end = timezone.make_aware(datetime.combine(timezone.localtime(reshuffle.end_time).date(), end_datetime.time()))
            time_dict[timezone.localtime(reshuffle.swap_time).date()] = (reshuffle, start, end)
            if overlapping_query:
                overlapping_query |= get_overlapping_query(start, end)
            else:
                overlapping_query = get_overlapping_query(start, end)
        messages, conflict_times = is_conflict(driver, licence_id, overlapping_query, reshuffle_upd)
        for reshuffle_time, (reshuffle, start, end) in time_dict.items():
            if reshuffle_time not in conflict_times:
                reshuffle.swap_time = start
                reshuffle.end_time = end
                reshuffle.driver_start_id = driver
                reshuffle.swap_vehicle_id = licence_id
                reshuffle.dtp_or_maintenance = driver_id if not driver else None
                updated_reshuffles.append(reshuffle)

        DriverReshuffle.objects.bulk_update(updated_reshuffles,
                                            fields=['swap_time', 'end_time', 'driver_start', 'swap_vehicle',
                                                    'dtp_or_maintenance'])
        return (True, f"Оновлено {len(updated_reshuffles)} змін") if not messages else (False, messages)


def sending_to_crm(name, phone, theme, email=None, city=None, vehicle=None, year=None):
    default_token_key = 'BINOTEL_TOKEN'
    calculation_token_key = 'BINOTEL_TOKEN_CALCULATION'

    default_token = os.environ.get(default_token_key)
    calculation_token = os.environ.get(calculation_token_key)

    token = calculation_token if theme == 'Розрахунок вартості' else default_token

    formData = {
        "name": "Заявка на консультацию" if theme != 'Розрахунок вартості' else "Заявка на розрахунок вартості",
        "fields": [{"fieldId": 14024, "value": theme}]
    }

    customerDraft = {"name": name, "number": phone, "email": email}

    if theme == 'Розрахунок вартості':
        del customerDraft['email']
        formData["fields"].extend([
            {"fieldId": 43309, "value": city},
            {"fieldId": 43307, "value": vehicle},
            {"fieldId": 43308, "value": year}
        ])

    formData["customerDraft"] = customerDraft
    url = f"https://my.binotel.ua/b/smartcrm/api/widget/v1/deal/create?token={token}"
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json=formData)

    return response.status_code
