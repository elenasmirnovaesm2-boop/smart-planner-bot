import re
import storage


# ---------- вспомогательное разбиение текста на задачи ----------

def split_into_items(text: str):
    """
    Пытаемся разнести длинный текст на отдельные задачи.
    Поддерживаем:
    - строки через перевод строки
    - нумерованные списки вида '1. ...2. ...3. ...'
    """
    text = (text or "").strip()
    items = []

    # 1) если есть переносы строк — режем по строкам
    if "\n" in text:
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            low = line.lower()
            if low.startswith("твой инбокс") or low.startswith("inbox"):
                continue
            items.append(line)

    # 2) если переносов нет, но есть нумерация 1. 2. 3.
    else:
        m = re.search(r"\d+[.)]", text)
        if m:
            body = text[m.start():]
        else:
            return [text]

        parts = re.split(r"(?=\d+[.)])", body)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            part = re.sub(r"^\d+[.)]\s*", "", part)
            if part:
                items.append(part)

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

    if len(items) == 1:
        item = items[0]
        if not item:
            return {"text": "Пустую задачу не добавляю 🙂"}
        task = storage.add_task(item)
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
                "Базовые возможности:\n"
                "• Напиши текст или список — добавлю задачи в инбокс.\n"
                "• /inbox — показать задачи (с кнопками 'Готово').\n\n"
                "Слои:\n"
                "1. Рутины: /routines, /routine_add\n"
                "2. Шаблоны дня: /templates, /template_add\n"
                "3. Привычки/расписания: /habits, /habit_add\n"
                "4. Проекты: /projects, /project_add, /project_step_add\n"
                "5. Аварийные чеклисты: /sos_list, /sos_add"
            )
        }

    if cmd == "/help":
        return {
            "text": (
                "Команды:\n"
                "— Задачи —\n"
                "Просто напиши текст или список — добавлю в инбокс.\n"
                "/inbox — показать невыполненные задачи.\n\n"
                "— Рутины —\n"
                "/routines — список рутин\n"
                "/routine_add Название: шаг1; шаг2; шаг3\n"
                "/routine_show Название_или_ID\n\n"
                "— Шаблоны дня —\n"
                "/templates — список\n"
                "/template_add Название: блок1; блок2; блок3\n\n"
                "— Привычки/расписания —\n"
                "/habits — список\n"
                "/habit_add Название: расписание\n\n"
                "— Проекты —\n"
                "/projects — список\n"
                "/project_add Название\n"
                "/project_step_add ID_проекта: шаг\n\n"
                "— Аварийные чеклисты —\n"
                "/sos_list — список\n"
                "/sos_add Название: шаг1; шаг2; шаг3\n"
                "/sos Название_или_ID — показать чеклист"
            )
        }

    # ---------- задачи / inbox ----------

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
        if len(items) == 1:
            task = storage.add_task(items[0])
            return {"text": f"Добавила задачу #{task['id']}:\n{task['text']}"}
        created_lines = []
        for item in items:
            task = storage.add_task(item)
            created_lines.append(f"{task['id']}. {task['text']}")
        reply_text = "Добавила несколько задач:\n" + "\n".join(created_lines)
        return {"text": reply_text}

    # ---------- рутины ----------

    if cmd == "/routines":
        routines = storage.list_routines()
        if not routines:
            return {"text": "Рутин пока нет. Добавь так:\n/routine_add Утро: вода; умыться; зарядка"}
        lines = [f"{r['id']}. {r['name']}" for r in routines]
        return {"text": "Рутины:\n" + "\n".join(lines)}

    if cmd == "/routine_add":
        # формат: /routine_add Название: шаг1; шаг2; шаг3
        if ":" not in arg:
            return {"text": "Формат: /routine_add Название: шаг1; шаг2; шаг3"}
        name_part, steps_part = arg.split(":", 1)
        name = name_part.strip()
        steps = [s.strip() for s in steps_part.split(";") if s.strip()]
        if not name or not steps:
            return {"text": "Нужны и название, и шаги. Пример:\n/routine_add Утро: вода; умыться; зарядка"}
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

    # ---------- шаблоны дня ----------

    if cmd == "/templates":
        templates = storage.list_templates()
        if not templates:
            return {"text": "Шаблонов дня пока нет. Добавь так:\n/template_add Будний: утро; работа; вечер"}
        lines = [f"{t['id']}. {t['name']}" for t in templates]
        return {"text": "Шаблоны дня:\n" + "\n".join(lines)}

    if cmd == "/template_add":
        # формат: /template_add Название: блок1; блок2; блок3
        if ":" not in arg:
            return {"text": "Формат: /template_add Название: блок1; блок2; блок3"}
        name_part, blocks_part = arg.split(":", 1)
        name = name_part.strip()
        blocks = [b.strip() for b in blocks_part.split(";") if b.strip()]
        if not name or not blocks:
            return {"text": "Нужны и название, и блоки."}
        template = storage.add_template(name, blocks)
        return {"text": f"Добавила шаблон дня #{template['id']}: {template['name']}"}

    # ---------- привычки / расписания ----------

    if cmd == "/habits":
        habits = storage.list_habits()
        if not habits:
            return {"text": "Привычек/расписаний пока нет. Добавь так:\n/habit_add Таблетки: каждый день в 22:00"}
        lines = [f"{h['id']}. {h['name']} — {h['schedule']}" for h in habits]
        return {"text": "Привычки / расписания:\n" + "\n".join(lines)}

    if cmd == "/habit_add":
        # формат: /habit_add Название: расписание
        if ":" not in arg:
            return {"text": "Формат: /habit_add Название: расписание"}
        name_part, sched_part = arg.split(":", 1)
        name = name_part.strip()
        schedule = sched_part.strip()
        if not name or not schedule:
            return {"text": "Нужны и название, и расписание."}
        habit = storage.add_habit(name, schedule)
        return {"text": f"Добавила привычку #{habit['id']}: {habit['name']} — {habit['schedule']}"}

    # ---------- проекты ----------

    if cmd == "/projects":
        projects = storage.list_projects()
        if not projects:
            return {"text": "Проектов пока нет. Добавь так:\n/project_add Поиск новой работы"}
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
        # формат: /project_step_add ID: шаг
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

    # ---------- аварийные чеклисты (SOS) ----------

    if cmd == "/sos_list":
        sos_list = storage.list_sos()
        if not sos_list:
            return {"text": "Аварийных чеклистов пока нет. Добавь так:\n/sos_add Стресс: шаг1; шаг2; шаг3"}
        lines = [f"{s['id']}. {s['name']}" for s in sos_list]
        return {"text": "Аварийные чеклисты:\n" + "\n".join(lines)}

    if cmd == "/sos_add":
        # формат: /sos_add Название: шаг1; шаг2; шаг3
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

    # неизвестная команда
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