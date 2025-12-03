import os
import requests
from flask import Flask, request
import logic_tasks

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Не задан TELEGRAM_BOT_TOKEN")

API_URL = f"https://api.telegram.org/bot{TOKEN}/"

# ТВОЙ TELEGRAM ID
ALLOWED_USER = 7604757170   # ← замени, если нужно

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    return "Bot is running"


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)

    # обработка callback кнопок
    callback = data.get("callback_query")
    if callback:
        user_id = callback["from"]["id"]
        chat_id = callback["message"]["chat"]["id"]
        message_id = callback["message"]["message_id"]
        data_str = callback["data"]

        if user_id != ALLOWED_USER:
            send_message(chat_id, "Нет доступа")
            return "ok"

        reply = logic_tasks.handle_callback(data_str)
        edit_message(chat_id, message_id, reply)
        return "ok"

    # обычное сообщение
    message = data.get("message")
    if not message:
        return "ok"

    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    text = message.get("text", "")

    if user_id != ALLOWED_USER:
        send_message(chat_id, "Нет доступа")
        return "ok"

    reply = logic_tasks.handle_update(text)

    # если логика вернула много сообщений
    if isinstance(reply, dict) and reply.get("multiple"):
        for item in reply["items"]:
            send_message_with_buttons(chat_id, item["text"], item["buttons"])
        return "ok"

    # одно сообщение с кнопками
    if isinstance(reply, dict) and reply.get("buttons"):
        send_message_with_buttons(chat_id, reply["text"], reply["buttons"])
        return "ok"

    # обычный текст
    send_message(chat_id, reply.get("text", reply))
    return "ok"


def send_message(chat_id, text):
    requests.post(
        API_URL + "sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=5,
    )


def send_message_with_buttons(chat_id, text, buttons):
    inline_buttons = []
    for b in buttons:
        inline_buttons.append([{
            "text": b["text"],
            "callback_data": b["callback"]
        }])

    requests.post(
        API_URL + "sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "reply_markup": {"inline_keyboard": inline_buttons}
        },
        timeout=5,
    )


def edit_message(chat_id, message_id, text):
    requests.post(
        API_URL + "editMessageText",
        json={
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text
        },
        timeout=5,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)