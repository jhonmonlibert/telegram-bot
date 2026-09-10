from __future__ import annotations

from app.config import Config
from app.services.groups import GroupService, VALID_MODES
from app.utils.security import is_admin


def test_is_admin_uses_configured_ids(monkeypatch):
    import app.utils.security as security_module

    monkeypatch.setattr(security_module, "config", Config(admin_telegram_ids=[42]))
    assert security_module.is_admin(42) is True
    assert security_module.is_admin(43) is False


async def test_group_mode_defaults_and_valid_values(test_db):
    service = GroupService(test_db)
    group = await service.get_or_create(-100123, title="Test Group")
    assert group.mode in VALID_MODES

    ok = await service.set_mode(-100123, "always")
    assert ok is True
    updated = await service.get(-100123)
    assert updated.mode == "always"


async def test_group_mode_rejects_invalid_value(test_db):
    service = GroupService(test_db)
    await service.get_or_create(-100999, title="Another Group")
    ok = await service.set_mode(-100999, "not-a-real-mode")
    assert ok is False


async def test_group_enable_disable(test_db):
    service = GroupService(test_db)
    group = await service.get_or_create(-100555, title="G")
    assert group.enabled is True
    await service.set_enabled(-100555, False)
    updated = await service.get(-100555)
    assert updated.enabled is False
