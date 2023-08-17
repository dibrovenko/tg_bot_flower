import datetime
import ssl
import uuid
import os
import logging
import aiohttp
from dotenv import load_dotenv, find_dotenv

from parameters import info_start_point


py_logger = logging.getLogger(__name__)
py_logger.setLevel(logging.INFO)

# настройка обработчика и форматировщика в соответствии с нашими нуждами
log_file = os.path.join(f"log_directory/{__name__}.log")
py_handler = logging.FileHandler(log_file, mode='w')

#py_handler = logging.FileHandler(f"{__name__}.log", mode='w')
py_formatter = logging.Formatter("%(name)s %(asctime)s %(levelname)s %(message)s")

# добавление форматировщика к обработчику
py_handler.setFormatter(py_formatter)
# добавление обработчика к логгеру
py_logger.addHandler(py_handler)


async def calculate_price_yandex(lat: float, lon: float, address: str, available_points: list, phone_client: str,
                                 name_client: str, comment_client: str, ssl_context=None) -> list:
    """
    функция, которая вычисляет стоимость доставки в dostavista на сегодня и на завтра
    :rtype: data_for_return - [цена, место откуда везти, id заказа, который ждет подтверждения], а может быть просто [False]
    :param lat: широта
    :param lon: долгота
    :param available_points: ["Калужское", "Маяковского", "Смольная"]
    :param phone_client:
    :param name_client:
    :param comment_client:
    """
    try:
        now = datetime.datetime.now() - datetime.timedelta(hours=10) #- datetime.timedelta(minutes=20)
        if now.hour < 9 or now.hour > 19:
            py_logger.info(f"calculate_price_yandex data_for_return: {[False]}")
            return [False]
        py_logger.info(f"calculate_price_yandex nowtime: {now}")

        # время когда нужно приехать курьеру
        due_time = (now.astimezone() + datetime.timedelta(minutes=21)).replace(second=0, microsecond=0).isoformat()

        dict_start_point = info_start_point

        # Создаем новый словарь с помощью генератора списка и условного выражения
        new_dict_start_point = {k: v for k, v in dict_start_point.items() if k in available_points}

        # проверка стоимости
        load_dotenv(find_dotenv())
        api_key = os.getenv('api_key_yandex_delivery')

        # URL для отправки запроса_для проверки цены
        url = "https://b2b.taxi.yandex.net/b2b/cargo/integration/v2/check-price"

        # Заголовки запроса
        headers = {
            'Authorization': f'Bearer {api_key}',
            "Accept-Language": 'en-US'
        }

        min_value_list = [100000, "test"]
        for key in new_dict_start_point:
            # Тело запроса
            data = {

                "requirements": {
                    "taxi_class": "express"
                },
                "route_points": [
                    {
                        # "coordinates": [55.830907, 37.497863],
                        "fullname": new_dict_start_point[key]["address"]
                    },
                    {
                        # "coordinates": [55.863550, 37.478459],
                        "fullname": address
                    }
                ],
                "skip_door_to_door": False
            }

            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
                async with session.post(url, headers=headers, json=data) as response:
                    # Обработка ответа здесь
                    res_json = await response.json()
                    price = res_json['price']
                    if min_value_list[0] > float(price):
                        min_value_list[0] = float(price)
                        min_value_list[1] = key


        # URL для отправки запроса
        url = f"https://b2b.taxi.yandex.net/b2b/cargo/integration/v2/claims/create?request_id={str(uuid.uuid4())}"

        # Тело запроса
        data = {

            "callback_properties": {
                "callback_url": "https://test.pavel0dibr.repl.co/updated_ts=&"
            },
            "client_requirements": {
                "pro_courier": False,
                "taxi_class": "express"
            },
            "comment": "доставка цветов",
            #"due": due_time,
            "emergency_contact": {
                "name": new_dict_start_point[f"{min_value_list[1]}"]["name"],
                "phone": new_dict_start_point[f"{min_value_list[1]}"]["phone"]
            },

            "client_requirements": {
                "taxi_class": "express"
            },

            "items": [{
                "cost_currency": "RUB",
                "cost_value": "0",
                "droppof_point": 6992,
                "pickup_point": 6987,
                "quantity": 1,
                "title": "Цветы"
            }],
            "optional_return": False,
            "route_points": [{
                "address": {
                    "comment": new_dict_start_point[f"{min_value_list[1]}"]["comment"],
                    "fullname": new_dict_start_point[f"{min_value_list[1]}"]["address"],
                    "coordinates": [new_dict_start_point[f"{min_value_list[1]}"]["lon"],
                                    new_dict_start_point[f"{min_value_list[1]}"]["lat"]], #[37.733850, 55.779398]
                },
                "contact": {
                    "name": new_dict_start_point[f"{min_value_list[1]}"]["name"],
                    "phone": new_dict_start_point[f"{min_value_list[1]}"]["phone"]
                },
                # "pickup_code": "893422",
                "point_id": 6987,
                "skip_confirmation": False,
                "type": "source",
                "visit_order": 1
            },
                {
                    "address": {
                        "comment": comment_client,
                        "fullname": address,
                        "coordinates": [lon, lat], #[37.723178, 55.794786],
                    },
                    "contact": {
                        "name": " ",
                        "phone": phone_client
                    },
                    # "pickup_code": "893422",
                    "point_id": 6992,
                    "skip_confirmation": False,
                    "type": "destination",
                    "visit_order": 2
                }
            ],
            "skip_client_notify": False,
            "skip_door_to_door": False,
            "skip_emergency_notify": False,
        }

        # Отправка POST-запроса и получение ответа
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            async with session.post(url, headers=headers, json=data) as response:
                # Обработка ответа здесь
                res_json = await response.json()
                min_value_list.append(res_json["id"])

        py_logger.info(f"calculate_price_yandex data_for_return: {min_value_list}")
        return min_value_list

    except Exception as e:
        py_logger.error(f"функция calculate_price_yandex, message:, Ошибка: {e}")



