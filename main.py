import os
import re
import requests
import datetime
from flask import Flask, request

from storage import (
    add_task,
    list_active_tasks,
    complete_task_by_id,
    delete_task_by_id,
    update_task_text,
    add_today_from_task,
    add_tomorrow_from_task,
    list_today,
    list_tomorrow,
    set_pending_action,
    get_pending_action,
    get_task_by_id,
    list_routines,
    list_templates,
    list_habits,
    list_projects,
    list_sos,
    add_project,
    add_project_step,
)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Не задан TELEGRAM_BOT_TOKEN")

API_URL = f"https://api.telegram.org/bot{TOKEN}/"

app = Flask(__name__)


# ---------- ВСПОМОГАТЕЛЬНОЕ ----------

def tg_request(method: str, payload: dict):
    try:
        r = requests.post(API_URL + method, json=payload, timeout=5)
        return r.json()
    except Exception as e:
        print("Telegram API error:", e)
        return None


def send_message(chat_id, text, reply_markup=None, parse_mode=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    if parse_mode:
        payload["parse_mode"] = parse_mode
    tg_request("sendMessage", payload)


def edit_message(chat_id, message_id, text, reply_markup=None, parse_mode=None):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    if parse_mode:
        payload["parse_mode"] = parse_mode
    tg_request("editMessageText", payload)


def answer_callback_query(callback_query_id, text=None, show_alert=False):
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    if show_alert:
        payload["show_alert"] = True
    tg_request("answerCallbackQuery", payload)


# ---------- УТИЛИТЫ ФОРМАТИРОВАНИЯ ----------

def format_datetime_short(value: str | None) -> str:
    if not value:
        return "—"
    try:
        dt = datetime.datetime.fromisoformat(value)
        return dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return value


def format_importance(value: str | None) -> str:
    if not value:
        return "не классифицировано"
    v = value.lower()
    mapping = {
        "срочно и важно": "🔴 Срочно и важно",
        "срочно, но не важно": "🟠 Срочно, но не важно",
        "не срочно, но важно": "🔵 Не срочно, но важно",
        "не срочно и не важно": "🟡 Не срочно и не важно",
    }
    return mapping.get(v, value)


# ---------- КЛАВИАТУРЫ ----------

def main_keyboard():
    return {
        "keyboard": [
            [{"text": "📥 Инбокс"}, {"text": "📅 Сегодня"}],
            [{"text": "📆 Завтра"}, {"text": "🔁 Рутины"}],
            [{"text": "📑 Шаблоны дня"}, {"text": "📂 Проекты"}],
            [{"text": "🌱 Привычки"}, {"text": "🚨 SOS чеклисты"}],
            [{"text": "⚙️ Меню"}],
        ],
        "resize_keyboard": True,
    }


def inbox_inline_keyboard(tasks):
    # Только общие кнопки — без отдельных кнопок для каждой задачи
    return {
        "inline_keyboard": [
            [
                {"text": "➕ Добавить", "callback_data": "inbox_add"},
                {"text": "🔄 Обновить", "callback_data": "inbox_refresh"},
            ]
        ]
    }


def task_inline_keyboard(task_id):
    # Карточка задачи с Today / Tomorrow / дедлайном / приоритетом / перемещением
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Готово", "callback_data": f"task_done:{task_id}"},
                {"text": "✏️ Редактировать", "callback_data": f"task_edit:{task_id}"},
            ],
            [
                {"text": "➡️ В Сегодня", "callback_data": f"task_today:{task_id}"},
                {"text": "➡️ На завтра", "callback_data": f"task_tomorrow:{task_id}"},
            ],
            [
                {"text": "⏳ Дедлайн", "callback_data": f"task_deadline:{task_id}"},
                {"text": "⚡ Приоритет", "callback_data": f"task_priority:{task_id}"},
            ],
            [
                {"text": "📂 Переместить", "callback_data": f"task_move:{task_id}"},
                {"text": "🗑 Удалить", "callback_data": f"task_delete:{task_id}"},
            ],
        ]
    }


# ---------- ЛОГИКА: ИНБОКС ----------

def render_inbox_text():
    tasks = list_active_tasks()
    if not tasks:
        return (
            "📥 Инбокс пуст.\n\n"
            "Напиши задачу одним сообщением или отправь список (каждая строка — отдельная задача).",
            tasks,
        )

    lines = ["📥 Твой инбокс", ""]
    for t in tasks:
        mark = "☐" if not t.get("done") else "✅"
        lines.append(f"{t['id']}. {mark} {t['text']}")
    lines.append("")
    lines.append(
        "Выбери задачу: просто напиши её номер (например: 3)\n"
        "Несколько задач: 1 3 5 today / 2,4 done / 1-3 delete (диапазон 1-3 тоже работает)."
    )
    return "\n".join(lines), tasks


def send_inbox(chat_id):
    text, tasks = render_inbox_text()
    kb = inbox_inline_keyboard(tasks)
    send_message(chat_id, text, reply_markup=kb)


def render_task_card(task):
    status = "выполнена ✅" if task.get("done") else