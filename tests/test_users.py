from __future__ import annotations

from app.services.users import UserService


async def test_get_or_create_creates_new_user(test_db):
    service = UserService(test_db)
    user = await service.get_or_create(12345, username="alice", first_name="Alice")
    assert user.telegram_user_id == 12345
    assert user.username == "alice"
    assert user.memory_enabled is True
    assert user.notifications_enabled is True


async def test_get_or_create_is_idempotent(test_db):
    service = UserService(test_db)
    await service.get_or_create(12345, username="alice")
    await service.get_or_create(12345, username="alice_renamed")
    count = await service.count_all()
    assert count == 1
    user = await service.get(12345)
    assert user.username == "alice_renamed"


async def test_settings_toggles(test_db):
    service = UserService(test_db)
    await service.get_or_create(999)
    await service.set_language(999, "en")
    await service.set_memory_enabled(999, False)
    await service.set_notifications_enabled(999, False)
    await service.set_response_style(999, "concise")

    user = await service.get(999)
    assert user.language == "en"
    assert user.memory_enabled is False
    assert user.notifications_enabled is False
    assert user.response_style == "concise"


async def test_list_notifiable_excludes_opted_out_and_blocked(test_db):
    service = UserService(test_db)
    await service.get_or_create(1)
    await service.get_or_create(2)
    await service.get_or_create(3)
    await service.set_notifications_enabled(2, False)
    await service.set_blocked(3, True)

    notifiable_ids = {u.telegram_user_id for u in await service.list_notifiable()}
    assert notifiable_ids == {1}
