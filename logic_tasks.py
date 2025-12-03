import re
import storage

# Тексты меню
MENU_INBOX = "Инбокс"
MENU_TODAY = "Сегодня"
MENU_ROUTINES = "Рутины"
MENU_TEMPLATES = "Шаблоны дня"
MENU_HABITS = "Привычки"
MENU_PROJECTS = "Проекты"
MENU_SOS = "SOS"


# ---------- разбиение текста на задачи ----------

def split_into_items(text: str):
    """
    Правило:
    - если сообщение короткое и без признаков списка -> одна задача
    - если длинное и есть переносы строк или нумерация/буллеты -> несколько задач
    """
    text = (text or "").strip()
    if not text:
        return []

    is_short = len(text) < 80

    has_newlines = "\n" in text
    has_numbering = bool(re.search(r"\d+[.)]\s", text))
    has_bullets = bool(re.search(r"(^|\n)\s*[-•–]\s+\S+", text))

    if is_short and not (has_newlines or has_numbering or has_bullets):
        return [text]

    items = []

    if has_newlines:
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            low = line.lower()
            if low.startswith("твой инбокс") or low.startswith("inbox"):
                continue
            line = re.sub(r"^\s*[-•–]\s*", "", line)
            line = re.sub(r"^\s*\d+[.)]\s*", "", line)
            if line:
                items.append(line)

    elif has_numbering:
        m = re.search(r"\d+[.)]\s", text)
        if m:
            body = text[m.start():]
        else:
            body = text
        parts = re.split(r"(?=\d+[.)]\s)", body)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            part = re.sub(r"^\d+[.)]\s*", "", part)
            if part:
                items.append(part)

    elif has_bullets:
        parts = re.split(r"(?=(^|\n)\s*[-•–]\s+\S+)", text)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            part = re.sub(r"^\s*[-•–]\s*", "", part)
            if part:
                items.append(part)

    if not items:
        return [text]

    return items


# ---------- входная точка ----------

def handle_update(text: str):
    text = (text or "").strip()

    # 1. Проверяем, нет ли "режима" (редактирование и т.п.)
    pending = storage.get_pending_action()
    if pending:
        ptype = pending.get("type")
        if ptype == "edit_task":
            task_id = pending.get("task_id")
            storage.set_pending_action(None)
            ok, task = storage.update_task_text(task_id, text)
            if ok:
                return {"text": f"Обновила задачу #{task['id']}:\n{task['text']}"}
            else:
                return {"text": "Не смогла обновить задачу — не нашла её."}

    # 2. Команды
    if text.startswith("/"):
        return handle_command(text)

    # 3. Меню (кнопки)
    if text in {
        MENU_INBOX,
        MENU_TODAY,
        MENU_ROUTINES,
        MENU_TEMPLATES,
        MENU_HABITS,
        MENU_PROJECTS,
        MENU_SOS,
    }:
        return handle_menu_action(text)

    # 4. Обычный текст → задачи
    return handle_plain_text(text)


# ---------- обработка обычного текста ----------

def handle_plain_text(text: str):
    items = split_into_items(text)

    if not items:
        return {"text": "Пустую задачу не добавляю 🙂"}

    if len(items) == 1:
        task = storage.add_task(items[0])
        return {"text": f"Добавила задачу #{task['id']}:\n{task['text']}"}

    created_lines = []
    for item in items:
        task = storage.add_task(item)
        created_lines.append(f"{task['id']}. {task['text']}")

    reply_text = "Добавила несколько задач:\n" + "\n".join(created_lines)
    return {"text": reply_text}


# ---------- меню ----------

def handle_menu_action(label: str):
    if label == MENU_INBOX:
        return handle_inbox()
    if label == MENU_TODAY:
        return handle_today_screen()
    if label == MENU_ROUTINES:
        return handle_command("/routines")
    if label == MENU_TEMPLATES:
        return handle_command("/templates")
    if label == MENU_HABITS:
        return handle_command("/habits")
    if label == MENU_PROJECTS:
        return handle_command("/projects")
    if label == MENU_SOS:
        return handle_command("/sos_list")
    return {"text": "Пока не знаю, что делать с этим пунктом меню."}


# ---------- экран "Сегодня" ----------

def handle_today_screen():
    today = storage.list_today()
    if not today:
        return {"text": "На сегодня ничего не запланировано.\nВыбери задачи в Инбоксе и добавь в 'Сегодня'."}
    lines = [f"{t['id']}. {t['text']}" for t in today]
    return {"text": "Список на сегодня:\n" + "\n".join(lines)}


# ---------- inbox ----------

def handle_inbox():
    tasks = storage.list_active_tasks()
    if not tasks:
        return {"text": "В инбоксе пусто ✨"}

    items = []
    for t in tasks:
        items.append({
            "text": f"{t['id']}. {t['text']}",
            "buttons": [
                {"text": "✅ Готово", "callback": f"done:{t['id']}"},
                {"text": "✏ Редактировать", "callback": f"edit:{t['id']}"},
                {"text": "🗑 Удалить", "callback": f"del:{t['id']}"},
                {"text": "⭐ Сегодня", "callback": f"today:{t['id']}"},
                {"text": "➡ В проект", "callback": f"proj:{t['id']}"},
            ],
        })

    return {"multiple": True, "items": items}


# ---------- команды ----------

def handle_command(text: str):
    cmd, *rest = text.split(maxsplit=1)
    arg = rest[0] if rest else ""
    cmd = cmd.lower()

    if cmd == "/start":
        return {
            "text": (
                "Привет! Я твой личный планировщик.\n\n"
                "Короткое сообщение → одна задача.\n"
                "Длинный список (с переносами, 1. 2. 3., -) → несколько задач.\n\n"
                "Снизу есть меню:\n"
                "• Инбокс — входящие задачи\n"
                "• Сегодня — план на день\n"
                "• Рутины, Шаблоны дня, Привычки, Проекты, SOS\n\n"
                "Также доступны команды /help, /inbox и т.п., но можно пользоваться только кнопками."
            )
        }

    if cmd == "/help":
        return {
            "text": (
                "Основное управление — через меню (кнопки внизу).\n\n"
                "Команды (если захочешь):\n"
                "/inbox — показать невыполненные задачи\n"
                "/add текст — добавить задачу или список задач\n"
                "/routines — рутины\n"
                "/templates — шаблоны дня\n"
                "/habits — привычки\n"
                "/projects — проекты\n"
                "/sos_list — аварийные чеклисты"
            )
        }

    if cmd == "/inbox":
        return handle_inbox()

    if cmd == "/add":
        arg = arg.strip()
        if not arg:
            return {"text": "Напиши так: /add купить молоко\nили список задач."}
        return handle_plain_text(arg)

    # ----- рутины -----

    if cmd == "/routines":
        routines = storage.list_routines()
        if not routines:
            return {"text": "Рутин пока нет."}
        lines = [f"{r['id']}. {r['name']}" for r in routines]
        return {"text": "Рутины:\n" + "\n".join(lines)}

    if cmd == "/routine_add":
        if ":" not in arg:
            return {"text": "Формат: /routine_add Название: шаг1; шаг2; шаг3"}
        name_part, steps_part = arg.split(":", 1)
        name = name_part.strip()
        steps = [s.strip() for s in steps_part.split(";") if s.strip()]
        if not name or not steps:
            return {"text": "Нужны и название, и шаги."}
        routine = storage.add_routine(name, steps)
        return {"text": f"Добавила рутину #{routine['id']}: {routine['name']}"}

    if cmd == "/routine_show":
        key = arg.strip()
        if not key:
            return {"text": "Напиши: /routine_show Название_или_ID"}
        r = storage.get_routine_by_name_or_id(key)
        if not r:
            return {"text": "Не нашла такую рутину."}
        lines = [f"{i+1}. {s}" for i, s in enumerate(r["steps"])]
        return {"text": f"Рутина {r['name']}:\n" + "\n".join(lines)}

    # ----- шаблоны дня -----

    if cmd == "/templates":
        templates = storage.list_templates()
        if not templates:
            return {"text": "Шаблонов дня пока нет."}
        lines = [f"{t['id']}. {t['name']}" for t in templates]
        return {"text": "Шаблоны дня:\n" + "\n".join(lines)}

    if cmd == "/template_add":
        if ":" not in arg:
            return {"text": "Формат: /template_add Название: блок1; блок2; блок3"}
        name_part, blocks_part = arg.split(":", 1)
        name = name_part.strip()
        blocks = [b.strip() for b in blocks_part.split(";") if b.strip()]
        if not name or not blocks:
            return {"text": "Нужны и название, и блоки."}
        template = storage.add_template(name, blocks)
        return {"text": f"Добавила шаблон дня #{template['id']}: {template['name']}"}

    # ----- привычки -----

    if cmd == "/habits":
        habits = storage.list_habits()
        if not habits:
            return {"text": "Привычек пока нет."}
        lines = [f"{h['id']}. {h['name']} — {h['schedule']}" for h in habits]
        return {"text": "Привычки:\n" + "\n".join(lines)}

    if cmd == "/habit_add":
        if ":" not in arg:
            return {"text": "Формат: /habit_add Название: расписание"}
        name_part, sched_part = arg.split(":", 1)
        name = name_part.strip()
        schedule = sched_part.strip()
        if not name or not schedule:
            return {"text": "Нужны и название, и расписание."}
        habit = storage.add_habit(name, schedule)
        return {"text": f"Добавила привычку #{habit['id']}: {habit['name']} — {habit['schedule']}"}

    # ----- проекты -----

    if cmd == "/projects":
        projects = storage.list_projects()
        if not projects:
            return {"text": "Проектов пока нет."}
        lines = []
        for p in projects:
            steps = p.get("steps", [])
            done = sum(1 for s in steps if s.get("done"))
            total = len(steps)
            lines.append(f"{p['id']}. {p['name']} ({done}/{total})")
        return {"text": "Проекты:\n" + "\n".join(lines)}

    if cmd == "/project_add":
        name = arg.strip()
        if not name:
            return {"text": "Формат: /project_add Название проекта"}
        p = storage.add_project(name)
        return {"text": f"Добавила проект #{p['id']}: {p['name']}"}

    if cmd == "/project_step_add":
        if ":" not in arg:
            return {"text": "Формат: /project_step_add ID: текст шага"}
        left, right = arg.split(":", 1)
        pid_str = left.strip()
        step_text = right.strip()
        if not pid_str.isdigit() or not step_text:
            return {"text": "Нужны ID проекта и текст шага."}
        pid = int(pid_str)
        p, step = storage.add_project_step(pid, step_text)
        if not p:
            return {"text": "Не нашла проект с таким ID."}
        return {"text": f"В проект '{p['name']}' добавлен шаг #{step['id']}:\n{step['text']}"}

    # ----- SOS -----

    if cmd == "/sos_list":
        sos_list = storage.list_sos()
        if not sos_list:
            return {"text": "Аварийных чеклистов пока нет."}
        lines = [f"{s['id']}. {s['name']}" for s in sos_list]
        return {"text": "Аварийные чеклисты:\n" + "\n".join(lines)}

    if cmd == "/sos_add":
        if ":" not in arg:
            return {"text": "Формат: /sos_add Название: шаг1; шаг2; шаг3"}
        name_part, steps_part = arg.split(":", 1)
        name = name_part.strip()
        steps = [s.strip() for s in steps_part.split(";") if s.strip()]
        if not name or not steps:
            return {"text": "Нужны и название, и шаги."}
        sos = storage.add_sos(name, steps)
        return {"text": f"Добавила аварийный чеклист #{sos['id']}: {sos['name']}"}

    if cmd == "/sos":
        key = arg.strip()
        if not key:
            return {"text": "Напиши: /sos Название_или_ID"}
        sos = storage.get_sos_by_name_or_id(key)
        if not sos:
            return {"text": "Не нашла такой чеклист."}
        lines = [f"{i+1}. {s}" for i, s in enumerate(sos["steps"])]
        return {"text": f"Чеклист '{sos['name']}':\n" + "\n".join(lines)}

    return {"text": "Не знаю такую команду. Попробуй /help или используй меню."}


# ---------- callback-кнопки ----------

def handle_callback(data: str):
    # done:id, edit:id, del:id, today:id, proj:id
    if data.startswith("done:"):
        task_id = int(data.split(":", 1)[1])
        ok, task = storage.complete_task_by_id(task_id)
        if ok:
            return f"Готово: {task['text']}"
        return "Не нашла задачу"

    if data.startswith("del:"):
        task_id = int(data.split(":", 1)[1])
        ok = storage.delete_task_by_id(task_id)
        if ok:
            return "Задачу удаляла."
        return "Не нашла задачу для удаления"

    if data.startswith("edit:"):
        task_id = int(data.split(":", 1)[1])
        task = storage.get_task_by_id(task_id)
        if not task:
            return "Не нашла задачу для редактирования."
        storage.set_pending_action({"type": "edit_task", "task_id": task_id})
        return f"Пришли новый текст для задачи:\n{task['text']}"

    if data.startswith("today:"):
        task_id = int(data.split(":", 1)[1])
        item = storage.add_today_from_task(task_id)
        if item:
            return f"Добавила в 'Сегодня': {item['text']}"
        return "Не получилось добавить в 'Сегодня' — не нашла задачу."

    if data.startswith("proj:"):
        task_id = int(data.split(":", 1)[1])
        task = storage.get_task_by_id(task_id)
        if not task:
            return "Не нашла задачу для перевода в проект."
        # Простой вариант: создаём отдельный проект с названием задачи
        p = storage.add_project(task["text"])
        return f"Создала проект из задачи:\n{p['name']}"

    return "Неизвестная кнопка"