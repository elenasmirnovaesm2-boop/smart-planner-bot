import storage


def handle_update(text: str):
    """Главная точка входа логики."""
    text = (text or "").strip()

    if text.startswith("/"):
        return handle_command(text)

    return handle_plain_text(text)


def handle_plain_text(text: str):
    """Обычное сообщение → новая задача."""
    if not text:
        return {"text": "Пустую задачу не добавляю 🙂"}

    task = storage.add_task(text)
    return {"text": f"Добавила задачу #{task['id']}:\n{task['text']}"}


def handle_command(text: str):
    cmd, *rest = text.split(maxsplit=1)
    arg = rest[0] if rest else ""

    if cmd == "/start":
        return {
            "text": (
                "Привет! Я твой личный планировщик.\n\n"
                "• Напиши сообщение — добавлю в инбокс.\n"
                "• /inbox — показать задачи.\n"
                "• Теперь задачи можно завершать кнопкой 'Готово'."
            )
        }

    if cmd == "/help":
        return {
            "text": (
                "Команды:\n"
                "/inbox — показать задачи\n"
                "/add текст — добавить задачу\n"
                "или просто напиши текст — я добавлю задачу в инбокс."
            )
        }

    if cmd == "/add":
        if not arg:
            return {"text": "Напиши так: /add купить молоко"}
        task = storage.add_task(arg)
        return {"text": f"Добавила задачу #{task['id']}:\n{task['text']}"}

    if cmd == "/inbox":
        tasks = storage.list_active_tasks()
        if not tasks:
            return {"text": "В инбоксе пусто ✨"}

        items = []
        for t in tasks:
            items.append({
                "text": f"{t['id']}. {t['text']}",
                "buttons": [
                    {
                        "text": "✅ Готово",
                        "callback": f"done:{t['id']}"
                    }
                ]
            })

        return {"multiple": True, "items": items}

    return {"text": "Не знаю такую команду. Попробуй /help."}


def handle_callback(data: str):
    """Обработка нажатий кнопок."""
    if data.startswith("done:"):
        task_id = int(data.split(":")[1])
        ok, task = storage.complete_task_by_id(task_id)

        if ok:
            return f"Готово: {task['text']}"
        else:
            return "Не нашла задачу"

    return "Неизвестная кнопка"