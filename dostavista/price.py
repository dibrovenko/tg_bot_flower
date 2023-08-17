import datetime
import ssl
import asyncio
import aiohttp
import os
import logging
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



async def calculate_price_dostavista(lat: float, lon: float, address: str, vehicle_type_id: int, available_points: list, ssl_context=None) -> dict:
    """
            функция, которая вычисляет стоимость доставки в dostavista на сегодня и на завтра
            :rtype: data_for_return - {
                                       "today": { "время": [цена, место откуда везти], ... },
                                       'tomorrow': {8: [525.0, 'Маяковского'], час: [цена, место откуда везти],
                                        ... 19: [525.0, 'Маяковского']}
                                       }
            :param lat: широта
            :param lon: долгота
            :param vehicle_type_id: 6- (Пеший курьер), 7 — Легковой автомобиль.
            :param available_points: ["Калужское", "Маяковского", "Смольная"]
            """

    try:
        dict_start_point = info_start_point

        # Создаем новый словарь с помощью генератора списка и условного выражения
        new_dict_start_point = {k: v for k, v in dict_start_point.items() if k in available_points}
        # Создаем словарь для возвращения данных
        data_for_return = {"today": {}, "tomorrow": {}}

        #параметры запроса для dostavista
        load_dotenv(find_dotenv())
        api_key = os.getenv('api_key_dostavista')
        url = 'https://robot.dostavista.ru/api/business/1.3/calculate-order'
        headers = {
            'X-DV-Auth-Token': api_key,
            'Content-Type': 'application/json'
        }

        #запускаем цикл по получению цен на доставку на завтра
        time_to_create_list = datetime.datetime.now().astimezone().replace(hour=8, minute=0, second=0, microsecond=0) + datetime.timedelta(hours=24)
        while time_to_create_list.hour < 19 or (time_to_create_list.hour == 19 and time_to_create_list.minute == 0):

            min_value_list = [100000, "test"]
            for key in new_dict_start_point:
                data = {
                    "type": "standard",
                    "vehicle_type_id": vehicle_type_id,
                    "matter": "цветы",
                    "total_weight_kg": 0,
                    "points": [{
                        "address": new_dict_start_point[key]["address"],
                        "latitude": new_dict_start_point[key]["lat"],
                        "longitude": new_dict_start_point[key]["lon"],
                        "required_start_datetime": (time_to_create_list + datetime.timedelta(hours=1)).isoformat(),
                        "required_finish_datetime": (time_to_create_list + datetime.timedelta(hours=2)).isoformat()
                    },
                        {
                            "address": address,
                            "latitude": lat,
                            "longitude": lon,
                            "required_start_datetime": (time_to_create_list + datetime.timedelta(hours=2)).isoformat(),
                            "required_finish_datetime": (time_to_create_list + datetime.timedelta(hours=3)).isoformat()
                        }]
                }

                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
                    async with session.post(url, headers=headers, json=data) as response:
                        # Обработка ответа здесь
                        res_json = await response.json()
                        price = res_json["order"]["payment_amount"]
                        if min_value_list[0] > float(price):
                            min_value_list[0] = float(price)
                            min_value_list[1] = key
            data_for_return["tomorrow"][time_to_create_list.strftime("%H:%M")] = min_value_list

            time_to_create_list += datetime.timedelta(hours=1)


        # Здесь начинаем работать с сегодняшним временем
        # приводим время к правильному формату
        now = datetime.datetime.now().astimezone()# + datetime.timedelta(hours=0) - datetime.timedelta(minutes=26)
        py_logger.info(f"price nowtime: {now}")

        if now.minute < 15:
            rounded_time = now.replace(minute=0, second=0, microsecond=0)
        elif now.minute < 45:
            rounded_time = now.replace(minute=30, second=0, microsecond=0)
        else:
            rounded_time = now.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1)


        if rounded_time.hour < 19 or (rounded_time.hour == 19 and rounded_time.minute == 0):
            while rounded_time.hour < 19 or (rounded_time.hour == 19 and rounded_time.minute == 0):
                if rounded_time.hour > 7:
                    time_when_taking = {"start": (rounded_time + datetime.timedelta(hours=1)).isoformat(),
                                        "end": (rounded_time + datetime.timedelta(hours=2)).isoformat()}
                    time_when_giving = {"start": (rounded_time + datetime.timedelta(hours=2)).isoformat(),
                                        "end": (rounded_time + datetime.timedelta(hours=3)).isoformat()}
                    min_value_list = [100000, "test"]
                    for key in new_dict_start_point:
                        data = {
                            "type": "standard",
                            "vehicle_type_id": vehicle_type_id,
                            "matter": "цветы",
                            "total_weight_kg": 0,
                            "points": [{
                                "address": new_dict_start_point[key]["address"],
                                "latitude": new_dict_start_point[key]["lat"],
                                "longitude": new_dict_start_point[key]["lon"],
                                "required_start_datetime": (rounded_time + datetime.timedelta(hours=1)).isoformat(),
                                "required_finish_datetime": (rounded_time + datetime.timedelta(hours=2)).isoformat()
                            },
                                {
                                    "address": address,
                                    "latitude": lat,
                                    "longitude": lon,
                                    "required_start_datetime": (rounded_time + datetime.timedelta(hours=2)).isoformat(),
                                    "required_finish_datetime": (rounded_time + datetime.timedelta(hours=3)).isoformat()
                                }]
                        }

                        ssl_context = ssl.create_default_context()
                        ssl_context.check_hostname = False
                        ssl_context.verify_mode = ssl.CERT_NONE
                        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
                            async with session.post(url, headers=headers, json=data) as response:
                                # Обработка ответа здесь
                                res_json = await response.json()
                                price = res_json["order"]["payment_amount"]
                                if min_value_list[0] > float(price):
                                    min_value_list[0] = float(price)
                                    min_value_list[1] = key

                    data_for_return["today"][rounded_time.strftime("%H:%M")] = min_value_list

                rounded_time += datetime.timedelta(hours=1)
        else:
            data_for_return["today"] = False

        py_logger.info(f"price data_for_return: {data_for_return}")
        return data_for_return

    except asyncio.CancelledError:
        py_logger.info("Асинхронная функция price была остановлена")
        return {"today": False, 'tomorrow': False}

    except Exception as e:
        py_logger.error(f"Асинхронная функция price ошибка: {e}")
        return {"today": False, 'tomorrow': False}
