"""
Rotating file + console logging, with a filter that redacts secrets so
tokens / API keys can never end up in a log file.
"""
from __future__ import annotations

import logging
import os
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import config

_SECRET_PATTERNS = [
    re.compile(re.escape(config.telegram_bot_token)) if config.telegram_bot_token else None,
    re.compile(re.escape(config.openrouter_api_key)) if config.openrouter_api_key else None,
    re.compile(re.escape(config.gemini_api_key)) if config.gemini_api_key else None,
]
_SECRET_PATTERNS = [p for p in _SECRET_PATTERNS if p is not None]

_HEADER_PATTERN = re.compile(r"(authorization\s*[:=]\s*)\S+", re.IGNORECASE)
_BEARER_PATTERN = re.compile(r"Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*")


class RedactSecretsFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        redacted = msg
        for pattern in _SECRET_PATTERNS:
            redacted = pattern.sub("[REDACTED]", redacted)
        redacted = _HEADER_PATTERN.sub(r"\1[REDACTED]", redacted)
        redacted = _BEARER_PATTERN.sub("Bearer [REDACTED]", redacted)
        if redacted != msg:
            record.msg = redacted
            record.args = ()
        return True


def setup_logging() -> None:
    log_dir = Path(config.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, config.log_level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    redact_filter = RedactSecretsFilter()

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    console.addFilter(redact_filter)

    file_handler = RotatingFileHandler(
        log_dir / "bot.log", maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    file_handler.addFilter(redact_filter)

    # Avoid duplicate handlers if setup_logging() is called twice (e.g. in tests).
    root.handlers.clear()
    root.addHandler(console)
    root.addHandler(file_handler)

    # Silence noisy third-party libraries a bit.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
