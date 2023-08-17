import requests
from aiogram import types
import os
import logging
from dotenv import load_dotenv, find_dotenv


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


def address_correctness_check(message: types.Message) -> list:
    """
    функция, которая вычисляет коректность адреса
    :rtype если верно: [True, adress, lon, lat]
           если неверно: [False, adress, текст для ошибки]
    :param message:
    """

    # токен api yandex
    load_dotenv(find_dotenv())
    api_key_yandex = os.getenv('api_key_yandex_address')

    if message.location is not None:
        data = f'{message.location["longitude"]},{message.location["latitude"]}'
    elif message.text is not None and len(message.text) > 5:
        data = message.text
    else:
        return [False, " ", " "]

    try:
        address = requests.get(f"https://geocode-maps.yandex.ru/1.x/?apikey={api_key_yandex}"
                               f"&geocode={data}&results=1&format=json").json()['response']["GeoObjectCollection"][
            "featureMember"][0]["GeoObject"]

        points = address["Point"]['pos']
        kind = address["metaDataProperty"]["GeocoderMetaData"]["kind"]
        text = address["metaDataProperty"]["GeocoderMetaData"]["text"].split(', ', 1)[1]
        exact = address["metaDataProperty"]["GeocoderMetaData"]["precision"]
        city = address["metaDataProperty"]["GeocoderMetaData"]["Address"]["Components"][2]["name"]

        if exact == "other" and kind !="district" and kind != "street":
            return [False, " ", " "]
        elif city != "Москва" and city != "Московская область":
            return [False, "Вы указали: " + text, ". Мы доставляем только в Москву и в Мос область"]
        elif kind != "house":
            return [False, "Вы указали: " + text, ". Вы не указали номер дома"]
        elif exact != "exact":
            return [False, "Вы указали: " + text, ". Неточный адресс"]
        else:
            return [True, text, float(points.split()[0]), float(points.split()[1])]

    except Exception as e:
        py_logger.error(f"функция adress, message: {message}, Ошибка: {e}")
        return [False, " ", " "]

