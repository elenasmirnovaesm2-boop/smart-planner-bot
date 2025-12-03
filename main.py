import os
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Не задан TELEGRAM_BOT_TOKEN")

bot = Bot(TOKEN)
app = Flask(__name__)

# Диспетчер обрабатывает апдейты
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)


def start(update, context):
    update.message.reply_text("Привет! Я тестовый бот на Render с webhook 🧪")


def echo(update, context):
    text = update.message.text or ""
    update.message.reply_text(f"Ты написала: {text}")


# Регистрируем хендлеры
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))


@app.route("/" + TOKEN, methods=["POST"])
def webhook():
    """Сюда Telegram будет присылать апдейты."""
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"


@app.route("/", methods=["GET"])
def index():
    return "ok"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)