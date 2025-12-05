# bot/routine_task.py
"""
Карточка задачи-рутины.

Это НЕ обычная "рутина" из списка,
а более детальная штука для работы с одной конкретной рутиной.
"""

from typing import List, Optional
import datetime


def new_routine_task(
    *,
    id: int,
    name: str,
    description: str = "",
    steps: Optional[List[str]] = None,
    components: Optional[List[str]] = None,
    planned_minutes: Optional[int] = None,
    actual_minutes: Optional[int] = None,
    comment: str = "",
    repeat: str = "",
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    reminder: bool = False,
) -> dict:
    """
    Создаёт словарь с полной карточкой задачи-рутины.

    Поля:
      id               — внутренний id (можно брать из счётчика)
      name             — название рутины (обязательное поле)
      description      — общее описание / смысл рутины
      steps            — мелкие шаги / действия (список строк)
      components       — предметы / ресурсы, которые нужны (список строк)
      planned_minutes  — предполагаемое время (в минутах)
      actual_minutes   — фактическое затраченное время (в минутах)
      comment          — что улучшить / заметки
      repeat           — повторяемость (например: "каждый день", "по будням")
      start_time       — время начала, строка "HH:MM" (например "08:30")
      end_time         — время конца, строка "HH:MM"
      reminder         — нужно ли напоминание (True/False)
    """

    return {
        "id": id,
        "name": name,
        "description": description,
        "steps": steps or [],
        "components": components or [],
        "planned_minutes": planned_minutes,
        "actual_minutes": actual_minutes,
        "comment": comment,
        "repeat": repeat,
        "start_time": start_time,
        "end_time": end_time,
        "reminder": reminder,
        "created_at": datetime.datetime.utcnow().isoformat(),
    }


def render_routine_task_card(rt: dict) -> str:
    """
    Красиво выводит карточку задачи-рутины в текстовом виде
    (для отправки в Telegram).
    """

    lines: List[str] = []

    # Заголовок
    lines.append(f"🔁 Рутина-задача #{rt.get('id', '?')}")
    lines.append("")
    lines.append(f"Название: {rt.get('name', 'Без названия')}")

    # Описание
    desc = (rt.get("description") or "").strip()
    if desc:
        lines.append("")
        lines.append("Описание:")
        lines.append(desc)

    # Шаги
    steps = rt.get("steps") or []
    if steps:
        lines.append("")
        lines.append("Шаги:")
        for i, s in enumerate(steps, start=1):
            lines.append(f"{i}. {s}")

    # Компоненты / предметы
    comps = rt.get("components") or []
    if comps:
        lines.append("")
        lines.append("Что понадобится:")
        for c in comps:
            lines.append(f"• {c}")

    # Время
    planned = rt.get("planned_minutes")
    actual = rt.get("actual_minutes")
    start_time = rt.get("start_time")
    end_time = rt.get("end_time")

    time_lines = []
    if planned is not None:
        time_lines.append(f"план: ~{planned} мин")
    if actual is not None:
        time_lines.append(f"факт: {actual} мин")

    if start_time or end_time:
        span = f"{start_time or '??:??'}–{end_time or '??:??'}"
        time_lines.append(f"окно: {span}")

    if time_lines:
        lines.append("")
        lines.append("⏱ Время:")
        for t in time_lines:
            lines.append(f"- {t}")

    # Повторяемость
    repeat = (rt.get("repeat") or "").strip()
    if repeat:
        lines.append("")
        lines.append(f"🔁 Повторяемость: {repeat}")

    # Напоминание
    if rt.get("reminder"):
        lines.append("🔔 Напоминание: включено")
    else:
        lines.append("🔔 Напоминание: выключено")

    # Комментарий
    comment = (rt.get("comment") or "").strip()
    if comment:
        lines.append("")
        lines.append("Комментарий:")
        lines.append(comment)

    return "\n".join(lines)