"""Paper search and approval API routes placeholder."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/", summary="List discovered papers for review")
async def list_papers():
    """Endpoint placeholder for listing candidate papers."""
    return {"papers": []}
