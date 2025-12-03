import os
import requests
from flask import Flask, request

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Не задан TELEGRAM_BOT_TOKEN")

API_URL = f"https://api.telegram.org/bot{TOKEN}/"

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    return "Bot is running"


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)

    # Проверяем, что это обычное сообщение
    message = data.get("message")
    if not message:
        return "ok"

    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    # Простейшая логика: /start и эхо
    if text == "/start":
        reply = "Привет! Я тестовый бот на вебхуке без сложных библиотек 🧪"
    else:
        reply = f"Ты написала: {text}"

    # Отправляем ответ через HTTP API Telegram
    requests.post(
        API_URL + "sendMessage",
        json={"chat_id": chat_id, "text": reply},
        timeout=5,
    )

    return "ok"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)