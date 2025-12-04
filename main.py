import os
import re
import requests
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
            [{"text": "⚙️ Меню"}],
        ],
        "resize_keyboard": True,
    }


def inbox_inline_keyboard(tasks):
    # Кнопки для задач (#1, #2, ...)
    task_buttons = []
    for t in tasks:
        btn = {
            "text": f"#{t['id']}",
            "callback_data": f"task_open:{t['id']}",
        }
        task_buttons.append([btn])

    # Общие кнопки
    common = [
        [
            {"text": "➕ Добавить", "callback_data": "inbox_add"},
            {"text": "🔄 Обновить", "callback_data": "inbox_refresh"},
        ],
        [{"text": "⬅️ В меню", "callback_data": "back_menu"}],
    ]
    return {"inline_keyboard": common + task_buttons}


def task_inline_keyboard(task_id):
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Готово", "callback_data": f"task_done:{task_id}"},
                {"text": "✏️ Редактировать", "callback_data": f"task_edit:{task_id}"},
            ],
            [
                {"text": "🗑 Удалить", "callback_data": f"task_delete:{task_id}"},
                {"text": "➡️ В Сегодня", "callback_data": f"task_today:{task_id}"},
            ],
            [
                {"text": "⬅️ В инбокс", "callback_data": "back_inbox"},
            ],
        ]
    }


# ---------- ЛОГИКА: ИНБОКС ----------

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
    return (
        f"Задача #{task['id']}\n\n"
        f"Текст: {task['text']}\n"
        f"Статус: {status}{comment_part}"
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

    # 2. обычные команды и кнопки
    if text == "/start":
        send_message(
            chat_id,
            "Привет! Это твой планировщик.\n\n"
            "Используй кнопки ниже, чтобы работать с задачами.",
            reply_markup=main_keyboard(),
        )
        return

    if text in ("/menu", "⚙️ Меню"):
        send_message(
            chat_id,
            "Главное меню.\n\n"
            "📥 Инбокс — собрать и разобрать задачи\n"
            "📅 Сегодня — задачи на сегодня (позже)\n",
            reply_markup=main_keyboard(),
        )
        return

    if text in ("/inbox", "📥 Инбокс"):
        send_inbox(chat_id)
        return

    if text == "📅 Сегодня":
        send_message(chat_id, "Экран «Сегодня» мы ещё доделаем. Пока работаем с инбоксом 🤓")
        return

    # по умолчанию
    send_message(chat_id, "Не знаю такую команду. Нажми «⚙️ Меню» или «📥 Инбокс».", reply_markup=main_keyboard())


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

    # навигация
    if data == "back_menu":
        answer_callback_query(cq_id)
        send_message(chat_id, "Главное меню:", reply_markup=main_keyboard())
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
        from storage import get_task_by_id
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
        # на будущее: можно обрабатывать фото/документы
    return "ok"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)