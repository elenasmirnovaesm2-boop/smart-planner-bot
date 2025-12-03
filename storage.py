import json
import datetime
import os

BASE_DIR = os.path.dirname(__file__)

TASKS_FILE = os.path.join(BASE_DIR, "tasks.json")
ROUTINES_FILE = os.path.join(BASE_DIR, "routines.json")
TEMPLATES_FILE = os.path.join(BASE_DIR, "templates.json")
HABITS_FILE = os.path.join(BASE_DIR, "habits.json")
PROJECTS_FILE = os.path.join(BASE_DIR, "projects.json")
SOS_FILE = os.path.join(BASE_DIR, "sos.json")


# ---------- общие утилиты ----------

def _load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------- задачи (inbox / слой 1 базовый) ----------

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


# ---------- рутины (слой 1: рутины) ----------

def load_routines():
    return _load_json(ROUTINES_FILE, [])


def save_routines(routines):
    _save_json(ROUTINES_FILE, routines)


def add_routine(name: str, steps):
    routines = load_routines()
    new_id = max((r.get("id", 0) for r in routines), default=0) + 1
    routine = {
        "id": new_id,
        "name": name,
        "steps": steps,  # список строк
    }
    routines.append(routine)
    save_routines(routines)
    return routine


def list_routines():
    return load_routines()


def get_routine_by_name_or_id(key: str):
    routines = load_routines()
    # по id
    if key.isdigit():
        rid = int(key)
        for r in routines:
            if r["id"] == rid:
                return r
    # по имени (кейс-инсенситив)
    low = key.lower()
    for r in routines:
        if r["name"].lower() == low:
            return r
    return None


# ---------- шаблоны дня (слой 2: шаблон дня) ----------

def load_templates():
    return _load_json(TEMPLATES_FILE, [])


def save_templates(templates):
    _save_json(TEMPLATES_FILE, templates)


def add_template(name: str, blocks):
    """
    blocks: список строк, каждый блок – текст вида "07:30 утро: рутина Утро"
    сейчас без строгого парсинга времени.
    """
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


# ---------- привычки / расписания (слой 3: расписания) ----------

def load_habits():
    return _load_json(HABITS_FILE, [])


def save_habits(habits):
    _save_json(HABITS_FILE, habits)


def add_habit(name: str, schedule: str):
    """
    schedule – пока просто текст, например:
    'каждый день в 22:00', 'по будням утром'.
    """
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


# ---------- проекты (слой 4: проекты) ----------

def load_projects():
    return _load_json(PROJECTS_FILE, [])


def save_projects(projects):
    _save_json(PROJECTS_FILE, projects)


def add_project(name: str):
    projects = load_projects()
    new_id = max((p.get("id", 0) for p in projects), default=0) + 1
    project = {
        "id": new_id,
        "name": name,
        "steps": [],  # список шагов
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


# ---------- аварийные чеклисты (слой 5: SOS / аварийный режим) ----------

def load_sos():
    return _load_json(SOS_FILE, [])


def save_sos(sos_list):
    _save_json(SOS_FILE, sos_list)


def add_sos(name: str, steps):
    """
    steps – список строк: пошаговый чеклист для стресса, бессонницы и т.п.
    """
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