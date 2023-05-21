import asyncio
import requests
import datetime

from create_bot import dp, bot
from aiogram import types, Dispatcher
from data_base.sqlite_dp import sql_read_name
from aiogram.types import BotCommandScopeChat


async def find_best_way(destination: str):
    """
    функция, которая вычисляет наилучшее время и точку для принятия заказа
    :param destination:
    :return отсортированный по time словарь dict = {'origin1': [time, distance], 'origin2': [time, distance], 'origin3': [time, distance]}
:
    """
    # Ключ API Яндекс.Маршрутов
    api_key = 'e2cbc913-9374-4946-b0d9-702861816621'

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
        time = data['rows'][0]['elements'][0]['duration']['value']
        distance = data['rows'][0]['elements'][0]['distance']['value']
        origin_dict[origin] = [time, distance]

    return dict(sorted(origin_dict.items(), key=lambda x: x[1][0]))


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
        await asyncio.sleep(time_circle)
        await bot.delete_message(chat_id=chat_id, message_id=i)


#@dp.message_handler()
async def echo_send(message: types.Message):
    if message.text == "Привет" :
        await asyncio.sleep(5)
        await message.answer(message.from_user.id)
    elif message.text == "инфа" :
        await message.answer(message.text)
    else:
        await message.answer(message.text)
    #await message.reply(message.text)
    #await bot.send_message(message.from_user.id, message.text)

def register_handlers_other(dp : Dispatcher):
    dp.register_message_handler(echo_send)


# Устанавливаем команды для удаления для конкретного чата (ID чата: 1234567890)
async def set_admin_dell_commands(message: types.Message):
    read = await sql_read_name()
    commands = []
    for i, command in enumerate(read):
        commands.append(types.BotCommand(command=command[1], description=command[0]))
    scope = BotCommandScopeChat(chat_id=message.chat.id)
    await bot.set_my_commands(commands=commands, scope=scope)


admins_list = [310251240, 421278460, 450091492]
async def set_admin_commands(message: types.Message):
    bot_commands = [
        types.BotCommand(command="/start", description="вернуться в клиенский интерфейс"),
        types.BotCommand(command="/admin", description="admin интерфейс"),
        types.BotCommand(command="/export_data", description="получить exel таблицу данных")
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
    now = datetime.datetime.now() - datetime.timedelta(hours=4)
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

    rounded_hour = now.replace(hour=10, minute=0, second=0, microsecond=0)
    dt = now.replace(hour=22, minute=0, second=0, microsecond=0)
    list_tomorrow = []

    while rounded_hour < dt:
        list_tomorrow.append(
            f"{rounded_hour.strftime('%H:%M')} - {(rounded_hour + datetime.timedelta(hours=2)).strftime('%H:%M')}")
        rounded_hour += datetime.timedelta(hours=2)

    list_for_return.append(list_tomorrow)

    return list_for_return
