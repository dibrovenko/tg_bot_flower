import asyncio
import random
import time
import os
from dotenv import load_dotenv, find_dotenv
import requests
import datetime
from datetime import datetime, timedelta
import phonenumbers

from aiogram.dispatcher import FSMContext
from create_bot import dp, bot
from aiogram import types, Dispatcher
from data_base.sqlite_dp import sql_read_name
from aiogram.types import BotCommandScopeChat, InlineKeyboardButton, InlineKeyboardMarkup

from dostavista.price import calculate_price_dostavista
from keyboards import kb_client_registration, kb_client
from yandex.calculate_price_yandex import calculate_price_yandex
from yandex.cancellation_order import cancellation_order


#@dp.message_handler()
async def echo_send(message: types.Message):
    if message.text == "Привет":
        await asyncio.sleep(5)
        await message.answer(message.from_user.id)
    elif message.text == "инфа":
        await message.answer(message.text)
    else:
        await message.answer(message.text)
    #await message.reply(message.text)
    #await bot.send_message(message.from_user.id, message.text)

def register_handlers_other(dp : Dispatcher):
    dp.register_message_handler(echo_send)



async def delete_messages(chat_id, start, end, time: float, time_circle: float):
    """
    Удаляет промежуток сообщений за нужное время
    :param chat_id:
    :param start:
    :param end:
    :param time:
    :param time_circle:
    """
    await asyncio.sleep(time)
    for i in range(start, end):
        try:
            await asyncio.sleep(time_circle)
            await bot.delete_message(chat_id=chat_id, message_id=i)
        except:
            pass


async def find_best_way(destination: str):
    """
    функция, которая вычисляет наилучшее время и точку для принятия заказа
    :param destination:
    :return отсортированный по time словарь dict = {'origin1': [time, distance], 'origin2': [time, distance], 'origin3': [time, distance]}
:
    """
    # Ключ API Яндекс.Маршрутов
    load_dotenv(find_dotenv())
    api_key = os.getenv('api_key_yandex_routes')

    # Координаты точек складов
    origin1 = '55.601010,37.471102'  # Москва, поселение Сосенское, Калужское шоссе, 22-й километр, 10
    origin2 = '55.738667,37.658239'  # г. Москва, переулок Маяковского, дом 10, строение 6
    origin3 = '55.860984,37.482708'  # Смольная улица, 24Гс6

    origin_dict = dict()
    origin_list = [origin1, origin2, origin3]

    for origin in origin_list:
        data = requests.get(
            f'https://api.routing.yandex.net/v2/distancematrix?origins={origin}&destinations={destination}&'
            f'mode=driving&departure_time={int((datetime.datetime.now() + datetime.timedelta(minutes=20)).timestamp())}&'
            f'avoid_tolls=true&apikey={api_key}').json()
        try:
            time = data['rows'][0]['elements'][0]['duration']['value']
            distance = data['rows'][0]['elements'][0]['distance']['value']
            origin_dict[origin] = [time, distance]
        except:
            origin_dict_sorted = {
                origin1: [10, 2500],
                origin2: [20, 3600],
                origin3: [30, 4700]
            }
            return origin_dict_sorted


    return dict(sorted(origin_dict.items(), key=lambda x: x[1][0]))



# Устанавливаем команды для удаления для конкретного чата (ID чата: 1234567890)
async def set_admin_dell_commands(message: types.Message):
    read = await sql_read_name()
    commands = []
    for i, command in enumerate(read):
        commands.append(types.BotCommand(command=command[1], description=command[0]))
    scope = BotCommandScopeChat(chat_id=message.chat.id)
    await bot.set_my_commands(commands=commands, scope=scope)



async def set_admin_commands(message: types.Message):
    bot_commands = [
        types.BotCommand(command="/start", description="перезапустить бота"),
        types.BotCommand(command="/client", description="клиенский интерфейс"),
        types.BotCommand(command="/collector", description="интерфейс сборщика"),
        types.BotCommand(command="/export_data", description="получить exel таблицу данных")
    ]
    scope = BotCommandScopeChat(chat_id=message.chat.id)
    await bot.set_my_commands(bot_commands, scope=scope)


async def set_collectors_commands(message: types.Message):
    bot_commands = [
        types.BotCommand(command="/start", description="перезапустить бота"),
        types.BotCommand(command="/client", description="клиенский интерфейс"),
        types.BotCommand(command="/admin", description="admin интерфейс"),
    ]
    scope = BotCommandScopeChat(chat_id=message.chat.id)
    await bot.set_my_commands(bot_commands, scope=scope)


async def set_client_commands():
    bot_commands = [
        types.BotCommand(command="/start", description="перезапустить бота"),
        types.BotCommand(command="/help", description="подсказки"),
        types.BotCommand(command="/info", description="получить информацию")
    ]
    await bot.set_my_commands(bot_commands)


async def set_client_commands2(message: types.Message):
    bot_commands = [
        types.BotCommand(command="/start", description="перезапустить бота"),
        types.BotCommand(command="/admin", description="admin интерфейс"),
        types.BotCommand(command="/collector", description="интерфейс сборщика"),
    ]
    scope = BotCommandScopeChat(chat_id=message.chat.id)
    await bot.set_my_commands(bot_commands, scope=scope)


def check_valid_text(text):
    """ Проверяет, что текст состоит только из не заглавных английских букв, цифр и символа _"""
    return all(c.islower() or c.isdigit() or c == '_' for c in text)


def delivery_time():
    """
    функция, кото рая возращает список для формирования времени для доставки
    :rtype: object
    :return: "[Express, Today, [time interval for today], [time interval for tomorrow], Вот два примера:"
      "[True, False, [], ['10:00 - 12:00', '12:00 - 14:00', '14:00 - 16:00', '16:00 - 18:00', '18:00 - 20:00', '20:00 - 22:00']]"
      "[True, True, ['20:00 - 21:00', '21:00 - 22:00'], ['10:00 - 12:00', '12:00 - 14:00', '14:00 - 16:00', '16:00 - 18:00', '18:00 - 20:00', '20:00 - 22:00']]"
    """
    now = datetime.datetime.now() - datetime.timedelta(hours=1)
    print(now)
    start_time_of_work = now.replace(hour=10, minute=0, second=0, microsecond=0)
    end_time_of_work = now.replace(hour=21, minute=0, second=0, microsecond=0)
    end_time_of_work_ordinary_deliver = now.replace(hour=19, minute=0, second=0, microsecond=0)
    list_for_return = []

    if start_time_of_work <= now <= end_time_of_work:
        list_for_return.append(True)

        if start_time_of_work <= now <= end_time_of_work_ordinary_deliver:
            list_for_return.append(True)
            rounded_hour = now.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=3)
            dt = now.replace(hour=22, minute=0, second=0, microsecond=0)
            list_today = []

            while rounded_hour < dt:
                list_today.append(
                    f"{rounded_hour.strftime('%H:%M')} - {(rounded_hour + datetime.timedelta(hours=1)).strftime('%H:%M')}")
                rounded_hour += datetime.timedelta(hours=1)
            list_for_return.append(list_today)

        else:
            list_for_return.append(False)
            list_for_return.append([])

    else:
        list_for_return.append(False)
        list_for_return.append([])
        list_for_return.append([])

    rounded_hour = now.replace(hour=10, minute=0, second=0, microsecond=0)
    dt = now.replace(hour=22, minute=0, second=0, microsecond=0)
    list_tomorrow = []

    while rounded_hour < dt:
        list_tomorrow.append(
            f"{rounded_hour.strftime('%H:%M')} - {(rounded_hour + datetime.timedelta(hours=2)).strftime('%H:%M')}")
        rounded_hour += datetime.timedelta(hours=2)

    list_for_return.append(list_tomorrow)

    return list_for_return


async def phone_send_messages(message: types.Message):
    try:
        await bot.send_sticker(chat_id=message.chat.id,
                               sticker=r"CAACAgEAAxkBAAEJuEhktY0N0UeoJaRp-QTxzI5KWBRWLQACFQEAAjgOghGqOtb4EGwFOy8E",
                               reply_markup=kb_client_registration)
        await asyncio.sleep(0.8)
        msg = await bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id,
                                          text=message.text + f"\n_Нажмите на скрепку📎 снизу_", parse_mode="Markdown")
        await asyncio.sleep(0.8)
        await bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id,
                                              text=message.text + f"_\nНажмите на скрепку📎 снизу.\nЗатем в разделе 'Contact'👤 выберите человека, которому нужно доставить букет_ или введите номер вручную", parse_mode="Markdown")
    except:
        return


async def phone2_send_messages(message: types.Message):
    try:
        await asyncio.sleep(0.8)
        msg = await bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id,
                                          text=message.text + f"\n_Нажмите на скрепку📎 снизу_", parse_mode="Markdown")
        await asyncio.sleep(0.8)
        await bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id,
                                              text=message.text + f"_\nНажмите на скрепку📎 снизу \nЗатем в разделе 'Location'📍 выберите нужный адрес для доставки_ или введите адрес вручную", parse_mode="Markdown")
    except:
        return


async def comment_courier_send_messages(message: types.Message):
    await asyncio.sleep(0.2)
    first_message_text = message.text
    text = ": за 10 минут до доставки позвонить, этаж 10, домофон В15"
    typing_speed = 60  # Скорость печати (задержка между символами)
    for word in text.split():
        for i in word:
            await asyncio.sleep(random.uniform(0.01, 0.1) * typing_speed / 100)
            try:
                message = await bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id,
                                                      text=message.text + i)
            except:
                return
    message.text += " "

    first_message_text += "_" + text + "..._"
    await bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id,
                                text=first_message_text, parse_mode="Markdown")


async def comment_collector_send_messages(message: types.Message):
    await asyncio.sleep(0.2)
    first_message_text = message.text
    text = ": к упаковке добавить записку"
    typing_speed = 60  # Скорость печати (задержка между символами)
    for word in text.split():
        for i in word:
            await asyncio.sleep(random.uniform(0.01, 0.1) * typing_speed / 100)
            try:
                message = await bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id,
                                                      text=message.text + i)
            except:
                return
        message.text += " "
    first_message_text += "_" + text + "..._"
    await bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id,
                                text=first_message_text, parse_mode="Markdown")


def func_for_valid_phone_number(my_string_number)->bool:
    if my_string_number.startswith("8"):
        my_string_number = "+7" + my_string_number[1:]
    try:
        return phonenumbers.is_valid_number(phonenumbers.parse(my_string_number))
    except:
        return False


async def func_send_way_delivery(message: types.Message, state: FSMContext, price_yandex, min_price_today,
                                 min_price_tommorow, start_time_today, text=None):
    if text is None:
        text = f"Отлично, осталось выбрать способ доставки:"
        text2 = f"Сейчас уже закрылись наши магазины, но вы можете сделать заказ"
        sticker = r"CAACAgEAAxkBAAEJwLxkuXmCBONjmdCVDBsL8aPRwwoi8QACEwEAAjgOghGMb2aRzBGcWS8E"
    else:
        text2 = text
        sticker = r"CAACAgEAAxkBAAEJ3INkxux-IkU9FKkVaT8_q_dpzQcYzgACEgEAAjgOghHo9UX5qETZii8E"

    async with state.proxy() as data:
        data['message_id_start'] = await bot.send_sticker(chat_id=message.chat.id,
                                                          sticker=sticker,
                                                          reply_markup=kb_client_registration)

        if price_yandex == False and min_price_today != False: #today tommorow
            data['message_back']["way_of_delivery2"] = \
                data['message_id_start'] = await message.answer(text=text, parse_mode="Markdown",
                                                                reply_markup=InlineKeyboardMarkup().
                                                                insert(InlineKeyboardButton(
                                                                    f'🚚Сегодня после {start_time_today} '
                                                                    f'от {min_price_today}₽',
                                                                    callback_data=f"Today")).
                                                                add(InlineKeyboardButton(
                                                                    f'🚛Завтра от {min_price_tommorow}₽',
                                                                    callback_data=f"tomorrow")))

        elif price_yandex != False and min_price_today != False:  #express today tommorow
            data['message_back']["way_of_delivery2"] = \
                data['message_id_start'] = await message.answer(text=text, parse_mode="Markdown",
                                                                reply_markup=InlineKeyboardMarkup().
                                                                insert(InlineKeyboardButton(
                                                                    f'⚡️Express за {price_yandex}₽',
                                                                    callback_data=f"Express")).
                                                                add(InlineKeyboardButton(
                                                                    f'🚚Сегодня после {start_time_today} '
                                                                    f'от {min_price_today}₽',
                                                                    callback_data=f"Today")).
                                                                add(InlineKeyboardButton(
                                                                    f'🚛Завтра от {min_price_tommorow}₽',
                                                                    callback_data=f"tomorrow")))

        elif price_yandex != False and min_price_today == False:  #express tommorow
            data['message_back']["way_of_delivery2"] = \
                data['message_id_start'] = await message.answer(text=text, parse_mode="Markdown",
                                                                reply_markup=InlineKeyboardMarkup().
                                                                insert(InlineKeyboardButton(
                                                                    f'⚡️Express за {price_yandex}₽',
                                                                    callback_data=f"Express")).
                                                                add(InlineKeyboardButton(
                                                                    f'🚛Завтра от {min_price_tommorow}₽',
                                                                    callback_data=f"tomorrow")))

        else:  #tommorow
            data['message_back']["way_of_delivery2"] = \
                data['message_id_start'] = await message.answer(text=text2, parse_mode="Markdown",
                                                                reply_markup=InlineKeyboardMarkup().
                                                                add(InlineKeyboardButton(
                                                                    f'🚛 на завтра от {min_price_tommorow}₽',
                                                                    callback_data=f"tomorrow")))



async def control_time_order(message: types.Message, state: FSMContext):
    try:
        await asyncio.sleep(3600)
        current_state = await state.get_state()
        if current_state is not None:
            async with state.proxy() as data:
                msg = await message.answer('Это магазин, который позволит быстро и дешево купить цветы!',
                                           reply_markup=kb_client)
                asyncio.create_task(
                    delete_messages(message.chat.id, data['message_id_buy'], msg.message_id, 0, 0))

            await state.finish()

    except asyncio.CancelledError:
        print("Асинхронная функция t_order была остановлена")


async def control_time_dostavista(message: types.Message, state: FSMContext):
    try:
        for i in range(1, 4):
            await asyncio.sleep(850)
            current_state = await state.get_state()
            if current_state is not None:
                async with state.proxy() as data:
                    task = asyncio.create_task(
                        calculate_price_dostavista(lat=data['address_lat'],
                                                   lon=data['address_lon'],
                                                   address=data['address'],
                                                   vehicle_type_id=6,
                                                   available_points=data['available_points']))

                result_calculate_price_dostavista = await task
                async with state.proxy() as data:
                    data["result_calculate_price_dostavista"] = result_calculate_price_dostavista

            else:
                return

    except asyncio.CancelledError:
        print("Асинхронная функция control_time_dostavista была остановлена")



async def control_time_yandex(message: types.Message, state: FSMContext, time_when_get_price_dostavista,
                              FSMRegistration_way_of_delivery):
    try:
        if time.time() - time_when_get_price_dostavista > 550:
            await asyncio.sleep(550)
        else:
            await asyncio.sleep(550)

        for i in range(1, 4):
            current_state = await state.get_state()
            if current_state is not None:
                async with state.proxy() as data:
                    task_dostavista = asyncio.create_task(
                        calculate_price_dostavista(lat=data['address_lat'],
                                                   lon=data['address_lon'],
                                                   address=data['address'],
                                                   vehicle_type_id=6,
                                                   available_points=data['available_points']))
                    task_yandex = asyncio.create_task(
                            calculate_price_yandex(lat=data['address_lat'], lon=data['address_lon'],
                                                   address=data['address'],
                                                   available_points=data['available_points'],
                                                   phone_client=data["phone2"], name_client=data['name_real'],
                                                   comment_client=data["comment_courier"]))

                result_calculate_price_yandex = await task_yandex
                result_calculate_price_dostavista = await task_dostavista

                async with state.proxy() as data:
                    try:
                        asyncio.create_task(cancellation_order(id=data['result_calculate_price_yandex'][2]))
                    except:
                        pass

                    data["result_calculate_price_dostavista"] = result_calculate_price_dostavista
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

                current_state = await state.get_state()
                if current_state[16:] in ["way_of_delivery", "payment"]:
                    # выводит варианты способов доставки
                    task_send_way_delivery = asyncio.create_task(
                        func_send_way_delivery(message, state, price_yandex, min_price_today, min_price_tommorow,
                                               start_time_today, text="К сожалению, сейчас уже изменилась доставка"))
                    await FSMRegistration_way_of_delivery.set()
                    await task_send_way_delivery
                    async with state.proxy() as data:
                        asyncio.create_task(
                            delete_messages(message.chat.id, data["message_id_comment_collector"]+3,
                                            data['message_back']["way_of_delivery2"].message_id-1, 0, 0))
                    await asyncio.sleep(550)
                else:
                    return
            else:
                return

        msg = await message.answer('Это магазин, который позволит быстро и дешево купить цветы!',
                                   reply_markup=kb_client)
        asyncio.create_task(
            delete_messages(message.chat.id, data['message_back']["way_of_delivery2"].message_id-1,
                            msg.message_id, 0, 0))
        async with state.proxy() as data:
            try:
                asyncio.create_task(cancellation_order(id=data['result_calculate_price_yandex'][2]))
            except:
                pass
        await state.finish()


    except asyncio.CancelledError:
        print("Асинхронная функция control_time_yandex была остановлена")

    except:
        pass