# Create driver and other
from telegram import ReplyKeyboardRemove

from app.models import DriverManager, Vehicle, User, Driver, Fleets_drivers_vehicles_rate, Fleet, NewUklonPaymentsOrder, \
    BoltPaymentsOrder, UberPaymentsOrder, JobApplication
from auto_bot.handlers.driver.static_text import BROKEN
from auto_bot.handlers.driver_job.static_text import JOB_DRIVER
from auto_bot.handlers.driver_manager.keyboards import create_user_keyboard, role_keyboard, fleets_keyboard, \
    fleet_job_keyboard, drivers_status_buttons
from auto_bot.handlers.driver_manager.static_text import *
from auto_bot.handlers.main.keyboards import markup_keyboard, markup_keyboard_onetime
from auto.tasks import send_on_job_application_on_driver


# Add users and vehicle to db and others
def add(update, context):
    chat_id = update.message.chat.id
    driver_manager = DriverManager.get_by_chat_id(chat_id)
    if driver_manager is not None:
        context.user_data['role'] = driver_manager
        update.message.reply_text('Оберіть опцію, кого ви бажаєте створити',
                                  reply_markup=markup_keyboard([create_user_keyboard]))
    else:
        update.message.reply_text(not_manager_text)


def create(update, context):
    update.message.reply_text('Оберіть, якого користувача ви бажаєте створити',
                              reply_markup=markup_keyboard([role_keyboard]))


def name(update, context):
    context.user_data['manager_state'] = NAME
    context.user_data['role'] = update.message.text
    update.message.reply_text("Введіть Ім`я:", reply_markup=ReplyKeyboardRemove())


def second_name(update, context):
    new_name = update.message.text
    new_name = User.name_and_second_name_validator(name=new_name)
    if new_name is not None:
        context.user_data['name'] = new_name
        update.message.reply_text("Введіть Прізвище:")
        context.user_data['manager_state'] = SECOND_NAME
    else:
        update.message.reply_text('Ім`я занадто довге. Спробуйте ще раз')


def email(update, context):
    second_name = update.message.text
    second_name = User.name_and_second_name_validator(name=second_name)
    if second_name is not None:
        context.user_data['second_name'] = second_name
        update.message.reply_text("Введіть електронну адресу:")
        context.user_data['manager_state'] = EMAIL
    else:
        update.message.reply_text('Прізвище занадто довге. Спробуйте ще раз')


def phone_number(update, context):
    email = update.message.text
    email = User.email_validator(email=email)
    if email is not None:
        context.user_data['email'] = email
        update.message.reply_text("Введіть телефонний номер:")
        context.user_data['manager_state'] = PHONE_NUMBER
    else:
        update.message.reply_text('Eлектронна адреса некоректна. Спробуйте ще раз')


def create_user(update, context):
    phone_number = update.message.text
    chat_id = update.message.chat.id
    phone_number = User.phone_number_validator(phone_number=phone_number)
    if phone_number is not None:
        if context.user_data['role'] == USER_DRIVER:
            driver = Driver.objects.create(
                name=context.user_data['name'],
                second_name=context.user_data['second_name'],
                email=context.user_data['email'],
                phone_number=phone_number)

            manager = DriverManager.get_by_chat_id(chat_id)
            manager.driver_id.add(driver.id)
            manager.save()
            update.message.reply_text('Водія було добавленно в базу данних')
        elif context.user_data['role'] == USER_MANAGER_DRIVER:
            DriverManager.objects.create(
                name=context.user_data['name'],
                second_name=context.user_data['second_name'],
                email=context.user_data['email'],
                phone_number=phone_number)

            update.message.reply_text('Менеджера водія було добавленно в базу данних')
        context.user_data['manager_state'] = None
    else:
        update.message.reply_text('Телефонний номер некоректний')


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
        update.message.reply_text(not_manager_text)


# Viewing status driver
def driver_status(update, context):
    chat_id = update.message.chat.id
    driver_manager = DriverManager.get_by_chat_id(chat_id)
    if driver_manager is not None:
        context.user_data['manager_state'] = STATUS
        context.bot.send_message(chat_id=update.effective_chat.id, text='Оберіть статус',
                                 reply_markup=markup_keyboard_onetime(drivers_status_buttons))
    else:
        update.message.reply_text(not_manager_text)


def viewing_status_driver(update, context):
    status = update.message.text
    status = status[2:]
    driver = Driver.objects.filter(driver_status=status)
    report = ''
    result = [f'{i.name} {i.second_name}' for i in driver]
    if len(result) == 0:
        update.message.reply_text('Зараз немає водіїв з таким статусом', reply_markup=ReplyKeyboardRemove())
    else:
        for i in result:
            report += f'{i}\n'
    update.message.reply_text(f'{report}', reply_markup=ReplyKeyboardRemove())
    context.user_data['manager_state'] = None


# Add Vehicle to driver
def get_list_drivers(update, context):
    chat_id = update.message.chat.id
    driver_manager = DriverManager.get_by_chat_id(chat_id)
    if driver_manager is not None:
        drivers = {i.id: f'{i.name } {i.second_name}' for i in Driver.objects.all()}
        if len(drivers) == 0:
            update.message.reply_text('Кількість зареєстрованих водіїв 0')
        else:
            drivers_keys = sorted(drivers)
            drivers = {i: drivers[i] for i in drivers_keys}
            report_list_drivers = ''
            for k, v in drivers.items():
                report_list_drivers += f'{k}: {v}\n'
            update.message.reply_text(f'{report_list_drivers}')
            context.user_data['manager_state'] = DRIVER
            update.message.reply_text('Укажіть номер водія, якому хочете добавити авто.')
    else:
        update.message.reply_text(not_manager_text)


def get_list_vehicle(update, context):
    id_driver = update.message.text
    try:
        id_driver = int(id_driver)
        context.user_data['driver'] = Driver.objects.get(id=id_driver)
    except:
        update.message.reply_text('Не вдалось обробити ваше значення, або переданий номер водія виявився недійсним. Спробуйте ще раз')
    vehicles = {i.id: i.licence_plate for i in Vehicle.objects.all()}
    if len(vehicles) == 0:
        update.message.reply_text('Кількість зареєстрованих траспортних засобів 0')
    else:
        if context.user_data['driver'] is not None:
            report_list_vehicles = ''
            for k, v in vehicles.items():
                report_list_vehicles += f'{k}: {v}\n'
            update.message.reply_text(f'{report_list_vehicles}')
            context.user_data['manager_state'] = CAR_NUMBERPLATE
            update.message.reply_text('Укажіть номер авто, який ви хочете прикріпити до водія')


def get_fleet(update, context):
    id_vehicle = update.message.text
    try:
        id_vehicle = int(id_vehicle)
        context.user_data['vehicle'] = Vehicle.objects.get(id=id_vehicle)
    except:
        update.message.reply_text('Не вдалось обробити ваше значення, або переданий номер автомобільного номера виявився недійсним. Спробуйте ще раз')
    if context.user_data['vehicle'] is not None:

        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='Оберіть автопарк. Для прикріплення автомобіля водію',
                                 reply_markup=markup_keyboard(fleets_keyboard))


def get_driver_external_id(update, context):
    fleet = update.message.text
    context.user_data['fleet'] = fleet
    try:
        response = Fleets_drivers_vehicles_rate.objects.get(
            fleet=Fleet.objects.get(name=fleet),
            driver=context.user_data['driver'],
            vehicle=context.user_data['vehicle'])
        response = str(response)
    except:
        if fleet == F_UKLON:
            try:
                driver = str(context.user_data['driver'])
                driver = driver.split()
                driver = f'{driver[1]} {driver[0]}'
                driver_external_id = NewUklonPaymentsOrder.objects.get(full_name=driver)
                driver_external_id = driver_external_id.signal
            except:
                pass
        elif fleet == F_BOLT:
            try:
                driver_external_id = BoltPaymentsOrder.objects.get(driver_full_name=str(context.user_data['driver']))
                driver_external_id = driver_external_id.mobile_number
            except:
                pass
        else:
            try:
                driver = str(context.user_data['driver'])
                driver = driver.split()
                driver_external_id = UberPaymentsOrder.objects.get(first_name=driver[0], last_name=driver[1])
                driver_external_id = driver_external_id.driver_uuid
            except:
                pass

        try:
            context.user_data['driver_external_id'] = driver_external_id
        except:
            context.user_data['driver_external_id'] = 'pass'

        drivers_rate = {key: round(key * 0.05, 2) for key in range(1, 21)}
        rate = ''
        for k, v in drivers_rate.items():
            rate += f'{k}: {v}\n'

        context.user_data['rate'] = drivers_rate
        update.message.reply_text(f"{rate}",  reply_markup=ReplyKeyboardRemove())
        update.message.reply_text(f"Укажіть номер рейтингу, який ви хочете встановити для {context.user_data['driver']}"
                                  f" в автопарку {context.user_data['fleet']}")
        context.user_data['manager_state'] = RATE
    try:
        if isinstance(response, str):
            update.message.reply_text('Для даного водія вже прикріплене данне авто та автопарк. Спробуйте спочатку')
            context.user_data['manager_state'] = None
    except:
        pass


def add_information_to_driver(update, context):
    id_rate = update.message.text
    try:
        id_rate = int(id_rate)
        rate = context.user_data['rate']
        rate = rate[id_rate]
    except:
        update.message.reply_text('Не вдалось обробити ваше значення, або переданий номер рейтингу не є дійсним. Спробуйте ще раз')
    if isinstance(rate, float):
        Fleets_drivers_vehicles_rate.objects.create(
                fleet=Fleet.objects.get(name=context.user_data['fleet']),
                driver=context.user_data['driver'],
                vehicle=context.user_data['vehicle'],
                driver_external_id=context.user_data['driver_external_id'],
                rate=rate)
        update.message.reply_text(f"Ви добавили водію машину та рейтинг в автопарк {context.user_data['fleet']}")
        if context.user_data['driver_external_id'] == 'pass':
            update.message.reply_text(f"Водія {context.user_data['driver']} збереженно зі значенням driver_external_id = \
                        {context.user_data['driver_external_id']}. Ви можете його змінити власноруч, через панель адміністратора")
        context.user_data['manager_state'] = None


# Push job application to fleets
def get_list_job_application(update, context):
    chat_id = update.message.chat.id
    driver_manager = DriverManager.get_by_chat_id(chat_id)
    if driver_manager is not None:
        applications = {i.id: f'{i}' for i in JobApplication.objects.all() if (i.role == f'{JOB_DRIVER}' and i.status_bolt == False)}
        if len(applications) == 0:
            update.message.reply_text('Заявок на роботу водія поки немає')
        else:
            report_list_applications = ''
            for k, v in applications.items():
                report_list_applications += f'{k}: {v}\n'
            update.message.reply_text(report_list_applications)
            update.message.reply_text('Укажіть номер користувача, заявку якого ви бажаєте відправити')
            context.user_data['manager_state'] = JOB_APPLICATION
    else:
        update.message.reply_text('Зареєструйтесь як менеджер водіїв')


def get_fleet_for_job_application(update, context):
    id_job_application = update.message.text
    try:
        id_job_application = int(id_job_application)
        context.user_data['job_application'] = JobApplication.objects.get(id=id_job_application)

        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='Ви дійсно бажаєте подати заявку?',
                                 reply_markup=markup_keyboard(fleet_job_keyboard))
        context.user_data['manager_state'] = None
    except:
        update.message.reply_text('Не вдалось обробити ваше значення. Спробуйте ще раз')


def add_job_application_to_fleet(update, context):
    data = context.user_data['job_application']
    send_on_job_application_on_driver.delay(data.id)
    update.message.reply_text('Заявки додано в Uklon та Bolt.Користувачу потрібно зареєструватись на сайті Uber як водій')


# Add vehicle to db
def name_vehicle(update, context):
    update.message.reply_text('Введіть назву авто:', reply_markup=ReplyKeyboardRemove())
    context.user_data['manager_state'] = NAME_VEHICLE


def get_name_vehicle(update, context):
    name_vehicle = update.message.text
    name_vehicle = Vehicle.name_validator(name=name_vehicle)
    if name_vehicle is not None:
        context.user_data['name_vehicle'] = name_vehicle
        update.message.reply_text('Введіть модель авто:')
        context.user_data['manager_state'] = MODEL_VEHICLE
    else:
        update.message.reply_text('Назва занадто довга. Спробуйте ще раз')


def get_model_vehicle(update, context):
    model_vehicle = update.message.text
    model_vehicle = Vehicle.model_validator(model=model_vehicle)
    if model_vehicle is not None:
        context.user_data['model_vehicle'] = model_vehicle
        update.message.reply_text('Введіть автомобільний номер:')
        context.user_data['manager_state'] = LICENCE_PLATE_VEHICLE
    else:
        update.message.reply_text('Назва занадто довга. Спробуйте ще раз')


def get_licence_plate_vehicle(update, context):
    licence_plate_vehicle = update.message.text
    licence_plate_vehicle = Vehicle.licence_plate_validator(licence_plate=licence_plate_vehicle)
    if licence_plate_vehicle is not None:
        context.user_data['licence_plate_vehicle'] = licence_plate_vehicle
        update.message.reply_text('Введіть vin_code для машини (максимальна кількість символів 17)')
        context.user_data['manager_state'] = VIN_CODE_VEHICLE
    else:
        update.message.reply_text('Номерний знак занадто довгий. Спробуйте ще раз')


def get_vin_code_vehicle(update, context):
    vin_code = update.message.text
    vin_code = Vehicle.vin_code_validator(vin_code=vin_code)
    if vin_code is not None:
        Vehicle.objects.create(
            name=context.user_data['name_vehicle'],
            model=context.user_data['model_vehicle'],
            licence_plate=context.user_data['licence_plate_vehicle'],
            vin_code=vin_code)
        update.message.reply_text('Машину додано до бази даних')
        context.user_data['manager_state'] = None
    else:
        update.message.reply_text('Vin code занадто довгий. Спробуйте ще раз')


def get_licence_plate_for_gps_imei(update, context):
    chat_id = update.message.chat.id
    driver_manager = DriverManager.get_by_chat_id(chat_id)
    vehicles = {i.id: i.licence_plate for i in Vehicle.objects.all()}
    vehicles = {k: vehicles[k] for k in sorted(vehicles)}
    report_list_vehicles = ''
    if driver_manager is not None:
        if vehicles:
            for k, v in vehicles.items():
                report_list_vehicles += f'{k}: {v}\n'
            update.message.reply_text(f'{report_list_vehicles}')
            update.message.reply_text(f'Укажіть номер машини від 1-{len(vehicles)}, для якого ви бажаєте добавити gps_imei')
            context.user_data['manager_state'] = V_GPS
        else:
            update.message.reply_text("Не здайдено жодного авто у автопарку")
    else:
        update.message.reply_text('Зареєструйтесь як менеджер водіїв')


def get_n_vehicle(update, context):
    id_vehicle = update.message.text
    try:
        id_vehicle = int(id_vehicle)
        context.user_data['vehicle'] = Vehicle.objects.get(id=id_vehicle)
        update.message.reply_text('Введіть gps_imei для данного авто')
        context.user_data['manager_state'] = V_GPS_IMEI
    except:
        update.message.reply_text('Не вдалось обробити ваше значення, або переданий номер автомобільного'
                                  ' номера виявився недійсним. Спробуйте ще раз')


def get_gps_imea(update, context):
    gps_imei = update.message.text
    gps_imei = Vehicle.gps_imei_validator(gps_imei=gps_imei)
    if gps_imei is not None:
        context.user_data['vehicle'].gps_imei = gps_imei
        context.user_data['vehicle'].save()
        update.message.reply_text('Ми встановили GPS imei до авто, яке ви вказали')
        context.user_data['manager_state'] =  None
    else:
        update.message.reply_text("Задовге значення. Спробуйте ще раз")