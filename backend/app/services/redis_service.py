import json
from typing import Any, Dict, List, Optional, Union

import redis.asyncio as aioredis

from app.core.config import settings

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
