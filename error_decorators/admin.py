import logging
import os
from aiogram import types

# получение пользовательского логгера и установка уровня логирования
from aiogram.dispatcher import FSMContext

from create_bot import bot
from keyboards import kb_client

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

apology_text = "С сожалением сообщаем, что произошел непредвиденный сбой в работе нашего бота." \
               " Сделайте скриншот последних действий и напиши админу"


def dec_error_mes(func):
    async def wrapper(message: types.Message):
        try:
            return await func(message)
        except Exception as e:
            print(message)
            print()
            # Обработка ошибки
            await bot.send_sticker(chat_id=message.chat.id,
                                   sticker=r"CAACAgEAAxkBAAEKCMdk29ptkGokSTC9s9vYXCD4FtelXQACGgEAAjgOghG-CmKJFmOt7DAE")
            global apology_text
            await message.answer(text=apology_text, reply_markup=kb_client)
            py_logger.error(f"Ошибка: {e}, chat.id: {message.chat.id}")

    return wrapper


def dec_error_mes_state(func):
    async def wrapper(message: types.Message, state: FSMContext, *args):
        try:
            return await func(message, state, *args)
        except Exception as e:
            # Обработка ошибки
            await bot.send_sticker(chat_id=message.chat.id,
                                   sticker=r"CAACAgEAAxkBAAEKCMdk29ptkGokSTC9s9vYXCD4FtelXQACGgEAAjgOghG-CmKJFmOt7DAE")
            global apology_text
            await message.answer(text=apology_text, reply_markup=kb_client)
            py_logger.error(f"State: {await state.get_state()} \n Ошибка: {e}, chat.id: {message.chat.id}")
            await state.finish()

    return wrapper


def dec_error_callback_state(func):
    async def wrapper(callback: types.CallbackQuery, state: FSMContext):
        try:
            return await func(callback, state)
        except Exception as e:
            # Обработка ошибки
            await bot.send_sticker(chat_id=callback.message.chat.id,
                                   sticker=r"CAACAgEAAxkBAAEKCMdk29ptkGokSTC9s9vYXCD4FtelXQACGgEAAjgOghG-CmKJFmOt7DAE")
            global apology_text
            await callback.message.answer(text=apology_text)
            py_logger.error(
                f"State: {await state.get_state()} \n Ошибка: {e}, chat.id: {callback.message.chat.id}"
            )
            await state.finish()

    return wrapper
