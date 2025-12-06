"""
Entry point for the Smart Planner bot.

Это полноценное Flask‑приложение для Telegram‑бота. Файл
включает обработку вебхука, маршруты для проверки состояния,
отображение списков задач и остальных сущностей, обработку
текстовых команд для инбокса и других разделов. Вызываемые функции
хранятся в модулях bot/* и storage.py.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

from flask import Flask, request

from bot.telegram_api import send_message
from bot.keyboards import main_keyboard
from bot.inbox import (
    send_inbox,
    handle_add_inbox_text,
    handle_edit_task_text,
    handle_delete_tasks,
    handle_move_task,
    handle_open_task,
)
from storage import (
    list_today,
    list_routines,
    list_templates,
    list_projects,
    list_sos,
    list_habits,
)
from bot.entities import (
    render_routine_card,
    render_template_card,
    render_project_card,
    render_sos_card,
    render_habit_card,
)

app = Flask(__name__)


def render_today_list() -> str:
    """Сформировать текстовую строку для списка «Сегодня»."""
    items = list_today()
    if not items:
        return "Сегодня пока пусто. Переноси задачи из инбокса командой mv <id> today."
    lines: List[str] = ["Твой список 'Сегодня':"]
    for item in items:
        tid = item.get("task_id")
        text = item.get("text", "")
        lines.append(f"{item['id']}. {text} (id задачи {tid})")
    return "\n".join(lines)


def handle_list_entities(chat_id: int, entities: List[Dict[str, Any]], renderer) -> None:
    """
    Отправить одну или несколько карточек сущностей пользователю. Каждая
    сущность отображается через функцию ``renderer``. Если список пуст,
    выводится сообщение о пустоте раздела.
    """
    if not entities:
        send_message(chat_id, "Пока ничего нет в этом разделе.")
        return
    for ent in entities:
        text = renderer(ent)
        send_message(chat_id, text)


def handle_text_message(message: Dict[str, Any]) -> None:
    """
    Главный обработчик входящих текстовых сообщений. Команды распознаются
    по ключевым словам и перенаправляются на соответствующие функции. Всё
    остальное воспринимается как текст новых задач для инбокса.
    """
    chat_id = message["chat"]["id"]
    text = (message.get("text") or "").strip()
    if not text:
        return

    # Команды для старта, меню и списка доступных команд.
    if text == "/start":
        send_message(
            chat_id,
            "Привет! Это твой планировщик.\n"
            "Используй кнопки ниже для работы с инбоксом, сегодня, рутинами и другими разделами.",
            reply_markup=main_keyboard(),
        )
        return
    if text in ("/menu", "🔆 Меню"):
        send_message(
            chat_id,
            "Главное меню.\n\nНажми «ℹ️ Команды», чтобы посмотреть список текстовых команд.",
            reply_markup=main_keyboard(),
        )
        return
    if text in ("/commands", "ℹ️ Команды"):
        send_message(
            chat_id,
            "Список команд:\n"
            "• add <текст> — добавить задачу в инбокс. Несколько задач можно разделять переводом строки.\n"
            "• edit <ID> <новый текст> — изменить текст задачи.\n"
            "• del <ID или диапазон> — удалить одну или несколько задач (пример: del 1 3-5).\n"
            "• mv <ID> today — перенести задачу в список «Сегодня».\n"
            "• open <ID> — открыть подробный вид задачи.\n"
            "\n"
            "Примеры: 'add Купить продукты' или 'del 1 3-5'",
        )
        return

    # Переходы между разделами.
    if text in ("/inbox", "📝 Инбокс"):
        send_inbox(chat_id)
        return
    if text in ("/today", "📅 Сегодня"):
        today_text = render_today_list()
        send_message(chat_id, today_text)
        return
    if text in ("/routines", "📋 Рутины"):
        handle_list_entities(chat_id, list_routines(), render_routine_card)
        return
    if text in ("/templates", "📅 Шаблоны"):
        handle_list_entities(chat_id, list_templates(), render_template_card)
        return
    if text in ("/projects", "📦 Проекты"):
        handle_list_entities(chat_id, list_projects(), render_project_card)
        return
    if text in ("/sos", "🆘 SOS"):
        handle_list_entities(chat_id, list_sos(), render_sos_card)
        return
    if text in ("/habits", "🔥 Привычки"):
        handle_list_entities(chat_id, list_habits(), render_habit_card)
        return

    # Обработка команд для задач. Команды чувствительны к порядку и
    # должны находиться в начале сообщения.
    lower_text = text.lower()
    if lower_text.startswith("add ") or lower_text == "add":
        # Всё после 'add' считается текстом новой задачи (поддерживаются многострочные задачи).
        to_add = text[3:].strip()
        handle_add_inbox_text(chat_id, to_add)
        return
    if lower_text.startswith("edit "):
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            send_message(chat_id, "Формат: edit <ID> <новый текст>")
            return
        try:
            task_id = int(parts[1])
        except ValueError:
            send_message(chat_id, "Не поняла номер задачи в команде edit.")
            return
        new_text = parts[2].strip()
        handle_edit_task_text(chat_id, new_text, task_id)
        return
    if lower_text.startswith("del "):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Формат: del <ID или диапазон>")
            return
        ids_part = parts[1]
        handle_delete_tasks(chat_id, ids_part)
        return
    if lower_text.startswith("mv "):
        parts = text.split()
        # Ожидаем 'mv <id> today'
        if len(parts) != 3 or parts[2].lower() != "today":
            send_message(chat_id, "Формат: mv <ID> today")
            return
        try:
            task_id = int(parts[1])
        except ValueError:
            send_message(chat_id, "Не поняла номер задачи в команде mv.")
            return
        handle_move_task(chat_id, task_id)
        return
    if lower_text.startswith("open "):
        parts = text.split()
        if len(parts) != 2:
            send_message(chat_id, "Формат: open <ID>")
            return
        try:
            task_id = int(parts[1])
        except ValueError:
            send_message(chat_id, "Не поняла номер задачи в команде open.")
            return
        handle_open_task(chat_id, task_id)
        return

    # Любой другой текст рассматриваем как задачи для добавления в инбокс.
    handle_add_inbox_text(chat_id, text)


@app.route("/webhook", methods=["POST"])
def webhook() -> str:
    """
    HTTP‑маршрут для получения обновлений от Telegram. Передаёт
    сообщения в обработчик.
    """
    data = request.get_json(force=True, silent=True)  # type: ignore[assignment]
    if not data:
        return ""
    if "message" in data and isinstance(data["message"], dict):
        handle_text_message(data["message"])
    return ""


@app.route("/health", methods=["GET"])
def health() -> str:
    """Простой эндпойнт для проверки доступности приложения."""
    return "ok"


if __name__ == "__main__":
    # Определяем порт через переменную окружения PORT, либо берём 5000.
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)