"""WebSocket endpoint for real-time literature review pipeline streaming.

Assignee Task (Issue BE-09):
- Implement WebSocket route at /reviews/{review_id}
- Listen to Redis Pub/Sub channel f"review:{review_id}:events"
- Broadcast agent progress events to connected clients
"""

from fastapi import APIRouter, WebSocket

router = APIRouter()


@router.websocket("/reviews/{review_id}")
async def websocket_review_stream(websocket: WebSocket, review_id: int):
    """Real-time WebSocket endpoint streaming agent execution progress.

    TODO (Assignee - BE-09):
    1. Accept WebSocket connection (await websocket.accept())
    2. Subscribe to Redis channel f"review:{review_id}:events"
    3. Stream incoming messages to client using await websocket.send_text() or send_json()
    4. Handle WebSocketDisconnect gracefully
    """
    await websocket.accept()
    # TODO (Assignee - BE-09): Add Redis Pub/Sub listener loop here
    await websocket.close()
