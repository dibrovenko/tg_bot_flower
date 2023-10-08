import logging
import os

from aiogram import types, Dispatcher

from data_base.sqlite_dp import update_positions_sql, get_positions_sql
from parameters import admins, collectors
from create_bot import bot

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


async def estimate_order_start(chat_id_client, message_id_client, order_number):
    await bot.unpin_chat_message(chat_id=chat_id_client, message_id=message_id_client)
    keyboard = types.InlineKeyboardMarkup(row_width=5)
    keyboard.add(
        types.InlineKeyboardButton(text="😡", callback_data=f"est 1 {order_number}"),
        types.InlineKeyboardButton(text="😕", callback_data=f"est 2 {order_number}"),
        types.InlineKeyboardButton(text="😐", callback_data=f"est 3 {order_number}"),
        types.InlineKeyboardButton(text="🙂", callback_data=f"est 4 {order_number}"),
        types.InlineKeyboardButton(text="😄", callback_data=f"est 5 {order_number}")
    )
    await bot.send_message(text="Спасибо за ваш заказ! Пожалуйста, оцените нашу работу с помощью смайликов:",
                           chat_id=chat_id_client, reply_markup=keyboard)


#@dp.callback_query_handler(lambda x: x.data and x.data.startswith('est '))
async def estimate_order_end(callback: types.CallbackQuery):
    await callback.answer("Спасибо")
    await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    py_logger.info(f"callback.data estimate_order_end: {callback.data}")
    mark = callback.data.split()[1]
    number_order = callback.data.split()[2]
    await update_positions_sql(table_name="orders", column_values={"mark": mark},
                               condition=f"WHERE number = '{number_order}'")
    sql_order = await get_positions_sql("name_tg_client", table_name="orders",
                                   condition="WHERE number = $1", condition_value=number_order)
    # если неудовлетворительная оценка
    if mark in ["1", "2",  "3"]:
        for chat_id_admin in admins_list:
            await bot.send_message(chat_id=chat_id_admin,
                                   text=f"Клиент @{sql_order[0][0]} оставил негативную оценку {mark}."
                                        f" Номер заказа: {number_order}")




def register_handlers_client_order_end(dp: Dispatcher):
    dp.register_callback_query_handler(estimate_order_end, lambda x: x.data and x.data.startswith('est '))


