"""
Central application configuration.

All configuration is read from environment variables (via a .env file in
development). Nothing here should ever contain a hardcoded secret.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv

# Load .env once, at import time, before anything else touches os.environ.
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)
else:
    load_dotenv()  # fall back to default search behaviour


def _get_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def _get_int(name: str, default: int) -> int:
    val = os.getenv(name)
    if val is None or val.strip() == "":
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    val = os.getenv(name)
    if val is None or val.strip() == "":
        return default
    try:
        return float(val)
    except ValueError:
        return default


def _parse_admin_ids(raw: str) -> List[int]:
    ids: List[int] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            ids.append(int(chunk))
        except ValueError:
            continue
    return ids


@dataclass(frozen=True)
class Config:
    # --- Telegram ---
    telegram_bot_token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))

    # --- OpenRouter (primary AI provider) ---
    openrouter_api_key: str = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", ""))
    openrouter_model: str = field(default_factory=lambda: os.getenv("OPENROUTER_MODEL", "openrouter/free"))
    openrouter_base_url: str = field(
        default_factory=lambda: os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    )

    # --- Gemini (Google AI Studio) — automatic fallback provider ---
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))
    gemini_base_url: str = field(
        default_factory=lambda: os.getenv(
            "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"
        )
    )
    enable_gemini_fallback: bool = field(default_factory=lambda: _get_bool("ENABLE_GEMINI_FALLBACK", True))

    # --- Admins ---
    admin_telegram_ids: List[int] = field(
        default_factory=lambda: _parse_admin_ids(os.getenv("ADMIN_TELEGRAM_IDS", ""))
    )

    # --- Language ---
    default_language: str = field(default_factory=lambda: os.getenv("DEFAULT_LANGUAGE", "fa"))

    # --- Conversation memory ---
    max_history_messages: int = field(default_factory=lambda: _get_int("MAX_HISTORY_MESSAGES", 20))
    max_message_length: int = field(default_factory=lambda: _get_int("MAX_MESSAGE_LENGTH", 8000))

    # --- Group behaviour ---
    group_mode: str = field(default_factory=lambda: os.getenv("GROUP_MODE", "mention"))

    # --- Rate limiting ---
    user_rate_limit_per_minute: int = field(
        default_factory=lambda: _get_int("USER_RATE_LIMIT_PER_MINUTE", 10)
    )
    user_rate_limit_per_hour: int = field(
        default_factory=lambda: _get_int("USER_RATE_LIMIT_PER_HOUR", 100)
    )
    group_rate_limit_per_minute: int = field(
        default_factory=lambda: _get_int("GROUP_RATE_LIMIT_PER_MINUTE", 5)
    )

    # --- AI generation params ---
    ai_temperature: float = field(default_factory=lambda: _get_float("AI_TEMPERATURE", 0.7))
    ai_max_tokens: int = field(default_factory=lambda: _get_int("AI_MAX_TOKENS", 1024))
    ai_timeout_seconds: float = field(default_factory=lambda: _get_float("AI_TIMEOUT_SECONDS", 30.0))
    ai_max_retries: int = field(default_factory=lambda: _get_int("AI_MAX_RETRIES", 3))

    # --- Database ---
    database_path: str = field(default_factory=lambda: os.getenv("DATABASE_PATH", "./data/bot.db"))

    # --- Logging ---
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_dir: str = field(default_factory=lambda: os.getenv("LOG_DIR", "./logs"))

    def validate_telegram(self) -> bool:
        return bool(self.telegram_bot_token)

    def validate_openrouter(self) -> bool:
        return bool(self.openrouter_api_key)

    def validate_gemini(self) -> bool:
        return bool(self.gemini_api_key)

    def is_admin(self, telegram_user_id: int) -> bool:
        return telegram_user_id in self.admin_telegram_ids


# Singleton, imported everywhere else.
config = Config()
