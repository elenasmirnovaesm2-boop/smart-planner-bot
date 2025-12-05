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
    task_buttons = []
    for t in tasks:
        btn = {
            "text": f"#{t['id']}",
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


def today_inline_keyboard(items):
    task_buttons = []
    for it in items:
        task_id = it.get("task_id")
        if not task_id:
            continue
        btn = {
            "text": f"#{task_id}",
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
                {"text": "⬅️ В инбокс", "callback_data": "back_inbox"},
            ],
        ]
    }


def simple_list_keyboard(prefix, items):
    rows = []
    for it in items:
        text = f"{it.get('id', '')}. {it.get('name', 'Без названия')}"
        rows.append([{
            "text": text,
            "callback_data": f"{prefix}_open:{it['id']}"
        }])
    rows.append([{"text": "⬅️ В меню", "callback_data": "back_menu"}])
    return {"inline_keyboard": rows}
