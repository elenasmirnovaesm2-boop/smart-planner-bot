# auth_config.py

# сюда ВПИШИ свой Telegram user_id вместо 123456789
ALLOWED_USERS = {7604757170}


def is_allowed(user_id: int) -> bool:
    """Проверяем, есть ли user_id в белом списке."""
    return user_id in ALLOWED_USERS