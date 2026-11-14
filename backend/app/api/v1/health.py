"""Health check API endpoint.

Assignee Task (Issue BE-01 / BE-02 / BE-04):
- Return API status, version, database connection health (BE-02), and Redis health (BE-04).
"""

import asyncio
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.redis_service import check_redis_connection

router = APIRouter()


@router.get("/health", summary="Perform API health check")
async def health_check(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Returns server status, database connection, and redis health check payload."""
    db_status = "disconnected"
    db_error = None
    try:
        await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=5.0)
        db_status = "connected"
    except Exception as e:
        db_status = "disconnected"
        db_error = str(e)
        print(f"HEALTH CHECK DB ERROR: {e}")

    redis_status = "disconnected"
    try:
        if await check_redis_connection():
            redis_status = "connected"
    except Exception:
        redis_status = "disconnected"

    is_healthy = db_status == "connected" and redis_status == "connected"

    res = {
        "status": "healthy" if is_healthy else "degraded",
        "service": "multi-agent-research-backend",
        "version": "1.0.0",
        "database": db_status,
        "redis": redis_status,
    }
    if db_error:
        res["database_error"] = db_error
    return res
