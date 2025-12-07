import json
import os

# Глобальное хранилище задач (словарь: user_id -> данные по разделам)
tasks_by_user = {}

DATA_DIR = "data"  # каталог для хранения файлов с данными

def get_data_file(user_id):
    """Путь к файлу хранения данных для заданного пользователя."""
    # Храним каждый пользовательский список в отдельном файле JSON
    return os.path.join(DATA_DIR, f"user_{user_id}.json")

def load_data(user_id):
    """Загрузить данные задач пользователя из файла (если существует)."""
    file_path = get_data_file(user_id)
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except Exception as e:
            print(f"Ошибка при загрузке данных пользователя {user_id}: {e}")
            return None
    return None

def save_data(user_id, data):
    """Сохранить данные задач пользователя в файл JSON."""
    os.makedirs(DATA_DIR, exist_ok=True)
    file_path = get_data_file(user_id)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка при сохранении данных пользователя {user_id}: {e}")