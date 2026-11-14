"""LangGraph Checkpointer Factory with Persistent Neon PostgreSQL & Memory Fallback.

get_checkpointer() is synchronous and never raises. It returns a saver that is
safe to create at import time (no event loop needed). On first async use it
opens the Neon connection pool and creates the checkpoint tables.

Each thread is pinned to the backend it started on:
- Threads whose first write happens while PostgreSQL is unavailable stay in
  memory, so their state is never stranded when the database comes back.
- Threads already on PostgreSQL keep using it; a later database error is raised
  (state stays safe in Neon and can be resumed) instead of silently switching.
- A failed read never pins a thread and is never answered from memory for an
  unpinned thread: it may already exist in PostgreSQL.

The connection pool is bound to the event loop that created it. If the running
loop changes (for example, a new loop per test), the old pool is discarded and
a new one is opened in the current loop.
"""

import asyncio
import logging
import os
import sys
import time
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from app.core.config import settings

logger = logging.getLogger(__name__)

_RETRY_COOLDOWN_SECONDS = 30.0
_POOL_OPEN_TIMEOUT_SECONDS = 10.0
_SETUP_TIMEOUT_SECONDS = 15.0
_POOL_CLOSE_TIMEOUT_SECONDS = 5.0
_WRITE_OPS = frozenset({"aput", "aput_writes"})

# Global checkpointer cache
_checkpointer_instance: Optional[BaseCheckpointSaver] = None


def _is_test_env() -> bool:
    # The module-level graph in the reviews router is compiled at import time,
    # i.e. during pytest collection, when PYTEST_CURRENT_TEST is not set yet.
    # "pytest" in sys.modules is already true then, so CI uses MemorySaver even
    # if ENVIRONMENT=test is not exported in the workflow. Production never
    # imports pytest.
    if "pytest" in sys.modules or os.getenv("PYTEST_CURRENT_TEST"):
        return True
    # Settings has no ENVIRONMENT field, so also read the real environment variable.
    env = os.getenv("ENVIRONMENT") or getattr(settings, "ENVIRONMENT", "")
    return str(env).lower() == "test"


def sanitize_connection_string(url: str) -> str:
    """Convert a SQLAlchemy/asyncpg style URL into a psycopg3 connection string."""
    url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    parts = urlsplit(url)
    query = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        # asyncpg uses ?ssl=require, libpq/psycopg uses ?sslmode=require
        query.append(("sslmode" if key == "ssl" else key, value))
    return urlunsplit(parts._replace(query=urlencode(query)))


class LazyPostgresSaver(BaseCheckpointSaver):
    """Checkpointer that connects to Neon PostgreSQL lazily, with memory fallback.

    Creating it needs no event loop and no database. The pipeline only uses the
    async API (astream / aget_state); sync methods use the in-memory fallback.
    """

    def __init__(self) -> None:
        super().__init__()
        self._memory = MemorySaver()
        self._saver: Optional[BaseCheckpointSaver] = None
        self._pool = None
        self._lock: Optional[asyncio.Lock] = None
        self._retry_at = 0.0
        self._memory_threads: set[str] = set()  # threads pinned to memory
        self._pg_threads: set[str] = set()  # threads confirmed on PostgreSQL
        self._thread_locks: dict[str, asyncio.Lock] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    @staticmethod
    def _thread_id(config) -> str:
        return str(((config or {}).get("configurable") or {}).get("thread_id", ""))

    def _check_loop(self) -> None:
        """Drop connection state bound to a previous (closed) event loop."""
        loop = asyncio.get_running_loop()
        if self._loop is not None and self._loop is not loop:
            # The pool belongs to another event loop and cannot be reused.
            # It is not closed here: closing a pool from a different loop can
            # itself hang. PostgreSQL thread ownership (_pg_threads) stays valid.
            self._saver = None
            self._pool = None
            self._lock = None
            self._thread_locks.clear()
            self._retry_at = 0.0
        self._loop = loop

    async def _connect(self) -> Optional[BaseCheckpointSaver]:
        """Return the Postgres saver, or None while unavailable (cooldown applies)."""
        if self._saver is not None:
            return self._saver
        if time.monotonic() < self._retry_at:
            return None
        if self._lock is None:
            self._lock = asyncio.Lock()
        async with self._lock:
            if self._saver is not None:
                return self._saver
            # Recheck: another caller may have just failed while we waited.
            if time.monotonic() < self._retry_at:
                return None
            pool = None
            try:
                from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
                from psycopg.rows import dict_row
                from psycopg_pool import AsyncConnectionPool

                pool = AsyncConnectionPool(
                    conninfo=sanitize_connection_string(settings.DATABASE_URL),
                    max_size=10,
                    open=False,
                    kwargs={
                        "autocommit": True,
                        "prepare_threshold": 0,
                        "row_factory": dict_row,
                    },
                )
                await pool.open(wait=True, timeout=_POOL_OPEN_TIMEOUT_SECONDS)
                saver = AsyncPostgresSaver(pool)
                # Bound setup() so a stuck handshake or lock can never hang the pipeline.
                await asyncio.wait_for(saver.setup(), timeout=_SETUP_TIMEOUT_SECONDS)
                self._pool = pool
                self._saver = saver
                logger.info("Persistent Neon PostgreSQL checkpointer ready.")
                return saver
            except Exception as exc:
                logger.warning(
                    "Postgres checkpointer unavailable (%s). " "Falling back to MemorySaver.",
                    exc,
                )
                self._retry_at = time.monotonic() + _RETRY_COOLDOWN_SECONDS
                if pool is not None:
                    try:
                        await asyncio.wait_for(pool.close(), timeout=_POOL_CLOSE_TIMEOUT_SECONDS)
                    except Exception:  # nosec B110 - best-effort cleanup
                        pass
                return None

    async def _fallback(self, tid: str, config, op: str, args):
        """Serve from memory. Only a write proves a thread is new and pins it."""
        if op in _WRITE_OPS:
            self._memory_threads.add(tid)
        return await getattr(self._memory, op)(config, *args)

    async def _run(self, config, op: str, *args):
        """Run an async saver operation on the backend this thread is pinned to."""
        self._check_loop()
        tid = self._thread_id(config)

        # Fast paths: thread already pinned to a backend.
        if tid in self._memory_threads:
            return await getattr(self._memory, op)(config, *args)
        if tid in self._pg_threads and self._saver is not None:
            # Already on PostgreSQL: let errors surface so state is not split.
            return await getattr(self._saver, op)(config, *args)

        # First backend selection: serialize per thread so overlapping
        # operations cannot choose different backends.
        lock = self._thread_locks.setdefault(tid, asyncio.Lock())
        async with lock:
            if tid in self._memory_threads:
                return await getattr(self._memory, op)(config, *args)
            if tid in self._pg_threads and self._saver is not None:
                return await getattr(self._saver, op)(config, *args)

            saver = await self._connect()
            if saver is None:
                return await self._fallback(tid, config, op, args)

            try:
                result = await getattr(saver, op)(config, *args)
            except Exception as exc:
                if op not in _WRITE_OPS:
                    # A failed read on an unpinned thread may hide existing
                    # PostgreSQL state, so surface the error instead of
                    # returning an empty memory result.
                    raise
                logger.warning(
                    "Postgres checkpointer failed for thread %s (%s). "
                    "Using MemorySaver for this call.",
                    tid,
                    exc,
                )
                return await self._fallback(tid, config, op, args)

            self._pg_threads.add(tid)
            return result

    # ---- async API used by the LangGraph pipeline ----
    async def aget_tuple(self, config):
        return await self._run(config, "aget_tuple")

    async def alist(self, config, *, filter=None, before=None, limit=None):
        self._check_loop()
        if self._thread_id(config) in self._memory_threads:
            backend = self._memory
        else:
            backend = await self._connect() or self._memory
        async for item in backend.alist(config, filter=filter, before=before, limit=limit):
            yield item

    async def aput(self, config, checkpoint, metadata, new_versions):
        return await self._run(config, "aput", checkpoint, metadata, new_versions)

    async def aput_writes(self, config, writes, task_id, task_path=""):
        return await self._run(config, "aput_writes", writes, task_id, task_path)

    async def adelete_thread(self, thread_id):
        self._check_loop()
        tid = str(thread_id)
        lock = self._thread_locks.setdefault(tid, asyncio.Lock())
        async with lock:
            saver = await self._connect()
            if saver is not None:
                # If this raises, PostgreSQL ownership is preserved.
                await saver.adelete_thread(thread_id)
                self._pg_threads.discard(tid)
            self._memory.delete_thread(thread_id)
            self._memory_threads.discard(tid)

    # ---- sync API: in-memory fallback only ----
    def get_tuple(self, config):
        return self._memory.get_tuple(config)

    def list(self, config, *, filter=None, before=None, limit=None):
        return self._memory.list(config, filter=filter, before=before, limit=limit)

    def put(self, config, checkpoint, metadata, new_versions):
        return self._memory.put(config, checkpoint, metadata, new_versions)

    def put_writes(self, config, writes, task_id, task_path=""):
        return self._memory.put_writes(config, writes, task_id, task_path)


def get_checkpointer(force_memory: bool = False) -> BaseCheckpointSaver:
    """Retrieve the active LangGraph checkpointer instance.

    Never raises and needs no event loop. Returns MemorySaver in test
    environments or when force_memory=True; otherwise a cached
    LazyPostgresSaver that connects to Neon on first async use.
    """
    global _checkpointer_instance

    if force_memory or _is_test_env():
        return MemorySaver()

    if _checkpointer_instance is None:
        _checkpointer_instance = LazyPostgresSaver()
    return _checkpointer_instance
