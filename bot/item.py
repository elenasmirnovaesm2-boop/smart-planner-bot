# bot/item.py
"""
Карточка предмета (объект/класс).

Используется для вещей: техника, аптечка, уход, расходники и т.п.
"""

import datetime
from typing import Optional


def new_item(
    *,
    id: int,
    name: str,
    price: Optional[float] = None,
    expected_usage_days: Optional[int] = None,
    actual_usage_days: Optional[int] = None,
    purchased_at: Optional[str] = None,      # Дата покупки ISO
    usage_start: Optional[str] = None,       # Начало использования
    usage_expected_end: Optional[str] = None,# Предполагаемый конец
    reminder: bool = False                   # Нужно ли напомнить о покупке
) -> dict:
    """
    Создаёт карточку предмета.

    Поля:
      id                    — уникальный ID
      name                  — название предмета
      price                 — стоимость
      expected_usage_days   — планируемая длительность использования
      actual_usage_days     — фактическая длительность
      purchased_at          — дата покупки (str, ISO)
      usage_start           — когда начали использовать
      usage_expected_end    — когда предположительно закончится
      reminder              — True/False, нужно ли напоминать о покупке
    """

    return {
        "id": id,
        "name": name,
        "price": price,
        "expected_usage_days": expected_usage_days,
        "actual_usage_days": actual_usage_days,
        "purchased_at": purchased_at,
        "usage_start": usage_start,
        "usage_expected_end": usage_expected_end,
        "reminder": reminder,
        "created_at": datetime.datetime.utcnow().isoformat(),
    }


def render_item_card(item: dict) -> str:
    """
    Формирует красивый текст для карточки предмета (Telegram).
    """

    lines = []
    lines.append(f"📦 Предмет #{item.get('id', '?')}")
    lines.append(f"Название: {item.get('name', 'Без названия')}")

    # Стоимость
    if item.get("price") is not None:
        lines.append(f"💰 Стоимость: {item['price']} €")

    # Расчётное / фактическое время пользования
    if item.get("expected_usage_days") is not None:
        lines.append(f"⏳ План использования: ~{item['expected_usage_days']} дней")

    if item.get("actual_usage_days") is not None:
        lines.append(f"📌 Факт использования: {item['actual_usage_days']} дней")

    # Даты
    purchased = item.get("purchased_at")
    if purchased:
        lines.append(f"🛒 Куплено: {purchased}")

    start = item.get("usage_start")
    if start:
        lines.append(f"▶️ Начало использования: {start}")

    end = item.get("usage_expected_end")
    if end:
        lines.append(f"🔚 Предполагаемый конец: {end}")

    # Напоминание
    reminder = item.get("reminder")
    if reminder:
        lines.append("🔔 Напоминание: включено")
    else:
        lines.append("🔔 Напоминание: выключено")

    return "\n".join(lines)