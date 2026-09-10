"""
OpenRouter API client (OpenAI-compatible /chat/completions endpoint).

Handles timeouts, retries with exponential backoff, 429 / 5xx detection,
invalid-API-key detection and unavailable-model detection, and always
raises a clean application-level exception instead of leaking raw
provider errors to the rest of the app.
"""
from __future__ import annotations

import asyncio
import logging
import random
from typing import List, Optional

import httpx

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

logger = logging.getLogger(__name__)


class OpenRouterClient(AIProvider):
    name = "openrouter"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else config.openrouter_api_key
        self.model = model or config.openrouter_model
        self.base_url = (base_url or config.openrouter_base_url).rstrip("/")
        self.timeout = timeout if timeout is not None else config.ai_timeout_seconds
        self.max_retries = max_retries if max_retries is not None else config.ai_max_retries
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "Content-Type": "application/json",
                    # Optional but recommended by OpenRouter for routing/analytics.
                    "HTTP-Referer": "https://github.com/",
                    "X-Title": "Telegram AI Assistant",
                },
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def chat(
        self,
        messages: List[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AIResponse:
        if not self.api_key:
            raise AIProviderAuthError("OpenRouter API key is not configured")

        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}

        last_error: Optional[Exception] = None
        client = self._get_client()

        for attempt in range(1, self.max_retries + 1):
            try:
                response = await client.post("/chat/completions", json=payload, headers=headers)
            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning("OpenRouter timeout (attempt %d/%d)", attempt, self.max_retries)
                await self._backoff(attempt)
                continue
            except httpx.RequestError as exc:
                last_error = exc
                logger.warning("OpenRouter network error (attempt %d/%d): %s", attempt, self.max_retries, exc.__class__.__name__)
                await self._backoff(attempt)
                continue

            if response.status_code == 200:
                return self._parse_response(response)

            if response.status_code == 401 or response.status_code == 403:
                logger.error("OpenRouter authentication failed (status %d)", response.status_code)
                raise AIProviderAuthError("Invalid OpenRouter API key")

            if response.status_code == 429:
                last_error = AIProviderRateLimited("OpenRouter rate limit reached")
                logger.warning("OpenRouter rate limited (attempt %d/%d)", attempt, self.max_retries)
                await self._backoff(attempt, respect_retry_after=response.headers.get("Retry-After"))
                continue

            if response.status_code == 404:
                # Model not found / not available.
                logger.error("OpenRouter model unavailable: %s", self.model)
                raise AIProviderUnavailable(f"Model '{self.model}' is not available on OpenRouter")

            if 500 <= response.status_code < 600:
                last_error = AIProviderUnavailable(f"OpenRouter server error {response.status_code}")
                logger.warning(
                    "OpenRouter server error %d (attempt %d/%d)",
                    response.status_code,
                    attempt,
                    self.max_retries,
                )
                await self._backoff(attempt)
                continue

            # Any other unexpected status.
            logger.error("OpenRouter unexpected status %d", response.status_code)
            raise AIProviderError(f"OpenRouter returned unexpected status {response.status_code}")

        logger.error("OpenRouter exhausted retries: %s", last_error)
        if isinstance(last_error, AIProviderRateLimited):
            raise last_error
        raise AIProviderUnavailable("OpenRouter is temporarily unavailable") from last_error

    def _parse_response(self, response: httpx.Response) -> AIResponse:
        try:
            data = response.json()
            choice = data["choices"][0]
            text = choice["message"]["content"]
            usage = data.get("usage", {}) or {}
            return AIResponse(
                text=text.strip(),
                provider=self.name,
                model=data.get("model", self.model),
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
            )
        except (KeyError, IndexError, ValueError) as exc:
            logger.error("Failed to parse OpenRouter response: %s", exc)
            raise AIProviderError("Received a malformed response from OpenRouter") from exc

    @staticmethod
    async def _backoff(attempt: int, respect_retry_after: Optional[str] = None) -> None:
        if respect_retry_after:
            try:
                delay = float(respect_retry_after)
                await asyncio.sleep(min(delay, 15.0))
                return
            except ValueError:
                pass
        delay = min(2 ** attempt, 10) + random.uniform(0, 0.5)
        await asyncio.sleep(delay)
