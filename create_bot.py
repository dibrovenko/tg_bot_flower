from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher

from aiogram.contrib.fsm_storage.memory import MemoryStorage
storage = MemoryStorage()


bot = Bot(token = "6298386098:AAF5AvPZAdujTZOneKOGvAGHpjMGZKZ_dgg")
dp = Dispatcher(bot, storage=storage)