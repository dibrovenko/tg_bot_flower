from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, \
    InlineKeyboardButton

b1 = KeyboardButton(f"/Купить")
b2 = KeyboardButton('/поддержка')
b3 = KeyboardButton('/Меню')
b4 = KeyboardButton('Поделиться номером', request_contact=True)
b5 = KeyboardButton('Отправить где я', request_location=True)

kb_client = ReplyKeyboardMarkup(resize_keyboard=True)
kb_client.add(b1).add(b2).insert(b3)



bb1 = KeyboardButton(f"отмена ✕")
bb2 = KeyboardButton('назад ⤴')

kb_client_registration = ReplyKeyboardMarkup(resize_keyboard=True)
kb_client_registration.row(bb1, bb2)


a1 = KeyboardButton(f"отмена ✕")
a2 = KeyboardButton('назад ⤴')
a3 = KeyboardButton('Поделиться номером', request_contact=True)

kb_client_registration_name = ReplyKeyboardMarkup(resize_keyboard=True)
kb_client_registration_name.add(a3).row(a1, a2)


c1 = KeyboardButton(f"отмена ✕")
c2 = KeyboardButton('назад ⤴')
c3 = KeyboardButton('Пропустить')

kb_client_registration_comment = ReplyKeyboardMarkup(resize_keyboard=True)
kb_client_registration_comment.add(c3).row(c1, c2)

kb_client_pay_inline = InlineKeyboardMarkup(row_width=1).\
    add(InlineKeyboardButton(text='Oплатить', pay=True)).\
    add(InlineKeyboardButton(text='отмена', callback_data='stop_pay'))


kb_client_order_inline = InlineKeyboardMarkup(row_width=1).\
    row(InlineKeyboardButton(text='редактировать', callback_data='edit'),
        InlineKeyboardButton(text='отмена', callback_data='stop'))

d1 = KeyboardButton(f"отмена ✕")

kb_client_registration_start = ReplyKeyboardMarkup(resize_keyboard=True)
kb_client_registration_start.add(d1)