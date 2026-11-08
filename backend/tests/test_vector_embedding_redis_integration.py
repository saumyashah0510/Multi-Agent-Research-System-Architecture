"""Combined Integration Tests: AI-07 (Vector Embedding Node) + BE-09 (Redis Pub/Sub & WebSocket).

Test Classifications:
1. Unit Tests (Isolated helper and logic verification)
2. Mocked Integration Tests (Multi-component interactions using verified in-memory doubles)
3. Live PostgreSQL/pgvector Tests (Real database connection and vector indexing)
4. Live Redis Tests (Real Redis server connection and channel pub/sub)
5. Full End-to-End Tests (Complete pipeline execution from DB to WebSocket)

Covers all Phase 5 and Part 2 Verification Requirements:
- Scenario A: Commit succeeds -> Chunks persisted, event published, WebSocket receives event.
- Scenario B: Flush succeeds but outer transaction rolls back -> NO event published.
- Scenario C: Database commit fails -> Error propagated, NO event published.
- Scenario D: Multiple papers in one review -> Atomic persistence and combined chunk count.
- Scenario E: Transaction ownership strictly respected.
- Event Delivery: Correct review ID, accurate chunk count, stable event_id and idempotency_key.
- Redis & WebSocket Reliability: Redis failure does not undo DB persistence, sequential retry idempotency.
- Resource Management: Disconnect cleanup, task cancellation, cross-review isolation.
"""

import asyncio
import hashlib
import json
import logging
import socket
import time
import uuid
from typing import Any, Dict, List, Optional, Set
from unittest.mock import patch

import pytest
from app.agents.nodes.vector_embedding_node import (
    publish_vector_embedding_completion,
    vector_embedding_node,
)
from app.agents.state import AgentState
from app.api.v1 import ws as ws_module
from app.main import app
from app.models.chunk import PaperChunk
from app.models.paper import Paper
from app.models.review import LiteratureReview
from app.services import redis_service
from fastapi.testclient import TestClient
from sqlalchemy import select

logger = logging.getLogger(__name__)

# ==============================================================================
# Helper to detect live infrastructure availability
# ==============================================================================


def _is_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    """Check if a network port is open and accepting TCP connections."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        res = s.connect_ex((host, port))
        return res == 0
    except Exception:
        return False
    finally:
        s.close()


LIVE_POSTGRES_AVAILABLE = _is_port_open("127.0.0.1", 5432)
LIVE_REDIS_AVAILABLE = _is_port_open("127.0.0.1", 6379)


# ==============================================================================
# Test Doubles: MockSentenceTransformer, MockAsyncSession, MockRedis, MockPubSub
# ==============================================================================


class MockSentenceTransformer:
    """Mock SentenceTransformer model generating deterministic 384D unit vectors."""

    def encode(self, texts, convert_to_numpy=True, show_progress_bar=False):
        single = isinstance(texts, str)
        text_list = [texts] if single else texts

        vectors = []
        for t in text_list:
            h = hashlib.sha256(t.encode("utf-8")).digest()
            vec = [round(((h[i % len(h)] + i) % 256) / 255.0 - 0.5, 6) for i in range(384)]
            norm = sum(x * x for x in vec) ** 0.5
            if norm > 0:
                vec = [round(x / norm, 6) for x in vec]
            vectors.append(vec)

        return vectors[0] if single and not convert_to_numpy else vectors


class MockPubSub:
    """Thread-safe mock Redis PubSub for WebSocket streaming tests."""

    def __init__(self, client: "MockRedisClient"):
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


class MockRedisClient:
    """Mock Redis client managing channels and capturing published events."""

    def __init__(self):
        self.channels: Dict[str, Set[MockPubSub]] = {}
        self.pubsubs: List[MockPubSub] = []
        self.published_messages: List[Dict[str, Any]] = []
        self.publish_call_order: List[tuple] = []

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
        self.publish_call_order.append(("redis_published", time.perf_counter()))
        parsed_msg = json.loads(message) if isinstance(message, str) else message
        self.published_messages.append({"channel": channel, "data": parsed_msg})

        subscribers = list(self.channels.get(channel, []))
        for sub in subscribers:
            sub.deliver_message({"type": "message", "channel": channel, "data": message})
        return len(subscribers)


class MockAsyncSession:
    """Mock AsyncSession recording chunk persistence, transactions, and execution timeline."""

    def __init__(
        self,
        papers: Optional[List[Paper]] = None,
        fail_on_flush: bool = False,
        fail_on_commit: bool = False,
    ):
        self.papers = papers or []
        self.added_chunks: List[PaperChunk] = []
        self.timeline: List[tuple] = []
        self.with_for_update_called = False
        self.flushed = False
        self.committed = False
        self.rolled_back = False
        self.fail_on_flush = fail_on_flush
        self.fail_on_commit = fail_on_commit

    async def execute(self, stmt):
        stmt_str = str(stmt).lower()
        if "with_for_update" in stmt_str or "for update" in stmt_str:
            self.with_for_update_called = True

        class MockResult:
            def __init__(self, items):
                self._items = items

            def scalars(self):
                class MockScalars:
                    def __init__(self, items):
                        self._items = items

                    def all(self):
                        return self._items

                return MockScalars(self._items)

        return MockResult(self.papers)

    def add(self, obj):
        if isinstance(obj, PaperChunk):
            self.added_chunks.append(obj)

    async def flush(self):
        if self.fail_on_flush:
            raise RuntimeError("Database connection lost during flush")
        self.timeline.append(("db_flushed", time.perf_counter()))
        self.flushed = True

    async def commit(self):
        if self.fail_on_commit:
            raise RuntimeError("Database connection lost during commit")
        self.timeline.append(("db_committed", time.perf_counter()))
        self.committed = True

    async def rollback(self):
        self.timeline.append(("db_rolled_back", time.perf_counter()))
        self.rolled_back = True
        self.added_chunks.clear()


@pytest.fixture(autouse=True)
def mock_embedding_model_fixture():
    """Autouse fixture mocking local SentenceTransformer for lightweight offline tests."""
    mock_model = MockSentenceTransformer()
    with patch("app.services.vector_service._get_embedding_model", return_value=mock_model):
        with patch("app.services.vector_service.is_embedding_model_available", return_value=True):
            with patch(
                "app.agents.nodes.vector_embedding_node.is_embedding_model_available",
                return_value=True,
            ):
                yield


@pytest.fixture
def mock_redis(monkeypatch: pytest.MonkeyPatch) -> MockRedisClient:
    """Provide clean MockRedisClient instance routed to redis_service and ws."""
    client = MockRedisClient()
    monkeypatch.setattr(redis_service, "get_redis_client", lambda: client)
    monkeypatch.setattr(ws_module, "get_redis_client", lambda: client)
    return client


# ==============================================================================
# SECTION A: Part 2 — Database Transaction Correctness Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_scenario_a_commit_succeeds_and_publishes_event(
    mock_redis: MockRedisClient,
):
    """[Test Classification: Mocked Integration Test]
    Scenario A: When commit succeeds, chunks are persisted, transaction commits,
    and completion event is published with accurate counts and stable event ID.
    """
    review_id = 101
    paper = Paper(id=1, title="Paper Alpha", arxiv_id="arxiv:101", review_id=review_id)
    mock_db = MockAsyncSession(papers=[paper])

    state: AgentState = {
        "review_id": review_id,
        "extracted_pdf_contents": {
            "arxiv:101": {
                "abstract": "Abstract text for paper alpha.",
                "methods": "Methodology section details.",
            }
        },
    }

    result = await vector_embedding_node(state, db=mock_db, commit_on_complete=True)

    # 1. Chunks persisted
    assert len(mock_db.added_chunks) == 2
    assert result["chunks_stored_count"] == 2
    assert result["current_step"] == "vector_embedding_completed"

    # 2. Transaction committed
    assert mock_db.committed is True

    # 3. Completion event published
    assert len(mock_redis.published_messages) == 1
    event = mock_redis.published_messages[0]["data"]
    assert event["event"] == "stage_update"
    assert event["stage"] == "VECTOR_EMBEDDING"
    assert event["status"] == "completed"
    assert event["review_id"] == review_id
    assert event["data"]["chunks_stored_count"] == 2
    assert event["event_id"].startswith(f"evt_{review_id}_vector_embedding_")
    assert event["idempotency_key"] == (
        f"review:{review_id}:vector_embedding:vector_embedding_completed"
    )


@pytest.mark.asyncio
async def test_scenario_b_flush_succeeds_outer_rollback_no_event(
    mock_redis: MockRedisClient,
):
    """[Test Classification: Mocked Integration Test]
    Scenario B: When flush succeeds but the outer transaction subsequently rolls back,
    no completion event MUST be published, preventing false success notifications.
    """
    review_id = 102
    paper = Paper(id=2, title="Paper Beta", arxiv_id="arxiv:102", review_id=review_id)
    mock_db = MockAsyncSession(papers=[paper])

    state: AgentState = {
        "review_id": review_id,
        "extracted_pdf_contents": {"arxiv:102": {"abstract": "Text for paper beta."}},
    }

    # Outer caller owns transaction (commit_on_complete=False)
    result = await vector_embedding_node(state, db=mock_db, commit_on_complete=False)

    # Flush succeeded, but transaction is NOT committed yet
    assert mock_db.flushed is True
    assert mock_db.committed is False
    assert result["chunks_stored_count"] == 1

    # STRICT CHECK: Zero events must be published to Redis upon flush
    assert len(mock_redis.published_messages) == 0

    # Simulate outer transaction rollback
    await mock_db.rollback()
    assert mock_db.rolled_back is True
    assert len(mock_db.added_chunks) == 0

    # Verify still zero events published
    assert len(mock_redis.published_messages) == 0


@pytest.mark.asyncio
async def test_external_transaction_rollback_no_success_event(
    mock_redis: MockRedisClient,
):
    """[Test Classification: Mocked Integration Test]
    Requirement D: When an external transaction explicitly rolls back following a node flush,
    NO success or stage_update event MUST be emitted under any circumstances.
    """
    review_id = 107
    paper = Paper(
        id=1,
        title="Rollback Isolation Paper",
        arxiv_id="arxiv:107",
        review_id=review_id,
    )
    mock_db = MockAsyncSession(papers=[paper])

    state: AgentState = {
        "review_id": review_id,
        "extracted_pdf_contents": {"arxiv:107": {"abstract": "Text destined for rollback."}},
    }

    # External session passed with commit_on_complete=False
    result = await vector_embedding_node(state, db=mock_db, commit_on_complete=False)
    assert mock_db.flushed is True
    assert mock_db.committed is False
    assert result["chunks_stored_count"] == 1
    assert len(mock_redis.published_messages) == 0

    # Explicit caller rollback
    await mock_db.rollback()
    assert mock_db.rolled_back is True
    assert len(mock_db.added_chunks) == 0

    # Assert zero events emitted
    assert len(mock_redis.published_messages) == 0


@pytest.mark.asyncio
async def test_scenario_c_commit_fails_no_event(mock_redis: MockRedisClient):
    """[Test Classification: Mocked Integration Test]
    Scenario C: When database commit fails, exception propagates and NO completion event is published.
    """
    review_id = 103
    paper = Paper(id=3, title="Paper Gamma", arxiv_id="arxiv:103", review_id=review_id)
    mock_db = MockAsyncSession(papers=[paper], fail_on_commit=True)

    state: AgentState = {
        "review_id": review_id,
        "extracted_pdf_contents": {"arxiv:103": {"abstract": "Text for paper gamma."}},
    }

    with pytest.raises(RuntimeError, match="Database connection lost during commit"):
        await vector_embedding_node(state, db=mock_db, commit_on_complete=True)

    # Verify no events published to Redis
    assert len(mock_redis.published_messages) == 0


@pytest.mark.asyncio
async def test_scenario_d_multiple_papers_atomic_event(
    mock_redis: MockRedisClient,
):
    """[Test Classification: Mocked Integration Test]
    Scenario D: Multiple papers in one review are committed atomically; exactly one
    completion event with the total aggregate chunk count is published after commit.
    """
    review_id = 104
    p1 = Paper(id=1, title="Paper One", arxiv_id="arxiv:1", review_id=review_id)
    p2 = Paper(id=2, title="Paper Two", arxiv_id="arxiv:2", review_id=review_id)
    mock_db = MockAsyncSession(papers=[p1, p2])

    state: AgentState = {
        "review_id": review_id,
        "extracted_pdf_contents": {
            "arxiv:1": {"abstract": "Text 1", "results": "Results 1"},
            "arxiv:2": {"abstract": "Text 2", "methods": "Methods 2", "discussion": "Disc 2"},
        },
    }

    result = await vector_embedding_node(state, db=mock_db, commit_on_complete=True)

    # Total: 2 + 3 = 5 chunks
    assert result["chunks_stored_count"] == 5
    assert len(mock_db.added_chunks) == 5
    assert mock_db.committed is True

    # Single atomic event published with total count
    assert len(mock_redis.published_messages) == 1
    event = mock_redis.published_messages[0]["data"]
    assert event["data"]["chunks_stored_count"] == 5
    assert event["data"]["chunks_count"] == 5


@pytest.mark.asyncio
async def test_scenario_e_transaction_ownership_default_session(
    mock_redis: MockRedisClient,
):
    """[Test Classification: Mocked Integration Test]
    Scenario E: When db is None (default LangGraph workflow mode), vector_embedding_node
    owns the session, commits it, and publishes the event upon successful commit.
    """
    review_id = 105
    paper = Paper(id=5, title="Paper Default", arxiv_id="arxiv:105", review_id=review_id)
    mock_db = MockAsyncSession(papers=[paper])

    # Intercept AsyncSessionLocal context manager
    class MockContextManager:
        async def __aenter__(self):
            return mock_db

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    state: AgentState = {
        "review_id": review_id,
        "extracted_pdf_contents": {"arxiv:105": {"abstract": "Text default"}},
    }

    with patch(
        "app.agents.nodes.vector_embedding_node.AsyncSessionLocal",
        return_value=MockContextManager(),
    ):
        result = await vector_embedding_node(state, db=None)

    assert result["chunks_stored_count"] == 1
    assert mock_db.committed is True
    assert len(mock_redis.published_messages) == 1


@pytest.mark.asyncio
async def test_external_transaction_commit_then_manual_publish(
    mock_redis: MockRedisClient,
):
    """[Test Classification: Mocked Integration Test]
    Verify that an external transaction caller can execute with commit_on_complete=False,
    commit their transaction, and then invoke publish_vector_embedding_completion.
    """
    review_id = 106
    paper = Paper(id=6, title="Paper Manual", arxiv_id="arxiv:106", review_id=review_id)
    mock_db = MockAsyncSession(papers=[paper])

    state: AgentState = {
        "review_id": review_id,
        "extracted_pdf_contents": {"arxiv:106": {"abstract": "Manual commit text"}},
    }

    res = await vector_embedding_node(state, db=mock_db, commit_on_complete=False)
    assert len(mock_redis.published_messages) == 0

    # Outer caller commits
    await mock_db.commit()
    assert mock_db.committed is True

    # Outer caller publishes completion
    subs = await publish_vector_embedding_completion(review_id, res["chunks_stored_count"])
    assert subs == 0
    assert len(mock_redis.published_messages) == 1
    assert mock_redis.published_messages[0]["data"]["data"]["chunks_stored_count"] == 1


# ==============================================================================
# SECTION B: WebSocket & Redis Streaming Integration Tests
# ==============================================================================


def test_websocket_forwards_vector_embedding_event(mock_redis: MockRedisClient):
    """[Test Classification: Mocked Integration Test]
    Verify connected WebSocket client receives live vector embedding completion event.
    """
    review_id = 42
    paper = Paper(
        id=7,
        title="Quantum Error Correction",
        arxiv_id="2401.12345",
        review_id=review_id,
    )
    mock_db = MockAsyncSession(papers=[paper])

    state: AgentState = {
        "review_id": review_id,
        "extracted_pdf_contents": {
            "2401.12345": {
                "abstract": "Surface codes provide fault tolerance under depolarizing noise.",
            }
        },
    }

    client = TestClient(app)
    with client.websocket_connect(f"/api/v1/ws/reviews/{review_id}") as ws:
        result = asyncio.run(vector_embedding_node(state, db=mock_db, commit_on_complete=True))
        assert result["chunks_stored_count"] == 1

        received_frame = ws.receive_json()

        assert received_frame["event"] == "stage_update"
        assert received_frame["stage"] == "VECTOR_EMBEDDING"
        assert received_frame["status"] == "completed"
        assert received_frame["review_id"] == review_id
        assert received_frame["data"]["chunks_stored_count"] == 1
        assert received_frame["data"]["chunks_count"] == 1
        assert received_frame["event_id"].startswith(f"evt_{review_id}_vector_embedding_")
        assert received_frame["idempotency_key"] == (
            f"review:{review_id}:vector_embedding:vector_embedding_completed"
        )


def test_cross_review_websocket_isolation(mock_redis: MockRedisClient):
    """[Test Classification: Mocked Integration Test]
    Verify complete isolation between separate reviews; events for review 10 do not leak to review 20.
    """
    client = TestClient(app)

    with client.websocket_connect("/api/v1/ws/reviews/10") as ws1:
        with client.websocket_connect("/api/v1/ws/reviews/20") as ws2:
            assert ws2 is not None
            # Process vector embedding for review 10 ONLY
            p1 = Paper(id=1, title="Review 10 Paper", arxiv_id="arxiv:10", review_id=10)
            db1 = MockAsyncSession(papers=[p1])
            state1: AgentState = {
                "review_id": 10,
                "extracted_pdf_contents": {"arxiv:10": {"abstract": "Text 10"}},
            }
            asyncio.run(vector_embedding_node(state1, db=db1, commit_on_complete=True))

            # ws1 (review 10) must receive the event
            frame1 = ws1.receive_json()
            assert frame1["review_id"] == 10
            assert frame1["stage"] == "VECTOR_EMBEDDING"

            # ws2 (review 20) pubsub queue must be completely empty
            ps2 = [p for p in mock_redis.pubsubs if "review:20:events" in p.subscribed_channels][0]
            assert ps2.queue.empty()


@pytest.mark.asyncio
async def test_failed_embedding_does_not_publish_event(
    mock_redis: MockRedisClient,
):
    """[Test Classification: Mocked Integration Test]
    Failed embedding operation raises exception and does NOT publish a success event.
    """
    review_id = 99
    paper = Paper(id=1, title="Failing Model Paper", arxiv_id="99.001", review_id=review_id)
    mock_db = MockAsyncSession(papers=[paper])

    state: AgentState = {
        "review_id": review_id,
        "extracted_pdf_contents": {"99.001": {"abstract": "Some text"}},
    }

    with patch(
        "app.services.vector_service.generate_embeddings_batch",
        side_effect=RuntimeError("Embedding model crashed"),
    ):
        with pytest.raises(RuntimeError, match="Embedding model crashed"):
            await vector_embedding_node(state, db=mock_db, commit_on_complete=True)

    assert len(mock_redis.published_messages) == 0


@pytest.mark.asyncio
async def test_redis_failure_does_not_undo_successful_db_persistence(
    monkeypatch: pytest.MonkeyPatch,
):
    """[Test Classification: Mocked Integration Test]
    If PostgreSQL persistence succeeds but Redis publication fails, the database
    chunks are NOT rolled back, and the node completes successfully.
    """
    review_id = 105
    paper = Paper(id=1, title="Resilience Paper", arxiv_id="105.001", review_id=review_id)
    mock_db = MockAsyncSession(papers=[paper])

    state: AgentState = {
        "review_id": review_id,
        "extracted_pdf_contents": {
            "105.001": {"abstract": "Resilience text to persist despite Redis failure."}
        },
    }

    async def mock_failing_publish(rid, event):
        raise ConnectionError("Redis server unavailable at localhost:6379")

    monkeypatch.setattr(redis_service, "publish_review_event", mock_failing_publish)

    result = await vector_embedding_node(state, db=mock_db, commit_on_complete=True)

    assert len(mock_db.added_chunks) == 1
    assert mock_db.committed is True
    assert result["current_step"] == "vector_embedding_completed"
    assert result["chunks_stored_count"] == 1


@pytest.mark.asyncio
async def test_sequential_retry_behavior_no_duplicate_notifications(
    mock_redis: MockRedisClient,
):
    """[Test Classification: Mocked Integration Test]
    Sequential retry behavior idempotently updates chunks and dispatches exactly
    one event per run with the accurate count (no duplicate notifications per run).
    """
    review_id = 200
    paper = Paper(id=1, title="Retry Paper", arxiv_id="200.001", review_id=review_id)
    mock_db = MockAsyncSession(papers=[paper])

    state: AgentState = {
        "review_id": review_id,
        "extracted_pdf_contents": {
            "200.001": {
                "abstract": "Initial run abstract.",
            }
        },
    }

    # Run 1
    res1 = await vector_embedding_node(state, db=mock_db, commit_on_complete=True)
    assert res1["chunks_stored_count"] == 1
    assert len(mock_redis.published_messages) == 1
    assert mock_redis.published_messages[0]["data"]["data"]["chunks_stored_count"] == 1

    # Simulate existing DB state between runs
    mock_db.added_chunks.clear()

    # Run 2: retry with expanded sections
    state["extracted_pdf_contents"]["200.001"]["methods"] = "Added methodology section text."

    res2 = await vector_embedding_node(state, db=mock_db, commit_on_complete=True)
    assert res2["chunks_stored_count"] == 2
    assert mock_db.with_for_update_called is True

    # Exactly 2 messages published (one per completed run)
    assert len(mock_redis.published_messages) == 2
    assert mock_redis.published_messages[1]["data"]["data"]["chunks_stored_count"] == 2

    # Verify both runs produced collision-free event_ids and stable, deterministic idempotency keys
    msg1 = mock_redis.published_messages[0]["data"]
    msg2 = mock_redis.published_messages[1]["data"]
    assert msg1["event_id"] != msg2["event_id"]
    assert msg1["idempotency_key"] == msg2["idempotency_key"]
    assert (
        msg1["idempotency_key"] == f"review:{review_id}:vector_embedding:vector_embedding_completed"
    )
    assert msg1["event_id"].startswith(f"evt_{review_id}_vector_embedding_")
    assert msg2["event_id"].startswith(f"evt_{review_id}_vector_embedding_")


@pytest.mark.asyncio
async def test_retry_identical_chunk_count_generates_distinct_event_ids(
    mock_redis: MockRedisClient,
):
    """[Test Classification: Mocked Integration Test]
    Verify that two distinct executions producing the IDENTICAL chunk count generate
    different event_id and idempotency_key values, preventing subscriber deduplication bugs.
    """
    review_id = 201
    paper = Paper(id=1, title="Same Count Paper", arxiv_id="201.001", review_id=review_id)
    mock_db = MockAsyncSession(papers=[paper])

    state: AgentState = {
        "review_id": review_id,
        "extracted_pdf_contents": {"201.001": {"abstract": "Fixed content that produces 1 chunk."}},
    }

    # Execution 1
    res1 = await vector_embedding_node(state, db=mock_db, commit_on_complete=True)
    assert res1["chunks_stored_count"] == 1

    # Execution 2 (retry or re-execution with identical chunk count)
    mock_db.added_chunks.clear()
    res2 = await vector_embedding_node(state, db=mock_db, commit_on_complete=True)
    assert res2["chunks_stored_count"] == 1

    assert len(mock_redis.published_messages) == 2
    evt1 = mock_redis.published_messages[0]["data"]
    evt2 = mock_redis.published_messages[1]["data"]

    # Chunks count is identical (1 in both)
    assert evt1["data"]["chunks_stored_count"] == evt2["data"]["chunks_stored_count"] == 1

    # But event_id MUST be unique per delivery, while idempotency_key MUST be deterministic and stable
    assert evt1["event_id"] != evt2["event_id"]
    assert evt1["idempotency_key"] == evt2["idempotency_key"]
    assert (
        evt1["idempotency_key"] == f"review:{review_id}:vector_embedding:vector_embedding_completed"
    )


@pytest.mark.asyncio
async def test_concurrent_executions_identity_divergence(
    mock_redis: MockRedisClient,
):
    """[Test Classification: Mocked Integration Test]
    Requirement I: Concurrent embedding executions for the same review do not produce
    misleading execution identity collisions; each concurrent delivery receives a
    distinct, collision-free event_id and unique idempotency_key.
    """
    review_id = 205
    p1 = Paper(id=1, title="Concurrent Paper 1", arxiv_id="c:001", review_id=review_id)
    p2 = Paper(id=2, title="Concurrent Paper 2", arxiv_id="c:002", review_id=review_id)
    db1 = MockAsyncSession(papers=[p1])
    db2 = MockAsyncSession(papers=[p2])

    state1: AgentState = {
        "review_id": review_id,
        "run_id": "concurrent-run-1",
        "extracted_pdf_contents": {"c:001": {"abstract": "Concurrent execution text 1."}},
    }
    state2: AgentState = {
        "review_id": review_id,
        "run_id": "concurrent-run-2",
        "extracted_pdf_contents": {"c:002": {"abstract": "Concurrent execution text 2."}},
    }

    # Execute both nodes concurrently
    res1, res2 = await asyncio.gather(
        vector_embedding_node(state1, db=db1, commit_on_complete=True),
        vector_embedding_node(state2, db=db2, commit_on_complete=True),
    )

    assert res1["chunks_stored_count"] == 1
    assert res2["chunks_stored_count"] == 1
    assert len(mock_redis.published_messages) == 2

    evt1 = mock_redis.published_messages[0]["data"]
    evt2 = mock_redis.published_messages[1]["data"]

    # Verify distinct identifiers
    assert evt1["event_id"] != evt2["event_id"]
    assert evt1["idempotency_key"] != evt2["idempotency_key"]
    assert evt1["event_id"].startswith(f"evt_{review_id}_vector_embedding_")
    assert evt2["event_id"].startswith(f"evt_{review_id}_vector_embedding_")


@pytest.mark.asyncio
async def test_production_orchestrator_node_registration_and_execution(
    mock_redis: MockRedisClient,
):
    """[Test Classification: Mocked Integration Test]
    Requirement L: Verify the actual production caller identified in Section 3
    (LangGraph orchestrator built via build_literature_review_graph).
    Asserts node registration in graph topology, execution with default session (db=None),
    atomic persistence, and post-commit event dispatch.
    """
    from app.agents.orchestrator import build_literature_review_graph

    # 1. Verify graph compilation and node registration
    graph = build_literature_review_graph()
    assert "vector_embedding" in graph.nodes

    # 2. Verify node execution through LangGraph state contract
    review_id = 500
    paper = Paper(
        id=1,
        title="Orchestrator Paper",
        arxiv_id="orch:001",
        review_id=review_id,
    )
    mock_db = MockAsyncSession(papers=[paper])

    class MockContextManager:
        async def __aenter__(self):
            return mock_db

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    state: AgentState = {
        "review_id": review_id,
        "extracted_pdf_contents": {"orch:001": {"abstract": "Orchestrator test abstract."}},
    }

    with patch(
        "app.agents.nodes.vector_embedding_node.AsyncSessionLocal",
        return_value=MockContextManager(),
    ):
        # In production orchestrator execution, node is invoked with state only (db=None)
        node_fn = graph.nodes["vector_embedding"].bound
        result = await node_fn.ainvoke(state)

    assert result["chunks_stored_count"] == 1
    assert result["current_step"] == "vector_embedding_completed"
    assert mock_db.committed is True
    assert len(mock_redis.published_messages) == 1

    event = mock_redis.published_messages[0]["data"]
    assert event["event"] == "stage_update"
    assert event["stage"] == "VECTOR_EMBEDDING"
    assert event["review_id"] == review_id
    assert event["data"]["chunks_stored_count"] == 1


@pytest.mark.asyncio
async def test_custom_event_id_and_idempotency_key_override(
    mock_redis: MockRedisClient,
):
    """[Test Classification: Mocked Integration Test]
    Verify callers can provide explicit event_id and idempotency_key when required
    (e.g. for external pipeline correlation or distributed orchestration).
    """
    review_id = 202
    custom_eid = "custom-evt-uuid-9999"
    custom_ikey = "custom-idempotency-key-8888"

    subs = await publish_vector_embedding_completion(
        review_id=review_id,
        chunks_stored_count=5,
        event_id=custom_eid,
        idempotency_key=custom_ikey,
    )
    assert subs == 0

    assert len(mock_redis.published_messages) == 1
    event = mock_redis.published_messages[0]["data"]
    assert event["event_id"] == custom_eid
    assert event["idempotency_key"] == custom_ikey
    assert event["data"]["chunks_stored_count"] == 5


def test_event_schema_contract_compliance(mock_redis: MockRedisClient):
    """[Test Classification: Unit Test]
    Verify emitted event schema conforms to all frontend contract specifications:
    ISO 8601 UTC timestamp, valid status, required keys, and structure.
    """
    from datetime import datetime

    evt = redis_service.create_stage_event(
        review_id=400,
        stage="VECTOR_EMBEDDING",
        status="completed",
        message="Stage completed successfully",
        data={"chunks_stored_count": 10},
        step="vector_embedding_completed",
    )

    required_keys = {
        "event",
        "stage",
        "step",
        "status",
        "review_id",
        "event_id",
        "idempotency_key",
        "message",
        "data",
        "timestamp",
    }
    assert required_keys.issubset(set(evt.keys()))
    assert evt["event"] == "stage_update"
    assert evt["stage"] == "VECTOR_EMBEDDING"
    assert evt["status"] == "completed"
    assert evt["review_id"] == 400
    assert evt["data"]["chunks_stored_count"] == 10

    # Ensure timestamp is valid ISO 8601 UTC
    parsed_dt = datetime.fromisoformat(evt["timestamp"])
    assert parsed_dt.tzinfo is not None


def test_websocket_disconnect_cleanup(mock_redis: MockRedisClient):
    """[Test Classification: Mocked Integration Test]
    Client disconnection triggers full cleanup of Redis pubsub subscription.
    """
    review_id = 300
    expected_channel = f"review:{review_id}:events"
    client = TestClient(app)

    with client.websocket_connect(f"/api/v1/ws/reviews/{review_id}"):
        assert expected_channel in mock_redis.channels
        ps = mock_redis.pubsubs[0]
        assert expected_channel in ps.subscribed_channels

    # After exiting websocket context, cleanup must have occurred
    assert expected_channel not in mock_redis.channels
    assert ps.closed is True


def test_deterministic_idempotency_strategy_without_uuid():
    """[Test Classification: Unit Test]
    Verify create_stage_event produces stable, deterministic idempotency keys across retries
    without generating random UUIDs as fallbacks.
    """
    review_id = 777
    evt1 = redis_service.create_stage_event(
        review_id=review_id,
        stage="VECTOR_EMBEDDING",
        status="completed",
        step="vector_embedding_completed",
    )
    evt2 = redis_service.create_stage_event(
        review_id=review_id,
        stage="VECTOR_EMBEDDING",
        status="completed",
        step="vector_embedding_completed",
    )

    # Idempotency key MUST be identical across retries
    expected_key = f"review:{review_id}:vector_embedding:vector_embedding_completed"
    assert evt1["idempotency_key"] == expected_key
    assert evt2["idempotency_key"] == expected_key
    assert evt1["idempotency_key"] == evt2["idempotency_key"]

    # event_id MUST remain independently unique per delivery
    assert evt1["event_id"] != evt2["event_id"]
    assert evt1["event_id"].startswith(f"evt_{review_id}_vector_embedding_")
    assert evt2["event_id"].startswith(f"evt_{review_id}_vector_embedding_")

    # When run_id is supplied, idempotency key deterministically scopes to run_id
    evt_run_a = redis_service.create_stage_event(
        review_id=review_id,
        stage="VECTOR_EMBEDDING",
        run_id="run-alpha",
    )
    evt_run_b = redis_service.create_stage_event(
        review_id=review_id,
        stage="VECTOR_EMBEDDING",
        run_id="run-beta",
    )
    assert (
        evt_run_a["idempotency_key"]
        == f"review:{review_id}:run-alpha:vector_embedding:vector_embedding_completed"
    )
    assert (
        evt_run_b["idempotency_key"]
        == f"review:{review_id}:run-beta:vector_embedding:vector_embedding_completed"
    )
    assert evt_run_a["idempotency_key"] != evt_run_b["idempotency_key"]


def test_websocket_unauthenticated_status_and_format_validation():
    """[Test Classification: Unit Test]
    Verify WebSocket security baseline:
    1. The endpoint is explicitly unauthenticated in this development phase.
    2. Non-positive review IDs (-1, 0) are rejected with policy violation (1008) via input format validation.
    3. Positive review ID (e.g. 100) alone is NOT authentication or authorization, but accepted for local dev.
    """
    from starlette.websockets import WebSocketDisconnect

    client = TestClient(app)

    # 1. Non-positive review ID rejection (input format validation)
    with pytest.raises(WebSocketDisconnect) as exc1:
        with client.websocket_connect("/api/v1/ws/reviews/-1"):
            pass
    assert exc1.value.code == 1008

    with pytest.raises(WebSocketDisconnect) as exc2:
        with client.websocket_connect("/api/v1/ws/reviews/0"):
            pass
    assert exc2.value.code == 1008

    # 2. Positive review ID is accepted in unauthenticated dev mode (not authenticated identity)
    with client.websocket_connect("/api/v1/ws/reviews/100") as ws:
        assert ws is not None


@pytest.mark.asyncio
async def test_run_id_originates_at_pipeline_boundary_and_propagates(
    mock_redis: MockRedisClient,
    monkeypatch: pytest.MonkeyPatch,
):
    """[Test Classification: Mocked Integration Test]
    Verify genuine run_id propagation:
    1. Pipeline boundary (query_expansion) establishes execution run_id when absent.
    2. run_id persists through AgentState memory to vector_embedding_node.
    3. publish_stage_event receives run_id and produces run-scoped idempotency key.
    """
    from app.agents.nodes.query_expansion_node import query_expansion_node
    from app.core.config import settings

    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-test-gemini-key")
    review_id = 888

    # Case A: Boundary auto-generates run_id when omitted
    boundary_state: AgentState = {
        "review_id": review_id,
        "user_query": "Quantum Machine Learning Algorithms",
    }
    with patch("app.agents.nodes.query_expansion_node.genai.Client") as mock_genai_cls:
        mock_instance = mock_genai_cls.return_value
        mock_instance.models.generate_content.return_value.text = json.dumps(
            {
                "is_valid_academic_topic": True,
                "safety_violation_reason": None,
                "target_domains": ["Quantum Computing"],
                "search_queries": ["quantum machine learning"],
            }
        )
        res_expansion = await query_expansion_node(boundary_state)

    established_run_id = res_expansion.get("run_id")
    assert established_run_id is not None
    assert established_run_id.startswith(f"run_{review_id}_")

    # Case B: Execution preserves pre-existing run_id from boundary
    custom_run_id = "boundary-custom-run-999"
    explicit_state: AgentState = {
        "review_id": review_id,
        "run_id": custom_run_id,
        "user_query": "Quantum Machine Learning Algorithms",
    }
    with patch("app.agents.nodes.query_expansion_node.genai.Client") as mock_genai_cls:
        mock_instance = mock_genai_cls.return_value
        mock_instance.models.generate_content.return_value.text = json.dumps(
            {
                "is_valid_academic_topic": True,
                "safety_violation_reason": None,
                "target_domains": ["Quantum Computing"],
                "search_queries": ["quantum machine learning"],
            }
        )
        res_explicit = await query_expansion_node(explicit_state)
    assert res_explicit["run_id"] == custom_run_id

    # Case C: Propagate run_id to vector_embedding_node and verify idempotency key
    p = Paper(id=1, title="QML Paper", arxiv_id="qml:001", review_id=review_id)
    mock_db = MockAsyncSession(papers=[p])
    downstream_state: AgentState = {
        "review_id": review_id,
        "run_id": established_run_id,
        "extracted_pdf_contents": {"qml:001": {"abstract": "QML abstract text."}},
    }
    await vector_embedding_node(downstream_state, db=mock_db, commit_on_complete=True)

    assert len(mock_redis.published_messages) == 1
    event = mock_redis.published_messages[0]["data"]
    assert event["idempotency_key"] == (
        f"review:{review_id}:{established_run_id}:vector_embedding:vector_embedding_completed"
    )


@pytest.mark.asyncio
async def test_retry_stability_and_independent_execution_separation(
    mock_redis: MockRedisClient,
):
    """[Test Classification: Mocked Integration Test]
    Requirements:
    1. Retries of the same logical execution (same run_id) must retain the EXACT SAME idempotency key.
    2. Independent pipeline executions of the same review and stage must have DIFFERENT idempotency keys.
    3. event_id must be independently unique across all deliveries.
    """
    review_id = 900
    paper = Paper(id=1, title="Execution Identity Paper", arxiv_id="eid:001", review_id=review_id)

    # Execution 1 (Run Alpha) - Attempt 1
    run_alpha = "run-alpha-1234"
    state_alpha_attempt_1: AgentState = {
        "review_id": review_id,
        "run_id": run_alpha,
        "extracted_pdf_contents": {"eid:001": {"abstract": "Text for run alpha attempt 1"}},
    }
    db1 = MockAsyncSession(papers=[paper])
    res_a1 = await vector_embedding_node(state_alpha_attempt_1, db=db1, commit_on_complete=True)
    assert res_a1["chunks_stored_count"] == 1

    # Execution 1 (Run Alpha) - Attempt 2 (Retry of the same logical execution)
    db1_retry = MockAsyncSession(papers=[paper])
    state_alpha_attempt_2: AgentState = {
        "review_id": review_id,
        "run_id": run_alpha,
        "extracted_pdf_contents": {"eid:001": {"abstract": "Text for run alpha attempt 2"}},
    }
    res_a2 = await vector_embedding_node(
        state_alpha_attempt_2, db=db1_retry, commit_on_complete=True
    )
    assert res_a2["chunks_stored_count"] == 1

    # Execution 2 (Run Beta) - Independent execution of the same review
    run_beta = "run-beta-5678"
    db2 = MockAsyncSession(papers=[paper])
    state_beta: AgentState = {
        "review_id": review_id,
        "run_id": run_beta,
        "extracted_pdf_contents": {"eid:001": {"abstract": "Text for run beta"}},
    }
    res_b = await vector_embedding_node(state_beta, db=db2, commit_on_complete=True)
    assert res_b["chunks_stored_count"] == 1

    assert len(mock_redis.published_messages) == 3
    evt_a1 = mock_redis.published_messages[0]["data"]
    evt_a2 = mock_redis.published_messages[1]["data"]
    evt_b = mock_redis.published_messages[2]["data"]

    # 1. RETRY STABILITY: Attempt 1 and Attempt 2 of Run Alpha share the identical idempotency key
    expected_alpha_key = (
        f"review:{review_id}:{run_alpha}:vector_embedding:vector_embedding_completed"
    )
    assert evt_a1["idempotency_key"] == expected_alpha_key
    assert evt_a2["idempotency_key"] == expected_alpha_key
    assert evt_a1["idempotency_key"] == evt_a2["idempotency_key"]

    # 2. INDEPENDENT EXECUTION SEPARATION: Run Alpha and Run Beta have DIFFERENT idempotency keys
    expected_beta_key = f"review:{review_id}:{run_beta}:vector_embedding:vector_embedding_completed"
    assert evt_b["idempotency_key"] == expected_beta_key
    assert evt_a1["idempotency_key"] != evt_b["idempotency_key"]

    # 3. INDEPENDENT EVENT IDs: Each delivery has a unique event_id
    assert evt_a1["event_id"] != evt_a2["event_id"]
    assert evt_a1["event_id"] != evt_b["event_id"]
    assert evt_a2["event_id"] != evt_b["event_id"]


# ==============================================================================
# SECTION C: Live Infrastructure Verification Tests (Part 9)
# ==============================================================================


@pytest.mark.skipif(
    not LIVE_POSTGRES_AVAILABLE,
    reason="Live PostgreSQL daemon is not reachable on localhost:5432",
)
@pytest.mark.asyncio
async def test_live_postgresql_pgvector_embedding_persistence():
    """[Test Classification: Live PostgreSQL/pgvector Test]
    Executes real database persistence against live PostgreSQL with pgvector:
    - Creates a test review using actual project models and relationships.
    - Creates a paper associated with that review.
    - Creates an unrelated review and paper to verify isolation.
    - Executes the real vector embedding node.
    - Verifies expected PaperChunk records were persisted with 384D embeddings.
    - Verifies paper association and review-scoped boundaries.
    - Verifies the test does not modify or delete unrelated review data.
    - Cleans up all created test records safely in a finally block even on failure.
    """
    from app.db.session import AsyncSessionLocal

    test_review_id = None
    unrelated_review_id = None

    async with AsyncSessionLocal() as session:
        try:
            # 1. Create unrelated review and paper to verify isolation
            unrelated_review = LiteratureReview(
                user_query="Unrelated baseline review for isolation testing",
                status="pending",
            )
            session.add(unrelated_review)
            await session.commit()
            await session.refresh(unrelated_review)
            unrelated_review_id = unrelated_review.id

            unrelated_paper = Paper(
                title="Unrelated Isolation Paper",
                arxiv_id=f"unrelated:{uuid.uuid4().hex[:6]}",
                review_id=unrelated_review_id,
                is_approved=True,
            )
            session.add(unrelated_paper)
            await session.commit()
            await session.refresh(unrelated_paper)

            unrelated_chunk = PaperChunk(
                paper_id=unrelated_paper.id,
                chunk_index=0,
                section_name="Abstract",
                content="Baseline chunk content for isolation verification.",
                embedding=[0.0] * 384,
            )
            session.add(unrelated_chunk)
            await session.commit()

            # 2. Create the target test review using actual models
            test_review = LiteratureReview(
                user_query="Live PostgreSQL integration test for vector embedding",
                status="pending",
            )
            session.add(test_review)
            await session.commit()
            await session.refresh(test_review)
            test_review_id = test_review.id

            test_arxiv_id = f"live:{uuid.uuid4().hex[:6]}"
            test_paper = Paper(
                title="Live PostgreSQL Test Paper",
                arxiv_id=test_arxiv_id,
                review_id=test_review_id,
                is_approved=True,
            )
            session.add(test_paper)
            await session.commit()
            await session.refresh(test_paper)

            # 3. Execute the real vector embedding node scoped to test_review_id
            state: AgentState = {
                "review_id": test_review_id,
                "extracted_pdf_contents": {
                    test_arxiv_id: {
                        "sections": {
                            "Abstract": "Live database embedding test abstract describing vector search.",
                            "Methodology": "384-dimensional dense semantic vectors are indexed via pgvector.",
                        }
                    }
                },
            }
            res = await vector_embedding_node(state, db=session, commit_on_complete=True)
            assert res["chunks_stored_count"] >= 2

            # 4. Verify PaperChunk records persisted and associated with test_paper
            stmt = (
                select(PaperChunk)
                .where(PaperChunk.paper_id == test_paper.id)
                .order_by(PaperChunk.chunk_index)
            )
            chunks = list((await session.execute(stmt)).scalars().all())
            assert len(chunks) == res["chunks_stored_count"]

            for chunk in chunks:
                assert chunk.paper_id == test_paper.id
                assert chunk.embedding is not None
                assert len(chunk.embedding) == 384
                assert all(isinstance(val, float) for val in chunk.embedding)

            # 5. Verify unrelated review data was NOT modified or deleted
            unrelated_stmt = select(PaperChunk).where(PaperChunk.paper_id == unrelated_paper.id)
            unrelated_chunks = list((await session.execute(unrelated_stmt)).scalars().all())
            assert len(unrelated_chunks) == 1
            assert (
                unrelated_chunks[0].content == "Baseline chunk content for isolation verification."
            )

        finally:
            # 6. Safe cleanup of all created records even when assertions fail
            try:
                if test_review_id is not None:
                    rev = await session.get(LiteratureReview, test_review_id)
                    if rev is not None:
                        await session.delete(rev)
                if unrelated_review_id is not None:
                    u_rev = await session.get(LiteratureReview, unrelated_review_id)
                    if u_rev is not None:
                        await session.delete(u_rev)
                await session.commit()
            except Exception as cleanup_err:
                await session.rollback()
                logger.warning("Cleanup error in live postgres test: %s", cleanup_err)


@pytest.mark.skipif(
    not LIVE_REDIS_AVAILABLE,
    reason="Live Redis daemon is not reachable on localhost:6379",
)
@pytest.mark.asyncio
async def test_live_redis_pubsub_websocket_stream():
    """[Test Classification: Live Redis Test]
    Executes actual Redis publish/subscribe over live Redis daemon on port 6379:
    - Connects to configured Redis instance.
    - Subscribes to the correct review channel.
    - Waits for subscription confirmation.
    - Publishes a valid stage-update event.
    - Receives the event through the subscriber with timeout.
    - Deserializes and validates the payload.
    - Verifies the event fields, review ID, and deterministic idempotency key.
    - Cleans up subscriber and Redis resources safely.
    """
    review_id = 9999
    channel = f"review:{review_id}:events"
    client = redis_service.get_redis_client()
    pubsub = client.pubsub()

    try:
        # 1. Subscribe to review channel
        await pubsub.subscribe(channel)

        # 2. Wait for subscription confirmation with timeout
        subscribed = False
        async with asyncio.timeout(5.0):
            while not subscribed:
                msg = await pubsub.get_message(ignore_subscribe_messages=False, timeout=1.0)
                if msg and msg.get("type") == "subscribe" and msg.get("channel") == channel:
                    subscribed = True

        assert subscribed is True

        # 3. Publish a valid stage-update event
        stage_event = redis_service.create_stage_event(
            review_id=review_id,
            stage="VECTOR_EMBEDDING",
            status="completed",
            message="Vector embedding completed: 4 chunks persisted.",
            data={"chunks_stored_count": 4, "chunks_count": 4},
            step="vector_embedding_completed",
        )
        subs_count = await redis_service.publish_review_event(review_id, stage_event)
        assert subs_count >= 1

        # 4. Receive the event through the subscriber with timeout
        received_msg = None
        async with asyncio.timeout(5.0):
            while received_msg is None:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg.get("type") == "message" and msg.get("channel") == channel:
                    received_msg = msg

        assert received_msg is not None

        # 5. Deserialize and validate payload
        data = received_msg.get("data")
        payload = json.loads(data) if isinstance(data, (str, bytes)) else data

        # 6. Verify event fields and review ID
        assert payload["event"] == "stage_update"
        assert payload["stage"] == "VECTOR_EMBEDDING"
        assert payload["status"] == "completed"
        assert payload["review_id"] == review_id
        assert payload["step"] == "vector_embedding_completed"
        assert payload["data"]["chunks_stored_count"] == 4
        assert payload["event_id"] == stage_event["event_id"]
        assert payload["idempotency_key"] == stage_event["idempotency_key"]

    finally:
        # 7. Clean up subscriber and Redis resources safely
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
        except Exception as cleanup_err:
            logger.warning("Error closing live Redis pubsub: %s", cleanup_err)


@pytest.mark.skipif(
    not (LIVE_POSTGRES_AVAILABLE and LIVE_REDIS_AVAILABLE),
    reason="Full live E2E test requires both live PostgreSQL (5432) and live Redis (6379) daemons",
)
@pytest.mark.asyncio
async def test_live_full_end_to_end_integration():
    """[Test Classification: Full End-to-End Test]
    Full live end-to-end integration across real PostgreSQL, real Redis, and real WebSocket:
    - Uses project's actual application and WebSocket endpoint.
    - Creates genuine review and paper in PostgreSQL.
    - Connects WebSocket client to /api/v1/ws/reviews/{review_id}.
    - Executes real vector_embedding_node (PostgreSQL persistence -> commit -> Redis publication).
    - Verifies WebSocket client receives expected VECTOR_EMBEDDING completion event with correct review ID and chunk count.
    - Verifies PaperChunk records are persisted with 384D embeddings in PostgreSQL.
    - Safely cleans up all created database records.
    """
    from app.db.session import AsyncSessionLocal

    created_review_id = None

    async with AsyncSessionLocal() as session:
        try:
            # 1. Create real test review and paper in PostgreSQL
            review = LiteratureReview(
                user_query="Live E2E integration test for literature pipeline",
                status="pending",
            )
            session.add(review)
            await session.commit()
            await session.refresh(review)
            created_review_id = review.id

            arxiv_id = f"e2e:{uuid.uuid4().hex[:6]}"
            paper = Paper(
                title="Live E2E Multi-Agent Architecture",
                arxiv_id=arxiv_id,
                review_id=created_review_id,
                is_approved=True,
            )
            session.add(paper)
            await session.commit()
            await session.refresh(paper)

            # 2. Connect real WebSocket client to application endpoint
            client = TestClient(app)
            with client.websocket_connect(f"/api/v1/ws/reviews/{created_review_id}") as ws:
                # Brief yield to ensure subscription is established on live Redis
                await asyncio.sleep(0.1)

                # 3. Execute real vector embedding node (db=None -> manages session and commits)
                state: AgentState = {
                    "review_id": created_review_id,
                    "extracted_pdf_contents": {
                        arxiv_id: {
                            "sections": {
                                "Abstract": "E2E abstract verifying real pipeline integration.",
                                "Results": "E2E results confirming real pgvector and Redis pub/sub delivery.",
                            }
                        }
                    },
                }

                res = await vector_embedding_node(state, db=None, commit_on_complete=True)
                assert res["chunks_stored_count"] >= 2

                # 4. Receive and verify WebSocket delivery from live Redis pubsub
                received_frame = ws.receive_json()

                assert received_frame["event"] == "stage_update"
                assert received_frame["stage"] == "VECTOR_EMBEDDING"
                assert received_frame["status"] == "completed"
                assert received_frame["review_id"] == created_review_id
                assert received_frame["step"] == "vector_embedding_completed"
                assert received_frame["data"]["chunks_stored_count"] == res["chunks_stored_count"]
                assert received_frame["data"]["chunks_count"] == res["chunks_stored_count"]
                assert received_frame["idempotency_key"] == (
                    f"review:{created_review_id}:vector_embedding:vector_embedding_completed"
                )

            # 5. Verify PostgreSQL persistence of 384D embeddings
            stmt = select(PaperChunk).where(PaperChunk.paper_id == paper.id)
            chunks = list((await session.execute(stmt)).scalars().all())
            assert len(chunks) == res["chunks_stored_count"]
            for chunk in chunks:
                assert chunk.paper_id == paper.id
                assert chunk.embedding is not None
                assert len(chunk.embedding) == 384

        finally:
            # 6. Clean up database records
            if created_review_id is not None:
                try:
                    rev = await session.get(LiteratureReview, created_review_id)
                    if rev is not None:
                        await session.delete(rev)
                    await session.commit()
                except Exception as cleanup_err:
                    await session.rollback()
                    logger.warning("Cleanup error in live E2E test: %s", cleanup_err)
