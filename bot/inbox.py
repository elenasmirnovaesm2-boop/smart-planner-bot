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


def handle_merge_command(chat_id, raw_text: str):
    """
    merge 1 2 5-7
    → создаёт новую задачу-блок с подзадачами (+ ...)
    → исходные задачи помечает выполненными (они пропадают из инбокса)
    """
    from bot.telegram_api import send_message  # локальный импорт, чтобы не ловить циклы

    # убираем слово 'merge'
    args = raw_text[len("merge"):].strip()
    if not args:
        send_message(chat_id, "После merge укажи номера задач, например: merge 1 2 5-7")
        return

    ids = parse_task_ids(args)
    if not ids:
        send_message(chat_id, "Не поняла номера задач. Пример: merge 1 2 5-7")
        return

    tasks = list_active_tasks()
    selected = [t for t in tasks if t["id"] in ids]

    if not selected:
        send_message(chat_id, "Не нашла эти задачи в инбоксе.")
        return

    # формируем текст блока: каждая подзадача с префиксом "+ "
    merged_lines = [f"+ {t['text']}" for t in selected]
    merged_text = "\n".join(merged_lines)

    new_task = add_task(merged_text)

    # исходные задачи помечаем выполненными, чтобы не засоряли инбокс
    for t in selected:
        complete_task_by_id(t["id"])

    sel_ids_str = ", ".join(str(t["id"]) for t in selected)
    send_message(
        chat_id,
        f"Создала блок-задачу #{new_task['id']} из задач: {sel_ids_str}",
    )
    send_inbox(chat_id)