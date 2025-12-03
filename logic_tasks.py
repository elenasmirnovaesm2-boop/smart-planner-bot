import re
import storage


# ---------- разбиение текста на задачи ----------

def split_into_items(text: str):
    """
    Правило:
    - если сообщение короткое и без явных признаков списка -> одна задача
    - если длинное и есть переносы строк или нумерация/буллеты -> несколько задач
    """
    text = (text or "").strip()
    if not text:
        return []

    # "короткое" сообщение (условно)
    is_short = len(text) < 80

    has_newlines = "\n" in text
    has_numbering = bool(re.search(r"\d+[.)]\s", text))
    has_bullets = bool(re.search(r"(^|\n)\s*[-•–]\s+\S+", text))

    # Если короткое и без признаков списка → одна задача
    if is_short and not (has_newlines or has_numbering or has_bullets):
        return [text]

    items = []

    # 1) если есть переносы строк — режем по строкам
    if has_newlines:
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue

            low = line.lower()
            if low.startswith("твой инбокс") or low.startswith("inbox"):
                continue

            # убираем начальные буллеты / номера
            line = re.sub(r"^\s*[-•–]\s*", "", line)
            line = re.sub(r"^\s*\d+[.)]\s*", "", line)

            if line:
                items.append(line)

    # 2) если нет переносов, но есть нумерация в одну строку
    elif has_numbering:
        # обрезаем всё до первой цифры, если там заголовок
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

    # 3) если длинное, без нумерации, но с буллетами
    elif has_bullets:
        parts = re.split(r"(?=(^|\n)\s*[-•–]\s+\S+)", text)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            part = re.sub(r"^\s*[-•–]\s*", "", part)
            if part:
                items.append(part)

    # если ничего не распознали как список — возвращаем как одну задачу
    if not items:
        return [text]

    return items


# ---------- входная точка ----------

def handle_update(text: str):
    text = (text or "").strip()

    if text.startswith("/"):
        return handle_command(text)

    return handle_plain_text(text)


# ---------- обычный текст → задачи ----------

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
                "Длинный список с переносами / 1. 2. 3. → несколько задач.\n\n"
                "• /inbox — показать задачи\n"
                "• /routines — рутины\n"
                "• /templates — шаблоны дня\n"
                "• /habits — привычки\n"
                "• /projects — проекты\n"
                "• /sos_list — аварийные чеклисты"
            )
        }

    if cmd == "/help":
        return {
            "text": (
                "Команды:\n"
                "/inbox — показать невыполненные задачи\n"
                "/add текст — добавить задачу или список задач\n\n"
                "/routines — список рутин\n"
                "/routine_add Название: шаг1; шаг2; шаг3\n"
                "/routine_show Название_или_ID\n\n"
                "/templates — шаблоны дня\n"
                "/template_add Название: блок1; блок2; блок3\n\n"
                "/habits — привычки\n"
                "/habit_add Название: расписание\n\n"
                "/projects — проекты\n"
                "/project_add Название\n"
                "/project_step_add ID: шаг\n\n"
                "/sos_list — аварийные чеклисты\n"
                "/sos_add Название: шаг1; шаг2; шаг3\n"
                "/sos Название_или_ID — показать чеклист"
            )
        }

    # ----- задачи -----

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

    if cmd == "/add":
        arg = arg.strip()
        if not arg:
            return {"text": "Напиши так: /add купить молоко\nили список задач."}
        items = split_into_items(arg)
        if not items:
            return {"text": "Не получилось распознать задачи."}
        if len(items) == 1:
            task = storage.add_task(items[0])
            return {"text": f"Добавила задачу #{task['id']}:\n{task['text']}"}
        created_lines = []
        for item in items:
            task = storage.add_task(item)
            created_lines.append(f"{task['id']}. {task['text']}")
        reply_text = "Добавила несколько задач:\n" + "\n".join(created_lines)
        return {"text": reply_text}

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

    return {"text": "Не знаю такую команду. Попробуй /help."}


# ---------- callback-кнопки (кнопка 'Готово' у задач) ----------

def handle_callback(data: str):
    if data.startswith("done:"):
        task_id = int(data.split(":", 1)[1])
        ok, task = storage.complete_task_by_id(task_id)
        if ok:
            return f"Готово: {task['text']}"
        return "Не нашла задачу"
    return "Неизвестная кнопка"