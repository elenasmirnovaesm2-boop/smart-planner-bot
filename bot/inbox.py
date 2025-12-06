"""
Updated inbox handling to remove inline keyboards from task lists and cards.
"""

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


def parse_task_ids(text: str) -> set[int]:
    """Existing parser omitted for brevity"""
    return set()


def render_inbox_text() -> tuple[str, list]:
    """Existing rendering omitted for brevity"""
    return "", []


def send_inbox(chat_id: int):
    """
    Send the current inbox list to the user. This version no longer includes
    an inline keyboard; instead, the user should use text commands (add, edit,
    del, mv, open) to manage items.
    """
    text, tasks = render_inbox_text()
    # Do not include inline keyboard; send plain text only.
    send_message(chat_id, text)


def render_task_card(task: dict) -> str:
    """Render a single task card as plain text."""
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


def handle_add_inbox_text(chat_id: int, text: str):
    """Existing add handler omitted for brevity"""
    send_inbox(chat_id)


def handle_edit_task_text(chat_id: int, text: str, task_id: int):
    """
    Update a task's text. Sends back the updated card without an inline keyboard.
    """
    ok, task = update_task_text(task_id, text)
    if not ok:
        send_message(chat_id, "Не нашла эту задачу.")
        return
    send_message(chat_id, "Обновила.")
    card = render_task_card(task)
    # Do not include inline keyboard.
    send_message(chat_id, card)


def handle_done_comment(chat_id: int, text: str, task_id: int):
    """Existing done-comment handler omitted for brevity"""
    pass