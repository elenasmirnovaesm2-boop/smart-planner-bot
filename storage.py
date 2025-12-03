import json
import datetime
import os

# tasks.json будет лежать рядом с файлами проекта
TASKS_FILE = os.path.join(os.path.dirname(__file__), "tasks.json")


def load_tasks():
    """Читаем задачи из файла."""
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_tasks(tasks):
    """Сохраняем задачи в файл."""
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)


def add_task(text: str):
    """Создать новую задачу."""
    tasks = load_tasks()
    new_id = max((t.get("id", 0) for t in tasks), default=0) + 1

    task = {
        "id": new_id,
        "text": text,
        "done": False,
        "created_at": datetime.datetime.utcnow().isoformat()
    }

    tasks.append(task)
    save_tasks(tasks)
    return task


def list_active_tasks():
    """Вернуть все активные задачи."""
    tasks = load_tasks()
    return [t for t in tasks if not t.get("done")]


def complete_task_by_id(task_id: int):
    """Отметить задачу выполненной по ID."""
    tasks = load_tasks()

    for t in tasks:
        if t["id"] == task_id:
            t["done"] = True
            save_tasks(tasks)
            return True, t

    return False, None