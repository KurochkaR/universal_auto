from telegram import ParseMode
from telegram.error import BadRequest

from auto_bot.main import bot


def send_long_message(chat_id, text, keyboard=None):
    try:
        bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)
    except BadRequest as e:
        if e.message == 'Message is too long':
            num_parts = (len(text) - 1) // 4090 + 1
            message_parts = [text[i:i + 4090] for i in range(0, len(text), 4090)]
            for i, part in enumerate(message_parts):
                text_message = bot.send_message(chat_id=chat_id, text=f"{i + 1}/{num_parts}:\n{part}",
                                                parse_mode=ParseMode.HTML)
            if keyboard:
                bot.edit_message_reply_markup(chat_id=chat_id, message_id=text_message.message_id, reply_markup=keyboard)
        else:
            pass
