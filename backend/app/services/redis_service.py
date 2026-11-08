import json
import logging
import uuid
from datetime import datetime, timezone
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


async def publish_review_event(review_id: int, event_data: Dict[str, Any]) -> int:
    """Publish a real-time JSON event to Redis channel 'review:{review_id}:events'.

    Args:
        review_id: The ID of the review being processed.
        event_data: The event dictionary to serialize and broadcast.

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

    client = get_redis_client()
    try:
        subscribers_count = await client.publish(channel, serialized_val)
        return int(subscribers_count)
    except Exception as exc:
        logger.error(f"Failed to publish event to Redis channel '{channel}': {exc}")
        raise


def create_stage_event(
    review_id: int,
    stage: str,
    status: str = "completed",
    message: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    step: Optional[str] = None,
    event_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    run_id: Optional[Union[str, int]] = None,
) -> Dict[str, Any]:
    """Construct a standardized stage update event payload matching frontend schema.

    Generates a unique, collision-free event_id per delivery and a deterministic,
    execution-scoped idempotency_key when not explicitly provided by the caller.

    Deterministic idempotency strategy:
    Constructed from logical execution identity:
      - review ID
      - pipeline execution/run ID (if available via run_id or data)
      - stage (lowercased)
      - step (resolved step name)
    Does NOT use random UUIDs for idempotency keys, guaranteeing stable idempotency across retries.
    Maintains independently unique event_id per event delivery.
    """
    resolved_step = step or f"{stage.lower()}_{status}"
    resolved_eid = event_id or f"evt_{review_id}_{stage.lower()}_{uuid.uuid4().hex[:12]}"

    if idempotency_key is not None:
        resolved_key = idempotency_key
    else:
        # Resolve execution/run ID from parameter or event data payload
        resolved_run_id = run_id
        if resolved_run_id is None and data and isinstance(data, dict):
            resolved_run_id = (
                data.get("run_id") or data.get("pipeline_run_id") or data.get("execution_id")
            )

        if resolved_run_id is not None:
            resolved_key = f"review:{review_id}:{resolved_run_id}:{stage.lower()}:{resolved_step}"
        else:
            resolved_key = f"review:{review_id}:{stage.lower()}:{resolved_step}"

    return {
        "event": "stage_update",
        "stage": stage,
        "step": resolved_step,
        "status": status,
        "review_id": review_id,
        "event_id": resolved_eid,
        "idempotency_key": resolved_key,
        "message": message or f"Stage {stage} {status}.",
        "data": data or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def publish_stage_event(
    review_id: int,
    stage: str,
    status: str = "completed",
    message: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    step: Optional[str] = None,
    event_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    run_id: Optional[Union[str, int]] = None,
) -> int:
    """Publish a standardized stage update event through publish_review_event.

    Args:
        review_id: The ID of the review being processed.
        stage: The pipeline stage name (e.g. 'VECTOR_EMBEDDING').
        status: The execution status (default 'completed').
        message: Optional human-readable progress message.
        data: Optional dictionary containing stage metrics (e.g. chunk counts).
        step: Optional specific step name.
        event_id: Optional unique event ID for consumer deduplication.
        idempotency_key: Optional idempotency key for distributed delivery.
        run_id: Optional pipeline execution / run identifier.

    Returns:
        The number of Redis subscribers that received the message.
    """
    payload = create_stage_event(
        review_id=review_id,
        stage=stage,
        status=status,
        message=message,
        data=data,
        step=step,
        event_id=event_id,
        idempotency_key=idempotency_key,
        run_id=run_id,
    )
    return await publish_review_event(review_id, payload)
