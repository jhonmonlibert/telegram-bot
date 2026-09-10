from __future__ import annotations

import asyncio
import os
import tempfile

import pytest

# Ensure a clean, isolated environment before app.config is imported by any test.
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("OPENROUTER_API_KEY", "test-openrouter-key")
os.environ.setdefault("GEMINI_API_KEY", "")
os.environ.setdefault("ADMIN_TELEGRAM_IDS", "111,222")

from app.database.db import Database  # noqa: E402
from app.database.migrations import run_migrations  # noqa: E402


@pytest.fixture
async def test_db():
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = os.path.join(tmp_dir, "test.db")
        database = Database(path)
        await database.connect()
        await run_migrations(database)
        yield database
        await database.close()
