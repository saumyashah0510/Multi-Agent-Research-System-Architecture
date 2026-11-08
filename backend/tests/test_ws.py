"""Unit and integration tests for WebSocket live event streaming (Issue BE-09).

Covers:
1. WebSocket connection acceptance.
2. Correct review-specific Redis channel subscription.
3. Publishing an event and receiving it through the WebSocket.
4. Correct JSON payload forwarding.
5. Multiple events in sequence.
6. Disconnect handling.
7. Redis subscription cleanup.
8. Redis failures and cleanup (initial subscribe and mid-stream).
9. Multiple clients subscribing to separate review channels.
10. Malformed JSON frame handling and bytes decoding.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Set

import pytest
from app.api.v1 import ws as ws_module
from app.main import app
from app.services import redis_service
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


class MockPubSub:
    """Thread-safe mock Redis PubSub for unit testing WebSocket streaming."""

    def __init__(self, client: "MockRedis"):
        self.client = client
        self.subscribed_channels: Set[str] = set()
        self.unsubscribed_channels: List[str] = []
        self.closed = False
        self.queue: asyncio.Queue = asyncio.Queue()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def subscribe(self, channel: str):
        self._loop = asyncio.get_running_loop()
        self.subscribed_channels.add(channel)
        self.client._register_subscriber(channel, self)

    async def unsubscribe(self, channel: str):
        self.unsubscribed_channels.append(channel)
        self.subscribed_channels.discard(channel)
        self.client._unregister_subscriber(channel, self)

    async def aclose(self):
        self.closed = True
        for ch in list(self.subscribed_channels):
            self.client._unregister_subscriber(ch, self)
        self.subscribed_channels.clear()

    async def close(self):
        await self.aclose()

    async def listen(self):
        while not self.closed:
            try:
                msg = await self.queue.get()
                if msg is None:
                    break
                if isinstance(msg, Exception):
                    raise msg
                yield msg
            except asyncio.CancelledError:
                break

    def deliver_message(self, msg: Dict[str, Any]):
        if self._loop and not self.closed:
            self._loop.call_soon_threadsafe(self.queue.put_nowait, msg)

    def inject_error(self, exc: Exception):
        if self._loop and not self.closed:
            self._loop.call_soon_threadsafe(self.queue.put_nowait, exc)


class MockRedis:
    """Mock Redis client managing channels and delivering PubSub messages."""

    def __init__(self):
        self.channels: Dict[str, Set[MockPubSub]] = {}
        self.pubsubs: List[MockPubSub] = []

    def pubsub(self) -> MockPubSub:
        ps = MockPubSub(self)
        self.pubsubs.append(ps)
        return ps

    def _register_subscriber(self, channel: str, pubsub: MockPubSub):
        if channel not in self.channels:
            self.channels[channel] = set()
        self.channels[channel].add(pubsub)

    def _unregister_subscriber(self, channel: str, pubsub: MockPubSub):
        if channel in self.channels:
            self.channels[channel].discard(pubsub)
            if not self.channels[channel]:
                del self.channels[channel]

    async def publish(self, channel: str, message: str) -> int:
        subscribers = list(self.channels.get(channel, []))
        for sub in subscribers:
            sub.deliver_message({"type": "message", "channel": channel, "data": message})
        return len(subscribers)


@pytest.fixture
def mock_redis(monkeypatch: pytest.MonkeyPatch) -> MockRedis:
    """Provide a clean MockRedis instance for tests."""
    client = MockRedis()
    monkeypatch.setattr(redis_service, "get_redis_client", lambda: client)
    monkeypatch.setattr(ws_module, "get_redis_client", lambda: client)
    return client


def test_websocket_connection_acceptance(mock_redis: MockRedis):
    """Requirement 1: Verify WebSocket connection is accepted at /api/v1/ws/reviews/{review_id}."""
    client = TestClient(app)
    with client.websocket_connect("/api/v1/ws/reviews/101"):
        # Connection established without exception
        assert len(mock_redis.pubsubs) == 1


def test_correct_review_specific_channel_subscription(mock_redis: MockRedis):
    """Requirement 2: Verify subscription to Redis channel 'review:{review_id}:events'."""
    review_id = 42
    expected_channel = f"review:{review_id}:events"
    client = TestClient(app)

    with client.websocket_connect(f"/api/v1/ws/reviews/{review_id}"):
        assert expected_channel in mock_redis.channels
        ps = mock_redis.pubsubs[0]
        assert expected_channel in ps.subscribed_channels


def test_publish_event_and_receive_through_websocket(mock_redis: MockRedis):
    """Requirements 3 & 4: Publish an event to Redis and receive forwarded JSON frame."""
    review_id = 15
    client = TestClient(app)

    with client.websocket_connect(f"/api/v1/ws/reviews/{review_id}") as ws:
        event = {
            "event": "node_progress",
            "node": "screening",
            "status": "in_progress",
            "progress": 30,
        }
        subscribers = asyncio.run(redis_service.publish_review_event(review_id, event))
        assert subscribers == 1

        received = ws.receive_json()
        assert received == event


def test_multiple_events_in_sequence(mock_redis: MockRedis):
    """Requirement 5: Stream multiple events in sequence to the connected client."""
    review_id = 20
    client = TestClient(app)

    with client.websocket_connect(f"/api/v1/ws/reviews/{review_id}") as ws:
        events = [
            {"event": "start", "step": 1},
            {"event": "search_complete", "step": 2, "papers": 25},
            {"event": "synthesis_complete", "step": 3, "status": "completed"},
        ]
        for ev in events:
            asyncio.run(redis_service.publish_review_event(review_id, ev))

        for ev in events:
            received = ws.receive_json()
            assert received == ev


def test_client_disconnect_and_redis_cleanup(mock_redis: MockRedis):
    """Requirements 6 & 7: Verify Redis subscription cleanup when client disconnects."""
    review_id = 88
    channel = f"review:{review_id}:events"
    client = TestClient(app)

    with client.websocket_connect(f"/api/v1/ws/reviews/{review_id}"):
        assert channel in mock_redis.channels
        ps = mock_redis.pubsubs[0]
        assert not ps.closed

    # Once the with block exits, client disconnects
    assert ps.closed is True
    assert channel in ps.unsubscribed_channels
    assert channel not in mock_redis.channels


def test_redis_subscription_failure_cleanup(monkeypatch: pytest.MonkeyPatch):
    """Requirement 8: Handle Redis connection failure during initial subscription."""

    class FailingRedis:
        def pubsub(self):
            ps = MockPubSub(self)

            async def fail_subscribe(channel: str):
                raise ConnectionError("Redis server unreachable")

            ps.subscribe = fail_subscribe
            return ps

    failing_client = FailingRedis()
    monkeypatch.setattr(ws_module, "get_redis_client", lambda: failing_client)

    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/ws/reviews/99") as ws:
            ws.receive_json()

    assert exc_info.value.code == 1011


def test_redis_listen_error_during_streaming(mock_redis: MockRedis):
    """Requirement 8: Handle Redis failure during message streaming."""
    review_id = 70
    client = TestClient(app)

    with client.websocket_connect(f"/api/v1/ws/reviews/{review_id}") as ws:
        ps = mock_redis.pubsubs[0]

        # Deliver a first valid event
        ps.deliver_message(
            {
                "type": "message",
                "channel": f"review:{review_id}:events",
                "data": json.dumps({"event": "first"}),
            }
        )
        first_msg = ws.receive_json()
        assert first_msg == {"event": "first"}

        # Inject a mid-stream connection error
        ps.inject_error(ConnectionError("Redis connection dropped mid-stream"))

        # Next receive detects closed connection
        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws.receive_json()

        assert exc_info.value.code == 1011

    assert ps.closed is True


def test_multiple_clients_subscribing_to_separate_reviews(mock_redis: MockRedis):
    """Requirement 9: Multiple clients subscribing independently to different review channels."""
    client = TestClient(app)

    with client.websocket_connect("/api/v1/ws/reviews/10") as ws1:
        with client.websocket_connect("/api/v1/ws/reviews/20") as ws2:
            assert "review:10:events" in mock_redis.channels
            assert "review:20:events" in mock_redis.channels

            # Publish to review 10
            asyncio.run(
                redis_service.publish_review_event(10, {"review": 10, "msg": "for_client_1"})
            )
            # Publish to review 20
            asyncio.run(
                redis_service.publish_review_event(20, {"review": 20, "msg": "for_client_2"})
            )

            assert ws1.receive_json() == {"review": 10, "msg": "for_client_1"}
            assert ws2.receive_json() == {"review": 20, "msg": "for_client_2"}

        # ws2 disconnected, review 20 should be cleaned up
        assert "review:20:events" not in mock_redis.channels
        # ws1 is still active
        assert "review:10:events" in mock_redis.channels

        # ws1 should still receive events
        asyncio.run(
            redis_service.publish_review_event(10, {"review": 10, "msg": "second_for_client_1"})
        )
        assert ws1.receive_json() == {"review": 10, "msg": "second_for_client_1"}

    # ws1 disconnected, review 10 cleaned up
    assert "review:10:events" not in mock_redis.channels


def test_multiple_clients_same_review_channel(mock_redis: MockRedis):
    """Multiple clients subscribing independently to the same review channel."""
    review_id = 999
    client = TestClient(app)

    with client.websocket_connect(f"/api/v1/ws/reviews/{review_id}") as ws1:
        with client.websocket_connect(f"/api/v1/ws/reviews/{review_id}") as ws2:
            assert len(mock_redis.channels[f"review:{review_id}:events"]) == 2

            asyncio.run(redis_service.publish_review_event(review_id, {"event": "broadcast_test"}))

            assert ws1.receive_json() == {"event": "broadcast_test"}
            assert ws2.receive_json() == {"event": "broadcast_test"}


def test_malformed_json_skipped_and_bytes_handled(mock_redis: MockRedis):
    """Verify non-JSON/malformed payloads are skipped and bytes are properly decoded."""
    review_id = 111
    client = TestClient(app)

    with client.websocket_connect(f"/api/v1/ws/reviews/{review_id}") as ws:
        ps = mock_redis.pubsubs[0]

        # 1. Deliver malformed JSON string (should be skipped)
        ps.deliver_message({"type": "message", "data": "not-valid-json{{{"})

        # 2. Deliver valid UTF-8 bytes payload (should be decoded and forwarded)
        ps.deliver_message(
            {
                "type": "message",
                "data": json.dumps({"event": "bytes_event", "ok": True}).encode("utf-8"),
            }
        )

        # 3. Deliver normal JSON dict
        ps.deliver_message(
            {
                "type": "message",
                "data": {"event": "dict_event", "ok": True},
            }
        )

        msg1 = ws.receive_json()
        assert msg1 == {"event": "bytes_event", "ok": True}

        msg2 = ws.receive_json()
        assert msg2 == {"event": "dict_event", "ok": True}


def test_websocket_invalid_review_id_rejected():
    """Verify that non-positive review_ids (-5, 0) are rejected with policy violation (code 1008)."""
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info1:
        with client.websocket_connect("/api/v1/ws/reviews/-5"):
            pass
    assert exc_info1.value.code == 1008

    with pytest.raises(WebSocketDisconnect) as exc_info2:
        with client.websocket_connect("/api/v1/ws/reviews/0"):
            pass
    assert exc_info2.value.code == 1008


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
def test_live_redis_websocket_stream():
    """Live integration test: publish event to live Redis and receive via WebSocket."""
    review_id = 9988
    client = TestClient(app)

    with client.websocket_connect(f"/api/v1/ws/reviews/{review_id}") as ws:
        event = {"event": "live_test", "review_id": review_id, "status": "ok"}
        asyncio.run(redis_service.publish_review_event(review_id, event))
        received = ws.receive_json()
        assert received == event
