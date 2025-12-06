"""
Entry point for the Smart Planner bot.

This module defines a Flask application that serves as the webhook
endpoint for a Telegram bot. Incoming updates are parsed and routed to
appropriate handlers for commands, inbox operations, and entity listings.

The bot relies on modules in the `bot` package as well as the `storage`
module to provide persistence. To run this bot locally, you must set the
`TELEGRAM_BOT_TOKEN` environment variable and expose the Flask
application via a public URL (e.g. using ngrok) so Telegram can deliver
webhook updates. Refer to Telegram's Bot API documentation for details
on configuring webhooks.
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
    # CRUD functions for routines
    add_routine,
    update_routine,
    delete_routine,
    get_routine_by_id,
    # CRUD functions for templates
    add_template,
    update_template,
    delete_template,
    get_template_by_id,
    # CRUD functions for projects
    add_project,
    update_project,
    delete_project,
    get_project_by_id,
    # CRUD functions for habits
    add_habit,
    update_habit,
    delete_habit,
    get_habit_by_id,
    # CRUD functions for SOS
    add_sos,
    update_sos,
    delete_sos,
    get_sos_by_id,
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
    """Return a textual representation of the 'today' list."""
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
    Send one or more entity cards to the user. Each entity is rendered
    via the provided ``renderer`` function. If the list is empty,
    inform the user that the corresponding list is empty.
    """
    if not entities:
        send_message(chat_id, "Пока ничего нет в этом разделе.")
        return
    for ent in entities:
        send_message(chat_id, renderer(ent))


def handle_text_message(message: Dict[str, Any]) -> None:
    """
    Primary dispatcher for incoming text messages. This function parses
    user commands and routes them to the appropriate inbox or listing
    handlers. If no known command is found, the text is treated as
    one or more tasks to add to the inbox.
    """
    chat_id = message["chat"]["id"]
    text = (message.get("text") or "").strip()
    if not text:
        return

    # Стандартные команды: старт, меню и справка.
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
            "Главное меню.\n\nНажми «ℹ️ Команды» чтобы посмотреть список текстовых команд.",
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
            "Команды для рутин: radd <название>|<шаг1;шаг2;...>, redit <ID> <название>|<шаг1;...>, "
            "rdel <ID>, ropen <ID>\n"
            "Команды для шаблонов: tadd <название>|<блок1;блок2;...>, tedit <ID> <название>|<блоки>, "
            "tdel <ID>, topen <ID>\n"
            "Команды для проектов: padd <название>|<шаг1;шаг2;...>, pedit <ID> <название>|<шаги>, "
            "pdel <ID>, popen <ID>\n"
            "Команды для привычек: hadd <название>|<график>, hedit <ID> <название>|<график>, hdel <ID>, hopen <ID>\n"
            "Команды для SOS: sadd <название>|<шаг1;шаг2;...>, sedit <ID> <название>|<шаги>, "
            "sdel <ID>, sopen <ID>\n"
            "\n"
            "Примеры: 'radd Утренняя рутина|проснуться;завтрак' или 'tedit 2 Новый день|работа;отдых'",
        )
        return

    # Переходы между разделами по кнопкам/командам.
    if text in ("/inbox", "📝 Инбокс"):
        send_inbox(chat_id)
        return
    if text in ("/today", "📅 Сегодня"):
        send_message(chat_id, render_today_list())
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

    # Команды для задач (инбокса).
    lower = text.lower()
    if lower.startswith("add ") or lower == "add":
        handle_add_inbox_text(chat_id, text[3:].strip())
        return
    if lower.startswith("edit "):
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            send_message(chat_id, "Формат: edit <ID> <новый текст>")
            return
        try:
            tid = int(parts[1])
        except ValueError:
            send_message(chat_id, "Не поняла номер задачи в команде edit.")
            return
        handle_edit_task_text(chat_id, parts[2].strip(), tid)
        return
    if lower.startswith("del "):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Формат: del <ID или диапазон>")
            return
        handle_delete_tasks(chat_id, parts[1])
        return
    if lower.startswith("mv "):
        parts = text.split()
        if len(parts) != 3 or parts[2].lower() != "today":
            send_message(chat_id, "Формат: mv <ID> today")
            return
        try:
            tid = int(parts[1])
        except ValueError:
            send_message(chat_id, "Не поняла номер задачи в команде mv.")
            return
        handle_move_task(chat_id, tid)
        return
    if lower.startswith("open "):
        parts = text.split()
        if len(parts) != 2:
            send_message(chat_id, "Формат: open <ID>")
            return
        try:
            tid = int(parts[1])
        except ValueError:
            send_message(chat_id, "Не поняла номер задачи в команде open.")
            return
        handle_open_task(chat_id, tid)
        return

    # === Команды для рутин ===
    if lower.startswith("radd"):
        rest = text[4:].strip()
        if not rest:
            send_message(chat_id, "Формат: radd <название>|<шаг1;шаг2;...>")
            return
        if "|" in rest:
            name_part, steps_str = rest.split("|", 1)
            name = name_part.strip()
            steps = [s.strip() for s in steps_str.split(";") if s.strip()]
        else:
            name = rest
            steps = []
        routine = add_routine(name, steps)
        send_message(chat_id, f"Добавила рутину #{routine['id']}: {routine['name']}")
        return
    if lower.startswith("redit "):
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            send_message(chat_id, "Формат: redit <ID> <название>|<шаги>")
            return
        try:
            rid = int(parts[1])
        except ValueError:
            send_message(chat_id, "Не поняла номер рутины.")
            return
        rest = parts[2]
        if "|" in rest:
            name_part, steps_str = rest.split("|", 1)
            name = name_part.strip()
            steps = [s.strip() for s in steps_str.split(";") if s.strip()]
        else:
            name = rest.strip()
            steps = []
        ok, updated = update_routine(rid, name, steps)
        if not ok:
            send_message(chat_id, "Не нашла такую рутину.")
            return
        send_message(chat_id, f"Обновила рутину #{rid}.")
        send_message(chat_id, render_routine_card(updated))
        return
    if lower.startswith("rdel "):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Формат: rdel <ID>")
            return
        try:
            rid = int(parts[1])
        except ValueError:
            send_message(chat_id, "Не поняла номер рутины.")
            return
        if delete_routine(rid):
            send_message(chat_id, f"Удалена рутина #{rid}.")
        else:
            send_message(chat_id, "Не нашла такую рутину.")
        return
    if lower.startswith("ropen "):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Формат: ropen <ID>")
            return
        try:
            rid = int(parts[1])
        except ValueError:
            send_message(chat_id, "Не поняла номер рутины.")
            return
        routine = get_routine_by_id(rid)
        if routine:
            send_message(chat_id, render_routine_card(routine))
        else:
            send_message(chat_id, "Не нашла такую рутину.")
        return

    # === Команды для шаблонов ===
    if lower.startswith("tadd"):
        rest = text[4:].strip()
        if not rest:
            send_message(chat_id, "Формат: tadd <название>|<блок1;блок2;...>")
            return
        if "|" in rest:
            name_part, blocks_str = rest.split("|", 1)
            name = name_part.strip()
            blocks = [b.strip() for b in blocks_str.split(";") if b.strip()]
        else:
            name = rest
            blocks = []
        tpl = add_template(name, blocks)
        send_message(chat_id, f"Добавила шаблон #{tpl['id']}: {tpl['name']}")
        return
    if lower.startswith("tedit "):
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            send_message(chat_id, "Формат: tedit <ID> <название>|<блоки>")
            return
        try:
            tid = int(parts[1])
        except ValueError:
            send_message(chat_id, "Не поняла номер шаблона.")
            return
        rest = parts[2]
        if "|" in rest:
            name_part, blocks_str = rest.split("|", 1)
            name = name_part.strip()
            blocks = [b.strip() for b in blocks_str.split(";") if b.strip()]
        else:
            name = rest.strip()
            blocks = []
        ok, updated = update_template(tid, name, blocks)
        if not ok:
            send_message(chat_id, "Не нашла такой шаблон.")
            return
        send_message(chat_id, f"Обновила шаблон #{tid}.")
        send_message(chat_id, render_template_card(updated))
        return
    if lower.startswith("tdel "):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Формат: tdel <ID>")
            return
        try:
            tid = int(parts[1])
        except ValueError:
            send_message(chat_id, "Не поняла номер шаблона.")
            return
        if delete_template(tid):
            send_message(chat_id, f"Удалён шаблон #{tid}.")
        else:
            send_message(chat_id, "Не нашла такой шаблон.")
        return
    if lower.startswith("topen "):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Формат: topen <ID>")
            return
        try:
            tid = int(parts[1])
        except ValueError:
            send_message(chat_id, "Не поняла номер шаблона.")
            return
        tpl = get_template_by_id(tid)
        if tpl:
            send_message(chat_id, render_template_card(tpl))
        else:
            send_message(chat_id, "Не нашла такой шаблон.")
        return

    # === Команды для проектов ===
    if lower.startswith("padd"):
        rest = text[4:].strip()
        if not rest:
            send_message(chat_id, "Формат: padd <название>|<шаг1;шаг2;...>")
            return
        if "|" in rest:
            name_part, steps_str = rest.split("|", 1)
            name = name_part.strip()
            steps = [s.strip() for s in steps_str.split(";") if s.strip()]
        else:
            name = rest
            steps = []
        proj = add_project(name, steps)
        send_message(chat_id, f"Добавила проект #{proj['id']}: {proj['name']}")
        return
    if lower.startswith("pedit "):
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            send_message(chat_id, "Формат: pedit <ID> <название>|<шаги>")
            return
        try:
            pid = int(parts[1])
        except ValueError:
            send_message(chat_id, "Не поняла номер проекта.")
            return
        rest = parts[2]
        if "|" in rest:
            name_part, steps_str = rest.split("|", 1)
            name = name_part.strip()
            steps = [s.strip() for s in steps_str.split(";") if s.strip()]
        else:
            name = rest.strip()
            steps = []
        ok, updated = update_project(pid, name, steps)
        if not ok:
            send_message(chat_id, "Не нашла такой проект.")
            return
        send_message(chat_id, f"Обновила проект #{pid}.")
        send_message(chat_id, render_project_card(updated))
        return
    if lower.startswith("pdel "):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Формат: pdel <ID>")
            return
        try:
            pid = int(parts[1])
        except ValueError:
            send_message(chat_id, "Не поняла номер проекта.")
            return
        if delete_project(pid):
            send_message(chat_id, f"Удалён проект #{pid}.")
        else:
            send_message(chat_id, "Не нашла такой проект.")
        return
    if lower.startswith("popen "):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Формат: popen <ID>")
            return
        try:
            pid = int(parts[1])
        except ValueError:
            send_message(chat_id, "Не поняла номер проекта.")
            return
        proj = get_project_by_id(pid)
        if proj:
            send_message(chat_id, render_project_card(proj))
        else:
            send_message(chat_id, "Не нашла такой проект.")
        return

    # === Команды для привычек ===
    if lower.startswith("hadd"):
        rest = text[4:].strip()
        if not rest:
            send_message(chat_id, "Формат: hadd <название>|<график>")
            return
        if "|" in rest:
            name_part, sched = rest.split("|", 1)
            name = name_part.strip()
            schedule = sched.strip()
        else:
            name = rest
            schedule = ""
        habit = add_habit(name, schedule)
        send_message(chat_id, f"Добавила привычку #{habit['id']}: {habit['name']}")
        return
    if lower.startswith("hedit "):
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            send_message(chat_id, "Формат: hedit <ID> <название>|<график>")
            return
        try:
            hid = int(parts[1])
        except ValueError:
            send_message(chat_id, "Не поняла номер привычки.")
            return
        rest = parts[2]
        if "|" in rest:
            name_part, sched = rest.split("|", 1)
            name = name_part.strip()
            schedule = sched.strip()
        else:
            name = rest.strip()
            schedule = ""
        ok, updated = update_habit(hid, name, schedule)
        if not ok:
            send_message(chat_id, "Не нашла такую привычку.")
            return
        send_message(chat_id, f"Обновила привычку #{hid}.")
        send_message(chat_id, render_habit_card(updated))
        return
    if lower.startswith("hdel "):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Формат: hdel <ID>")
            return
        try:
            hid = int(parts[1])
        except ValueError:
            send_message(chat_id, "Не поняла номер привычки.")
            return
        if delete_habit(hid):
            send_message(chat_id, f"Удалена привычка #{hid}.")
        else:
            send_message(chat_id, "Не нашла такую привычку.")
        return
    if lower.startswith("hopen "):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Формат: hopen <ID>")
            return
        try:
            hid = int(parts[1])
        except ValueError:
            send_message(chat_id, "Не поняла номер привычки.")
            return
        habit = get_habit_by_id(hid)
        if habit:
            send_message(chat_id, render_habit_card(habit))
        else:
            send_message(chat_id, "Не нашла такую привычку.")
        return

    # === Команды для SOS ===
    if lower.startswith("sadd"):
        rest = text[4:].strip()
        if not rest:
            send_message(chat_id, "Формат: sadd <название>|<шаг1;шаг2;...>")
            return
        if "|" in rest:
            name_part, steps_str = rest.split("|", 1)
            name = name_part.strip()
            steps = [s.strip() for s in steps_str.split(";") if s.strip()]
        else:
            name = rest
            steps = []
        sos = add_sos(name, steps)
        send_message(chat_id, f"Добавила SOS #{sos['id']}: {sos['name']}")
        return
    if lower.startswith("sedit "):
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            send_message(chat_id, "Формат: sedit <ID> <название>|<шаги>")
            return
        try:
            sid = int(parts[1])
        except ValueError:
            send_message(chat_id, "Не поняла номер SOS.")
            return
        rest = parts[2]
        if "|" in rest:
            name_part, steps_str = rest.split("|", 1)
            name = name_part.strip()
            steps = [s.strip() for s in steps_str.split(";") if s.strip()]
        else:
            name = rest.strip()
            steps = []
        ok, updated = update_sos(sid, name, steps)
        if not ok:
            send_message(chat_id, "Не нашла такой SOS.")
            return
        send_message(chat_id, f"Обновила SOS #{sid}.")
        send_message(chat_id, render_sos_card(updated))
        return
    if lower.startswith("sdel "):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Формат: sdel <ID>")
            return
        try:
            sid = int(parts[1])
        except ValueError:
            send_message(chat_id, "Не поняла номер SOS.")
            return
        if delete_sos(sid):
            send_message(chat_id, f"Удалён SOS #{sid}.")
        else:
            send_message(chat_id, "Не нашла такой SOS.")
        return
    if lower.startswith("sopen "):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Формат: sopen <ID>")
            return
        try:
            sid = int(parts[1])
        except ValueError:
            send_message(chat_id, "Не поняла номер SOS.")
            return
        sos_item = get_sos_by_id(sid)
        if sos_item:
            send_message(chat_id, render_sos_card(sos_item))
        else:
            send_message(chat_id, "Не нашла такой SOS.")
        return

    # Если команда не распознана, пытаемся добавить текст как задачу.
    handle_add_inbox_text(chat_id, text)


@app.route("/webhook", methods=["POST"])
def webhook() -> str:
    """Receive updates from Telegram and dispatch them."""
    data = request.get_json(force=True, silent=True)
    if not data:
        return ""
    if "message" in data and isinstance(data["message"], dict):
        handle_text_message(data["message"])
    return ""


@app.route("/health", methods=["GET"])
def health() -> str:
    """Simple health endpoint for uptime checks."""
    return "ok"


if __name__ == "__main__":
    # Bind to PORT if defined; default to 5000.
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)