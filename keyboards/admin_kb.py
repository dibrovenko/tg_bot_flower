from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
import emoji

b1 = KeyboardButton(f"/Заказы{emoji.emojize(':clipboard:')}")
b2 = KeyboardButton(f"/Аналитика{emoji.emojize(':chart_increasing:')}")
b3 = KeyboardButton("/Добавить_товар")
b4 = KeyboardButton("/Удалить_товар")
b5 = KeyboardButton("/Изменить_товар")

kb_admin = ReplyKeyboardMarkup(resize_keyboard=True)
kb_admin.row(b1, b2).row(b3, b4).add(b5)


b11 = KeyboardButton("/отмена")
b12 = KeyboardButton("/загрузить")

kb_add_admin = ReplyKeyboardMarkup(resize_keyboard=True)
kb_add_admin.row(b11)

kb_load_photo_admin = ReplyKeyboardMarkup(resize_keyboard=True)
kb_load_photo_admin.row(b12, b11)

urlkb_delete_admin = InlineKeyboardMarkup(row_width=1)
utlButton_delete = InlineKeyboardButton(text='delete', callback_data = 'удалить товар')
urlkb_delete_admin.add(utlButton_delete)


# Создаем инлайн-клавиатуру с тремя кнопками для категорий
inline_kb_category_admin = InlineKeyboardMarkup(row_width=1)
in1 = InlineKeyboardButton("Монобукеты", callback_data="Монобукеты")
in2 = InlineKeyboardButton("Авторские букеты", callback_data="Авторские_букеты")
in3 = InlineKeyboardButton("Цветы в коробке", callback_data="Цветы_в_коробке")
inline_kb_category_admin.add(in1, in2, in3)

# Создаем инлайн-клавиатуру с  кнопками для субкатегорий
inline_kb_subcategory_admin = InlineKeyboardMarkup(row_width=2)
subcategory = ["Розы", "Георгины", "Пионы", "Лилии", "Ромашки", "Гипсофилы"]
for i in range(len(subcategory)):
    inline_kb_subcategory_admin.insert(InlineKeyboardButton(subcategory[i], callback_data=subcategory[i]))

# Создаем инлайн-клавиатуру с  кнопками для видимости
inline_visibility_admin = InlineKeyboardMarkup(row_width=2)
visibility = ["Да", "Нет"]
for i in range(len(visibility)):
    inline_visibility_admin.insert(InlineKeyboardButton(visibility[i], callback_data=visibility[i]))