import os
from flask import Flask, request

from storage import (
    # задачи
    add_today_from_task,
    set_pending_action,
    get_pending_action,
    get_task_by_id,
    complete_task_by_id,
    delete_task_by_id,
    # сущности
    list_routines,
    list_templates,
    list_projects,
    list_sos,
    list_habits,
)

from bot.inbox import (
    send_inbox,
    render_inbox_text,
    render_task_card,
    handle_add_inbox_text,
    handle_edit_task_text,
    handle_done_comment,
    parse_task_ids,      # <── добавили
)

from bot.today import send_today, refresh_today

from bot.keyboards import (
    main_keyboard,
    inbox_inline_keyboard,
    task_inline_keyboard,
    simple_list_keyboard,
)

from bot.telegram_api import (
    send_message,
    edit_message,
    answer_callback_query,
)

from bot.entities import (
    render_routine_card,
    render_template_card,
    render_project_card,
    render_sos_card,
    render_habit_card,
)


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Не задан TELEGRAM_BOT_TOKEN")

app = Flask(__name__)


# ---------- ВСПОМОГАТЕЛЬНОЕ ----------

def get_reply_context(message):
    """
    Определяем контекст по сообщению, на которое идёт reply.
    Сейчас используем только:
    - 'inbox'  — если это список инбокса
    - 'today'  — если это список «Сегодня»
    Остальное можно будет добавить дальше (рутины, проекты и т.п.).
    """
    reply = message.get("reply_to_message")
    if not reply:
        return None

    from_user = reply.get("from") or {}
    if not from_user.get("is_bot"):
        return None

    text = (reply.get("text") or "").strip()

    if text.startswith("Твой инбокс:") or text.startswith("Инбокс пуст"):
        return "inbox"

    if text.startswith("Задачи на сегодня:") or "На сегодня пока ничего нет" in text:
        return "today"

    return None


def handle_inbox_command(chat_id, text):
    """
    Обработка команд в контексте ИНБОКСА при reply на список.
    Поддерживаются:
      add Текст
      edit ID Новый текст
      del 1 2 5-7
      mv ID... today
      open ID
    """
    raw = text.strip()
    if not raw:
        return False  # ничего не делали

    tokens = raw.split()
    cmd = tokens[0].lower()

    # --- ADD ---
    if cmd in ("add", "a"):
        new_text = raw[len(tokens[0]):].strip()
        if not new_text:
            send_message(chat_id, "После команды add нужно указать текст задачи.")
            return True
        handle_add_inbox_text(chat_id, new_text)
        return True

    # --- EDIT ---
    if cmd in ("edit", "e"):
        if len(tokens) < 3:
            send_message(chat_id, "Формат: edit <номер> <новый текст>")
            return True
        try:
            task_id = int(tokens[1])
        except ValueError:
            send_message(chat_id, "Номер задачи должен быть числом.")
            return True
        # восстановим текст после второго токена
        new_text = raw.split(None, 2)[2]
        handle_edit_task_text(chat_id, new_text, task_id)
        return True

    # --- DEL ---
    if cmd in ("del", "d"):
        if len(tokens) < 2:
            send_message(chat_id, "Формат: del <номера>, например: del 1 2 5-7")
            return True
        id_text = raw[len(tokens[0]):].strip()
        ids = parse_task_ids(id_text)
        if not ids:
            send_message(chat_id, "Не поняла номера задач. Пример: del 1 2 5-7")
            return True
        deleted = 0
        for tid in ids:
            if delete_task_by_id(tid):
                deleted += 1
        send_message(chat_id, f"Удалено задач: {deleted}.")
        send_inbox(chat_id)
        return True

    # --- MV ... today ---
    if cmd in ("mv", "move"):
        if len(tokens) < 3:
            send_message(chat_id, "Формат: mv <номера> today")
            return True
        target = tokens[-1].lower()
        if target != "today":
            send_message(chat_id, "Сейчас поддерживаю только mv ... today.")
            return True
        id_text = " ".join(tokens[1:-1])
        ids = parse_task_ids(id_text)
        if not ids:
            send_message(chat_id, "Не поняла номера задач для перемещения.")
            return True
        moved = 0
        for tid in ids:
            if add_today_from_task(tid):
                moved += 1
        send_message(chat_id, f"Перенесла в «Сегодня»: {moved} задач.")
        return True

    # --- OPEN ---
    if cmd == "open":
        if len(tokens) < 2:
            send_message(chat_id, "Формат: open <номер>")
            return True
        try:
            tid = int(tokens[1])
        except ValueError:
            send_message(chat_id, "Номер задачи должен быть числом.")
            return True
        task = get_task_by_id(tid)
        if not task:
            send_message(chat_id, f"Не нашла задачу #{tid}.")
            return True
        card = render_task_card(task)
        kb = task_inline_keyboard(tid)
        send_message(chat_id, card, reply_markup=kb)
        return True

    # если команда не распознана — вернём False,
    # чтобы можно было обработать текст как обычные задачи
    return False


# ---------- MESSAGE ----------

def handle_text_message(message):
    chat_id = message["chat"]["id"]
    text = (message.get("text") or "").strip()
    pending = get_pending_action() or {}
    context = get_reply_context(message)

    # 1) если отвечаем на список ИНБОКСА — пробуем интерпретировать как команду
    if context == "inbox" and not pending:
        if handle_inbox_command(chat_id, text):
            return  # команда обработана

    # 2) отложенное действие (редактирование, комментарий и т.п.)
    if pending:
        ptype = pending.get("type")
        if ptype == "add_inbox":
            set_pending_action(None)
            handle_add_inbox_text(chat_id, text)
            return
        if ptype == "edit_task":
            task_id = int(pending["task_id"])
            set_pending_action(None)
            handle_edit_task_text(chat_id, text, task_id)
            return
        if ptype == "done_comment":
            task_id = int(pending["task_id"])
            set_pending_action(None)
            handle_done_comment(chat_id, text, task_id)
            return

    # 3) команды / кнопки
    if text == "/start":
        send_message(
            chat_id,
            "Привет! Это твой планировщик.\n\n"
            "Используй кнопки ниже для работы с задачами, рутинами и шаблонами.",
            reply_markup=main_keyboard(),
        )
        return

    if text in ("/menu", "⚙️ Меню"):
        send_message(chat_id, "Главное меню.", reply_markup=main_keyboard())
        return

    if text in ("/inbox", "📥 Инбокс"):
        send_inbox(chat_id)
        return

    if text in ("📅 Сегодня", "/today"):
        send_today(chat_id)
        return

    # РУТИНЫ
    if text in ("🔁 Рутины", "/routines"):
        routines = list_routines()
        if not routines:
            send_message(chat_id, "Пока нет рутин.", reply_markup=main_keyboard())
            return
        kb = simple_list_keyboard("routine", routines)
        send_message(
            chat_id,
            "Твои рутины.\nПока только просмотр.\n\n"
            "Позже добавим редактирование и создание своих рутин.",
            reply_markup=kb,
        )
        return

    # ШАБЛОНЫ ДНЯ
    if text in ("📋 Шаблоны", "/templates"):
        templates = list_templates()
        if not templates:
            send_message(chat_id, "Пока нет шаблонов дня.", reply_markup=main_keyboard())
            return
        kb = simple_list_keyboard("template", templates)
        send_message(chat_id, "Твои шаблоны дня:", reply_markup=kb)
        return

    # ПРОЕКТЫ
    if text in ("📂 Проекты", "/projects"):
        projects = list_projects()
        if not projects:
            send_message(chat_id, "Пока нет проектов.", reply_markup=main_keyboard())
            return
        kb = simple_list_keyboard("project", projects)
        send_message(chat_id, "Твои проекты:", reply_markup=kb)
        return

    # SOS
    if text in ("🆘 SOS", "/sos"):
        sos_list = list_sos()
        if not sos_list:
            send_message(chat_id, "Пока нет SOS-чеклистов.", reply_markup=main_keyboard())
            return
        kb = simple_list_keyboard("sos", sos_list)
        send_message(chat_id, "Твои SOS-чеклисты:", reply_markup=kb)
        return

    # ПРИВЫЧКИ
    if text in ("📊 Привычки", "/habits"):
        habits = list_habits()
        if not habits:
            send_message(chat_id, "Пока нет привычек.", reply_markup=main_keyboard())
            return
        kb = simple_list_keyboard("habit", habits)
        send_message(chat_id, "Твои привычки:", reply_markup=kb)
        return

    # если это неизвестная команда (начинается с /) — не добавляем в инбокс
    if text.startswith("/"):
        send_message(chat_id, "Не знаю такую команду. Нажми кнопки внизу.")
        return

    # 4) по умолчанию — считаем текст списком задач для инбокса
    handle_add_inbox_text(chat_id, text)


# ---------- CALLBACK ----------

def handle_callback(callback_query):
    cq_id = callback_query["id"]
    data = callback_query.get("data") or ""
    msg = callback_query.get("message") or {}
    chat_id = msg.get("chat", {}).get("id")
    message_id = msg.get("message_id")

    if not chat_id:
        answer_callback_query(cq_id)
        return

    # навигация
    if data == "back_menu":
        answer_callback_query(cq_id)
        send_message(chat_id, "Главное меню.", reply_markup=main_keyboard())
        return

    # инбокс
    if data == "inbox_add":
        answer_callback_query(cq_id)
        set_pending_action({"type": "add_inbox"})
        send_message(chat_id, "Отправь одну или несколько задач (каждая с новой строки).")
        return

    if data in ("inbox_refresh", "back_inbox"):
        answer_callback_query(cq_id)
        text, tasks = render_inbox_text()
        kb = inbox_inline_keyboard(tasks)
        try:
            edit_message(chat_id, message_id, text, reply_markup=kb)
        except Exception:
            send_inbox(chat_id)
        return

    # сегодня
    if data == "today_refresh":
        answer_callback_query(cq_id)
        if message_id:
            refresh_today(chat_id, message_id)
        else:
            send_today(chat_id)
        return

    # действия с задачами
    if data.startswith("task_open:"):
        _, sid = data.split(":")
        tid = int(sid)
        task = get_task_by_id(tid)
        if not task:
            answer_callback_query(cq_id, "Не найдено")
            return
        answer_callback_query(cq_id)
        card = render_task_card(task)
        kb = task_inline_keyboard(tid)
        try:
            edit_message(chat_id, message_id, card, reply_markup=kb)
        except Exception:
            send_message(chat_id, card, reply_markup=kb)
        return

    if data.startswith("task_delete:"):
        _, sid = data.split(":")
        tid = int(sid)
        ok = delete_task_by_id(tid)
        answer_callback_query(cq_id, "Удалено" if ok else "Не найдено")
        send_inbox(chat_id)
        return

    if data.startswith("task_edit:"):
        _, sid = data.split(":")
        tid = int(sid)
        answer_callback_query(cq_id)
        set_pending_action({"type": "edit_task", "task_id": tid})
        send_message(chat_id, f"Напиши новый текст для задачи #{tid}.")
        return

    if data.startswith("task_done:"):
        _, sid = data.split(":")
        tid = int(sid)
        ok, task = complete_task_by_id(tid)
        if not ok:
            answer_callback_query(cq_id, "Не найдено")
            return
        answer_callback_query(cq_id, "Готово")
        set_pending_action({"type": "done_comment", "task_id": tid})
        send_message(
            chat_id,
            f"Задача #{tid} отмечена как выполненная.\n"
            "Добавь комментарий или напиши «-».",
        )
        return

    if data.startswith("task_today:"):
        _, sid = data.split(":")
        tid = int(sid)
        item = add_today_from_task(tid)
        answer_callback_query(cq_id, "Добавила" if item else "Не нашла")
        return

    # карточки сущностей
    if data.startswith("routine_open:"):
        _, sid = data.split(":")
        rid = int(sid)
        routines = list_routines()
        r = next((x for x in routines if x["id"] == rid), None)
        if not r:
            answer_callback_query(cq_id, "Не нашла рутину")
            return
        answer_callback_query(cq_id)
        send_message(chat_id, render_routine_card(r), reply_markup=main_keyboard())
        return

    if data.startswith("template_open:"):
        _, sid = data.split(":")
        tid = int(sid)
        templates = list_templates()
        tpl = next((x for x in templates if x["id"] == tid), None)
        if not tpl:
            answer_callback_query(cq_id, "Не нашла шаблон")
            return
        answer_callback_query(cq_id)
        send_message(chat_id, render_template_card(tpl), reply_markup=main_keyboard())
        return

    if data.startswith("project_open:"):
        _, sid = data.split(":")
        pid = int(sid)
        projects = list_projects()
        p = next((x for x in projects if x["id"] == pid), None)
        if not p:
            answer_callback_query(cq_id, "Не нашла проект")
            return
        answer_callback_query(cq_id)
        send_message(chat_id, render_project_card(p), reply_markup=main_keyboard())
        return

    if data.startswith("sos_open:"):
        _, sid = data.split(":")
        sid_int = int(sid)
        sos_items = list_sos()
        s = next((x for x in sos_items if x["id"] == sid_int), None)
        if not s:
            answer_callback_query(cq_id, "Не нашла SOS")
            return
        answer_callback_query(cq_id)
        send_message(chat_id, render_sos_card(s), reply_markup=main_keyboard())
        return

    if data.startswith("habit_open:"):
        _, sid = data.split(":")
        hid = int(sid)
        habits = list_habits()
        h = next((x for x in habits if x["id"] == hid), None)
        if not h:
            answer_callback_query(cq_id, "Не нашла привычку")
            return
        answer_callback_query(cq_id)
        send_message(chat_id, render_habit_card(h), reply_markup=main_keyboard())
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