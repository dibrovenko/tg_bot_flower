from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, \
    InlineKeyboardButton

b1 = KeyboardButton(f"Сегодня")
b2 = KeyboardButton('Завтра')
b3 = KeyboardButton('Найти заказ 🔎')
b4 = KeyboardButton('Последние 5')

kb_collector = ReplyKeyboardMarkup(resize_keyboard=True)
kb_collector.add(b1).insert(b2).add(b3).insert(b4)

