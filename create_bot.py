import os
from dotenv import load_dotenv, find_dotenv

from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
storage = MemoryStorage()

load_dotenv(find_dotenv())

bot = Bot(token=os.getenv('bot_token'))
dp = Dispatcher(bot, storage=storage)


from handlers import client, admin, collector, other
client.register_handlers_clients(dp)
admin.register_handlers_admin(dp)
collector.register_handlers_collector(dp)
other.register_handlers_other(dp) #должен быть ниже всех
