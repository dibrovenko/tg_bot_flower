import asyncio
import re

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram import types, Dispatcher
from aiogram.dispatcher.filters import IDFilter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ContentType, Poll

from create_bot import dp, bot, types
from keyboards import kb_client, kb_admin, kb_client_registration, kb_client_registration_name
from data_base import sqlite_dp

from handlers.other import set_client_commands, set_admin_commands, delete_messages, find_best_way, delivery_time
from data_base.sqlite_dp import sql_update_data, sql_get_phot_and_address, get_quantity_by_name

admins_list = [310251240, 421278460, 450091492]


# @dp.message_handler(commands = ['start', 'help'])
async def commands_start(message: types.Message):
    await set_client_commands()
    await bot.send_message(message.from_user.id, f'Это магазин, который позволит быстро и дешево купить цветы !',
                           reply_markup=kb_client)


# @dp.message_handler(commands = ['admin'])
async def commands_Admin(message: types.Message):
    await set_admin_commands(message)
    await message.reply('Вы получили права администратора', reply_markup=kb_admin)


# @dp.message_handler(commands = ['Меню'])
async def commands_menu(message: types.Message):
    await sqlite_dp.sql_read(message)


# @dp.message_handler(commands = ['поддержка'])
async def commands_help(message: types.Message):
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id - 1)
    await bot.send_message(message.from_user.id,
                           'Это магазин, который позволит быстро и дешево купить цветы ! ПОДДЕРЖКА')


class FSMRegistration(StatesGroup):
    name_tg = State()
    name_real = State()
    phone = State()
    phone2 = State()
    address = State()
    way_of_delivery = State()
    time_delivery = State()
    payment = State()


# Начало диалога регистрации
# @dp.message_handler(commands='/Купить', state=None)
async def cm_start_registration(message: types.Message, state: FSMContext):
    name = 'Розы Silva Pink'
    quantity = 21
    full_cost_without_delivery = '21 × 200 + 150_(упаковка)_ = *4350* руб.'
    # await message.answer(f'_ВАШ ЗАКАЗ_', parse_mode="Markdown", reply_markup=kb_client_registration)
    for ret in await sql_get_phot_and_address(name):
        caption = name + "\n" + full_cost_without_delivery
        album = types.MediaGroup()
        matches = re.findall(r"'(.*?)'", ret[3])

        for i, match in enumerate(matches):
            if i == len(matches) - 1:
                album.attach_photo(photo=match, caption=caption, parse_mode="Markdown")
            else:
                album.attach_photo(photo=match)

        await message.answer_media_group(media=album)
    await message.answer(text="Все верно?", reply_markup=InlineKeyboardMarkup().
                         insert(InlineKeyboardButton(f'Да, продолжить оформление', callback_data=f"Yes")).
                         add(InlineKeyboardButton(f'Нет, вернуться в корзину', callback_data=f"No")))
    await FSMRegistration.name_tg.set()
    async with state.proxy() as data:
        data['message_id_start'] = message.message_id
        data['name'] = name  # название товара
        data['quantity'] = quantity
        if message.from_user["username"] is None:
            data['name_tg'] = message.from_user["id"]
        else:
            data['name_tg'] = message.from_user["username"]


# Подтверждение регистрации
@dp.callback_query_handler(lambda c: c.data in ['Yes', 'No'], state=FSMRegistration.name_tg)
async def cm_confirmation_registration(callback: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        asyncio.create_task(
            delete_messages(callback.message.chat.id, data['message_id_start'], callback.message.message_id, 5, 0.3))
    asyncio.create_task(
        delete_messages(callback.from_user.id, callback.message.message_id, callback.message.message_id + 1, 7, 0))

    if callback.data == 'Yes':
        async with state.proxy() as data:
            data['message_id_start'] = await callback.message.answer(text=f"Как вас зовут?",
                                                                     reply_markup=kb_client_registration)
            await callback.answer()
        await FSMRegistration.name_real.set()

    elif callback.data == "No":
        await callback.message.answer(text=f"ок, позже будет реализовано")
        await callback.answer()
        await state.finish()


# получаем имя пользователя
@dp.message_handler(state=FSMRegistration.name_real)
async def cm_name_registration(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name_real'] = message.text
        asyncio.create_task(
            delete_messages(message.chat.id, data['message_id_start']['message_id'], message.message_id + 1, 5, 2))
        data['message_id_start'] = await message.answer(text=f"Для доставки нам нужен ваш номер теелефона",
                                                        reply_markup=kb_client_registration_name)
        await FSMRegistration.phone.set()


# получаем номер телефона
@dp.message_handler(content_types=ContentType.CONTACT, state=FSMRegistration.phone)
async def cm_phone_registration(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['phone'] = message.contact.phone_number
        asyncio.create_task(
            delete_messages(message.chat.id, data['message_id_start']['message_id'], message.message_id + 1, 5, 2))
        data['message_id_start'] = await message.answer(text=f"Для доставки нам нужен номер теелефона получателя"
                                                             f"\n_Нажмите на скрепку внизу\n"
                                                             f"Затем выберите в разделе 'Contact' номер человека, которому нужно доставить букет_",
                                                        parse_mode="Markdown", reply_markup=kb_client_registration)
        await FSMRegistration.phone2.set()


# получаем неверный номер телефона
@dp.message_handler(state=FSMRegistration.phone)
async def cm_phone_wrong_registration(message: types.Message, state: FSMContext):
    await message.answer(text=f"Неверные данные, просто нажмите на кнопку _'Поделиться номером'_ ",
                         parse_mode="Markdown",
                         reply_markup=kb_client_registration_name)
    await FSMRegistration.phone.set()


# получаем второй номер телефона
@dp.message_handler(content_types=ContentType.CONTACT, state=FSMRegistration.phone2)
async def cm_phone2_registration(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['phone2'] = message.contact.phone_number
        asyncio.create_task(
            delete_messages(message.chat.id, data['message_id_start']['message_id'], message.message_id + 1, 5, 2))
        data['message_id_start'] = await message.answer(text=f"Укажите адрес "
                                                             f"\n_Нажмите на скрепку внизу\n"
                                                             f"Затем выберите в разделе 'Location' нужный адрес для доставки._",
                                                        parse_mode="Markdown", reply_markup=kb_client_registration)
        await FSMRegistration.address.set()


# получаем неверный второй номер телефона
@dp.message_handler(state=FSMRegistration.phone2)
async def cm_phone2_wrong_registration(message: types.Message, state: FSMContext):
    await message.answer(text=f"Неверные данные, внимательно прочитайте как нужно отправить контакт"
                              f"\n_Нажмите на скрепку внизу\n"
                              f"Затем выберите в разделе 'Contact' номер человека, которому нужно доставить букет_",
                         parse_mode="Markdown", reply_markup=kb_client_registration)
    await FSMRegistration.phone2.set()


# получаем адрес доставки
@dp.message_handler(content_types=[types.ContentType.LOCATION, types.ContentType.VENUE], state=FSMRegistration.address)
async def cm_address_registration(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['address'] = f'{message.location["latitude"]},{message.location["longitude"]}'
        print(data['address'])
        asyncio.create_task(
            delete_messages(message.chat.id, data['message_id_start']['message_id'], message.message_id + 1, 5, 2))

        origin_dict_sorted = await find_best_way(data['address'])
        quantity_dict = await get_quantity_by_name(data['name'])
        # Создаем новый словарь
        new_origin_dict_sorted = {}
        # Обходим все ключи в origin_dict_sorted
        for key in origin_dict_sorted:
            # Добавляем новую пару ключ-значение в новый словарь, если на складе есть нужное количество
            if quantity_dict[key] >= data['quantity']:
                new_origin_dict_sorted[key] = [origin_dict_sorted[key], quantity_dict[key]]
                break

        # print(origin_dict_sorted)
        # print(quantity_dict)
        # print(new_origin_dict_sorted)

        for key, value in new_origin_dict_sorted.items():
            data['delivery_from_point'] = key
            data['time_of_delivery'] = value[0][0]
            data['destination_of_delivery'] = value[0][1]

        prices = {'600': 1800, '800': 2700, '1000': 36000}
        if data['time_of_delivery'] < prices['600']:
            price = list(prices.keys())[0]
        elif prices['800'] <= data['time_of_delivery'] <= prices['1000']:
            price = list(prices.keys())[1]
        else:
            price = list(prices.keys())[2]

        data['list_of_time_for_delivery'] = []
        data['list_of_time_for_delivery'] = delivery_time()
        print(data['list_of_time_for_delivery'])

        if data['list_of_time_for_delivery'][0] and data['list_of_time_for_delivery'][1]:
            data['message_id_start'] = await message.answer(text=f"Отлично осталось выбрать способ доставки ",
                                                            parse_mode="Markdown",
                                                            reply_markup=InlineKeyboardMarkup().
                                                            insert(InlineKeyboardButton(
                                                                f'Express доставка за {price} рублей',
                                                                callback_data=f"Express")).
                                                            add(InlineKeyboardButton(
                                                                f'Обычная доставка сегодня после {data["list_of_time_for_delivery"][2][0].split()[0]}',
                                                                callback_data=f"Today")).
                                                            add(InlineKeyboardButton(f'Завтра к определенному времени',
                                                                                     callback_data=f"tomorrow")))
        elif data['list_of_time_for_delivery'][0]:
            data['message_id_start'] = await message.answer(text=f"Отлично осталось выбрать способ доставки ",
                                                            parse_mode="Markdown",
                                                            reply_markup=InlineKeyboardMarkup().
                                                            insert(InlineKeyboardButton(
                                                                f'Express доставка за {price} рублей',
                                                                callback_data=f"Express")).
                                                            add(InlineKeyboardButton(f'Завтра к определенному времени',
                                                                                     callback_data=f"tomorrow")))
        else:
            data['message_id_start'] = await message.answer(text=f"Отлично осталось выбрать способ доставки ",
                                                            parse_mode="Markdown",
                                                            reply_markup=InlineKeyboardMarkup().
                                                            add(InlineKeyboardButton(f'Завтра к определенному времени',
                                                                                     callback_data=f"tomorrow")))

    await FSMRegistration.way_of_delivery.set()


# получаем неверный адрес
@dp.message_handler(content_types=[types.ContentType.ANY], state=FSMRegistration.address)
async def cm_address_wrong_registration(message: types.Message, state: FSMContext):
    await message.answer(text=f"Неверные данные, внимательно прочитайте, как нужно отправить адрес"
                              f"\n_Нажмите на скрепку внизу\n"
                              f"Затем выберите в разделе 'Location' нужный адрес для доставки._",
                         parse_mode="Markdown", reply_markup=kb_client_registration)
    await FSMRegistration.address.set()



@dp.callback_query_handler(
    lambda x: x.data and (x.data.startswith('Express') or x.data.startswith('Today') or x.data.startswith('tomorrow')),
    state=FSMRegistration.way_of_delivery)
async def cm_way_of_delivery_registration(callback: types.CallbackQuery, state: FSMContext):
    asyncio.create_task(
        delete_messages(callback.from_user.id, callback.message.message_id, callback.message.message_id + 1, 7, 0))
    async with state.proxy() as data:

        data['way_of_delivery'] = callback.data.split()[0]
        print(data['way_of_delivery'])

        match callback.data.split()[0]:
            case 'Express':
                await callback.message.answer(text=f"ок, позже будет реализована оплата", reply_markup=kb_client)
                await callback.answer()
                await state.finish()
            case 'Today':
                async with state.proxy() as data:
                    await callback.answer()
                    data['message_id_start'] = await bot.send_poll(chat_id=callback.message.chat.id,
                                                                   question='Выберите удобное время для доставки',
                                                                   options=list(data['list_of_time_for_delivery'][2]),
                                                                   is_anonymous=False,
                                                                   allows_multiple_answers=True)
                    #await FSMRegistration.time_delivery.set()
                    await state.finish()
            case 'tomorrow':
                async with state.proxy() as data:
                    await callback.answer()
                    data['message_id_start'] = await bot.send_poll(chat_id=callback.message.chat.id,
                                                                   question='Выберите удобное время для доставки',
                                                                   options=list(data['list_of_time_for_delivery'][2]),
                                                                   is_anonymous=False,
                                                                   allows_multiple_answers=True)
                #await FSMRegistration.time_delivery.set()
                await state.finish()


# обработчик ответов на опрос по времени
#@dp.message_handler(state=FSMRegistration.time_delivery)
@dp.poll_answer_handler()
async def process_poll_answer(poll_answer: types.PollAnswer):
    time = str(poll_answer["option_ids"])
    print(time)
    print(poll_answer)
    await bot.send_message(poll_answer.user.id, text=f"ок, позже будет реализована оплата", reply_markup=kb_client)


# Регистрируем хендлеры
def register_handlers_clients(dp: Dispatcher):
    dp.register_message_handler(commands_start, commands=['start', 'help'])
    dp.register_message_handler(commands_Admin, IDFilter(admins_list), commands=['admin'])
    dp.register_message_handler(commands_menu, commands=['Меню'])
    dp.register_message_handler(commands_help, commands=['поддержка'])
    dp.register_message_handler(cm_start_registration, commands=['Купить'], state=None)
