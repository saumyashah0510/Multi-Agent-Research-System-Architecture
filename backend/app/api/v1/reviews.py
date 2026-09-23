"""Literature review task orchestration API routes placeholder.

Assignee Task (Issue BE-01 / BE-03):
- POST /: Submit new research prompt and launch pipeline.
- GET /{review_id}: Fetch current review status and structured report.
- POST /{review_id}/approve: Submit human user approved paper selections.
"""

from fastapi import APIRouter

router = APIRouter()


@router.post("/", summary="Submit new literature review task")
async def create_review_task():
    """Endpoint placeholder for triggering literature review pipeline."""
    return {"status": "accepted", "review_id": "placeholder-id"}


@router.get("/{review_id}", summary="Get literature review status & report")
async def get_review_status(review_id: str):
    """Endpoint placeholder for fetching review task status and report."""
    return {"review_id": review_id, "status": "discovering"}


@router.post("/{review_id}/approve", summary="Human-in-the-loop paper approval")
async def approve_papers(review_id: str):
    """Endpoint placeholder for receiving human-selected papers."""
    return {"status": "approved", "review_id": review_id}
