"""LangSmith observability and public run sharing helpers."""

import logging
import time
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def is_langsmith_enabled() -> bool:
    """Return True if LangSmith tracing is configured and enabled."""
    return bool(
        settings.LANGCHAIN_TRACING_V2.lower() in ("true", "1")
        and settings.LANGCHAIN_API_KEY.strip()
    )


def get_shared_run_url(
    run_id: str, max_retries: int = 3, retry_delay: float = 1.0
) -> Optional[str]:
    """Generate a public read-only shareable URL for a LangSmith run.

    Args:
        run_id: UUID of the LangGraph/LangChain execution run.
        max_retries: Number of retry attempts while waiting for trace queue flush.
        retry_delay: Delay in seconds between retries.

    Returns:
        Optional[str]: Public URL (e.g. https://smith.langchain.com/public/<id>/r),
        or None if LangSmith is not configured or sharing fails.
    """
    if not is_langsmith_enabled():
        return None

    try:
        from langsmith import Client

        client = Client(
            api_url=settings.LANGCHAIN_ENDPOINT,
            api_key=settings.LANGCHAIN_API_KEY,
        )

        for attempt in range(max_retries):
            try:
                return client.share_run(run_id)
            except Exception as exc:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    logger.warning("Failed to generate LangSmith shared run URL: %s", exc)
                    return None
    except Exception as exc:
        logger.warning("Failed to initialize LangSmith client: %s", exc)
        return None
