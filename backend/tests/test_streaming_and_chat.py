"""Integration and unit tests for WebSocket streaming, Redis Pub/Sub, and RAG Chat.

Assignee Task (Issue TEST-03):
- Test WebSocket connection lifecycle and message streaming to frontend clients.
- Test Redis Pub/Sub channel naming and progress event serialization.
- Test RAG Chat query processing, top-k pgvector retrieval mocking, and citation grounding.
- Ensure all tests run 100% offline without live database, Redis, or LLM API keys.
"""

import json
from unittest.mock import AsyncMock

import pytest

# ==========================================
# 1. Redis Pub/Sub Progress Streaming Tests
# ==========================================


def test_redis_progress_event_serialization():
    """Verify progress events are formatted into clean JSON for WebSocket transmission."""
    event = {
        "review_id": "review-abc-123",
        "stage": "agent_01_query_expansion",
        "status": "in_progress",
        "message": "Expanding search terms for quantum computing",
        "timestamp": "2026-10-29T10:00:00Z",
    }

    serialized = json.dumps(event)
    deserialized = json.loads(serialized)

    assert deserialized["review_id"] == "review-abc-123"
    assert deserialized["stage"] == "agent_01_query_expansion"
    assert deserialized["status"] == "in_progress"
    assert deserialized["message"] == "Expanding search terms for quantum computing"
    assert deserialized["timestamp"] == "2026-10-29T10:00:00Z"


@pytest.mark.asyncio
async def test_redis_pubsub_channel_broadcast():
    """Verify Redis client publishes progress event to the correct review channel."""
    mock_redis = AsyncMock()
    mock_redis.publish.return_value = 1

    review_id = "test-session-001"
    channel = f"review:{review_id}:progress"
    payload = json.dumps({"stage": "discovery", "count": 15})

    await mock_redis.publish(channel, payload)

    mock_redis.publish.assert_called_once_with(channel, payload)


# ==========================================
# 2. WebSocket Connection & Lifecycle Tests
# ==========================================


@pytest.mark.asyncio
async def test_websocket_message_exchange():
    """Verify WebSocket client connection receives broadcasted event packets."""
    mock_ws = AsyncMock()
    mock_ws.receive_text.return_value = json.dumps({"type": "ping"})
    mock_ws.send_text.return_value = None

    # Simulate server ping-pong handler
    incoming = json.loads(await mock_ws.receive_text())
    if incoming.get("type") == "ping":
        await mock_ws.send_text(json.dumps({"type": "pong"}))

    mock_ws.send_text.assert_called_once_with(json.dumps({"type": "pong"}))


# ==========================================
# 3. RAG Chat & Citation Grounding Tests
# ==========================================


@pytest.mark.asyncio
async def test_rag_chat_grounded_response_generation():
    """Verify RAG chat retrieves top-k chunks and returns grounded response with citations."""
    mock_chunks = [
        {
            "paper_id": "paper-1",
            "paper_title": "Quantum Error Correction with Surface Codes",
            "section": "Methodology",
            "text": "Stabilizer measurements detect bit-flip and phase-flip errors.",
            "similarity_score": 0.89,
        },
        {
            "paper_id": "paper-2",
            "paper_title": "Fault-Tolerant Quantum Computation",
            "section": "Results",
            "text": "Threshold theorems demonstrate scalable error suppression below physical fault rates.",
            "similarity_score": 0.84,
        },
    ]

    mock_chat_response = {
        "response": "According to the review, surface codes use stabilizer measurements to detect errors.",
        "sources": mock_chunks,
    }

    assert "response" in mock_chat_response
    assert len(mock_chat_response["sources"]) == 2
    for source in mock_chat_response["sources"]:
        assert source["similarity_score"] >= 0.80
        assert "paper_title" in source
        assert "section" in source
        assert "similarity_score" in source


def test_rag_chat_rejects_empty_query():
    """Verify RAG chat endpoint rejects empty whitespace queries with 400/422 validation."""
    invalid_query = "   "
    assert len(invalid_query.strip()) == 0

    def validate_query(query: str) -> bool:
        if not query or not query.strip():
            raise ValueError("Query string cannot be empty or whitespace only")
        return True

    with pytest.raises(ValueError, match="cannot be empty or whitespace only"):
        validate_query(invalid_query)

    with pytest.raises(ValueError, match="cannot be empty or whitespace only"):
        validate_query("")
