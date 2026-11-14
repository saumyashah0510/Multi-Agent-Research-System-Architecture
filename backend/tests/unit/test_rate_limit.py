"""Unit tests for Redis Sliding-Window Rate Limiter (Issue BE-14)."""

import pytest
from app.core.rate_limit import RateLimiter
from fastapi import Request


def test_rate_limiter_initialization():
    """Verify rate limiter instantiates with configured thresholds."""
    limiter = RateLimiter(times=5, seconds=60, key_prefix="test_limit")
    assert limiter.times == 5
    assert limiter.seconds == 60
    assert limiter.key_prefix == "test_limit"


def test_resolve_identifier_ip_fallback():
    """Verify rate limiter extracts client IP when no Authorization header is present."""
    limiter = RateLimiter(times=10, seconds=60)

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/reviews/",
        "headers": [(b"host", b"localhost:8000")],
        "client": ("192.168.1.100", 54321),
    }
    request = Request(scope)

    identifier = limiter._resolve_identifier(request)
    assert identifier == "ip:192.168.1.100"


@pytest.mark.skip(
    reason="Assignee will unskip upon implementing sliding window Redis logic in BE-14"
)
@pytest.mark.asyncio
async def test_sliding_window_threshold_exceeded(monkeypatch):
    """Verify rate limiter raises HTTPException 429 when quota is exceeded."""
    _ = RateLimiter(times=2, seconds=60)
    # Assignee will mock redis pipeline and verify 429 exception with Retry-After header
    pass
