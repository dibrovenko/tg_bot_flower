import asyncio
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional
import os
import logging

from create_bot import bot
from handlers.client_order_end import estimate_order_start
from parameters import admins, yandex_status, collectors
from yandex.get_courier_phone import get_courier_info

admins_list = [value[0] for value in admins.values()]

# получение пользовательского логгера и установка уровня логирования
from data_base.sqlite_dp import get_positions_sql, update_positions_sql

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


class VisitedAt(BaseModel):
    expected_waiting_time_sec: int
    actual: Optional[str] = None


class RoutePoint(BaseModel):
    id: int
    type: str
    sharing_link: Optional[str] = None
    visited_at: Optional[VisitedAt]


class PerformerInfo(BaseModel):
    courier_name: str
    legal_name: str


class Claim(BaseModel):
    claim_id: str
    updated_ts: datetime
    status: str
    performer_info: PerformerInfo = None
    route_points: List[RoutePoint]


async def catch_answer_from_yandex(data: dict):
    py_logger.info(data)
    # Валидация JSON
    try:
        update = Claim(**data)
        py_logger.info(update)
    except Exception as e:
        py_logger.error(e)
        return

    # задержка, чтобы остальные данные обновились
    await asyncio.sleep(0.5)
    # проверяем что заказ существует в нашей базе данных
    sql_data = await get_positions_sql("status_order", "address", "time_delivery", "courier_name",
                                       "courier_phone", "point_start_delivery", "message_id_client2",
                                       "message_id_collector2", "chat_id_client", "time_delivery_end",
                                       "message_id_client", "message_id_collector", "link_collector", "link_client",
                                       table_name="orders", condition="WHERE number = $1",
                                       condition_value=str(update.claim_id))
    py_logger.info(f"sql_data: {sql_data}")
    if sql_data is not None and sql_data:
        # выходим из функции, если уже статус закзаа: отменен, завершен
        if sql_data[0][0] in ["ourselves", "delivered", "performer_not_found", "estimating_failed", "delivered_finish",
                              "returned_finish", "cancelled_with_payment", "cancelled"]:
            return

        # запускаем функцию оценки пользователем заказа, если он завершен
        if update.status in ["delivered_finish", "delivered", "returned_finish", "cancelled_with_payment", "cancelled"]:
            py_logger.debug("заказ завершен")
            await estimate_order_start(chat_id_client=sql_data[0][8], order_number=update.claim_id,
                                       message_id_client=sql_data[0][10])

        text = "(◕‿◕) "
        text += yandex_status[update.status] + "\n"
        # обновляем статус в бд если он изменился
        if sql_data[0][0] != update.status:
            await update_positions_sql(table_name="orders", column_values={"status_order": update.status},
                                       condition=f"WHERE number = '{str(update.claim_id)}'")

        # обрабатываем информацию связанную с курьером
        if update.performer_info is not None:
            courier_info = await get_courier_info(claim_id=update.claim_id)
            if courier_info["result"]:
                text += "Курьера 📞: " + courier_info["phone"] + "\n"
                text += "Имя курьера: " + update.performer_info.courier_name + "\n"
                if update.performer_info.courier_name != sql_data[0][3] or courier_info["phone"] != sql_data[0][4]:
                    await update_positions_sql(table_name="orders",
                                               column_values={"courier_name": update.performer_info.courier_name,
                                                              "courier_phone": courier_info["phone"]},
                                               condition=f"WHERE number = '{str(update.claim_id)}'")
            else:
                text += "Имя курьера: " + update.performer_info.courier_name + "\n"
                if update.performer_info.courier_name != sql_data[0][3]:
                    await update_positions_sql(table_name="orders",
                                               column_values={"courier_name": update.performer_info.courier_name},
                                               condition=f"WHERE number = '{str(update.claim_id)}'")

        # находим ссылки на доставки
        link_dict = {}
        for route_point in update.route_points:
            link_dict[route_point.type] = route_point.sharing_link
        if link_dict["source"] is None and link_dict["destination"] is None:
            link_client = link_collector = " "
        elif link_dict["destination"] is None:
            link_client = link_collector = link_dict["source"]
        elif link_dict["source"] is None:
            link_client = link_collector = link_dict["destination"]
        else:
            link_client = f'Ссылка на доставку: {link_dict["destination"]}\n'
            link_collector = f'Ссылка на доставку: {link_dict["source"]}\n'
        # обновляем ссылки в бд если они изменились
        if link_client != sql_data[0][0] or link_collector != sql_data[0][0]:
            await update_positions_sql(table_name="orders", column_values={"link_collector": link_collector,
                                                                           "link_client": link_client},
                                       condition=f"WHERE number = '{update.claim_id}'")

        # отправляем инфу клиенту
        if sql_data[0][6] is None:
            msg = await bot.send_message(chat_id=sql_data[0][8], text=text+link_client,
                                         reply_to_message_id=sql_data[0][10])
            await update_positions_sql(table_name="orders", column_values={"message_id_client2": msg.message_id},
                                       condition=f"WHERE number = '{update.claim_id}'")
        else:
            try:
                await bot.edit_message_text(chat_id=sql_data[0][8], message_id=sql_data[0][6], text=text+link_client)
            except:
                pass

        # отправляем инфу сборщику
        if sql_data[0][7] is None:
            msg = await bot.send_message(chat_id=collectors[sql_data[0][5]][0], text=text+link_collector,
                                         reply_to_message_id=sql_data[0][11])
            await update_positions_sql(table_name="orders", column_values={"message_id_collector2": msg.message_id},
                                       condition=f"WHERE number = '{update.claim_id}'")
        else:
            try:
                await bot.edit_message_text(chat_id=collectors[sql_data[0][5]][0], message_id=sql_data[0][7],
                                            text=text+link_collector)
            except:
                pass
