"""
Text formatting / chunking helpers.
"""
from __future__ import annotations

TELEGRAM_MAX_MESSAGE_LENGTH = 4096


def chunk_text(text: str, max_length: int = TELEGRAM_MAX_MESSAGE_LENGTH) -> list[str]:
    """Split long text into Telegram-safe chunks, preferring to break on
    paragraph/line boundaries rather than mid-word."""
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    remaining = text
    while len(remaining) > max_length:
        split_at = remaining.rfind("\n", 0, max_length)
        if split_at == -1 or split_at < max_length // 2:
            split_at = remaining.rfind(" ", 0, max_length)
        if split_at == -1 or split_at < max_length // 2:
            split_at = max_length
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks


def format_error_for_user(lang: str = "en") -> str:
    if lang == "fa":
        return "⚠️ متاسفانه در حال حاضر مشکلی پیش آمده. لطفاً کمی بعد دوباره امتحان کنید."
    return "⚠️ Something went wrong on our end. Please try again in a moment."
