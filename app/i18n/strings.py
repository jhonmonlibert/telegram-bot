"""
Minimal i18n: a nested dict of strings for 'fa' and 'en'. Not a full
gettext setup on purpose — keeps the dependency footprint at zero.
"""
from __future__ import annotations

STRINGS: dict[str, dict[str, str]] = {
    "welcome": {
        "fa": (
            "🤖 دستیار هوشمند\n\n"
            "می‌تونم در این موارد کمکتون کنم:\n"
            "• پاسخ به سوالات\n"
            "• برنامه‌نویسی\n"
            "• ترجمه\n"
            "• خلاصه‌سازی\n"
            "• ایده‌پردازی\n"
            "• کمک عمومی\n\n"
            "پیام‌تون رو بفرستید تا شروع کنیم."
        ),
        "en": (
            "🤖 AI Assistant\n\n"
            "I can help you with:\n"
            "• Questions\n"
            "• Programming\n"
            "• Translation\n"
            "• Summaries\n"
            "• Ideas\n"
            "• General assistance\n\n"
            "Send me a message to get started."
        ),
    },
    "btn_chat": {"fa": "💬 گفتگو", "en": "💬 Chat"},
    "btn_settings": {"fa": "⚙️ تنظیمات", "en": "⚙️ Settings"},
    "btn_reset": {"fa": "🧹 پاک‌سازی", "en": "🧹 Reset"},
    "btn_help": {"fa": "ℹ️ راهنما", "en": "ℹ️ Help"},
    "help": {
        "fa": (
            "دستورات:\n"
            "/start - شروع\n"
            "/help - راهنما\n"
            "/settings - تنظیمات\n"
            "/model - انتخاب مدل\n"
            "/reset - پاک‌سازی حافظه گفتگو\n"
            "/status - وضعیت\n"
            "/id - نمایش شناسه شما\n"
            "/about - درباره ربات\n\n"
            "در گروه‌ها:\n"
            "/ask <سوال>\n"
            "/summarize، /translate، /explain\n"
            "یا با ریپلای/منشن به ربات صحبت کنید."
        ),
        "en": (
            "Commands:\n"
            "/start - start\n"
            "/help - help\n"
            "/settings - settings\n"
            "/model - choose a model\n"
            "/reset - clear conversation memory\n"
            "/status - status\n"
            "/id - show your Telegram ID\n"
            "/about - about this bot\n\n"
            "In groups:\n"
            "/ask <question>\n"
            "/summarize, /translate, /explain\n"
            "or mention/reply to the bot."
        ),
    },
    "reset_done": {"fa": "✅ حافظه گفتگو پاک شد.", "en": "✅ Conversation memory cleared."},
    "about": {
        "fa": "🤖 دستیار هوشمند تلگرام — مبتنی بر OpenRouter با پشتیبان Gemini، سبک و مناسب اجرای ۲۴/۷.",
        "en": "🤖 Telegram AI Assistant — powered by OpenRouter with a Gemini fallback, lightweight and built for 24/7 operation.",
    },
    "error_generic": {
        "fa": "⚠️ متاسفانه در حال حاضر مشکلی پیش آمده. لطفاً کمی بعد دوباره امتحان کنید.",
        "en": "⚠️ Something went wrong on our end. Please try again in a moment.",
    },
    "rate_limited": {
        "fa": "⏳ شما درخواست‌های زیادی ارسال کرده‌اید. لطفاً کمی صبر کنید.",
        "en": "⏳ You're sending requests too quickly. Please wait a bit.",
    },
    "message_too_long": {
        "fa": "✂️ پیام شما خیلی طولانی است. لطفاً کوتاه‌ترش کنید.",
        "en": "✂️ Your message is too long. Please shorten it.",
    },
    "not_admin": {
        "fa": "⛔️ این دستور فقط برای مدیران است.",
        "en": "⛔️ This command is for admins only.",
    },
    "not_group_admin": {
        "fa": "⛔️ فقط مدیران گروه می‌توانند تنظیمات را تغییر دهند.",
        "en": "⛔️ Only group administrators can change settings.",
    },
    "thinking": {"fa": "🤔 در حال فکر کردن...", "en": "🤔 Thinking..."},
}


def t(key: str, lang: str = "en") -> str:
    entry = STRINGS.get(key)
    if not entry:
        return key
    return entry.get(lang) or entry.get("en") or key
