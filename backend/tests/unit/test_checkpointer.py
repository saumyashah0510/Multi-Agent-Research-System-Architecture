"""Unit tests for LangGraph Checkpointer Factory (Issue BE-15)."""

import asyncio

import pytest
from app.agents import checkpointer as cp
from app.agents.checkpointer import (
    LazyPostgresSaver,
    get_checkpointer,
    sanitize_connection_string,
)
from app.agents.orchestrator import build_literature_review_graph
from langgraph.checkpoint.base import BaseCheckpointSaver, empty_checkpoint
from langgraph.checkpoint.memory import MemorySaver


def _config(thread_id="be-15-thread"):
    return {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}


def _metadata():
    return {"source": "input", "step": 0, "writes": {}, "parents": {}}


def test_checkpointer_force_memory():
    """Verify that force_memory=True returns a valid MemorySaver instance."""
    checkpointer = get_checkpointer(force_memory=True)
    assert isinstance(checkpointer, MemorySaver)


def test_environment_variable_enables_test_mode(monkeypatch):
    """ENVIRONMENT=test must select MemorySaver without a live database."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    assert isinstance(get_checkpointer(), MemorySaver)


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


def test_get_checkpointer_is_safe_at_import_time(monkeypatch):
    """Outside an event loop (module-level graph compile) the factory must not fail."""
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setattr(cp, "_is_test_env", lambda: False)
    monkeypatch.setattr(cp, "_checkpointer_instance", None)
    saver = get_checkpointer()
    assert isinstance(saver, BaseCheckpointSaver)
    assert isinstance(saver, LazyPostgresSaver)
    assert get_checkpointer() is saver  # cached


@pytest.mark.asyncio
async def test_postgres_unavailable_falls_back_to_memory(monkeypatch):
    """A failing database must never break the pipeline; state still persists in memory."""
    import langgraph.checkpoint.postgres.aio  # noqa: F401  (import before patching)
    import psycopg_pool

    class _BrokenPool:
        def __init__(self, *args, **kwargs):
            pass

        def __class_getitem__(cls, item):
            return cls

        async def open(self, *args, **kwargs):
            raise RuntimeError("database unavailable")

        async def close(self):
            pass

    monkeypatch.setattr(psycopg_pool, "AsyncConnectionPool", _BrokenPool)

    saver = LazyPostgresSaver()
    checkpoint = empty_checkpoint()
    await saver.aput(_config(), checkpoint, _metadata(), {})
    restored = await saver.aget_tuple(_config())
    assert restored is not None
    assert restored.checkpoint["id"] == checkpoint["id"]


@pytest.mark.asyncio
async def test_concurrent_callers_share_one_failed_attempt(monkeypatch):
    """During an outage, concurrent callers must not each retry the connection."""
    import langgraph.checkpoint.postgres.aio  # noqa: F401  (import before patching)
    import psycopg_pool

    attempts = []

    class _SlowBrokenPool:
        def __init__(self, *args, **kwargs):
            attempts.append(1)

        def __class_getitem__(cls, item):
            return cls

        async def open(self, *args, **kwargs):
            await asyncio.sleep(0.05)
            raise RuntimeError("database unavailable")

        async def close(self):
            pass

    monkeypatch.setattr(psycopg_pool, "AsyncConnectionPool", _SlowBrokenPool)

    saver = LazyPostgresSaver()
    await asyncio.gather(*(saver.aget_tuple(_config(f"t{i}")) for i in range(10)))
    assert len(attempts) == 1


@pytest.mark.asyncio
async def test_fallback_thread_stays_in_memory_after_recovery():
    """A thread started during an outage must remain readable after Postgres recovers."""
    saver = LazyPostgresSaver()
    saver._retry_at = float("inf")  # simulate an outage

    first = empty_checkpoint()
    await saver.aput(_config("t1"), first, _metadata(), {})

    recovered = MemorySaver()  # stands in for the recovered Postgres saver
    saver._saver = recovered
    saver._retry_at = 0.0

    restored = await saver.aget_tuple(_config("t1"))
    assert restored is not None
    assert restored.checkpoint["id"] == first["id"]

    second = empty_checkpoint()
    await saver.aput(_config("t2"), second, _metadata(), {})
    assert await recovered.aget_tuple(_config("t2")) is not None
    assert await recovered.aget_tuple(_config("t1")) is None


@pytest.mark.asyncio
async def test_database_failure_after_init_is_handled():
    """After init, a DB error must keep existing thread state safe and not break new threads."""

    class _FlakySaver(MemorySaver):
        fail = False

        async def aput(self, config, checkpoint, metadata, new_versions):
            if self.fail:
                raise RuntimeError("connection lost")
            return await super().aput(config, checkpoint, metadata, new_versions)

    flaky = _FlakySaver()
    saver = LazyPostgresSaver()
    saver._saver = flaky

    first = empty_checkpoint()
    await saver.aput(_config("t1"), first, _metadata(), {})

    flaky.fail = True
    # Existing Postgres thread: the error surfaces and its state stays intact.
    with pytest.raises(RuntimeError):
        await saver.aput(_config("t1"), empty_checkpoint(), _metadata(), {})

    # New thread: falls back to memory instead of failing the review.
    second = empty_checkpoint()
    await saver.aput(_config("t2"), second, _metadata(), {})
    restored = await saver.aget_tuple(_config("t2"))
    assert restored is not None
    assert restored.checkpoint["id"] == second["id"]

    flaky.fail = False
    kept = await flaky.aget_tuple(_config("t1"))
    assert kept is not None
    assert kept.checkpoint["id"] == first["id"]


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


@pytest.mark.asyncio
async def test_failed_read_does_not_pin_thread_to_memory():
    """A failed read must not strand a thread that already exists in PostgreSQL."""

    class _FlakyReads(MemorySaver):
        fail = False

        async def aget_tuple(self, config):
            if self.fail:
                raise RuntimeError("connection lost")
            return await super().aget_tuple(config)

    pg = _FlakyReads()
    existing = empty_checkpoint()
    await pg.aput(_config("t1"), existing, _metadata(), {})  # persisted earlier

    saver = LazyPostgresSaver()
    saver._saver = pg

    pg.fail = True
    with pytest.raises(RuntimeError):
        await saver.aget_tuple(_config("t1"))
    assert "t1" not in saver._memory_threads

    pg.fail = False
    restored = await saver.aget_tuple(_config("t1"))
    assert restored is not None
    assert restored.checkpoint["id"] == existing["id"]


@pytest.mark.asyncio
async def test_failed_delete_keeps_postgres_ownership():
    """If deleting from PostgreSQL fails, the thread must stay owned by PostgreSQL."""

    class _FailingDelete(MemorySaver):
        async def adelete_thread(self, thread_id):
            raise RuntimeError("connection lost")

    saver = LazyPostgresSaver()
    saver._saver = _FailingDelete()

    await saver.aput(_config("t1"), empty_checkpoint(), _metadata(), {})
    assert "t1" in saver._pg_threads

    with pytest.raises(RuntimeError):
        await saver.adelete_thread("t1")

    assert "t1" in saver._pg_threads
    assert "t1" not in saver._memory_threads
    assert await saver.aget_tuple(_config("t1")) is not None


@pytest.mark.asyncio
async def test_concurrent_first_operations_use_one_backend():
    """Overlapping first operations on one thread must not split across backends."""
    calls = []

    class _SlowFailing(MemorySaver):
        async def aput(self, config, checkpoint, metadata, new_versions):
            calls.append(checkpoint["id"])
            await asyncio.sleep(0.05)
            raise RuntimeError("connection lost")

    saver = LazyPostgresSaver()
    saver._saver = _SlowFailing()

    await asyncio.gather(
        saver.aput(_config("t1"), empty_checkpoint(), _metadata(), {}),
        saver.aput(_config("t1"), empty_checkpoint(), _metadata(), {}),
    )

    assert len(calls) == 1  # the second call saw the thread already pinned
    assert "t1" in saver._memory_threads


@pytest.mark.asyncio
async def test_delete_keeps_shared_thread_lock():
    """Deleting a thread must not discard the lock other operations share."""
    saver = LazyPostgresSaver()
    saver._saver = MemorySaver()

    await saver.aput(_config("t1"), empty_checkpoint(), _metadata(), {})
    lock = saver._thread_locks["t1"]

    await saver.adelete_thread("t1")

    assert saver._thread_locks["t1"] is lock
    assert await saver.aget_tuple(_config("t1")) is None
