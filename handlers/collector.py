import asyncio
import re

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext, filters
from aiogram.dispatcher.filters import IDFilter
import os

from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from create_bot import bot
from data_base.sqlite_dp import get_positions_sql, update_positions_sql
from error_decorators.admin import dec_error_mes, dec_error_mes_state
from handlers.other import set_collectors_commands, delete_messages
from keyboards.collector_kb import kb_collector
from parameters import collectors, admins

import logging

# получение пользовательского логгера и установка уровня логирования
py_logger = logging.getLogger(__name__)
py_logger.setLevel(logging.DEBUG)

# настройка обработчика и форматировщика в соответствии с нашими нуждами
log_file = os.path.join(f"log_directory/{__name__}.log")
py_handler = logging.FileHandler(log_file, mode='w')

# py_handler = logging.FileHandler(f"{__name__}.log", mode='w')
py_formatter = logging.Formatter("%(name)s %(asctime)s %(levelname)s %(message)s")

# добавление форматировщика к обработчику
py_handler.setFormatter(py_formatter)
# добавление обработчика к логгеру
py_logger.addHandler(py_handler)

admins_list = [value[0] for value in admins.values()]
collector_list = [value[0] for value in collectors.values()]


class FSMCFind_order(StatesGroup):
    number_order = State()


def make_shablon_order_text(info_order: list, number_order: str):

    text = f"{info_order[1]} {str(info_order[2])}шт.\n" \
           f"Статус заказа: {info_order[14]}\n" \
           f"Стоимость заказа: {info_order[20]}\n" \
           f"Точка сборки: {info_order[16]}\n" \
           f"Номер заказа: {number_order}\n\n" \
           f"Ссылка на доставку сборщика: {info_order[9]}\n" \
           f"Комментарий к заказу: {info_order[10]}\n" \
           f"Время до которого должен приехать курьер: {info_order[8]}\n" \
           f"Адрес доставки: {info_order[7]}\n" \
           f"Имя клиента: {info_order[3]}\n" \
           f"Имя клиента в tg: @{info_order[6]}\n" \
           f"Телефон клиента: {info_order[4]}\n" \
           f"Телефон клиента, которому доставляют: {info_order[5]}\n\n" \
           f"Сбособ доставки: {info_order[11]}\n" \
           f"Ссылка на доставку клиента: {info_order[12]}\n" \
           f"Комментарий курьеру: {info_order[13]}\n" \
           f"Шаг сборки: {info_order[15]}\n" \
           f"Телефон курьера: {info_order[18]}\n" \
           f"Имя курьера: {info_order[19]}\n" \
           f"Оценка клиента: {info_order[17]}\n\n " \
           f"❗️ Здесь не вся информация о заказе, подробнее смотри в excel таблице /take_orders_excel"

    return text


# Обработчик кнопки 'Найти заказ 🔎'
# @dp.message_handler(IDFilter(admins_list, coolector_list), filters.Text(equals='Найти заказ 🔎'), state=None)
@dec_error_mes_state
async def find_order_pressed(message: types.Message, state: FSMContext):
    await message.answer("Отправьте номер закза в таком формате: 'cdbcbea885014164a1f27a60e8d6c153'")
    await FSMCFind_order.number_order.set()
    async with state.proxy() as data:
        data['message_id'] = message.message_id


# Ловим номер закза для поиска
#@dp.message_handler(IDFilter(admins_list, collector_list), state=FSMCFind_order.number_order)
@dec_error_mes_state
async def catch_order_number(message: types.Message, state: FSMContext):
    info_order = await get_positions_sql("name_english", "name", "quantity", "name_client", "phone_client",
                                         "phone_client2", "name_tg_client", "address", "time_delivery",
                                         "link_collector", "comment_collector", "way_of_delivery", "link_client",
                                         "comment_courier", "status_order", "step_collector", "point_start_delivery",
                                         "mark", "courier_phone", "courier_name", "full_cost", "img",
                                         table_name="orders",
                                         condition="WHERE number = $1", condition_value=message.text)
    if info_order:
        shablon_order_text = make_shablon_order_text(info_order=info_order[0], number_order=message.text)
        if info_order[0][21] is None:
            await message.answer(text=shablon_order_text)
            py_logger.debug(info_order[0][21])
        else:
            py_logger.debug(f"is not None {info_order[0][21]}")
            await bot.send_photo(chat_id=message.chat.id, photo=info_order[0][21], caption=shablon_order_text)
    else:
        await message.answer(text="Заказа не найден, проверьте данные")

    await state.finish()


# Обработчик кнопки 'Сегодня и завтра'
# @dp.message_handler(IDFilter(admins_list, coolector_list), filters.Text(equals=('Сегодня', 'Завтра'))
@dec_error_mes
async def today_tomorrow_order_pressed(message: types.Message):
    condition = None
    if message.text == "Сегодня":
        condition = f"WHERE DATE(time_delivery) = current_date and time_delivery > current_timestamp"
    if message.text == "Завтра":
        condition = f"WHERE DATE(time_delivery) = current_date + 1"

    if message.chat.id in collector_list:
        for name, data in collectors.items():
            if data[0] == message.chat.id:
                point_start_delivery = name
                condition += f" and point_start_delivery = '{point_start_delivery}'"

    info_orders = await get_positions_sql("name_english", "name", "quantity", "name_client", "phone_client",
                                          "phone_client2", "name_tg_client", "address", "time_delivery",
                                          "link_collector", "comment_collector", "way_of_delivery", "link_client",
                                          "comment_courier", "status_order", "step_collector", "point_start_delivery",
                                          "mark", "courier_phone", "courier_name", "full_cost", "img", "number",
                                          table_name="orders",
                                          condition=condition)
    for info_order in info_orders:
        shablon_order_text = make_shablon_order_text(info_order=info_order, number_order=info_order[22])
        await message.answer(text=shablon_order_text)

    if not info_orders:
        await message.answer(text=f"заказов на {message.text} не найдено")


# Обработчик кнопки 'Последние 5'
# @dp.message_handler(IDFilter(admins_list, coolector_list), filters.Text(equals=('Последние 5'))
@dec_error_mes
async def last_5_order_pressed(message: types.Message):
    condition = f"WHERE time_delivery < current_timestamp"

    if message.chat.id in collector_list:
        for name, data in collectors.items():
            if data[0] == message.chat.id:
                point_start_delivery = name
                condition += f" and point_start_delivery = '{point_start_delivery}'"

    condition += f" ORDER BY time_delivery DESC LIMIT 5"
    info_orders = await get_positions_sql("name_english", "name", "quantity", "name_client", "phone_client",
                                          "phone_client2", "name_tg_client", "address", "time_delivery",
                                          "link_collector", "comment_collector", "way_of_delivery", "link_client",
                                          "comment_courier", "status_order", "step_collector", "point_start_delivery",
                                          "mark", "courier_phone", "courier_name", "full_cost", "img", "number",
                                          table_name="orders",
                                          condition=condition)
    for info_order in info_orders:
        shablon_order_text = make_shablon_order_text(info_order=info_order, number_order=info_order[22])
        if info_order[21] is None:
            await message.answer(text=shablon_order_text)
        else:
            await bot.send_photo(chat_id=message.chat.id, photo=info_order[21], caption=shablon_order_text)

    if not info_orders:
        await message.answer(text=f"{message.text}  заказов не найдено")


#@dp.message_handler(commands=['collector'])
async def commands_collector(message: types.Message):
    await set_collectors_commands(message)
    await message.reply('Вы получили права сборщика', reply_markup=kb_collector)


def register_handlers_collector(dp: Dispatcher):
    dp.register_message_handler(commands_collector, IDFilter(collector_list), commands=['collector'])
    dp.register_message_handler(find_order_pressed, IDFilter(collector_list + admins_list),
                                filters.Text(equals='Найти заказ 🔎'), state=None)
    dp.register_message_handler(catch_order_number, IDFilter(collector_list + admins_list),
                                state=FSMCFind_order.number_order)
    dp.register_message_handler(today_tomorrow_order_pressed, IDFilter(collector_list + admins_list),
                                filters.Text(equals=('Сегодня', 'Завтра')))
    dp.register_message_handler(last_5_order_pressed, IDFilter(collector_list + admins_list),
                                filters.Text(equals=('Последние 5')))



