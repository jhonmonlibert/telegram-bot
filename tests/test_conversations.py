from __future__ import annotations

from app.services.conversations import ConversationService


async def test_add_and_get_history(test_db):
    service = ConversationService(test_db)
    await service.add_message("user", 1, "user", "hello")
    await service.add_message("user", 1, "assistant", "hi there")

    history = await service.get_history("user", 1)
    assert [m.role for m in history] == ["user", "assistant"]
    assert history[0].content == "hello"


async def test_history_is_pruned_to_max_messages(test_db):
    service = ConversationService(test_db, max_history_messages=4)
    for i in range(10):
        await service.add_message("user", 2, "user", f"msg-{i}")

    history = await service.get_history("user", 2)
    assert len(history) == 4
    # The most recent messages must be the ones kept.
    assert history[-1].content == "msg-9"


async def test_reset_clears_history(test_db):
    service = ConversationService(test_db)
    await service.add_message("user", 3, "user", "hello")
    await service.reset("user", 3)
    history = await service.get_history("user", 3)
    assert history == []


async def test_reset_on_nonexistent_conversation_is_noop(test_db):
    service = ConversationService(test_db)
    # Should not raise even though owner 999 never had a conversation.
    await service.reset("user", 999)
