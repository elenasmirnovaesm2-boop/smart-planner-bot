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
    set_pending_action,
    get_pending_action,
    get_task_by_id,
    list_routines,
    list_templates,
    list_habits,
    list_projects,
    list_sos,
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


# ---------- КЛАВИАТУРЫ ----------

def main_keyboard():
    return {
        "keyboard": [
            [{"text": "📥 Инбокс"}, {"text": "📅 Сегодня"}],
            [{"text": "🔁 Рутины"}, {"text": "📑 Шаблоны дня"}],
            [{"text": "🌱 Привычки"}, {"text": "📂 Проекты"}],
            [{"text": "🚨 SOS чеклисты"}, {"text": "⚙️ Меню"}],
        ],
        "resize_keyboard": True,
    }


def inbox_inline_keyboard(tasks):
    # Только общие кнопки — без отдельных кнопок для каждой задачи и без "В меню"
    return {
        "inline_keyboard": [
            [
                {"text": "➕ Добавить", "callback_data": "inbox_add"},
                {"text": "🔄 Обновить", "callback_data": "inbox_refresh"},
            ]
        ]
    }


def task_inline_keyboard(task_id):
    # Карточка задачи без "в инбокс", с дедлайном, приоритетом и перемещением
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Готово", "callback_data": f"task_done:{task_id}"},
                {"text": "✏️ Редактировать", "callback_data": f"task_edit:{task_id}"},
            ],
            [
                {"text": "➡️ В Сегодня", "callback_data": f"task_today:{task_id}"},
                {"text": "⏳ Дедлайн", "callback_data": f"task_deadline:{task_id}"},
                {"text": "⚡ Важность", "callback_data": f"task_priority:{task_id}"},
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
    lines.append("Выбери задачу: просто напиши её номер (например: 3)")
    return "\n".join(lines), tasks


def send_inbox(chat_id):
    text, tasks = render_inbox_text()
    kb = inbox_inline_keyboard(tasks)
    send_message(chat_id, text, reply_markup=kb)


def render_task_card(task):
    status = "выполнена ✅" if task.get("done") else "не выполнена"
    comment = task.get("done_comment")
    comment_part = f"\nКомментарий: {comment}" if comment else ""
    created_at = task.get("created_at", "—")
    deadline = task.get("deadline", "не установлен")
    importance = task.get("importance", "не классифицировано")
    return (
        f"📝 Задача #{task['id']}\n\n"
        f"Текст: {task['text']}\n"
        f"Создано: {created_at}\n"
        f"Статус: {status}\n\n"
        f"Матрица Эйзенхауэра: {importance}\n"
        f"Дедлайн: {deadline}"
        f"{comment_part}"
    )


def handle_add_inbox_text(chat_id, text):
    # Разбиваем текст на строки, создаём несколько задач, если их несколько
    lines = [line.strip() for line in text.split("\n")]
    lines = [ln for ln in lines if ln]  # убираем пустые

    if not lines:
        send_message(chat_id, "Не нашла текста для задач. Отправь текст ещё раз.")
        return

    created = []

    for ln in lines:
        # убираем нумерацию вида "1. ", "2) ", "- " в начале
        ln = re.sub(r"^\s*[\-\d]+[\.\)]\s*", "", ln).strip()
        if not ln:
            continue
        task = add_task(ln)
        created.append(task)

    if not created:
        send_message(chat_id, "Ничего не добавила. Попробуй сформулировать задачи ещё раз.")
        return

    if len(created) == 1:
        send_message(chat_id, f"Добавила задачу #{created[0]['id']}: {created[0]['text']}")
    else:
        send_message(chat_id, f"Добавила {len(created)} задач в инбокс.")

    # после добавления показываем обновлённый инбокс
    send_inbox(chat_id)


def handle_edit_task_text(chat_id, text, task_id):
    ok, task = update_task_text(task_id, text)
    if not ok:
        send_message(chat_id, "Не нашла эту задачу. Возможно, она уже была удалена.")
        return
    send_message(chat_id, f"Обновила задачу #{task_id}.")
    # показываем карточку
    card = render_task_card(task)
    kb = task_inline_keyboard(task_id)
    send_message(chat_id, card, reply_markup=kb)


def handle_done_comment(chat_id, text, task_id):
    from storage import save_tasks, load_tasks  # импорт тут, чтобы не ломать остальной код

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
    """
    Устанавливаем дедлайн задаче.
    Принимаем:
      - 'сегодня' / 'today'
      - 'завтра' / 'tomorrow'
      - или любую строку как есть
    """
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
        # оставляем как ввели
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
    """
    Устанавливаем приоритет по матрице Эйзенхауэра.
    Ожидаем:
      1 — срочно и важно
      2 — срочно, но не важно
      3 — не срочно, но важно
      4 — не срочно и не важно
    Можно вводить цифру или текстом.
    """
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

    # разрешаем вводить текстом
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
            send_message(chat_id, f"Установила приоритет для задачи #{task_id}: {value}")
            return
    send_message(chat_id, "Не нашла задачу для установки приоритета.")


# ---------- ЭКРАНЫ: РУТИНЫ / ШАБЛОНЫ / ПРИВЫЧКИ / ПРОЕКТЫ / SOS ----------

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


# ---------- ОБРАБОТКА MESSAGE ----------

def handle_text_message(message):
    chat_id = message["chat"]["id"]
    text = (message.get("text") or "").strip()

    # state (ожидаем следующий шаг)
    pending = get_pending_action() or {}

    # 1. специальные режимы (редактирование, добавление и т.п.)
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
                send_message(chat_id, "Что-то пошло не так: не знаю, какую задачу редактировать.")
                return
            handle_edit_task_text(chat_id, text, int(task_id))
            return
        if ptype == "done_comment":
            task_id = pending.get("task_id")
            set_pending_action(None)
            if task_id is None:
                send_message(chat_id, "Что-то пошло не так: не знаю, к какой задаче добавить комментарий.")
                return
            handle_done_comment(chat_id, text, int(task_id))
            return
        if ptype == "set_deadline":
            task_id = pending.get("task_id")
            set_pending_action(None)
            if task_id is None:
                send_message(chat_id, "Не знаю, для какой задачи установить дедлайн.")
                return
            handle_set_deadline(chat_id, text, int(task_id))
            return
        if ptype == "set_priority":
            task_id = pending.get("task_id")
            set_pending_action(None)
            if task_id is None:
                send_message(chat_id, "Не знаю, для какой задачи установить приоритет.")
                return
            handle_set_priority(chat_id, text, int(task_id))
            return

    # 2. обычные команды и кнопки
    if text == "/start":
        send_message(
            chat_id,
            "Привет! Это твой планировщик.\n\n"
            "Используй кнопки ниже, чтобы работать с задачами, рутинами и шаблонами.",
            reply_markup=main_keyboard(),
        )
        return

    if text in ("/menu", "⚙️ Меню"):
        send_message(
            chat_id,
            "Главное меню.\n\n"
            "📥 Инбокс — собрать и разобрать задачи\n"
            "📅 Сегодня — задачи на сегодня (позже)\n"
            "🔁 Рутины — утро/вечер/уборка и т.п.\n"
            "📑 Шаблоны дня — будни, выходные, день минимума\n"
            "🌱 Привычки — вода, зарядка, английский\n"
            "📂 Проекты — большие цели\n"
            "🚨 SOS — действия при стрессе, бессоннице и т.п.\n",
            reply_markup=main_keyboard(),
        )
        return

    if text in ("/inbox", "📥 Инбокс"):
        send_inbox(chat_id)
        return

    if text in ("/today", "📅 Сегодня"):
        send_message(
            chat_id,
            "Экран «Сегодня» мы ещё доделаем.\n"
            "Сейчас можно добавлять задачи в «Сегодня» так:\n"
            "— открыть инбокс\n"
            "— посмотреть номер задачи\n"
            "— написать: 3 today",
            reply_markup=main_keyboard(),
        )
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

    # 3. короткие команды вида "N ..." (работа с задачами по номеру)
    m = re.match(r"^(\d+)(?:\s+(.+))?$", text)
    if m:
        task_id = int(m.group(1))
        cmd = (m.group(2) or "").strip().lower()

        # если есть доп.команда после номера
        if cmd:
            if cmd in ("today", "сегодня"):
                item = add_today_from_task(task_id)
                if item:
                    send_message(chat_id, f"Добавила задачу #{task_id} в «Сегодня».")
                else:
                    send_message(chat_id, f"Не нашла задачу #{task_id}.")
                return

            if cmd in ("done", "готово"):
                ok, _ = complete_task_by_id(task_id)
                if ok:
                    send_message(chat_id, f"Задача #{task_id} отмечена как выполненная.")
                else:
                    send_message(chat_id, f"Не нашла задачу #{task_id}.")
                return

            if cmd in ("delete", "удалить"):
                ok = delete_task_by_id(task_id)
                if ok:
                    send_message(chat_id, f"Удалена задача #{task_id}.")
                else:
                    send_message(chat_id, f"Не нашла задачу #{task_id}.")
                return

        # если доп.команды нет — просто открываем карточку задачи
        task = get_task_by_id(task_id)
        if not task:
            send_message(chat_id, f"Не нашла задачу #{task_id}.")
            return

        card = render_task_card(task)
        kb = task_inline_keyboard(task_id)
        send_message(chat_id, card, reply_markup=kb)
        return

    # 4. всё остальное считаем новыми задачами в инбоксе
    handle_add_inbox_text(chat_id, text)


# ---------- ОБРАБОТКА CALLBACK_QUERY ----------

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

    if data == "inbox_refresh" or data == "back_inbox":
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

    # действия с конкретными задачами
    if data.startswith("task_open:"):
        _, sid = data.split(":", 1)
        tid = int(sid)
        task = get_task_by_id(tid)
        if not task:
            answer_callback_query(cq_id, "Задача не найдена")
            return
        answer_callback_query(cq_id)
        card = render_task_card(task)
        kb = task_inline_keyboard(tid)
        if message_id:
            try:
                edit_message(chat_id, message_id, card, reply_markup=kb)
            except Exception:
                send_message(chat_id, card, reply_markup=kb)
        else:
            send_message(chat_id, card, reply_markup=kb)
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
            "Хочешь добавить короткий комментарий (сложности, как прошло)?\n"
            "Если нет — напиши «-».",
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

    if data.startswith("task_deadline:"):
        _, sid = data.split(":", 1)
        tid = int(sid)
        set_pending_action({"type": "set_deadline", "task_id": tid})
        answer_callback_query(cq_id)
        send_message(
            chat_id,
            "Напиши дедлайн для задачи в удобном виде.\n"
            "Например: «сегодня», «завтра» или дату в формате ГГГГ-ММ-ДД.",
        )
        return

    if data.startswith("task_priority:"):
        _, sid = data.split(":", 1)
        tid = int(sid)
        set_pending_action({"type": "set_priority", "task_id": tid})
        answer_callback_query(cq_id)
        send_message(
            chat_id,
            "Укажи приоритет (матрица Эйзенхауэра).\n"
            "Напиши число 1–4:\n"
            "1 — Срочно и важно\n"
            "2 — Срочно, но не важно\n"
            "3 — Не срочно, но важно\n"
            "4 — Не срочно и не важно",
        )
        return

    if data.startswith("task_move:"):
        # пока только заглушка, чтобы кнопка не ломала ничего
        answer_callback_query(cq_id, "Перемещение в другие сущности пока не реализовано.")
        return

    # если что-то неизвестное
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
    if message:
        if "text" in message:
            handle_text_message(message)
    return "ok"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)