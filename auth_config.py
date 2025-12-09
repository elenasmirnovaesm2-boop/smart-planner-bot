# auth_config.py

# сюда ВПИШИ свой Telegram user_id вместо 123456789
ALLOWED_USERS = {7604757170}

def is_allowed(message):
    # Если прилетело не сообщение (например, системный апдейт) — отклоняем
    if not hasattr(message, "from_user") or message.from_user is None:
        return False

    return message.from_user.id in ALLOWED_USERS