from aiogram import types, Dispatcher
from aiogram.dispatcher.filters import IDFilter

from handlers.other import set_collectors_commands
from keyboards.collector_kb import kb_collector
from parameters import collectors


collector_list = [value[0] for value in collectors.values()]
#@dp.message_handler(commands=['collector'])
async def commands_collector(message: types.Message):
    await set_collectors_commands(message)
    await message.reply('Вы получили права сборщика', reply_markup=kb_collector)


def register_handlers_collector(dp: Dispatcher):
    dp.register_message_handler(commands_collector, IDFilter(collector_list), commands=['collector'])
