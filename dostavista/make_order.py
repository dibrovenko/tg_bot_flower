import datetime
import ssl
import asyncio
import aiohttp
import os
import logging
from dotenv import load_dotenv, find_dotenv

from parameters import info_start_point


py_logger = logging.getLogger(__name__)
py_logger.setLevel(logging.DEBUG)

# настройка обработчика и форматировщика в соответствии с нашими нуждами
log_file = os.path.join(f"log_directory/{__name__}.log")
py_handler = logging.FileHandler(log_file, mode='w')

#py_handler = logging.FileHandler(f"{__name__}.log", mode='w')
py_formatter = logging.Formatter("%(name)s %(asctime)s %(levelname)s %(message)s")

# добавление форматировщика к обработчику
py_handler.setFormatter(py_formatter)
# добавление обработчика к логгеру
py_logger.addHandler(py_handler)


async def dostavista_make_order(address: str, lat: float, lon: float, phone: str, comment: str,
                                time_client_delivery: datetime.datetime, point_start_delivery: str) -> dict | None:

    """ Функция `dostavista_make_order` используется для создания заказа в сервисе доставки Dostavista. Функция работает
        асинхронно и принимает следующие параметры:

            :param address: Адрес доставки.
            :param lat: Широта места доставки.
            :param lon: Долгота места доставки.
            :param phone: Номер телефона клиента.
            :param comment: Комментарий к заказу от клиента.
            :param time_client_delivery: Время начала, когда клиент желает получить доставку.
            :param point_start_delivery: Начальная точка доставки(ключ по названию магазина).

    :rtype: dict | None - Если заказ успешно создан, функция возвращает словарь с информацией о заказе. В противном
                          случае, если возникла ошибка при создании заказа, функция возвращает None.
    """

    dict_start_point = info_start_point

    py_logger.debug(f"address: {address}, lat: {lat}, lon: {lon}, phone: {phone}, comment: {comment}, "
                    f"time_client_delivery: {time_client_delivery}, point_start_delivery: {point_start_delivery}")

    # параметры запроса для dostavista
    load_dotenv(find_dotenv())
    api_key = os.getenv('api_key_dostavista')

    url = 'https://robot.dostavista.ru/api/business/1.3/create-order'

    headers = {
        'X-DV-Auth-Token': api_key,
        'Content-Type': 'application/json'
    }

    try:
        data = {
            "type": "standard",
            "payment_method": "bank_card",
            "bank_card_id": 3903871,
            "is_client_notification_enabled": True,
            "is_contact_person_notification_enabled": True,
            "vehicle_type_id": 6,
            "matter": "цветы",
            "total_weight_kg": 3,
            "points": [{
                "address": dict_start_point[point_start_delivery]["address"],
                "latitude": dict_start_point[point_start_delivery]["lat"],
                "longitude": dict_start_point[point_start_delivery]["lon"],
                "required_start_datetime": (time_client_delivery - datetime.timedelta(hours=1)).isoformat() + "+03:00",
                "required_finish_datetime": time_client_delivery.isoformat() + "+03:00",
                "note": dict_start_point[point_start_delivery]["comment"],
                "packages": [],
                "contact_person": {
                    "name": dict_start_point[point_start_delivery]["name"],
                    "phone": dict_start_point[point_start_delivery]["phone"]
                }
            },
                {
                "address": address,
                "latitude": lat,
                "longitude": lon,
                "required_start_datetime": time_client_delivery.isoformat() + "+03:00",
                "required_finish_datetime": (time_client_delivery + datetime.timedelta(hours=1)).isoformat() + "+03:00",
                "note": comment,
                "packages": [],
                "contact_person": {
                    "name": None,
                    "phone": phone
                }
                }]
        }
        py_logger.debug(f"data: {data}")
        dict_for_return = {}

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            async with session.post(url, headers=headers, json=data) as response:
                # Обработка ответа здесь
                res_json = await response.json()
                if res_json["is_successful"]:
                    py_logger.debug(f"res_json: {res_json}")
                    dict_for_return["number"] = res_json["order"]["order_id"]
                    dict_for_return["status"] = res_json["order"]["status"]
                    dict_for_return["tracking_url_collector"] = res_json["order"]["points"][0]["tracking_url"]
                    dict_for_return["tracking_url_client"] = res_json["order"]["points"][1]["tracking_url"]
                    py_logger.info(f"dict_for_return: {dict_for_return}")
                    return dict_for_return

                else:
                    py_logger.error(f"dostavista_make_order функция res_json: {res_json}")
                    return None

    except asyncio.CancelledError:
        py_logger.info("dostavista_make_order функция была остановлена")
        return None

    except Exception as e:
        py_logger.error(f"dostavista_make_order функция  ошибка: {e}")
        return None

