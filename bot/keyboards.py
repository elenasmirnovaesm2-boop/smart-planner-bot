def inbox_inline_keyboard(tasks):
    task_buttons = []
    for t in tasks:
        btn = {
            "text": f"#{t['id']}",
            "callback_data": f"task_open:{t['id']}",
        }
        task_buttons.append([btn])

    common = [
        [
            {"text": "➕ Добавить", "callback_data": "inbox_add"},
            {"text": "🔄 Обновить", "callback_data": "inbox_refresh"},
        ],
        [{"text": "⬅️ В меню", "callback_data": "back_menu"}],
    ]
    return {"inline_keyboard": common + task_buttons}