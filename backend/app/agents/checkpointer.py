"""LangGraph Checkpointer Factory with Persistent Neon PostgreSQL & Memory Fallback.

get_checkpointer() is synchronous and never raises. It returns a saver that is
safe to create at import time (no event loop needed). On its first async use it
opens the Neon connection pool and creates the checkpoint tables. If the
database is unavailable it serves requests from an in-memory fallback and
retries the database after a short cooldown, so the literature review pipeline
never crashes because of the checkpointer.
"""

import asyncio
import logging
import time
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from app.core.config import settings

logger = logging.getLogger(__name__)

_RETRY_COOLDOWN_SECONDS = 30.0

# Global checkpointer cache
_checkpointer_instance: Optional[BaseCheckpointSaver] = None


def _is_test_env() -> bool:
    return str(getattr(settings, "ENVIRONMENT", "")).lower() == "test"


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

    async def _backend(self) -> BaseCheckpointSaver:
        if self._saver is not None:
            return self._saver
        if time.monotonic() < self._retry_at:
            return self._memory
        if self._lock is None:
            self._lock = asyncio.Lock()
        async with self._lock:
            if self._saver is not None:
                return self._saver
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
                await pool.open(wait=True, timeout=10)
                saver = AsyncPostgresSaver(pool)
                await saver.setup()
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
                        await pool.close()
                    except Exception:  # nosec B110 - best-effort cleanup
                        pass
                return self._memory

    # ---- async API used by the LangGraph pipeline ----
    async def aget_tuple(self, config):
        return await (await self._backend()).aget_tuple(config)

    async def alist(self, config, *, filter=None, before=None, limit=None):
        backend = await self._backend()
        async for item in backend.alist(config, filter=filter, before=before, limit=limit):
            yield item

    async def aput(self, config, checkpoint, metadata, new_versions):
        backend = await self._backend()
        return await backend.aput(config, checkpoint, metadata, new_versions)

    async def aput_writes(self, config, writes, task_id, task_path=""):
        backend = await self._backend()
        return await backend.aput_writes(config, writes, task_id, task_path)

    async def adelete_thread(self, thread_id):
        return await (await self._backend()).adelete_thread(thread_id)

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
