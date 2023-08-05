from aiogram.utils import executor
from create_bot import dp, bot
from data_base import sqlite_dp

import emoji

from aiogram.contrib.fsm_storage.memory import MemoryStorage
storage = MemoryStorage()

print(emoji.emojize(':thumbs_up:'))


async def on_startup(_):
    print('Бот вышел в онлайн')
    sqlite_dp.sql_start()



from handlers import client, admin, collector, other
client.register_handlers_clients(dp)
admin.register_handlers_admin(dp)
collector.register_handlers_collector(dp)
other.register_handlers_other(dp) #должен быть ниже всех



executor.start_polling(dp, skip_updates=True, on_startup=on_startup)



