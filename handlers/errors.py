import logging
import os

from aiogram import Dispatcher
from aiogram.utils.exceptions import (Unauthorized, MessageCantBeDeleted, MessageToDeleteNotFound, MessageNotModified,
                                      MessageTextIsEmpty, CantParseEntities, CantDemoteChatCreator, InvalidQueryID,
                                      RetryAfter, TelegramAPIError, BadRequest)
from create_bot import dp

# получение пользовательского логгера и установка уровня логирования
py_logger = logging.getLogger(__name__)
py_logger.setLevel(logging.ERROR)

# настройка обработчика и форматировщика в соответствии с нашими нуждами
log_file = os.path.join(f"log_directory/{__name__}.log")
py_handler = logging.FileHandler(log_file, mode='w')

# py_handler = logging.FileHandler(f"{__name__}.log", mode='w')
py_formatter = logging.Formatter("%(name)s %(asctime)s %(levelname)s %(message)s")

# добавление форматировщика к обработчику
py_handler.setFormatter(py_formatter)
# добавление обработчика к логгеру
py_logger.addHandler(py_handler)


#@dp.errors_handler()
async def errors_handler(update, exception):

    # Сообщение для удаления не найдено.
    if isinstance(exception, MessageToDeleteNotFound):
        py_logger.error("Message to delete not found.")
        return True

    # Сообщение не может быть удалено.
    if isinstance(exception, MessageCantBeDeleted):
        py_logger.error(f"Message cant be deleted.")
        return True

    # Сообщение не изменено.
    if isinstance(exception, MessageNotModified):
        py_logger.info('Message is not modified.')
        return True

    # Неавторизованный
    if isinstance(exception, Unauthorized):
        py_logger.error(f"Unauthorized: {exception}")
    return True

    # Текст сообщения пуст.
    if isinstance(exception, MessageTextIsEmpty):
        py_logger.debug('Message text is empty.')
        return True

    # Не идается разобрать объекты
    if isinstance(exception, CantParseEntities):
        py_logger.debug(f'Can\'t parse entities. ExceptionArgs: {exception.args}')
        return True


    # Невозможно понизить создателя чата.
    if isinstance(exception, CantDemoteChatCreator):
        py_logger.debug('Can\'+ demote chat creator.')
        return True

    # Недопустимый идентификатор запраса
    if isinstance(exception, InvalidQueryID):
        py_logger.error(f"InvalidQUeryID: {exception} \nUpdate: {update}")
        return True

    # Повторить после
    if isinstance(exception, RetryAfter):
        py_logger.error(f'RetryAfter: {exception} \nUpdate: {update}')
        return True

    # Неверный запрос
    if isinstance(exception, BadRequest):
        py_logger.error(f'BadRequest: {exception} \nUpdate: {fupdate}')
        return True

    # Ошибка API Telegram
    if isinstance(exception, TelegramAPIError):
        py_logger.error(f"TelegramAPIError: {update} \nUpdate: {update}")
        return True

    # Другая ошибка
    py_logger.error(f"Update: {update} \nException: {exception}")


# Регистрируем хендлеры
def register_handlers_error(dp: Dispatcher):
    dp.register_errors_handler(errors_handler)