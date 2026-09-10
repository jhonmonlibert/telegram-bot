"""
Settings-related keyboards.
"""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def settings_keyboard(user) -> InlineKeyboardMarkup:
    memory_label = "🧠 Memory: ON" if user.memory_enabled else "🧠 Memory: OFF"
    notif_label = "🔔 Notifications: ON" if user.notifications_enabled else "🔕 Notifications: OFF"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇮🇷 فارسی", callback_data="lang:fa"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
            ],
            [InlineKeyboardButton(text=memory_label, callback_data="toggle:memory")],
            [InlineKeyboardButton(text=notif_label, callback_data="toggle:notifications")],
            [
                InlineKeyboardButton(text="Concise", callback_data="style:concise"),
                InlineKeyboardButton(text="Normal", callback_data="style:normal"),
                InlineKeyboardButton(text="Detailed", callback_data="style:detailed"),
            ],
        ]
    )


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇮🇷 فارسی", callback_data="lang:fa"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
            ]
        ]
    )
