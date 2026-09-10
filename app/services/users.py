"""
User persistence and preference management.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.config import config
from app.database.db import Database, db


@dataclass
class User:
    id: int
    telegram_user_id: int
    username: Optional[str]
    first_name: Optional[str]
    language: str
    selected_model: Optional[str]
    memory_enabled: bool
    notifications_enabled: bool
    response_style: str
    is_blocked: bool
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row) -> "User":
        return cls(
            id=row["id"],
            telegram_user_id=row["telegram_user_id"],
            username=row["username"],
            first_name=row["first_name"],
            language=row["language"],
            selected_model=row["selected_model"],
            memory_enabled=bool(row["memory_enabled"]),
            notifications_enabled=bool(row["notifications_enabled"]),
            response_style=row["response_style"],
            is_blocked=bool(row["is_blocked"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class UserService:
    def __init__(self, database: Database | None = None) -> None:
        self.db = database or db

    async def get_or_create(
        self, telegram_user_id: int, username: Optional[str] = None, first_name: Optional[str] = None
    ) -> User:
        row = await self.db.fetchone(
            "SELECT * FROM users WHERE telegram_user_id = ?", (telegram_user_id,)
        )
        if row is not None:
            # Keep username/first_name fresh.
            await self.db.execute(
                """UPDATE users SET username = ?, first_name = ?, updated_at = datetime('now')
                   WHERE telegram_user_id = ?""",
                (username, first_name, telegram_user_id),
            )
            row = await self.db.fetchone(
                "SELECT * FROM users WHERE telegram_user_id = ?", (telegram_user_id,)
            )
            return User.from_row(row)

        await self.db.execute(
            """INSERT INTO users (telegram_user_id, username, first_name, language, selected_model)
               VALUES (?, ?, ?, ?, ?)""",
            (telegram_user_id, username, first_name, config.default_language, config.openrouter_model),
        )
        row = await self.db.fetchone(
            "SELECT * FROM users WHERE telegram_user_id = ?", (telegram_user_id,)
        )
        return User.from_row(row)

    async def get(self, telegram_user_id: int) -> Optional[User]:
        row = await self.db.fetchone(
            "SELECT * FROM users WHERE telegram_user_id = ?", (telegram_user_id,)
        )
        return User.from_row(row) if row else None

    async def set_language(self, telegram_user_id: int, language: str) -> None:
        await self.db.execute(
            "UPDATE users SET language = ?, updated_at = datetime('now') WHERE telegram_user_id = ?",
            (language, telegram_user_id),
        )

    async def set_model(self, telegram_user_id: int, model: str) -> None:
        await self.db.execute(
            "UPDATE users SET selected_model = ?, updated_at = datetime('now') WHERE telegram_user_id = ?",
            (model, telegram_user_id),
        )

    async def set_memory_enabled(self, telegram_user_id: int, enabled: bool) -> None:
        await self.db.execute(
            "UPDATE users SET memory_enabled = ?, updated_at = datetime('now') WHERE telegram_user_id = ?",
            (int(enabled), telegram_user_id),
        )

    async def set_notifications_enabled(self, telegram_user_id: int, enabled: bool) -> None:
        await self.db.execute(
            "UPDATE users SET notifications_enabled = ?, updated_at = datetime('now') WHERE telegram_user_id = ?",
            (int(enabled), telegram_user_id),
        )

    async def set_response_style(self, telegram_user_id: int, style: str) -> None:
        await self.db.execute(
            "UPDATE users SET response_style = ?, updated_at = datetime('now') WHERE telegram_user_id = ?",
            (style, telegram_user_id),
        )

    async def set_blocked(self, telegram_user_id: int, blocked: bool) -> None:
        await self.db.execute(
            "UPDATE users SET is_blocked = ?, updated_at = datetime('now') WHERE telegram_user_id = ?",
            (int(blocked), telegram_user_id),
        )

    async def count_all(self) -> int:
        row = await self.db.fetchone("SELECT COUNT(*) AS c FROM users")
        return row["c"] if row else 0

    async def list_notifiable(self) -> list[User]:
        """Users who have started the bot and not opted out — the only
        valid targets for /broadcast."""
        rows = await self.db.fetchall(
            "SELECT * FROM users WHERE notifications_enabled = 1 AND is_blocked = 0"
        )
        return [User.from_row(r) for r in rows]

    async def list_all(self, limit: int = 50, offset: int = 0) -> list[User]:
        rows = await self.db.fetchall(
            "SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)
        )
        return [User.from_row(r) for r in rows]
