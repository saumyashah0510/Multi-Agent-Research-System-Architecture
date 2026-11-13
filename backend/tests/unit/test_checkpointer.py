"""Unit tests for LangGraph Checkpointer Factory (Issue BE-15)."""

import pytest
from app.agents import checkpointer as cp
from app.agents.checkpointer import get_checkpointer, sanitize_connection_string
from app.agents.orchestrator import build_literature_review_graph
from langgraph.checkpoint.base import empty_checkpoint
from langgraph.checkpoint.memory import MemorySaver


def _config():
    return {"configurable": {"thread_id": "be-15-thread", "checkpoint_ns": ""}}


def _metadata():
    return {"source": "input", "step": 0, "writes": {}, "parents": {}}


def test_checkpointer_force_memory():
    """Verify that force_memory=True returns a valid MemorySaver instance."""
    checkpointer = get_checkpointer(force_memory=True)
    assert isinstance(checkpointer, MemorySaver)


def test_orchestrator_compiles_with_custom_checkpointer():
    """Verify that build_literature_review_graph accepts and compiles with a custom checkpointer."""
    custom_saver = MemorySaver()
    compiled_graph = build_literature_review_graph(checkpointer=custom_saver)
    assert compiled_graph is not None
    assert hasattr(compiled_graph, "checkpointer")
    assert compiled_graph.checkpointer is custom_saver


def test_sanitize_connection_string():
    """asyncpg-style URLs are converted to psycopg3-compatible ones."""
    url = "postgresql+asyncpg://user:pw@host.neon.tech/db?ssl=require"
    assert (
        sanitize_connection_string(url) == "postgresql://user:pw@host.neon.tech/db?sslmode=require"
    )
    plain = "postgresql://user:pw@localhost/db"
    assert sanitize_connection_string(plain) == plain


def test_get_checkpointer_never_raises_without_event_loop(monkeypatch):
    """Outside an event loop the factory must fall back instead of crashing."""
    monkeypatch.setattr(cp, "_is_test_env", lambda: False)
    monkeypatch.setattr(cp, "_checkpointer_instance", None)
    assert isinstance(get_checkpointer(), MemorySaver)


@pytest.mark.asyncio
async def test_postgres_unavailable_falls_back_to_memory(monkeypatch):
    """A failing database must never break the pipeline; state still persists in memory."""
    import psycopg_pool

    class _BrokenPool:
        def __init__(self, *args, **kwargs):
            pass

        async def open(self, *args, **kwargs):
            raise RuntimeError("database unavailable")

        async def close(self):
            pass

    monkeypatch.setattr(cp, "_is_test_env", lambda: False)
    monkeypatch.setattr(cp, "_checkpointer_instance", None)
    monkeypatch.setattr(psycopg_pool, "AsyncConnectionPool", _BrokenPool)

    saver = get_checkpointer()
    checkpoint = empty_checkpoint()
    await saver.aput(_config(), checkpoint, _metadata(), {})
    restored = await saver.aget_tuple(_config())
    assert restored is not None
    assert restored.checkpoint["id"] == checkpoint["id"]


@pytest.mark.asyncio
async def test_checkpoint_snapshot_persistence():
    """Verify state snapshot writing and retrieval across a thread ID."""
    saver = get_checkpointer(force_memory=True)
    checkpoint = empty_checkpoint()

    saved_config = await saver.aput(_config(), checkpoint, _metadata(), {})
    assert saved_config["configurable"]["checkpoint_id"] == checkpoint["id"]

    restored = await saver.aget_tuple(_config())
    assert restored is not None
    assert restored.checkpoint["id"] == checkpoint["id"]
    assert restored.metadata["step"] == 0
