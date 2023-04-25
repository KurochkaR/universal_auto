import re
import datetime
import threading
import time
import os
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from telegram import ReplyKeyboardRemove, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, \
    KeyboardButton

from app.models import Order, ParkSettings, User, Driver, Vehicle, UseOfCars, ParkStatus
from auto.tasks import logger
from auto_bot.handlers.order.keyboards import location_keyboard, order_keyboard, markup_keyboard, timeorder_keyboard, \
    markup_keyboard_onetime, payment_keyboard, inline_markup_accept, inline_spot_keyboard
from auto_bot.main import bot
from scripts.conversion import get_address, get_addresses_by_radius, geocode, get_location_from_db, get_route_price
from auto_bot.handlers.order.static_text import *

STATE = None


def continue_order(update, context):
    order = Order.objects.filter(chat_id_client=update.message.chat.id, status_order__in=[Order.ON_TIME, Order.WAITING])
    if order:
        update.message.reply_text(already_ordered)
    else:
        update.message.reply_text(price_info)

    reply_markup = markup_keyboard(order_keyboard)

    update.message.reply_text(continue_ask, reply_markup=reply_markup)


def time_for_order(update, context):
    global STATE
    STATE = START_TIME_ORDER
    reply_markup = markup_keyboard(timeorder_keyboard)
    update.message.reply_text(timeorder_ask, reply_markup=reply_markup)


def cancel_order(update, context):
    update.message.reply_text(canceled_order_text,  reply_markup=ReplyKeyboardRemove())
    cancel(update, context)


def location(update, context):
    global STATE
    STATE = None
    m = update.message
    # geocoding lat and lon to address
    context.user_data['latitude'], context.user_data['longitude'] = m.location.latitude, m.location.longitude
    address = get_address(context.user_data['latitude'], context.user_data['longitude'], os.environ["GOOGLE_API_KEY"])
    if address is not None:
        context.user_data['location_address'] = address
        update.message.reply_text(f'Ваша адреса: {address}')
        the_confirmation_of_location(update, context)
    else:
        update.message.reply_text('Нам не вдалось обробити ваше місце знаходження')
        from_address(update, context)


def the_confirmation_of_location(update, context):
    reply_markup = markup_keyboard(location_keyboard)
    update.message.reply_text('Оберіть статус посадки', reply_markup=reply_markup)


def from_address(update, context):
    global STATE
    STATE = FROM_ADDRESS
    update.message.reply_text(f'Введіть адресу місця посадки:{STATE}', reply_markup=ReplyKeyboardRemove())


def to_the_address(update, context):
    global STATE
    if STATE == FROM_ADDRESS:
        buttons = [[KeyboardButton(f'{NOT_CORRECT_ADDRESS}')], ]
        address = update.message.text
        addresses = buttons_addresses(update, context, address=address)
        if addresses is not None:
            for key in addresses.keys():
                buttons.append([KeyboardButton(key)])
            reply_markup = ReplyKeyboardMarkup(buttons)
            context.user_data['addresses_first'] = addresses
            update.message.reply_text(choose_address_text, reply_markup=reply_markup)
            STATE = FIRST_ADDRESS_CHECK
        else:
            update.message.reply_text(wrong_address_request)
            from_address(update, context)
    else:
        update.message.reply_text('Введіть адресу місця призначення:', reply_markup=ReplyKeyboardRemove())
        STATE = TO_THE_ADDRESS


def payment_method(update, context):
    global STATE
    if STATE == TO_THE_ADDRESS:
        address = update.message.text
        buttons = [[KeyboardButton(f'{NOT_CORRECT_ADDRESS}')], ]
        addresses = buttons_addresses(update, context, address=address)
        if addresses is not None:
            for key in addresses.keys():
                buttons.append([KeyboardButton(key)])
            reply_markup = ReplyKeyboardMarkup(buttons)
            context.user_data['addresses_second'] = addresses
            update.message.reply_text(
                choose_address_text,
                reply_markup=reply_markup)
            STATE = SECOND_ADDRESS_CHECK
        else:
            update.message.reply_text(wrong_address_request)
            to_the_address(update, context)
    else:
        STATE = None
        markup = markup_keyboard_onetime(payment_keyboard)
        update.message.reply_text('Виберіть спосіб оплати:', reply_markup=markup)


def second_address_check(update, context):
    response = update.message.text
    lst = context.user_data['addresses_second']
    if response not in lst.keys() or response == NOT_CORRECT_ADDRESS:
        to_the_address(update, context)
    else:
        context.user_data['to_the_address'] = response
        payment_method(update, context)


def first_address_check(update, context):
    response = update.message.text
    lst = context.user_data['addresses_first']
    if response not in lst.keys() or response == NOT_CORRECT_ADDRESS:
        from_address(update, context)
    else:
        context.user_data['from_address'] = response
        to_the_address(update, context)


def buttons_addresses(update, context, address):
    center_lat, center_lng = f"{ParkSettings.get_value('CENTRE_CITY_LAT')}", f"{ParkSettings.get_value('CENTRE_CITY_LNG')}"
    center_radius = int(f"{ParkSettings.get_value('CENTRE_CITY_RADIUS')}")
    dict_addresses = get_addresses_by_radius(address, center_lat, center_lng, center_radius, os.environ["GOOGLE_API_KEY"])
    if dict_addresses is not None:
        return dict_addresses
    else:
        return None


def order_create(update, context):
    payment = update.message.text
    user = User.get_by_chat_id(update.message.chat.id)
    context.user_data['phone_number'] = user.phone_number
    destination_place = context.user_data['addresses_second'].get(context.user_data['to_the_address'])
    destination_lat, destination_long = geocode(destination_place, os.environ["GOOGLE_API_KEY"])
    if not context.user_data.get('from_address'):
        context.user_data['from_address'] = context.user_data['location_address']
    else:
        from_place = context.user_data['addresses_first'].get(context.user_data['from_address'])
        context.user_data['latitude'], context.user_data['longitude'] = geocode(from_place, os.environ["GOOGLE_API_KEY"])
    order = Order.objects.filter(chat_id_client=update.message.chat.id, payment_method="",
                                  status_order=Order.ON_TIME).first()
    if order:
        order.from_address = context.user_data['from_address']
        order.latitude = context.user_data['latitude']
        order.longitude = context.user_data['longitude']
        order.to_the_address = context.user_data['to_the_address']
        order.to_latitude = destination_lat
        order.to_longitude = destination_long
        order.phone_number = user.phone_number
        order.payment_method = payment.split()[1]
        order.save()
        update.message.reply_text(f'Замовлення прийняте, очікуйте водія о {timezone.localtime(order.order_time).time()}')
    else:
        Order.objects.create(
            from_address=context.user_data['from_address'],
            latitude=context.user_data['latitude'],
            longitude=context.user_data['longitude'],
            to_the_address=context.user_data['to_the_address'],
            to_latitude=destination_lat,
            to_longitude=destination_long,
            phone_number=user.phone_number,
            chat_id_client=update.message.chat.id,
            payment_method=payment.split()[1],
            status_order=Order.WAITING)


@receiver(post_save, sender=Order)
def send_order_to_driver(sender, instance, **kwargs):
    if instance.status_order == Order.WAITING or not instance.status_order:
        try:
            bot.send_message(chat_id=instance.chat_id_client, text='Шукаємо водія')
        except:
            #     send sms
            pass
        message = f"Отримано нове замовлення:\n" \
                  f"Адреса посадки: {instance.from_address}\n" \
                  f"Місце прибуття: {instance.to_the_address}\n" \
                  f"Спосіб оплати: {instance.payment_method}\n" \
                  f"Номер телефону: {instance.phone_number}\n"

        markup = inline_markup_accept(instance.pk)
        drivers = [i.chat_id for i in Driver.objects.all() if i.driver_status == Driver.ACTIVE]
        # drivers = Driver.objects.filter(driver_status=Driver.ACTIVE).order_by('Fleets_drivers_vehicles_rate__rate')
        if drivers:
            for driver in drivers:
                try:
                    bot.send_message(chat_id=driver, text=message, reply_markup=markup)
                except:
                    pass


def time_order(update, context):
    global STATE
    if STATE == START_TIME_ORDER:
        answer = update.message.text
        context.user_data['time_order'] = answer
    STATE = TIME_ORDER
    update.message.reply_text('Вкажіть, будь ласка, час для подачі таксі(напр. 18:45)', reply_markup=ReplyKeyboardRemove())


def order_on_time(update, context):
    global STATE
    STATE = None
    pattern = r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'
    user_time = update.message.text
    user = User.get_by_chat_id(update.message.chat.id)
    if re.match(pattern, user_time):
        format_time = datetime.datetime.strptime(user_time, '%H:%M').time()
        min_time = timezone.localtime().replace(tzinfo=None) + datetime.timedelta(minutes=int(ParkSettings.get_value('SEND_TIME_ORDER_MIN', 15)))
        conv_time = timezone.datetime.combine(timezone.localtime(), format_time)
        if min_time <= conv_time:
            if context.user_data['time_order'] == TODAY:
                Order.objects.create(chat_id_client=update.message.chat.id,
                                     status_order=Order.ON_TIME,
                                     phone_number=user.phone_number,
                                     order_time=conv_time)
                from_address(update, context)
            else:
                order = Order.get_order(chat_id_client=context.user_data['client_chat_id'],
                                        phone=context.user_data['phone_number'],
                                        status_order=Order.WAITING)
                order.status = Order.ON_TIME
                order.order_time = conv_time
                order.save()
        else:
            update.message.reply_text('Вкажіть, будь ласка, більш пізній час')
            STATE = TIME_ORDER
    else:
        update.message.reply_text('Невірний формат.Вкажіть, будь ласка, час у форматі HH:MM(напр. 18:45)')
        STATE = TIME_ORDER


def send_time_orders(context):
    min_sending_time = timezone.localtime()+datetime.timedelta(minutes=int(ParkSettings.get_value('SEND_TIME_ORDER_MIN', 15)))
    orders = Order.objects.filter(status_order=Order.ON_TIME,
                                  order_time__gte=timezone.localtime(),
                                  order_time__lte=min_sending_time)
    if orders:
        for timeorder in orders:
            message = f"<u>Замовлення на певний час:</u>\n" \
            f"<b>Час подачі:{timezone.localtime(timeorder.order_time).time()}</b>\n" \
            f"Адреса посадки: {timeorder.from_address}\n" \
            f"Місце прибуття: {timeorder.to_the_address}\n" \
            f"Спосіб оплати: {timeorder.payment_method}\n" \
            f"Номер телефону: {timeorder.phone_number}\n"
            drivers = [i.chat_id for i in Driver.objects.all() if i.driver_status == Driver.ACTIVE]
            if drivers:
                for driver in drivers:
                    try:
                        context.bot.send_message(chat_id=driver, text=message,
                                                 reply_markup=inline_markup_accept(timeorder.pk), parse_mode=ParseMode.HTML)
                    except:
                        pass


def handle_callback_order(update, context):
    query = update.callback_query
    data = query.data.split(' ')
    driver = Driver.get_by_chat_id(chat_id=query.message.chat_id)
    if data[0] == "Accept_order":
        order_id = int(data[1])
        order = Order.objects.filter(pk=order_id).first()
        if order:
            record = UseOfCars.objects.filter(user_vehicle=driver, created_at__date=timezone.now().date())
            if record:
                licence_plate = (list(record))[-1].licence_plate
                vehicle = Vehicle.objects.get(licence_plate=licence_plate)
                driver_lat, driver_long = get_location_from_db(vehicle)
                if not order.sum:
                    distance_price = get_route_price(order.latitude, order.longitude,
                                            order.to_latitude, order.to_longitude,
                                            driver_lat, driver_long,
                                            os.environ["GOOGLE_API_KEY"])
                    price = distance_price[1]
                else:
                    price = order.sum

                markup = inline_spot_keyboard(order.pk)
                order.status_order = Order.IN_PROGRESS
                order.driver = driver
                order.sum = price
                order.save()
                ParkStatus.objects.create(driver=driver,
                                          status=Driver.WAIT_FOR_CLIENT)

                message = f"Адреса посадки: {order.from_address}\n" \
                          f"Місце прибуття: {order.to_the_address}\n" \
                          f"Спосіб оплати: {order.payment_method}\n" \
                          f"Номер телефону: {order.phone_number}\n" \
                          f"Загальна вартість: {order.sum}грн"
                query.edit_message_text(text=message)
                query.edit_message_reply_markup(reply_markup=markup)

                report_for_client = f'Ваш водій: {driver}\n' \
                                    f'Назва: {vehicle.name}\n' \
                                    f'Номер машини: {licence_plate}\n' \
                                    f'Номер телефону: {driver.phone_number}\n' \
                                    f'Сума замовлення:{order.sum}грн'
                try:
                    context.bot.send_message(chat_id=order.chat_id_client, text=report_for_client)
                    context.user_data['running'] = True
                    r = threading.Thread(target=send_map_to_client,
                                         args=(update, context, order.chat_id_client, vehicle), daemon=True)
                    r.start()
                except:
                    pass
            else:
                query.edit_message_text(text=select_car_error)
        else:
            query.edit_message_text(text="Це замовлення вже виконується.")

    elif data[0] == 'Reject_order':
        query.edit_message_text(text=f"Ви <<Відмовились від замовлення>>")
        order_id = int(data[1])
        order = Order.objects.filter(pk=order_id).first()
        if order:
            order.status_order = Order.WAITING
            order.save()
            # remove inline keyboard markup from the message
            context.bot.send_message(chat_id=order.chat_id_client,
                text="Водій відхилив замовлення. Пошук іншого водія...")
        else:
            query.edit_message_text(text="Це замовлення вже виконано.")
    elif query.data == "On_the_spot":
        order_id = int(data[1])
        order = Order.objects.filter(pk=order_id).first()
        context.user_data['running'] = False
        context.bot.send_message(chat_id=order.chat_id_client, text='Машину подано. Водій вас очікує')


def send_map_to_client(update, context, client_chat_id, licence_plate):
    # client_chat_id, car_gps_imei = context.args[0], context.args[1]
    latitude, longitude = get_location_from_db(licence_plate)
    context.bot.send_message(chat_id=client_chat_id, text=order_customer_text)
    m = context.bot.sendLocation(client_chat_id, latitude=latitude, longitude=longitude, live_period=600)

    while context.user_data['running']:
        latitude, longitude = get_location_from_db(licence_plate)
        try:
            m = context.bot.editMessageLiveLocation(m.chat_id, m.message_id, latitude=latitude, longitude=longitude)
            print(m)
        except Exception as e:
            logger.error(msg=e.message)
            time.sleep(30)
