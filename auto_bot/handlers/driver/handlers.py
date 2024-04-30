from datetime import datetime, timedelta
from django.utils import timezone
from telegram import ReplyKeyboardRemove, InlineKeyboardMarkup, ParseMode
from telegram.ext import ConversationHandler

from app.models import Driver, Vehicle, ReportDriveDebt, Event, DriverPayments
from auto.tasks import add_screen_to_payment, generate_rent_message_driver
from auto_bot.handlers.driver.keyboards import service_auto_buttons, inline_debt_keyboard, inline_dates_kb, \
    back_to_payment, detail_payment_kb, detail_payment_buttons
from auto_bot.handlers.driver.static_text import *
from auto_bot.handlers.driver.utils import generate_detailed_info, generate_detailed_bonus
from auto_bot.handlers.driver_job.utils import save_storage_photo
from auto_bot.handlers.driver_manager.static_text import waiting_task_text
from auto_bot.handlers.driver_manager.utils import message_driver_report
from auto_bot.handlers.main.keyboards import markup_keyboard_onetime, back_to_main_menu
from auto_bot.utils import edit_long_message
from scripts.redis_conn import redis_instance


def bolt_report_photo_callback(update, context):
    query = update.callback_query
    chat_id = update.effective_chat.id
    context.bot.send_photo(
        chat_id=chat_id,
        photo='https://storage.googleapis.com/jobdriver-bucket/docs/bolt_screen.jpeg',
        caption=f"Надішліть, будь ласка, фото поточного звіту Bolt, як вказано на фото вище."
                f"Якщо виконуєте замовлення надішліть звіт після його завершення"
    )

    context.bot.delete_message(chat_id=chat_id, message_id=query.message.message_id)
    redis_instance().hset(str(chat_id), 'photo_state', BOLT_REPORT_PHOTO)


def upload_bolt_report_photo(update, context):
    chat_id = str(update.effective_chat.id)
    driver = Driver.get_by_chat_id(chat_id)
    if update.message.photo:
        redis_instance().hdel(chat_id, 'photo_state')
        image = update.message.photo[-1].get_file()
        filename = f'bolt/reports/{image["file_unique_id"]}.jpg'
        save_storage_photo(image, filename)
        add_screen_to_payment.apply_async(args=[filename, driver.pk])
        update.message.reply_text("Дякую дані збережено для розрахунку виплати")
    else:
        update.message.reply_text("Будь ласка, надішліть знімок екрану з поточним звітом")
        redis_instance().hset(str(chat_id), 'photo_state', BOLT_REPORT_PHOTO)


def detailed_payment_info(update, context):
    query = update.callback_query
    payment_id = query.data.split()[1]
    query.edit_message_reply_markup(detail_payment_buttons(payment_id))


def detailed_payment_kasa(update, context):
    query = update.callback_query
    payment_id = query.data.split()[1]
    detailed_info = generate_detailed_info(payment_id)
    if detailed_info:
        edit_long_message(query.from_user.id, detailed_info, query.message.message_id, back_to_payment(payment_id))
    else:
        query.edit_message_text(no_payment_text)


def detailed_payment_rent(update, context):
    query = update.callback_query
    payment_id = query.data.split()[1]
    payment_obj = DriverPayments.objects.get(pk=payment_id)
    query.edit_message_text(waiting_task_text)
    generate_rent_message_driver.apply_async(args=[payment_obj.driver_id, query.from_user.id,
                                                   query.message.message_id, payment_id])
    query.edit_message_reply_markup(back_to_payment(payment_id))


def detailed_payment_bonus(update, context):
    query = update.callback_query
    payment_id = query.data.split()[1]
    detailed_bonus_text = generate_detailed_bonus(payment_id)
    if detailed_bonus_text:
        query.edit_message_text(detailed_bonus_text)
        query.edit_message_reply_markup(back_to_payment(payment_id))
    else:
        query.edit_message_text(no_payment_text)


def back_to_payment_info(update, context):
    query = update.callback_query
    payment_id = query.data.split()[1]
    payment_obj = DriverPayments.objects.get(pk=payment_id)
    payment_text = message_driver_report(payment_obj)
    context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=query.message.message_id,
                             text=payment_text, reply_markup=detail_payment_kb(payment_id), parse_mode=ParseMode.HTML)


def status_car(update, context):
    chat_id = update.message.chat.id
    driver = Driver.get_by_chat_id(chat_id)
    if driver is not None:

        context.bot.send_message(chat_id=update.effective_chat.id, text='Оберіть статус автомобіля',
                                 reply_markup=markup_keyboard_onetime([service_auto_buttons]))
    else:
        update.message.reply_text(not_driver_text, reply_markup=ReplyKeyboardRemove())


def numberplate(update, context):
    context.user_data['status'] = update.message.text
    update.message.reply_text('Введіть номер автомобіля', reply_markup=ReplyKeyboardRemove())
    context.user_data['driver_state'] = NUMBERPLATE


def change_status_car(update, context):
    context.user_data['licence_place'] = update.message.text.upper()
    number_car = context.user_data['licence_place']
    numberplates = [i.licence_plate for i in Vehicle.objects.all()]
    if number_car in numberplates:
        vehicle = Vehicle.objects.get(licence_plate=number_car)
        vehicle.car_status = context.user_data['status']
        vehicle.save()
        numberplates.clear()
        update.message.reply_text('Статус авто був змінений')
    else:
        update.message.reply_text(
            'Цього номера немає в базі даних або надіслано неправильні дані.'
            ' Зверніться до менеджера або повторіть команду')
    context.user_data['driver_state'] = None


# Sending report for drivers(payment debt)
def sending_report(update, context):
    chat_id = update.message.chat.id
    driver = Driver.get_by_chat_id(chat_id)
    if driver is not None:
        context.bot.send_message(chat_id=update.effective_chat.id, text='Оберіть опцію:',
                                 reply_markup=inline_debt_keyboard())
        return "WAIT_FOR_DEBT_OPTION"
    else:
        update.message.reply_text(not_driver_text, reply_markup=ReplyKeyboardRemove())


def get_debt_photo(update, context):
    empty_keyboard = InlineKeyboardMarkup([])
    update.callback_query.answer()
    update.callback_query.edit_message_text(text='Надішліть фото оплати заборгованості', reply_markup=empty_keyboard)
    return 'WAIT_FOR_DEBT_PHOTO'


def save_debt_report(update, context):
    chat_id = update.message.chat.id
    driver = Driver.get_by_chat_id(chat_id)
    if update.message.photo:
        image = update.message.photo[-1].get_file()
        filename = f'{image.file_unique_id}.jpg'
        image.download(filename)
        ReportDriveDebt.objects.create(
            driver=driver,
            image=f'static/{filename}'
        )
        update.message.reply_text(text='Ваш звіт збережено')
        return ConversationHandler.END
    else:
        update.message.reply_text('Будь ласка, надішліть фото', reply_markup=ReplyKeyboardRemove())
        return 'WAIT_FOR_DEBT_PHOTO'


def choose_day_off_or_sick(update, context):
    query = update.callback_query
    data = query.data.split()[0]
    if data == "Off":
        day = timezone.localtime() + timedelta(days=2)
    else:
        day = timezone.localtime()
    query.edit_message_text(select_off_text)
    query.edit_message_reply_markup(inline_dates_kb(data, day, 'More_driver'))


def take_a_day_off_or_sick_leave(update, context):
    query = update.callback_query
    event_str, date_str = query.data.split()
    event = Event.DAY_OFF if event_str == "Off" else Event.SICK_DAY
    driver = Driver.get_by_chat_id(update.effective_chat.id)
    selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    result = f"Водій {driver} взяв {event} на {selected_date}"
    Event.objects.create(
        full_name_driver=driver,
        event=event,
        event_date=selected_date,
        chat_id=driver.chat_id)
    query.edit_message_text(text=f'Ви взяли {event} на {selected_date}.')
    query.edit_message_reply_markup(reply_markup=back_to_main_menu())
    context.bot.send_message(chat_id=driver.manager.chat_id, text=result)
