import os
import requests
from flask import Flask, request
import logic_tasks  # наша логика задач

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Не задан TELEGRAM_BOT_TOKEN")

API_URL = f"https://api.telegram.org/bot{TOKEN}/"

# Твой Telegram ID
ALLOWED_USER = 7604757176  # ← если нужно, замени на свой

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    return "Bot is running"


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)

    message = data.get("message")
    if not message:
        return "ok"

    chat = message.get("chat") or {}
    from_user = message.get("from") or {}

    chat_id = chat.get("id")
    user_id = from_user.get("id")
    text = message.get("text", "") or ""

    # защита по ID
    if user_id != ALLOWED_USER:
        send_message(chat_id, "У вас нет доступа к этому боту")
        return "ok"

    # отдаём текст в логику задач
    reply = logic_tasks.handle_update(text)

    # отправляем ответ
    send_message(chat_id, reply)

    return "ok"


def send_message(chat_id, text: str):
    if not chat_id:
        return
    requests.post(
        API_URL + "sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=5,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)