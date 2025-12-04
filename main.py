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

def format_datetime_short(value):
    if not value:
        return "—"
    try:
        dt = datetime.datetime.fromisoformat(value)
        return dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return value


def format_importance(value):
    if not value:
        return "не классифицировано"
    v = str(value).lower()
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
    return {
        "inline_keyboard": [
            [
                {"text": "➕ Добавить", "callback_data": "inbox_add"},
                {"text": "🔄 Обновить", "callback_data": "inbox_refresh"},
            ]
        ]
    }


def task_inline_keyboard(task_id):
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
        "Несколько задач: 1 3 5 today / 2,4 done / 1-3 delete."
    )
    return "\n".join(lines), tasks


def send_inbox(chat_id):
    text, tasks = render_inbox_text()
    kb = inbox_inline_keyboard(tasks)
    send_message(chat_id, text, reply_markup=kb)


def render_task_card(task):
    status = "выполнена ✅" if task.get("done") else "не выполнена"
    comment = task.get("done_comment")
    comment_part = f"\nКомментарий: {comment}" if comment else ""
    created_at = format_datetime_short(task.get("created_at"))
    deadline = task.get("deadline", "не установлен")
    importance = format_importance(task.get("importance"))

    return (
        f"📝 Задача #{task['id']}\n\n"
        f"Текст: {task['text']}\n"
        f"Создано: {created_at}\n"
        f"Статус: {status}\n\n"
        f"Приоритет: {importance}\n"
        f"Дедлайн: {deadline}"
        f"{comment_part}"
    )


def handle_add_inbox_text(chat_id, text):
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

    if not created:
        send_message(chat_id, "Ничего не добавила. Попробуй ещё раз.")
        return

    if len(created) == 1:
        send_message(chat_id, f"Добавила задачу #{created[0]['id']}: {created[0]['text']}")
    else:
        send_message(chat_id, f"Добавила {len(created)} задач в инбокс.")

    send_inbox(chat_id)


def handle_edit_task_text(chat_id, text, task_id):
    ok, task = update_task_text(task_id, text)
    if not ok:
        send_message(chat_id, "Не нашла эту задачу. Возможно, она уже удалена.")
        return
    send_message(chat_id, f"Обновила задачу #{task_id}.")
    card = render_task_card(task)
    kb = task_inline_keyboard(task_id)
    send_message(chat_id, card, reply_markup=kb)


def handle_done_comment(chat_id, text, task_id):
    from storage import save_tasks, load_tasks

    tasks = load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            if text.strip() != "-":
                t["done_comment"] = text.strip()
            save_tasks(tasks)
            send_message(chat_id, f"Записала комментарий к задаче #{task_id}.")
            return
    send_message(chat_id, "Не нашла задачу для комментария.")


def handle_set_deadline(chat_id, text, task_id):
    from storage import save_tasks, load_tasks

    raw = text.strip()
    if not raw:
        send_message(chat_id, "Пустой дедлайн, ничего не изменила.")
        return

    now = datetime.datetime.now()
    lower = raw.lower()

    if lower in ("сегодня", "today"):
        value = now.date().isoformat()
    elif lower in ("завтра", "tomorrow"):
        value = (now.date() + datetime.timedelta(days=1)).isoformat()
    else:
        value = raw

    tasks = load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            t["deadline"] = value
            save_tasks(tasks)
            send_message(chat_id, f"Установила дедлайн для задачи #{task_id}: {value}")
            return
    send_message(chat_id, "Не нашла задачу для установки дедлайна.")


def handle_set_priority(chat_id, text, task_id):
    from storage import save_tasks, load_tasks

    raw = text.strip().lower()
    if not raw:
        send_message(chat_id, "Пустой приоритет, ничего не изменила.")
        return

    mapping = {
        "1": "Срочно и важно",
        "2": "Срочно, но не важно",
        "3": "Не срочно, но важно",
        "4": "Не срочно и не важно",
    }
    for key, label in list(mapping.items()):
        mapping[label.lower()] = label

    value = mapping.get(raw)
    if not value:
        send_message(
            chat_id,
            "Не поняла приоритет.\n"
            "Напиши число 1–4:\n"
            "1 — Срочно и важно\n"
            "2 — Срочно, но не важно\n"
            "3 — Не срочно, но важно\n"
            "4 — Не срочно и не важно",
        )
        return

    tasks = load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            t["importance"] = value
            save_tasks(tasks)
            send_message(chat_id, f"Установила приоритет для задачи #{task_id}: {format_importance(value)}")
            return
    send_message(chat_id, "Не нашла задачу для приоритета.")


# ---------- TODAY / TOMORROW ----------

def render_scheduled_list(title, items):
    if not items:
        return f"{title}\n\nСписок пуст. Добавь задачи из инбокса (например: 3 today)."

    lines = [title, ""]
    any_task = False
    for item in items:
        task = get_task_by_id(item.get("task_id"))
        if not task:
            continue
        any_task = True
        mark = "☐" if not task.get("done") else "✅"
        lines.append(f"{task['id']}. {mark} {task['text']}")
    if not any_task:
        return f"{title}\n\nСписок пуст (задачи могли быть удалены)."

    lines.append("")
    lines.append("Выбери задачу: просто напиши её номер, как в инбоксе.")
    return "\n".join(lines)


def send_today_screen(chat_id):
    items = list_today()
    text = render_scheduled_list("📅 Сегодня", items)
    send_message(chat_id, text, reply_markup=main_keyboard())


def send_tomorrow_screen(chat_id):
    items = list_tomorrow()
    text = render_scheduled_list("📆 Завтра", items)
    send_message(chat_id, text, reply_markup=main_keyboard())


# ---------- РУТИНЫ / ШАБЛОНЫ / ПРИВЫЧКИ / ПРОЕКТЫ / SOS ----------

def render_routines_text():
    routines = list_routines()
    if not routines:
        return "Рутин пока нет."
    lines = ["🔁 Рутины:\n"]
    for r in routines:
        lines.append(f"{r['id']}. {r['name']}")
        steps = r.get("steps") or []
        for i, s in enumerate(steps, start=1):
            lines.append(f"   {i}) {s}")
        lines.append("")
    return "\n".join(lines)


def render_templates_text():
    templates = list_templates()
    if not templates:
        return "Шаблонов дня пока нет."
    lines = ["📑 Шаблоны дня:\n"]
    for t in templates:
        lines.append(f"{t['id']}. {t['name']}")
        blocks = t.get("blocks") or []
        for i, b in enumerate(blocks, start=1):
            lines.append(f"   {i}) {b}")
        lines.append("")
    return "\n".join(lines)


def render_habits_text():
    habits = list_habits()
    if not habits:
        return "Привычек пока нет."
    lines = ["🌱 Привычки:\n"]
    for h in habits:
        lines.append(f"{h['id']}. {h['name']}")
        sched = h.get("schedule")
        if sched:
            lines.append(f"   ⏱ {sched}")
        lines.append("")
    return "\n".join(lines)


def render_projects_text():
    projects = list_projects()
    if not projects:
        return "Проектов пока нет."
    lines = ["📂 Проекты:\n"]
    for p in projects:
        lines.append(f"{p['id']}. {p['name']}")
        steps = p.get("steps") or []
        for s in steps:
            mark = "☐" if not s.get("done") else "✅"
            lines.append(f"   - {mark} {s['text']}")
        lines.append("")
    return "\n".join(lines)


def render_sos_text():
    sos_list = list_sos()
    if not sos_list:
        return "SOS-чеклистов пока нет."
    lines = ["🚨 SOS чеклисты:\n"]
    for s in sos_list:
        lines.append(f"{s['id']}. {s['name']}")
        steps = s.get("steps") or []
        for i, st in enumerate(steps, start=1):
            lines.append(f"   {i}) {st}")
        lines.append("")
    return "\n".join(lines)


# ---------- MESSAGE ----------

def handle_text_message(message):
    chat_id = message["chat"]["id"]
    text = (message.get("text") or "").strip()

    pending = get_pending_action() or {}

    if pending:
        ptype = pending.get("type")
        if ptype == "add_inbox":
            set_pending_action(None)
            handle_add_inbox_text(chat_id, text)
            return
        if ptype == "edit_task":
            task_id = pending.get("task_id")
            set_pending_action(None)
            if task_id is None:
                send_message(chat_id, "Не знаю, какую задачу редактировать.")
                return
            handle_edit_task_text(chat_id, text, int(task_id))
            return
        if ptype == "done_comment":
            task_id = pending.get("task_id")
            set_pending_action(None)
            if task_id is None:
                send_message(chat_id, "Не знаю, к какой задаче комментарий.")
                return
            handle_done_comment(chat_id, text, int(task_id))
            return
        if ptype == "set_deadline":
            task_id = pending.get("task_id")
            set_pending_action(None)
            if task_id is None:
                send_message(chat_id, "Не знаю, для какой задачи дедлайн.")
                return
            handle_set_deadline(chat_id, text, int(task_id))
            return
        if ptype == "set_priority":
            task_id = pending.get("task_id")
            set_pending_action(None)
            if task_id is None:
                send_message(chat_id, "Не знаю, для какой задачи приоритет.")
                return
            handle_set_priority(chat_id, text, int(task_id))
            return
        if ptype == "move_task_to_project":
            task_id = pending.get("task_id")
            set_pending_action(None)
            if task_id is None:
                send_message(chat_id, "Не знаю, какую задачу переносить.")
                return

            projects = list_projects()
            raw = text.strip()
            target_project = None

            if raw.isdigit():
                pid = int(raw)
                for p in projects:
                    if p["id"] == pid:
                        target_project = p
                        break
                if not target_project:
                    send_message(chat_id, f"Проект с номером {pid} не найден.")
                    return
            else:
                target_project = add_project(raw)
                send_message(chat_id, f"Создала новый проект: {target_project['name']}.")

            task = get_task_by_id(int(task_id))
            if not task:
                send_message(chat_id, "Не нашла задачу для перемещения.")
                return
            proj, step = add_project_step(target_project["id"], task["text"])
            delete_task_by_id(int(task_id))
            send_message(
                chat_id,
                f"Перенесла задачу в проект «{target_project['name']}» как шаг: {step['text']}",
            )
            return

    # команды и кнопки
    if text == "/start":
        send_message(
            chat_id,
            "Привет! Это твой планировщик.\n\n"
            "Кнопки внизу: инбокс, сегодня, завтра, рутины, проекты и т.п.",
            reply_markup=main_keyboard(),
        )
        return

    if text in ("/menu", "⚙️ Меню"):
        send_message(
            chat_id,
            "Главное меню.\n\n"
            "📥 Инбокс — собрать и разобрать задачи\n"
            "📅 Сегодня / 📆 Завтра — задачи на эти дни\n"
            "🔁 Рутины — утро/вечер/уборка\n"
            "📑 Шаблоны дня — будни, выходные, день минимума\n"
            "🌱 Привычки — вода, зарядка, английский\n"
            "📂 Проекты — большие цели\n"
            "🚨 SOS — действия при стрессе, бессоннице и т.п.",
            reply_markup=main_keyboard(),
        )
        return

    if text in ("/inbox", "📥 Инбокс"):
        send_inbox(chat_id)
        return

    if text in ("/today", "📅 Сегодня"):
        send_today_screen(chat_id)
        return

    if text in ("/tomorrow", "📆 Завтра"):
        send_tomorrow_screen(chat_id)
        return

    if text in ("/routines", "🔁 Рутины"):
        send_message(chat_id, render_routines_text(), reply_markup=main_keyboard())
        return

    if text in ("/templates", "📑 Шаблоны дня"):
        send_message(chat_id, render_templates_text(), reply_markup=main_keyboard())
        return

    if text in ("/habits", "🌱 Привычки"):
        send_message(chat_id, render_habits_text(), reply_markup=main_keyboard())
        return

    if text in ("/projects", "📂 Проекты"):
        send_message(chat_id, render_projects_text(), reply_markup=main_keyboard())
        return

    if text in ("/sos", "🚨 SOS чеклисты"):
        send_message(chat_id, render_sos_text(), reply_markup=main_keyboard())
        return

    # мультивыбор: "1 3 5 today"
    multi_match = re.match(r"^([\d,\s\-]+)\s+(\S+)$", text.strip())
    if multi_match:
        ids_part, cmd = multi_match.groups()
        cmd = cmd.lower()

        raw_tokens = re.split(r"[,\s]+", ids_part)
        task_ids = []
        for tok in raw_tokens:
            if "-" in tok:
                try:
                    start, end = tok.split("-", 1)
                    start_i = int(start)
                    end_i = int(end)
                    if start_i <= end_i:
                        task_ids.extend(range(start_i, end_i + 1))
                except ValueError:
                    continue
            elif tok.isdigit():
                task_ids.append(int(tok))

        task_ids = sorted(set(task_ids))

        if task_ids and cmd in (
            "today",
            "сегодня",
            "tomorrow",
            "завтра",
            "done",
            "готово",
            "delete",
            "удалить",
        ):
            ok_ids = []
            fail_ids = []

            for tid in task_ids:
                success = False
                if cmd in ("today", "сегодня"):
                    success = add_today_from_task(tid) is not None
                elif cmd in ("tomorrow", "завтра"):
                    success = add_tomorrow_from_task(tid) is not None
                elif cmd in ("done", "готово"):
                    success, _ = complete_task_by_id(tid)
                elif cmd in ("delete", "удалить"):
                    success = delete_task_by_id(tid)
                if success:
                    ok_ids.append(tid)
                else:
                    fail_ids.append(tid)

            if ok_ids:
                action_name = {
                    "today": "в «Сегодня»",
                    "сегодня": "в «Сегодня»",
                    "tomorrow": "на «Завтра»",
                    "завтра": "на «Завтра»",
                    "done": "как выполненные",
                    "готово": "как выполненные",
                    "delete": "как удалённые",
                    "удалить": "как удалённые",
                }[cmd]
                send_message(chat_id, f"Обработала задачи {ok_ids} {action_name}.")
            if fail_ids:
                send_message(chat_id, f"Не нашла задачи: {fail_ids}.")
            return

    # одиночный номер: "3"
    m = re.match(r"^(\d+)$", text)
    if m:
        task_id = int(m.group(1))
        task = get_task_by_id(task_id)
        if not task:
            send_message(chat_id, f"Не нашла задачу #{task_id}.")
            return
        card = render_task_card(task)
        kb = task_inline_keyboard(task_id)
        send_message(chat_id, card, reply_markup=kb)
        return

    # всё остальное — добавляем в инбокс
    handle_add_inbox_text(chat_id, text)


# ---------- CALLBACK_QUERY ----------

def handle_callback(callback_query):
    cq_id = callback_query["id"]
    data = callback_query.get("data") or ""
    message = callback_query.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    message_id = message.get("message_id")

    if not chat_id:
        answer_callback_query(cq_id)
        return

    if data == "inbox_add":
        answer_callback_query(cq_id)
        set_pending_action({"type": "add_inbox"})
        send_message(
            chat_id,
            "Отправь одну задачу или список задач (каждая с новой строки).\n"
            "Нумерация 1., 2) и т.п. будет автоматически убрана.",
        )
        return

    if data == "inbox_refresh":
        answer_callback_query(cq_id)
        text, tasks = render_inbox_text()
        kb = inbox_inline_keyboard(tasks)
        if message_id:
            try:
                edit_message(chat_id, message_id, text, reply_markup=kb)
            except Exception:
                send_inbox(chat_id)
        else:
            send_inbox(chat_id)
        return

    if data.startswith("task_delete:"):
        _, sid = data.split(":", 1)
        tid = int(sid)
        ok = delete_task_by_id(tid)
        answer_callback_query(cq_id, "Удалено" if ok else "Не нашла задачу")
        send_inbox(chat_id)
        return

    if data.startswith("task_edit:"):
        _, sid = data.split(":", 1)
        tid = int(sid)
        set_pending_action({"type": "edit_task", "task_id": tid})
        answer_callback_query(cq_id)
        send_message(chat_id, f"Напиши новый текст для задачи #{tid}.")
        return

    if data.startswith("task_done:"):
        _, sid = data.split(":", 1)
        tid = int(sid)
        ok, task = complete_task_by_id(tid)
        if not ok:
            answer_callback_query(cq_id, "Не нашла задачу")
            return
        answer_callback_query(cq_id, "Отметила как выполненную")
        set_pending_action({"type": "done_comment", "task_id": tid})
        send_message(
            chat_id,
            f"Задача #{tid} отмечена как выполненная.\n"
            "Хочешь добавить короткий комментарий? Если нет — напиши «-».",
        )
        return

    if data.startswith("task_today:"):
        _, sid = data.split(":", 1)
        tid = int(sid)
        item = add_today_from_task(tid)
        if not item:
            answer_callback_query(cq_id, "Не нашла задачу")
            return
        answer_callback_query(cq_id, "Добавила в «Сегодня»")
        return

    if data.startswith("task_tomorrow:"):
        _, sid = data.split(":", 1)
        tid = int(sid)
        item = add_tomorrow_from_task(tid)
        if not item:
            answer_callback_query(cq_id, "Не нашла задачу")
            return
        answer_callback_query(cq_id, "Добавила на «Завтра»")
        return

    if data.startswith("task_deadline:"):
        _, sid = data.split(":", 1)
        tid = int(sid)
        set_pending_action({"type": "set_deadline", "task_id": tid})
        answer_callback_query(cq_id)
        send_message(
            chat_id,
            "Напиши дедлайн для задачи.\n"
            "Например: «сегодня», «завтра» или дату ГГГГ-ММ-ДД.",
        )
        return

    if data.startswith("task_priority:"):
        _, sid = data.split(":", 1)
        tid = int(sid)
        set_pending_action({"type": "set_priority", "task_id": tid})
        answer_callback_query(cq_id)
        send_message(
            chat_id,
            "Матрица Эйзенхауэра.\n"
            "Напиши число 1–4:\n"
            "1 — Срочно и важно\n"
            "2 — Срочно, но не важно\n"
            "3 — Не срочно, но важно\n"
            "4 — Не срочно и не важно",
        )
        return

    if data.startswith("task_move:"):
        _, sid = data.split(":", 1)
        tid = int(sid)
        set_pending_action({"type": "move_task_to_project", "task_id": tid})
        answer_callback_query(cq_id)
        projects = list_projects()
        if projects:
            lines = ["Куда перенести задачу?\n", "Существующие проекты:"]
            for p in projects:
                lines.append(f"{p['id']}. {p['name']}")
            lines.append("")
            lines.append(
                "Напиши номер проекта или новое название проекта,\n"
                "и я создам его и перенесу туда задачу."
            )
            send_message(chat_id, "\n".join(lines))
        else:
            send_message(
                chat_id,
                "У тебя пока нет проектов.\n"
                "Напиши название нового проекта, и я создам его и перенесу туда задачу.",
            )
        return

    answer_callback_query(cq_id)


# ---------- FLASK ROUTES ----------

@app.route("/", methods=["GET"])
def index():
    return "Bot is running"


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)

    if "callback_query" in data:
        handle_callback(data["callback_query"])
        return "ok"

    message = data.get("message")
    if message and "text" in message:
        handle_text_message(message)
    return "ok"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)