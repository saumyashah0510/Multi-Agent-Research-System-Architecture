"""Redis caching service for academic search API results and session states.

Assignee Task (Issue BE-04):
- Connect to Redis using REDIS_URL from settings.
- Implement get_cached_query(key) and set_cached_query(key, value, expire_seconds) helper functions.
- Implement check_redis_connection() for health status pings.
"""

from typing import Optional

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


async def get_cached_query(key: str) -> str | None:
    """Retrieve cached search query result string from Redis."""
    client = get_redis_client()
    try:
        val = await client.get(key)
        return val
    except Exception:
        return None


async def set_cached_query(key: str, value: str, expire_seconds: int = 86400) -> bool:
    """Save query result string into Redis with an expiration TTL timer."""
    client = get_redis_client()
    try:
        await client.set(key, value, ex=expire_seconds)
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
