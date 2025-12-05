from bot.keyboards import today_inline_keyboard
from bot.telegram_api import send_message, edit_message
from storage import list_today, get_task_by_id


def render_today_text():
    items = list_today()
    buttons_tasks = []

    if not items:
        text = (
            "На сегодня пока ничего нет.\n\n"
            "Открой задачу из инбокса и нажми «➡️ В Сегодня»."
        )
        return text, buttons_tasks

    lines = ["Задачи на сегодня:"]
    for it in items:
        task_id = it.get("task_id")
        if not task_id:
            continue
        task = get_task_by_id(task_id)
        if not task:
            continue

        mark = "✅" if task.get("done") else "[ ]"
        lines.append(f"{task['id']}. {mark} {task['text']}")

        # данные для кнопок
        buttons_tasks.append({"id": task["id"], "text": task["text"]})

    if len(lines) == 1:
        lines.append("Похоже, задачи были удалены. Добавь новые из инбокса.")

    return "\n".join(lines), buttons_tasks


def send_today(chat_id):
    text, buttons_tasks = render_today_text()
    kb = today_inline_keyboard(buttons_tasks)
    send_message(chat_id, text, reply_markup=kb)


def refresh_today(chat_id, message_id):
    text, buttons_tasks = render_today_text()
    kb = today_inline_keyboard(buttons_tasks)
    try:
        edit_message(chat_id, message_id, text, reply_markup=kb)
    except Exception:
        send_today(chat_id)