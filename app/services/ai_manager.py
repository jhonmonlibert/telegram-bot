"""
AIManager: the single entry point the rest of the bot talks to for AI
completions.

Strategy (per user's choice):
  1. Always try OpenRouter first (the configured free/paid model).
  2. If OpenRouter fails after its own internal retries — rate limited,
     unavailable, auth error, or any other provider error — and Gemini
     fallback is enabled and configured, automatically retry the same
     conversation on Gemini.
  3. If both fail, raise AIManagerError with a safe, user-facing message.
     Raw provider errors are never shown to the user.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from app.config import config
from app.services.ai_provider import (
    AIProvider,
    AIProviderAuthError,
    AIProviderError,
    AIProviderRateLimited,
    AIProviderUnavailable,
    AIResponse,
    ChatMessage,
)
from app.services.gemini import GeminiClient
from app.services.openrouter import OpenRouterClient

logger = logging.getLogger(__name__)


class AIManagerError(Exception):
    """Safe, user-facing error raised when no provider could answer."""


class AIManager:
    def __init__(
        self,
        primary: Optional[AIProvider] = None,
        fallback: Optional[AIProvider] = None,
        fallback_enabled: Optional[bool] = None,
    ) -> None:
        self.primary: AIProvider = primary or OpenRouterClient()
        self.fallback_enabled = (
            fallback_enabled if fallback_enabled is not None else config.enable_gemini_fallback
        )
        self.fallback: Optional[AIProvider] = None
        if fallback is not None:
            self.fallback = fallback
        elif self.fallback_enabled and config.validate_gemini():
            self.fallback = GeminiClient()

    async def close(self) -> None:
        await self.primary.close()
        if self.fallback is not None:
            await self.fallback.close()

    async def chat(
        self,
        messages: List[ChatMessage],
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AIResponse:
        temperature = temperature if temperature is not None else config.ai_temperature
        max_tokens = max_tokens if max_tokens is not None else config.ai_max_tokens

        primary_error: Optional[Exception] = None
        try:
            return await self.primary.chat(messages, temperature=temperature, max_tokens=max_tokens)
        except AIProviderAuthError as exc:
            logger.error("Primary provider (%s) auth error: %s", self.primary.name, exc)
            primary_error = exc
        except (AIProviderRateLimited, AIProviderUnavailable, AIProviderError) as exc:
            logger.warning("Primary provider (%s) failed: %s", self.primary.name, exc)
            primary_error = exc

        if self.fallback is not None:
            logger.info("Falling back from %s to %s", self.primary.name, self.fallback.name)
            try:
                response = await self.fallback.chat(messages, temperature=temperature, max_tokens=max_tokens)
                return response
            except AIProviderError as exc:
                logger.error("Fallback provider (%s) also failed: %s", self.fallback.name, exc)
                raise AIManagerError(
                    "AI service is temporarily unavailable. Please try again in a moment."
                ) from exc

        raise AIManagerError(
            "AI service is temporarily unavailable. Please try again in a moment."
        ) from primary_error


# Module-level singleton, created lazily so tests can construct their own
# AIManager instances with fakes/mocks instead.
_ai_manager: Optional[AIManager] = None


def get_ai_manager() -> AIManager:
    global _ai_manager
    if _ai_manager is None:
        _ai_manager = AIManager()
    return _ai_manager
