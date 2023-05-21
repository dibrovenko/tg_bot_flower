from aiogram.dispatcher import FSMContext, filters
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram import types, Dispatcher
from create_bot import bot
from keyboards import kb_admin, kb_add_admin, kb_load_photo_admin, \
    inline_kb_category_admin, inline_kb_subcategory_admin, subcategory, \
    inline_visibility_admin
from data_base import sqlite_dp
from data_base.sqlite_dp import sql_read_name_english, sql_get_name, sql_del,sql_update_data, exel_upload
from handlers.other import set_admin_dell_commands, check_valid_text, set_admin_commands

import re



# Обработчик команды /export_data
#@dp.message_handler(commands=['export_data'])
async def process_export_data_command(message: types.Message):
    await exel_upload(message)


class FSMAdmin(StatesGroup):
    photo = State()
    name = State()
    name_english = State()
    category = State()
    subcategory = State()
    description = State()
    quantity1 = State()
    quantity2 = State()
    quantity3 = State()
    visibility = State()
    price = State()

    show_delete = State()
    delete = State()

    show_change = State()
    change = State()
    change_end = State()




#Выход из состояний
#@dp.message_handler(state="*", commands='отмена')
#@dp.message_handler(filters.Text(equals='отмена', ignore_case=True), state="*")
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    elif current_state == FSMAdmin.show_delete.state:
        await state.finish()
        await message.reply('Хорошо, изменения не будут сохранены', reply_markup=kb_admin)
        await set_admin_commands(message)
        return
    await state.finish()
    await message.reply('OK', reply_markup=kb_admin)
    await set_admin_commands(message)


#Начало диалога загрузки нового пункта меню
#@dp.message_handler(commands='/Добавить_товар', state=None)
async def cm_start(message : types.Message, state: FSMContext):
    await FSMAdmin.photo.set()
    async with state.proxy() as data:
        data['photo'] = list()
    await message.reply('Загрузи фото', reply_markup=kb_add_admin)


#Выход из состояний загрузки фото
#@dp.message_handler(state=FSMAdmin.photo, commands='загрузить')
async def stop_load_photo(message: types.Message, state: FSMContext):
    await FSMAdmin.name.set()
    await bot.send_message(message.from_user.id, "Теперь введи название",
                           reply_markup=kb_add_admin)


#Ловим первый ответ и пишем в словарь
#@dp.message_handler(content_types=['photo'], state=FSMAdmin.photo)
async def load_photo(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['photo'].append(message.photo[0].file_id)

    current_state = await state.get_state()
    if current_state == FSMAdmin.photo.state:
        await bot.send_message(message.from_user.id, "Отправь еще фото, либо нажми /загрузить ", reply_markup=kb_load_photo_admin)
    else:
        await FSMAdmin.name.set()
        await message.reply("Теперь введи название")


#Ловим второй ответ на имя
#@dp.message_handler(state=FSMAdmin.name)
async def load_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
    await FSMAdmin.name_english.set()
    await message.answer('Введите имя на английском строчными буквы.\nC помощью этого названия будет осуществляться поиск.\nМежду словами должен быть не пробел, а "_"\nВот пример: rose_red_15sm', reply_markup=kb_add_admin)


#Ловим второй ответ на имя
#@dp.message_handler(state=FSMAdmin.name_english)
async def load_english_name(message: types.Message, state: FSMContext):
    if check_valid_text(message.text):
        async with state.proxy() as data:
            data['name_english'] = message.text
        await FSMAdmin.category.set()
        await message.answer('Выберите категорию:', reply_markup=inline_kb_category_admin)
    else:
        await message.answer('Введите в правильном формате, название содержит неверные символы')


# Обработчик нажатий на кнопки категорий
#@dp.callback_query_handler(lambda c: c.data in ["Монобукеты", "Авторские_букеты", "Цветы_в_коробке"], state=FSMAdmin.category)
async def load_category(callback: types.CallbackQuery, state: FSMContext):
    # Если нажата первая кнопка, открываем подкатегорию
    if callback.data == "Монобукеты":
        async with state.proxy() as data:
            data['category'] = callback.data
        await FSMAdmin.subcategory.set()
        await callback.message.answer("вы выбрали Монобукеты.\n\nТеперь добавьте подкатегорию:", reply_markup=inline_kb_subcategory_admin)
        await callback.answer()
    # Если нажата вторая или третья кнопка, то субкатегория не нужна
    else:
        async with state.proxy() as data:
            data['category'] = callback.data
            data['subcategory'] = None
        await FSMAdmin.description.set()
        await callback.message.answer(text=f"вы выбрали {callback.data}.\n\nВведи описание")
        await callback.answer()


# Обработчик нажатий на кнопки ПОДкатегорий
#@dp.callback_query_handler(lambda c: c.data in subcategory, state=FSMAdmin.subcategory)
async def load_subcategory(callback: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data['subcategory'] = callback.data
    await FSMAdmin.description.set()
    await callback.message.answer(text=f"вы выбрали {callback.data}.\n\nВведи описание")
    await callback.answer()


#Ловим пятый ответ на описание
#@dp.message_handler(state=FSMAdmin.description)
async def load_description(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['description'] = message.text
    await FSMAdmin.quantity1.set()
    await message.answer('Теперь укажи количество на Калужском шоссе')


#Ловим ответ на количество на Калужском шоссе
#@dp.message_handler(state=FSMAdmin.quantity1)
async def load_quantity1(message: types.Message, state: FSMContext):
        try:
            async with state.proxy() as data:
                data['quantity1'] = int(message.text)
            await FSMAdmin.quantity2.set()
            await message.answer('Укажи количество на Маяковском переулке')
        except ValueError:
            await message.reply(f"Ошибка: {message.text} не является целым числом.\nЖду целое число")


#Ловим ответ на количество на Маяковском переулке
#@dp.message_handler(state=FSMAdmin.quantity2)
async def load_quantity2(message: types.Message, state: FSMContext):
        try:
            async with state.proxy() as data:
                data['quantity2'] = int(message.text)
            await FSMAdmin.quantity3.set()
            await message.answer('Укажи количество на улице Смольная')
        except ValueError:
            await message.reply(f"Ошибка: {message.text} не является целым числом.\nЖду целое число")


#Ловим ответ на количество на улице Смольная
#@dp.message_handler(state=FSMAdmin.quantity3)
async def load_quantity3(message: types.Message, state: FSMContext):
        try:
            async with state.proxy() as data:
                data['quantity3'] = int(message.text)
            await FSMAdmin.visibility.set()
            await message.answer('Теперь укажи видимость для пользователя', reply_markup=inline_visibility_admin)
        except ValueError:
            await message.reply(f"Ошибка: {message.text} не является целым числом.\nЖду целое число")


#Ловим ответ на видимость
#@dp.callback_query_handler(lambda c: c.data in ["Да", "Нет"], state=FSMAdmin.visibility)
async def load_visibility(callback: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data['visibility'] = callback.data
    await FSMAdmin.price.set()
    await callback.message.answer(text=f"вы выбрали '{callback.data}'\n\nТеперь укажи цену за одну штуку")
    await callback.answer()


#Ловим последний ответ и используем полученные данные
#@dp.message_handler(state=FSMAdmin.price)
async def load_price(message: types.Message, state: FSMContext):
        try:
            async with state.proxy() as data:
                data['price'] = float(message.text)
            async with state.proxy() as data:
                await message.reply(str(data), reply_markup=kb_admin)
            await sqlite_dp.sql_add_command(state)
            await state.finish()

        except ValueError:
            await message.reply(f"Ошибка: {message.text} не является числом.\nЖду числа")


#Начало диалога удаления  пункта меню
#@dp.message_handler(commands='/Удалить_товар', state=None)
async def cm_start_delete(message: types.Message):
    await FSMAdmin.show_delete.set()
    await message.reply('через / выберите товар', reply_markup=kb_add_admin)
    await set_admin_dell_commands(message)


#Показываем выбор удаления
#@dp.message_handler(state=FSMAdmin.show_delete)
async def cm_show_delete(message: types.Message):
    if message.text[1:] in await sql_read_name_english():
        await FSMAdmin.delete.set()
        await set_admin_commands(message)
        lst = await sql_get_name(message.text[1:], message)
        for ret in lst:
            caption = f'*{ret[1]}*\n_English_: *{ret[2]}*\n_Категория:_ *{ret[3]}*\n_Подкатегория:_ *{ret[4]}*\n_Описание:_ *{ret[5]}*' \
                      f'\n_Количество на Калужском:_ *{ret[6]}*\n_Количество на Маяковском:_ *{ret[7]}*\n_Количество на Смольной:_ *{ret[8]}*' \
                      f'\n_Видимость:_ *{ret[9]}*\n_Цена_ *{ret[-1]}*'
            album = types.MediaGroup()
            matches = re.findall(r"'(.*?)'", ret[0])
            for i, match in enumerate(matches):
                if i == len(matches)-1:
                    album.attach_photo(photo=match, caption=caption, parse_mode="Markdown")
                else:
                    album.attach_photo(photo=match)
            await message.answer_media_group(media=album)
            await message.answer(text="**************", reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton(f'удалить {ret[1]}', callback_data=f"del {ret[1]}")))
    else:
        await set_admin_commands(message)


#Ловим ответ  удаляем данные
#@dp.callback_query_handler(lambda x: x.data and x.data.startswith('del '), state=FSMAdmin.delete)
async def cm_delete(callback_query: types.CallbackQuery, state: FSMContext):
    await sql_del(callback_query.data.replace('del ', ''))
    await callback_query.answer(text=f"{callback_query.data.replace('del ', '')} удален.", show_alert=True)
    await state.finish()
    await callback_query.message.answer('вы вернулись в админскую панель!', reply_markup=kb_admin)


#Начало диалога изменеия  пункта меню
#@dp.message_handler(commands='/Изменить_товар', state=None)
async def cm_start_change(message: types.Message):
    await FSMAdmin.show_change.set()
    await message.reply('через / выберите товар', reply_markup=kb_add_admin)
    await set_admin_dell_commands(message)


#Показываем выбор изменения
#@dp.message_handler(state=FSMAdmin.show_change)
async def cm_show_change(message: types.Message, state: FSMContext):
    if message.text[1:] in await sql_read_name_english():
        await set_admin_commands(message)
        await FSMAdmin.change.set()
        async with state.proxy() as data:
            data['name_change'] = message.text[1:]
        lst = await sql_get_name(message.text[1:], message)
        for ret in lst:
            caption = f'*{ret[1]}*\n_English_: *{ret[2]}*\n_Категория:_ *{ret[3]}*\n_Подкатегория:_ *{ret[4]}*\n_Описание:_ *{ret[5]}*' \
                      f'\n_Количество на Калужском:_ *{ret[6]}*\n_Количество на Маяковском:_ *{ret[7]}*\n_Количество на Смольной:_ *{ret[8]}*' \
                      f'\n_Видимость:_ *{ret[9]}*\n_Цена_ *{ret[-1]}*'

            async with state.proxy() as data:
                data['visibility'] = ret[9]

            album = types.MediaGroup()
            matches = re.findall(r"'(.*?)'", ret[0])
            for i, match in enumerate(matches):
                if i == len(matches)-1:
                    album.attach_photo(photo=match, caption=caption, parse_mode="Markdown")
                else:
                    album.attach_photo(photo=match)
            await message.answer_media_group(media=album)
            await message.answer(text="Что изменить?", reply_markup=InlineKeyboardMarkup().
                                 insert(InlineKeyboardButton(f'Видимость', callback_data=f"visibility {ret[1]}")).
                                 insert(InlineKeyboardButton(f'Цену', callback_data=f"price {ret[1]}")).
                                 add(InlineKeyboardButton(f'Количество на Калужском', callback_data=f"quantity1 {ret[1]}")).
                                 add(InlineKeyboardButton(f'Кол. на Маяковском', callback_data=f"quantity2 {ret[1]}")).
                                 insert(InlineKeyboardButton(f'Кол. на Смольной', callback_data=f"quantity3 {ret[1]}")))
    else:
        return


#Ловим ответ какую строчку поменять
#@dp.callback_query_handler(lambda x: x.data and (x.data.startswith('visibility ') or x.data.startswith('quantity') or x.data.startswith('price ')), state=FSMAdmin.change)
async def cm_change(callback_query: types.CallbackQuery, state: FSMContext):
    #await set_admin_commands()
    column_name = callback_query.data.split()[0]
    async with state.proxy() as data:
        data['column_name'] = column_name
    match column_name:
        case 'visibility':
            async with state.proxy() as data:

                if data['visibility'] == 'Да':
                    await sql_update_data(name=data['name_change'], column_name=data['column_name'], new_value='Нет')
                else:
                    await sql_update_data(name=data['name_change'], column_name=data['column_name'], new_value='Да')

            await callback_query.message.answer(text="Видиость изменена", reply_markup=kb_admin)
            await callback_query.answer()
            await state.finish()

        case 'quantity1' | 'quantity2' | 'quantity3':
            await callback_query.message.answer(text="Теперь укажи новое количество")
            await callback_query.answer()
            await FSMAdmin.change_end.set()

        case 'price':
            await callback_query.message.answer(text="Теперь укажи новую цену за одну штуку")
            await callback_query.answer()
            await FSMAdmin.change_end.set()


#Ловим ответ и меняем данные
#@dp.message_handler(state=FSMAdmin.change_end)
async def cm_change_end(message: types.Message, state: FSMContext):
    try:
        async with state.proxy() as data:
            column_name = data['column_name']
            match column_name:
                case 'quantity1' | 'quantity2' | 'quantity3':
                    int(message.text)
                case 'price':
                    float(message.text)
            await sql_update_data(name=data['name_change'], column_name=data['column_name'], new_value=message.text)
            await state.finish()
            await message.answer('вы вернулись в админскую панель!', reply_markup=kb_admin)
    except ValueError:
        await message.reply('не верный формат ввода, введи еще раз')




#Регистрируем хендлеры
def register_handlers_clients(dp: Dispatcher):
    dp.register_message_handler(cm_start, commands='Добавить_товар', state=None)
    dp.register_message_handler(cancel_handler, state="*", commands='отмена')
    dp.register_message_handler(cancel_handler, filters.Text(equals='отмена', ignore_case=True), state="*")
    dp.register_message_handler(stop_load_photo, state=FSMAdmin.photo, commands='загрузить')
    dp.register_message_handler(load_photo, content_types=['photo'], state=FSMAdmin.photo)
    dp.register_message_handler(load_name, state=FSMAdmin.name)
    dp.register_message_handler(load_english_name, state=FSMAdmin.name_english)
    dp.register_callback_query_handler(load_category, lambda c: c.data in ["Монобукеты", "Авторские_букеты", "Цветы_в_коробке"],
                                       state=FSMAdmin.category)
    dp.register_callback_query_handler(load_subcategory, lambda c: c.data in subcategory,
                                       state=FSMAdmin.subcategory)
    dp.register_message_handler(load_description, state=FSMAdmin.description)
    dp.register_message_handler(load_quantity1, state=FSMAdmin.quantity1)
    dp.register_message_handler(load_quantity2, state=FSMAdmin.quantity2)
    dp.register_message_handler(load_quantity3, state=FSMAdmin.quantity3)
    dp.register_callback_query_handler(load_visibility,
                                       lambda c: c.data in ["Да", "Нет"], state=FSMAdmin.visibility)
    dp.register_message_handler(load_price, state=FSMAdmin.price)

    dp.register_message_handler(cm_start_delete, commands='Удалить_товар', state=None)
    dp.register_message_handler(cm_show_delete, state=FSMAdmin.show_delete)
    dp.register_callback_query_handler(cm_delete, lambda x: x.data and x.data.startswith('del '), state=FSMAdmin.delete)

    dp.register_message_handler(cm_start_change, commands='Изменить_товар', state=None)
    dp.register_message_handler(cm_show_change, state=FSMAdmin.show_change)
    dp.register_callback_query_handler(cm_change,
                                       lambda x: x.data and (x.data.startswith('visibility ') or x.data.startswith('quantity') or x.data.startswith('price ')),
                                       state=FSMAdmin.change)
    dp.register_message_handler(cm_change_end, state=FSMAdmin.change_end)
    dp.register_message_handler(exel_upload, commands=['export_data'])




