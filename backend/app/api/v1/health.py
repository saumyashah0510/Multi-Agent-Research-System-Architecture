"""Health check API endpoint placeholder.

Assignee Task (Issue BE-01 / BE-02 / BE-04):
- Return API status, version, database connection health (BE-02), and Redis health (BE-04).
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", summary="Perform API health check")
async def health_check():
    """Returns server status, database connection, and redis health check payload."""
    # TODO (Assignee - BE-01): Return basic status {"status": "healthy", "service": "multi-agent-research-backend", "version": "1.0.0"}
    # TODO (Assignee - BE-02): Add database ping check ("database": "connected")
    # TODO (Assignee - BE-04): Add Redis ping check ("redis": "connected")
    return {}
