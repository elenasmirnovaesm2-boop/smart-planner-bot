import json
import datetime
import os

# файл с задачами лежит рядом с этим файлом
TASKS_FILE = os.path.join(os.path.dirname(__file__), "tasks.json")


def load_tasks():
    """
    Читает задачи из tasks.json.
    Возвращает список словарей.
    """
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_tasks(tasks):
    """
    Сохраняет список задач в tasks.json.
    """
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)


def add_task(text: str):
    """
    Добавляет новую задачу в инбокс.
    Возвращает добавленную задачу.
    """
    tasks = load_tasks()
    new_id = (max((t.get("id", 0) for t in tasks), default=0) + 1)
    task = {
        "id": new_id,
        "text": text,
        "created_at": datetime.datetime.utcnow().isoformat(),
        "done": False,
    }
    tasks.append(task)
    save_tasks(tasks)
    return task


def list_active_tasks():
    """
    Возвращает список невыполненных задач.
    """
    tasks = load_tasks()
    return [t for t in tasks if not t.get("done")]


def complete_task_by_number(number: int):
    """
    Отмечает как выполненную задачу по порядковому номеру
    из списка активных задач (/inbox).
    Возвращает (успех: bool, задача или None).
    """
    tasks = load_tasks()
    active = [t for t in tasks if not t.get("done")]

    if number < 1 or number > len(active):
        return False, None

    task = active[number - 1]

    for t in tasks:
        if t["id"] == task["id"]:
            t["done"] = True
            break

    save_tasks(tasks)
    return True, task