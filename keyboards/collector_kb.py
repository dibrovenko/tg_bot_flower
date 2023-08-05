from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, \
    InlineKeyboardButton

b1 = KeyboardButton(f"Сегодня")
b2 = KeyboardButton('Завтра')
b3 = KeyboardButton('Последние 5 заказов')

kb_collector = ReplyKeyboardMarkup(resize_keyboard=True)
kb_collector.add(b1).add(b2).insert(b3)