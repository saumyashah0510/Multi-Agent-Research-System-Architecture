import json
import logging
from typing import Any, Dict, List, Optional, Union

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis client instance
redis_client: Optional[aioredis.Redis] = None


def get_redis_client() -> aioredis.Redis:
    """Get or create the global async Redis client instance."""
    global redis_client
    if redis_client is None:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
    return redis_client


async def get_cached_query(key: str, as_json: bool = False) -> Any | None:
    """Retrieve cached search query result from Redis.

    If as_json=True, deserializes JSON string into a Python dict or list.
    """
    client = get_redis_client()
    try:
        val = await client.get(key)
        if val is None:
            return None
        if as_json:
            return json.loads(val)
        return val
    except Exception:
        return None


async def set_cached_query(
    key: str,
    value: Union[str, Dict[str, Any], List[Any]],
    expire_seconds: int = 86400,
) -> bool:
    """Save query result string, dict, or list into Redis with an expiration TTL timer."""
    client = get_redis_client()
    try:
        if isinstance(value, (dict, list)):
            serialized_val = json.dumps(value)
        else:
            serialized_val = str(value)
        await client.set(key, serialized_val, ex=expire_seconds)
        return True
    except Exception:
        return False


async def check_redis_connection() -> bool:
    """Execute a ping check against the Redis server for health status."""
    client = get_redis_client()
    try:
        res = await client.ping()
        return bool(res)
    except Exception:
        return False


async def close_redis_client() -> None:
    """Close the global Redis client connection."""
    global redis_client
    if redis_client is not None:
        await redis_client.close()
        redis_client = None


async def publish_review_event(
    review_id: int,
    event_data: Dict[str, Any],
    client: Optional[aioredis.Redis] = None,
) -> int:
    """Publish a real-time JSON event to Redis channel 'review:{review_id}:events'.

    Args:
        review_id: The ID of the review being processed.
        event_data: The event dictionary to serialize and broadcast.
        client: Optional Redis client instance. If omitted, uses get_redis_client().

    Returns:
        The number of Redis subscribers that received the message.

    Raises:
        TypeError, ValueError: If event_data cannot be serialized to JSON.
        Exception: If Redis publication fails.
    """
    channel = f"review:{review_id}:events"
    try:
        serialized_val = json.dumps(event_data)
    except (TypeError, ValueError) as exc:
        logger.error(f"Failed to serialize review event for review {review_id}: {exc}")
        raise

    redis_cli = client if client is not None else get_redis_client()
    try:
        subscribers_count = await redis_cli.publish(channel, serialized_val)
        return int(subscribers_count)
    except Exception as exc:
        logger.error(f"Failed to publish event to Redis channel '{channel}': {exc}")
        raise
