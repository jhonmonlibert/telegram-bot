from __future__ import annotations

from app.utils.security import (
    is_valid_callback_data,
    is_valid_telegram_id,
    redact_secrets,
    sanitize_text,
)


def test_sanitize_text_strips_control_chars():
    dirty = "hello\x00world\x1f!"
    assert sanitize_text(dirty) == "helloworld!"


def test_sanitize_text_enforces_max_length():
    text = "a" * 100
    result = sanitize_text(text, max_length=10)
    assert len(result) == 10


def test_is_valid_telegram_id():
    assert is_valid_telegram_id(123456) is True
    assert is_valid_telegram_id(-5) is False
    assert is_valid_telegram_id("not-a-number") is False
    assert is_valid_telegram_id(0) is False


def test_is_valid_callback_data():
    assert is_valid_callback_data("menu:chat") is True
    assert is_valid_callback_data("gmode:-100123:mention") is True
    assert is_valid_callback_data("has spaces") is False
    assert is_valid_callback_data("a" * 100) is False
    assert is_valid_callback_data(None) is False


def test_redact_secrets_removes_configured_secrets():
    from app.config import config as real_config

    # The conftest sets these env vars, so the singleton config picks them up.
    secret = real_config.telegram_bot_token
    if secret:
        text = f"token is {secret} do not log it"
        assert secret not in redact_secrets(text)
