"""
Provider-agnostic interfaces shared by OpenRouter and Gemini clients.

Keeping this abstraction small means the fallback manager (ai_manager.py)
and the handlers never need to know which concrete provider answered.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class AIResponse:
    text: str
    provider: str
    model: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


class AIProviderError(Exception):
    """Base class for all provider-level failures."""


class AIProviderRateLimited(AIProviderError):
    """HTTP 429 or provider-reported rate limit."""


class AIProviderUnavailable(AIProviderError):
    """Model/provider temporarily unavailable (5xx, timeout, model not found)."""


class AIProviderAuthError(AIProviderError):
    """Invalid / missing API key."""


class AIProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def chat(
        self,
        messages: List[ChatMessage],
        *,
        temperature: float,
        max_tokens: int,
    ) -> AIResponse:
        """Send a chat completion request and return the assistant's reply."""

    async def close(self) -> None:
        """Override if the concrete client owns resources (HTTP clients, etc.)."""
        return None
