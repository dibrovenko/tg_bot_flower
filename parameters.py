
info_start_point = {"Калужское": {"lat": 55.601010,
                                      "lon": 37.471102,
                                      "address": "Москва, поселение Сосенское, Калужское шоссе, 22-й километр, 10",
                                      "phone": "+79161052259",
                                      "name": "Павел",
                                      "comment": "Домофон не работает"},
                        "Маяковского": {"lat": 55.738667,
                                        "lon": 37.658239,
                                        "address": "Москва, переулок Маяковского, дом 10, строение 6",
                                        "phone": "+79161052259",
                                        "name": "Павел",
                                        "comment": "Домофон не работает"},
                        "Смольная": {"lat": 55.860984,
                                     "lon": 37.482708,
                                     "address": "Москва, Смольная улица, 24Гс6",
                                     "phone": "+79161052259",
                                     "name": "Павел",
                                     "comment": "Домофон не работает"}}


admins = {
    "Паша": [310251240, "@paveldibr"],
    "Лева": [421278460, "@..."],
    #"Ваня": [450091492, "@..."],
    "Смольная": [5996434253, "@..."]
    }


collectors = {
    #"Паша": [310251240, "@paveldibr"],
    "Калужское": [6283299341, "@....."],
    "Маяковского": [6072410523, "@..."],
    "Смольная": [5996434253, "@..."]
    }


new = "Созданный заказ, ожидает одобрения оператора."
available = "Заказ одобрен оператором и доступен курьерам."
active = "Заказ выполняется курьером."
completed = "Заказ выполнен."
reactivated = "Заказ повторно активирован и вновь доступен курьерам."
draft = "Черновик заказа."
canceled = "Заказ отменен."
delayed = "Заказа отложен."

Order = {
    'new': new,
    'available': available,
    'active': active,
    'completed': completed,
    'reactivated': reactivated,
    'draft': draft,
    'canceled': canceled,
    'delayed': delayed
}


invalid = "Невалидный черновик доставки"
draft = "Черновик доставки"
planned = "Доставка запланирована (Курьер еще не назначен)"
active = "Доставка выполняется (Курьер в пути)"
finished = "Доставка завершена (Курьер доставил посылку)"
canceled = "Доставка на точку отменена"
delayed = "Доставка на точку отложена"
failed = "Доставка на точку не состоялась (Курьер не смог найти клиента)"
courier_assigned = "Курьер назначен, но еще никуда не выехал"
courier_departed = "Курьер выехал на точку забора"
courier_at_pickup = "Курьер приехал на точку забора"
parcel_picked_up = "Курьер взял посылку на точке забора"
courier_arrived = "Курьер приехал и ожидает клиента"
deleted = "Доставка удалена"
return_planned = "Возврат запланирован, курьер не назначен"
return_courier_assigned = "Курьер назначен на возврат"
return_courier_departed = "Курьер выехал на точку забора посылки на возврат"
return_courier_picked_up = "Курьер забрал и везёт возврат"
return_finished = "Возврат товара завершен"
reattempt_planned = "Повторная попытка вручения запланирована"
reattempt_courier_assigned = "Курьер для повторной попытки вручения назначен"
reattempt_courier_departed = "Курьер выехал за посылкой, для повторной попытки вручения"
reattempt_courier_picked_up = "Курьер забрал посылку и делает повторное вручение"
reattempt_finished = "Повторное вручение удалось"

Delivery = {
    'invalid': invalid,
    'draft': draft,
    'planned': planned,
    'active': active,
    'finished': finished,
    'canceled': canceled,
    'delayed': delayed,
    'failed': failed,
    'courier_assigned': courier_assigned,
    'courier_departed': courier_departed,
    'courier_at_pickup': courier_at_pickup,
    'parcel_picked_up': parcel_picked_up,
    'courier_arrived': courier_arrived,
    'deleted': deleted,
    'return_planned': return_planned,
    'return_courier_assigned': return_courier_assigned,
    'return_courier_departed': return_courier_departed,
    'return_courier_picked_up': return_courier_picked_up,
    'return_finished': return_finished,
    'reattempt_planned': reattempt_planned,
    'reattempt_courier_assigned': reattempt_courier_assigned,
    'reattempt_courier_departed': reattempt_courier_departed,
    'reattempt_courier_picked_up': reattempt_courier_picked_up,
    'reattempt_finished': reattempt_finished
}


dostavista_status = {"Order": Order, "Delivery": Delivery}