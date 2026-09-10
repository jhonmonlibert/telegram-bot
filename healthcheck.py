#!/usr/bin/env python3
"""
Lightweight healthcheck: verifies the process's own config is sane and
that SQLite is reachable, without making any external network calls
(no Telegram/OpenRouter requests). Suitable for a cron job or manual
`python3 healthcheck.py` check.

Exit code 0 = healthy, 1 = unhealthy.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from app.config import config
from app.database.db import Database
from app.database.migrations import run_migrations


async def check_database() -> tuple[bool, str]:
    try:
        database = Database(config.database_path)
        await database.connect()
        await run_migrations(database)
        await database.fetchone("SELECT 1")
        await database.close()
        return True, "SQLite OK"
    except Exception as exc:  # pragma: no cover - defensive
        return False, f"SQLite error: {exc}"


def check_telegram_config() -> tuple[bool, str]:
    if config.validate_telegram():
        return True, "TELEGRAM_BOT_TOKEN present"
    return False, "TELEGRAM_BOT_TOKEN missing"


def check_openrouter_config() -> tuple[bool, str]:
    if config.validate_openrouter():
        return True, "OPENROUTER_API_KEY present"
    return False, "OPENROUTER_API_KEY missing (AI replies will fail)"


def check_gemini_config() -> tuple[bool, str]:
    if not config.enable_gemini_fallback:
        return True, "Gemini fallback disabled"
    if config.validate_gemini():
        return True, "GEMINI_API_KEY present (fallback active)"
    return True, "GEMINI_API_KEY missing (fallback inactive, not fatal)"


async def main() -> int:
    checks = [
        check_telegram_config(),
        check_openrouter_config(),
        check_gemini_config(),
        await check_database(),
    ]

    healthy = True
    for ok, message in checks:
        status = "OK  " if ok else "FAIL"
        print(f"[{status}] {message}")
        # Only Telegram config + database are hard requirements.
        if not ok and ("TELEGRAM_BOT_TOKEN" in message or "SQLite" in message):
            healthy = False

    print("\nOverall:", "HEALTHY" if healthy else "UNHEALTHY")
    return 0 if healthy else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
