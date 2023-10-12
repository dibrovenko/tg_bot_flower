import asyncio
import re
import os
import logging

from aiogram.dispatcher import FSMContext, filters
from aiogram.dispatcher.filters import IDFilter
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram import types, Dispatcher
from create_bot import bot
from keyboards import kb_admin, kb_add_admin, kb_load_photo_admin, inline_kb_category_admin, \
    inline_kb_subcategory_admin, subcategory, inline_visibility_admin

from data_base.sqlite_dp import get_positions_sql, add_positions_sql, \
    del_positions_sql, update_positions_sql, export_to_excel, notifications_start, update_database_from_excel
from handlers.other import set_admin_dell_commands, check_valid_text, set_admin_commands, delete_messages
from error_decorators.admin import dec_error_mes, dec_error_mes_state, dec_error_callback_state
from keyboards.collector_kb import kb_collector
from parameters import admins


# получение пользовательского логгера и установка уровня логирования
py_logger = logging.getLogger(__name__)
py_logger.setLevel(logging.ERROR)

# настройка обработчика и форматировщика в соответствии с нашими нуждами
log_file = os.path.join(f"log_directory/{__name__}.log")
py_handler = logging.FileHandler(log_file, mode='w')

#py_handler = logging.FileHandler(f"{__name__}.log", mode='w')
py_formatter = logging.Formatter("%(name)s %(asctime)s %(levelname)s %(message)s")

# добавление форматировщика к обработчику
py_handler.setFormatter(py_formatter)
# добавление обработчика к логгеру
py_logger.addHandler(py_handler)


admins_list = [value[0] for value in admins.values()]
notifications_start_var = True


# Обработчик кнопки Заказы 📦
# @dp.message_handler(IDFilter(admins_list), filters.Text(equals='Заказы 📦'))
@dec_error_mes
async def orders_pressed(message: types.Message):
    await message.answer("Внизу появились кнопки, связанные с заказами. Чтобы вернуться назад, /admin", reply_markup=kb_collector)


# Обработчик кнопки 'Аналитика 📊'
# @dp.message_handler(IDFilter(admins_list), filters.Text(equals='Аналитика 📊'))
@dec_error_mes
async def analytics_pressed(message: types.Message):
    await message.answer("еще в разработке 🧑‍💻")


# Обработчик команды /take_goods_exel
# @dp.message_handler(commands=['take_goods_exel'])
@dec_error_mes
async def take_goods_exel(message: types.Message):
    result = await export_to_excel("goods")
    if result:
        # Отправляем excel файл пользователю
        with open('Exel/data.xlsx', 'rb') as file:
            await bot.send_document(message.chat.id, file, reply_markup=kb_admin)
    else:
        await message.answer("ошибка на сервере", reply_markup=kb_admin)


# Обработчик команды /take_orders_exel
# @dp.message_handler(commands=['take_orders_exel'])
@dec_error_mes
async def take_orders_exel(message: types.Message):
    result = await export_to_excel("orders")
    if result:
        # Отправляем excel файл пользователю
        with open('Exel/data.xlsx', 'rb') as file:
            await bot.send_document(message.chat.id, file)
    else:
        await message.answer("ошибка на сервере")


class FSMAdmin_record_start_goods_exel(StatesGroup):
    start = State()


# Обработчик команды /record_goods_excel
# @dp.message_handler(commands=['record_goods_excel'], state=None)
@dec_error_mes_state
async def record_start_goods_exel(message: types.Message, state: FSMContext):
    await FSMAdmin_record_start_goods_exel.start.set()
    async with state.proxy() as data:
        data['start_message_id'] = message.message_id

    result = await export_to_excel()
    global notifications_start_var

    if result and notifications_start_var is True:
        # Отправляем excel файл пользователю
        with open('Exel/data_goods.xlsx', 'rb') as file:
            await message.answer("WARNING!!!  Просим вас внимательно ознакомиться с инструкцией.\n "
                                 "При работе с файлом возможно прерывание процесса из-за изменений данных другими"
                                 " пользователями. В таком случае, пожалуйста, повторите вызов команды и загрузите файл"
                                 " заново.\n Для начала работы, пожалуйста, скачайте файл и производите изменения "
                                 "только в нем. Ниже приведена информация о столбцах в таблице:\n "
                                 "- quantity1: количество на Калужском шоссе \n"
                                 "- quantity2: количество на переулке Маяковского \n "
                                 "- quantity3: количество на улице Смольная\n "
                                 "- visibility: видимость для пользователя (можно указывать только Да/Нет)\n"
                                 "Просим вас тщательно и внимательно работать с таблицей. Если вам требуется внести "
                                 "незначительные изменения, рекомендуется использовать стандартный способ изменения "
                                 "данных.", reply_markup=kb_add_admin)

            await bot.send_document(message.chat.id, file)
            await bot.send_sticker(chat_id=message.chat.id,
                                   sticker=r"CAACAgIAAxkBAAEJ-yxk1YAg_dlxwc3YQMbFvUE__G42oQACAgEAAjDUnREHq4uVsB20UjAE")

            notifications_start_var = asyncio.create_task(notifications_start())
            if not await notifications_start_var:
                msg = await message.answer("Только что произошло обращение к базе данных, в результате которого были"
                                           " внесены изменения. Поэтому файл, который вам был отправлен, является "
                                           "некорректным.\nЕсли вы желаете продолжить изменение данных, пожалуйста, "
                                           "отправьте команду /record_goods_excel", reply_markup=kb_admin)
                await state.finish()
                asyncio.create_task(
                    delete_messages(message.chat.id, message.message_id, msg.message_id, 4, 0))

    elif result:
        await message.answer("В данный момент другой администратор уже осуществляет изменения, поэтому в настоящее "
                             "время невозможно внести изменения.", reply_markup=kb_admin)
        await state.finish()
        notifications_start_var = True

    else:
        await message.answer("ошибка на сервере", reply_markup=kb_admin)
        await state.finish()


# Ловим ответ в виде exel файла после команды /record_goods_exсel
# @dp.message_handler(content_types=['document'], state=FSMAdmin_record_start_goods_exel.start,)
@dec_error_mes_state
async def record_end_goods_exel(message: types.Message, state: FSMContext):
    # Проверяем тип файла и сохраняем его с именем data.xlsx
    if message.document.mime_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
        # останавляем прослушивание изменений базы данных
        global notifications_start_var
        notifications_start_var = notifications_start_var.cancel()

        if os.path.exists('Exel/data_goods.xlsx'):
            os.remove('Exel/data_goods.xlsx')

        await message.document.download(destination_file='Exel/data_goods.xlsx')
        # вносим изменения в базу данных
        result_update = await update_database_from_excel()

        if result_update:
            msg = await message.answer('Файл успешно сохранен.')
        else:
            msg = await message.answer('Файл не сохранен, ошибка на сервере')

        async with state.proxy() as data:
            asyncio.create_task(
                delete_messages(message.chat.id, data['start_message_id'], msg.message_id, 4, 0))
        await state.finish()

    else:
        await message.answer('Пожалуйста, отправьте файл в формате Excel.')


# @dp.message_handler(IDFilter(admins_list), commands=['admin'])
@dec_error_mes
async def commands_Admin(message: types.Message):
    await set_admin_commands(message)
    await message.reply('Вы получили права администратора', reply_markup=kb_admin)


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


# Выход из состояний
# @dp.message_handler(state="*", commands='отмена')
# @dp.message_handler(filters.Text(equals='отмена', ignore_case=True), state="*")
@dec_error_mes_state
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    elif current_state == FSMAdmin.show_delete.state:
        async with state.proxy() as data:
            asyncio.create_task(
                delete_messages(message.chat.id, data['start_message_id'], message.message_id + 1, 4, 0))
        await message.reply('Хорошо, изменения не будут сохранены', reply_markup=kb_admin)
        await state.finish()
        await set_admin_commands(message)

    elif current_state == FSMAdmin_record_start_goods_exel.start.state:
        async with state.proxy() as data:
            asyncio.create_task(
                delete_messages(message.chat.id, data['start_message_id'], message.message_id + 1, 4, 0))
        await message.reply('хорошо', reply_markup=kb_admin)
        # останавляем прослушивание изменений базы данных
        global notifications_start_var
        notifications_start_var = notifications_start_var.cancel()
        await state.finish()
        await set_admin_commands(message)

    else:
        async with state.proxy() as data:
            asyncio.create_task(
                delete_messages(message.chat.id, data['start_message_id'], message.message_id + 1, 4, 0))
        await message.reply('OK', reply_markup=kb_admin)
        await state.finish()
        await set_admin_commands(message)


# Начало диалога загрузки нового пункта меню
# @dp.message_handler(commands='/Добавить_товар', state=None)
@dec_error_mes_state
async def cm_start(message: types.Message, state: FSMContext):
    await FSMAdmin.photo.set()
    async with state.proxy() as data:
        data['photo'] = list()
        data['start_message_id'] = message.message_id
    await message.reply('Загрузи фото', reply_markup=kb_add_admin)


# Выход из состояний загрузки фото
# @dp.message_handler(state=FSMAdmin.photo, commands='загрузить')
@dec_error_mes_state
async def stop_load_photo(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['message_id_start'] = message.message_id

    await FSMAdmin.name.set()
    await bot.send_message(message.from_user.id, "Теперь введи название",
                           reply_markup=kb_add_admin)


# Ловим первый ответ и пишем в словарь
# @dp.message_handler(content_types=['photo'], state=FSMAdmin.photo)
@dec_error_mes_state
async def load_photo(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['photo'].append(message.photo[0].file_id)

    current_state = await state.get_state()
    if current_state == FSMAdmin.photo.state:
        await bot.send_message(message.from_user.id, "Отправь еще фото, либо нажми /загрузить ",
                               reply_markup=kb_load_photo_admin)
    else:
        await FSMAdmin.name.set()
        await message.reply("Теперь введи название")


# Ловим второй ответ на имя
# @dp.message_handler(state=FSMAdmin.name)
@dec_error_mes_state
async def load_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
    await FSMAdmin.name_english.set()
    await message.answer('Введите имя на английском строчными буквы.'
                         '\nC помощью этого названия будет осуществляться поиск.\nМежду словами должен быть не пробел,'
                         ' а "_"\nВот пример: rose_red_15sm', reply_markup=kb_add_admin)


# Ловим второй ответ на имя
# @dp.message_handler(state=FSMAdmin.name_english)
@dec_error_mes_state
async def load_english_name(message: types.Message, state: FSMContext):
    if check_valid_text(message.text):
        async with state.proxy() as data:
            data['name_english'] = message.text
        await FSMAdmin.category.set()
        await message.answer('Выберите категорию:', reply_markup=inline_kb_category_admin)
    else:
        await message.answer('Введите в правильном формате, название содержит неверные символы')


# Обработчик нажатий на кнопки категорий
# @dp.callback_query_handler(lambda c: c.data in ["Монобукеты", "Авторские_букеты", "Цветы_в_коробке"], state=FSMAdmin.category)
@dec_error_callback_state
async def load_category(callback: types.CallbackQuery, state: FSMContext):
    # Если нажата первая кнопка, открываем подкатегорию
    if callback.data == "Монобукеты":
        async with state.proxy() as data:
            data['category'] = callback.data
        await FSMAdmin.subcategory.set()
        await callback.message.answer("вы выбрали Монобукеты.\n\nТеперь добавьте подкатегорию:",
                                      reply_markup=inline_kb_subcategory_admin)
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
# @dp.callback_query_handler(lambda c: c.data in subcategory, state=FSMAdmin.subcategory)
async def load_subcategory(callback: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data['subcategory'] = callback.data
    await FSMAdmin.description.set()
    await callback.message.answer(text=f"вы выбрали {callback.data}.\n\nВведи описание")
    await callback.answer()


# Ловим пятый ответ на описание
# @dp.message_handler(state=FSMAdmin.description)
@dec_error_mes_state
async def load_description(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['description'] = message.text
    await FSMAdmin.quantity1.set()
    await message.answer('Теперь укажи количество на Калужском шоссе')


# Ловим ответ на количество на Калужском шоссе
# @dp.message_handler(state=FSMAdmin.quantity1)
@dec_error_mes_state
async def load_quantity1(message: types.Message, state: FSMContext):
    try:
        async with state.proxy() as data:
            data['quantity1'] = int(message.text)
        await FSMAdmin.quantity2.set()
        await message.answer('Укажи количество на Маяковском переулке')

    except ValueError:
        await message.reply(f"Ошибка: {message.text} не является целым числом.\nЖду целое число")


# Ловим ответ на количество на Маяковском переулке
# @dp.message_handler(state=FSMAdmin.quantity2)
@dec_error_mes_state
async def load_quantity2(message: types.Message, state: FSMContext):
    try:
        async with state.proxy() as data:
            data['quantity2'] = int(message.text)
        await FSMAdmin.quantity3.set()
        await message.answer('Укажи количество на улице Смольная')

    except ValueError:
        await message.reply(f"Ошибка: {message.text} не является целым числом.\nЖду целое число")


# Ловим ответ на количество на улице Смольная
# @dp.message_handler(state=FSMAdmin.quantity3)
@dec_error_mes_state
async def load_quantity3(message: types.Message, state: FSMContext):
    try:
        async with state.proxy() as data:
            data['quantity3'] = int(message.text)
        await FSMAdmin.visibility.set()
        await message.answer('Теперь укажи видимость для пользователя', reply_markup=inline_visibility_admin)

    except ValueError:
        await message.reply(f"Ошибка: {message.text} не является целым числом.\nЖду целое число")


# Ловим ответ на видимость
# @dp.callback_query_handler(lambda c: c.data in ["Да", "Нет"], state=FSMAdmin.visibility)
@dec_error_callback_state
async def load_visibility(callback: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data['visibility'] = callback.data
    await FSMAdmin.price.set()
    await callback.message.answer(text=f"вы выбрали '{callback.data}'\n\nТеперь укажи цену за одну штуку")
    await callback.answer()


# Ловим последний ответ и используем полученные данные
# @dp.message_handler(state=FSMAdmin.price)
@dec_error_mes_state
async def load_price(message: types.Message, state: FSMContext):
    try:
        async with state.proxy() as data:
            data['price'] = float(message.text)

            # await message.reply(str(data), reply_markup=kb_admin)
            await message.answer(text="Товар добавлен", reply_markup=kb_admin)
            asyncio.create_task(
                delete_messages(message.chat.id, data['start_message_id'], message.message_id + 1, 4, 0))
            columns_sql = ["img", "name", "name_english", "category", "subcategory", "description", "quantity1",
                           "quantity2", "quantity3", "visibility", "price"]
            values_sql = [str(data["photo"])]
            for key in columns_sql[1:]:
                values_sql.append(data[key])

            result = await add_positions_sql(table_name="goods", columns=columns_sql, values=values_sql)
            if not result:
                py_logger.error(
                    f"change_goods_FALSE: данные не записались в базу данных, State: {await state.get_state()}"
                    f"\nchat_id: {message.chat.id}, values: {values_sql}"
                )
        await state.finish()

    except ValueError:
        await message.reply(f"Ошибка: {message.text} не является числом.\nЖду числа")


# Начало диалога удаления  пункта меню
# @dp.message_handler(commands='/Удалить_товар', state=None)
@dec_error_mes_state
async def cm_start_delete(message: types.Message, state: FSMContext):
    await FSMAdmin.show_delete.set()
    await message.reply('через / выберите товар', reply_markup=kb_add_admin)
    await set_admin_dell_commands(message)
    async with state.proxy() as data:
        data['start_message_id'] = message.message_id


# Показываем выбор удаления
# @dp.message_handler(state=FSMAdmin.show_delete)
@dec_error_mes
async def cm_show_delete(message: types.Message):
    list_name = []
    for ret in await get_positions_sql("name_english", table_name="goods"):
        list_name.append(ret[0])

    if message.text[1:] in list_name:
        await FSMAdmin.delete.set()
        await set_admin_commands(message)
        lst = await get_positions_sql("*", table_name="goods", condition="WHERE name_english = $1",
                                      condition_value=message.text[1:])
        for ret in lst:
            caption = f'*{ret[1]}*\n_English_: *{ret[2]}*\n_Категория:_ *{ret[3]}*\n_Подкатегория:_ *{ret[4]}*\n_' \
                      f'Описание:_ *{ret[5]}*\n_Количество на Калужском:_ *{ret[6]}*' \
                      f'\n_Количество на Маяковском:_ *{ret[7]}*\n_Количество на Смольной:_ *{ret[8]}*' \
                      f'\n_Видимость:_ *{ret[9]}*\n_Цена_ *{ret[-1]}*'
            album = types.MediaGroup()
            matches = re.findall(r"'(.*?)'", ret[0])
            for i, match in enumerate(matches):
                if i == len(matches) - 1:
                    album.attach_photo(photo=match, caption=caption, parse_mode="Markdown")
                else:
                    album.attach_photo(photo=match)
            await message.answer_media_group(media=album)
            await message.answer(text="**************", reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton(f'удалить {ret[1]}', callback_data=f"del {ret[1]}")))
    else:
        await set_admin_commands(message)


# Ловим ответ  удаляем данные
# @dp.callback_query_handler(lambda x: x.data and x.data.startswith('del '), state=FSMAdmin.delete)
@dec_error_callback_state
async def cm_delete(callback_query: types.CallbackQuery, state: FSMContext):
    result = await del_positions_sql(table_name="goods", condition="WHERE name = $1",
                                     value=callback_query.data.replace('del ', ''))
    if result:
        await callback_query.answer(text=f"{callback_query.data.replace('del ', '')} удален.", show_alert=True)
    else:
        py_logger.error(
            f"change_goods_FALSE: данные не удалились из базы данных, State: {await state.get_state()}"
            f"\nchat_id: {callback_query.message.chat.id}, callback_query.dat: {callback_query}"
        )
        await callback_query.answer(text=f"{callback_query.data.replace('del ', '')} не удален\nОшибка!!!",
                                    show_alert=True)
    async with state.proxy() as data:
        asyncio.create_task(
            delete_messages(callback_query.message.chat.id, data['start_message_id'],
                            callback_query.message.message_id + 1, 4, 0))
    await state.finish()
    await callback_query.message.answer('вы вернулись в админскую панель!', reply_markup=kb_admin)


# Начало диалога изменеия  пункта меню
# @dp.message_handler(commands='/Изменить_товар', state=None)
@dec_error_mes_state
async def cm_start_change(message: types.Message, state: FSMContext):
    await FSMAdmin.show_change.set()
    await message.reply('через / выберите товар', reply_markup=kb_add_admin)
    await set_admin_dell_commands(message)
    async with state.proxy() as data:
        data['start_message_id'] = message.message_id


# Показываем выбор изменения
# @dp.message_handler(state=FSMAdmin.show_change)
@dec_error_mes_state
async def cm_show_change(message: types.Message, state: FSMContext):
    list_name = []
    for ret in await get_positions_sql("name_english", table_name="goods"):
        list_name.append(ret[0])

    if message.text[1:] in list_name:
        await set_admin_commands(message)
        await FSMAdmin.change.set()
        async with state.proxy() as data:
            data['name_change'] = message.text[1:]
        lst = await get_positions_sql("*", table_name="goods", condition="WHERE name_english = $1",
                                      condition_value=message.text[1:])
        for ret in lst:
            caption = f'*{ret[1]}*\n_English_: *{ret[2]}*\n_Категория:_ *{ret[3]}*\n_Подкатегория:_ *{ret[4]}*' \
                      f'\n_Описание:_ *{ret[5]}*\n_Количество на Калужском:_ *{ret[6]}*' \
                      f'\n_Количество на Маяковском:_ *{ret[7]}*\n_Количество на Смольной:_ *{ret[8]}*' \
                      f'\n_Видимость:_ *{ret[9]}*\n_Цена_ *{ret[-1]}*'

            async with state.proxy() as data:
                data['visibility'] = ret[9]

            album = types.MediaGroup()
            matches = re.findall(r"'(.*?)'", ret[0])
            for i, match in enumerate(matches):
                if i == len(matches) - 1:
                    album.attach_photo(photo=match, caption=caption, parse_mode="Markdown")
                else:
                    album.attach_photo(photo=match)
            await message.answer_media_group(media=album)
            await message.answer(text="Что изменить?", reply_markup=InlineKeyboardMarkup().
                                 insert(InlineKeyboardButton(f'Видимость',
                                                             callback_data=f"visibility {ret[1]}")).
                                 insert(InlineKeyboardButton(f'Цену',
                                                             callback_data=f"price {ret[1]}")).
                                 add(InlineKeyboardButton(f'Количество на Калужском',
                                                          callback_data=f"quantity1 {ret[1]}")).
                                 add(InlineKeyboardButton(f'Кол. на Маяковском',
                                                          callback_data=f"quantity2 {ret[1]}")).
                                 insert(InlineKeyboardButton(f'Кол. на Смольной',
                                                             callback_data=f"quantity3 {ret[1]}")))
    else:
        return


# Ловим ответ какую строчку поменять
# @dp.callback_query_handler(lambda x: x.data and (x.data.startswith('visibility ') or x.data.startswith('quantity')
# or x.data.startswith('price ')), state=FSMAdmin.change)
@dec_error_callback_state
async def cm_change(callback_query: types.CallbackQuery, state: FSMContext):
    # await set_admin_commands()
    column_name = callback_query.data.split()[0]
    async with state.proxy() as data:
        data['column_name'] = column_name
    match column_name:
        case 'visibility':
            async with state.proxy() as data:

                if data['visibility'].split()[0] == "Нет":
                    update = await update_positions_sql(table_name="goods",
                                                        column_values={data['column_name']: 'Да'},
                                                        condition=f"WHERE name_english = '{data['name_change']}'")
                else:
                    update = await update_positions_sql(table_name="goods",
                                                        column_values={data['column_name']: 'Нет'},
                                                        condition=f"WHERE name_english = '{data['name_change']}'")
                    # await sql_update_data(name=data['name_change'], column_name=data['column_name'], new_value='Да')

                asyncio.create_task(
                    delete_messages(callback_query.message.chat.id, data['start_message_id'],
                                    callback_query.message.message_id + 1, 5, 0))
            if update:
                await callback_query.message.answer(text="Видимость изменена", reply_markup=kb_admin)
            else:
                py_logger.error(
                    f"change_goods_FALSE: данные не записались в базу данных, State: {await state.get_state()}"
                    f"\nchat_id: {callback_query.message.chat.id}, Ошибка. Видимость не изменена")

                await callback_query.message.answer(text="Ошибка. Видимость не изменена", reply_markup=kb_admin)
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


# Ловим ответ и меняем данные
# @dp.message_handler(state=FSMAdmin.change_end)
@dec_error_mes_state
async def cm_change_end(message: types.Message, state: FSMContext):
    try:
        async with state.proxy() as data:
            column_name = data['column_name']
            match column_name:
                case 'quantity1' | 'quantity2' | 'quantity3':
                    int(message.text)
                case 'price':
                    float(message.text)
            update = await update_positions_sql(table_name="goods", column_values={data['column_name']: message.text},
                                                condition=f"WHERE name_english = '{data['name_change']}'")
            asyncio.create_task(
                delete_messages(message.chat.id, data['start_message_id'], message.message_id + 1, 4, 0))
        await state.finish()
        if update:
            await message.answer('вы вернулись в админскую панель!', reply_markup=kb_admin)
        else:
            py_logger.error(f"change_goods_FALSE: данные не записались в базу данных, State: {await state.get_state()}"
                            f"\nchat_id: {message.chat.id}, данные: {data['column_name']} {message.text}")
            await message.answer('Ошибка, данные не записались', reply_markup=kb_admin)
    except ValueError:
        await message.reply('не верный формат ввода, введи еще раз')


# Регистрируем хендлеры
def register_handlers_admin(dp: Dispatcher):
    dp.register_message_handler(commands_Admin, IDFilter(admins_list), commands=['admin'])

    dp.register_message_handler(cm_start, IDFilter(admins_list), filters.Text(equals='Добавить товар'), state=None)
    dp.register_message_handler(cancel_handler, IDFilter(admins_list), state="*", commands='отмена')
    dp.register_message_handler(cancel_handler, IDFilter(admins_list), filters.Text(equals='отмена', ignore_case=True),
                                state="*")
    dp.register_message_handler(stop_load_photo, IDFilter(admins_list), state=FSMAdmin.photo, commands='загрузить')
    dp.register_message_handler(load_photo, IDFilter(admins_list), content_types=['photo'], state=FSMAdmin.photo)
    dp.register_message_handler(load_name, IDFilter(admins_list), state=FSMAdmin.name)
    dp.register_message_handler(load_english_name, IDFilter(admins_list), state=FSMAdmin.name_english)
    dp.register_callback_query_handler(
        load_category, lambda c: c.data in ["Монобукеты", "Авторские_букеты", "Цветы_в_коробке"], IDFilter(admins_list),
        state=FSMAdmin.category)
    dp.register_callback_query_handler(load_subcategory, lambda c: c.data in subcategory, IDFilter(admins_list),
                                       state=FSMAdmin.subcategory)
    dp.register_message_handler(load_description, IDFilter(admins_list), state=FSMAdmin.description)
    dp.register_message_handler(load_quantity1, IDFilter(admins_list), state=FSMAdmin.quantity1)
    dp.register_message_handler(load_quantity2, IDFilter(admins_list), state=FSMAdmin.quantity2)
    dp.register_message_handler(load_quantity3, IDFilter(admins_list), state=FSMAdmin.quantity3)
    dp.register_callback_query_handler(load_visibility, IDFilter(admins_list),
                                       lambda c: c.data in ["Да", "Нет"], state=FSMAdmin.visibility)
    dp.register_message_handler(load_price, IDFilter(admins_list), state=FSMAdmin.price)

    dp.register_message_handler(cm_start_delete, IDFilter(admins_list), filters.Text(equals='Удалить товар'),
                                state=None)
    dp.register_message_handler(cm_show_delete, IDFilter(admins_list), state=FSMAdmin.show_delete)
    dp.register_callback_query_handler(cm_delete, lambda x: x.data and x.data.startswith('del '), IDFilter(admins_list),
                                       state=FSMAdmin.delete)

    dp.register_message_handler(cm_start_change, IDFilter(admins_list), filters.Text(equals='Изменить товар'),
                                state=None)
    dp.register_message_handler(cm_show_change, IDFilter(admins_list), state=FSMAdmin.show_change)
    dp.register_callback_query_handler(cm_change, IDFilter(admins_list),
                                       lambda x: x.data and (x.data.startswith('visibility ')
                                                             or x.data.startswith('quantity')
                                                             or x.data.startswith('price ')),
                                       state=FSMAdmin.change)
    dp.register_message_handler(cm_change_end, IDFilter(admins_list), state=FSMAdmin.change_end)
    dp.register_message_handler(record_start_goods_exel, IDFilter(admins_list), commands=['record_goods_excel'])
    dp.register_message_handler(record_end_goods_exel, IDFilter(admins_list), content_types=['document'],
                                state=FSMAdmin_record_start_goods_exel.start)
    dp.register_message_handler(take_goods_exel, commands=['take_goods_excel'])
    dp.register_message_handler(take_orders_exel, commands=['take_orders_excel'])
    dp.register_message_handler(orders_pressed, IDFilter(admins_list), filters.Text(equals='Заказы 📦'))
    dp.register_message_handler(analytics_pressed, IDFilter(admins_list), filters.Text(equals='Аналитика 📊'))
