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
    """Endpoint for receiving human-selected papers and resuming LangGraph execution.

    TODO (Assignee - AI-05):
    1. Update review status from 'awaiting_user_input' in Neon DB
    2. Resume the paused LangGraph workflow using Command(resume=...) or graph.update_state()
    3. Pass user_decision ('continue' or 'find_more') and approved_paper_ids
    4. Return status: 'resumed'
    """
    return {"status": "approved", "review_id": review_id}


# TODO (Assignee - BE-10): Implement RAG Chat endpoint with conversation history:
# @router.post("/{review_id}/chat", response_model=ChatResponse, summary="Chat with literature review using RAG")
# async def chat_with_review(review_id: int, request: ChatRequest, db: AsyncSession = Depends(get_db)):
#     """Perform pgvector similarity search on review chunks, pass question + history to chat_service."""
#     # 1. Verify literature review exists in DB (or raise HTTPException 404)
#     # 2. Retrieve top-4 relevant chunks: chunks = await similarity_search(db, request.question, review_id, top_k=4)
#     # 3. Call chat_service: result = await generate_rag_chat_response(request.question, chunks, [h.model_dump() for h in request.history])
#     # 4. Return ChatResponse(answer=result["answer"], citations=result["citations"])
#     pass
