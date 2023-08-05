import ssl
import aiohttp
import os
from dotenv import load_dotenv, find_dotenv

async def confirmation_order(id: str):

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

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        async with session.post(url, headers=headers, json=data) as response:
            # Обработка ответа здесь
            res_json = await response.json()
            print(res_json)