"""
Main / private-chat keyboards.
"""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.i18n import t


def main_menu_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_chat", lang), callback_data="menu:chat")],
            [
                InlineKeyboardButton(text=t("btn_settings", lang), callback_data="menu:settings"),
                InlineKeyboardButton(text=t("btn_reset", lang), callback_data="menu:reset"),
            ],
            [InlineKeyboardButton(text=t("btn_help", lang), callback_data="menu:help")],
        ]
    )
