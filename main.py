"""
Main entry point for the smart planner bot.

This simplified version demonstrates how to route incoming text messages
and handle commands without using inline keyboards. It includes a
commands list and uses the new keyboard layout defined in bot/keyboards.py.
Note: For brevity, many auxiliary functions (e.g. get_reply_context,
handle_inbox_command) are omitted; in a full application you would
retain their existing logic and extend as necessary.
"""

from bot.keyboards import main_keyboard
from bot.inbox import send_inbox, handle_add_inbox_text, handle_edit_task_text, parse_task_ids, render_inbox_text
from bot.telegram_api import send_message


def handle_text_message(message: dict):
    """
    Handle a text message sent to the bot. This function demonstrates
    how to present the menu and commands list, as well as forward
    messages to other handlers (e.g. inbox) based on context.
    """
    chat_id = message["chat"]["id"]
    text = (message.get("text") or "").strip()

    # Start command: greet and show main keyboard
    if text == "/start":
        send_message(chat_id, "Привет! Это твой планировщик.\nИспользуй кнопки ниже для работы с задачами, рутинами и шаблонами.", reply_markup=main_keyboard())
        return

    # Show main menu
    if text in ("/menu", "🔆 Меню"):
        send_message(chat_id, "Главное меню.\n\nНажми «ℹ️ Команды» чтобы посмотреть список текстовых команд.", reply_markup=main_keyboard())
        return

    # Show list of commands
    if text in ("/commands", "ℹ️ Команды"):
        send_message(
            chat_id,
            "Список команд:\n"
            "• add <текст> — добавить задачу в текущий список.\n"
            "• edit <ID> <новый текст> — изменить текст задачи.\n"
            "• del <ID или диапазон> — удалить одну или несколько задач.\n"
            "• mv <ID> today — перенести задачу в список ‘Сегодня’.\n"
            "• open <ID> — открыть подробный вид задачи.\n\n"
            "Например: 'add Купить продукты' или 'del 1 3-5'",
        )
        return

    # Routing examples: send inbox or handle add commands
    if text in ("/inbox", "📝 Инбокс"):
        send_inbox(chat_id)
        return

    # Example: treat any other message as text to add to inbox
    if text:
        handle_add_inbox_text(chat_id, text)
        return

    # Unknown or empty message
    send_message(chat_id, "Не знаю такую команду. Нажми одну из кнопок меню.")