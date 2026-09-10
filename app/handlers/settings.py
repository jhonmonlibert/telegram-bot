"""
/settings and /model, plus the callback handlers behind the settings
inline keyboard (language, memory toggle, notifications toggle, style,
and model selection).
"""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.config import config
from app.i18n import t
from app.keyboards.settings import settings_keyboard
from app.services.users import User, UserService
from app.utils.security import is_valid_callback_data

logger = logging.getLogger(__name__)
router = Router(name="settings")

user_service = UserService()

# A small, safe list of suggested models. The admin can still set any
# OPENROUTER_MODEL via .env; this is just a convenience picker.
SUGGESTED_MODELS = [
    "openrouter/free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
    "mistralai/mistral-7b-instruct:free",
]


async def send_settings_menu(message: Message, user: User) -> None:
    text = "⚙️ Settings" if user.language == "en" else "⚙️ تنظیمات"
    await message.answer(text, reply_markup=settings_keyboard(user))


@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    user = await user_service.get_or_create(
        message.from_user.id, message.from_user.username, message.from_user.first_name
    )
    await send_settings_menu(message, user)


@router.message(Command("model"))
async def cmd_model(message: Message) -> None:
    user = await user_service.get_or_create(
        message.from_user.id, message.from_user.username, message.from_user.first_name
    )
    current = user.selected_model or config.openrouter_model
    buttons = [
        [InlineKeyboardButton(text=("✅ " if m == current else "") + m, callback_data=f"model:{i}")]
        for i, m in enumerate(SUGGESTED_MODELS)
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    label = f"Current model: {current}\nChoose a model:" if user.language == "en" else f"مدل فعلی: {current}\nیک مدل انتخاب کنید:"
    await message.answer(label, reply_markup=kb)


@router.callback_query(F.data.startswith("model:"))
async def on_model_callback(callback: CallbackQuery) -> None:
    if not is_valid_callback_data(callback.data):
        await callback.answer()
        return
    try:
        index = int(callback.data.split(":", 1)[1])
        model = SUGGESTED_MODELS[index]
    except (ValueError, IndexError):
        await callback.answer("Invalid selection", show_alert=True)
        return

    await user_service.set_model(callback.from_user.id, model)
    await callback.answer(f"Model set to {model}")
    await callback.message.edit_text(f"✅ Model updated: {model}")


@router.callback_query(F.data.startswith("lang:"))
async def on_language_callback(callback: CallbackQuery) -> None:
    if not is_valid_callback_data(callback.data):
        await callback.answer()
        return
    lang = callback.data.split(":", 1)[1]
    if lang not in ("fa", "en"):
        await callback.answer()
        return
    await user_service.set_language(callback.from_user.id, lang)
    user = await user_service.get(callback.from_user.id)
    await callback.answer("✅")
    await callback.message.edit_text(
        "⚙️ Settings" if lang == "en" else "⚙️ تنظیمات", reply_markup=settings_keyboard(user)
    )


@router.callback_query(F.data == "toggle:memory")
async def on_toggle_memory(callback: CallbackQuery) -> None:
    user = await user_service.get_or_create(
        callback.from_user.id, callback.from_user.username, callback.from_user.first_name
    )
    await user_service.set_memory_enabled(callback.from_user.id, not user.memory_enabled)
    user = await user_service.get(callback.from_user.id)
    await callback.answer("✅")
    await callback.message.edit_reply_markup(reply_markup=settings_keyboard(user))


@router.callback_query(F.data == "toggle:notifications")
async def on_toggle_notifications(callback: CallbackQuery) -> None:
    user = await user_service.get_or_create(
        callback.from_user.id, callback.from_user.username, callback.from_user.first_name
    )
    await user_service.set_notifications_enabled(callback.from_user.id, not user.notifications_enabled)
    user = await user_service.get(callback.from_user.id)
    await callback.answer("✅")
    await callback.message.edit_reply_markup(reply_markup=settings_keyboard(user))


@router.callback_query(F.data.startswith("style:"))
async def on_style_callback(callback: CallbackQuery) -> None:
    if not is_valid_callback_data(callback.data):
        await callback.answer()
        return
    style = callback.data.split(":", 1)[1]
    if style not in ("concise", "normal", "detailed"):
        await callback.answer()
        return
    await user_service.set_response_style(callback.from_user.id, style)
    await callback.answer(f"Style set to {style}")
