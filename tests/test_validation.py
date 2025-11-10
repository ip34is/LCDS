from src.validation import validate_registration, validate_transaction_amount

def test_registration_success():
    """Перевіряє, що коректні дані проходять валідацію."""
    is_valid, msg = validate_registration("test_user", "password123")
    assert is_valid is True
    assert msg == ""

def test_registration_password_too_short():
    """Тест на пароль '01' (коротший за 8 символів)."""
    is_valid, msg = validate_registration("test_user", "01")
    assert is_valid is False
    assert "8 символів" in msg

def test_registration_username_too_short():
    """Тест на логін 'u' (коротший за 2 символи)."""
    is_valid, msg = validate_registration("u", "password123")
    assert is_valid is False
    assert "2 символів" in msg

def test_registration_empty_fields():
    """Тест на порожні поля."""
    is_valid, msg = validate_registration("", "")
    assert is_valid is False
    assert "порожніми" in msg

def test_transaction_amount_success():
    """Перевіряє коректне число."""
    is_valid, value = validate_transaction_amount("150.50")
    assert is_valid is True
    assert value == 150.50

def test_transaction_amount_letters():
    """Перевіряє, що літери (напр. 'ЗП') не проходять."""
    is_valid, value = validate_transaction_amount("ЗП")
    assert is_valid is False
    assert value is None

def test_transaction_amount_zero():
    """Перевіряє нульову суму."""
    is_valid, value = validate_transaction_amount("0")
    assert is_valid is False
    assert value is None

def test_transaction_amount_negative():
    """Перевіряє від'ємну суму."""
    is_valid, value = validate_transaction_amount("-100")
    assert is_valid is False
    assert value is None