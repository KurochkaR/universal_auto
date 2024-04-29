from datetime import timedelta

from telegram import KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup

from auto_bot.handlers.driver.static_text import *
from auto_bot.handlers.main.keyboards import main
from auto_bot.handlers.order.static_text import order_inline_buttons

service_auto_buttons = [KeyboardButton(f'{SERVICEABLE}'), KeyboardButton(f'{BROKEN}')]


def detail_payment_kb(pk):
    keyboard = [
        [InlineKeyboardButton(detailed_text, callback_data=f"Detail_payment {pk}")]
    ]
    return InlineKeyboardMarkup(keyboard)


def detail_payment_buttons(pk):
    keyboard = [
        [InlineKeyboardButton(detailed_kasa, callback_data=f"Detail_payment_kasa {pk}")],
        [InlineKeyboardButton(detailed_rent, callback_data=f"Detail_payment_rent {pk}")],
        [InlineKeyboardButton(detailed_bonus, callback_data=f"Detail_bonus_penalty {pk}")]
    ]
    return InlineKeyboardMarkup(keyboard)


def back_to_payment(pk):
    keyboard = [
        [InlineKeyboardButton(back_to_payment_text, callback_data=f"Payment_info {pk}")]
    ]
    return InlineKeyboardMarkup(keyboard)

def inline_debt_keyboard():
    debt_buttons = [[InlineKeyboardButton(text=f'{SEND_REPORT_DEBT}', callback_data='photo_debt')]]
    return InlineKeyboardMarkup(debt_buttons)


def inline_bolt_report_keyboard():
    report_buttons = [[InlineKeyboardButton(text=f'{SEND_BOLT_REPORT}', callback_data='photo_bolt_report')]]
    return InlineKeyboardMarkup(report_buttons)


def inline_dates_kb(event, day, back_step):
    dates = []
    start_date = day
    for i in range(7):
        dates.append([InlineKeyboardButton(text=f'{start_date.strftime("%d.%m")}',
                                           callback_data=f'{event} {start_date.strftime("%Y-%m-%d")}')])
        start_date += timedelta(days=1)

    dates.append([InlineKeyboardButton(order_inline_buttons[6], callback_data=back_step)],)
    dates.append(main)

    return InlineKeyboardMarkup(dates)
