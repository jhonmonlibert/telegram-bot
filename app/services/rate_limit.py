"""
Lightweight in-memory sliding-window rate limiter.

Deliberately avoids Redis: this process is the only consumer, so a plain
dict of deques is enough and costs almost no memory for a bot with a
modest user base.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict

from app.config import config


@dataclass
class _Window:
    minute: Deque[float] = field(default_factory=deque)
    hour: Deque[float] = field(default_factory=deque)


class RateLimiter:
    def __init__(
        self,
        per_minute: int | None = None,
        per_hour: int | None = None,
    ) -> None:
        self.per_minute = per_minute if per_minute is not None else config.user_rate_limit_per_minute
        self.per_hour = per_hour if per_hour is not None else config.user_rate_limit_per_hour
        self._windows: Dict[int, _Window] = {}

    def _prune(self, dq: Deque[float], horizon_seconds: float, now: float) -> None:
        while dq and now - dq[0] > horizon_seconds:
            dq.popleft()

    def check(self, key: int) -> tuple[bool, str | None]:
        """Returns (allowed, reason_if_denied)."""
        now = time.monotonic()
        window = self._windows.setdefault(key, _Window())

        self._prune(window.minute, 60.0, now)
        self._prune(window.hour, 3600.0, now)

        if len(window.minute) >= self.per_minute:
            return False, "per_minute"
        if self.per_hour and len(window.hour) >= self.per_hour:
            return False, "per_hour"
        return True, None

    def record(self, key: int) -> None:
        now = time.monotonic()
        window = self._windows.setdefault(key, _Window())
        window.minute.append(now)
        window.hour.append(now)

    def hit(self, key: int) -> tuple[bool, str | None]:
        """Check + record in one call. Returns (allowed, reason_if_denied)."""
        allowed, reason = self.check(key)
        if allowed:
            self.record(key)
        return allowed, reason


# Separate limiter instances: users are keyed by telegram_user_id,
# groups by chat_id, so they never collide even though both are ints.
user_rate_limiter = RateLimiter(
    per_minute=config.user_rate_limit_per_minute, per_hour=config.user_rate_limit_per_hour
)
group_rate_limiter = RateLimiter(per_minute=config.group_rate_limit_per_minute, per_hour=0)
