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
        return "Инбокс пуст.\n\nНажми «➕ Добавить», чтобы создать задачи.", tasks

    lines = ["Твой инбокс:"]
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
    # разбираем текст как список задач
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
    ok, task = update_task_text(task_id, text)
    if not ok:
        send_message(chat_id, "Не нашла эту задачу.")
        return
    send_message(chat_id, "Обновила.")
    card = render_task_card(task)
    kb = task_inline_keyboard(task_id)
    send_message(chat_id, card, reply_markup=kb)


def handle_done_comment(chat_id, text, task_id):
    from storage import save_tasks, load_tasks  # локальный импорт, чтобы не тянуть лишнее наверх

    tasks = load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            if text.strip() != "-":
                t["done_comment"] = text.strip()
            save_tasks(tasks)
            send_message(chat_id, "Сохранила комментарий.")
            return
    send_message(chat_id, "Не нашла задачу.")


# ---------- МАССОВЫЕ ОПЕРАЦИИ С ЗАДАЧАМИ ----------

def bulk_complete_tasks(chat_id, text):
    """
    Отмечает несколько задач как выполненные по номерам.
    """
    ids = parse_task_ids(text)
    if not ids:
        send_message(chat_id, "Не нашла номеров задач. Напиши, например: 1 2 5-7")
        return

    done = 0
    for tid in ids:
        ok, _ = complete_task_by_id(tid)
        if ok:
            done += 1

    if done == 0:
        send_message(chat_id, "Не удалось найти ни одной задачи по этим номерам.")
    else:
        send_message(chat_id, f"Отметила как выполненные: {done} задач(и).")


def bulk_delete_tasks(chat_id, text):
    """
    Удаляет несколько задач по номерам.
    """
    ids = parse_task_ids(text)
    if not ids:
        send_message(chat_id, "Не нашла номеров задач. Напиши, например: 3 4 10-12")
        return

    deleted = 0
    for tid in ids:
        if delete_task_by_id(tid):
            deleted += 1

    if deleted == 0:
        send_message(chat_id, "Ничего не удалила. Проверь номера задач.")
    else:
        send_message(chat_id, f"Удалено задач: {deleted}.")


def bulk_move_to_today(chat_id, text):
    """
    Переносит несколько задач в «Сегодня» по номерам.
    """
    ids = parse_task_ids(text)
    if not ids:
        send_message(chat_id, "Не нашла номеров задач. Напиши, например: 1 2 5-7")
        return

    added = 0
    for tid in ids:
        item = add_today_from_task(tid)
        if item:
            added += 1

    if added == 0:
        send_message(chat_id, "Не удалось добавить ни одной задачи в «Сегодня».")
    else:
        send_message(chat_id, f"Добавила в «Сегодня» задач: {added}.")


def bulk_prepare_routine(chat_id, text):
    """
    Первый шаг создания рутины из задач.
    Здесь только парсим номера и возвращаем набор id.
    Проверка и создание рутины делаются в main.py.
    """
    ids = parse_task_ids(text)
    if not ids:
        send_message(chat_id, "Не нашла номеров задач. Попробуй ещё раз: 1 2 5-7")
    return ids