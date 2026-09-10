from __future__ import annotations

from app.config import Config


def test_defaults_are_sane():
    cfg = Config(telegram_bot_token="", openrouter_api_key="")
    assert cfg.openrouter_model == "openrouter/free"
    assert cfg.group_mode == "mention"
    assert cfg.max_history_messages == 20
    assert cfg.default_language in ("fa", "en")


def test_validate_telegram_and_openrouter():
    cfg = Config(telegram_bot_token="abc", openrouter_api_key="")
    assert cfg.validate_telegram() is True
    assert cfg.validate_openrouter() is False


def test_admin_parsing_and_is_admin():
    cfg = Config(admin_telegram_ids=[111, 222])
    assert cfg.is_admin(111) is True
    assert cfg.is_admin(999) is False


def test_gemini_validation():
    cfg = Config(gemini_api_key="")
    assert cfg.validate_gemini() is False
    cfg2 = Config(gemini_api_key="some-key")
    assert cfg2.validate_gemini() is True
