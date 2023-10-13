import asyncpg_listen
import asyncpg
import asyncio
import sqlite3 as sq
import pandas as pd
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


# Flag variable to indicate if handle_notifications has been triggered
notification_received = False

async def connect_to_base():
    load_dotenv(find_dotenv())
    host = os.getenv('host_dp')
    user = os.getenv('user_dp')
    password = os.getenv('password_dp')
    database = os.getenv('name_dp')
    port = os.getenv('port_dp')

    con = await asyncpg.connect(host=host, user=user, password=password, database=database, port=port)
    return con


async def sql_start():
    """"
    global base, cur
    base = sq.connect('flower_cool.db')
    cur = base.cursor()
    """
    con = await connect_to_base()
    await con.execute(
        'CREATE TABLE IF NOT EXISTS goods(img TEXT, name TEXT PRIMARY KEY, name_english TEXT,'
        ' category TEXT, subcategory TEXT, description TEXT, quantity1 INTEGER, quantity2 INTEGER,'
        ' quantity3 INTEGER, visibility CHAR(4), price FLOAT)'
    )

    await con.execute(
        'CREATE TABLE IF NOT EXISTS orders(number VARCHAR(40) PRIMARY KEY, name_english TEXT, name TEXT, quantity '
        'INTEGER, delivery_cost FLOAT, flower_cost FLOAT, pack_cost FLOAT, discount FLOAT, promo_code VARCHAR(32), '
        'full_cost FLOAT, name_client TEXT, phone_client VARCHAR(15), name_tg_client VARCHAR(32), chat_id_client '
        'BIGINT, phone_client2 VARCHAR(15), address TEXT, way_of_delivery TEXT, time_delivery TIMESTAMP, '
        'time_delivery_end TIMESTAMP, link_collector TEXT, link_client TEXT, comment_courier TEXT, '
        'comment_collector TEXT, message_id_client BIGINT, message_id_collector BIGINT, status_order TEXT, '
        'step_collector TEXT, point_start_delivery TEXT, mark INTEGER, message_id_client2 BIGINT, '
        'message_id_collector2 BIGINT, courier_name TEXT, courier_phone VARCHAR(15), img TEXT)'
    )
    await con.close()


async def add_positions_sql(table_name: str, columns: list, values: list):
    con = await connect_to_base()

    try:
        # Формируем SQL запрос для вставки новой строки
        query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES " \
                f"({', '.join([f'${index + 1}' for index, _ in enumerate(values)])})"

        # Выполняем запрос с переданными значениями
        py_logger.info(f"add_positions_sql query: {query}, {values}")
        record = await con.execute(query, *values)
        py_logger.info(f"record: {record}")

        # Выполнение уведомления об изменении
        if table_name == "goods":
            await con.execute(f"NOTIFY update_goods, '{1}'")

    except Exception as e:
        # Возврат значения по умолчанию в случае ошибки
        py_logger.error(f"Не добавились данные в базу данных. table_name: {table_name}, columns: {columns},"
                        f" values: {values} , Ошибка: {e}")
        return False

    finally:
        # Закрытие соединения с базой данных
        await con.close()

    return True


async def get_positions_sql(*args: str, table_name: str, condition=None, condition_value=None):
    con = await connect_to_base()
    try:
        py_logger.info(f"get_positions_sql запустилась")
        # Формирование SQL-запроса
        query = "SELECT "

        # Добавление столбцов в запрос
        query += ", ".join(args) + f" FROM {table_name}"
        py_logger.info(f"query: {query}")

        # Добавление условия в запрос (если оно указано)
        if condition and condition_value:
            query += " " + condition
            py_logger.debug(f"query: {query} {condition_value}")
            result = await con.fetch(query, condition_value)
            py_logger.debug(f"result: {result}")

        elif condition:
            query += " " + condition
            py_logger.debug(f"query: {query}")
            result = await con.fetch(query)
            py_logger.debug(f"result: {result}")

        else:
            py_logger.info(f"query: {query}")
            result = await con.fetch(query)
            py_logger.debug(f"result: {result}")

    except Exception as e:
        # Возврат значения по умолчанию в случае ошибки
        py_logger.error(f"Не выдали данные из базы данных. table_name: {table_name}, condition:{condition}, "
                        f"condition_value:{condition_value}, Ошибка: {e}")
        return None

    finally:
        # Закрытие соединения с базой данных
        await con.close()

    return result


async def del_positions_sql(table_name: str, condition: str, value: str):
    con = await connect_to_base()
    try:
        # Формируем SQL запрос для вставки новой строки
        query = f'DELETE FROM {table_name} {condition}'

        # Выполняем запрос с переданными значениями
        await con.execute(query, value)

        # Выполнение уведомления об изменении
        if table_name == "goods":
            await con.execute(f"NOTIFY update_goods, '{1}'")

    except Exception as e:
        py_logger.error(f"Не удалили данные из базы данных. table_name: {table_name}, condition: {condition}, "
                        f"value: {value}, Ошибка: {e}")
        # Возврат значения по умолчанию в случае ошибки
        return False

    finally:
        # Закрытие соединения с базой данных
        await con.close()

    return True


async def update_positions_sql(table_name: str, column_values: dict, condition=None):
    con = await connect_to_base()
    try:
        # Формирование SQL-запроса для обновления данных
        query = f"UPDATE {table_name} SET "

        # Добавление значений столбцов для обновления
        for column, value in column_values.items():
            query += f"{column} = '{value}', "

        # Удаление последней запятой и пробела из запроса
        query = query[:-2]

        # Добавление условия для обновления данных (если указано)
        if condition:
            query += f" {condition}"

        # Выполнение SQL-запроса
        py_logger.info(f"query: {query}")
        await con.execute(query)
        # Выполнение уведомления об изменении
        if table_name == "goods":
            await con.execute(f"NOTIFY update_goods, '{1}'")

    except Exception as e:
        py_logger.error(f"Не обновили данные из базы данных. table_name: {table_name}, condition: {condition}, "
                        f"column_values: {column_values}, Ошибка: {e}")
        # Возврат значения по умолчанию в случае ошибки
        return False

    finally:
        # Закрытие соединения с базой данных
        await con.close()

    return True


async def handle_notifications(notification: asyncpg_listen.NotificationOrTimeout) -> None:
    global notification_received
    py_logger.info(f"{notification} has been received")
    notification_received = True


async def notifications_start():
    global notification_received
    load_dotenv(find_dotenv())
    host = os.getenv('host_dp')
    user = os.getenv('user_dp')
    password = os.getenv('password_dp')
    database = os.getenv('name_dp')
    port = os.getenv('port_dp')
    listener = asyncpg_listen.NotificationListener(asyncpg_listen.connect_func(database=database, user=user,
                                                                               password=password, host=host, port=port))
    listener_task = asyncio.create_task(
        listener.run(
            {"update_goods": handle_notifications},
            policy=asyncpg_listen.ListenPolicy.ALL,
            notification_timeout=3600
        )
    )

    try:
        while not notification_received:
            await asyncio.sleep(3)

    except asyncio.CancelledError:
        py_logger.info("функция notifications_start остановлена")
        return True

    except Exception as e:
        py_logger.error(f"функция notifications_start, Ошибка: {e}")
        return False

    finally:
        listener_task.cancel()
        notification_received = False

    return False


async def export_to_excel(table_name=None):
    # Подключение к базе данных
    conn = await connect_to_base()

    try:
        if not table_name:
            # Укажите путь к файлу Excel, который нужно удалить
            file_path = "Exel/data_goods.xlsx"

            # Проверяем, существует ли файл
            if os.path.exists(file_path):
                # Удаляем файл
                os.remove(file_path)

            # Выполнение запроса к базе данных
            query = 'SELECT name, name_english, price, quantity1, quantity2, quantity3, visibility FROM goods'
            result = await conn.fetch(query)

            # Создание DataFrame из результата запроса
            df = pd.DataFrame(result, columns=['name', 'name_english', 'price', 'quantity1', 'quantity2', 'quantity3',
                                               'visibility'])
            # Экспорт DataFrame в Excel таблицу
            df.to_excel(file_path, index=False)

        else:
            # Укажите путь к файлу Excel, который нужно удалить
            file_path = "Exel/data.xlsx"

            # Проверяем, существует ли файл
            if os.path.exists(file_path):
                # Удаляем файл
                os.remove(file_path)

            # Выполнение запроса к базе данных
            query = f'SELECT * FROM {table_name}'
            result = await conn.fetch(query)

            dict_colums = {"goods": ["img", "name", "name_english", "category", "subcategory", "description",
                                     "quantity1", "quantity2", "quantity3", "visibility", "price"],
                           "orders": ["number", "name_english", "name", "quantity", "delivery_cost", "flower_cost",
                                      "pack_cost", "discount", "promo_code", "full_cost", "name_client", "phone_client",
                                      "name_tg_client", "chat_id_client", "phone_client2", "address", "way_of_delivery",
                                      "time_delivery", "time_delivery_end", "link_collector", "link_client",
                                      "comment_courier", "comment_collector", "message_id_client",
                                      "message_id_collector", "status_order", "step_collector", "point_start_delivery",
                                      "mark", "message_id_client2",  "message_id_collector2", "courier_name",
                                      "courier_phone", "img"]}
            # Создание DataFrame из результата запроса
            df = pd.DataFrame(result, columns=dict_colums[table_name])
            # Экспорт DataFrame в Excel таблицу
            df.to_excel(file_path, index=False)

    except Exception as e:
        py_logger.error(f"функция export_to_excel, table_name: {table_name}, Ошибка: {e}")
        return False

    finally:
        # Закрытие соединения с базой данных
        await conn.close()
    return True


async def update_database_from_excel():
    # Подключение к базе данных
    conn = await connect_to_base()

    try:
        # Чтение данных из Excel файла
        df = pd.read_excel("Exel/data_goods.xlsx")

        # Получение списка колонок из базы данных
        columns = await conn.fetch(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'goods';")

        # Обновление данных в базе данных по каждой колонке из Excel файла
        for column in columns:
            column_name = column['column_name']

            if column_name in df.columns:
                values = df[column_name].tolist()

                # Обновление данных в базе данных с использованием параметризованного запроса
                await conn.executemany(f'UPDATE goods SET {column_name} = $1 WHERE name = $2;',
                                       zip(values, df['name'].tolist()))

    except Exception as e:
        py_logger.error(f"функция update_database_from_excel не смогла обновить данные, Ошибка: {e}")
        return False

    finally:
        # Закрытие соединения с базой данных
        await conn.close()

    return True
