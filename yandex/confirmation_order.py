import ssl
import aiohttp
import os
import logging
from dotenv import load_dotenv, find_dotenv


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


async def confirmation_order(id: str) -> bool:
    py_logger.debug("confirmation_order")
    load_dotenv(find_dotenv())
    api_key = os.getenv('api_key_yandex_delivery')

    url = f'https://b2b.taxi.yandex.net/b2b/cargo/integration/v2/claims/accept?claim_id={id}'
    # Заголовки запроса
    headers = {
        'Authorization': f'Bearer {api_key}',
        "Accept-Language": 'en-US'
    }
    # Тело запроса quantity
    data = {
        "version": 1
    }

    try:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            async with session.post(url, headers=headers, json=data) as response:
                # Обработка ответа здесь
                res_json = await response.json()
                py_logger.debug(f"res_json {res_json}")
                if res_json["status"] == "accepted":
                    return True
                else:
                    raise Exception("no accepted заказ")

    except Exception as e:
        py_logger.error(f"функция confirmation_order, Ошибка: {e}")
        return False