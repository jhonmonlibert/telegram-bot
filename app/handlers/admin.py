"""
Admin-only commands. Every handler here re-checks config.is_admin() itself
(defense in depth) even though the router-level filter already restricts
access.
"""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from app.config import config
from app.database.db import db
from app.services.groups import GroupService
from app.services.users import UserService
from app.utils.security import is_admin, sanitize_text

logger = logging.getLogger(__name__)
router = Router(name="admin")

user_service = UserService()
group_service = GroupService()


async def _admin_only(message: Message) -> bool:
    return bool(message.from_user) and is_admin(message.from_user.id)


router.message.filter(_admin_only)

BROADCAST_BATCH_SIZE = 25
BROADCAST_DELAY_SECONDS = 1.0  # stay well under Telegram's rate limits


async def _log_admin_action(admin_id: int, action: str, details: str = "") -> None:
    await db.execute(
        "INSERT INTO admin_actions (admin_telegram_id, action, details) VALUES (?, ?, ?)",
        (admin_id, action, details),
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    await message.answer(
        "🛠 Admin panel\n\n"
        "/stats - usage statistics\n"
        "/users - recent users\n"
        "/groups - recent groups\n"
        "/broadcast <text> - message all opted-in users\n"
        "/reload - reload runtime configuration"
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    user_count = await user_service.count_all()
    group_count = await group_service.count_all()
    row = await db.fetchone("SELECT COUNT(*) AS c FROM messages")
    message_count = row["c"] if row else 0
    await message.answer(
        "📊 Stats\n"
        f"Users: {user_count}\n"
        f"Groups: {group_count}\n"
        f"Stored messages: {message_count}\n"
        f"Primary model: {config.openrouter_model}\n"
        f"Gemini fallback: {'enabled' if config.enable_gemini_fallback and config.validate_gemini() else 'disabled'}"
    )


@router.message(Command("users"))
async def cmd_users(message: Message) -> None:
    users = await user_service.list_all(limit=20)
    if not users:
        await message.answer("No users yet.")
        return
    lines = [f"{u.telegram_user_id} | @{u.username or '-'} | {u.language} | blocked={u.is_blocked}" for u in users]
    await message.answer("👥 Recent users:\n" + "\n".join(lines))


@router.message(Command("groups"))
async def cmd_groups(message: Message) -> None:
    groups = await group_service.list_all(limit=20)
    if not groups:
        await message.answer("No groups yet.")
        return
    lines = [f"{g.chat_id} | {g.title or '-'} | mode={g.mode} | enabled={g.enabled}" for g in groups]
    await message.answer("👥 Recent groups:\n" + "\n".join(lines))


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, command: CommandObject, bot: Bot) -> None:
    text = sanitize_text((command.args or "").strip(), max_length=config.max_message_length)
    if not text:
        await message.answer("Usage: /broadcast <message>")
        return

    recipients = await user_service.list_notifiable()
    if not recipients:
        await message.answer("No opted-in users to broadcast to.")
        return

    await message.answer(f"📢 Broadcasting to {len(recipients)} users...")
    await _log_admin_action(message.from_user.id, "broadcast", f"recipients={len(recipients)}")

    sent = 0
    failed = 0
    for i in range(0, len(recipients), BROADCAST_BATCH_SIZE):
        batch = recipients[i : i + BROADCAST_BATCH_SIZE]
        for user in batch:
            try:
                await bot.send_message(user.telegram_user_id, text)
                sent += 1
            except Exception as exc:
                failed += 1
                logger.warning("Broadcast failed for user %s: %s", user.telegram_user_id, exc.__class__.__name__)
        await asyncio.sleep(BROADCAST_DELAY_SECONDS)

    await message.answer(f"✅ Broadcast complete. Sent: {sent}, Failed: {failed}")


@router.message(Command("reload"))
async def cmd_reload(message: Message) -> None:
    # Configuration is read from environment variables at process start.
    # A full hot-reload would need to reinitialize the AI clients; here we
    # simply confirm current values so the admin can verify env changes
    # after restarting the process (see restart.sh).
    await _log_admin_action(message.from_user.id, "reload")
    await message.answer(
        "🔄 Current configuration (restart the process to apply .env changes):\n"
        f"OPENROUTER_MODEL={config.openrouter_model}\n"
        f"GEMINI_MODEL={config.gemini_model}\n"
        f"GROUP_MODE={config.group_mode}\n"
        f"MAX_HISTORY_MESSAGES={config.max_history_messages}"
    )
