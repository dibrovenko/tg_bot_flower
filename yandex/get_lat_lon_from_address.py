import requests
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
        py_logger.info(f"get_lan_lon_from_addrees data_for_return: {address}")
        return address

    except Exception as e:
        py_logger.info(f"get_lan_lon_from_addrees ошибка: {e}")
        return None
