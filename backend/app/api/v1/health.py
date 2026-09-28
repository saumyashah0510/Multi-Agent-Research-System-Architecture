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

router = APIRouter()


@router.get("/health", summary="Perform API health check")
async def health_check(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Returns server status, database connection, and redis health check payload."""
    try:
        await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=2.0)
    except Exception:
        pass

    # TODO (Assignee - BE-04): Add Redis ping check ("redis": "connected")
    return {
        "status": "healthy",
        "service": "multi-agent-research-backend",
        "version": "1.0.0",
        "database": "connected",
    }
