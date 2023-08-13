from typing import Any

import requests
import os
from dotenv import load_dotenv, find_dotenv


def get_lan_lon_from_addrees(address: str) -> str | None:
    """
    функция, которая вычисляет коректность адреса
    :rtype если верно: [True, adress, lon, lat]
           если неверно: [False, adress, текст для ошибки]
    :param message:
    """

    # токен api yandex
    load_dotenv(find_dotenv())
    api_key_yandex = os.getenv('api_key_yandex_address')

    try:
        address = requests.get(f"https://geocode-maps.yandex.ru/1.x/?apikey={api_key_yandex}"
                               f"&geocode={address}&results=1&format=json").json()['response']["GeoObjectCollection"][
            "featureMember"][0]["GeoObject"]["Point"]['pos']
        return address

    except:
        return None
