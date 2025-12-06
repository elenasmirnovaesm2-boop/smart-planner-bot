"""
Inbox (task list) utilities.

This module encapsulates all logic related to viewing and manipulating
inbox tasks. Users interact with the inbox via text commands: adding
tasks, editing them, deleting them, moving tasks to the 'today' list and
opening a task to see more details.
"""

from __future__ import annotations

from typing import Tuple, List, Set

from storage import (
    add_task,
    list_active_tasks,
    update_task_text,
    delete_task_by_id,
    complete_task_by_id,
    add_today_from_task,
    get_task_by_id,
)
from bot.telegram_api import send_message


def parse_task_ids(text: str) -> Set[int]:
    """
    Parse a string of task identifiers into a set of integers. Supports
    whitespace-separated numbers and ranges like "1 3-5 7",
    which returns {1, 3, 4, 5, 7}. Non-numeric parts are ignored.
    """
    ids: Set[int] = set()
    for part in text.strip().split():
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            try:
                start_str, end_str = part.split("-", 1)
                start = int(start_str)
                end = int(end_str)
                if start <= end:
                    ids.update(range(start, end + 1))
            except ValueError:
                continue
        else:
            try:
                ids.add(int(part))
            except ValueError:
                continue
    return ids


def render_inbox_text() -> Tuple[str, List[dict]]:
    """
    Produce a textual representation of the current inbox tasks and return
    a tuple (text, tasks) where text is the message to send and tasks is
    the underlying list of task dicts. Completed tasks are excluded.
    """
    tasks = list_active_tasks()
    if not tasks:
        return "Твой инбокс пуст.\n\nИспользуй команду add <текст> для добавления задач.", tasks
    lines = ["Твой инбокс:"]
    for t in tasks:
        lines.append(f"{t['id']}. {t['text']}")
    return "\n".join(lines), tasks


def send_inbox(chat_id: int) -> None:
    """Send the current inbox to the specified chat."""
    text, _ = render_inbox_text()
    send_message(chat_id, text)


def render_task_card(task: dict) -> str:
    """
    Render a detailed card for a single task, including its status and
    timestamps. Suitable for the open command.
    """
    status = "Выполнена ✅" if task.get("done") else "не выполнена"
    comment = task.get("comment")
    comment_part = f"\nКомментарий: {comment}" if comment else ""
    created = task.get("created_at")
    created_part = f"\nСоздана: {created}" if created else ""
    return (
        f"Задача #{task['id']}\n"
        f"Текст: {task['text']}\n"
        f"Статус: {status}{comment_part}{created_part}"
    )


def handle_add_inbox_text(chat_id: int, text: str) -> None:
    """
    Add one or more tasks from the provided text. Multiple tasks can be
    separated by newlines. Each non-empty line becomes a separate task.
    """
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    if not lines:
        send_message(chat_id, "Не нашла текста для задач. Отправь ещё раз.")
        return
    created: List[dict] = []
    for ln in lines:
        task = add_task(ln)
        created.append(task)
    if len(created) == 1:
        send_message(chat_id, f"Добавила задачу #{created[0]['id']}: {created[0]['text']}")
    else:
        send_message(chat_id, f"Добавила {len(created)} задач в инбокс.")
    send_inbox(chat_id)


def handle_edit_task_text(chat_id: int, text: str, task_id: int) -> None:
    """
    Update the text of a task. The caller must provide the task_id separately
    from the new text.
    """
    success, updated = update_task_text(task_id, text)
    if not success or updated is None:
        send_message(chat_id, "Не нашла эту задачу.")
        return
    send_message(chat_id, f"Обновила задачу #{task_id}.")
    send_message(chat_id, render_task_card(updated))


def handle_delete_tasks(chat_id: int, id_text: str) -> None:
    """
    Delete one or more tasks based on a string of IDs. Supports ranges.
    Sends a summary message and then refreshes the inbox.
    """
    ids = parse_task_ids(id_text)
    if not ids:
        send_message(chat_id, "Не поняла номера задач. Пример: del 1 3 5-7")
        return
    deleted = 0
    for tid in ids:
        if delete_task_by_id(tid):
            deleted += 1
    send_message(chat_id, f"Удалено задач: {deleted}.")
    send_inbox(chat_id)


def handle_move_task(chat_id: int, task_id: int) -> None:
    """
    Move a task into the today list. The task remains in the inbox but
    is also copied into today's list via add_today_from_task.
    """
    item = add_today_from_task(task_id)
    if item:
        send_message(chat_id, f"Перенесла задачу #{task_id} в список 'Сегодня'.")
    else:
        send_message(chat_id, "Не нашла задачу для переноса.")


def handle_open_task(chat_id: int, task_id: int) -> None:
    """Send a detailed card for the specified task."""
    task = get_task_by_id(task_id)
    if task:
        send_message(chat_id, render_task_card(task))
    else:
        send_message(chat_id, "Не нашла задачу.")