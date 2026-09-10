"""
The actual AI conversation handler for private chats, plus /reset.
"""
from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.config import config
from app.i18n import t
from app.services.ai_manager import AIManagerError, get_ai_manager
from app.services.ai_provider import ChatMessage
from app.services.conversations import ConversationService
from app.services.rate_limit import user_rate_limiter
from app.services.users import User, UserService
from app.utils.security import sanitize_text
from app.utils.text import chunk_text

logger = logging.getLogger(__name__)
router = Router(name="chat")

user_service = UserService()
conversation_service = ConversationService()

STYLE_INSTRUCTIONS = {
    "concise": "Answer briefly and to the point, in a few sentences.",
    "normal": "Answer clearly with a normal, balanced level of detail.",
    "detailed": "Answer thoroughly, with explanations and examples where useful.",
}

BASE_SYSTEM_PROMPT = (
    "You are a helpful, safe AI assistant integrated into a Telegram bot. "
    "You must never reveal API keys, tokens, environment variables, or any "
    "server configuration. You must never execute or simulate executing "
    "shell commands, code on the host machine, or system-level actions. "
    "If asked to do something outside a normal conversational assistant's "
    "scope (e.g. accessing files, running commands, revealing secrets), "
    "politely decline."
)


def _build_system_prompt(user: User) -> str:
    style = STYLE_INSTRUCTIONS.get(user.response_style, STYLE_INSTRUCTIONS["normal"])
    lang_hint = "Respond in Persian (فارسی)." if user.language == "fa" else "Respond in English."
    return f"{BASE_SYSTEM_PROMPT}\n{style}\n{lang_hint}"


@router.message(Command("reset"))
async def cmd_reset(message: Message) -> None:
    user = await user_service.get_or_create(
        message.from_user.id, message.from_user.username, message.from_user.first_name
    )
    await conversation_service.reset("user", message.from_user.id)
    await message.answer(t("reset_done", user.language))


@router.message()
async def on_private_message(message: Message) -> None:
    if message.chat.type != "private":
        return  # group messages are handled by handlers/groups.py
    if not message.text:
        return
    if message.text.startswith("/"):
        return  # unknown command — let aiogram's default handling ignore it

    user = await user_service.get_or_create(
        message.from_user.id, message.from_user.username, message.from_user.first_name
    )

    allowed, _reason = user_rate_limiter.hit(message.from_user.id)
    if not allowed:
        await message.answer(t("rate_limited", user.language))
        return

    text = sanitize_text(message.text, max_length=config.max_message_length)
    if not text:
        return
    if len(message.text) > config.max_message_length:
        await message.answer(t("message_too_long", user.language))

    history: list[ChatMessage] = []
    if user.memory_enabled:
        history = await conversation_service.get_history("user", message.from_user.id)

    messages = [ChatMessage(role="system", content=_build_system_prompt(user))]
    messages.extend(history)
    messages.append(ChatMessage(role="user", content=text))

    thinking_msg = await message.answer(t("thinking", user.language))

    try:
        ai_manager = get_ai_manager()
        response = await ai_manager.chat(messages)
    except AIManagerError as exc:
        logger.warning("AI manager could not produce a response for user %s: %s", message.from_user.id, exc)
        await thinking_msg.edit_text(t("error_generic", user.language))
        return
    except Exception:
        logger.exception("Unexpected error handling private chat message")
        await thinking_msg.edit_text(t("error_generic", user.language))
        return

    if user.memory_enabled:
        await conversation_service.add_message("user", message.from_user.id, "user", text)
        await conversation_service.add_message("user", message.from_user.id, "assistant", response.text)

    chunks = chunk_text(response.text)
    await thinking_msg.edit_text(chunks[0] if chunks else t("error_generic", user.language))
    for chunk in chunks[1:]:
        await message.answer(chunk)
