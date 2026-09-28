"""Unit tests for Redis caching service (Issue BE-04)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.services import redis_service


@pytest.mark.asyncio
async def test_get_redis_client(monkeypatch: pytest.MonkeyPatch):
    """Verify get_redis_client returns a Redis client singleton instance."""
    monkeypatch.setattr(redis_service, "redis_client", None)
    mock_from_url = MagicMock()
    monkeypatch.setattr(redis_service.aioredis, "from_url", mock_from_url)

    client1 = redis_service.get_redis_client()
    client2 = redis_service.get_redis_client()

    assert client1 == client2
    mock_from_url.assert_called_once()


@pytest.mark.asyncio
async def test_set_cached_query_success(monkeypatch: pytest.MonkeyPatch):
    """Verify set_cached_query sets key with TTL in Redis."""
    mock_client = AsyncMock()
    mock_client.set.return_value = True
    monkeypatch.setattr(redis_service, "get_redis_client", lambda: mock_client)

    result = await redis_service.set_cached_query("test_key", "test_val", 300)
    assert result is True
    mock_client.set.assert_called_once_with("test_key", "test_val", ex=300)


@pytest.mark.asyncio
async def test_set_cached_query_failure(monkeypatch: pytest.MonkeyPatch):
    """Verify set_cached_query returns False when exception occurs."""
    mock_client = AsyncMock()
    mock_client.set.side_effect = Exception("Redis Error")
    monkeypatch.setattr(redis_service, "get_redis_client", lambda: mock_client)

    result = await redis_service.set_cached_query("test_key", "test_val")
    assert result is False


@pytest.mark.asyncio
async def test_get_cached_query_hit(monkeypatch: pytest.MonkeyPatch):
    """Verify get_cached_query returns cached string on cache hit."""
    mock_client = AsyncMock()
    mock_client.get.return_value = "cached_json_result"
    monkeypatch.setattr(redis_service, "get_redis_client", lambda: mock_client)

    result = await redis_service.get_cached_query("test_key")
    assert result == "cached_json_result"
    mock_client.get.assert_called_once_with("test_key")


@pytest.mark.asyncio
async def test_get_cached_query_miss_or_error(monkeypatch: pytest.MonkeyPatch):
    """Verify get_cached_query returns None on cache miss or exception."""
    mock_client = AsyncMock()
    mock_client.get.side_effect = Exception("Redis Error")
    monkeypatch.setattr(redis_service, "get_redis_client", lambda: mock_client)

    result = await redis_service.get_cached_query("test_key")
    assert result is None


@pytest.mark.asyncio
async def test_check_redis_connection_success(monkeypatch: pytest.MonkeyPatch):
    """Verify check_redis_connection returns True when ping succeeds."""
    mock_client = AsyncMock()
    mock_client.ping.return_value = True
    monkeypatch.setattr(redis_service, "get_redis_client", lambda: mock_client)

    result = await redis_service.check_redis_connection()
    assert result is True


@pytest.mark.asyncio
async def test_check_redis_connection_failure(monkeypatch: pytest.MonkeyPatch):
    """Verify check_redis_connection returns False when ping fails."""
    mock_client = AsyncMock()
    mock_client.ping.side_effect = Exception("Ping failed")
    monkeypatch.setattr(redis_service, "get_redis_client", lambda: mock_client)

    result = await redis_service.check_redis_connection()
    assert result is False


@pytest.mark.asyncio
async def test_close_redis_client(monkeypatch: pytest.MonkeyPatch):
    """Verify close_redis_client closes connection and clears singleton."""
    mock_client = AsyncMock()
    monkeypatch.setattr(redis_service, "redis_client", mock_client)

    await redis_service.close_redis_client()
    mock_client.close.assert_called_once()
    assert redis_service.redis_client is None
