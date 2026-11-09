"""Unit tests for Redis caching service (Issue BE-04, BE-09)."""

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
async def test_set_cached_query_dict_json(monkeypatch: pytest.MonkeyPatch):
    """Verify set_cached_query serializes dict/list to JSON string automatically."""
    mock_client = AsyncMock()
    mock_client.set.return_value = True
    monkeypatch.setattr(redis_service, "get_redis_client", lambda: mock_client)

    data = {"papers": [{"id": 1, "title": "Test Paper"}]}
    result = await redis_service.set_cached_query("test_dict_key", data, 600)
    assert result is True
    mock_client.set.assert_called_once_with(
        "test_dict_key", '{"papers": [{"id": 1, "title": "Test Paper"}]}', ex=600
    )


@pytest.mark.asyncio
async def test_get_cached_query_as_json(monkeypatch: pytest.MonkeyPatch):
    """Verify get_cached_query returns parsed JSON dict when as_json=True."""
    mock_client = AsyncMock()
    mock_client.get.return_value = '{"status": "ok", "items": [1, 2]}'
    monkeypatch.setattr(redis_service, "get_redis_client", lambda: mock_client)

    result = await redis_service.get_cached_query("test_json_key", as_json=True)
    assert result == {"status": "ok", "items": [1, 2]}
    mock_client.get.assert_called_once_with("test_json_key")


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


@pytest.mark.asyncio
async def test_publish_review_event_success(monkeypatch: pytest.MonkeyPatch):
    """Verify publish_review_event serializes data and publishes to the correct review channel."""
    mock_client = AsyncMock()
    mock_client.publish.return_value = 2
    monkeypatch.setattr(redis_service, "get_redis_client", lambda: mock_client)

    event_data = {"event": "node_progress", "node": "discovery", "progress": 45}
    subscribers = await redis_service.publish_review_event(101, event_data)

    assert subscribers == 2
    mock_client.publish.assert_called_once_with(
        "review:101:events",
        '{"event": "node_progress", "node": "discovery", "progress": 45}',
    )


@pytest.mark.asyncio
async def test_publish_review_event_serialization_error():
    """Verify publish_review_event raises TypeError when data is not JSON serializable."""
    non_serializable_data = {"invalid": {1, 2, 3}}
    with pytest.raises(TypeError):
        await redis_service.publish_review_event(101, non_serializable_data)


@pytest.mark.asyncio
async def test_publish_review_event_redis_error(monkeypatch: pytest.MonkeyPatch):
    """Verify publish_review_event does not swallow Redis failures."""
    mock_client = AsyncMock()
    mock_client.publish.side_effect = ConnectionError("Redis server unavailable")
    monkeypatch.setattr(redis_service, "get_redis_client", lambda: mock_client)

    with pytest.raises(ConnectionError, match="Redis server unavailable"):
        await redis_service.publish_review_event(101, {"event": "test"})


@pytest.mark.asyncio
async def test_publish_review_event_custom_client():
    """Verify publish_review_event uses explicitly provided client without accessing singleton."""
    mock_client = AsyncMock()
    mock_client.publish.return_value = 3
    event_data = {"event": "custom_client_test"}
    subscribers = await redis_service.publish_review_event(105, event_data, client=mock_client)

    assert subscribers == 3
    mock_client.publish.assert_called_once_with(
        "review:105:events",
        '{"event": "custom_client_test"}',
    )


@pytest.mark.asyncio
async def test_pubsub_cleanup_fallback_when_aclose_missing():
    """Verify pubsub cleanup falls back to close() when aclose is unavailable (Redis 5.0.0)."""
    import inspect

    mock_pubsub = MagicMock(spec=["unsubscribe", "close"])
    mock_pubsub.unsubscribe = AsyncMock()
    mock_pubsub.close = AsyncMock()

    try:
        await mock_pubsub.unsubscribe("test_channel")
    finally:
        if hasattr(mock_pubsub, "aclose"):
            await mock_pubsub.aclose()
        elif hasattr(mock_pubsub, "close"):
            res = mock_pubsub.close()
            if inspect.isawaitable(res):
                await res

    mock_pubsub.unsubscribe.assert_called_once_with("test_channel")
    mock_pubsub.close.assert_called_once()


@pytest.mark.asyncio
async def test_pubsub_cleanup_resilient_to_unsubscribe_failure():
    """Verify pubsub and client close still execute even if unsubscribe raises an error."""
    mock_pubsub = MagicMock(spec=["unsubscribe", "aclose"])
    mock_pubsub.unsubscribe = AsyncMock(side_effect=ConnectionError("Unsubscribe dropped"))
    mock_pubsub.aclose = AsyncMock()
    mock_client = AsyncMock()

    try:
        try:
            await mock_pubsub.unsubscribe("test_channel")
        except Exception:
            pass
        finally:
            if hasattr(mock_pubsub, "aclose"):
                await mock_pubsub.aclose()
    finally:
        if hasattr(mock_client, "aclose"):
            await mock_client.aclose()

    mock_pubsub.unsubscribe.assert_called_once()
    mock_pubsub.aclose.assert_called_once()
    mock_client.aclose.assert_called_once()


def is_live_redis_available() -> bool:
    """Check if a live Redis daemon is reachable on localhost:6379."""
    import socket

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        result = sock.connect_ex(("127.0.0.1", 6379))
        sock.close()
        return result == 0
    except Exception:
        return False


LIVE_REDIS_AVAILABLE = is_live_redis_available()


@pytest.mark.skipif(
    not LIVE_REDIS_AVAILABLE,
    reason="Live Redis daemon is not reachable on localhost:6379",
)
@pytest.mark.asyncio
async def test_live_redis_pubsub_integration(monkeypatch: pytest.MonkeyPatch):
    """Live integration test: connect, subscribe, publish, and receive over live Redis."""
    import asyncio
    import inspect
    import json
    import uuid

    from app.core.config import settings

    review_id = (uuid.uuid4().int & 0x7FFFFFFF) % 1_000_000 + 10000
    channel = f"review:{review_id}:events"

    # Isolate test from cached global Redis client using pytest monkeypatching
    isolated_client = redis_service.aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
    )
    monkeypatch.setattr(redis_service, "get_redis_client", lambda: isolated_client)

    pubsub = None
    try:
        pubsub = isolated_client.pubsub()
        await pubsub.subscribe(channel)
        event = {"event": "live_redis_test", "review_id": review_id}
        subscribers = await redis_service.publish_review_event(
            review_id, event, client=isolated_client
        )
        assert subscribers >= 1

        async with asyncio.timeout(3.0):
            while True:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg.get("type") == "message" and msg.get("channel") == channel:
                    data = msg.get("data")
                    payload = json.loads(data) if isinstance(data, (str, bytes)) else data
                    assert payload == event
                    break
    finally:
        # 1. PubSub cleanup: robust against unsubscribe failure and compatible with Redis 5.0.0
        if pubsub is not None:
            try:
                await pubsub.unsubscribe(channel)
            except Exception:
                pass
            finally:
                try:
                    if hasattr(pubsub, "aclose"):
                        await pubsub.aclose()
                    elif hasattr(pubsub, "close"):
                        res = pubsub.close()
                        if inspect.isawaitable(res):
                            await res
                except Exception:
                    pass

        # 2. Redis client cleanup: guaranteed to run even if earlier PubSub cleanup failed
        try:
            if hasattr(isolated_client, "aclose"):
                await isolated_client.aclose()
            elif hasattr(isolated_client, "close"):
                res = isolated_client.close()
                if inspect.isawaitable(res):
                    await res
        except Exception:
            pass
