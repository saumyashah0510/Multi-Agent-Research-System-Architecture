"""WebSocket endpoint for real-time literature review pipeline streaming.

Assignee Task (Issue BE-09):
- Implement WebSocket route at /reviews/{review_id}
- Listen to Redis Pub/Sub channel f"review:{review_id}:events"
- Broadcast agent progress events to connected clients
"""

import asyncio
import inspect
import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.services.redis_service import get_redis_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/reviews/{review_id}")
async def websocket_review_stream(websocket: WebSocket, review_id: int):
    """Real-time WebSocket endpoint streaming agent execution progress.

    Subscribes to Redis Pub/Sub channel 'review:{review_id}:events' and
    forwards agent execution events as JSON frames to the connected client.
    """
    # Authorization & input validation: reject non-positive review IDs
    if review_id <= 0:
        await websocket.close(code=1008)
        return

    await websocket.accept()

    channel = f"review:{review_id}:events"
    redis_client = get_redis_client()
    pubsub = None

    try:
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel)
        logger.info(f"WebSocket client connected and subscribed to Redis channel: {channel}")
    except Exception as exc:
        logger.error(
            f"Failed to subscribe to Redis channel {channel} for review {review_id}: {exc}"
        )
        if pubsub is not None:
            try:
                if hasattr(pubsub, "aclose"):
                    await pubsub.aclose()
                elif hasattr(pubsub, "close"):
                    res = pubsub.close()
                    if inspect.isawaitable(res):
                        await res
            except Exception:
                pass
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=1011)
        return

    receiver_task: Optional[asyncio.Task] = None
    redis_task: Optional[asyncio.Task] = None
    has_error: bool = False

    async def monitor_disconnect():
        """Listen for incoming WebSocket messages or client disconnection."""
        try:
            while True:
                msg = await websocket.receive()
                if msg.get("type") == "websocket.disconnect":
                    break
        except WebSocketDisconnect:
            pass
        except Exception as err:
            logger.debug(f"WebSocket receive ended for review {review_id}: {err}")

    async def stream_redis_events():
        """Listen to Redis Pub/Sub channel and stream JSON frames to client."""
        try:
            async for message in pubsub.listen():
                if not message:
                    continue
                if message.get("type") == "message":
                    data = message.get("data")
                    if data is None:
                        continue

                    if isinstance(data, bytes):
                        data = data.decode("utf-8")

                    if isinstance(data, str):
                        try:
                            payload = json.loads(data)
                        except (json.JSONDecodeError, TypeError) as parse_err:
                            logger.warning(
                                f"Skipping malformed JSON from channel {channel}: {parse_err}"
                            )
                            continue
                    elif isinstance(data, dict):
                        payload = data
                    else:
                        continue

                    await websocket.send_json(payload)
        except asyncio.CancelledError:
            raise
        except (WebSocketDisconnect, RuntimeError):
            logger.debug(f"WebSocket disconnected during send for review {review_id}")
        except Exception as err:
            logger.error(f"Error streaming Redis events for review {review_id}: {err}")
            raise

    try:
        receiver_task = asyncio.create_task(monitor_disconnect())
        redis_task = asyncio.create_task(stream_redis_events())

        done, pending = await asyncio.wait(
            [receiver_task, redis_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as task_err:
                logger.debug(f"Pending task cancellation exception: {task_err}")

        # Check for unexpected exceptions in completed tasks
        for task in done:
            if not task.cancelled():
                exc = task.exception()
                if exc and not isinstance(exc, (WebSocketDisconnect, RuntimeError)):
                    has_error = True
                    logger.warning(f"Task finished with exception: {exc}")

    finally:
        # Guarantee cancellation and awaiting of any remaining tasks
        for task in (receiver_task, redis_task):
            if task is not None and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception:
                    pass

        # Cleanup Redis pubsub subscription
        if pubsub is not None:
            try:
                await pubsub.unsubscribe(channel)
            except Exception as exc:
                logger.debug(f"Error unsubscribing from Redis channel {channel}: {exc}")
            finally:
                try:
                    if hasattr(pubsub, "aclose"):
                        await pubsub.aclose()
                    elif hasattr(pubsub, "close"):
                        res = pubsub.close()
                        if inspect.isawaitable(res):
                            await res
                except Exception as exc:
                    logger.debug(f"Error closing Redis pubsub: {exc}")

        # Ensure WebSocket connection is closed if still connected
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                close_code = 1011 if has_error else 1000
                await websocket.close(code=close_code)
            except Exception:
                pass
        logger.info(f"Cleaned up WebSocket connection and Redis pubsub for review {review_id}")
