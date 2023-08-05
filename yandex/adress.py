import requests
from aiogram import types
import os
from dotenv import load_dotenv, find_dotenv

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

    except:
        return [False, " ", " "]

