import asyncio
from datetime import datetime, timedelta
import re
import time

import phonenumbers
from aiogram.dispatcher import FSMContext, filters
from aiogram.dispatcher.filters import IDFilter
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram import Dispatcher
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ContentType, ChatActions

from create_bot import dp, bot, types
from dostavista.price import calculate_price_dostavista
from keyboards import kb_client, kb_client_registration, kb_client_registration_name, kb_admin
from data_base import sqlite_dp

from handlers.other import set_client_commands, set_admin_commands, delete_messages, find_best_way, delivery_time, \
    phone_send_messages, phone2_send_messages, comment_courier_send_messages, comment_collector_send_messages, \
    func_for_valid_phone_number, func_send_way_delivery, control_time_order, control_time_dostavista, \
    control_time_yandex, set_collectors_commands, set_client_commands2
from data_base.sqlite_dp import sql_update_data, sql_get_phot_and_address, get_quantity_by_name
from keyboards.client_kb import kb_client_registration_comment, kb_client_pay_inline, kb_client_order_inline, \
    kb_client_registration_start
from keyboards.collector_kb import kb_collector
from yandex.adress import address_correctness_check
from yandex.calculate_price_yandex import calculate_price_yandex
from yandex.cancellation_order import cancellation_order
from yandex.confirmation_order import confirmation_order
from parameters import admins, collectors

admins_list = [value[0] for value in admins.values()]
collector_list = [value[0] for value in collectors.values()]

# @dp.message_handler(commands = ['start', 'help'])
async def commands_start(message: types.Message):
    if message.chat.id in admins_list:
        await set_admin_commands(message=message)
        await bot.send_message(message.from_user.id, f'Вы получили права администратора',
                               reply_markup=kb_admin)
    elif message.chat.id in collector_list:
        await set_collectors_commands(message=message)
        await bot.send_message(message.from_user.id, f'Вы получили права сборщика',
                               reply_markup=kb_collector)
    else:
        await set_client_commands()
        await bot.send_message(message.from_user.id, f'Это магазин, который позволит быстро и дешево купить цветы !',
                               reply_markup=kb_client)


#@dp.message_handler(commands = ['client'])
async def commands_client(message: types.Message):
    await set_client_commands2(message=message)
    await bot.send_message(message.from_user.id, f'Это магазин, который позволит быстро и дешево купить цветы !',
                           reply_markup=kb_client)


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
    comment_courier = State()
    comment_collector = State()
    way_of_delivery = State()
    way_of_delivery2 = State()
    payment = State()
    payment_success = State()


t = {}
t_order = {}
t_dostavista = {}
t_yandex = {}

class TimeError(Exception):
    pass


# Начало диалога регистрации
# @dp.message_handler(commands='/Купить', state=None)
async def cm_start_registration(message: types.Message, state: FSMContext):
    available_points = ["Калужское", "Маяковского", "Смольная"]
    name = 'Розы Silva Pink'
    quantity = 21
    price = 200
    packaging_price = 150
    full_cost_without_delivery = quantity * price + packaging_price
    price_as_str = f'{quantity} × {price} + 150_(упаковка)_ = *{full_cost_without_delivery}* руб.'
    # await message.answer(f'_ВАШ ЗАКАЗ_', parse_mode="Markdown", reply_markup=kb_client_registration)
    for ret in await sql_get_phot_and_address(name):
        caption = name + "\n" + price_as_str
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
    task_order = asyncio.create_task(control_time_order(message, state))
    global t_order
    t_order[message.chat.id] = task_order
    async with state.proxy() as data:
        data['message_id_buy'] = data['message_id_start'] = message.message_id
        data['name'] = name  # название товара
        data['name_english'] = name  # название товара
        data['quantity'] = quantity
        data['full_cost_without_delivery'] = full_cost_without_delivery
        data['packaging_price'] = packaging_price
        data['available_points'] = available_points
        if message.from_user["username"] is None:
            data['name_tg'] = message.from_user["id"]
        else:
            data['name_tg'] = message.from_user["username"]


# Подтверждение регистрации
#@dp.callback_query_handler(lambda c: c.data in ['Yes', 'No'], state=FSMRegistration.name_tg)
async def cm_confirmation_registration(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == 'Yes':
        await callback.message.delete()
        async with state.proxy() as data:
            data['message_back'] = {}
            data['message_back']["phone"] = \
                data['message_id_start'] = await callback.message.answer(text=f"Как вас зовут?",
                                                                         reply_markup=kb_client_registration_start)
            asyncio.create_task(
                delete_messages(callback.message.chat.id, callback.message.message_id+1,
                                data['message_id_start'].message_id, 0.5, 0.3))
            await callback.answer()
        await FSMRegistration.name_real.set()

    elif callback.data == "No":
        global t_order
        if callback.message.chat.id in t_order:
            t_order.pop(callback.message.chat.id).cancel()

        await callback.answer()
        async with state.proxy() as data:
            temporary_var = await callback.message.answer(text=f"ок, позже будет реализовано",
                                                          reply_markup=kb_client_registration)

            asyncio.create_task(
                delete_messages(temporary_var.chat.id, data['message_id_start'], temporary_var.message_id+1, 0.3, 0.2))
        await state.finish()



#Выход из состояний
#@dp.message_handler(filters.Text(equals='отмена ✕', ignore_case=True), state="*")
async def cancel_handler(message: types.Message, state: FSMContext):
    global t, t_order, t_dostavista, t_yandex
    if message.chat.id in t:
        t.pop(message.chat.id).cancel()
    if message.chat.id in t_order:
        t_order.pop(message.chat.id).cancel()
    if message.chat.id in t_dostavista:
        t_dostavista.pop(message.chat.id).cancel()
    if message.chat.id in t_yandex:
        t_yandex.pop(message.chat.id).cancel()

    async with state.proxy() as data:
        asyncio.create_task(
            delete_messages(message.chat.id, data['message_id_buy'], message.message_id + 1, 0, 0))
        try:
            asyncio.create_task(cancellation_order(id=data['result_calculate_price_yandex'][2]))
        except:
            pass

    await message.answer('OK', reply_markup=kb_client)
    await state.finish()



#Возвращение на предыдущее состояние
#@dp.message_handler(filters.Text(equals='назад ⤴', ignore_case=True), state="*")
async def back_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    global t, t_dostavista, t_yandex
    if message.chat.id in t and current_state[16:] == "comment_courier":
        t.pop(message.chat.id).cancel()
    if current_state[16:] == "comment_courier" and message.chat.id in t_dostavista:
        t_dostavista.pop(message.chat.id).cancel()

    dict_state = {'phone': [FSMRegistration.name_real, kb_client_registration_start],
                  'phone2': [FSMRegistration.phone, kb_client_registration_name],
                  'address': [FSMRegistration.phone2, kb_client_registration],
                  'comment_courier': [FSMRegistration.address, kb_client_registration],
                  'comment_collector': [FSMRegistration.comment_courier, kb_client_registration_comment],
                  'way_of_delivery': [FSMRegistration.comment_collector, kb_client_registration_comment]}

    await dict_state[current_state[16:]][0].set()
    async with state.proxy() as data:
        if current_state[16:] == "way_of_delivery" and data["counter_way_of_delivery"]:
            try:
                kb = InlineKeyboardMarkup(row_width=1)
                for value in data['message_back']["way_of_delivery2"]["reply_markup"]["inline_keyboard"]:
                    kb.add(InlineKeyboardButton(text=value[0].text, callback_data=value[0].callback_data))
                await FSMRegistration.way_of_delivery.set()
                await message.answer(text=data['message_back']["way_of_delivery2"]["text"], reply_markup=kb)
                await bot.delete_message(chat_id=message.chat.id,
                                         message_id=data['message_back']["way_of_delivery2"]['message_id'])
                await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
                await message.answer('...', reply_markup=kb_client_registration)
                data["counter_way_of_delivery"] = False
                return
            except:
                pass
        elif current_state[16:] == "way_of_delivery":
            data["counter_way_of_delivery"] = True

        asyncio.create_task(
            delete_messages(message.chat.id, data['message_back'][current_state[16:]]['message_id'] + 1,
                            message.message_id + 1, 0, 0))
    await message.answer('...', reply_markup=dict_state[current_state[16:]][1])

    current_state = await state.get_state()
    if current_state[16:] == "comment_collector" and message.chat.id in t_yandex:
        t_yandex.pop(message.chat.id).cancel()
        try:
            asyncio.create_task(cancellation_order(id=data['result_calculate_price_yandex'][2]))
        except:
            pass



# получаем имя пользователя
#@dp.message_handler(state=FSMRegistration.name_real)
async def cm_name_registration(message: types.Message, state: FSMContext):
    await bot.send_sticker(chat_id=message.chat.id,
                           sticker=r"CAACAgEAAxkBAAEJuGlktZSyBZW0uQr0znbNlnfzj6tq8wACDwEAAjgOghG1zE1_4hSRgi8E")

    async with state.proxy() as data:
        data['name_real'] = message.text
        data['message_back']["phone2"] = \
            data['message_id_start'] = await message.answer(text=f"Для доставки нам нужен ваш номер телефона\n"
                                                            f"_Нажмите на кнопку снизу👇_ или введите номер вручную",
                                                            parse_mode="Markdown",
                                                            reply_markup=kb_client_registration_name)
        await FSMRegistration.phone.set()



# получаем номер телефона
#@dp.message_handler(content_types=ContentType.CONTACT, state=FSMRegistration.phone)
#@dp.message_handler(lambda message: func_for_valid_phone_number(message.text), state=FSMRegistration.phone)
async def cm_phone_registration(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if message.text is None:

            if str(message.contact.phone_number).startswith("+"):
                data['phone'] = message.contact.phone_number
            else:
                data['phone'] = "+" + str(message.contact.phone_number)

        else:

            if message.text.startswith("8"):
                message.text = "+7" + message.text[1:]
            data['phone'] = "+" + str(phonenumbers.parse(message.text).country_code) + str(phonenumbers.parse(message.text).national_number)

        asyncio.create_task(
            delete_messages(message.chat.id, data['message_id_start']['message_id']+1, message.message_id, 12, 0.5))
        data['message_back']["address"] = \
            data['message_id_start'] = await message.answer(text=f"Для доставки нам нужен номер телефона получателя")
                                                        #,parse_mode="Markdown")#, reply_markup=kb_client_registration)
        asyncio.create_task(phone_send_messages(data['message_id_start']))
        await FSMRegistration.phone2.set()



# получаем неверный номер телефона
#@dp.message_handler(content_types=[types.ContentType.ANY], state=FSMRegistration.phone)
async def cm_phone_wrong_registration(message: types.Message, state: FSMContext):
    await message.answer(text=f"Неверные данные, просто нажмите на кнопку _'Поделиться номером'_ снизу👇 или введите номер вручную",
                         parse_mode="Markdown")
    await bot.send_sticker(chat_id=message.chat.id,
                           sticker=r"CAACAgEAAxkBAAEJuKhktalkP37uDW8eDmlS1GxFzUpBwwACKAEAAjgOghEjsrbXRh3sRi8E",
                           reply_markup=kb_client_registration_name)
    await FSMRegistration.phone.set()


# получаем второй номер телефона
#@dp.message_handler(content_types=ContentType.CONTACT, state=FSMRegistration.phone2)
#@dp.message_handler(lambda message: func_for_valid_phone_number(message.text), state=FSMRegistration.phone2)
async def cm_phone2_registration(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        await bot.send_sticker(chat_id=message.chat.id,
                               sticker=r"CAACAgEAAxkBAAEJuK5ktatlJaluPPwr6kzO98YVwqiqawAC_wADOA6CEct71ndrpd51LwQ",
                               reply_markup=kb_client_registration)
        if message.text is None:

            if str(message.contact.phone_number).startswith("+"):
                data['phone2'] = message.contact.phone_number
            else:
                data['phone2'] = "+" + str(message.contact.phone_number)

        else:
            if message.text.startswith("8"):
                message.text = "+7" + message.text[1:]
            data['phone2'] = "+" + str(phonenumbers.parse(message.text).country_code) + \
                             str(phonenumbers.parse(message.text).national_number)

        asyncio.create_task(
            delete_messages(message.chat.id, data['message_id_start']['message_id']+1, message.message_id, 10, 2))
        await asyncio.sleep(1.3)
        data['message_back']["comment_courier"] = data['message_id_start'] = await message.answer(text=f"Укажите адрес")
        asyncio.create_task(phone2_send_messages(data['message_id_start']))
        await FSMRegistration.address.set()


# получаем неверный второй номер телефона
#@dp.message_handler(content_types=[types.ContentType.ANY], state=FSMRegistration.phone2)
async def cm_phone2_wrong_registration(message: types.Message, state: FSMContext):
    await bot.send_sticker(chat_id=message.chat.id,
                           sticker=r"CAACAgEAAxkBAAEJuLBktbFiUkIgTMwqy86kHA7A5yuFhgACGgEAAjgOghG-CmKJFmOt7C8E")
    await message.answer(text=f"Неверные данные, внимательно прочитайте, как нужно отправить контакт:"
                              f"\n_Нажмите на скрепку📎 снизу\n"
                              f"Затем в разделе 'Contact'👤 выберите человека, которому нужно доставить букет_"
                              f"или введите вручную номер",
                         parse_mode="Markdown", reply_markup=kb_client_registration)
    await FSMRegistration.phone2.set()



# получаем адрес доставки
#@dp.message_handler(content_types=[types.ContentType.ANY], state=FSMRegistration.address)
async def cm_address_registration(message: types.Message, state: FSMContext):
    list_address_correctness_check = address_correctness_check(message=message)
    if list_address_correctness_check[0]:
        await bot.send_sticker(chat_id=message.chat.id,
                               sticker=r"CAACAgEAAxkBAAEJuMlktbRjy-D6k7ArJzVdctBKNmZE-AACJQEAAjgOghHn2fMsEB--jy8E")

        await FSMRegistration.comment_courier.set()
        async with state.proxy() as data:
            data['address_lat'] = list_address_correctness_check[3]
            data['address_lon'] = list_address_correctness_check[2]
            data['address'] = list_address_correctness_check[1]
            asyncio.create_task(
                delete_messages(message.chat.id, data['message_id_start']['message_id']+1, message.message_id, 5, 2))

            data['message_back']["comment_collector"] = \
                await message.answer(text=f"Отлично, ваш адрес: _"
                                          f"{data['address']}_\nОтпрвьте нам информацию для курьера🛵",
                                     parse_mode="Markdown", reply_markup=kb_client_registration_comment)
            data['message_id_start'] = await message.answer(text=f"_Например: за 10 минут до доставки позвонить,"
                                                                 f" этаж 10, домофон В15_", parse_mode="Markdown")
            data['dostavista_start_time'] = time.time()
            available_points = data['available_points']

        task = asyncio.create_task(
                calculate_price_dostavista(lat=list_address_correctness_check[3], lon=list_address_correctness_check[2],
                                           address=list_address_correctness_check[1],
                                           vehicle_type_id=6, available_points=available_points))
        global t
        t[message.chat.id] = task
        result_calculate_price_dostavista = await task
        async with state.proxy() as data:
            data["result_calculate_price_dostavista"] = result_calculate_price_dostavista
            data['time_when_get_price_dostavista'] = time.time()
        if result_calculate_price_dostavista['tomorrow'] == False:
            return
        else:
            task_dostavista = asyncio.create_task(control_time_dostavista(message, state))
            global t_dostavista
            t_dostavista[message.chat.id] = task_dostavista

    else:
        await bot.send_sticker(chat_id=message.chat.id,
                               sticker=r"CAACAgEAAxkBAAEJuMVktbNOWyY9QlS8ikqAr5LjMTwVeAACJwEAAjgOghHEPF8s8YAY0i8E")
        await message.answer(text=f"Неверные данные. {list_address_correctness_check[1]}{list_address_correctness_check[2]}")
        await message.answer(text=f"Внимательно прочитайте, как нужно отправить адрес"
                                  f"\n_Нажмите на скрепку📎 снизу\n"
                                  f"Затем выберите в разделе 'Location'📍 нужный адрес для доставки_ "
                                  f"или введите адрес вручную",
                             parse_mode="Markdown", reply_markup=kb_client_registration)
        await FSMRegistration.address.set()



# получаем коммент для курьера
#@dp.message_handler(state=FSMRegistration.comment_courier)
async def cm_comment_courier_registration(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if message.text == "Пропустить":
            data['comment_courier'] = None
        else:
            data['comment_courier'] = message.text

        data['message_back']["way_of_delivery"] = \
            await message.answer(text=f"Чтобы все прошло идеально, оставьте пожелания для сбощиков📦",
                                 reply_markup=kb_client_registration_comment)
        asyncio.create_task(
            delete_messages(message.chat.id, data['message_id_start']['message_id'], message.message_id, 0, 0))
        data['message_id_start'] = await message.answer(text=f"_Например: к упаковке добавить записку_",
                                                        parse_mode="Markdown")
        await FSMRegistration.comment_collector.set()



# получаем коммент для сбощика и формируем способы доставки
#@dp.message_handler(state=FSMRegistration.comment_collector)
async def cm_comment_collector_registration(message: types.Message, state: FSMContext):
    await FSMRegistration.way_of_delivery.set()
    async with state.proxy() as data:
        data["counter_way_of_delivery"] = False
        data["message_id_comment_collector"] = message.message_id
        asyncio.create_task(
            delete_messages(message.chat.id, data['message_id_start']['message_id'], message.message_id, 0, 0))

        data['message_id_start'] = \
            await message.answer(text=f"Подождите немного, пожалуйста, мы считаем стоимость доставки",
                                 reply_markup=kb_client_registration)
        await bot.send_sticker(chat_id=message.chat.id,
                               sticker=r"CAACAgEAAxkBAAEJuMtktbSM73H5cbOLlWW8E-_83hFHHQACHgEAAjgOghFGWGjXaYZe_S8E")
        if message.text == "Пропустить":
            data['comment_collector'] = None
        else:
            data['comment_collector'] = message.text
        task = asyncio.create_task(
            calculate_price_yandex(lat=data['address_lat'], lon=data['address_lon'], address=data['address'],
                                   available_points=data['available_points'],
                                   phone_client=data["phone2"], name_client=data['name_real'],
                                   comment_client=data["comment_courier"]))
    result_calculate_price_yandex = await task

    await asyncio.sleep(2)
    counter = 0
    while True:
        try:
            if counter > 60:
                raise TimeError

            current_state = await state.get_state()
            if current_state[16:] != "way_of_delivery":
                return

            async with state.proxy() as data:
                if data['result_calculate_price_dostavista']['today'] == False:
                   min_price_today = False
                   start_time_today = None

                else:
                    min_price_today = round(min([item[0] for item in
                                                 data['result_calculate_price_dostavista']['today'].values()]))
                    start_time_today = (datetime.strptime(next(iter(
                        data["result_calculate_price_dostavista"]["today"].keys())), "%H:%M") +
                                        timedelta(hours=2)).strftime("%H:%M")

                if result_calculate_price_yandex[0] == "False":
                    price_yandex = False

                else:
                    price_yandex = round(result_calculate_price_yandex[0])

                data['result_calculate_price_yandex'] = result_calculate_price_yandex
                min_price_tommorow = round(min([item[0] for item in
                                                data['result_calculate_price_dostavista']['tomorrow'].values()]))

                time_when_get_price_dostavista = data['time_when_get_price_dostavista']
                break

        except TimeError:
            await state.finish()
            await message.answer("Приносим свои извинения. Что-то пошло не так, перезапустите бота /start",
                                 reply_markup=kb_client)
            return

        except:
            await bot.send_chat_action(message.chat.id, ChatActions.TYPING)
            await asyncio.sleep(1.5)
            counter += 1

    asyncio.create_task(delete_messages(message.chat.id, message.message_id+1, message.message_id + 3, 0, 0))
    global t_dostavista
    if message.chat.id in t_dostavista:
        t_dostavista.pop(message.chat.id).cancel()

    current_state = await state.get_state()
    if current_state[16:] != "way_of_delivery":
        return

    # выводит варианты способов доставки
    asyncio.create_task(
        func_send_way_delivery(message, state, price_yandex, min_price_today, min_price_tommorow, start_time_today))

    #запускаем контроль за временим доставки
    global t_yandex
    if message.chat.id in t_yandex:
        t_yandex.pop(message.chat.id).cancel()
    task_yandex = asyncio.create_task(
        control_time_yandex(message, state, time_when_get_price_dostavista, FSMRegistration.way_of_delivery))
    t_yandex[message.chat.id] = task_yandex



######ловим варианты доставки
#@dp.callback_query_handler(
    #lambda x: x.data and (x.data.startswith('Express') or x.data.startswith('Today') or x.data.startswith('tomorrow')),
    #state=FSMRegistration.way_of_delivery)
async def cm_way_of_delivery_registration(callback: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data["counter_way_of_delivery"] = True
        match callback.data:
            case 'Express':
                await callback.answer()
                data['way_of_delivery'] = callback.data
                data["price_delivery_final"] = round(data['result_calculate_price_yandex'][0])

                # формируе описание заказа
                description = f'Ваш 📞: {data["phone"]} Получателя 📞: {data["phone2"]} Адрес: {data["address"]}' \
                              f' Время: ⚡️️как можно ️быстрее'
                comment_courier = "Нет инф. для курьера"
                comment_collector = "Нет инф. для сбощика"
                if data["comment_courier"] != None:
                    if (len(description) > 155 and len(data["comment_courier"]) > 45) or len(data["comment_courier"]) > 60:
                        comment_courier = f'Для курьера: {data["comment_courier"][:55]}...'
                        description = f'{description} {comment_courier}'
                    else:
                        comment_courier = f'Для курьера: {data["comment_courier"]}'
                        description = f'{description} {comment_courier}'
                if data["comment_collector"] != None:
                    comment_collector = f'Для сборщика: {data["comment_collector"][:237 - len(description)]}...'

                await bot.send_invoice(
                    chat_id=callback.message.chat.id,
                    title=f'{data["name"]} {data["quantity"]}шт.',
                    description='Ваш 📞: ' + data["phone"] +
                                '\nПолучателя 📞: ' + data["phone2"] +
                                '\nАдрес: ' + data["address"] +
                                '\nВремя: ⚡️️как можно быстрее' +
                                '\n' + comment_courier +
                                '\n' + comment_collector,
                    payload='Payment through a bot',
                    provider_token="401643678:TEST:56720fb5-8502-455b-bf0a-eff6e5509273",
                    currency='rub',
                    prices=[
                        types.LabeledPrice(
                            label='Букет',
                            amount=(data['full_cost_without_delivery']-data['packaging_price'])*100
                        ),
                        types.LabeledPrice(
                            label='Упаковка',
                            amount=data['packaging_price']*100
                        ),
                        types.LabeledPrice(
                            label='Доставка',
                            amount=data["price_delivery_final"] * 100
                        ),
                        types.LabeledPrice(
                            label='Скидка',
                            amount=-50000
                        )
                    ],
                    provider_data=None,
                    photo_url='https://ic.wampi.ru/2023/07/21/IMG_6324.jpg',
                    need_name=False,
                    need_phone_number=False,
                    need_email=False,
                    need_shipping_address=False,
                    send_phone_number_to_provider=False,
                    send_email_to_provider=False,
                    is_flexible=False,
                    disable_notification=False,
                    protect_content=False,
                    reply_to_message_id=None,
                    allow_sending_without_reply=True,
                    reply_markup=kb_client_pay_inline
                )
                await FSMRegistration.payment.set()
                asyncio.create_task(
                    delete_messages(callback.message.chat.id, data['message_id_buy'],
                                    callback.message.message_id + 1, 0, 0))

            case 'Today' | 'Today back':
                keyboard = types.InlineKeyboardMarkup()
                half_length = round(len(data["result_calculate_price_dostavista"]["today"]) / 2)
                if half_length < 4:
                    half_length = len(data["result_calculate_price_dostavista"]["today"])
                simbol = ["◑", "◐", "◒", "◓", "◑", "◐"]
                counter = 0
                for key, value in data["result_calculate_price_dostavista"]["today"].items():
                    if counter >= half_length:
                        break
                    else:
                        start_time = (datetime.strptime(key, "%H:%M") + timedelta(hours=2)).strftime("%H:%M")
                        end_time = (datetime.strptime(key, "%H:%M") + timedelta(hours=3)).strftime("%H:%M")
                        keyboard.add(types.InlineKeyboardButton(
                            text=f"{simbol[counter]} {start_time}-{end_time} за {round(value[0])}₽",
                            callback_data=f"Today {start_time}-{end_time}"))
                        counter += 1

                if half_length >= 4:
                    keyboard.add(types.InlineKeyboardButton(text=f"еще варианты ⇨", callback_data=f"Today more"))
                await callback.message.edit_text("Выберите удобное время\n для доставки на сегодня",
                                                 reply_markup=keyboard)
                await callback.answer()

            case 'Today more':
                keyboard = types.InlineKeyboardMarkup()
                half_length = len(data["result_calculate_price_dostavista"]["today"]) / 2
                simbol = ["◑", "◐", "◒", "◓", "◑", "◐", "◒", "◓", "◑", "◐", "◒", "◓"]
                counter = 0
                for key, value in data["result_calculate_price_dostavista"]["today"].items():
                    if counter >= half_length:
                        start_time = (datetime.strptime(key, "%H:%M") + timedelta(hours=2)).strftime("%H:%M")
                        end_time = (datetime.strptime(key, "%H:%M") + timedelta(hours=3)).strftime("%H:%M")
                        keyboard.add(types.InlineKeyboardButton(
                            text=f"{simbol[counter]} {start_time}-{end_time} за {round(value[0])}₽",
                            callback_data=f"Today {start_time}-{end_time}"))
                    counter += 1

                keyboard.add(types.InlineKeyboardButton(text=f"⇦ назад", callback_data=f"Today back"))
                await callback.message.edit_text("Выберите удобное время\n для доставки на сегодня",
                                                 reply_markup=keyboard)
                await callback.answer()

            case 'tomorrow' | 'tomorrow back':
                keyboard = types.InlineKeyboardMarkup()
                half_length = round(len(data["result_calculate_price_dostavista"]["tomorrow"]) / 2)
                simbol = ["◑", "◐", "◒", "◓", "◑", "◐"]
                counter = 0
                for key, value in data["result_calculate_price_dostavista"]["tomorrow"].items():
                    if counter >= half_length:
                        break
                    else:
                        start_time = (datetime.strptime(key, "%H:%M") + timedelta(hours=2)).strftime("%H:%M")
                        end_time = (datetime.strptime(key, "%H:%M") + timedelta(hours=3)).strftime("%H:%M")
                        keyboard.add(types.InlineKeyboardButton(
                            text=f"{simbol[counter]} {start_time}-{end_time} за {round(value[0])}₽",
                            callback_data=f"tomorrow {start_time}-{end_time}"))
                        counter += 1

                keyboard.add(types.InlineKeyboardButton(text=f"еще варианты ⇨", callback_data=f"tomorrow more"))
                await callback.message.edit_text("Выберите удобное время\n для доставки на завтра",
                                                 reply_markup=keyboard)
                await callback.answer()

            case 'tomorrow more':
                keyboard = types.InlineKeyboardMarkup()
                half_length = len(data["result_calculate_price_dostavista"]["tomorrow"]) / 2
                simbol = ["◑", "◐", "◒", "◓", "◑", "◐", "◒", "◓", "◑", "◐", "◒", "◓"]
                counter = 0
                for key, value in data["result_calculate_price_dostavista"]["tomorrow"].items():
                    if counter >= half_length:
                        start_time = (datetime.strptime(key, "%H:%M") + timedelta(hours=2)).strftime("%H:%M")
                        end_time = (datetime.strptime(key, "%H:%M") + timedelta(hours=3)).strftime("%H:%M")
                        keyboard.add(types.InlineKeyboardButton(
                            text=f"{simbol[counter]} {start_time}-{end_time} за {round(value[0])}₽",
                            callback_data=f"tomorrow {start_time}-{end_time}"))
                    counter += 1

                keyboard.add(types.InlineKeyboardButton(text=f"⇦ назад", callback_data=f"tomorrow back"))
                await callback.message.edit_text("Выберите удобное время\n для доставки на завтра", reply_markup=keyboard)
                await callback.answer()

            case _:
                dict_for_way_of_delivery = {"Today": "сегодня", "tomorrow": "завтра"}
                data['way_of_delivery'] = callback.data.split()[0]
                data['time_delivery'] = callback.data.split()[1][0:12]
                if data['way_of_delivery'] == 'Today':
                    start_time = (datetime.strptime(data['time_delivery'][:5], "%H:%M") -
                                  timedelta(hours=2)).strftime("%H:%M")
                    data["price_delivery_final"] = \
                        round(data["result_calculate_price_dostavista"]["today"][start_time][0])
                else:
                    start_time = (datetime.strptime(data['time_delivery'][:5], "%H:%M") -
                                  timedelta(hours=2)).strftime("%H:%M")
                    data["price_delivery_final"] = \
                        round(data["result_calculate_price_dostavista"]["tomorrow"][start_time][0])

                #формируе описание заказа
                description = f'Ваш 📞: {data["phone"]} Получателя 📞: {data["phone2"]} Адрес: {data["address"]} ' \
                              f'Время: {dict_for_way_of_delivery[callback.data.split()[0]]} {data["time_delivery"]} '
                comment_courier = "Нет инф. для курьера."
                comment_collector = "\nНет инф. для сбощика."
                if data["comment_courier"] != None:
                    if (len(description) > 155 and len(data["comment_courier"]) > 45) or len(data["comment_courier"]) > 60:
                        comment_courier = f'Для курьера: {data["comment_courier"][:55]}...'
                        description = f'{description} {comment_courier}'
                    else:
                        comment_courier = f'Для курьера: {data["comment_courier"]}'
                        description = f'{description} {comment_courier}'
                if data["comment_collector"] != None:
                    comment_collector = f'Для сборщика: {data["comment_collector"][:237-len(description)]}...'

                await bot.send_invoice(
                    chat_id=callback.message.chat.id,
                    title=f'{data["name"]} {data["quantity"]}шт.',
                    description='Ваш 📞: ' + data["phone"] +
                                '\nПолучателя 📞: ' + data["phone2"] +
                                '\nАдрес: ' + data["address"] +
                                '\nВремя: ' + dict_for_way_of_delivery[callback.data.split()[0]] + ' ' + data["time_delivery"] + '.'
                                '\n' + comment_courier +
                                '\n' + comment_collector,
                    payload='Payment through a bot',
                    provider_token="401643678:TEST:56720fb5-8502-455b-bf0a-eff6e5509273",
                    currency='rub',
                    prices=[
                        types.LabeledPrice(
                            label='Букет',
                            amount=(data['full_cost_without_delivery']-data['packaging_price'])*100
                        ),
                        types.LabeledPrice(
                            label='Упаковка',
                            amount=data['packaging_price']*100
                        ),
                        types.LabeledPrice(
                            label='Доставка',
                            amount=data["price_delivery_final"]*100
                        ),
                        types.LabeledPrice(
                            label='Скидка',
                            amount=-50000
                        )
                    ],
                    provider_data=None,
                    photo_url='https://ic.wampi.ru/2023/07/21/IMG_6324.jpg',
                    need_name=False,
                    need_phone_number=False,
                    need_email=False,
                    need_shipping_address=False,
                    send_phone_number_to_provider=False,
                    send_email_to_provider=False,
                    is_flexible=False,
                    disable_notification=False,
                    protect_content=False,
                    reply_to_message_id=None,
                    allow_sending_without_reply=True,
                    reply_markup=kb_client_pay_inline
                )

                await callback.answer()
                await FSMRegistration.payment.set()
                asyncio.create_task(
                    delete_messages(callback.message.chat.id, data['message_id_buy'],
                                    callback.message.message_id + 1, 0, 0))



#@dp.callback_query_handler(lambda c: c.data == 'stop_pay', state=FSMRegistration.payment)
async def cancellation_of_payment(callback: types.CallbackQuery, state: FSMContext):
    asyncio.create_task(
            delete_messages(callback.message.chat.id, callback.message.message_id, callback.message.message_id + 1, 0, 0))
    await callback.answer()
    await callback.message.answer('OK', reply_markup=kb_client)
    global t_order, t_yandex
    async with state.proxy() as data:
        if data['message_id_start'].chat.id in t_order:
            t_order.pop(data['message_id_start'].chat.id).cancel()
        if data['message_id_start'].chat.id in t_yandex:
            t_yandex.pop(data['message_id_start'].chat.id).cancel()
        try:
            asyncio.create_task(cancellation_order(id=data['result_calculate_price_yandex'][2]))
        except:
            pass
    await state.finish()


#@dp.pre_checkout_query_handler(lambda query: True, state=FSMRegistration.payment)
async def pre_checkout_query(pre_checkout_q: types.PreCheckoutQuery, state: FSMContext):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)
    global t_order, t_yandex
    async with state.proxy() as data:
        if data['message_id_start'].chat.id in t_order:
            t_order.pop(data['message_id_start'].chat.id).cancel()
        if data['message_id_start'].chat.id in t_yandex:
            t_yandex.pop(data['message_id_start'].chat.id).cancel()


#@dp.pre_checkout_query_handler(lambda query: True, state="*")
async def pre_checkout_query_false(pre_checkout_q: types.PreCheckoutQuery, state: FSMContext):
  await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=False,
                                      error_message="к сожалению, изменилась стоимость доставки")



# successful payment
#@dp.message_handler(content_types=types.ContentType.SUCCESSFUL_PAYMENT, state=FSMRegistration.payment)
async def successful_payment(message: types.Message, state: FSMContext):
    await FSMRegistration.payment_success.set()
    async with state.proxy() as data:
        global t_order
        if data['message_id_start'].chat.id in t_order:
            t_order.pop(data['message_id_start'].chat.id).cancel()
    asyncio.create_task(
        delete_messages(message.chat.id, message.message_id-1, message.message_id, 0, 0))
    async with state.proxy() as data:
        if data['way_of_delivery'] == "Express":
            time = 'Время: ⚡️️как можно быстрее'
            try:
                number_order = data['result_calculate_price_yandex'][2]
                #подтерждаем заказ в yandex # asyncio.create_task(confirmation_order(id=number_order))
            except:
                pass

        else:
            try:
                number_order = "u4884u494u489u984u89484848"
                asyncio.create_task(cancellation_order(id=data['result_calculate_price_yandex'][2]))
            except:
                pass

            dict_for_way_of_delivery = {"Today": "сегодня", "tomorrow": "завтра"}
            time = f'Время: {dict_for_way_of_delivery[data["way_of_delivery"]]} {data["time_delivery"]}'

        comment_courier = "Нет инф. для курьера"
        comment_collector = "Нет инф. для сбощика"
        if data["comment_courier"] != None:
            comment_courier = f'Для курьера: {data["comment_courier"]}'
        if data["comment_collector"] != None:
            comment_collector = f'Для курьера: {data["comment_collector"]}'

        description = 'Номер заказа №' + number_order + '\n' + \
                      data["name"] + ' ' + str(data["quantity"]) + 'шт.\n' + \
                      'Стоимость: ' + str(data['full_cost_without_delivery'] - 500 + data["price_delivery_final"]) + '₽\n' +\
                      'Ваш 📞: ' + data["phone"] + \
                      '\nПолучателя 📞: ' + data["phone2"] +\
                      '\nАдрес: ' + data["address"] +\
                      '\n' + time + \
                      '\nСсылка на доставку: https://yandex.ru/search/?text=номер+символ&lr=213&search_source=yaru_desktop_common' + \
                      '\n' + comment_courier + \
                      '\n' + comment_collector
        print(data)
    msg = await bot.send_message(message.chat.id, text=description, reply_markup=kb_client_order_inline)
    await bot.pin_chat_message(chat_id=msg.chat.id, message_id=msg.message_id)
    await state.finish()



# Регистрируем хендлеры
def register_handlers_clients(dp: Dispatcher):
    dp.register_message_handler(commands_start, commands=['start', 'help'])
    dp.register_message_handler(commands_client, IDFilter(admins_list + collector_list),  commands=['client'])
    dp.register_message_handler(commands_menu, commands=['Меню'])
    dp.register_message_handler(commands_help, commands=['поддержка'])


    dp.register_message_handler(cm_start_registration, commands=['Купить'], state=None)
    dp.register_callback_query_handler(cm_confirmation_registration, lambda c: c.data in ['Yes', 'No'],
                                       state=FSMRegistration.name_tg)
    dp.register_message_handler(cancel_handler, filters.Text(equals='отмена ✕', ignore_case=True), state="*")
    dp.register_message_handler(back_handler, filters.Text(equals='назад ⤴', ignore_case=True), state="*")
    dp.register_message_handler(cm_name_registration, state=FSMRegistration.name_real)
    dp.register_message_handler(cm_phone_registration, content_types=ContentType.CONTACT, state=FSMRegistration.phone)
    dp.register_message_handler(cm_phone_registration, lambda message: func_for_valid_phone_number(message.text),
                                state=FSMRegistration.phone)
    dp.register_message_handler(cm_phone_wrong_registration, content_types=[types.ContentType.ANY],
                                state=FSMRegistration.phone)

    dp.register_message_handler(cm_phone2_registration, content_types=ContentType.CONTACT, state=FSMRegistration.phone2)
    dp.register_message_handler(cm_phone2_registration, lambda message: func_for_valid_phone_number(message.text),
                                state=FSMRegistration.phone2)
    dp.register_message_handler(cm_phone2_wrong_registration, content_types=[types.ContentType.ANY],
                                state=FSMRegistration.phone2)
    dp.register_message_handler(cm_address_registration, content_types=[types.ContentType.ANY],
                                state=FSMRegistration.address)
    dp.register_message_handler(cm_comment_courier_registration, state=FSMRegistration.comment_courier)
    dp.register_message_handler(cm_comment_collector_registration, state=FSMRegistration.comment_collector)
    dp.register_callback_query_handler(cm_way_of_delivery_registration, lambda x: x.data and (
                        x.data.startswith('Express') or x.data.startswith('Today') or x.data.startswith('tomorrow')),
                        state=FSMRegistration.way_of_delivery)
    dp.register_callback_query_handler(cancellation_of_payment, lambda c: c.data == 'stop_pay',
                                       state=FSMRegistration.payment)
    dp.register_pre_checkout_query_handler(pre_checkout_query, lambda query: True, state=FSMRegistration.payment)
    dp.register_pre_checkout_query_handler(pre_checkout_query_false, lambda query: True, state="*")
    dp.register_message_handler(successful_payment, content_types=types.ContentType.SUCCESSFUL_PAYMENT,
                                state=FSMRegistration.payment)





