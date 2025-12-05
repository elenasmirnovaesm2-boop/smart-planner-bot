# bot/keyboards.py

def main_keyboard():
    return {
        "keyboard": [
            [{"text": "📥 Инбокс"}, {"text": "📅 Сегодня"}],
            [{"text": "🔁 Рутины"}, {"text": "📋 Шаблоны"}, {"text": "📂 Проекты"}],
            [{"text": "🆘 SOS"}, {"text": "📊 Привычки"}, {"text": "⚙️ Меню"}],
        ],
        "resize_keyboard": True,
    }


def inbox_inline_keyboard(tasks):
    """
    Кнопки для инбокса: показываем номер и короткий текст задачи.
    Пример: "1. Купить молоко".
    """
    task_buttons = []
    for t in tasks:
        full_text = t.get("text", "") or "(без текста)"
        short = (full_text[:25] + "…") if len(full_text) > 25 else full_text
        label = f"{t['id']}. {short}"

        btn = {
            "text": label,
            "callback_data": f"task_open:{t['id']}",
        }
        task_buttons.append([btn])

    common = [
        [
            {"text": "➕ Добавить", "callback_data": "inbox_add"},
            {"text": "🔄 Обновить", "callback_data": "inbox_refresh"},
        ],
        [{"text": "⬅️ В меню", "callback_data": "back_menu"}],
    ]
    return {"inline_keyboard": common + task_buttons}


def today_inline_keyboard(tasks_for_buttons):
    """
    Кнопки для «Сегодня».
    tasks_for_buttons: список словарей {"id": ..., "text": ...}
    """
    task_buttons = []
    for t in tasks_for_buttons:
        task_id = t["id"]
        full_text = t.get("text", "") or "(без текста)"
        short = (full_text[:25] + "…") if len(full_text) > 25 else full_text
        label = f"{task_id}. {short}"

        btn = {
            "text": label,
            "callback_data": f"task_open:{task_id}",
        }
        task_buttons.append([btn])

    common = [
        [{"text": "🔄 Обновить", "callback_data": "today_refresh"}],
        [{"text": "⬅️ В меню", "callback_data": "back_menu"}],
    ]
    return {"inline_keyboard": common + task_buttons}


def task_inline_keyboard(task_id):
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Готово", "callback_data": f"task_done:{task_id}"},
                {"text": "✏️ Редактировать", "callback_data": f"task_edit:{task_id}"},
            ],
            [
                {"text": "🗑 Удалить", "callback_data": f"task_delete:{task_id}"},
                {"text": "➡️ В Сегодня", "callback_data": f"task_today:{task_id}"},
            ],
            [
                {"text": "🔁 В рутину", "callback_data": f"task_to_routine:{task_id}"},
                {"text": "⬅️ В инбокс", "callback_data": "back_inbox"},
            ],
        ]
    }


def simple_list_keyboard(prefix, items):
    """
    Универсальная клавиатура для сущностей:
    prefix: 'routine', 'template', 'project', 'sos', 'habit'
    """
    rows = []
    for it in items:
        text = f"{it.get('id', '')}. {it.get('name', 'Без названия')}"
        rows.append([{
            "text": text,
            "callback_data": f"{prefix}_open:{it['id']}"
        }])
    rows.append([{"text": "⬅️ В меню", "callback_data": "back_menu"}])
    return {"inline_keyboard": rows}