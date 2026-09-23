"""Literature review task orchestration API routes placeholder."""

from fastapi import APIRouter

router = APIRouter()


@router.post("/", summary="Submit new literature review task")
async def create_review_task():
    """Endpoint placeholder for triggering literature review pipeline."""
    return {"status": "accepted", "task_id": "placeholder-id"}
