# bot/inbox.py
import re
import datetime
from bot.keyboards import inbox_inline_keyboard, task_inline_keyboard
from bot.telegram_api import send_message, edit_message
from storage import (
    add_task,
    list_active_tasks,
    update_task_text,
    complete_task_by_id,
    delete_task_by_id,
    add_today_from_task,
)


def parse_task_ids(text: str):
    """
    Парсит строку с номерами задач: '1 2 5-7' -> {1,2,5,6,7}
    Поддерживает пробелы, запятые и диапазоны через '-'.
    """
    ids = set()
    parts = re.split(r"[,\s]+", text.strip())
    for part in parts:
        if not part:
            continue
        if "-" in part:
            try:
                start_s, end_s = part.split("-", 1)
                start = int(start_s)
                end = int(end_s)
                if start > end:
                    start, end = end, start
                for i in range(start, end + 1):
                    ids.add(i)
            except ValueError:
                continue
        else:
            try:
                ids.add(int(part))
            except ValueError:
                continue
    return ids


def render_inbox_text():
    tasks = list_active_tasks()
    if not tasks:
        return (
            "📥 INBOX\n\n"
            "Инбокс пуст.\n\n"
            "Нажми «➕ Добавить», чтобы создать задачи.",
            tasks,
        )

    lines = [
        "📥 INBOX",
        "",
        "Твой инбокс:",
    ]
    for t in tasks:
        lines.append(f"{t['id']}. [ ] {t['text']}")
    return "\n".join(lines), tasks


def send_inbox(chat_id):
    text, tasks = render_inbox_text()
    kb = inbox_inline_keyboard(tasks)
    send_message(chat_id, text, reply_markup=kb)


def render_task_card(task):
    status = "выполнена ✅" if task.get("done") else "не выполнена"
    comment = task.get("done_comment")
    comment_part = f"\nКомментарий: {comment}" if comment else ""

    created_part = ""
    created = task.get("created_at")
    if created:
        try:
            dt = datetime.datetime.fromisoformat(created.replace("Z", ""))
            created_part = "\nСоздана: " + dt.strftime("%d.%m %H:%M")
        except Exception:
            created_part = "\nСоздана: " + str(created)

    return (
        f"Задача #{task['id']}\n\n"
        f"Текст: {task['text']}\n"
        f"Статус: {status}{comment_part}{created_part}"
    )


def handle_add_inbox_text(chat_id, text):
    from bot.telegram_api import send_message  # чтобы избежать циклических импортов

    lines = [line.strip() for line in text.split("\n")]
    lines = [ln for ln in lines if ln]

    if not lines:
        send_message(chat_id, "Не нашла текста для задач. Отправь текст ещё раз.")
        return

    created = []
    for ln in lines:
        ln = re.sub(r"^\s*[\-\d]+[\.\)]\s*", "", ln).strip()
        if not ln:
            continue
        task = add_task(ln)
        created.append(task)

    if len(created) == 1:
        send_message(chat_id, f"Добавила задачу #{created[0]['id']}: {created[0]['text']}")
    else:
        send_message(chat_id, f"Добавила {len(created)} задач в инбокс.")

    send_inbox(chat_id)


def handle_edit_task_text(chat_id, text, task_id):
    from bot.telegram_api import send_message

    ok, task = update_task_text(task_id, text)
    if not ok:
        send_message(chat_id, "Не нашла эту задачу.")
        return
    send_message(chat_id, "Обновила.")
    card = render_task_card(task)
    kb = task_inline_keyboard(task_id)
    send_message(chat_id, card, reply_markup=kb)


def handle_done_comment(chat_id, text, task_id):
    from storage import save_tasks, load_tasks
    from bot.telegram_api import send_message

    tasks = load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            if text.strip() != "-":
                t["done_comment"] = text.strip()
            save_tasks(tasks)
            send_message(chat_id, "Сохранила комментарий.")
            return
    send_message(chat_id, "Не нашла задачу.")


def handle_inbox_reply(chat_id, text):
    """
    Обработка ответов на сообщение с инбоксом:
    ✅ 1 2 5-7  -> отметить выполненными
    ❌ 1 3      -> удалить
    📆 2 4      -> в «Сегодня»
    ➕ новая задача -> добавить задачу(и)
    Также можно вместо номеров писать кусок текста: ✅ посуда
    """
    from bot.telegram_api import send_message

    text = (text or "").strip()
    if not text:
        send_message(chat_id, "Напиши команду и номера задач или текст.")
        return

    cmd = text[0]
    rest = text[1:].strip()

    tasks = list_active_tasks()

    # 1. пробуем вытащить номера
    ids = parse_task_ids(rest)

    # 2. если номеров нет, но есть текст — ищем по подстроке
    if not ids and rest:
        query = rest.lower()
        for t in tasks:
            if query in t["text"].lower():
                ids.add(t["id"])

    if cmd in ("➕", "+"):
        # добавление новых задач: весь rest — текст (можно с переносами строк)
        if not rest:
            send_message(chat_id, "После ➕ напиши текст задачи.")
            return
        handle_add_inbox_text(chat_id, rest)
        return

    if not ids:
        send_message(chat_id, "Не нашла задачи по этим номерам или тексту.")
        return

    if cmd in ("❌", "🗑"):
        count = 0
        for tid in ids:
            if delete_task_by_id(tid):
                count += 1
        send_message(chat_id, f"Удалено задач: {count}.")
        send_inbox(chat_id)
        return

    if cmd in ("✅", "✔"):
        count = 0
        for tid in ids:
            ok, _ = complete_task_by_id(tid)
            if ok:
                count += 1
        send_message(chat_id, f"Отметила выполненными: {count}.")
        send_inbox(chat_id)
        return

    if cmd in ("📆", "🗓"):
        count = 0
        for tid in ids:
            item = add_today_from_task(tid)
            if item:
                count += 1
        send_message(chat_id, f"Добавила в «Сегодня»: {count}.")
        return

    send_message(
        chat_id,
        "Не поняла команду.\n"
        "Примеры:\n"
        "✅ 1 2 4-5 — отметить выполненными\n"
        "❌ 3 — удалить\n"
        "📆 1 2 — добавить в «Сегодня»\n"
        "✅ посуда — найти по тексту и отметить выполненной",
    )