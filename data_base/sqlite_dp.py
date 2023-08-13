import asyncpg_listen
import asyncpg
import asyncio
import sqlite3 as sq
import re
import pandas as pd
from create_bot import dp, bot, types
import os
from dotenv import load_dotenv, find_dotenv

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
    global base, cur
    base = sq.connect('flower_cool.db')
    cur = base.cursor()

    con = await connect_to_base()
    await con.execute(
        'CREATE TABLE IF NOT EXISTS goods(img TEXT, name TEXT PRIMARY KEY, name_english TEXT,'
        ' category TEXT, subcategory TEXT, description TEXT, quantity1 INTEGER, quantity2 INTEGER,'
        ' quantity3 INTEGER, visibility CHAR(4), price FLOAT)'
    )

    await con.execute(
        'CREATE TABLE IF NOT EXISTS orders(number UUID PRIMARY KEY, name_english TEXT, name TEXT, quantity INTEGER, '
        'delivery_cost FLOAT, flower_cost FLOAT, pack_cost FLOAT, discount FLOAT, promo_code VARCHAR(32), '
        'full_cost FLOAT, name_client TEXT, phone_client VARCHAR(15), name_tg_client VARCHAR(32), chat_id_client INTEGER, '
        'phone_client2 VARCHAR(15), address TEXT, way_of_delivery TEXT, time_delivery TIMESTAMP, link_delivery TEXT, '
        'comment_courier TEXT, comment_collector TEXT, message_id_client INTEGER, message_id_collector INTEGER,'
        'status_order TEXT, step_collector TEXT, point_start_delivery TEXT, mark INTEGER)'
    )
    await con.close()


async def add_positions_sql(table_name: str, columns: list, values: list):
    con = await connect_to_base()

    try:
        # Формируем SQL запрос для вставки новой строки
        query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES " \
                f"({', '.join([f'${index + 1}' for index, _ in enumerate(values)])})"

        # Выполняем запрос с переданными значениями
        await con.execute(query, *values)

        # Выполнение уведомления об изменении
        if table_name == "goods":
            await con.execute(f"NOTIFY update_goods, '{1}'")

    except:
        # Возврат значения по умолчанию в случае ошибки
        return False

    finally:
        # Закрытие соединения с базой данных
        await con.close()

    return True


async def get_positions_sql(*args: str, table_name: str, condition=None, condition_value=None):
    con = await connect_to_base()
    try:
        # Формирование SQL-запроса
        query = "SELECT "

        # Добавление столбцов в запрос
        query += ", ".join(args) + f" FROM {table_name}"

        # Добавление условия в запрос (если оно указано)
        if condition and condition_value:
            query += " " + condition
            result = await con.fetch(query, condition_value)

        elif condition:
            query += " " + condition
            result = await con.fetch(query)

        else:
            result = await con.fetch(query)

    except:
        # Возврат значения по умолчанию в случае ошибки
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

    except:
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
        await con.execute(query)
        # Выполнение уведомления об изменении
        if table_name == "goods":
            await con.execute(f"NOTIFY update_goods, '{1}'")

    except Exception as e:
        print(f"Ошибка при обновлении данных: {str(e)}")
        # Возврат значения по умолчанию в случае ошибки
        return False

    finally:
        # Закрытие соединения с базой данных
        await con.close()

    return True


async def handle_notifications(notification: asyncpg_listen.NotificationOrTimeout) -> None:
    global notification_received
    print(f"{notification} has been received")
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
        print("функция остановлена")
        return True

    except:
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
                                      "time_delivery", "link_delivery", "comment_courier", "comment_collector",
                                      "message_id_client", "message_id_collector", "status_order", "step_collector",
                                      "point_start_delivery", "mark"]}
            # Создание DataFrame из результата запроса
            df = pd.DataFrame(result, columns=dict_colums[table_name])
            # Экспорт DataFrame в Excel таблицу
            df.to_excel(file_path, index=False)

    except:
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

    except:
        return False

    finally:
        # Закрытие соединения с базой данных
        await conn.close()

    return True
