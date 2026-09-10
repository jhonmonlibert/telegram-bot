from __future__ import annotations

from app.services.rate_limit import RateLimiter


def test_allows_up_to_the_limit():
    limiter = RateLimiter(per_minute=3, per_hour=100)
    for _ in range(3):
        allowed, reason = limiter.hit(1)
        assert allowed is True
        assert reason is None


def test_blocks_after_limit_reached():
    limiter = RateLimiter(per_minute=2, per_hour=100)
    limiter.hit(1)
    limiter.hit(1)
    allowed, reason = limiter.hit(1)
    assert allowed is False
    assert reason == "per_minute"


def test_hourly_limit_enforced_independently():
    limiter = RateLimiter(per_minute=1000, per_hour=2)
    limiter.hit(1)
    limiter.hit(1)
    allowed, reason = limiter.hit(1)
    assert allowed is False
    assert reason == "per_hour"


def test_different_keys_are_independent():
    limiter = RateLimiter(per_minute=1, per_hour=100)
    allowed_a, _ = limiter.hit(1)
    allowed_b, _ = limiter.hit(2)
    assert allowed_a is True
    assert allowed_b is True
