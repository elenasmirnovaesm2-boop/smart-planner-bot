import os
import json

import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError

# Бот в main.py импортирует это имя – оставляем.
tasks_by_user = {}

# Токен Dropbox берём из переменной окружения DROPBOX_TOKEN (Render → Environment)
DROPBOX_TOKEN = os.environ["DROPBOX_TOKEN"]

# Клиент Dropbox
dbx = dropbox.Dropbox(DROPBOX_TOKEN)

# Если файлы лежат в корне Dropbox – оставь пустую строку.
# Если они в папке (например, /planner), впиши FOLDER = "/planner"
FOLDER = ""


def _path(filename: str) -> str:
    """
    Собираем путь вида "/tasks.json" или "/planner/tasks.json"
    """
    if FOLDER:
        return f"{FOLDER.rstrip('/')}/{filename}"
    return f"/{filename}"


def _download_json(filename: str, default):
    """
    Скачиваем JSON из Dropbox.
    Если файла нет – возвращаем default.
    """
    try:
        _, res = dbx.files_download(_path(filename))
        data = res.content.decode("utf-8")
        return json.loads(data)
    except ApiError as e:
        print(f"[storage] Dropbox download error for {filename}: {e}")
        return default
    except Exception as e:
        print(f"[storage] JSON parse error for {filename}: {e}")
        return default


def _upload_json(filename: str, data):
    """
    Загружаем JSON в Dropbox, перезаписывая файл.
    """
    body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    dbx.files_upload(body, _path(filename), mode=WriteMode("overwrite"))


def _normalize_list(raw):
    """
    Приводим старый формат к новому:
    - строка -> {"title": строка, "children": []}
    - dict -> гарантируем наличие полей title и children
    """
    result = []
    if not raw:
        return result

    for item in raw:
        if isinstance(item, str):
            result.append({"title": item, "children": []})
        elif isinstance(item, dict):
            title = item.get("title") or item.get("text") or str(item)
            children = item.get("children") or []
            if not isinstance(children, list):
                children = []
            result.append({"title": title, "children": children})
        else:
            result.append({"title": str(item), "children": []})
    return result


def load_data(user_id):
    """
    Загружаем ВСЕ разделы из Dropbox и возвращаем единый dict.
    user_id по сути не используется – у нас один набор файлов.
    """
    inbox = _download_json("tasks.json", default=[])
    today = _download_json("today.json", default=[])
    routines = _download_json("routines.json", default=[])
    templates = _download_json("templates.json", default=[])
    projects = _download_json("projects.json", default=[])
    habits = _download_json("habits.json", default=[])
    sos = _download_json("sos.json", default=[])

    data = {
        "inbox": _normalize_list(inbox),
        "today": _normalize_list(today),
        "routines": _normalize_list(routines),
        "templates": _normalize_list(templates),
        "projects": _normalize_list(projects),
        "habits": _normalize_list(habits),
        "sos": _normalize_list(sos),
    }
    return data


def save_data(user_id, data):
    """
    Сохраняем разделы обратно в отдельные файлы Dropbox.
    """
    _upload_json("tasks.json", data.get("inbox", []))
    _upload_json("today.json", data.get("today", []))
    _upload_json("routines.json", data.get("routines", []))
    _upload_json("templates.json", data.get("templates", []))
    _upload_json("projects.json", data.get("projects", []))
    _upload_json("habits.json", data.get("habits", []))
    _upload_json("sos.json", data.get("sos", []))