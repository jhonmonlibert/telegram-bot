from __future__ import annotations

import pytest

from app.services.ai_manager import AIManager, AIManagerError
from app.services.ai_provider import (
    AIProvider,
    AIProviderAuthError,
    AIProviderRateLimited,
    AIProviderUnavailable,
    AIResponse,
    ChatMessage,
)


class FakeProvider(AIProvider):
    def __init__(self, name: str, *, should_fail: Exception | None = None, reply_text: str = "ok"):
        self.name = name
        self.should_fail = should_fail
        self.reply_text = reply_text
        self.called = False

    async def chat(self, messages, *, temperature, max_tokens):
        self.called = True
        if self.should_fail:
            raise self.should_fail
        return AIResponse(text=self.reply_text, provider=self.name, model="fake-model")


@pytest.fixture
def messages():
    return [ChatMessage(role="user", content="hello")]


async def test_uses_primary_when_it_succeeds(messages):
    primary = FakeProvider("openrouter", reply_text="primary reply")
    fallback = FakeProvider("gemini", reply_text="fallback reply")
    manager = AIManager(primary=primary, fallback=fallback)

    response = await manager.chat(messages)

    assert response.text == "primary reply"
    assert response.provider == "openrouter"
    assert fallback.called is False


async def test_falls_back_to_gemini_when_primary_unavailable(messages):
    primary = FakeProvider("openrouter", should_fail=AIProviderUnavailable("down"))
    fallback = FakeProvider("gemini", reply_text="fallback reply")
    manager = AIManager(primary=primary, fallback=fallback)

    response = await manager.chat(messages)

    assert response.text == "fallback reply"
    assert response.provider == "gemini"
    assert primary.called is True
    assert fallback.called is True


async def test_falls_back_on_rate_limit(messages):
    primary = FakeProvider("openrouter", should_fail=AIProviderRateLimited("rate limited"))
    fallback = FakeProvider("gemini", reply_text="fallback reply")
    manager = AIManager(primary=primary, fallback=fallback)

    response = await manager.chat(messages)
    assert response.provider == "gemini"


async def test_falls_back_on_auth_error(messages):
    primary = FakeProvider("openrouter", should_fail=AIProviderAuthError("bad key"))
    fallback = FakeProvider("gemini", reply_text="fallback reply")
    manager = AIManager(primary=primary, fallback=fallback)

    response = await manager.chat(messages)
    assert response.provider == "gemini"


async def test_raises_safe_error_when_no_fallback_configured(messages):
    primary = FakeProvider("openrouter", should_fail=AIProviderUnavailable("down"))
    manager = AIManager(primary=primary, fallback=None, fallback_enabled=False)

    with pytest.raises(AIManagerError):
        await manager.chat(messages)


async def test_raises_safe_error_when_both_providers_fail(messages):
    primary = FakeProvider("openrouter", should_fail=AIProviderUnavailable("down"))
    fallback = FakeProvider("gemini", should_fail=AIProviderUnavailable("also down"))
    manager = AIManager(primary=primary, fallback=fallback)

    with pytest.raises(AIManagerError):
        await manager.chat(messages)
