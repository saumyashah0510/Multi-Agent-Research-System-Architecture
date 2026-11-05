"""Literature review task orchestration API routes.

Assignee Task (Issue BE-01 / BE-03):
- POST /: Submit new research prompt and launch pipeline with input guardrails.
- GET /{review_id}: Fetch current review status and structured report.
- POST /{review_id}/approve: Submit human user approved paper selections.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.guardrails import enforce_query_guardrail
from app.db.session import get_db
from app.models.review import LiteratureReview
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import generate_rag_chat_response
from app.services.vector_service import similarity_search

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
    """Endpoint for triggering literature review pipeline with input guardrails."""
    if request is not None and request.query:
        enforce_query_guardrail(request.query)

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
    """Endpoint for receiving human-selected approved papers and resuming LangGraph execution.

    TODO (Assignee - AI-05):
    1. Update review status from 'awaiting_user_input' in Neon DB
    2. Resume the paused LangGraph workflow using Command(resume=...) or graph.update_state()
    3. Pass user_decision ('continue' or 'find_more') and approved_paper_ids
    4. Return status: 'resumed'
    """
    return {"status": "approved", "review_id": review_id}


@router.post(
    "/{review_id}/chat",
    response_model=ChatResponse,
    summary="Chat with literature review using RAG",
)
async def chat_with_review(
    review_id: int,
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ChatResponse:
    """Perform pgvector similarity search and generate a grounded chat response."""

    review_result = await db.execute(
        select(LiteratureReview).where(LiteratureReview.id == review_id)
    )
    review = review_result.scalar_one_or_none()

    if review is None:
        raise HTTPException(
            status_code=404,
            detail="Literature review not found",
        )

    chunks = await similarity_search(
        db,
        query_text=request.question,
        review_id=review_id,
        top_k=4,
    )

    result = await generate_rag_chat_response(
        request.question,
        chunks,
        [message.model_dump() for message in request.history],
    )

    return ChatResponse(
        answer=result["answer"],
        citations=result["citations"],
    )
