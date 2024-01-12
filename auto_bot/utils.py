from telegram.error import BadRequest

from auto_bot.main import bot


def send_long_message(chat_id, text, keyboard=None):
    try:
        print(len(text))
        num_parts = (len(text) - 1) // 4090 + 1
        message_parts = [text[i:i + 4090] for i in range(0, len(text), 4090)]
        for i, part in enumerate(message_parts):
            text = bot.send_message(chat_id=chat_id, text=f"{i + 1}/{num_parts}:\n{part}")
        bot.edit_message_reply_markup(chat_id=chat_id, message_id=text.id, reply_markup=keyboard)
    except BadRequest:
        pass
