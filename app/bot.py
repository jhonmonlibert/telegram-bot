"""
Bot factory: builds the aiogram Bot + Dispatcher, wires up all routers in
the correct order, and defines startup/shutdown hooks (DB connect/close,
AI client cleanup).
"""
from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import config
from app.database.db import db
from app.database.migrations import run_migrations
from app.handlers import admin, chat, groups, settings, start
from app.services.ai_manager import get_ai_manager

logger = logging.getLogger(__name__)


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()

    # Order matters: more specific routers first, the private-chat
    # catch-all handler in `chat` last so it never swallows updates meant
    # for other routers.
    dp.include_router(start.router)
    dp.include_router(settings.router)
    dp.include_router(admin.router)
    dp.include_router(groups.router)
    dp.include_router(chat.router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    return dp


def create_bot() -> Bot:
    return Bot(
        token=config.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


async def on_startup(bot: Bot) -> None:
    await db.connect()
    await run_migrations(db)
    me = await bot.get_me()
    logger.info("Bot started as @%s (id=%s)", me.username, me.id)
    if not config.validate_openrouter():
        logger.warning("OPENROUTER_API_KEY is not set — AI replies will fail until it is configured.")
    if config.enable_gemini_fallback and not config.validate_gemini():
        logger.info("Gemini fallback is enabled but GEMINI_API_KEY is not set — fallback is inactive.")


async def on_shutdown(bot: Bot) -> None:
    logger.info("Shutting down...")
    await get_ai_manager().close()
    await db.close()
    await bot.session.close()
