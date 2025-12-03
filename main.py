import os
import requests
from flask import Flask, request

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Не задан TELEGRAM_BOT_TOKEN")

API_URL = f"https://api.telegram.org/bot{TOKEN}/"

# ТВОЙ Telegram ID
ALLOWED_USER = 7604757170  # ← оставь свой ID здесь

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

    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]   # <-- вот ЭТО ID пользователя
    text = message.get("text", "")

    # 🔐 Проверяем именно user_id
    if user_id != ALLOWED_USER:
        requests.post(
            API_URL + "sendMessage",
            json={"chat_id": chat_id, "text": "У вас нет доступа"},
            timeout=5,
        )
        return "ok"

    # Небольшая подсказка в /start
    if text == "/start":
        reply = "Привет! Доступ разрешён только тебе 🙂"
    else:
        reply = f"Ты написала: {text}"

    requests.post(
        API_URL + "sendMessage",
        json={"chat_id": chat_id, "text": reply},
        timeout=5,
    )

    return "ok"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)