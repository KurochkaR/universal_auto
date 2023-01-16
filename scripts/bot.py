import os
import time
import csv
import datetime
import pendulum
import sys
import redis
import re
import html
import json
import time
import logging
import traceback
from telegram import * 
from telegram.ext import *
from app.models import *
from . import bolt, uklon, uber
from scripts.driversrating import DriversRatingMixin
import traceback
import hashlib
from django.db import IntegrityError

PORT = int(os.environ.get('PORT', '8443'))
DEVELOPER_CHAT_ID = 803129892

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)
logger = logging.getLogger(__name__)

processed_files = []


#Ordering taxi
def start(update, context):
    update.message.reply_text('Привіт! Тебе вітає Універсальне таксі - викликай кнопкою нижче.')
    chat_id = update.message.chat.id
    user = User.get_by_chat_id(chat_id)
    keyboard = [KeyboardButton(text="\U0001f4f2 Надати номер телефону", request_contact=True),
                KeyboardButton(text="\U0001f696 Викликати Таксі", request_location=True),
                KeyboardButton(text="\U0001f465 Надати повну інформацію"),
                KeyboardButton(text="\U0001f4e2 Залишити відгук")]
    if user:
        user.chat_id = chat_id
        user.save()
        if user.phone_number:
           keyboard = [keyboard[1], keyboard[2], keyboard[3]]
        reply_markup = ReplyKeyboardMarkup(
          keyboard=[keyboard],
          resize_keyboard=True,
        )
    else:
        User.objects.create(
            chat_id=chat_id,
            name=update.message.from_user.first_name,
            second_name=update.message.from_user.last_name
        )
        reply_markup = ReplyKeyboardMarkup(
          keyboard=[keyboard],
          resize_keyboard=True,
        )
    update.message.reply_text("Будь ласка розшарьте номер телефону та геолокацію для виклику таксі", reply_markup=reply_markup,)


def update_phone_number(update, context):
    chat_id = update.message.chat.id
    user = User.get_by_chat_id(chat_id)
    phone_number = update.message.contact.phone_number
    if (phone_number and user):
        user.phone_number = phone_number
        user.chat_id = chat_id
        user.save()
        update.message.reply_text('Дякуємо ми отримали ваш номер телефону для звязку з водієм')


LOCATION_WRONG = "Місце посадки - невірне"
LOCATION_CORRECT = "Місце посадки - вірне"


def location(update: Update, context: CallbackContext):
    active_drivers = [i.chat_id for i in Driver.objects.all() if i.driver_status == f'{Driver.ACTIVE}']

    if len(active_drivers) == 0:
        report = update.message.reply_text('Вибачте, але зараз немає вільний водіїв. Скористайтеся послугою пізніше')
        return report
    else:
        if update.edited_message:
            m = update.edited_message
        else:
            m = update.message
        m = context.bot.sendLocation(update.effective_chat.id, latitude=m.location.latitude,
                                     longitude=m.location.longitude, live_period=600)


        context.user_data['latitude'], context.user_data['longitude'] = m.location.latitude, m.location.longitude
        context.user_data['from_address'] = 'Null'
        the_confirmation_of_location(update, context)

        for i in range(1, 10):
            try:
                logger.error(i)
                m = context.bot.editMessageLiveLocation(m.chat_id, m.message_id, latitude=i * 10, longitude=i * 10)
                print(m)
            except Exception as e:
                logger.error(msg=e.message)
                logger.error(i)
            time.sleep(5)


STATE = None
LOCATION, FROM_ADDRESS, TO_THE_ADDRESS, COMMENT, NAME, SECOND_NAME, EMAIL = range(1, 8)


def the_confirmation_of_location(update, context):
    global STATE
    STATE = LOCATION

    keyboard = [KeyboardButton(text=f"\u2705 {LOCATION_CORRECT}"),
                KeyboardButton(text=f"\u274c {LOCATION_WRONG}")]

    reply_markup = ReplyKeyboardMarkup(
        keyboard=[keyboard],
        resize_keyboard=True, )

    update.message.reply_text('Виберіть статус вашої геолокації!', reply_markup=reply_markup)


def from_address(update, context):
    global STATE
    STATE = FROM_ADDRESS
    context.user_data['latitude'], context.user_data['longitude'] = 'Null', 'Null'
    update.message.reply_text('Введіть адресу місця посадки:', reply_markup=ReplyKeyboardRemove())


def to_the_adress(update, context):
    global STATE
    if STATE == FROM_ADDRESS:
        context.user_data['from_address'] = update.message.text
    update.message.reply_text('Введіть адресу місця призначення:', reply_markup=ReplyKeyboardRemove())
    STATE = TO_THE_ADDRESS


def payment_method(update, context):
    global STATE
    STATE = None
    context.user_data['to_the_address'] = update.message.text

    keyboard = [KeyboardButton(text=f"\U0001f4b7 {Order.CASH}"),
                KeyboardButton(text=f"\U0001f4b8 {Order.CARD}")]

    reply_markup = ReplyKeyboardMarkup(
        keyboard=[keyboard],
        resize_keyboard=True, )

    update.message.reply_text('Виберіть спосіб оплати:', reply_markup=reply_markup)


def order_create(update, context):
    WAITING = 'Очікується'

    payment_method = update.message.text
    chat_id = update.message.chat.id
    user = User.get_by_chat_id(chat_id)

    order = Order.objects.create(
        from_address=context.user_data['from_address'],
        latitude=context.user_data['latitude'],
        longitude=context.user_data['longitude'],
        to_the_address=context.user_data['to_the_address'],
        phone_number=user.phone_number,
        chat_id_client=chat_id,
        sum='',
        payment_method=payment_method.split()[1],
        status_order=WAITING)

    order.save()
    update.message.reply_text('Ваша заявка прийнята')


# Changing status of driver
def status(update, context):
    chat_id = update.message.chat.id
    driver = Driver.get_by_chat_id(chat_id)
    if driver is not None:
        buttons = [ [KeyboardButton(Driver.ACTIVE)],
                    [KeyboardButton(Driver.WITH_CLIENT)],
                    [KeyboardButton(Driver.WAIT_FOR_CLIENT)],
                    [KeyboardButton(Driver.OFFLINE)]
                ]

        context.bot.send_message(chat_id=update.effective_chat.id, text='Оберіть статус',
                                 reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True))
    else:
        update.message.reply_text(f'Зареєструйтесь як водій')


def set_status(update, context):
    status = update.message.text
    chat_id = update.message.chat.id
    driver = Driver.get_by_chat_id(chat_id)
    driver.driver_status = status
    driver.save()
    update.message.reply_text(f'Твій статус: <b>{status}</b>', reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)


# Sending comment
def comment(update, context):
    global STATE
    STATE = COMMENT
    update.message.reply_text('Залишіть відгук або сповістіть о проблемі', reply_markup=ReplyKeyboardRemove())


def save_comment(update, context):
    global STATE
    context.user_data['comment'] = update.message.text
    chat_id = update.message.chat.id

    order = Comment.objects.create(
                comment=context.user_data['comment'],
                chat_id=chat_id)
    order.save()

    STATE = None
    update.message.reply_text('Ваш відгук був збережено. Очікуйте, менеджер скоро з вами звяжеться!')


# Getting id for users
def get_id(update, context):
    chat_id = update.message.chat.id
    update.message.reply_text(f"Ваш id: {chat_id}")


# Adding information for Users
def name(update, context):
    global STATE
    STATE = NAME
    update.message.reply_text("Введіть ваше Ім`я:")


def second_name(update, context):
    global STATE
    STATE = SECOND_NAME
    name = update.message.text
    name = User.name_and_second_name_validator(name=name)
    if name is not None:
        context.user_data['name'] = name
        update.message.reply_text("Введіть ваше Прізвище:")
    else:
        update.message.reply_text('Ваше Ім`я занадто довге. Спробуйте ще раз')


def email(update, context):
    global STATE
    STATE = EMAIL
    second_name = update.message.text
    second_name = User.name_and_second_name_validator(name=second_name)
    if second_name is not None:
        context.user_data['second_name'] = second_name
        update.message.reply_text("Введіть вашу електронну адресу:")
    else:
        update.message.reply_text('Ваше Прізвище занадто довге. Спробуйте ще раз')


def update_data_for_user(update, context):
    global STATE
    email = update.message.text
    chat_id = update.message.chat.id
    email = User.email_validator(email=email)
    if email is not None:
        user = User.get_by_chat_id(chat_id)
        user.name, user.second_name, user.email = context.user_data['name'], context.user_data['second_name'], email
        user.save()
        update.message.reply_text('Ваші дані оновлені')
        STATE = None
    else:
        update.message.reply_text('Ваша електронна адреса некоректна. Спробуйте ще раз')


SERVICEABLE = 'Придатна до обслуговування'
BROKEN = 'Зламана'

STATE_D = None
NUMBERPLATE = 1

# Changing status car
def status_car(update, context):
    chat_id = update.message.chat.id
    driver = Driver.get_by_chat_id(chat_id)
    if driver is not None:
        buttons = [[KeyboardButton(f'{SERVICEABLE}')], [KeyboardButton(f'{BROKEN}')]]
        context.bot.send_message(chat_id=chat_id, text='Оберіть статус автомобіля',
                                        reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True))
    else:
        update.message.reply_text(f'Зареєструтесь як водій', reply_markup=ReplyKeyboardRemove())


def numberplate(update, context):
    global STATE_D
    context.user_data['status'] = update.message.text
    update.message.reply_text('Введіть номер автомобіля', reply_markup=ReplyKeyboardRemove())
    STATE_D = NUMBERPLATE

def change_status_car(update, context):
    global STATE_D
    context.user_data['licence_place'] = update.message.text.upper()
    number_car = context.user_data['licence_place']
    numberplates = [i.licence_plate for i in Vehicle.objects.all()]
    if number_car in numberplates:
        vehicle = Vehicle.get_by_numberplate(number_car)
        vehicle.car_status = context.user_data['status']
        vehicle.save()
        numberplates.clear()
        update.message.reply_text('Статус авто був змінений')
    else:
        update.message.reply_text('Цього номера немає в базі даних або надіслано неправильні дані. Зверніться до менеджера або повторіть команду')

    STATE_D = None


# Viewing broken car
def broken_car(update, context):
    chat_id = update.message.chat.id
    driver_manager = DriverManager.get_by_chat_id(chat_id)
    if driver_manager is not None:
        vehicle = Vehicle.objects.filter(car_status=f'{BROKEN}')
        report = ''
        result = [f'{i.licence_plate}' for i in vehicle]
        if len(result) == 0:
            update.message.reply_text("Немає зламаних авто")
        else:
            for i in result:
                report += f'{i}\n'
            update.message.reply_text(f'{report}')
    else:
        update.message.reply_text('Зареєструйтесь як менеджер водіїв')

STATE_DM = None
STATUS = range(1, 2)

# Viewing status driver
def driver_status(update, context):
    global STATE_DM
    chat_id = update.message.chat.id
    driver_manager = DriverManager.get_by_chat_id(chat_id)
    if True:
        buttons = [[KeyboardButton(Driver.ACTIVE)],
                   [KeyboardButton(Driver.WITH_CLIENT)],
                   [KeyboardButton(Driver.WAIT_FOR_CLIENT)],
                   [KeyboardButton(Driver.OFFLINE)]
                   ]
        STATE_DM = STATUS
        context.bot.send_message(chat_id=update.effective_chat.id, text='Оберіть статус',
                                 reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True))
    else:
        update.message.reply_text('Зареєструйтесь як менеджер водіїв')


def viewing_status_driver(update, context):
    global STATE_DM
    status = update.message.text
    driver = Driver.objects.filter(driver_status=status)
    report = ''
    result = [f'{i.name} {i.second_name}: {i.fleet}' for i in driver]
    if len(result) == 0:
        update.message.reply_text('Зараз немає водіїв з таким статусом', reply_markup=ReplyKeyboardRemove())
    else:
        for i in result:
            report += f'{i}\n'
    update.message.reply_text(f'{report}', reply_markup=ReplyKeyboardRemove())
    STATE_DM = None


STATE_SSM = None
LICENCE_PLATE, PHOTO, START_OF_REPAIR, END_OF_REPAIR = range(1, 5)

# Sending report on repair
def numberplate_car(update, context):
    global STATE_SSM
    chat_id = update.message.chat.id
    service_station_manager = ServiceStationManager.get_by_chat_id(chat_id)
    if service_station_manager is not None:
        STATE_SSM = LICENCE_PLATE
        update.message.reply_text('Будь ласка, введіть номерний знак автомобіля')
    else:
        update.message.reply_text('Зареєструйтесь як менеджер сервісного центру')


def photo(update, context):
    global STATE_SSM
    context.user_data['licence_plate'] = update.message.text.upper()
    numberplates = [i.licence_plate for i in Vehicle.objects.all()]
    if context.user_data['licence_plate'] not in numberplates:
        update.message.reply_text('Написаного вами номера немає в базі, зверніться до менеджера парку')
    STATE_SSM = PHOTO
    update.message.reply_text('Будь ласка, надішліть мені фото звіту про ремонт (Одне фото)')


def start_of_repair(update, context):
    global STATE_SSM
    context.user_data['photo'] = update.message.photo[-1].get_file()
    update.message.reply_text('Будь ласка, введіть дату та час початку ремонту у форматі: %Y-%m-%d %H:%M:%S')
    STATE_SSM = START_OF_REPAIR


def end_of_repair(update, context):
    global STATE_SSM
    context.user_data['start_of_repair'] = update.message.text + "+00"
    try:
        time.strptime(context.user_data['start_of_repair'], "%Y-%m-%d %H:%M:%S+00")
    except ValueError:
        update.message.reply_text('Недійсна дата')
    STATE_SSM = END_OF_REPAIR
    update.message.reply_text("Будь ласка, введіть дату та час закінченяя ремонту у форматі: %Y-%m-%d %H:%M:%S")


def send_report_to_db_and_driver(update, context):
    global STATE_SSM
    context.user_data['end_of_repair'] = update.message.text + '+00'
    try:
        time.strptime(context.user_data['end_of_repair'], "%Y-%m-%d %H:%M:%S+00")
    except ValueError:
        update.message.reply_text('Недійсна дата')

    order = RepairReport(
                    repair=context.user_data['photo']["file_path"],
                    numberplate=context.user_data['licence_plate'],
                    start_of_repair=context.user_data['start_of_repair'],
                    end_of_repair=context.user_data['end_of_repair'])
    order.save()
    STATE_SSM = None
    update.message.reply_text('Ваш звіт збережено в базі даних')


def error_handler(update: object, context: CallbackContext) -> None:
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)

    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096 character limit.
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        f'An exception was raised while handling an update\n'
        f'<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}'
        '</pre>\n\n'
        f'<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n'
        f'<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n'
        f'<pre>{html.escape(tb_string)}</pre>'
    )

    # Finally, send the message
    context.bot.send_message(chat_id=DEVELOPER_CHAT_ID, text=message, parse_mode=ParseMode.HTML)


def code(update: Update, context: CallbackContext):
    r = redis.Redis.from_url(os.environ["REDIS_URL"])
    r.publish('code', update.message.text)
    update.message.reply_text('Формування звіту...')
    context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)


def help(update, context) -> str:
    update.message.reply_text('Для першого кроку зробіть реєстрацію або авторизуйтеся командою /start \n' \
                              'Щоб переглянути команди для вашої ролі скористайтесь командою /get_information \n')


STATE_O = None
CARD, SUM = range(1, 3)

TRANSFER_MONEY = 'Перевести кошти'
GENERATE_LINK = 'Сгенерувати лінк'

def payments(update, context):
    #chat_id = update.message.chat.id
    #owner = Owner.get_by_chat_id(chat_id)
    buttons = [[KeyboardButton(f'{TRANSFER_MONEY}')],
               [KeyboardButton(f'{GENERATE_LINK}')]]
    context.bot.send_message(chat_id=update.effective_chat.id, text='Оберіть опцію:',
                             reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True))
    #else:
    #    update.message.reply_text('Ця команда тільки для власника')


def generate_link(update, context):
    pass


def get_card(update, context):
    global STATE_O
    update.message.reply_text('Введіть номер картки отримувача', reply_markup=ReplyKeyboardRemove())
    STATE_O = CARD


def get_sum(update, context):
    global STATE_O
    card = update.message.text
    card = Privat24.card_validator(card=card)
    if card is not None:
        context.user_data['card'] = card
        update.message.reply_text('Введіть суму в форматі DD.CC')
        STATE_O = SUM
    else:
        update.messega.reply_text('Введена карта невалідна')


THE_DATA_IS_CORRECT = "Транзакція заповнена вірно"
THE_DATA_IS_WRONG = "Транзакція заповнена невірно"

def transfer(update, context):
    global STATE_O
    global p

    buttons = [[KeyboardButton(f'{THE_DATA_IS_CORRECT}')],
               [KeyboardButton(f'{THE_DATA_IS_WRONG}')]]

    context.user_data['sum'] = update.message.text

    p = Privat24(card=context.user_data['card'], sum=context.user_data['sum'], driver=True, sleep=7, headless=True)
    p.login()
    p.password()
    p.money_transfer()

    context.bot.send_photo(chat_id=update.effective_chat.id, photo=open('privat_3.png', 'rb'))
    context.bot.send_message(chat_id=update.effective_chat.id, text='Оберіть опцію:',
                             reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True))
    STATE_O = None


def correct_transfer(update, context):
    p.transfer_confirmation()
    update.message.reply_text("Транзакція пройшла успішно")


def wrong_transfer(update, context):
    update.message.reply_text("Транзакція відмінена")
    p.quit()


def get_information(update, context):
    chat_id = update.message.chat.id
    driver_manager = DriverManager.get_by_chat_id(chat_id)
    driver = Driver.get_by_chat_id(chat_id)
    manager = ServiceStationManager.get_by_chat_id(chat_id)
    owner = Owner.get_by_chat_id(chat_id)
    standart_commands = '/start - Щоб зареєструватись та замовити таксі\n' \
                        '/help - Допомога\n' \
                        '/id - Дізнатись id\n'
    if driver is not None:
        report = 'Стандарті команди: \n\n' \
                f'{standart_commands}\n' \
                'Для вашої ролі:\n\n' \
                '/status - Змінити статус водія\n' \
                '/status_car -Змінити статус автомобіля\n'
        update.message.reply_text(f'{report}')
    elif driver_manager is not None:
        report = 'Стандарті команди: \n\n' \
                f'{standart_commands}\n' \
                'Для вашої ролі:\n\n' \
                '/car_status - Показати всі зломлені машини\n' \
                '/driver_status - Показати водіїв за їх статусом\n'
        update.message.reply_text(f'{report}')
    elif manager is not None:
        report = 'Стандарті команди: \n\n' \
                f'{standart_commands}\n' \
                'Для вашої ролі:\n\n' \
                '/send_report - відправити звіт про ремонт\n'
        update.message.reply_text(f'{report}')
    elif owner is not None:
        report = 'Стандарті команди: \n\n' \
                f'{standart_commands}\n' \
                'Для вашої ролі:\n\n' \
                '/report - загрузити та побачити недільні звіти\n' \
                '/rating - побачити рейтинг водіїв\n'
        update.message.reply_text(f'{report}')
    else:
        update.message.reply_text(f'{standart_commands}')


def text(update, context):
    """ STATE - for all users, STATE_D - for drivers, STATE_O - for owner,
            STATE_DM - for driver manager, STATE_SSM - for service station manager"""
    global STATE
    global STATE_O
    global STATE_D
    global STATE_DM
    global STATE_SSM

    if STATE is not None:
        if STATE == FROM_ADDRESS:
            return to_the_adress(update, context)
        elif STATE == TO_THE_ADDRESS:
            return payment_method(update, context)
        elif STATE == COMMENT:
            return save_comment(update, context)
        elif STATE == NAME:
            return second_name(update, context)
        elif STATE == SECOND_NAME:
            return email(update, context)
        elif STATE == EMAIL:
            return update_data_for_user(update, context)
    elif STATE_D is not None:
        if STATE_D == NUMBERPLATE:
            return change_status_car(update, context)
    elif STATE_O is not None:
        if STATE_O == CARD:
            return get_sum(update, context)
        elif STATE_O == SUM:
            return transfer(update, context)
    elif STATE_DM is not None:
        if STATE_DM == STATUS:
            return viewing_status_driver(update, context)
    elif STATE_SSM is not None:
        if STATE_SSM == LICENCE_PLATE:
            return photo(update, context)
        elif STATE_SSM ==PHOTO:
            return start_of_repair(update, context)
        elif STATE_SSM == START_OF_REPAIR:
            return end_of_repair(update, context)
        elif STATE_SSM == END_OF_REPAIR:
            return send_report_to_db_and_driver(update, context)

def drivers_rating(update, context):
    text = 'Рейтинг водіїв\n\n'
    # for fleet in DriversRatingMixin().get_rating():
    #     text += fleet['fleet'] + '\n'
    #     for period in fleet['rating']:
    #         text += f"{period['start']:%d.%m.%Y} - {period['end']:%d.%m.%Y}" + '\n'
    #         if period['rating']:
    #             text += '\n'.join([f"{item['num']} {item['driver']} {item['amount']:15.2f} - {item['trips'] if item['trips']>0 else ''}" for item in period['rating']]) + '\n\n'
    #         else:
    #             text += 'Отримання даних... Спробуйте пізніше\n'
    update.message.reply_text(text)


def report(update, context):
    update.message.reply_text("Введіть ваш Uber OTP код з SMS:")
    update.message.reply_text(get_report())


def cancel(update, context):
    global STATE
    global STATE_D
    global STATE_O
    global STATE_DM
    global STATE_SSM

    STATE, STATE_D, STATE_O, STATE_DM, STATE_SSM = None, None, None, None, None


#Need fix
def update_db(update, context):
    """Pushing data to database from weekly_csv files"""
    # getting and opening files
    directory = '../app'
    files = os.listdir(directory)

    UberPaymentsOrder.download_weekly_report()
    UklonPaymentsOrder.download_weekly_report()
    BoltPaymentsOrder.download_weekly_report()

    files = os.listdir(directory)
    files_csv = filter(lambda x: x.endswith('.csv'), files)
    list_new_files = list(set(files_csv)-set(processed_files))

    if len(list_new_files) == 0:
        update.message.reply_text('No new updates yet')
    else:
        update.message.reply_text('Please wait')
        for name_file in list_new_files:
            processed_files.append(name_file)
            with open(f'{directory}/{name_file}', encoding='utf8') as file:
                if 'Куцко - Income_' in name_file:
                    UklonPaymentsOrder.parse_and_save_weekly_report_to_database(file=file)
                elif '-payments_driver-___.csv' in name_file:
                    UberPaymentsOrder.parse_and_save_weekly_report_to_database(file=file)
                elif 'Kyiv Fleet 03_232 park Universal-auto.csv' in name_file:
                    BoltPaymentsOrder.parse_and_save_weekly_report_to_database(file=file)

        FileNameProcessed.save_filename_to_db(processed_files)
        list_new_files.clear()
        update.message.reply_text('Database updated')


def save_reports(update, context):
    wrf = WeeklyReportFile()
    wrf.save_weekly_reports_to_db()
    update.message.reply_text("Reports have been saved")


def get_owner_today_report(update, context) -> str:
    pass


def get_driver_today_report(update, context) -> str:
    driver_first_name = User.objects.filter(user_id = {update.message.chat.id})
    driver_ident = PaymentsOrder.objects.filter(driver_uuid='')
    if user.type == 0:
        data = PaymentsOrder.objects.filter(transaction_time = date.today(), driver_uuid = {driver_ident} )
        update.message.reply_text(f'Hi {update.message.chat.username} driver')
        update.message.reply_text(text = data)


def get_driver_week_report(update, context) -> str:
    pass


def choice_driver_option(update, context) -> list:
        update.message.reply_text(f'Hi {update.message.chat.username} driver')
        buttons = [[KeyboardButton('Get today statistic')], [KeyboardButton('Choice week number')],[KeyboardButton('Update report')]]
        context.bot.send_message(chat_id=update.effective_chat.id, text='choice option',
        reply_markup=ReplyKeyboardMarkup(buttons))


def get_manager_today_report(update, context) -> str:
    if user.type == 1:
        data = PaymentsOrder.objects.filter(transaction_time = date.today())
        update.message.reply_text(text=data)
    else:
        error_handler()


def get_stat_for_manager(update, context) -> list:
        update.message.reply_text(f'Hi {update.message.chat.username} manager')
        buttons = [[KeyboardButton('Get all today statistic')]]
        context.bot.send_message(chat_id=update.effective_chat.id, text='choice option',
        reply_markup=ReplyKeyboardMarkup(buttons))


def aut_handler(update, context) -> list:
    if 'Get autorizate' in update.message.text:
        if user.type == 0:
            choice_driver_option(update, context)
        elif user.type == 2:
            get_owner_today_report(update, context)
        elif user.type == 1:
            get_stat_for_manager(update, context)
        else:
            update_phone_number()


def get_update_report(update, context):
    user = User.get_by_chat_id(chat_id)
    if user in uklon_drivers_list:
        uklon.run()
        aut_handler(update, context)
    elif username in bolt_drivers_list:
        bolt.run()
        aut_handler(update, context)
    elif username in uber_drivers_list:
        update.message.reply_text("Enter you Uber OTP code from SMS:")
        uber.run()
        aut_handler(update, context)


def main():
    updater = Updater(os.environ['TELEGRAM_TOKEN'], use_context=True)
    dp = updater.dispatcher

    # Command for Owner
    dp.add_handler(CommandHandler("report", report, run_async=True))
    dp.add_handler(CommandHandler("rating", drivers_rating))

    # System commands
    dp.add_handler(CommandHandler("cancel", cancel))
    dp.add_handler(MessageHandler(Filters.regex(r'^\d{4}$'), code))  # this should be at the first place
    dp.add_handler(MessageHandler(Filters.text, text))
    dp.add_error_handler(error_handler)

    # tnansfer money
    dp.add_handler(CommandHandler("payment", payments))
    dp.add_handler(MessageHandler(Filters.text(f"{TRANSFER_MONEY}"), get_card))
    dp.add_handler(MessageHandler(Filters.text(f"{THE_DATA_IS_CORRECT}"), correct_transfer))
    dp.add_handler(MessageHandler(Filters.text(f"{THE_DATA_IS_WRONG}"), wrong_transfer))


    # Publicly available commands
    # Getting id
    dp.add_handler(CommandHandler("id", get_id))
    # Information on commands
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("get_information", get_information))


    # Commands for Users
    # Ordering taxi
    dp.add_handler(CommandHandler("start", start))
    # incomplete auth
    dp.add_handler(MessageHandler(Filters.contact, update_phone_number))
    # ordering taxi
    dp.add_handler(MessageHandler(Filters.location, location, run_async=True))
    dp.add_handler(MessageHandler(Filters.text(f"\u2705 {LOCATION_CORRECT}"), to_the_adress))
    dp.add_handler(MessageHandler(Filters.text(f"\u274c {LOCATION_WRONG}"), from_address))
    dp.add_handler(MessageHandler(
        Filters.text(f"\U0001f4b7 {Order.CASH}") |
        Filters.text(f"\U0001f4b8 {Order.CARD}"),
        order_create))
    # sending comment
    dp.add_handler(MessageHandler(Filters.text("\U0001f4e2 Залишити відгук"), comment))
    # updating information
    dp.add_handler(MessageHandler(Filters.text("\U0001f465 Надати повну інформацію"), name))


    # Commands for Drivers
    # Changing status of driver
    dp.add_handler(CommandHandler("status", status))
    dp.add_handler(MessageHandler(
        Filters.text(Driver.ACTIVE) |
        Filters.text(Driver.WITH_CLIENT) |
        Filters.text(Driver.WAIT_FOR_CLIENT) |
        Filters.text(Driver.OFFLINE),
        set_status))

    # Updating status_car
    dp.add_handler(CommandHandler("status_car", status_car))
    dp.add_handler(MessageHandler(
        Filters.text(f'{SERVICEABLE}') |
        Filters.text(f'{BROKEN}'),
        numberplate))


    # Commands for Driver Managers
    # Returns status cars
    dp.add_handler(CommandHandler("car_status", broken_car))
    # Viewing status driver
    dp.add_handler(CommandHandler("driver_status", driver_status))


    # Commands for Service Station Manager
    # Sending report on repair
    dp.add_handler(CommandHandler("send_report", numberplate_car))

    # need fix
    dp.add_handler(CommandHandler('update', update_db, run_async=True))
    dp.add_handler(CommandHandler("save_reports", save_reports))

    dp.add_handler(MessageHandler(Filters.text('Get all today statistic'), get_manager_today_report))
    dp.add_handler(MessageHandler(Filters.text('Get today statistic'), get_driver_today_report))
    dp.add_handler(MessageHandler(Filters.text('Choice week number'), get_driver_week_report))
    dp.add_handler(MessageHandler(Filters.text('Update report'), get_update_report))

    updater.start_polling()
    updater.idle()


def run():
    main()
