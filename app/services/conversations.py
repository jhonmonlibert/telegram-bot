"""
Lightweight, size-bounded conversation memory backed by SQLite.

Only the last `MAX_HISTORY_MESSAGES` user/assistant turns are kept per
conversation; older ones are pruned so the table (and the prompt sent to
the AI provider) never grows unbounded.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.config import config
from app.database.db import Database, db
from app.services.ai_provider import ChatMessage

OwnerType = Literal["user", "group"]


@dataclass
class StoredMessage:
    role: str
    content: str
    created_at: str


class ConversationService:
    def __init__(self, database: Database | None = None, max_history_messages: int | None = None) -> None:
        self.db = database or db
        self.max_history_messages = (
            max_history_messages if max_history_messages is not None else config.max_history_messages
        )

    async def _get_or_create_conversation_id(self, owner_type: OwnerType, owner_id: int) -> int:
        row = await self.db.fetchone(
            "SELECT id FROM conversations WHERE owner_type = ? AND owner_id = ?",
            (owner_type, owner_id),
        )
        if row is not None:
            return row["id"]
        cur = await self.db.execute(
            "INSERT INTO conversations (owner_type, owner_id) VALUES (?, ?)",
            (owner_type, owner_id),
        )
        return cur.lastrowid

    async def add_message(self, owner_type: OwnerType, owner_id: int, role: str, content: str) -> None:
        conversation_id = await self._get_or_create_conversation_id(owner_type, owner_id)
        await self.db.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, role, content),
        )
        await self.db.execute(
            "UPDATE conversations SET updated_at = datetime('now') WHERE id = ?", (conversation_id,)
        )
        await self._prune(conversation_id)

    async def _prune(self, conversation_id: int) -> None:
        limit = self.max_history_messages
        rows = await self.db.fetchall(
            "SELECT id FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT -1 OFFSET ?",
            (conversation_id, limit),
        )
        if not rows:
            return
        ids = [r["id"] for r in rows]
        placeholders = ",".join("?" for _ in ids)
        await self.db.execute(
            f"DELETE FROM messages WHERE id IN ({placeholders})", tuple(ids)
        )

    async def get_history(self, owner_type: OwnerType, owner_id: int) -> list[ChatMessage]:
        row = await self.db.fetchone(
            "SELECT id FROM conversations WHERE owner_type = ? AND owner_id = ?",
            (owner_type, owner_id),
        )
        if row is None:
            return []
        rows = await self.db.fetchall(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id ASC",
            (row["id"],),
        )
        return [ChatMessage(role=r["role"], content=r["content"]) for r in rows]

    async def reset(self, owner_type: OwnerType, owner_id: int) -> None:
        row = await self.db.fetchone(
            "SELECT id FROM conversations WHERE owner_type = ? AND owner_id = ?",
            (owner_type, owner_id),
        )
        if row is None:
            return
        await self.db.execute("DELETE FROM messages WHERE conversation_id = ?", (row["id"],))
