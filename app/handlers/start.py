"""
Basic private-chat commands: /start, /help, /status, /id, /about, and the
callback handlers for the main menu's inline keyboard.
"""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app import __version__ as APP_VERSION
from app.config import config
from app.i18n import t
from app.keyboards.main import main_menu_keyboard
from app.services.conversations import ConversationService
from app.services.users import UserService
from app.utils.security import is_valid_callback_data

logger = logging.getLogger(__name__)
router = Router(name="start")

user_service = UserService()
conversation_service = ConversationService()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    user = await user_service.get_or_create(
        telegram_user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    await message.answer(t("welcome", user.language), reply_markup=main_menu_keyboard(user.language))


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    user = await user_service.get_or_create(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await message.answer(t("help", user.language))


@router.message(Command("about"))
async def cmd_about(message: Message) -> None:
    user = await user_service.get_or_create(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await message.answer(t("about", user.language))


@router.message(Command("id"))
async def cmd_id(message: Message) -> None:
    await message.answer(
        f"👤 Your Telegram ID: `{message.from_user.id}`\n💬 This chat ID: `{message.chat.id}`",
        parse_mode="Markdown",
    )


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    user = await user_service.get_or_create(message.from_user.id, message.from_user.username, message.from_user.first_name)
    status_lines = [
        f"Language: {user.language}",
        f"Model: {user.selected_model or config.openrouter_model}",
        f"Memory: {'ON' if user.memory_enabled else 'OFF'}",
        f"Notifications: {'ON' if user.notifications_enabled else 'OFF'}",
        f"Response style: {user.response_style}",
        f"Bot version: {APP_VERSION}",
    ]
    await message.answer("📊 Status\n" + "\n".join(status_lines))


@router.callback_query(F.data.startswith("menu:"))
async def on_menu_callback(callback: CallbackQuery) -> None:
    if not is_valid_callback_data(callback.data):
        await callback.answer()
        return

    action = callback.data.split(":", 1)[1]
    user = await user_service.get_or_create(
        callback.from_user.id, callback.from_user.username, callback.from_user.first_name
    )

    if action == "help":
        await callback.message.answer(t("help", user.language))
    elif action == "reset":
        await conversation_service.reset("user", callback.from_user.id)
        await callback.message.answer(t("reset_done", user.language))
    elif action == "settings":
        from app.handlers.settings import send_settings_menu

        await send_settings_menu(callback.message, user)
    elif action == "chat":
        prompt = "پیام خودتون رو بفرستید 💬" if user.language == "fa" else "Send me your message 💬"
        await callback.message.answer(prompt)

    await callback.answer()
