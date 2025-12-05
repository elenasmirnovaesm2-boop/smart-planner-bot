# bot/today.py
from bot.keyboards import today_inline_keyboard
from bot.telegram_api import send_message, edit_message
from storage import list_today, get_task_by_id

def render_today_text():
    items = list_today()
    if not items:
        return (
            "На сегодня пока ничего нет.\n\n"
            "Открой задачу из инбокса и нажми «➡️ В Сегодня».",
            [],
        )

    lines = ["Задачи на сегодня:"]
    valid_items = []

    for it in items:
        task_id = it.get("task_id")
        if not task_id:
            continue
        task = get_task_by_id(task_id)
        if not task:
            continue
        mark = "✅" if task.get("done") else "[ ]"
        lines.append(f"{task['id']}. {mark} {task['text']}")
        valid_items.append(it)

    if len(valid_items) == 0:
        # все задачи из today уже удалены
        return (
            "Похоже, задачи, которые были в «Сегодня», уже удалены.\n\n"
            "Добавь новые задачи из инбокса.",
            [],
        )

    return "\n".join(lines), valid_items


def send_today(chat_id):
    text, items = render_today_text()
    kb = today_inline_keyboard(items)
    send_message(chat_id, text, reply_markup=kb)


def refresh_today(chat_id, message_id):
    text, items = render_today_text()
    kb = today_inline_keyboard(items)
    try:
        edit_message(chat_id, message_id, text, reply_markup=kb)
    except Exception:
        send_today(chat_id)
