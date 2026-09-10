"""
Group chat behaviour.

The bot never blindly reads every group message. Depending on the
group's configured mode it only reacts to:
  - "mention": being @mentioned or replied to
  - "command": explicit commands (/ask, /summarize, ...)
  - "always": every normal message (opt-in, admin-enabled only)
"""
from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.enums import ChatMemberStatus
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.config import config
from app.services.ai_manager import AIManagerError, get_ai_manager
from app.services.ai_provider import ChatMessage
from app.services.conversations import ConversationService
from app.services.groups import GroupService, VALID_MODES
from app.services.rate_limit import group_rate_limiter
from app.utils.security import is_valid_callback_data, sanitize_text
from app.utils.text import chunk_text

logger = logging.getLogger(__name__)
router = Router(name="groups")

group_service = GroupService()
conversation_service = ConversationService()

GROUP_SYSTEM_PROMPT = (
    "You are a helpful AI assistant participating in a Telegram group chat. "
    "Keep answers concise and relevant to the group discussion. Never reveal "
    "API keys, tokens, or server configuration, and never execute commands "
    "or code on the host system."
)


async def _is_group_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    if config.is_admin(user_id):
        return True
    try:
        member = await bot.get_chat_member(chat_id, user_id)
    except Exception:
        return False
    return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR)


def _is_bot_mentioned(message: Message, bot_username: str | None) -> bool:
    if not message.text or not bot_username:
        return False
    return f"@{bot_username.lower()}" in message.text.lower()


def _is_reply_to_bot(message: Message, bot_id: int) -> bool:
    return bool(
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == bot_id
    )


def _strip_mention(text: str, bot_username: str | None) -> str:
    if bot_username:
        text = text.replace(f"@{bot_username}", "").replace(f"@{bot_username.lower()}", "")
    return text.strip()


async def _run_ai_and_reply(message: Message, chat_id: int, prompt: str, extra_context: str | None = None) -> None:
    allowed, _reason = group_rate_limiter.hit(chat_id)
    if not allowed:
        await message.reply("⏳ Too many requests in this group right now. Please wait a bit.")
        return

    text = sanitize_text(prompt, max_length=config.max_message_length)
    if not text:
        return

    history = await conversation_service.get_history("group", chat_id)
    messages = [ChatMessage(role="system", content=GROUP_SYSTEM_PROMPT)]
    if extra_context:
        messages.append(ChatMessage(role="system", content=extra_context))
    messages.extend(history[-6:])  # keep group context short
    messages.append(ChatMessage(role="user", content=text))

    try:
        ai_manager = get_ai_manager()
        response = await ai_manager.chat(messages)
    except AIManagerError:
        await message.reply("⚠️ AI service is temporarily unavailable. Please try again shortly.")
        return
    except Exception:
        logger.exception("Unexpected error handling group AI request in chat %s", chat_id)
        await message.reply("⚠️ Something went wrong. Please try again shortly.")
        return

    await conversation_service.add_message("group", chat_id, "user", text)
    await conversation_service.add_message("group", chat_id, "assistant", response.text)

    for chunk in chunk_text(response.text):
        await message.reply(chunk)


@router.message(Command("ask"))
async def cmd_ask(message: Message, command: CommandObject) -> None:
    if message.chat.type not in ("group", "supergroup"):
        return
    await group_service.get_or_create(message.chat.id, message.chat.title)
    question = (command.args or "").strip()
    if not question:
        await message.reply("Usage: /ask <question>")
        return
    await _run_ai_and_reply(message, message.chat.id, question)


@router.message(Command("summarize"))
async def cmd_summarize(message: Message) -> None:
    if message.chat.type not in ("group", "supergroup"):
        return
    await group_service.get_or_create(message.chat.id, message.chat.title)
    await _run_ai_and_reply(
        message,
        message.chat.id,
        "Summarize the recent discussion in this group based on the conversation context provided.",
    )


@router.message(Command("translate"))
async def cmd_translate(message: Message, command: CommandObject) -> None:
    if message.chat.type not in ("group", "supergroup"):
        return
    await group_service.get_or_create(message.chat.id, message.chat.title)
    target = message.reply_to_message.text if message.reply_to_message else (command.args or "")
    target = (target or "").strip()
    if not target:
        await message.reply("Reply to a message or use: /translate <text>")
        return
    await _run_ai_and_reply(message, message.chat.id, f"Translate the following text:\n{target}")


@router.message(Command("explain"))
async def cmd_explain(message: Message, command: CommandObject) -> None:
    if message.chat.type not in ("group", "supergroup"):
        return
    await group_service.get_or_create(message.chat.id, message.chat.title)
    target = message.reply_to_message.text if message.reply_to_message else (command.args or "")
    target = (target or "").strip()
    if not target:
        await message.reply("Reply to a message or use: /explain <text>")
        return
    await _run_ai_and_reply(message, message.chat.id, f"Explain the following in simple terms:\n{target}")


@router.message(Command("group_settings"))
async def cmd_group_settings(message: Message, bot: Bot) -> None:
    if message.chat.type not in ("group", "supergroup"):
        return
    if not await _is_group_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("⛔️ Only group administrators can change settings.")
        return

    group = await group_service.get_or_create(message.chat.id, message.chat.title)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=("✅ " if group.mode == m else "") + m, callback_data=f"gmode:{message.chat.id}:{m}"
                )
                for m in VALID_MODES
            ],
            [
                InlineKeyboardButton(
                    text="🔴 Disable bot" if group.enabled else "🟢 Enable bot",
                    callback_data=f"gtoggle:{message.chat.id}",
                )
            ],
        ]
    )
    await message.reply(
        f"⚙️ Group settings for {message.chat.title or message.chat.id}\nCurrent mode: {group.mode}\nEnabled: {group.enabled}",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("gmode:"))
async def on_group_mode_callback(callback, bot: Bot) -> None:
    if not is_valid_callback_data(callback.data):
        await callback.answer()
        return
    _, chat_id_str, mode = callback.data.split(":", 2)
    chat_id = int(chat_id_str)
    if not await _is_group_admin(bot, chat_id, callback.from_user.id):
        await callback.answer("Admins only", show_alert=True)
        return
    ok = await group_service.set_mode(chat_id, mode)
    if ok:
        await callback.answer(f"Mode set to {mode}")
        await callback.message.edit_text(f"⚙️ Group mode updated to: {mode}")
    else:
        await callback.answer("Invalid mode", show_alert=True)


@router.callback_query(F.data.startswith("gtoggle:"))
async def on_group_toggle_callback(callback, bot: Bot) -> None:
    if not is_valid_callback_data(callback.data):
        await callback.answer()
        return
    chat_id = int(callback.data.split(":", 1)[1])
    if not await _is_group_admin(bot, chat_id, callback.from_user.id):
        await callback.answer("Admins only", show_alert=True)
        return
    group = await group_service.get(chat_id)
    if group is None:
        await callback.answer()
        return
    await group_service.set_enabled(chat_id, not group.enabled)
    await callback.answer("✅")
    await callback.message.edit_text(f"⚙️ Bot enabled: {not group.enabled}")


@router.message(F.text & F.chat.type.in_({"group", "supergroup"}))
async def on_group_message(message: Message, bot: Bot) -> None:
    """Free-form group messages, gated by the group's configured mode."""
    if message.text.startswith("/"):
        return  # commands are handled by their own dedicated handlers

    group = await group_service.get_or_create(message.chat.id, message.chat.title)
    if not group.enabled:
        return

    bot_username = (await bot.get_me()).username
    mentioned = _is_bot_mentioned(message, bot_username)
    replied_to_bot = _is_reply_to_bot(message, bot.id)

    if group.mode == "command":
        return  # only slash commands are handled in this mode
    if group.mode == "mention" and not (mentioned or replied_to_bot):
        return
    if group.mode == "always":
        pass  # falls through and processes every message, by design (admin opt-in)
    elif not (mentioned or replied_to_bot):
        return

    text = _strip_mention(message.text, bot_username)
    if not text:
        return
    await _run_ai_and_reply(message, message.chat.id, text)
