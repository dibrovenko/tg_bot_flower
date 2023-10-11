import asyncio

from pydantic import BaseModel
import datetime
from typing import List, Optional
import os
import logging

from create_bot import bot
from handlers.client_order_end import estimate_order_start
from parameters import dostavista_status, collectors, admins

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


class ContactPerson(BaseModel):
    name: str | None
    phone: str


class Courier(BaseModel):
    name: str | None
    phone: str


class Delivery(BaseModel):
    delivery_id: int
    delivery_type: str
    order_id: int
    client_id: int
    client_order_id: Optional[str]
    address: str
    latitude: Optional[float]
    longitude: Optional[float]
    status: str
    status_datetime: datetime.datetime
    created_datetime: datetime.datetime
    order_name: str
    required_start_datetime: datetime.datetime
    required_finish_datetime: datetime.datetime
    order_payment_amount: float
    delivery_price_amount: float
    point_id: int
    contact_person: ContactPerson
    courier: Optional[Courier] = None
    note: Optional[str]
    building_number: Optional[str]
    apartment_number: Optional[str]
    entrance_number: Optional[str]
    intercom_code: Optional[str]
    floor_number: Optional[int]
    invisible_mile_navigation_instructions: Optional[str]


class Point(BaseModel):
    point_type: str
    point_id: int
    delivery_id: int | None
    client_order_id: int | None
    address: str
    latitude: float
    longitude: float
    required_start_datetime: datetime.datetime
    required_finish_datetime: datetime.datetime
    arrival_start_datetime: Optional[datetime.datetime]
    arrival_finish_datetime: Optional[datetime.datetime]
    estimated_arrival_datetime: Optional[datetime.datetime]
    contact_person: ContactPerson
    taking_amount: float
    buyout_amount: float
    note: str | None
    previous_point_driving_distance_meters: int
    packages: Optional[list]
    tracking_url: str
    is_return_point: bool
    is_order_payment_here: bool


class Order(BaseModel):
    type: str
    order_id: int
    order_name: str | None
    vehicle_type_id: int
    created_datetime: datetime.datetime
    finish_datetime: Optional[datetime.datetime]
    status: str
    status_description: str
    matter: str
    total_weight_kg: float
    is_client_notification_enabled: bool
    is_contact_person_notification_enabled: bool
    loaders_count: int
    backpayment_details: Optional[str]
    points: List[Point]
    payment_amount: float
    delivery_fee_amount: float
    weight_fee_amount: float
    insurance_amount: float
    insurance_fee_amount: float
    loading_fee_amount: float
    money_transfer_fee_amount: float
    overnight_fee_amount: float
    door_to_door_fee_amount: float
    promo_code_discount_amount: float
    backpayment_amount: float
    cod_fee_amount: float
    payment_method: Optional[str]
    courier: Optional[Courier] = None


class Event(BaseModel):
    event_datetime: datetime.datetime
    event_type: str
    order: Order = None
    delivery: Delivery = None


async def catch_answer_from_dostavista(data: dict):
    update = Event(**data)
    py_logger.info(update)

    if update.order is None:
        sql_data = await get_positions_sql("status_order", "address", "time_delivery", "courier_name",
                                           "courier_phone", "point_start_delivery", "message_id_client2",
                                           "message_id_collector2", "chat_id_client", "time_delivery_end",
                                           "message_id_client", "message_id_collector", table_name="orders",
                                           condition="WHERE number = $1",
                                           condition_value=str(update.delivery.order_id))
        py_logger.info(f"sql_data: {sql_data}")
        if sql_data is not None:
            # выходим из функции, если уже статус закзаа: отменен, завершен
            if sql_data[0][0] in ["completed", "finished", "canceled"]:
                return
            text = "(◕‿◕) "
            if update.delivery.status != sql_data[0][0]:
                await update_positions_sql(table_name="orders", column_values={"status_order": update.delivery.status},
                                           condition=f"WHERE number = '{str(update.delivery.order_id)}'")
            text += dostavista_status["Delivery"][update.delivery.status] + "\n"

            if update.delivery.address != sql_data[0][1]:
                await update_positions_sql(table_name="orders", column_values={"status_order": sql_data[0][1]},
                                           condition=f"WHERE number = '{str(update.delivery.order_id)}'")

                await bot.send_message(chat_id=collectors[sql_data[0][5]][0],
                                       text=f"Ошибка в заказе {update.delivery.order_id}, изменился адрес "
                                            f"финальной точки, решайте проблему")

            if update.delivery.courier is not None:
                if update.delivery.courier.name != sql_data[0][3] or update.delivery.courier.name != sql_data[0][4]:
                    await update_positions_sql(table_name="orders",
                                               column_values={"courier_name": update.delivery.courier.name,
                                                              "courier_phone": update.delivery.courier.phone},
                                               condition=f"WHERE number = '{str(update.delivery.order_id)}'")
                text += "Курьера 📞: " + update.delivery.courier.phone + "\n"
                text += "Имя курьера : " + update.delivery.courier.name + "\n"

            if update.delivery.required_start_datetime.replace(tzinfo=None) != sql_data[0][2] or \
                    update.delivery.required_finish_datetime.replace(tzinfo=None) != sql_data[0][-3]:
                await bot.send_message(chat_id=sql_data[0][8],
                                       text=f"К сожалению, изменилось время доставки на другое: "
                                            f" {str(update.delivery.required_start_datetime.time())[:5]} - "
                                            f"{str(update.delivery.required_finish_datetime.time())[:5]}")
                await update_positions_sql(table_name="orders", column_values={"time_delivery":
                                           update.delivery.required_start_datetime.replace(tzinfo=None),
                                                                               "time_delivery_end":
                                           update.delivery.required_finish_datetime.replace(tzinfo=None)},
                                           condition=f"WHERE number = '{str(update.delivery.order_id)}'")

            # отправляем инфу клиенту
            if sql_data[0][6] is None:
                msg = await bot.send_message(chat_id=sql_data[0][8], text=text, reply_to_message_id=sql_data[0][-2])
                await update_positions_sql(table_name="orders",
                                           column_values={"message_id_client2": msg.message_id},
                                           condition=f"WHERE number = '{str(update.delivery.order_id)}'")
            else:
                try:
                    await bot.edit_message_text(chat_id=sql_data[0][8], message_id=sql_data[0][6], text=text)
                except:
                    pass

            # отправляем инфу сборщику только изменения если они меньше чем за час до начала доставки
            if update.delivery.required_start_datetime.replace(
                    tzinfo=None) - datetime.datetime.now() < datetime.timedelta(hours=2):
                if sql_data[0][7] is None:
                    msg = await bot.send_message(chat_id=collectors[sql_data[0][5]][0], text=text,
                                                 reply_to_message_id=sql_data[0][-1])
                    await update_positions_sql(table_name="orders",
                                               column_values={"message_id_collector2": msg.message_id},
                                               condition=f"WHERE number = '{str(update.delivery.order_id)}'")
                else:
                    try:
                        await bot.edit_message_text(chat_id=collectors[sql_data[0][5]][0], message_id=sql_data[0][7],
                                                    text=text)
                    except:
                        pass
            #запускаем функцию оценки пользователем заказа, если он завершен
            if update.delivery.status in ["completed", "finished", "canceled"]:
                py_logger.debug("заказ завершен")
                await estimate_order_start(chat_id_client=sql_data[0][8], order_number=update.delivery.order_id,
                                           message_id_client=sql_data[0][-2])
        else:
            raise Exception

    else:
        await asyncio.sleep(2.5)
        sql_data = await get_positions_sql("status_order", "address", "time_delivery", "courier_name",
                                           "courier_phone", "point_start_delivery", "message_id_client2",
                                           "message_id_collector2", "chat_id_client", "link_collector",
                                           "link_client", "delivery_cost", "phone_client2", "time_delivery_end",
                                           "message_id_client", "message_id_collector", table_name="orders",
                                           condition="WHERE number = $1",
                                           condition_value=str(update.order.order_id))
        if sql_data is not None:
            text = "(◕‿◕) "
            py_logger.info(f"sql_data: {sql_data}")
            # выходим из функции, если уже статус закзаа: отменен, завершен
            if sql_data[0][0] in ["completed", "finished", "canceled"]:
                return
            if update.order.status != sql_data[0][0]:
                py_logger.debug("status order")
                await update_positions_sql(table_name="orders", column_values={"status_order": update.order.status},
                                           condition=f"WHERE number = '{str(update.order.order_id)}'")
            text += dostavista_status["Order"][update.order.status] + "\n"

            if update.order.points[1].address != sql_data[0][1]:
                await update_positions_sql(table_name="orders",
                                           column_values={"status_order": update.order.points[1].address},
                                           condition=f"WHERE number = '{str(update.order.order_id)}'")

                await bot.send_message(chat_id=collectors[sql_data[0][5]][0],
                                       text=f"Ошибка в заказе {update.order.order_id}, изменился адрес "
                                            f"финальной точки, решайте проблему")

            if update.order.courier is not None:
                if update.order.courier.name != sql_data[0][3] or update.order.courier.phone != sql_data[0][4]:
                    await update_positions_sql(table_name="orders",
                                               column_values={"courier_name": update.order.courier.name,
                                                              "courier_phone": update.order.courier.phone},
                                               condition=f"WHERE number = '{str(update.order.order_id)}'")
                text += "Курьера 📞: " + update.order.courier.phone + "\n"
                text += "Имя курьера: " + update.order.courier.name + "\n"

            # проверка, что время доставки не изменилось
            if update.order.points[1].required_start_datetime.replace(tzinfo=None) != sql_data[0][2] or \
                    update.order.points[1].required_finish_datetime.replace(tzinfo=None) != sql_data[0][-3]:
                await bot.send_message(chat_id=sql_data[0][8],
                                       text=f"К сожалению, изменилось время доставки на другое: "
                                            f" {str(update.order.points[1].required_start_datetime.time())[:5]} - "
                                            f"{str(update.order.points[1].required_finish_datetime.time())[:5]}")
                await update_positions_sql(table_name="orders", column_values={"time_delivery":
                                           update.order.points[1].required_start_datetime.replace(tzinfo=None),
                                                                               "time_delivery_end":
                                           update.order.points[1].required_finish_datetime.replace(tzinfo=None)},
                                           condition=f"WHERE number = '{str(update.order.order_id)}'")

            # проверка, что телефон получателя не изменился:
            if sql_data[0][12] != "+" + update.order.points[0].contact_person.phone:
                await bot.send_message(chat_id=collectors[sql_data[0][5]][0],
                                       text=f"Ошибка в заказе {update.order.order_id}, изменился телефон получателя"
                                            f"на новый: +{update.order.points[0].contact_person.phone}, решайте проблему")
                await update_positions_sql(
                    table_name="orders",
                    column_values={"phone_client2": "+" + update.order.points[0].contact_person.phone},
                    condition=f"WHERE number = '{str(update.order.order_id)}'")
                py_logger.error(f"# проверка, что телефон получателя не изменился:"
                                f" {sql_data[0][13]}  {update.order.points[0].contact_person.phone}")

            # проверка, что ссылка на доставку сборщику не изменилась
            if sql_data[0][9] != update.order.points[0].tracking_url:
                await bot.send_message(chat_id=collectors[sql_data[0][5]][0],
                                       text=f"Изменения в заказе {update.order.order_id}, новая ссылка на доставку"
                                            f": {update.order.points[0].contact_person.phone}")
                await update_positions_sql(table_name="orders",
                                           column_values={"link_collector": update.order.points[0].tracking_url},
                                           condition=f"WHERE number = '{str(update.order.order_id)}'")
                py_logger.info(f"# проверка, что ссылка на доставку сборщику не изменилась"
                               f"  {sql_data[0][10]} {update.order.points[0].tracking_url}")

            # проверка, что ссылка на доставку клиента не изменилась
            if sql_data[0][10] != update.order.points[1].tracking_url:
                await bot.send_message(chat_id=sql_data[0][8],
                                       text=f"Изменения в заказе {update.order.order_id}, новая ссылка на доставку"
                                            f": {update.order.points[1].tracking_url}")
                await update_positions_sql(table_name="orders",
                                           column_values={"link_client": update.order.points[1].tracking_url},
                                           condition=f"WHERE number = '{str(update.order.order_id)}'")
                py_logger.info(f"# проверка, что ссылка на доставку клиенту не изменилась"
                               f" {sql_data[0][11]} {update.order.points[1].tracking_url}")

            # проверка, что метод оплаты не изменился
            if update.order.payment_method != "bank_card":
                await bot.send_message(chat_id=collectors[sql_data[0][5]][0],
                                       text=f"Ошибка в заказе {update.order.order_id}, изменился способ оплаты на"
                                            f": {update.order.payment_method}, решайте проблему")
                py_logger.error(f"# проверка, что метод оплаты не изменился {update.order.payment_method}")

            # проверка, что стоимость заказа не изменилась больше чем на 50 рублей
            if update.order.payment_amount - sql_data[0][11] > 50:
                for chat_id in admins_list:
                    await bot.send_message(chat_id=chat_id,
                                           text=f"Номер заказа: {str(update.order.order_id)}\n Стоимость доставки "
                                                f"изменилась \nCтарая цена: {sql_data[0][11]}, "
                                                f"новая цена: {update.order.payment_amount}")
                await update_positions_sql(table_name="orders",
                                           column_values={"delivery_cost": update.order.payment_amount},
                                           condition=f"WHERE number = '{str(update.order.order_id)}'")
                py_logger.info(f"# проверка, что стоимость заказа не изменилась"
                               f" {sql_data[0][12]} {update.order.payment_amount}")

            # отправляем инфу клиенту
            if sql_data[0][6] is None:
                msg = await bot.send_message(chat_id=sql_data[0][8], text=text, reply_to_message_id=sql_data[0][-2])
                await update_positions_sql(table_name="orders",
                                           column_values={"message_id_client2": msg.message_id},
                                           condition=f"WHERE number = '{str(update.order.order_id)}'")
            else:
                try:
                    await bot.edit_message_text(chat_id=sql_data[0][8], message_id=sql_data[0][6], text=text)
                except:
                    pass

            # отправляем инфу сборщику только изменения если они меньше чем за час до начала доставки
            if update.order.points[0].required_start_datetime.replace(tzinfo=None) - \
                    datetime.datetime.now() < datetime.timedelta(hours=1):
                if sql_data[0][7] is None:
                    msg = await bot.send_message(chat_id=collectors[sql_data[0][5]][0], text=text,
                                                 reply_to_message_id=sql_data[0][-1])
                    await update_positions_sql(table_name="orders",
                                               column_values={"message_id_collector2": msg.message_id},
                                               condition=f"WHERE number = '{str(update.order.order_id)}'")
                else:
                    try:
                        await bot.edit_message_text(chat_id=collectors[sql_data[0][5]][0], message_id=sql_data[0][7],
                                                    text=text)
                    except:
                        pass

            # запускаем функцию оценки пользователем заказа, если он завершен
            if update.order.status in ["completed", "finished", "canceled"]:
                py_logger.debug("заказ завершен")
                await estimate_order_start(chat_id_client=sql_data[0][8], order_number=update.order.order_id,
                                           message_id_client=sql_data[0][-2])
