import asyncio
import re

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import IDFilter
import os

from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from create_bot import bot
from data_base.sqlite_dp import get_positions_sql, update_positions_sql
from error_decorators.admin import dec_error_mes, dec_error_mes_state
from handlers.other import set_collectors_commands, delete_messages
from keyboards.collector_kb import kb_collector
from parameters import collectors, admins, dostavista_status, info_start_point, yandex_status

import logging

# получение пользовательского логгера и установка уровня логирования
from yandex.cancellation_order import cancellation_order

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


class FSMCollector(StatesGroup):
    photo_end = State()


class FSMCYandex_wrong(StatesGroup):
    phone = State()
    link = State()


#@dp.callback_query_handler(lambda x: x.data and x.data.startswith('strtclllct '))
@dec_error_mes
async def press_start_collect(callback: types.CallbackQuery):
    await callback.answer()
    await update_positions_sql(table_name="orders", column_values={"step_collector": "start_collect"},
                               condition=f"WHERE number = '{callback.data.split()[1]}'")
    await callback.message.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup().add
        (InlineKeyboardButton(f'показать букет', callback_data=f"flw {callback.data.split()[1]}")).add
        (InlineKeyboardButton(f'заказ собран 📦', callback_data=f"ndclllct {callback.data.split()[1]}")))


#@dp.callback_query_handler(lambda x: x.data and x.data.startswith('ndclllct '))
@dec_error_mes
async def press_end_collect(callback: types.CallbackQuery):
    await callback.answer()
    await update_positions_sql(table_name="orders", column_values={"step_collector": "end_collect"},
                               condition=f"WHERE number = '{callback.data.split()[1]}'")
    await callback.message.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup().add
        (InlineKeyboardButton(f'показать букет', callback_data=f"flw {callback.data.split()[1]}")).add
        (InlineKeyboardButton(f'отправить фотоотчет 📷🤳', callback_data=f"tkpht {callback.data.split()[1]}")))


#@dp.callback_query_handler(lambda x: x.data and x.data.startswith('tkpht '), state=None)
@dec_error_mes_state
async def take_photo(callback: types.CallbackQuery, state: FSMContext):
    py_logger.debug("0")
    await callback.answer()
    await update_positions_sql(table_name="orders", column_values={"step_collector": "waiting_photo"},
                               condition=f"WHERE number = '{callback.data.split()[1]}'")
    #await callback.message.edit_media()
    py_logger.debug("1")
    await callback.message.answer("Пожалуйста, пришлите сюда фотографию собранного букета.")
    await FSMCollector.photo_end.set()
    async with state.proxy() as data:
        data['text'] = callback.message.text
        data['number_order'] = callback.data.split()[1]
    py_logger.debug("2")
    #await callback.message.delete_reply_markup()


# Ловим фото готового букета
#@dp.message_handler(content_types=['photo'], state=FSMCollector.photo_end)
@dec_error_mes_state
async def load_photo_end(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        order_info = await get_positions_sql("message_id_collector", "message_id_collector2", "status_order",
                                             "courier_name", "courier_phone", "point_start_delivery", "link_collector",
                                             "way_of_delivery", table_name="orders", condition="WHERE number = $1",
                                             condition_value=data['number_order'])
        # Удаляем ненужные сообщения
        try:
            await bot.delete_message(message_id=order_info[0][0], chat_id=message.chat.id)
            await bot.delete_message(message_id=order_info[0][1], chat_id=message.chat.id)
        except Exception:
            pass
        try:
            await bot.delete_message(message_id=message.message_id, chat_id=message.chat.id)
            await bot.delete_message(message_id=message.message_id - 1, chat_id=message.chat.id)
        except Exception:
            pass
        msg = await message.answer_photo(photo=message.photo[0].file_id,
                                         caption="Заказ собран ✅\n" + '\n'.join(data['text'].splitlines()[1:]))
        # отправляем инфу админам
        global admins_list
        for chat_id in admins_list:
            await bot.send_photo(chat_id=chat_id, photo=message.photo[0].file_id,
                                 caption=f"Заказ собран ✅\n Номер: {data['number_order']}"
                                         f"\nТочка отправления: {order_info[0][5]}")
        text2 = "(◕‿◕) "
        py_logger.debug(f"sql_data load_photo_end {order_info}")
        if order_info[0][-1] == "Express":
            text2 += yandex_status[order_info[0][2]] + "\n"
            text2 += "Ссылка на доставку : " + str(order_info[0][-2]) + "\n"
        else:
            try:
                text2 += dostavista_status["Delivery"][order_info[0][2]] + "\n"
            except:
                text2 += dostavista_status["Order"][order_info[0][2]] + "\n"

        if order_info[0][4] is not None:
            text2 += "Курьера 📞: " + str(order_info[0][4]) + "\n"
        if order_info[0][3] is not None:
            text2 += "Имя курьера : " + str(order_info[0][3]) + "\n"

        msg2 = await msg.reply(text=text2)
        await update_positions_sql(table_name="orders", column_values={"step_collector": "end_with_photo",
                                                                       "img": message.photo[0].file_id,
                                                                       "message_id_collector": msg.message_id,
                                                                       "message_id_collector2": msg2.message_id},
                                   condition=f"WHERE number = '{data['number_order']}'")
    await state.finish()


#@dp.callback_query_handler(lambda x: x.data and x.data.startswith('flw '))
@dec_error_mes
async def commands_show_flower(callback: types.CallbackQuery):
    await callback.answer("показываем букет")
    flower_info = await get_positions_sql("goods.img", "goods.name", "goods.name_english", "goods.category",
                                          "goods.subcategory", "goods.description", "goods.price", table_name="goods",
                                          condition=f"INNER JOIN orders ON goods.name = orders.name "
                                                    f"WHERE orders.number = $1",
                                          condition_value=callback.data.split()[1])
    py_logger.info(f"commands_show_flower flower_info: {flower_info}")
    if flower_info:
        try:
            for ret in flower_info:
                caption = f'*{ret[1]}*\n_English_: *{ret[2]}*\n_Категория:_ *{ret[3]}*\n_Подкатегория:_ *{ret[4]}*\n_' \
                          f'Описание:_ *{ret[5]}*\n_Цена_ *{ret[-1]}*'
                album = types.MediaGroup()
                matches = re.findall(r"'(.*?)'", ret[0])
                for i, match in enumerate(matches):
                    if i == len(matches) - 1:
                        album.attach_photo(photo=match, caption=caption, parse_mode="Markdown")
                    else:
                        album.attach_photo(photo=match)
                msg = await callback.message.answer_media_group(media=album)
                await asyncio.sleep(100)
                for message in msg:
                    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        except Exception as e:
            py_logger.error(f"commands_show_flower: {e}")
            await callback.message.answer("не получилось вывести информацию о букете")
    else:
        await callback.message.answer("не получилось вывести информацию о букете")


async def start_colllect(chat_id: int, number_order: str):
    last_order = await get_positions_sql("name_english", "name", "quantity", "name_client", "phone_client",
                                         "phone_client2", "name_tg_client", "address", "time_delivery",
                                         "link_collector", "comment_collector", table_name="orders",
                                         condition="WHERE number = $1", condition_value=number_order)
    if last_order:
        msg = await bot.send_message(
            chat_id=chat_id,
            text=f"Курьер будет примерно через час!\n"
                 f"Номер заказа: {number_order}\n"
                 f"{last_order[0][1]} {str(last_order[0][2])}шт.\n"
                 f"Ссылка на доставку: {last_order[0][9]}\n"
                 f"Комментарий к заказу: {last_order[0][10]}\n"
                 f"Время до которого должен приехать курьер: {last_order[0][8]}\n"
                 f"Адрес доставки: {last_order[0][7]}\n"
                 f"Имя клиента: {last_order[0][3]}\n"
                 f"Имя клиента в tg: @{last_order[0][6]}\n"
                 f"Телефон клиента: {last_order[0][4]}\n"
                 f"Телефон клиента, которому доставляют: {last_order[0][5]}",
            reply_markup=InlineKeyboardMarkup().add
            (InlineKeyboardButton(f'показать букет', callback_data=f"flw {number_order}")).add
            (InlineKeyboardButton(f'начал собирать 📦', callback_data=f"strtclllct {number_order}"))
        )
        await bot.pin_chat_message(chat_id=msg.chat.id, message_id=msg.message_id)
        await update_positions_sql(table_name="orders", column_values={"message_id_collector": msg.message_id},
                                   condition=f"WHERE number = '{number_order}'")
        asyncio.create_task(control_step_collect(chat_id=chat_id, number_order=number_order))

    else:
        py_logger.error(f"Ошибка: не смогли вытащить данные из базы данных о заказе {number_order}")


async def control_step_collect(chat_id: int, number_order: str, time=3000):
    py_logger.debug("control_step_collect start")
    await asyncio.sleep(time)
    step = await get_positions_sql("step_collector", table_name="orders",
                                   condition="WHERE number = $1", condition_value=number_order)
    py_logger.debug(step[0][0])

    # проверяем начал ли собирать сборщик за 10 минут до прибытия курьера
    if step[0][0] == "waiting":
        await bot.send_message(chat_id=chat_id, text=f"Напоминаю, вы не начали собирать заказ: {number_order}")
    await asyncio.sleep(300)
    step = await get_positions_sql("step_collector", "point_start_delivery", table_name="orders",
                                   condition="WHERE number = $1", condition_value=number_order)
    if step[0][0] == "waiting":    #уведомляем админа
        for chat_id_admin in admins_list:
            await bot.send_message(chat_id=chat_id_admin,
                                   text=f"На точке {step[0][1]}, сборщик не начал собирать заказ номер: {number_order}")

    await asyncio.sleep(300)
    step = await get_positions_sql("step_collector", table_name="orders",
                                   condition="WHERE number = $1", condition_value=number_order)
    py_logger.debug(step[0][0])
    # проверяем закончил ли собирать сборщик прям перед прибытием курьера
    if step[0][0] == "start_collect" or step[0][0] == "waiting":
        await bot.send_message(chat_id=chat_id, text=f"Напоминаю, вы еще не собрали заказ: {number_order}")
    await asyncio.sleep(200)
    py_logger.debug("await asyncio.sleep(20)")
    step = await get_positions_sql("step_collector", "point_start_delivery", table_name="orders",
                                   condition="WHERE number = $1", condition_value=number_order)
    if step[0][0] == "start_collect" or step[0][0] == "waiting":   #уведомляем админа
        for chat_id_admin in admins_list:
            await bot.send_message(chat_id=chat_id_admin,
                                   text=f"На точке {step[0][1]}, сборщик еще не собрал заказ: {number_order}")


async def start_colllect_yandex(chat_id: int, number_order: str):
    last_order = await get_positions_sql("name_english", "name", "quantity", "name_client", "phone_client",
                                         "phone_client2", "name_tg_client", "address", "time_delivery",
                                         "link_collector", "comment_collector", table_name="orders",
                                         condition="WHERE number = $1", condition_value=number_order)
    if last_order:
        msg = await bot.send_message(
            chat_id=chat_id,
            text=f"⚡️Express заказ!\n"
                 f"Номер заказа: {number_order}\n"
                 f"{last_order[0][1]} {str(last_order[0][2])}шт.\n"
                 f"Комментарий к заказу: {last_order[0][10]}\n"
                 f"Ссылка на доставку: скоро появится\n"
                 f"Адрес доставки: {last_order[0][7]}\n"
                 f"Имя клиента: {last_order[0][3]}\n"
                 f"Имя клиента в tg: @{last_order[0][6]}\n"
                 f"Телефон клиента: {last_order[0][4]}\n"
                 f"Телефон клиента, которому доставляют: {last_order[0][5]}",
            reply_markup=InlineKeyboardMarkup().add
            (InlineKeyboardButton(f'показать букет', callback_data=f"flw {number_order}")).add
            (InlineKeyboardButton(f'начал собирать 📦', callback_data=f"strtclllct {number_order}"))
        )
        await bot.pin_chat_message(chat_id=msg.chat.id, message_id=msg.message_id)
        await update_positions_sql(table_name="orders", column_values={"message_id_collector": msg.message_id},
                                   condition=f"WHERE number = '{number_order}'")
        asyncio.create_task(control_step_collect(chat_id=chat_id, number_order=number_order, time=450))
        #asyncio.create_task(control_step_yandex(number_order=number_order))

    else:
        py_logger.error(f"Ошибка: не смогли вытащить данные из базы данных о заказе {number_order}")


async def control_step_yandex(number_order: str):
    await asyncio.sleep(720)
    last_order = await get_positions_sql("name_english", "name", "quantity", "name_client", "phone_client",
                                         "phone_client2", "name_tg_client", "address", "time_delivery",
                                         "link_collector", "comment_collector", "point_start_delivery",
                                         table_name="orders", condition="WHERE number = $1",
                                         condition_value=number_order)
    py_logger.debug(f"control_step_yandex url: {last_order[0][9]}")
    if last_order[0][9] is None:
        await cancellation_order(id=number_order)
        text_problem = f"Не нашлось курьера для ⚡️Express заказа! Закажите курьера сами, и загрузите сюда данные," \
                       f" нажав на кнопку 'загрузить данные'\n"\
                       f"Номер заказа: {number_order}\n"\
                       f"{last_order[0][1]} {str(last_order[0][2])}шт.\n"\
                       f"Адрес доставки: {last_order[0][7]}\n"\
                       f"Телефон клиента, которому доставляют: {last_order[0][5]}\n" \
                       f"Телефон точки сборщика: {info_start_point[last_order[0][-1]]['phone']}"

        for chat_id in admins_list:
            await bot.send_message(chat_id=chat_id, text=text_problem, reply_markup=InlineKeyboardMarkup().
                                   add(InlineKeyboardButton(f'загрузить данные',
                                                            callback_data=f"cntrl_ndx {number_order}")))


#@dp.callback_query_handler(lambda x: x.data and x.data.startswith('cntrl_ndx '))
@dec_error_mes_state
async def yandex_wrong_start(callback: types.CallbackQuery, state: FSMContext):
    await FSMCYandex_wrong.phone.set()
    async with state.proxy() as data:
        data["start_message_id"] = callback.message.message_id
        data['number'] = callback.data.split()[1]
    await callback.answer()
    await callback.message.answer("Пожалуйста, пришлите сюда номер курьера в формате 79161052259")


# Ловим телефон курьера
#@dp.message_handler(state=FSMCYandex_wrong.phone)
@dec_error_mes_state
async def yandex_wrong_phone(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['phone'] = message.text
    await message.answer("Пожалуйста, пришлите сюда ссылку на доставку")
    await FSMCYandex_wrong.link.set()


# Ловим ссылку на доставку
#@dp.message_handler(state=FSMCYandex_wrong.link)
@dec_error_mes_state
async def yandex_wrong_link(message: types.Message, state: FSMContext):
    msg = await message.answer("Спасибо")
    async with state.proxy() as data:
        data['link'] = message.text
        asyncio.create_task(
            delete_messages(message.chat.id, data['start_message_id'], msg.message_id + 1, 4, 0))
        sql_data = await get_positions_sql("message_id_client2", "message_id_collector2", "chat_id_client",
                                           "message_id_client", "message_id_collector", "point_start_delivery",
                                           table_name="orders", condition="WHERE number = $1",
                                           condition_value=data['number'])
        text = "(◕‿◕) Курьер назначен и уже отправляется за цветами!\n"
        text += "Курьера 📞: " + data['phone'] + "\n"
        text += "Ссылка на доставку : " + data['link'] + "\n"
        # отправляем инфу клиенту
        if sql_data[0][0] is None:
            msg = await bot.send_message(chat_id=sql_data[0][2], text=text, reply_to_message_id=sql_data[0][3])
            await update_positions_sql(table_name="orders",
                                       column_values={"message_id_client2": msg.message_id},
                                       condition=f"WHERE number = '{data['number']}'")
        else:
            try:
                await bot.edit_message_text(chat_id=sql_data[0][2], message_id=sql_data[0][0], text=text)
            except:
                pass

        # отправляем инфу сборщику
        if sql_data[0][1] is None:
            msg = await bot.send_message(chat_id=collectors[sql_data[0][5]][0], text=text,
                                         reply_to_message_id=sql_data[0][4])
            await update_positions_sql(table_name="orders",
                                       column_values={"message_id_collector2": msg.message_id},
                                       condition=f"WHERE number = '{data['number']}'")
        else:
            try:
                await bot.edit_message_text(chat_id=collectors[sql_data[0][5]][0], message_id=sql_data[0][1],
                                            text=text)
            except:
                pass

        # обновляем данные(ссылку и телефон)
        await update_positions_sql(table_name="orders",
                                   column_values={"link_collector": data['link'], "link_client": data['link'],
                                                  "courier_phone": data['phone']},
                                   condition=f"WHERE number = '{data['number']}'")
    await state.finish()


#@dp.message_handler(commands=['collector'])
async def commands_collector(message: types.Message):
    await set_collectors_commands(message)
    await message.reply('Вы получили права сборщика', reply_markup=kb_collector)


def register_handlers_collector(dp: Dispatcher):
    dp.register_message_handler(commands_collector, IDFilter(collector_list), commands=['collector'])
    dp.register_callback_query_handler(commands_show_flower, IDFilter(collector_list),
                                       lambda x: x.data and x.data.startswith('flw '))
    dp.register_callback_query_handler(press_start_collect, IDFilter(collector_list),
                                       lambda x: x.data and x.data.startswith('strtclllct '))
    dp.register_callback_query_handler(press_end_collect, IDFilter(collector_list),
                                       lambda x: x.data and x.data.startswith('ndclllct '))
    dp.register_callback_query_handler(take_photo, IDFilter(collector_list),
                                       lambda x: x.data and x.data.startswith('tkpht '), state=None)
    dp.register_message_handler(load_photo_end, content_types=['photo'], state=FSMCollector.photo_end)
    dp.register_callback_query_handler(yandex_wrong_start, IDFilter(admins_list),
                                       lambda x: x.data and x.data.startswith('cntrl_ndx '), state=None)
    dp.register_message_handler(yandex_wrong_phone, IDFilter(admins_list), state=FSMCYandex_wrong.phone)
    dp.register_message_handler(yandex_wrong_link, IDFilter(admins_list), state=FSMCYandex_wrong.link)

