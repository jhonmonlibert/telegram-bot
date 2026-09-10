"""
Small security helpers: input sanitization, secret redaction, admin/group
authorization checks, and callback-data validation.
"""
from __future__ import annotations

import re
from typing import Iterable, Optional

from app.config import config

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Whitelist for callback_data payloads used by inline keyboards.
_CALLBACK_DATA_RE = re.compile(r"^[a-zA-Z0-9_\-:]{1,64}$")


def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
    """Strip control characters and enforce a maximum length."""
    if text is None:
        return ""
    cleaned = _CONTROL_CHARS_RE.sub("", text)
    cleaned = cleaned.strip()
    limit = max_length if max_length is not None else config.max_message_length
    if len(cleaned) > limit:
        cleaned = cleaned[:limit]
    return cleaned


def is_valid_telegram_id(value) -> bool:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return False
    return 0 < n < 10_000_000_000_000  # generous but sane upper bound


def is_valid_callback_data(data: str) -> bool:
    if not isinstance(data, str):
        return False
    return bool(_CALLBACK_DATA_RE.match(data))


def is_admin(telegram_user_id: int) -> bool:
    return config.is_admin(telegram_user_id)


_SECRET_VALUES: list[str] = [
    v for v in (config.telegram_bot_token, config.openrouter_api_key, config.gemini_api_key) if v
]


def redact_secrets(text: str) -> str:
    """Defense-in-depth: strip any literal secret values that might have
    ended up in text destined for a user-facing message or a log line."""
    redacted = text
    for secret in _SECRET_VALUES:
        redacted = redacted.replace(secret, "[REDACTED]")
    return redacted


_DANGEROUS_PATTERNS: Iterable[re.Pattern] = (
    re.compile(r"\brm\s+-rf\b", re.IGNORECASE),
    re.compile(r"\bos\.system\b"),
    re.compile(r"\bsubprocess\.(run|call|Popen)\b"),
    re.compile(r"\beval\s*\("),
    re.compile(r"\bexec\s*\("),
)


def looks_like_command_injection(text: str) -> bool:
    """Heuristic guard: the bot never executes AI output or user text as
    shell/Python, but we still flag obviously dangerous payloads so they
    are not echoed verbatim in places like admin broadcast previews."""
    return any(p.search(text) for p in _DANGEROUS_PATTERNS)
