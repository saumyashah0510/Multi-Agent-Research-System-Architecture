"""Literature review task orchestration API routes.

Assignee Task (Issue BE-01 / BE-03):
- POST /: Submit new research prompt and launch pipeline.
- GET /{review_id}: Fetch current review status and structured report.
- POST /{review_id}/approve: Submit human user approved paper selections.
"""

import uuid
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class ReviewCreateRequest(BaseModel):
    """Schema for initiating a new literature review task."""

    query: str
    citation_format: str = "APA"
    max_papers: int = 20


class ReviewApprovalRequest(BaseModel):
    """Schema for submitting human-selected approved paper IDs."""

    user_decision: str = "continue"
    approved_paper_ids: list[str] = Field(default_factory=list)


@router.post("/", summary="Submit new literature review task")
@router.post("", include_in_schema=False)
async def create_review_task(
    request: ReviewCreateRequest | None = None,
) -> dict[str, Any]:
    """Endpoint for triggering literature review pipeline."""
    review_id = f"review-{uuid.uuid4().hex[:8]}"
    return {"status": "accepted", "review_id": review_id}


@router.get("/{review_id}", summary="Get literature review status & report")
async def get_review_status(review_id: str) -> dict[str, Any]:
    """Endpoint for fetching review task status and report."""
    return {
        "review_id": review_id,
        "status": "user_approval_pending",
        "screened_papers": [],
    }


@router.post("/{review_id}/approve", summary="Human-in-the-loop paper approval")
async def approve_papers(
    review_id: str,
    request: ReviewApprovalRequest | None = None,
) -> dict[str, Any]:
    """Endpoint for receiving human-selected papers."""
    return {"status": "approved", "review_id": review_id}
