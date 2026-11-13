"""LangGraph Checkpointer Factory with Persistent Neon PostgreSQL & Memory Fallback.

get_checkpointer() is synchronous and never raises. It returns a Postgres saver
that connects and creates its tables lazily on first async use. If the database
is unavailable, that saver transparently serves requests from an in-memory
fallback (and retries the database after a short cooldown), so the literature
review pipeline never crashes because of the checkpointer.
"""

import asyncio
import logging
import time
from typing import Any, Optional
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


def _build_postgres_saver() -> BaseCheckpointSaver:
    """Build an AsyncPostgresSaver that connects and sets up tables lazily."""
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from psycopg.rows import dict_row
    from psycopg_pool import AsyncConnectionPool

    class _ResilientPostgresSaver(AsyncPostgresSaver):
        """Opens the pool and creates tables on first use; falls back to memory."""

        def __init__(self, pool: Any) -> None:
            super().__init__(pool)
            self._pg_pool = pool
            self._pg_ready = False
            self._pg_retry_at = 0.0
            self._pg_init_lock: Optional[asyncio.Lock] = None
            self._memory_fallback = MemorySaver()

        async def _use_postgres(self) -> bool:
            if self._pg_ready:
                return True
            if time.monotonic() < self._pg_retry_at:
                return False
            if self._pg_init_lock is None:
                self._pg_init_lock = asyncio.Lock()
            async with self._pg_init_lock:
                if self._pg_ready:
                    return True
                try:
                    await self._pg_pool.open(wait=True, timeout=10)
                    await self.setup()
                    self._pg_ready = True
                    logger.info("Persistent Neon PostgreSQL checkpointer ready.")
                    return True
                except Exception as exc:
                    logger.warning(
                        "Postgres checkpointer unavailable (%s). " "Falling back to MemorySaver.",
                        exc,
                    )
                    self._pg_retry_at = time.monotonic() + _RETRY_COOLDOWN_SECONDS
                    try:
                        await self._pg_pool.close()
                    except Exception:  # nosec B110 - best-effort cleanup
                        pass
                    return False

        async def aget_tuple(self, config):
            if await self._use_postgres():
                return await super().aget_tuple(config)
            return await self._memory_fallback.aget_tuple(config)

        async def alist(self, config, *, filter=None, before=None, limit=None):
            if await self._use_postgres():
                async for item in super().alist(config, filter=filter, before=before, limit=limit):
                    yield item
            else:
                async for item in self._memory_fallback.alist(
                    config, filter=filter, before=before, limit=limit
                ):
                    yield item

        async def aput(self, config, checkpoint, metadata, new_versions):
            if await self._use_postgres():
                return await super().aput(config, checkpoint, metadata, new_versions)
            return await self._memory_fallback.aput(config, checkpoint, metadata, new_versions)

        async def aput_writes(self, config, writes, task_id, task_path=""):
            if await self._use_postgres():
                return await super().aput_writes(config, writes, task_id, task_path)
            return await self._memory_fallback.aput_writes(config, writes, task_id, task_path)

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
    return _ResilientPostgresSaver(pool)


def get_checkpointer(force_memory: bool = False) -> BaseCheckpointSaver:
    """Retrieve the active LangGraph checkpointer instance.

    Never raises. Returns MemorySaver in test environments or when
    force_memory=True; otherwise a cached Postgres-backed saver.
    """
    global _checkpointer_instance

    if force_memory or _is_test_env():
        return MemorySaver()

    if _checkpointer_instance is not None:
        return _checkpointer_instance

    try:
        _checkpointer_instance = _build_postgres_saver()
        return _checkpointer_instance
    except Exception as exc:
        # Not cached, so a later call (e.g. inside a running event loop) can retry.
        logger.warning(
            "Could not initialize persistent Postgres checkpointer (%s). "
            "Falling back to MemorySaver.",
            exc,
        )
        return MemorySaver()
