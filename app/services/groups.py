"""
Group persistence and per-group configuration (mode, language, enabled).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.config import config
from app.database.db import Database, db

VALID_MODES = ("mention", "command", "always")


@dataclass
class Group:
    id: int
    chat_id: int
    title: Optional[str]
    mode: str
    language: str
    enabled: bool
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row) -> "Group":
        return cls(
            id=row["id"],
            chat_id=row["chat_id"],
            title=row["title"],
            mode=row["mode"],
            language=row["language"],
            enabled=bool(row["enabled"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class GroupService:
    def __init__(self, database: Database | None = None) -> None:
        self.db = database or db

    async def get_or_create(self, chat_id: int, title: Optional[str] = None) -> Group:
        row = await self.db.fetchone("SELECT * FROM groups WHERE chat_id = ?", (chat_id,))
        if row is not None:
            if title:
                await self.db.execute(
                    "UPDATE groups SET title = ?, updated_at = datetime('now') WHERE chat_id = ?",
                    (title, chat_id),
                )
                row = await self.db.fetchone("SELECT * FROM groups WHERE chat_id = ?", (chat_id,))
            return Group.from_row(row)

        await self.db.execute(
            "INSERT INTO groups (chat_id, title, mode, language, enabled) VALUES (?, ?, ?, ?, 1)",
            (chat_id, title, config.group_mode, config.default_language),
        )
        row = await self.db.fetchone("SELECT * FROM groups WHERE chat_id = ?", (chat_id,))
        return Group.from_row(row)

    async def get(self, chat_id: int) -> Optional[Group]:
        row = await self.db.fetchone("SELECT * FROM groups WHERE chat_id = ?", (chat_id,))
        return Group.from_row(row) if row else None

    async def set_mode(self, chat_id: int, mode: str) -> bool:
        if mode not in VALID_MODES:
            return False
        await self.db.execute(
            "UPDATE groups SET mode = ?, updated_at = datetime('now') WHERE chat_id = ?",
            (mode, chat_id),
        )
        return True

    async def set_language(self, chat_id: int, language: str) -> None:
        await self.db.execute(
            "UPDATE groups SET language = ?, updated_at = datetime('now') WHERE chat_id = ?",
            (language, chat_id),
        )

    async def set_enabled(self, chat_id: int, enabled: bool) -> None:
        await self.db.execute(
            "UPDATE groups SET enabled = ?, updated_at = datetime('now') WHERE chat_id = ?",
            (int(enabled), chat_id),
        )

    async def count_all(self) -> int:
        row = await self.db.fetchone("SELECT COUNT(*) AS c FROM groups")
        return row["c"] if row else 0

    async def list_all(self, limit: int = 50, offset: int = 0) -> list[Group]:
        rows = await self.db.fetchall(
            "SELECT * FROM groups ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)
        )
        return [Group.from_row(r) for r in rows]
