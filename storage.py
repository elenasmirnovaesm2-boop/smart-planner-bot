import json
import datetime
import os

import dropbox
from dropbox.exceptions import ApiError
from dropbox.files import WriteMode

# ---------- Dropbox настройки ----------

DROPBOX_TOKEN = os.environ.get("DROPBOX_TOKEN")
DROPBOX_ROOT_PATH = os.environ.get("DROPBOX_ROOT_PATH", "/smart-planner")

_dbx = None


def get_dropbox_client():
    global _dbx
    if _dbx is not None:
        return _dbx
    if not DROPBOX_TOKEN:
        raise RuntimeError("Не задан DROPBOX_TOKEN")
    _dbx = dropbox.Dropbox(DROPBOX_TOKEN)
    return _dbx


def _dropbox_path(filename: str) -> str:
    """
    Преобразуем имя файла в путь в Dropbox внутри корневой папки.
    Например: tasks.json -> /smart-planner/tasks.json
    """
    root = DROPBOX_ROOT_PATH.rstrip("/")
    return f"{root}/{filename}"


BASE_DIR = os.path.dirname(__file__)

TASKS_FILE = os.path.join(BASE_DIR, "tasks.json")
ROUTINES_FILE = os.path.join(BASE_DIR, "routines.json")
TEMPLATES_FILE = os.path.join(BASE_DIR, "templates.json")
HABITS_FILE = os.path.join(BASE_DIR, "habits.json")
PROJECTS_FILE = os.path.join(BASE_DIR, "projects.json")
SOS_FILE = os.path.join(BASE_DIR, "sos.json")
TODAY_FILE = os.path.join(BASE_DIR, "today.json")
TOMORROW_FILE = os.path.join(BASE_DIR, "tomorrow.json")  # ← добавили файл для «Завтра»
STATE_FILE = os.path.join(BASE_DIR, "state.json")

# ---------- первоначальные шаблоны ----------

DEFAULT_ROUTINES = [
    {
        "id": 1,
        "name": "Утро (быстрое)",
        "steps": [
            "Выпить стакан воды",
            "Умыться / гигиена",
            "Застелить кровать",
            "Лёгкая зарядка 3–5 минут",
            "Проверить таблетки / витамины",
            "Одеться и открыть окно / балкон",
        ],
    },
    {
        "id": 2,
        "name": "Вечер (спокойный)",
        "steps": [
            "Убрать рабочее место (минимальный порядок)",
            "Подготовить одежду на завтра",
            "Проверить, приняты ли таблетки",
            "Лёгкое растяжение или дыхание",
            "Отключить экраны за 30 минут до сна",
            "Записать 1–3 мысли / итога дня",
        ],
    },
    {
        "id": 3,
        "name": "Мини-уборка квартиры",
        "steps": [
            "Собрать мусор по комнатам",
            "Освободить столы и поверхности от лишнего",
            "Сложить одежду: чистое / в стирку / на место",
            "Протереть кухонную поверхность",
            "Запустить / разобрать посудомойку или помыть посуду",
        ],
    },
    {
        "id": 4,
        "name": "Забота о себе",
        "steps": [
            "Проверить уровень усталости (1–10)",
            "Сделать что-то приятное и очень простое (чай, плед, свеча)",
            "Короткое упражнение для тела (шея, спина, плечи)",
            "Спросить себя: «Что мне сейчас нужно больше всего?»",
        ],
    },
]

DEFAULT_TEMPLATES = [
    {
        "id": 1,
        "name": "Будний день (фокус)",
        "blocks": [
            "06:30–07:30 Утро: вода, гигиена, лёгкое движение, завтрак",
            "07:30–09:00 Дорога / сборы / мягкий старт",
            "09:00–12:00 Фокусная работа над важными задачами",
            "12:00–13:00 Обед + короткая прогулка",
            "13:00–16:00 Рабочие задачи средней сложности",
            "16:00–17:00 Разбор почты / мелкие дела",
            "17:00–19:00 Свободное время / дела вне дома",
            "20:00–22:00 Спокойный вечер, ритуалы перед сном",
        ],
    },
    {
        "id": 2,
        "name": "Выходной (восстановление)",
        "blocks": [
            "09:00–10:00 Спокойное утро: вода, завтрак без спешки",
            "10:00–12:00 Прогулка / лёгкая активность",
            "12:00–14:00 Хобби или приятные дела",
            "14:00–16:00 Мини-уборка / организация пространства",
            "16:00–18:00 Встречи / общение / онлайн-дела",
            "18:00–22:00 Спокойный вечер, подготовка к следующей неделе",
        ],
    },
    {
        "id": 3,
        "name": "День минимума (когда нет сил)",
        "blocks": [
            "Утро: базовая гигиена + вода + одно маленькое приятное действие",
            "1–2 короткие задачи по 10–15 минут (самое необходимое)",
            "Обязательные вещи: таблетки, документы, письма (по минимуму)",
            "Остальное время — отдых, восстановление, мягкое движение",
            "Вечер: лёгкий ритуал перед сном без экрана",
        ],
    },
    {
        "id": 4,
        "name": "День фокуса на поиске работы",
        "blocks": [
            "Утро: рутина + короткое упражнение на энергию",
            "Блок: обновить резюме / портфолио",
            "Блок: поиск вакансий и отклики",
            "Блок: подготовка к собеседованию (вопросы, ответы)",
            "Мини-отдых: прогулка / музыка / растяжка",
            "Вечер: подведение итогов дня, план на завтра",
        ],
    },
]

DEFAULT_HABITS = [
    {
        "id": 1,
        "name": "Вода утром",
        "schedule": "Каждый день утром выпивать стакан воды",
    },
    {
        "id": 2,
        "name": "Короткая зарядка",
        "schedule": "Каждый день 3–5 минут простых упражнений",
    },
    {
        "id": 3,
        "name": "Английский",
        "schedule": "По будням 10–15 минут английского (чтение / видео)",
    },
    {
        "id": 4,
        "name": "Поиск работы",
        "schedule": "3 раза в неделю 30–60 минут на поиск вакансий / отклики",
    },
    {
        "id": 5,
        "name": "Запись мыслей",
        "schedule": "Каждый вечер 3–5 предложений: что было важным за день",
    },
]

DEFAULT_SOS = [
    {
        "id": 1,
        "name": "Сильные эмоции / перегруз",
        "steps": [
            "Стоп. Сделай 3 глубоких вдоха и выдоха, посчитай до 10.",
            "Поставь ноги на пол, почувствуй опору (земля / стул / спина).",
            "Назови вслух 5 предметов вокруг (что видишь).",
            "Спроси себя: «Без оценки, что сейчас происходит?»",
            "Запиши 2–3 предложения о ситуации, как наблюдатель.",
            "Сделай что-то мягкое: вода, тёплый чай, окно, пару шагов.",
        ],
    },
    {
        "id": 2,
        "name": "Стресс на работе / задачах",
        "steps": [
            "Отложи всё на 2 минуты. Вдох–выдох (4 счёта вдох, 6 счёта выдох).",
            "Запиши все задачи, которые крутятся в голове, как есть.",
            "Выдели 1–2 самые реальные задачи на ближайший час.",
            "Разбей выбранную задачу на самый маленький первый шаг.",
            "Сделай только первый шаг. Остальное пока не трогаем.",
            "После шага — короткий перерыв: вода, окно, пара движений.",
        ],
    },
    {
        "id": 3,
        "name": "Упадок сил",
        "steps": [
            "Оцени уровень энергии по шкале от 1 до 10.",
            "Если меньше 4: приоритет — восстановление.",
            "Сделай базовое: вода, перекус, душ или плед.",
            "Выбери одну маленькую задачу на 5–10 минут.",
            "После неё снова оцени состояние и реши, что дальше.",
        ],
    },
    {
        "id": 4,
        "name": "Бессонница / не могу заснуть",
        "steps": [
            "Не лежи в темноте больше 20–30 минут без сна: встань.",
            "Сделай что-то однообразное и спокойное: тёплый чай, тихое чтение.",
            "Убери яркий экран, уменьши свет.",
            "Дыхание: вдох на 4, выдох на 6, 10–15 раз.",
            "Запиши на бумагу мысли, которые крутятся, чтобы выгрузить голову.",
            "Вернись в кровать, когда появится лёгкая сонливость.",
        ],
    },
]

DEFAULT_PROJECTS = []


# ---------- общие утилиты (Dropbox JSON) ----------

def _load_json(path, default):
    """
    Читает JSON по имени файла из Dropbox (папка DROPBOX_ROOT_PATH).
    Если файла нет или ошибка — возвращает default.
    """
    filename = os.path.basename(path)
    dbx_path = _dropbox_path(filename)

    try:
        client = get_dropbox_client()
        _, res = client.files_download(dbx_path)
        raw = res.content.decode("utf-8")
        return json.loads(raw)
    except ApiError as e:
        # файл ещё не существует
        print(f"Dropbox: файл {dbx_path} не найден или ошибка API: {e}")
        return default
    except Exception as e:
        print(f"Dropbox: ошибка чтения {dbx_path}: {e}")
        return default


def _save_json(path, data):
    """
    Сохраняет JSON-файл с указанным именем в Dropbox.
    Если файл уже есть — перезаписывает.
    """
    filename = os.path.basename(path)
    dbx_path = _dropbox_path(filename)
    client = get_dropbox_client()

    content = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    try:
        client.files_upload(
            content,
            dbx_path,
            mode=WriteMode.overwrite,
        )
    except Exception as e:
        print(f"Dropbox: ошибка записи {dbx_path}: {e}")


# ---------- задачи (inbox) ----------

def load_tasks():
    return _load_json(TASKS_FILE, [])


def save_tasks(tasks):
    _save_json(TASKS_FILE, tasks)


def add_task(text: str):
    tasks = load_tasks()
    new_id = max((t.get("id", 0) for t in tasks), default=0) + 1
    task = {
        "id": new_id,
        "text": text,
        "done": False,
        "created_at": datetime.datetime.utcnow().isoformat(),
        "source": "inbox",
    }
    tasks.append(task)
    save_tasks(tasks)
    return task


def list_active_tasks():
    tasks = load_tasks()
    return [t for t in tasks if not t.get("done")]


def complete_task_by_id(task_id: int):
    tasks = load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            t["done"] = True
            save_tasks(tasks)
            return True, t
    return False, None


def delete_task_by_id(task_id: int):
    tasks = load_tasks()
    new_tasks = [t for t in tasks if t["id"] != task_id]
    if len(new_tasks) == len(tasks):
        return False
    save_tasks(new_tasks)
    return True


def update_task_text(task_id: int, new_text: str):
    tasks = load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            t["text"] = new_text
            save_tasks(tasks)
            return True, t
    return False, None


def get_task_by_id(task_id: int):
    tasks = load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            return t
    return None


# ---------- рутины ----------

def load_routines():
    routines = _load_json(ROUTINES_FILE, [])
    if not routines:
        routines = DEFAULT_ROUTINES
        _save_json(ROUTINES_FILE, routines)
    return routines


def save_routines(routines):
    _save_json(ROUTINES_FILE, routines)


def add_routine(name: str, steps):
    routines = load_routines()
    new_id = max((r.get("id", 0) for r in routines), default=0) + 1
    routine = {
        "id": new_id,
        "name": name,
        "steps": steps,
    }
    routines.append(routine)
    save_routines(routines)
    return routine


def list_routines():
    return load_routines()


def get_routine_by_name_or_id(key: str):
    routines = load_routines()
    if key.isdigit():
        rid = int(key)
        for r in routines:
            if r["id"] == rid:
                return r
    low = key.lower()
    for r in routines:
        if r["name"].lower() == low:
            return r
    return None


# ---------- шаблоны дня ----------

def load_templates():
    templates = _load_json(TEMPLATES_FILE, [])
    if not templates:
        templates = DEFAULT_TEMPLATES
        _save_json(TEMPLATES_FILE, templates)
    return templates


def save_templates(templates):
    _save_json(TEMPLATES_FILE, templates)


def add_template(name: str, blocks):
    templates = load_templates()
    new_id = max((t.get("id", 0) for t in templates), default=0) + 1
    template = {
        "id": new_id,
        "name": name,
        "blocks": blocks,
    }
    templates.append(template)
    save_templates(templates)
    return template


def list_templates():
    return load_templates()


def get_template_by_name_or_id(key: str):
    templates = load_templates()
    if key.isdigit():
        tid = int(key)
        for t in templates:
            if t["id"] == tid:
                return t
    low = key.lower()
    for t in templates:
        if t["name"].lower() == low:
            return t
    return None


# ---------- привычки ----------

def load_habits():
    habits = _load_json(HABITS_FILE, [])
    if not habits:
        habits = DEFAULT_HABITS
        _save_json(HABITS_FILE, habits)
    return habits


def save_habits(habits):
    _save_json(HABITS_FILE, habits)


def add_habit(name: str, schedule: str):
    habits = load_habits()
    new_id = max((h.get("id", 0) for h in habits), default=0) + 1
    habit = {
        "id": new_id,
        "name": name,
        "schedule": schedule,
    }
    habits.append(habit)
    save_habits(habits)
    return habit


def list_habits():
    return load_habits()


# ---------- проекты ----------

def load_projects():
    projects = _load_json(PROJECTS_FILE, [])
    if projects is None:
        projects = []
    return projects


def save_projects(projects):
    _save_json(PROJECTS_FILE, projects)


def add_project(name: str):
    projects = load_projects()
    new_id = max((p.get("id", 0) for p in projects), default=0) + 1
    project = {
        "id": new_id,
        "name": name,
        "steps": [],
    }
    projects.append(project)
    save_projects(projects)
    return project


def add_project_step(project_id: int, text: str):
    projects = load_projects()
    for p in projects:
        if p["id"] == project_id:
            steps = p.get("steps", [])
            new_step_id = max((s.get("id", 0) for s in steps), default=0) + 1
            step = {
                "id": new_step_id,
                "text": text,
                "done": False,
            }
            steps.append(step)
            p["steps"] = steps
            save_projects(projects)
            return p, step
    return None, None


def list_projects():
    return load_projects()


def get_project_by_name_or_id(key: str):
    projects = load_projects()
    if key.isdigit():
        pid = int(key)
        for p in projects:
            if p["id"] == pid:
                return p
    low = key.lower()
    for p in projects:
        if p["name"].lower() == low:
            return p
    return None


# ---------- SOS чеклисты ----------

def load_sos():
    sos_list = _load_json(SOS_FILE, [])
    if not sos_list:
        sos_list = DEFAULT_SOS
        _save_json(SOS_FILE, sos_list)
    return sos_list


def save_sos(sos_list):
    _save_json(SOS_FILE, sos_list)


def add_sos(name: str, steps):
    sos_list = load_sos()
    new_id = max((s.get("id", 0) for s in sos_list), default=0) + 1
    sos = {
        "id": new_id,
        "name": name,
        "steps": steps,
    }
    sos_list.append(sos)
    save_sos(sos_list)
    return sos


def list_sos():
    return sos_list


def list_sos():
    return load_sos()


def get_sos_by_name_or_id(key: str):
    sos_list = load_sos()
    if key.isdigit():
        sid = int(key)
        for s in sos_list:
            if s["id"] == sid:
                return s
    low = key.lower()
    for s in sos_list:
        if s["name"].lower() == low:
            return s
    return None


# ---------- "Сегодня" ----------

def load_today():
    return _load_json(TODAY_FILE, [])


def save_today(today_list):
    _save_json(TODAY_FILE, today_list)


def add_today_from_task(task_id: int):
    task = get_task_by_id(task_id)
    if not task:
        return None
    today = load_today()
    new_id = max((t.get("id", 0) for t in today), default=0) + 1
    item = {
        "id": new_id,
        "task_id": task_id,
        "text": task["text"],
        "added_at": datetime.datetime.utcnow().isoformat(),
    }
    today.append(item)
    save_today(today)
    return item


def list_today():
    return load_today()


def clear_today():
    save_today([])


# ---------- "Завтра" ----------

def load_tomorrow():
    return _load_json(TOMORROW_FILE, [])


def save_tomorrow(tomorrow_list):
    _save_json(TOMORROW_FILE, tomorrow_list)


def add_tomorrow_from_task(task_id: int):
    task = get_task_by_id(task_id)
    if not task:
        return None
    tomorrow = load_tomorrow()
    new_id = max((t.get("id", 0) for t in tomorrow), default=0) + 1
    item = {
        "id": new_id,
        "task_id": task_id,
        "text": task["text"],
        "added_at": datetime.datetime.utcnow().isoformat(),
    }
    tomorrow.append(item)
    save_tomorrow(tomorrow)
    return item


def list_tomorrow():
    return load_tomorrow()


def clear_tomorrow():
    save_tomorrow([])


# ---------- состояние (режимы) ----------

def load_state():
    return _load_json(STATE_FILE, {})


def save_state(state):
    _save_json(STATE_FILE, state)


def set_pending_action(action: dict | None):
    state = load_state()
    if action is None:
        state.pop("pending_action", None)
    else:
        state["pending_action"] = action
    save_state(state)


def get_pending_action():
    state = load_state()
    return state.get("pending_action")