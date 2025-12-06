"""
Persistent storage layer for the Smart Planner bot.

This module provides JSON-based persistence for tasks and other
entities (routines, templates, habits, projects, SOS and today list).
All records are stored in a ``data`` subdirectory relative to this file.
If a JSON file does not exist, sensible defaults (empty lists) are
returned. CRUD functions are provided for each entity type.
"""

from __future__ import annotations

import json
import os
import datetime
from typing import Any, List, Dict, Tuple, Optional

# Determine base directory for data files. This file lives in ``full_bot``.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Ensure the data directory exists.
os.makedirs(DATA_DIR, exist_ok=True)

# Paths for each entity's JSON file.
TASKS_FILE = os.path.join(DATA_DIR, "tasks.json")
ROUTINES_FILE = os.path.join(DATA_DIR, "routines.json")
TEMPLATES_FILE = os.path.join(DATA_DIR, "templates.json")
HABITS_FILE = os.path.join(DATA_DIR, "habits.json")
PROJECTS_FILE = os.path.join(DATA_DIR, "projects.json")
SOS_FILE = os.path.join(DATA_DIR, "sos.json")
TODAY_FILE = os.path.join(DATA_DIR, "today.json")
STATE_FILE = os.path.join(DATA_DIR, "state.json")


def _load_json(path: str, default: Any) -> Any:
    """Load a JSON file and return its contents, or return ``default`` if not found."""
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: str, data: Any) -> None:
    """Save ``data`` to ``path`` as JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# === Tasks management ===

def load_tasks() -> List[Dict[str, Any]]:
    return _load_json(TASKS_FILE, [])


def save_tasks(tasks: List[Dict[str, Any]]) -> None:
    _save_json(TASKS_FILE, tasks)


def add_task(text: str) -> Dict[str, Any]:
    tasks = load_tasks()
    new_id = max((t.get("id", 0) for t in tasks), default=0) + 1
    task = {
        "id": new_id,
        "text": text,
        "done": False,
        "created_at": datetime.datetime.utcnow().isoformat(),
    }
    tasks.append(task)
    save_tasks(tasks)
    return task


def list_active_tasks() -> List[Dict[str, Any]]:
    tasks = load_tasks()
    return [t for t in tasks if not t.get("done")]


def get_task_by_id(task_id: int) -> Optional[Dict[str, Any]]:
    tasks = load_tasks()
    for task in tasks:
        if task.get("id") == task_id:
            return task
    return None


def update_task_text(task_id: int, new_text: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    tasks = load_tasks()
    for task in tasks:
        if task.get("id") == task_id:
            task["text"] = new_text
            save_tasks(tasks)
            return True, task
    return False, None


def delete_task_by_id(task_id: int) -> bool:
    tasks = load_tasks()
    new_tasks = [t for t in tasks if t.get("id") != task_id]
    if len(new_tasks) == len(tasks):
        return False
    save_tasks(new_tasks)
    return True


def complete_task_by_id(task_id: int) -> Tuple[bool, Optional[Dict[str, Any]]]:
    tasks = load_tasks()
    for task in tasks:
        if task.get("id") == task_id:
            task["done"] = True
            save_tasks(tasks)
            return True, task
    return False, None


# === Routines management ===

def load_routines() -> List[Dict[str, Any]]:
    return _load_json(ROUTINES_FILE, [])


def list_routines() -> List[Dict[str, Any]]:
    return load_routines()


def get_routine_by_id(routine_id: int) -> Optional[Dict[str, Any]]:
    routines = load_routines()
    for r in routines:
        if r.get("id") == routine_id:
            return r
    return None


def add_routine(name: str, steps: List[str]) -> Dict[str, Any]:
    routines = load_routines()
    new_id = max((r.get("id", 0) for r in routines), default=0) + 1
    routine = {"id": new_id, "name": name, "steps": steps}
    routines.append(routine)
    _save_json(ROUTINES_FILE, routines)
    return routine


def update_routine(routine_id: int, name: str, steps: List[str]) -> Tuple[bool, Optional[Dict[str, Any]]]:
    routines = load_routines()
    updated = None
    for r in routines:
        if r.get("id") == routine_id:
            r["name"] = name
            r["steps"] = steps
            updated = r
            break
    if updated is None:
        return False, None
    _save_json(ROUTINES_FILE, routines)
    return True, updated


def delete_routine(routine_id: int) -> bool:
    routines = load_routines()
    new_routines = [r for r in routines if r.get("id") != routine_id]
    if len(new_routines) == len(routines):
        return False
    _save_json(ROUTINES_FILE, new_routines)
    return True


# === Templates management ===

def load_templates() -> List[Dict[str, Any]]:
    return _load_json(TEMPLATES_FILE, [])


def list_templates() -> List[Dict[str, Any]]:
    return load_templates()


def get_template_by_id(template_id: int) -> Optional[Dict[str, Any]]:
    templates = load_templates()
    for t in templates:
        if t.get("id") == template_id:
            return t
    return None


def add_template(name: str, blocks: List[str]) -> Dict[str, Any]:
    templates = load_templates()
    new_id = max((t.get("id", 0) for t in templates), default=0) + 1
    tpl = {"id": new_id, "name": name, "blocks": blocks}
    templates.append(tpl)
    _save_json(TEMPLATES_FILE, templates)
    return tpl


def update_template(template_id: int, name: str, blocks: List[str]) -> Tuple[bool, Optional[Dict[str, Any]]]:
    templates = load_templates()
    updated = None
    for t in templates:
        if t.get("id") == template_id:
            t["name"] = name
            t["blocks"] = blocks
            updated = t
            break
    if updated is None:
        return False, None
    _save_json(TEMPLATES_FILE, templates)
    return True, updated


def delete_template(template_id: int) -> bool:
    templates = load_templates()
    new_templates = [t for t in templates if t.get("id") != template_id]
    if len(new_templates) == len(templates):
        return False
    _save_json(TEMPLATES_FILE, new_templates)
    return True


# === Projects management ===

def load_projects() -> List[Dict[str, Any]]:
    return _load_json(PROJECTS_FILE, [])


def list_projects() -> List[Dict[str, Any]]:
    return load_projects()


def get_project_by_id(project_id: int) -> Optional[Dict[str, Any]]:
    projects = load_projects()
    for p in projects:
        if p.get("id") == project_id:
            return p
    return None


def add_project(name: str, steps: List[str]) -> Dict[str, Any]:
    projects = load_projects()
    new_id = max((p.get("id", 0) for p in projects), default=0) + 1
    step_dicts = [{"id": idx, "text": s, "done": False} for idx, s in enumerate(steps, start=1)]
    proj = {"id": new_id, "name": name, "steps": step_dicts}
    projects.append(proj)
    _save_json(PROJECTS_FILE, projects)
    return proj


def update_project(project_id: int, name: str, steps: List[str]) -> Tuple[bool, Optional[Dict[str, Any]]]:
    projects = load_projects()
    updated = None
    for p in projects:
        if p.get("id") == project_id:
            new_steps = [{"id": idx, "text": s, "done": False} for idx, s in enumerate(steps, start=1)]
            p["name"] = name
            p["steps"] = new_steps
            updated = p
            break
    if updated is None:
        return False, None
    _save_json(PROJECTS_FILE, projects)
    return True, updated


def delete_project(project_id: int) -> bool:
    projects = load_projects()
    new_projects = [p for p in projects if p.get("id") != project_id]
    if len(new_projects) == len(projects):
        return False
    _save_json(PROJECTS_FILE, new_projects)
    return True


# === Habits management ===

def load_habits() -> List[Dict[str, Any]]:
    return _load_json(HABITS_FILE, [])


def list_habits() -> List[Dict[str, Any]]:
    return load_habits()


def get_habit_by_id(habit_id: int) -> Optional[Dict[str, Any]]:
    habits = load_habits()
    for h in habits:
        if h.get("id") == habit_id:
            return h
    return None


def add_habit(name: str, schedule: str) -> Dict[str, Any]:
    habits = load_habits()
    new_id = max((h.get("id", 0) for h in habits), default=0) + 1
    habit = {"id": new_id, "name": name, "schedule": schedule}
    habits.append(habit)
    _save_json(HABITS_FILE, habits)
    return habit


def update_habit(habit_id: int, name: str, schedule: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    habits = load_habits()
    updated = None
    for h in habits:
        if h.get("id") == habit_id:
            h["name"] = name
            h["schedule"] = schedule
            updated = h
            break
    if updated is None:
        return False, None
    _save_json(HABITS_FILE, habits)
    return True, updated


def delete_habit(habit_id: int) -> bool:
    habits = load_habits()
    new_habits = [h for h in habits if h.get("id") != habit_id]
    if len(new_habits) == len(habits):
        return False
    _save_json(HABITS_FILE, new_habits)
    return True


# === SOS checklists management ===

def load_sos() -> List[Dict[str, Any]]:
    return _load_json(SOS_FILE, [])


def list_sos() -> List[Dict[str, Any]]:
    return load_sos()


def get_sos_by_id(sos_id: int) -> Optional[Dict[str, Any]]:
    sos_list = load_sos()
    for s in sos_list:
        if s.get("id") == sos_id:
            return s
    return None


def add_sos(name: str, steps: List[str]) -> Dict[str, Any]:
    sos_list = load_sos()
    new_id = max((s.get("id", 0) for s in sos_list), default=0) + 1
    sos = {"id": new_id, "name": name, "steps": steps}
    sos_list.append(sos)
    _save_json(SOS_FILE, sos_list)
    return sos


def update_sos(sos_id: int, name: str, steps: List[str]) -> Tuple[bool, Optional[Dict[str, Any]]]:
    sos_list = load_sos()
    updated = None
    for s in sos_list:
        if s.get("id") == sos_id:
            s["name"] = name
            s["steps"] = steps
            updated = s
            break
    if updated is None:
        return False, None
    _save_json(SOS_FILE, sos_list)
    return True, updated


def delete_sos(sos_id: int) -> bool:
    sos_list = load_sos()
    new_sos = [s for s in sos_list if s.get("id") != sos_id]
    if len(new_sos) == len(sos_list):
        return False
    _save_json(SOS_FILE, new_sos)
    return True


# === Today list management ===

def add_today_from_task(task_id: int) -> Optional[Dict[str, Any]]:
    """
    Copy a task into the today list based on its ID. Returns the new today
    item if successful, else ``None``.
    """
    task = get_task_by_id(task_id)
    if not task:
        return None
    today = _load_json(TODAY_FILE, [])
    new_id = max((i.get("id", 0) for i in today), default=0) + 1
    item = {
        "id": new_id,
        "task_id": task_id,
        "text": task.get("text"),
        "added_at": datetime.datetime.utcnow().isoformat(),
    }
    today.append(item)
    _save_json(TODAY_FILE, today)
    return item


def list_today() -> List[Dict[str, Any]]:
    """Return a list of items scheduled for today."""
    return _load_json(TODAY_FILE, [])


# === State for pending actions (optional) ===

def load_state() -> Dict[str, Any]:
    return _load_json(STATE_FILE, {})


def save_state(state: Dict[str, Any]) -> None:
    _save_json(STATE_FILE, state)


def set_pending_action(action: Optional[Dict[str, Any]]) -> None:
    """
    Save a pending action (or clear it by passing ``None``). A pending
    action might look like ``{"type": "edit_task", "task_id": 1}``.
    """
    state = load_state()
    if action is None:
        state.pop("pending_action", None)
    else:
        state["pending_action"] = action
    save_state(state)


def get_pending_action() -> Optional[Dict[str, Any]]:
    state = load_state()
    return state.get("pending_action")