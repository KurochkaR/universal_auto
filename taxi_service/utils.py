import json
import random
import secrets
import uuid
from datetime import timedelta, date, datetime, time

from django.db.models import Q
from django.utils import timezone
from django.core.mail import send_mail
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import ObjectDoesNotExist

from app.bolt_sync import BoltRequest
from app.models import Driver, UseOfCars, VehicleGPS, Order, ParkSettings, CredentialPartner, Fleet, \
    Vehicle, DriverReshuffle, CustomUser
from app.uagps_sync import UaGpsSynchronizer
from app.uber_sync import UberRequest
from app.uklon_sync import UklonRequest
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


def get_dates(period=None):
    current_date = datetime.combine(timezone.localtime(), time.min)

    if period == 'yesterday':
        previous_date = current_date - timedelta(days=1)
        start_date = previous_date
        end_date = current_date

    elif period == 'current_week':
        weekday = current_date.weekday()
        start_date = current_date - timedelta(days=weekday)
        end_date = start_date + timedelta(days=6)

    elif period == 'current_month':
        start_date = current_date.replace(day=1)
        next_month = current_date.replace(day=28) + timedelta(days=4)
        end_date = next_month - timedelta(days=next_month.day)

    elif period == 'current_quarter':
        current_month = current_date.month
        current_quarter = (current_month - 1) // 3 + 1

        if current_quarter == 1:
            start_date = datetime.combine(date(current_date.year, 1, 1), time.min)
            end_date = datetime.combine(date(current_date.year, 3, 31), time.max)
        elif current_quarter == 2:
            start_date = datetime.combine(date(current_date.year, 4, 1), time.min)
            end_date = datetime.combine(date(current_date.year, 6, 30), time.max)
        elif current_quarter == 3:
            start_date = datetime.combine(date(current_date.year, 7, 1), time.min)
            end_date = datetime.combine(date(current_date.year, 9, 30), time.max)
        else:
            start_date = datetime.combine(date(current_date.year, 10, 1), time.min)
            end_date = datetime.combine(date(current_date.year, 12, 31), time.max)

    elif period == 'last_week':
        start_date = current_date - timedelta(
            days=current_date.weekday() + 7)
        end_date = start_date + timedelta(days=6)

    elif period == 'last_month':
        last_month = current_date.replace(day=1) - timedelta(days=1)
        start_date = last_month.replace(day=1)
        end_date = last_month

    elif period == 'last_quarter':
        current_month = current_date.month
        current_quarter = (current_month - 1) // 3 + 1
        if current_quarter == 1:
            start_date = datetime.combine(date(current_date.year - 1, 10, 1), time.min)
            end_date = datetime.combine(date(current_date.year - 1, 12, 31), time.max)
        elif current_quarter == 2:
            start_date = datetime.combine(date(current_date.year, 1, 1), time.min)
            end_date = datetime.combine(date(current_date.year, 3, 31), time.max)
        elif current_quarter == 3:
            start_date = datetime.combine(date(current_date.year, 4, 1), time.min)
            end_date = datetime.combine(date(current_date.year, 6, 30), time.max)
        else:
            start_date = datetime.combine(date(current_date.year, 7, 1), time.min)
            end_date = datetime.combine(date(current_date.year, 9, 30), time.max)


    else:
        weekday = current_date.weekday()
        if weekday == 0:
            start_date = current_date - timedelta(days=7)
        else:
            start_date = current_date - timedelta(days=weekday)
        end_date = current_date

    start_date = datetime.combine(start_date, time.min)
    end_date = datetime.combine(end_date, time.max)
    return start_date, end_date


def get_start_end(period):
    if period in ('yesterday', 'current_week', 'current_month', 'current_quarter',
                  'last_week', 'last_month', 'last_quarter'):
        start, end = get_dates(period)
        format_start = start.strftime("%d.%m.%Y")
        format_end = end.strftime("%d.%m.%Y")
    else:
        start_str, end_str = period.split('&')
        start = datetime.combine(datetime.strptime(start_str, "%Y-%m-%d"), time.min)
        end = datetime.combine(datetime.strptime(end_str, "%Y-%m-%d"), time.max)
        format_start = ".".join(start_str.split("-")[::-1])
        format_end = ".".join(end_str.split("-")[::-1])
    return timezone.make_aware(start), timezone.make_aware(end), format_start, format_end


def update_park_set(partner, key, value, description=None, check_value=True, park=True):
    if park:
        try:
            setting = ParkSettings.objects.get(key=key, partner=partner)
            if setting.value != value and check_value:
                setting.value = value
                setting.save()
        except ObjectDoesNotExist:
            ParkSettings.objects.create(key=key, value=value, description=description, partner_id=partner)
    else:
        try:
            setting = CredentialPartner.objects.get(key=key, partner=partner)
            if CredentialPartner.decrypt_credential(value) != value and check_value:
                setting.value = CredentialPartner.encrypt_credential(value)
                setting.save()
        except ObjectDoesNotExist:
            value = CredentialPartner.encrypt_credential(value)
            CredentialPartner.objects.create(key=key, value=value, partner_id=partner)


def login_in(aggregator=None, partner_id=None, login_name=None, password=None, token=None):
    if aggregator == 'Bolt':
        update_park_set(partner_id, 'BOLT_PASSWORD', password, description='Пароль користувача Bolt', park=False)
        update_park_set(partner_id, 'BOLT_NAME', login_name, description='Ім\'я користувача Bolt', park=False)
        obj, created = BoltRequest.objects.get_or_create(name=aggregator, partner_id=partner_id)
    elif aggregator == 'Uklon':
        update_park_set(partner_id, 'UKLON_PASSWORD', password, description='Пароль користувача Uklon', park=False)
        update_park_set(partner_id, 'UKLON_NAME', login_name, description='Ім\'я користувача Uklon', park=False)
        update_park_set(partner_id, 'WITHDRAW_UKLON', '150000', description='Залишок грн на карті водія Uklon')
        obj, created = UklonRequest.objects.get_or_create(name=aggregator, partner_id=partner_id)
    elif aggregator == 'Uber':
        update_park_set(partner_id, 'UBER_PASSWORD', password, description='Пароль користувача Uber', park=False)
        update_park_set(partner_id, 'UBER_NAME', login_name, description='Ім\'я користувача Uber', park=False)
        obj, created = UberRequest.objects.get_or_create(name=aggregator, partner_id=partner_id)
    else:
        update_park_set(partner_id, 'UAGPS_TOKEN', token, description='Токен для GPS сервісу', park=False)
        obj, created = UaGpsSynchronizer.objects.get_or_create(name=aggregator, partner_id=partner_id)
    if not created:
        obj.deleted_at = None
        obj.save(update_fields=['deleted_at'])
    return True


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


def is_conflict(driver, vehicle, start_time, end_time, reshuffle_id_to_exclude=None):
    reshuffles = DriverReshuffle.objects.filter(
        Q(driver_start=driver) |
        Q(swap_vehicle=vehicle)
    )

    conflicts = reshuffles.filter(
        (Q(swap_time__range=(start_time, end_time)) | Q(end_time__range=(start_time, end_time))) |
        (Q(swap_time__lte=start_time, end_time__gte=end_time))
    )

    if reshuffle_id_to_exclude:
        conflicts = conflicts.exclude(id=reshuffle_id_to_exclude)

    overlapping_shifts = conflicts.filter(
        (Q(swap_time__lte=start_time) & Q(end_time__gt=start_time)) |
        (Q(swap_time__lt=end_time) & Q(end_time__gte=end_time)) |
        (Q(swap_time__gte=start_time) & Q(end_time__lte=end_time))
    )

    if overlapping_shifts.exists():
        conflicting_shift = overlapping_shifts.first()
        conflicting_time = (f"{timezone.localtime(conflicting_shift.swap_time).strftime('%Y-%m-%d %H:%M:%S')} "
                            f"{timezone.localtime(conflicting_shift.end_time).time()}")
        conflicting_vehicle_data = {
            'licence_plate': conflicting_shift.swap_vehicle.licence_plate,
            'conflicting_time': conflicting_time
        }
        return False, conflicting_vehicle_data
    else:
        return True, None


def add_shift(licence_plate, shift_date, start_time, end_time, driver_id, recurrence, partner):
    vehicle = Vehicle.objects.filter(licence_plate=licence_plate).first()
    driver = Driver.objects.get(id=driver_id)

    start_datetime = datetime.strptime(f"{shift_date} {start_time}", "%Y-%m-%d %H:%M")
    end_datetime = datetime.strptime(f"{shift_date} {end_time}", "%Y-%m-%d %H:%M")

    today_reshuffle = DriverReshuffle.objects.filter(
        swap_time__date=shift_date,
        swap_vehicle=vehicle
    ).count()

    if today_reshuffle > 3:
        return False, f"Авто {licence_plate} не може мати більше 4 змін на день"

    interval = range(1)

    if recurrence == 'daily':
        interval = range(0, 7)
    elif recurrence == 'everyOtherDay':
        interval = range(0, 7, 2)
    elif recurrence == 'every2Days':
        interval = range(0, 7, 4)
    elif recurrence == 'every3Days':
        interval = range(0, 7, 6)

    for day_offset in interval:
        current_date = start_datetime + timedelta(days=day_offset)

        current_swap_time = current_date.replace(hour=start_datetime.hour, minute=start_datetime.minute)
        current_end_time = current_date.replace(hour=end_datetime.hour, minute=end_datetime.minute)

        status, conflicting_vehicle = is_conflict(driver, vehicle, current_swap_time, current_end_time)
        if not status:
            return False, conflicting_vehicle

        reshuffle = DriverReshuffle.objects.create(
            swap_vehicle=vehicle,
            driver_start=driver,
            swap_time=current_swap_time,
            end_time=current_end_time,
            partner_id=partner.pk
        )
        reshuffle.save()
    return True, "Зміна успішно додана"


def delete_shift(action, reshuffle_id):
    try:
        reshuffle = DriverReshuffle.objects.get(id=reshuffle_id)
        if action == 'delete_shift':
            reshuffle.delete()
            text = "Зміна успішно видалена"
        else:
            reshuffle_del = DriverReshuffle.objects.filter(

                swap_time__gte=timezone.localtime(reshuffle.swap_time),
                swap_time__time=timezone.localtime(reshuffle.swap_time).time(),
                end_time__time=timezone.localtime(reshuffle.end_time).time(),
                driver_start=reshuffle.driver_start,
                swap_vehicle=reshuffle.swap_vehicle
            )
            reshuffle_count = reshuffle_del.count()
            reshuffle_del.delete()
            text = f"Видалено {reshuffle_count} змін"
    except ObjectDoesNotExist:
        text = "Виникла помилка, спробуйте ще раз"
        bot.send_message(chat_id=ParkSettings.get_value("DEVELOPER_CHAT_ID"), text="Reshuffle Does not exist")
    return True, text


def upd_shift(action, licence_id, start_time, end_time, shift_date, driver_id, reshuffle_id):
    start_datetime = datetime.strptime(shift_date + ' ' + start_time, '%Y-%m-%d %H:%M')
    end_datetime = datetime.strptime(shift_date + ' ' + end_time, '%Y-%m-%d %H:%M')

    if action == 'update_shift':
        status, conflicting_vehicle = is_conflict(driver_id, licence_id, start_datetime, end_datetime, reshuffle_id)
        if not status:
            return False, conflicting_vehicle

        DriverReshuffle.objects.filter(id=reshuffle_id).update(
            swap_time=start_datetime,
            end_time=end_datetime,
            driver_start=driver_id,
            swap_vehicle=licence_id
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

        successful_updates = 0
        for reshuffle in reshuffle_upd:
            start = datetime.combine(timezone.localtime(reshuffle.swap_time).date(), start_datetime.time())
            end = datetime.combine(timezone.localtime(reshuffle.end_time).date(), end_datetime.time())
            status, conflicting_vehicle = is_conflict(driver_id, licence_id, start, end, reshuffle.id)
            if not status:
                return False, conflicting_vehicle

            reshuffle.swap_time = start
            reshuffle.end_time = end
            reshuffle.driver_start_id = driver_id
            reshuffle.swap_vehicle_id = licence_id
            reshuffle.save()
            successful_updates += 1
        return True, f"Оновлено {successful_updates} змін"
    return True
