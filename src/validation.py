def validate_registration(username, password):
    MIN_PASSWORD_LENGTH = 8
    MIN_USERNAME_LENGTH = 2

    if not username or not password:
        return False, "Ім'я та пароль не можуть бути порожніми."

    if len(username) < MIN_USERNAME_LENGTH:
        return False, f"Логін має бути не менше {MIN_USERNAME_LENGTH} символів."

    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Пароль має бути не менше {MIN_PASSWORD_LENGTH} символів."

    return True, ""


def validate_transaction_amount(amount_str):
    try:
        amount_float = float(amount_str)
        if amount_float <= 0:
            return False, None
        return True, amount_float
    except (ValueError, TypeError):
        return False, None