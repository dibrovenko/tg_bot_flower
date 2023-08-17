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

apology_text = "С сожалением сообщаем, что произошел непредвиденный сбой в работе нашего бота. Мы приносим искренние " \
               "извинения за возникшие неудобства и хотим заверить вас, что мы уже работаем над исправлением этой " \
               "проблемы. \n\nДля того, чтобы продолжить пользоваться нашими услугами, рекомендуем перезапустить бота "\
               "/start. Это поможет устранить возникший сбой и вернуть все функции в полную работоспособность. \n\nМы "\
               "ценим ваше терпение и понимание. В ближайшее время мы примем все необходимые меры, чтобы предотвратить"\
               " подобные ситуации в будущем. Если перезапуск не решит проблему, нажмите /problem. Еще раз приносим " \
               "извинения за доставленные неудобства и благодарим вас за вашу лояльность."

apology_text_pay = "К сожалению, возникла ошибка на этапе оплаты вашего заказа. Мы приносим свои извинения за " \
                   "доставленные неудобства./n/nДля того чтобы помочь вам решить данную проблему, мы рекомендуем вам " \
                   "обратиться к администратору. Пожалуйста, отправьте боту команду /problem. Администратор будет " \
                   "уведомлен о вашей проблеме и предпримет необходимые действия для ее разрешения./n/nМы ценим ваше " \
                   "терпение и сделаем все возможное, чтобы исправить эту ситуацию как можно скорее."


def dec_error_mes(func):
    async def wrapper(message: types.Message):
        try:
            return await func(message)
        except Exception as e:
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


def dec_error_mes_state_collector(func):
    async def wrapper(message: types.Message, state: FSMContext, comment_collector: str | None = None):
        try:
            return await func(message, state, comment_collector)
        except Exception as e:
            # Обработка ошибки
            await bot.send_sticker(chat_id=message.chat.id,
                                   sticker=r"CAACAgEAAxkBAAEKCMdk29ptkGokSTC9s9vYXCD4FtelXQACGgEAAjgOghG-CmKJFmOt7DAE")
            global apology_text
            await message.answer(text=apology_text, reply_markup=kb_client)
            py_logger.error(f"State: {await state.get_state()} \n Ошибка: {e}, chat.id: {message.chat.id}")
            await state.finish()

    return wrapper


def dec_error_send_way_delivery(func):
    async def wrapper(message: types.Message, state: FSMContext, price_yandex: int, min_price_today: int,
                      min_price_tommorow: int, start_time_today: str, text: str | None = None):
        try:
            return await func(message, state, price_yandex, min_price_today, min_price_tommorow, start_time_today, text)
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


def dec_error_mes_state_pay(func):
    async def wrapper(message: types.Message, state: FSMContext, *args):
        try:
            return await func(message, state, *args)
        except Exception as e:
            # Обработка ошибки
            await bot.send_sticker(chat_id=message.chat.id,
                                   sticker=r"CAACAgEAAxkBAAEKCMdk29ptkGokSTC9s9vYXCD4FtelXQACGgEAAjgOghG-CmKJFmOt7DAE")
            global apology_text_pay
            await message.answer(text=apology_text, reply_markup=kb_client)
            py_logger.error(f"State: {await state.get_state()} \n Ошибка: {e}, chat_id: {message.chat.id}")
            await state.finish()

    return wrapper
