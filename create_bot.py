import os
from dotenv import load_dotenv, find_dotenv

from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()
storage = MemoryStorage()

load_dotenv(find_dotenv())

bot = Bot(token=os.getenv('bot_token'))
dp = Dispatcher(bot, storage=storage, run_tasks_by_default=True)


from handlers import client, admin, collector, order_from_collector, other, errors, client_order_end
client.register_handlers_clients(dp)
admin.register_handlers_admin(dp)
collector.register_handlers_collector(dp)
order_from_collector.register_handlers_collector(dp)
client_order_end.register_handlers_client_order_end(dp)
errors.register_handlers_error(dp)
other.register_handlers_other(dp) #должен быть ниже всех

