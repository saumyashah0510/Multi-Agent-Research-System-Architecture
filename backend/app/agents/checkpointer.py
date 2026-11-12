"""LangGraph Checkpointer Factory with Persistent Neon PostgreSQL & Memory Fallback.

Assignee Task (Issue BE-15):
- Implement get_postgres_checkpointer() using AsyncPostgresSaver backed by Neon DB.
- Ensure automated fallback to MemorySaver if connection fails or during unit tests.
- Manage saver connection lifecycle and table setup.
"""

import logging
from typing import Optional

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global checkpointer cache
_checkpointer_instance: Optional[BaseCheckpointSaver] = None


def get_checkpointer(force_memory: bool = False) -> BaseCheckpointSaver:
    """Retrieve the active LangGraph checkpointer instance.

    Guarantees zero-downtime fallback to MemorySaver if PostgreSQL checkpointer
    fails to initialize, ensuring the literature review pipeline never breaks.
    """
    global _checkpointer_instance

    if force_memory or getattr(settings, "ENVIRONMENT", "").lower() == "test":
        return MemorySaver()

    if _checkpointer_instance is not None:
        return _checkpointer_instance

    # TODO (Assignee - BE-15):
    # 1. Attempt to import AsyncPostgresSaver from langgraph.checkpoint.postgres.aio
    # 2. Convert settings.DATABASE_URL to standard postgresql:// connection string
    # 3. Create AsyncPostgresSaver instance using connection pool (or context manager)
    # 4. Call await saver.setup() to ensure checkpoint tables exist in Neon
    # 5. Cache in _checkpointer_instance and return
    # 6. Except Exception as e: log warning and fallback to MemorySaver()

    try:
        # Placeholder fallback until langgraph-checkpoint-postgres is configured
        logger.info("Initializing LangGraph checkpointer (BE-15)")
        _checkpointer_instance = MemorySaver()
        return _checkpointer_instance
    except Exception as exc:
        logger.warning(
            "Could not initialize persistent Postgres checkpointer (%s). Falling back to MemorySaver.",
            exc,
        )
        _checkpointer_instance = MemorySaver()
        return _checkpointer_instance
