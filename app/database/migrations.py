"""
Very small "migration" system: on startup we just make sure every table
from models.SCHEMA_STATEMENTS exists. SQLite's CREATE TABLE IF NOT EXISTS
makes this idempotent and safe to run on every boot.
"""
from __future__ import annotations

import logging

from app.database.db import Database
from app.database.models import SCHEMA_STATEMENTS

logger = logging.getLogger(__name__)


async def run_migrations(database: Database) -> None:
    for statement in SCHEMA_STATEMENTS:
        await database.conn.execute(statement)
    await database.conn.commit()
    logger.info("Database schema is up to date (%d statements applied)", len(SCHEMA_STATEMENTS))
