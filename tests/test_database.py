from __future__ import annotations

import pytest


async def test_all_tables_created(test_db):
    rows = await test_db.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
    names = {r["name"] for r in rows}
    expected = {"users", "groups", "conversations", "messages", "settings", "usage", "admin_actions"}
    assert expected.issubset(names)


async def test_wal_mode_enabled(test_db):
    row = await test_db.fetchone("PRAGMA journal_mode;")
    assert row[0].lower() == "wal"


async def test_migrations_are_idempotent(test_db):
    from app.database.migrations import run_migrations

    # Running twice must not raise.
    await run_migrations(test_db)
    await run_migrations(test_db)
