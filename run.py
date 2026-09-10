#!/usr/bin/env python3
"""
Main entrypoint. Run with:

    python3 run.py

or in the background with:

    nohup python3 run.py > bot.log 2>&1 &

The application validates its configuration and starts polling. It will
NOT crash the whole process on a single failed Telegram/OpenRouter
request — those are handled and logged inside the handlers/services.
"""
from __future__ import annotations

import asyncio
import logging
import sys

from app.bot import create_bot, create_dispatcher
from app.config import config
from app.logging_config import setup_logging

logger = logging.getLogger(__name__)


def _check_required_config() -> bool:
    ok = True
    if not config.validate_telegram():
        logger.error("TELEGRAM_BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")
        ok = False
    if not config.validate_openrouter():
        logger.warning(
            "OPENROUTER_API_KEY is not set. The bot will start, but AI replies will fail "
            "until it is configured."
        )
    return ok


async def main() -> None:
    setup_logging()
    logger.info("Starting Telegram AI Assistant...")

    if not _check_required_config():
        logger.error("Missing required configuration. Exiting.")
        sys.exit(1)

    bot = create_bot()
    dp = create_dispatcher()

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("Polling stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user, shutting down.")
