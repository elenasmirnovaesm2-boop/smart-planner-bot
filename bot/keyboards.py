"""
Defines the main reply keyboard for the bot.

This version extends the main keyboard with a “ℹ️ Команды” button so
users can quickly access a list of text commands. It intentionally
omits any inline keyboards for individual tasks; management is done via
text commands instead.
"""


def main_keyboard() -> dict:
    """
    Return the main reply keyboard layout. Includes buttons for the inbox
    and other entity lists (Сегодня, рутины, шаблоны, проекты, SOS, привычки)
    plus a separate button for the commands list.
    """
    return {
        "keyboard": [
            [{"text": "📝 Инбокс"}, {"text": "📅 Сегодня"}],
            [{"text": "📋 Рутины"}, {"text": "📅 Шаблоны"}, {"text": "📦 Проекты"}],
            [{"text": "🆘 SOS"}, {"text": "🔥 Привычки"}, {"text": "🔆 Меню"}, {"text": "ℹ️ Команды"}],
        ],
        "resize_keyboard": True,
    }


def inbox_inline_keyboard(tasks: list) -> dict:
    """
    Return an empty inline keyboard. Formerly, this built buttons for each
    task, but we’ve removed inline keyboards in favor of text commands.
    """
    # Returning an empty inline keyboard structure keeps compatibility with
    # callers that still expect a dict. It will not render buttons.
    return {"inline_keyboard": []}


def task_inline_keyboard(task_id: int) -> dict:
    """
    Return an empty inline keyboard for a task. See inbox_inline_keyboard
    for discussion. Individual task actions are now handled via text commands.
    """
    return {"inline_keyboard": []}