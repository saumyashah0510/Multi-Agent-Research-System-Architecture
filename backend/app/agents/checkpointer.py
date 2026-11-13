"""LangGraph Checkpointer Factory with Persistent Neon PostgreSQL & Memory Fallback.

- get_checkpointer() is synchronous and always safe to call: it returns the
  persistent Postgres saver once initialized, otherwise a shared MemorySaver.
- init_postgres_checkpointer() is awaited once at application startup to open
  the connection pool and create the checkpoint tables in Neon.
- close_checkpointer() closes the pool on application shutdown.
"""

import logging
from typing import Any, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global caches
_checkpointer_instance: Optional[BaseCheckpointSaver] = None  # Postgres saver
_memory_fallback: Optional[MemorySaver] = None  # shared in-memory fallback
_pool: Any = None


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


def get_checkpointer(force_memory: bool = False) -> BaseCheckpointSaver:
    """Retrieve the active LangGraph checkpointer instance.

    Never raises: returns the persistent Postgres saver if it has been
    initialized, otherwise a shared MemorySaver.
    """
    global _memory_fallback

    if force_memory or _is_test_env():
        return MemorySaver()

    if _checkpointer_instance is not None:
        return _checkpointer_instance

    if _memory_fallback is None:
        logger.info("Postgres checkpointer not initialized; using MemorySaver.")
        _memory_fallback = MemorySaver()
    return _memory_fallback


async def init_postgres_checkpointer() -> BaseCheckpointSaver:
    """Open the Neon connection pool and create checkpoint tables.

    Call once at startup. On any failure, logs a warning and falls back to
    MemorySaver so the pipeline keeps working.
    """
    global _checkpointer_instance, _pool

    if force_test := _is_test_env():
        return get_checkpointer(force_memory=force_test)

    if _checkpointer_instance is not None:
        return _checkpointer_instance

    pool = None
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from psycopg.rows import dict_row
        from psycopg_pool import AsyncConnectionPool

        conn_string = sanitize_connection_string(settings.DATABASE_URL)

        pool = AsyncConnectionPool(
            conninfo=conn_string,
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

        _pool = pool
        _checkpointer_instance = saver
        logger.info("Persistent Neon PostgreSQL checkpointer initialized.")
    except Exception as exc:
        logger.warning(
            "Could not initialize persistent Postgres checkpointer (%s). "
            "Falling back to MemorySaver.",
            exc,
        )
        if pool is not None:
            try:
                await pool.close()
            except Exception:  # nosec B110 - best-effort cleanup
                pass

    return get_checkpointer()


async def close_checkpointer() -> None:
    """Close the Postgres connection pool (call on application shutdown)."""
    global _checkpointer_instance, _pool

    if _pool is not None:
        try:
            await _pool.close()
        except Exception as exc:
            logger.warning("Error closing checkpointer pool: %s", exc)
    _pool = None
    _checkpointer_instance = None
