from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
import emoji

b1 = KeyboardButton(f"/Купить")
b2 = KeyboardButton('/поддержка')
b3 = KeyboardButton('/Меню')
b4 = KeyboardButton('Поделиться номером', request_contact=True)
b5 = KeyboardButton('Отправить где я', request_location=True)

kb_client = ReplyKeyboardMarkup(resize_keyboard=True)
kb_client.add(b1).add(b2).insert(b3)



bb1 = KeyboardButton(f"Отмена")
bb2 = KeyboardButton('Назад')

kb_client_registration = ReplyKeyboardMarkup(resize_keyboard=True)
kb_client_registration.row(bb1, bb2)


a1 = KeyboardButton(f"Отмена")
a2 = KeyboardButton('Назад')
a3 = KeyboardButton('Поделиться номером', request_contact=True)

kb_client_registration_name = ReplyKeyboardMarkup(resize_keyboard=True)
kb_client_registration_name.add(a3).row(a1, a2)

