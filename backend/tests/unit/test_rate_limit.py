"""Unit tests for Redis Sliding-Window Rate Limiter (Issue BE-14)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.rate_limit import RateLimiter
from fastapi import HTTPException, Request, Response


def create_request():
    """Create a mock FastAPI request."""
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/reviews/",
        "headers": [(b"host", b"localhost:8000")],
        "client": ("192.168.1.100", 54321),
        "scheme": "http",
        "server": ("localhost", 8000),
        "query_string": b"",
    }
    return Request(scope)


def test_rate_limiter_initialization():
    limiter = RateLimiter(times=5, seconds=60, key_prefix="test_limit")

    assert limiter.times == 5
    assert limiter.seconds == 60
    assert limiter.key_prefix == "test_limit"


def test_resolve_identifier_ip_fallback():
    limiter = RateLimiter(times=10, seconds=60)

    request = create_request()

    identifier = limiter._resolve_identifier(request)

    assert identifier == "ip:192.168.1.100"


@pytest.mark.asyncio
async def test_sliding_window_threshold_exceeded(monkeypatch):
    """Verify HTTP 429 is raised when the request limit is exceeded."""

    redis_mock = MagicMock()
    redis_mock.eval = AsyncMock(return_value=[0, 2, 5000, 1700000060000])

    monkeypatch.setattr(
        "app.core.rate_limit.get_redis_client",
        lambda: redis_mock,
    )

    limiter = RateLimiter(times=2, seconds=60)

    request = create_request()
    response = Response()

    with pytest.raises(HTTPException) as exc_info:
        await limiter(request, response)

    assert exc_info.value.status_code == 429
    assert exc_info.value.headers["Retry-After"] == "5"
    assert exc_info.value.headers["X-RateLimit-Limit"] == "2"
    assert exc_info.value.headers["X-RateLimit-Remaining"] == "0"

    redis_mock.eval.assert_awaited_once()


@pytest.mark.asyncio
async def test_request_within_rate_limit(monkeypatch):
    """Verify requests within the limit are allowed."""

    redis_mock = MagicMock()
    redis_mock.eval = AsyncMock(return_value=[1, 1, 0, 1700000060000])

    monkeypatch.setattr(
        "app.core.rate_limit.get_redis_client",
        lambda: redis_mock,
    )

    limiter = RateLimiter(times=5, seconds=60)

    request = create_request()
    response = Response()

    result = await limiter(request, response)

    assert result is True
    assert response.headers["X-RateLimit-Limit"] == "5"
    assert response.headers["X-RateLimit-Remaining"] == "4"
    assert "X-RateLimit-Reset" in response.headers

    redis_mock.eval.assert_awaited_once()
