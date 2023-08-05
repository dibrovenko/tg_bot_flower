import sqlite3 as sq
import re
import pandas as pd
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from create_bot import dp, bot, types


def sql_start():
    global base, cur
    base = sq.connect('flower_cool.db')
    cur = base.cursor()
    if base:
        print('Data base connected OK!')
    base.execute('CREATE TABLE IF NOT EXISTS menu(img TEXT, name TEXT PRIMARY KEY, name_english TEXT, category TEXT, '
                 'subcategory TEXT, description TEXT, quantity1 INTEGER, quantity2 INTEGER, quantity3 INTEGER, '
                 'visibility CHAR, price FLOAT)')
    base.execute(
        'CREATE TABLE IF NOT EXISTS orders(number TEXT PRIMARY KEY, name_english TEXT, name TEXT, quantity INTEGER, '
        'delivery_cost FLOAT, flower_cost FLOAT, pack_cost FLOAT, discount FLOAT, promo_code VARCHAR(32), '
        'full_cost FLOAT, phone_client VARCHAR(15), name_tg_client VARCHAR(32), chat_id_client INTEGER, '
        'phone_client2 VARCHAR(15), address TEXT, way_of_delivery TEXT, time_delivery TIMESTAMP, link_delivery TEXT, '
        'comment_courier TEXT, comment_collector TEXT, message_id_client INTEGER, message_id_collector INTEGER,'
        'status_order TEXT, step_collector TEXT, point_start_delivery TEXT, mark INTEGER)')
    base.commit()


async def sql_add_command(state, table_name='menu', number_order=None):
    if table_name == 'menu':
        async with state.proxy() as data:
            cur.execute('INSERT INTO menu(img, name, name_english, category, subcategory, description, quantity1, quantity2,'
                        ' quantity3, visibility, price) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                        (str(data["photo"]), data["name"], data["name_english"], data["category"], data["subcategory"],
                         data["description"], data["quantity1"], data["quantity2"], data["quantity3"],
                         data["visibility"], data["price"]))
            base.commit()
    else:
        async with state.proxy() as data:
            cur.execute(f'INSERT INTO {table_name}(number, name_english, name, quantity, delivery_cost, flower_cost, '
                        f'pack_cost, discount, promo_code, full_cost, phone_client, name_tg_client, chat_id_client, '
                        f'phone_client2, address, way_of_delivery, time_delivery, link_delivery, comment_courier, '
                        f'comment_collector, message_id_client, message_id_collector, status_order, step_collector, '
                        f'point_start_delivery, mark) '
                        f'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                        (number_order, data["name_english"], data["name"], data["quantity"], ))
            base.commit()



async def sql_read(message: types.Message):

    for ret in cur.execute('SELECT * FROM menu').fetchall():
        caption = f'*{ret[1]}*\n_English_: *{ret[2]}*\n_Категория:_ *{ret[3]}*\n_Подкатегория:_ *{ret[4]}*\n_Описание:_ *{ret[5]}*' \
                  f'\n_Количество на Калужском:_ *{ret[6]}*\n_Количество на Маяковском:_ *{ret[7]}*\n_Количество на Смольной:_ *{ret[8]}*' \
                  f'\n_Видимость:_ *{ret[9]}*\n_Цена_ *{ret[-1]}*'
        album = types.MediaGroup()
        print()
        matches = re.findall(r"'(.*?)'", ret[0])
        for i, match in enumerate(matches):
            if i == len(matches) - 1:
                album.attach_photo(photo=match, caption=caption, parse_mode="Markdown")
            else:
                album.attach_photo(photo=match)

        await message.answer_media_group(media=album)


async def sql_read2():
    return cur.execute('SELECT * FROM menu').fetchall()


async def sql_read_name():
    list_name = []
    for ret in cur.execute('SELECT name, name_english FROM menu').fetchall():
        list_name.append([ret[0], ret[1]])
    return list_name


async def sql_read_name_english():
    list_name = []
    for ret in cur.execute('SELECT name_english FROM menu').fetchall():
        list_name.append(ret[0])
    return list_name


async def sql_del(data):
    cur.execute('DELETE FROM menu WHERE name == ?', (data,))
    base.commit()


async def sql_get_name(data, message: types.Message):
    return cur.execute('SELECT * FROM menu WHERE name_english == ?', (data,)).fetchall()

async def sql_get_phot_and_address(name):
    return cur.execute('SELECT quantity1, quantity2, quantity3, img FROM menu WHERE name == ?', (name,)).fetchall()


async def sql_update_data(name, column_name, new_value, table_name='menu'):
    cur.execute(f"UPDATE {table_name} SET {column_name} = ? WHERE name_english == ?", (new_value, name))
    base.commit()

async def exel_upload(message: types.Message):

    # Подключаемся к базе данных SQLite3 и получаем все данные из таблицы 'users'
    df = pd.read_sql_query("SELECT * FROM menu", base)

    # Указываем полный путь к файлу
    #path = r'/Users/paveldibrovenko/Desktop/tg_bot/data.xlsx'

    # Преобразуем данные в формат Excel и сохраняем в файл 'data.xlsx'
    df.to_excel('data.xlsx', index=False)

    # Отправляем файл пользователю
    with open('data.xlsx', 'rb') as file:
        await bot.send_document(message.chat.id, file)



async def get_quantity_by_name(name):

    # Координаты точек складов
    origin1 = '55.601010,37.471102'  # Москва, поселение Сосенское, Калужское шоссе, 22-й километр, 10
    origin2 = '55.738667,37.658239'  # г. Москва, переулок Маяковского, дом 10, строение 6
    origin3 = '55.860984,37.482708'  # Смольная улица, 24Гс6
    origin_list = [origin1, origin2, origin3]

    # Выполняем запрос к базе данных
    row = cur.execute("SELECT quantity1, quantity2, quantity3 FROM menu WHERE name=?", (name,)).fetchall()
    # Создаем словарь с данными из запроса
    data_dict = {}

    for i, origin in enumerate(origin_list):
        data_dict[origin] = row[0][i]

    return data_dict
