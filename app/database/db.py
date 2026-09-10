"""
Thin async SQLite wrapper (aiosqlite) with a single shared connection,
WAL mode, and a small helper API used by every service module.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

import aiosqlite

from app.config import config

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, path: str | None = None):
        self.path = path or config.database_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        db_path = Path(self.path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL;")
        await self._conn.execute("PRAGMA synchronous=NORMAL;")
        await self._conn.execute("PRAGMA foreign_keys=ON;")
        await self._conn.commit()
        logger.info("Connected to SQLite database at %s", self.path)

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
            logger.info("Database connection closed")

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database is not connected. Call connect() first.")
        return self._conn

    async def execute(self, query: str, params: Sequence[Any] = ()) -> aiosqlite.Cursor:
        cur = await self.conn.execute(query, params)
        await self.conn.commit()
        return cur

    async def executemany(self, query: str, params_seq: Iterable[Sequence[Any]]) -> None:
        await self.conn.executemany(query, params_seq)
        await self.conn.commit()

    async def fetchone(self, query: str, params: Sequence[Any] = ()) -> Optional[aiosqlite.Row]:
        cur = await self.conn.execute(query, params)
        row = await cur.fetchone()
        await cur.close()
        return row

    async def fetchall(self, query: str, params: Sequence[Any] = ()) -> list[aiosqlite.Row]:
        cur = await self.conn.execute(query, params)
        rows = await cur.fetchall()
        await cur.close()
        return list(rows)


# Module-level singleton used across the app.
db = Database()
