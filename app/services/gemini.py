"""
Google AI Studio (Gemini) client, used as the automatic fallback provider
when OpenRouter's free model is unavailable or rate-limited.

Uses the plain REST `generateContent` endpoint so no extra Google SDK
(and its dependency weight) is required — just httpx, exactly like the
OpenRouter client.
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


class GeminiClient(AIProvider):
    name = "gemini"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else config.gemini_api_key
        self.model = model or config.gemini_model
        self.base_url = (base_url or config.gemini_base_url).rstrip("/")
        self.timeout = timeout if timeout is not None else config.ai_timeout_seconds
        self.max_retries = max_retries if max_retries is not None else config.ai_max_retries
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @staticmethod
    def _to_gemini_contents(messages: List[ChatMessage]) -> tuple[Optional[str], list[dict]]:
        """Split out the system prompt (Gemini wants it separately) and map
        the rest of the history to Gemini's {role, parts} format."""
        system_parts: list[str] = []
        contents: list[dict] = []
        for m in messages:
            if m.role == "system":
                system_parts.append(m.content)
                continue
            role = "model" if m.role == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": m.content}]})
        system_instruction = "\n".join(system_parts) if system_parts else None
        return system_instruction, contents

    async def chat(
        self,
        messages: List[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AIResponse:
        if not self.api_key:
            raise AIProviderAuthError("Gemini API key is not configured")

        system_instruction, contents = self._to_gemini_contents(messages)
        if not contents:
            raise AIProviderError("No user/assistant content to send to Gemini")

        payload: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        url = f"/models/{self.model}:generateContent"
        params = {"key": self.api_key}

        last_error: Optional[Exception] = None
        client = self._get_client()

        for attempt in range(1, self.max_retries + 1):
            try:
                response = await client.post(url, params=params, json=payload)
            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning("Gemini timeout (attempt %d/%d)", attempt, self.max_retries)
                await self._backoff(attempt)
                continue
            except httpx.RequestError as exc:
                last_error = exc
                logger.warning("Gemini network error (attempt %d/%d): %s", attempt, self.max_retries, exc.__class__.__name__)
                await self._backoff(attempt)
                continue

            if response.status_code == 200:
                return self._parse_response(response)

            if response.status_code in (401, 403):
                logger.error("Gemini authentication failed (status %d)", response.status_code)
                raise AIProviderAuthError("Invalid Gemini API key")

            if response.status_code == 429:
                last_error = AIProviderRateLimited("Gemini rate limit reached")
                logger.warning("Gemini rate limited (attempt %d/%d)", attempt, self.max_retries)
                await self._backoff(attempt)
                continue

            if response.status_code == 404:
                logger.error("Gemini model unavailable: %s", self.model)
                raise AIProviderUnavailable(f"Model '{self.model}' is not available on Gemini")

            if 500 <= response.status_code < 600:
                last_error = AIProviderUnavailable(f"Gemini server error {response.status_code}")
                logger.warning(
                    "Gemini server error %d (attempt %d/%d)", response.status_code, attempt, self.max_retries
                )
                await self._backoff(attempt)
                continue

            logger.error("Gemini unexpected status %d", response.status_code)
            raise AIProviderError(f"Gemini returned unexpected status {response.status_code}")

        logger.error("Gemini exhausted retries: %s", last_error)
        if isinstance(last_error, AIProviderRateLimited):
            raise last_error
        raise AIProviderUnavailable("Gemini is temporarily unavailable") from last_error

    def _parse_response(self, response: httpx.Response) -> AIResponse:
        try:
            data = response.json()
            candidate = data["candidates"][0]
            parts = candidate["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts)
            usage = data.get("usageMetadata", {}) or {}
            return AIResponse(
                text=text.strip(),
                provider=self.name,
                model=self.model,
                prompt_tokens=usage.get("promptTokenCount"),
                completion_tokens=usage.get("candidatesTokenCount"),
            )
        except (KeyError, IndexError, ValueError) as exc:
            logger.error("Failed to parse Gemini response: %s", exc)
            raise AIProviderError("Received a malformed response from Gemini") from exc

    @staticmethod
    async def _backoff(attempt: int) -> None:
        delay = min(2 ** attempt, 10) + random.uniform(0, 0.5)
        await asyncio.sleep(delay)
