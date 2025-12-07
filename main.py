import telebot
from storage import tasks_by_user, save_data, load_data
# import keyboards  # (клавиатура меню удалена, более не используется)

TOKEN = "YOUR_BOT_TOKEN_HERE"
bot = telebot.TeleBot(TOKEN)

# Глобальные структуры для контекста и истории действий (для undo)
context_map = {}  # {(chat_id, message_id): (section, parent_index)}
undo_stack = {}   # {chat_id: [actions...]}

# Список допустимых разделов для /open и назначения перемещения
SECTIONS = {"inbox", "today", "routines", "templates", "projects", "habits", "sos"}

def get_user_data(chat_id):
    """Получить (или инициализировать) хранилище задач для пользователя."""
    if chat_id not in tasks_by_user:
        tasks_by_user[chat_id] = load_data(chat_id)  # загрузить из файла или создать новые
        if tasks_by_user[chat_id] is None:
            # Инициализация с шаблонами по умолчанию, если нет сохраненных данных
            tasks_by_user[chat_id] = {
                "inbox": [],
                "today": [],
                "routines": [ {"title": "Пример утренней рутины", "children": [
                                    {"title": "Проснуться", "children": []},
                                    {"title": "Сделать зарядку", "children": []},
                                    {"title": "Позавтракать", "children": []}
                               ]} ],
                "templates": [ {"title": "Пример плана дня", "children": [
                                    {"title": "Утренние задачи", "children": []},
                                    {"title": "Дневные задачи", "children": []},
                                    {"title": "Вечерние задачи", "children": []}
                               ]},
                               {"title": "Шаблон SOS", "children": [
                                    {"title": "Пауза и глубокий вдох", "children": []},
                                    {"title": "Определить приоритетную задачу", "children": []},
                                    {"title": "Начать с малого шага", "children": []}
                               ]} ],
                "projects": [],
                "habits": [],
                "sos": []
            }
    return tasks_by_user[chat_id]

def save_user_data(chat_id):
    """Сохранить данные пользователя."""
    if chat_id in tasks_by_user:
        save_data(chat_id, tasks_by_user[chat_id])

def format_list(section, item_list):
    """Вернуть текстовое представление списка задач для раздела или подзадач."""
    if not item_list:
        return "Нет задач."
    lines = []
    for idx, item in enumerate(item_list, start=1):
        line = f"{idx}. {item['title']}"
        if item['children']:
            # Отметим наличие подзадач (количество)
            line += f" ({len(item['children'])} подзадач)"
        lines.append(line)
    return "\n".join(lines)

def send_section(chat_id, section, parent_index=None):
    """Отправить сообщение со списком задач раздела или вложенных задач элемента."""
    user_data = get_user_data(chat_id)
    if parent_index is None:
        # верхний уровень раздела
        header = section.capitalize() if section.lower() != "sos" else "SOS"
        header += ":"
        item_list = user_data.get(section, [])
        text = header + "\n" + (format_list(section, item_list) if item_list else "Нет задач.")
    else:
        # вложенные задачи элемента (например, задачи проекта или шаблона)
        parent_list = user_data.get(section, [])
        if parent_index < 0 or parent_index >= len(parent_list):
            bot.send_message(chat_id, "Элемент не найден.")
            return None
        parent_item = parent_list[parent_index]
        # Заголовок: название элемента (проекта/шаблона/рутины)
        title = parent_item["title"]
        # Добавим тип в заголовок для ясности (например, "Проект: ...")
        if section == "projects":
            header = f"Проект: {title}:"
        elif section == "templates":
            header = f"Шаблон: {title}:"
        elif section == "routines":
            header = f"Рутина: {title}:"
        else:
            header = title + ":"
        item_list = parent_item["children"]
        text = header + "\n" + (format_list(section, item_list) if item_list else "Нет задач.")
    # Отправляем сообщение со списком
    sent = bot.send_message(chat_id, text)
    # Сохраняем контекст для возможности ответов на это сообщение
    context_map[(chat_id, sent.message_id)] = (section, parent_index)
    return sent

def push_undo(chat_id, action):
    """Добавить действие в стек для undo (ограничение 5 записей)."""
    if chat_id not in undo_stack:
        undo_stack[chat_id] = []
    undo_stack[chat_id].append(action)
    # Ограничим размер стека последних действий
    if len(undo_stack[chat_id]) > 5:
        undo_stack[chat_id].pop(0)

@bot.message_handler(commands=['start'])
def start_handler(message):
    chat_id = message.chat.id
    # Инициализируем данные пользователя
    get_user_data(chat_id)
    # Приветственное сообщение
    bot.send_message(chat_id, 
        "Привет! Я Smart Planner Bot – помогу спланировать дела.\n"
        "Для справки по командам введите /help")
    # Сохраняем данные (например, создаем файл пользователя)
    save_user_data(chat_id)

@bot.message_handler(commands=['help'])
def help_handler(message):
    chat_id = message.chat.id
    help_text = (
        "**Доступные команды:**\n"
        "- `/open <раздел>` – открыть список задач раздела (например, `/open inbox`, `/open today`). "
        "Доступные разделы: inbox (входящие), today (сегодня), routines (рутины), templates (шаблоны), "
        "projects (проекты), habits (привычки), sos (SOS).\n"
        "- `/open <номер>` – открыть вложенные элементы задачи или проекта. Эту команду нужно отправлять ответом на сообщение со списком, содержащим нумерованные элементы. Например, ответив на список проектов командой `/open 2`, вы откроете задачи проекта №2.\n"
        "- `/add <текст>` – добавить новую задачу в текущий раздел. Команду следует отправлять ответом на сообщение списка раздела. Если отправить `/add` без ответа (просто сообщением), задача добавится в **Inbox**.\n"
        "- `/edit <N> <новый текст>` – изменить текст задачи под номером N в текущем списке (где N – число из списка задач, на сообщение которого вы отвечаете).\n"
        "- `/mv <N или N-M> to <раздел>` – переместить задачу(и) в другой раздел. Укажите номер или диапазон номеров через дефис. Например, `/mv 2-4 to today` переместит задачи с 2 по 4 в раздел **Today**. Команду нужно отправлять ответом на сообщение со списком (откуда переносим).\n"
        "- `/del <N или N-M>` – удалить задачу(и) из текущего списка. Можно указать один номер либо диапазон через дефис (например, `3-5`). Команда отправляется ответом на сообщение со списком. Удаленные задачи можно восстановить командой `/undo`.\n"
        "- `/undo` – отменить последнее действие (доступно до 5 последних изменений). Отменяет добавление, редактирование, перемещение или удаление задачи."
    )
    bot.send_message(chat_id, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['open'])
def open_handler(message):
    chat_id = message.chat.id
    user_data = get_user_data(chat_id)
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.send_message(chat_id, "Укажите, что открыть: раздел (inbox/today/...) или номер элемента.")
        return
    query = args[1].strip()
    # Если аргумент - число, пытаемся открыть вложенный список по номеру
    if query.isdigit():
        # Должно быть ответом на сообщение списка
        if not message.reply_to_message:
            bot.send_message(chat_id, "Для открытия элемента отправьте команду в ответ на сообщение со списком.")
            return
        # Получаем контекст из ответного сообщения
        ctx = context_map.get((chat_id, message.reply_to_message.message_id))
        if not ctx:
            bot.send_message(chat_id, "Контекст списка не найден.")
            return
        section, parent_index = ctx
        index = int(query) - 1  # перевод в 0-индекс
        # Открываем вложенные задачи (второй уровень)
        if parent_index is None:
            # Открываем элемент верхнего уровня раздела
            send_section(chat_id, section, parent_index=index)
        else:
            # Возможно, поддержка более глубокого уровня (не предполагается, но на всякий случай)
            send_section(chat_id, section, parent_index=parent_index)  # без изменений, т.к. глубже одного уровня не реализовано
    else:
        # Аргумент не число: вероятно, название раздела
        sec = query.lower()
        if sec in SECTIONS:
            send_section(chat_id, sec, parent_index=None)
        else:
            bot.send_message(chat_id, f"Раздел *{query}* не найден. Используйте один из: " 
                                      "inbox, today, routines, templates, projects, habits, sos.", parse_mode="Markdown")

@bot.message_handler(commands=['add'])
def add_handler(message):
    chat_id = message.chat.id
    user_data = get_user_data(chat_id)
    # Извлекаем текст задачи
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        bot.send_message(chat_id, "После команды /add укажите текст задачи.")
        return
    task_text = parts[1].strip()
    # Определяем целевой список (раздел)
    if message.reply_to_message:
        ctx = context_map.get((chat_id, message.reply_to_message.message_id))
        if not ctx:
            # Если вдруг нет контекста
            bot.send_message(chat_id, "Не удалось определить раздел для добавления задачи.")
            return
        section, parent_index = ctx
    else:
        # Если команда без ответа – добавляем в Inbox
        section, parent_index = "inbox", None
    # Создаем новую задачу (элемент)
    new_item = {"title": task_text, "children": []}
    if parent_index is None:
        # Добавляем на верхний уровень выбранного раздела
        user_data[section].append(new_item)
    else:
        # Добавляем как подзадачу к выбранному элементу (проекту/шаблону/рутине)
        parent_list = user_data[section]
        if parent_index < 0 or parent_index >= len(parent_list):
            bot.send_message(chat_id, "Не найден элемент для добавления подзадачи.")
            return
        parent_item = parent_list[parent_index]
        parent_item["children"].append(new_item)
    # Сохраняем действие для undo
    undo_action = {
        "type": "add",
        "section": section,
        "parent": parent_index,
        "item": new_item
    }
    push_undo(chat_id, undo_action)
    save_user_data(chat_id)
    # Отправляем подтверждение/обновленный список
    if message.reply_to_message:
        # Обновляем текущий список раздела
        send_section(chat_id, section, parent_index=parent_index)
    else:
        bot.send_message(chat_id, f"Задача добавлена в раздел *{section.capitalize()}*.", parse_mode="Markdown")

@bot.message_handler(commands=['edit'])
def edit_handler(message):
    chat_id = message.chat.id
    user_data = get_user_data(chat_id)
    if not message.reply_to_message:
        bot.send_message(chat_id, "Команду /edit нужно отправлять ответом на сообщение со списком задач.")
        return
    ctx = context_map.get((chat_id, message.reply_to_message.message_id))
    if not ctx:
        bot.send_message(chat_id, "Контекст списка не найден.")
        return
    section, parent_index = ctx
    # Парсим команду: ожидается "/edit N новый текст"
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        bot.send_message(chat_id, "Используйте формат: /edit <номер> <новый текст задачи> (команду отправлять ответом на список).")
        return
    try:
        idx = int(args[1]) - 1
    except ValueError:
        bot.send_message(chat_id, "Номер задачи должен быть числом.")
        return
    new_text = args[2].strip()
    if parent_index is None:
        item_list = user_data.get(section, [])
    else:
        parent_item = user_data.get(section, [])[parent_index]
        item_list = parent_item["children"]
    if idx < 0 or idx >= len(item_list):
        bot.send_message(chat_id, "Задача с таким номером не найдена.")
        return
    item = item_list[idx]
    old_text = item["title"]
    item["title"] = new_text
    # Сохраняем действие для undo
    undo_action = {
        "type": "edit",
        "section": section,
        "parent": parent_index,
        "item": item,
        "old_text": old_text
    }
    push_undo(chat_id, undo_action)
    save_user_data(chat_id)
    # Отправляем обновленный список
    send_section(chat_id, section, parent_index=parent_index)

@bot.message_handler(commands=['mv'])
def mv_handler(message):
    chat_id = message.chat.id
    user_data = get_user_data(chat_id)
    if not message.reply_to_message:
        bot.send_message(chat_id, "Команду /mv нужно отправлять ответом на сообщение со списком задач, откуда переносить.")
        return
    ctx = context_map.get((chat_id, message.reply_to_message.message_id))
    if not ctx:
        bot.send_message(chat_id, "Контекст списка не найден.")
        return
    section, parent_index = ctx
    # Парсим команду: ожидается "/mv 1-3 to section"
    args = message.text.split()
    if len(args) < 3:
        bot.send_message(chat_id, "Используйте формат: /mv <N или N-M> to <раздел>.")
        return
    # Объединяем все аргументы кроме команды и 'to'
    try:
        to_index = args.index("to")
    except ValueError:
        to_index = args.index("to".capitalize()) if "to".capitalize() in args else -1
    if to_index == -1:
        bot.send_message(chat_id, "Укажите раздел назначения после 'to'.")
        return
    selection_str = " ".join(args[1:to_index])
    dest_section = args[to_index+1].lower() if to_index+1 < len(args) else ""
    if dest_section not in SECTIONS:
        bot.send_message(chat_id, f"Недопустимый раздел назначения: {dest_section}.")
        return
    # Получаем список исходных задач
    if parent_index is None:
        src_list = user_data.get(section, [])
    else:
        src_list = user_data.get(section, [])[parent_index]["children"]
    # Разбираем диапазоны и номера
    # Поддерживаем синтаксис: "N", "N-M", "N, M, K-L"
    selection_str = selection_str.replace(",", " ")
    parts = selection_str.split()
    indices = []
    for part in parts:
        if "-" in part:
            try:
                a, b = part.split("-")
                start = int(a)
                end = int(b)
            except:
                bot.send_message(chat_id, f"Некорректный диапазон: {part}")
                return
            if start > end:
                start, end = end, start
            indices.extend(list(range(start, end+1)))
        else:
            try:
                n = int(part)
                indices.append(n)
            except:
                bot.send_message(chat_id, f"Некорректный номер задачи: {part}")
                return
    # Убираем дубликаты и сортируем
    indices = sorted(set(indices))
    if not indices:
        bot.send_message(chat_id, "Не указаны корректные номера задач для перемещения.")
        return
    # Переводим в 0-based индексы и проверяем границы
    indices0 = [i-1 for i in indices]
    max_index = len(src_list) - 1
    for i0 in indices0:
        if i0 < 0 or i0 > max_index:
            bot.send_message(chat_id, f"Задачи с номером {i0+1} не существует.")
            return
    # Сохраняем перемещаемые элементы и их исходные позиции
    moved_items = [src_list[i] for i in indices0]
    orig_positions = indices0[:]  # копия списка
    # Удаляем элементы из исходного списка (с конца, чтобы индексы не сдвинулись до удаления)
    for i in sorted(indices0, reverse=True):
        src_list.pop(i)
    # Добавляем элементы в целевой раздел (в конец списка целевого раздела)
    # Если переносим подзадачи из проекта/шаблона, они станут обычными задачами в новом разделе
    dest_list = user_data.get(dest_section)
    if dest_list is None:
        user_data[dest_section] = []
        dest_list = user_data[dest_section]
    for item in moved_items:
        dest_list.append(item)
    # Сохраняем действие для undo
    undo_action = {
        "type": "mv",
        "section": section,
        "parent": parent_index,
        "dest_section": dest_section,
        "dest_parent": None,  # (перенос всегда на верхний уровень другого раздела)
        "items": moved_items,
        "orig_positions": orig_positions
    }
    push_undo(chat_id, undo_action)
    save_user_data(chat_id)
    # Отправляем сообщение об успешном переносе и обновляем исходный список
    bot.send_message(chat_id, f"Перенесено задач: {len(moved_items)} -> раздел *{dest_section.capitalize()}*.", parse_mode="Markdown")
    send_section(chat_id, section, parent_index=parent_index)

@bot.message_handler(commands=['del'])
def del_handler(message):
    chat_id = message.chat.id
    user_data = get_user_data(chat_id)
    if not message.reply_to_message:
        bot.send_message(chat_id, "Команду /del нужно отправлять ответом на сообщение со списком задач.")
        return
    ctx = context_map.get((chat_id, message.reply_to_message.message_id))
    if not ctx:
        bot.send_message(chat_id, "Контекст списка не найден.")
        return
    section, parent_index = ctx
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.send_message(chat_id, "Укажите номер или диапазон задач для удаления.")
        return
    selection_str = args[1]
    # Получаем целевой список
    if parent_index is None:
        target_list = user_data.get(section, [])
    else:
        target_list = user_data.get(section, [])[parent_index]["children"]
    # Парсим диапазоны/номера (логика аналогично mv)
    selection_str = selection_str.replace(",", " ")
    parts = selection_str.split()
    indices = []
    for part in parts:
        if "-" in part:
            try:
                a, b = part.split("-")
                start = int(a)
                end = int(b)
            except:
                bot.send_message(chat_id, f"Некорректный диапазон: {part}")
                return
            if start > end:
                start, end = end, start
            indices.extend(list(range(start, end+1)))
        else:
            try:
                n = int(part)
                indices.append(n)
            except:
                bot.send_message(chat_id, f"Некорректный номер задачи: {part}")
                return
    indices = sorted(set(indices))
    if not indices:
        bot.send_message(chat_id, "Не указаны корректные номера задач.")
        return
    indices0 = [i-1 for i in indices]
    max_index = len(target_list) - 1
    for i0 in indices0:
        if i0 < 0 or i0 > max_index:
            bot.send_message(chat_id, f"Задачи с номером {i0+1} не существует.")
            return
    # Сохраняем удаляемые задачи и их позиции
    deleted_items = []
    deleted_positions = []
    for i in sorted(indices0, reverse=True):
        deleted_items.insert(0, target_list.pop(i))  # вставляем в начало, чтобы итоговый порядок соответствовал исходному
        deleted_positions.insert(0, i)
    # Логика: deleted_items теперь в порядке возрастания оригинальных индексов
    undo_action = {
        "type": "del",
        "section": section,
        "parent": parent_index,
        "items": deleted_items,
        "positions": deleted_positions
    }
    push_undo(chat_id, undo_action)
    save_user_data(chat_id)
    bot.send_message(chat_id, f"Удалено задач: {len(deleted_items)}.")
    # Обновляем список на экране
    send_section(chat_id, section, parent_index=parent_index)

@bot.message_handler(commands=['undo'])
def undo_handler(message):
    chat_id = message.chat.id
    if chat_id not in undo_stack or not undo_stack[chat_id]:
        bot.send_message(chat_id, "Нет действий для отмены.")
        return
    user_data = get_user_data(chat_id)
    action = undo_stack[chat_id].pop()  # получаем последнее действие
    typ = action["type"]
    if typ == "add":
        sec = action["section"]
        par = action["parent"]
        item = action["item"]
        # Найдем и удалим добавленный элемент из соответствующего списка
        if par is None:
            # верхний уровень
            if item in user_data[sec]:
                user_data[sec].remove(item)
        else:
            parent_item = user_data.get(sec, [])[par]
            if item in parent_item["children"]:
                parent_item["children"].remove(item)
        bot.send_message(chat_id, "Добавление задачи отменено.")
        # Обновим список, если он открыт
        send_section(chat_id, sec, parent_index=par)
    elif typ == "edit":
        sec = action["section"]
        par = action["parent"]
        item = action["item"]
        old_text = action["old_text"]
        # Вернем старый текст
        item["title"] = old_text
        bot.send_message(chat_id, "Изменение задачи отменено.")
        # Обновим список, чтобы отобразить старый текст
        send_section(chat_id, sec, parent_index=par)
    elif typ == "mv":
        sec = action["section"]
        par = action["parent"]
        dest_sec = action["dest_section"]
        items = action["items"]
        orig_positions = action["orig_positions"]
        # Удаляем элементы из раздела-назначения
        dest_list = user_data.get(dest_sec, [])
        for it in items:
            if it in dest_list:
                dest_list.remove(it)
        # Вставляем элементы обратно в исходный список на исходные позиции
        target_list = user_data.get(sec, [])
        if par is None:
            # верхний уровень
            for pos, it in sorted(zip(orig_positions, items), key=lambda x: x[0]):
                if pos <= len(target_list):
                    target_list.insert(pos, it)
                else:
                    # если позиция вне текущих границ (на случай), добавим в конец
                    target_list.append(it)
        else:
            parent_item = target_list[par]
            child_list = parent_item["children"]
            for pos, it in sorted(zip(orig_positions, items), key=lambda x: x[0]):
                if pos <= len(child_list):
                    child_list.insert(pos, it)
                else:
                    child_list.append(it)
        bot.send_message(chat_id, "Перемещение задач отменено.")
        # Обновим исходный список (предполагаем, что именно он сейчас открыт у пользователя)
        send_section(chat_id, sec, parent_index=par)
    elif typ == "del":
        sec = action["section"]
        par = action["parent"]
        items = action["items"]
        positions = action["positions"]
        # Вставляем удаленные задачи обратно на их исходные позиции
        target_list = user_data.get(sec, [])
        if par is None:
            for pos, it in zip(positions, items):
                if pos <= len(target_list):
                    target_list.insert(pos, it)
                else:
                    target_list.append(it)
        else:
            parent_item = target_list[par]
            child_list = parent_item["children"]
            for pos, it in zip(positions, items):
                if pos <= len(child_list):
                    child_list.insert(pos, it)
                else:
                    child_list.append(it)
        bot.send_message(chat_id, "Удаление задач отменено.")
        send_section(chat_id, sec, parent_index=par)
    save_user_data(chat_id)

# Отключаем какую-либо клавиатуру меню по умолчанию (не используем custom keyboard)
# bot.set_my_commands([])  # Можно очистить список команд меню, если необходимо

print("Bot is polling...")
bot.polling(none_stop=True)