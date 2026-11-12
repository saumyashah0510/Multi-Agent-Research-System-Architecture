"""Literature review task orchestration API routes.

Assignee Task (Issue BE-01 / BE-03):
- POST /: Submit new research prompt and launch pipeline with input guardrails.
- GET /{review_id}: Fetch current review status and structured report.
- POST /{review_id}/approve: Submit human user approved paper selections.
- GET /: List previous literature review sessions for the History Drawer.
"""

import asyncio
import inspect
import logging
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import RedirectResponse
from langgraph.types import Command
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import build_literature_review_graph
from app.core.guardrails import enforce_query_guardrail
from app.db.session import AsyncSessionLocal, get_db
from app.models.paper import Paper
from app.models.review import LiteratureReview, ReviewStatus
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import generate_rag_chat_response
from app.services.export_service import (
    check_report_pdf_exists_in_s3,
    compile_literature_review_pdf,
    generate_presigned_download_url,
    upload_report_pdf_to_s3,
)
from app.services.redis_service import publish_review_event
from app.services.vector_service import similarity_search

logger = logging.getLogger(__name__)

router = APIRouter()

# The graph that was paused must be the same one that gets resumed,
# because its in-memory checkpointer holds the saved state.
graph = build_literature_review_graph()


class ReviewCreateRequest(BaseModel):
    """Schema for initiating a new literature review task."""

    query: str
    citation_format: str = "APA"
    max_papers: int = 20


class ReviewApprovalRequest(BaseModel):
    """Schema for submitting human-selected approved paper IDs."""

    user_decision: str = "continue"
    approved_paper_ids: list[str] = Field(default_factory=list)


async def _run_initial_graph(
    review_id: int,
    query: str,
    citation_format: str = "APA",
    max_papers: int = 10,
) -> None:
    """Execute stages 1-3 of the LangGraph pipeline until human interrupt."""
    initial_state: dict[str, Any] = {
        "user_query": query,
        "review_id": review_id,
        "max_papers": max_papers,
        "search_queries": [],
        "discovered_papers": [],
        "screened_papers": [],
        "approved_papers": [],
    }
    config = {"configurable": {"thread_id": str(review_id)}}

    try:
        await publish_review_event(
            review_id,
            {
                "event": "stage_update",
                "stage": "QUERY_EXPANSION",
                "status": "running",
                "message": "Analyzing research query and classifying domains...",
                "review_id": str(review_id),
            },
        )
    except Exception as exc:
        logger.debug("Could not publish initial event to Redis: %s", exc)

    try:
        async for update in graph.astream(initial_state, config=config, stream_mode="updates"):
            if not isinstance(update, dict):
                continue

            if "query_expansion" in update:
                node_out = update["query_expansion"]
                sub_queries = node_out.get("search_queries", [])
                try:
                    async with AsyncSessionLocal() as session:
                        rev = await session.get(LiteratureReview, review_id)
                        if rev:
                            rev.status = ReviewStatus.PAPER_DISCOVERY.value
                            await session.commit()
                except Exception as db_exc:
                    logger.debug("DB status update error: %s", db_exc)

                await publish_review_event(
                    review_id,
                    {
                        "event": "stage_completed",
                        "stage": "QUERY_EXPANSION",
                        "status": "completed",
                        "message": f"Expanded into {len(sub_queries)} academic queries",
                        "data": {"sub_queries": sub_queries, "queries": sub_queries},
                        "review_id": str(review_id),
                    },
                )
                await publish_review_event(
                    review_id,
                    {
                        "event": "stage_update",
                        "stage": "PAPER_DISCOVERY",
                        "status": "running",
                        "message": "Querying arXiv, PubMed, and academic repositories...",
                        "review_id": str(review_id),
                    },
                )

            elif "paper_discovery" in update:
                node_out = update["paper_discovery"]
                discovered = node_out.get("discovered_papers", [])
                try:
                    async with AsyncSessionLocal() as session:
                        rev = await session.get(LiteratureReview, review_id)
                        if rev:
                            rev.status = ReviewStatus.SCREENING.value
                            await session.commit()
                except Exception as db_exc:
                    logger.debug("DB status update error: %s", db_exc)

                await publish_review_event(
                    review_id,
                    {
                        "event": "stage_completed",
                        "stage": "PAPER_DISCOVERY",
                        "status": "completed",
                        "message": f"Discovered {len(discovered)} candidate papers",
                        "data": {"total_count": len(discovered), "count": len(discovered)},
                        "review_id": str(review_id),
                    },
                )
                await publish_review_event(
                    review_id,
                    {
                        "event": "stage_update",
                        "stage": "SCREENING",
                        "status": "running",
                        "message": "Screening candidate papers against relevance criteria...",
                        "review_id": str(review_id),
                    },
                )

            elif "screening" in update:
                node_out = update["screening"]
                screened = node_out.get("screened_papers", [])

                try:
                    async with AsyncSessionLocal() as session:
                        rev = await session.get(LiteratureReview, review_id)
                        if rev:
                            rev.status = ReviewStatus.AWAITING_USER_INPUT.value
                        for p in screened:
                            paper_obj = Paper(
                                title=p.get("title") or "Untitled Paper",
                                authors=p.get("authors"),
                                abstract=p.get("abstract"),
                                published_year=p.get("published_year") or p.get("year"),
                                arxiv_id=p.get("arxiv_id"),
                                doi=p.get("doi"),
                                pubmed_id=p.get("pubmed_id"),
                                pdf_url=p.get("pdf_url"),
                                source=p.get("source") or "arxiv",
                                relevance_score=float(p.get("relevance_score") or 0.0),
                                is_approved=False,
                                review_id=review_id,
                            )
                            session.add(paper_obj)
                        await session.commit()
                except Exception as db_exc:
                    logger.debug("DB paper persistence error: %s", db_exc)

                await publish_review_event(
                    review_id,
                    {
                        "event": "stage_completed",
                        "stage": "SCREENING",
                        "status": "completed",
                        "message": f"Screened {len(screened)} relevant papers",
                        "data": {"screened_papers": screened, "total_screened": len(screened)},
                        "review_id": str(review_id),
                    },
                )
                await publish_review_event(
                    review_id,
                    {
                        "event": "awaiting_user_input",
                        "stage": "AWAITING_USER_INPUT",
                        "status": "paused",
                        "message": "Awaiting human-in-the-loop candidate paper selection",
                        "data": {"screened_papers": screened, "total_screened": len(screened)},
                        "review_id": str(review_id),
                    },
                )

    except Exception as exc:
        logger.error(
            "Error executing initial graph for review %s: %s", review_id, exc, exc_info=True
        )
        try:
            async with AsyncSessionLocal() as session:
                rev = await session.get(LiteratureReview, review_id)
                if rev:
                    rev.status = ReviewStatus.FAILED.value
                    await session.commit()
        except Exception:
            pass
        try:
            await publish_review_event(
                review_id,
                {
                    "event": "stage_failed",
                    "stage": "FAILED",
                    "status": "failed",
                    "message": f"Initial pipeline execution error: {str(exc)}",
                    "review_id": str(review_id),
                },
            )
        except Exception:
            pass


async def _resume_graph(review_id: str, resume_value: dict[str, Any]) -> None:
    """Resume the paused LangGraph thread belonging to this review."""
    config = {"configurable": {"thread_id": str(review_id)}}
    numeric_id = int(review_id) if str(review_id).isdigit() else None
    try:
        snapshot = await graph.aget_state(config)
        if not snapshot.next:
            logger.warning("No paused graph found for review %s; nothing to resume.", review_id)
            return

        decision = resume_value.get("user_decision", "continue")
        if decision == "find_more":
            if numeric_id is not None:
                await publish_review_event(
                    numeric_id,
                    {
                        "event": "stage_update",
                        "stage": "QUERY_EXPANSION",
                        "status": "running",
                        "message": "Expanding search queries for additional papers...",
                        "review_id": str(review_id),
                    },
                )
        else:
            if numeric_id is not None:
                await publish_review_event(
                    numeric_id,
                    {
                        "event": "stage_update",
                        "stage": "PDF_EXTRACTION",
                        "status": "running",
                        "message": "Extracting scientific section text from approved PDFs...",
                        "review_id": str(review_id),
                    },
                )

        async for update in graph.astream(
            Command(resume=resume_value), config=config, stream_mode="updates"
        ):
            if not isinstance(update, dict):
                continue

            if "pdf_extraction" in update:
                node_out = update["pdf_extraction"]
                pdf_contents = node_out.get("extracted_pdf_contents", {})
                if numeric_id is not None:
                    try:
                        async with AsyncSessionLocal() as session:
                            rev = await session.get(LiteratureReview, numeric_id)
                            if rev:
                                rev.status = ReviewStatus.VECTOR_EMBEDDING.value
                                await session.commit()
                    except Exception as db_exc:
                        logger.debug("DB status error: %s", db_exc)

                    await publish_review_event(
                        numeric_id,
                        {
                            "event": "stage_completed",
                            "stage": "PDF_EXTRACTION",
                            "status": "completed",
                            "message": f"Extracted sections from {len(pdf_contents)} papers",
                            "data": {"pdf_count": len(pdf_contents), "count": len(pdf_contents)},
                            "review_id": str(review_id),
                        },
                    )
                    await publish_review_event(
                        numeric_id,
                        {
                            "event": "stage_update",
                            "stage": "VECTOR_EMBEDDING",
                            "status": "running",
                            "message": "Generating 384D semantic embeddings and indexing in pgvector...",
                            "review_id": str(review_id),
                        },
                    )

            elif "vector_embedding" in update:
                node_out = update["vector_embedding"]
                chunks_count = node_out.get("chunks_stored_count", 0)
                if numeric_id is not None:
                    try:
                        async with AsyncSessionLocal() as session:
                            rev = await session.get(LiteratureReview, numeric_id)
                            if rev:
                                rev.status = ReviewStatus.GAP_ANALYSIS.value
                                await session.commit()
                    except Exception as db_exc:
                        logger.debug("DB status error: %s", db_exc)

                    await publish_review_event(
                        numeric_id,
                        {
                            "event": "stage_completed",
                            "stage": "VECTOR_EMBEDDING",
                            "status": "completed",
                            "message": f"Indexed {chunks_count} passages in pgvector",
                            "data": {"chunks": chunks_count, "chunk_count": chunks_count},
                            "review_id": str(review_id),
                        },
                    )
                    await publish_review_event(
                        numeric_id,
                        {
                            "event": "stage_update",
                            "stage": "GAP_ANALYSIS",
                            "status": "running",
                            "message": "Performing comparative methodology synthesis and literature gap analysis...",
                            "review_id": str(review_id),
                        },
                    )

            elif "gap_analysis" in update:
                node_out = update["gap_analysis"]
                gaps = node_out.get("research_gaps", [])
                if numeric_id is not None:
                    try:
                        async with AsyncSessionLocal() as session:
                            rev = await session.get(LiteratureReview, numeric_id)
                            if rev:
                                rev.status = ReviewStatus.CITATION_VERIFICATION.value
                                await session.commit()
                    except Exception as db_exc:
                        logger.debug("DB status error: %s", db_exc)

                    await publish_review_event(
                        numeric_id,
                        {
                            "event": "stage_completed",
                            "stage": "GAP_ANALYSIS",
                            "status": "completed",
                            "message": f"Mapped methodology matrix and {len(gaps)} research gaps",
                            "data": {"gaps": gaps, "gaps_count": len(gaps)},
                            "review_id": str(review_id),
                        },
                    )
                    await publish_review_event(
                        numeric_id,
                        {
                            "event": "stage_update",
                            "stage": "CITATION_VERIFICATION",
                            "status": "running",
                            "message": "Verifying citation claims against source passages...",
                            "review_id": str(review_id),
                        },
                    )

            elif "citation_verification" in update:
                node_out = update["citation_verification"]
                verified_refs = node_out.get("verified_references", [])
                if numeric_id is not None:
                    try:
                        async with AsyncSessionLocal() as session:
                            rev = await session.get(LiteratureReview, numeric_id)
                            if rev:
                                rev.status = ReviewStatus.REPORT_SYNTHESIS.value
                                await session.commit()
                    except Exception as db_exc:
                        logger.debug("DB status error: %s", db_exc)

                    await publish_review_event(
                        numeric_id,
                        {
                            "event": "stage_completed",
                            "stage": "CITATION_VERIFICATION",
                            "status": "completed",
                            "message": f"Verified {len(verified_refs)} citations against source chunks",
                            "data": {
                                "verified_claims": len(verified_refs),
                                "verified_count": len(verified_refs),
                            },
                            "review_id": str(review_id),
                        },
                    )
                    await publish_review_event(
                        numeric_id,
                        {
                            "event": "stage_update",
                            "stage": "REPORT_SYNTHESIS",
                            "status": "running",
                            "message": "Synthesizing comprehensive academic literature review report...",
                            "review_id": str(review_id),
                        },
                    )

            elif "report_synthesis" in update:
                node_out = update["report_synthesis"]
                synthesized = node_out.get("synthesized_review", {})
                if numeric_id is not None:
                    try:
                        async with AsyncSessionLocal() as session:
                            rev = await session.get(LiteratureReview, numeric_id)
                            if rev:
                                rev.synthesized_review = synthesized
                                rev.status = ReviewStatus.COMPLETED.value
                                await session.commit()
                    except Exception as db_exc:
                        logger.debug("DB completion error: %s", db_exc)

                    await publish_review_event(
                        numeric_id,
                        {
                            "event": "stage_completed",
                            "stage": "REPORT_SYNTHESIS",
                            "status": "completed",
                            "message": "Literature review report synthesized successfully",
                            "review_id": str(review_id),
                        },
                    )
                    await publish_review_event(
                        numeric_id,
                        {
                            "event": "completed",
                            "stage": "COMPLETED",
                            "status": "completed",
                            "message": "Literature review pipeline completed",
                            "review_id": str(review_id),
                        },
                    )

    except Exception as exc:
        logger.error("Failed to resume graph for review %s: %s", review_id, exc, exc_info=True)
        if numeric_id is not None:
            try:
                async with AsyncSessionLocal() as session:
                    rev = await session.get(LiteratureReview, numeric_id)
                    if rev:
                        rev.status = ReviewStatus.FAILED.value
                        await session.commit()
            except Exception:
                pass
            try:
                await publish_review_event(
                    numeric_id,
                    {
                        "event": "stage_failed",
                        "stage": "FAILED",
                        "status": "failed",
                        "message": f"Pipeline execution failed: {str(exc)}",
                        "review_id": str(review_id),
                    },
                )
            except Exception:
                pass


@router.post("/", summary="Submit new literature review task")
@router.post("", include_in_schema=False)
async def create_review_task(
    request: ReviewCreateRequest | None = None,
    background_tasks: BackgroundTasks = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> dict[str, Any]:
    """Endpoint for triggering literature review pipeline with input guardrails."""
    if request is not None and request.query:
        enforce_query_guardrail(request.query)

    review_id_val: int | None = None
    if db is not None and request is not None and request.query:
        try:
            review = LiteratureReview(
                user_query=request.query,
                status=ReviewStatus.QUERY_EXPANSION.value,
            )
            add_res = db.add(review)
            if inspect.isawaitable(add_res):
                await add_res
            commit_res = db.commit()
            if inspect.isawaitable(commit_res):
                await commit_res
            refresh_res = getattr(db, "refresh", None)
            if refresh_res is not None:
                refresh_coro = refresh_res(review)
                if inspect.isawaitable(refresh_coro):
                    await refresh_coro
            review_id_val = getattr(review, "id", None)
        except Exception as exc:
            logger.warning("Could not persist initial LiteratureReview record: %s", exc)

    assigned_id = review_id_val if review_id_val is not None else f"review-{uuid.uuid4().hex[:8]}"

    if request is not None and request.query:
        bg_id = review_id_val if review_id_val is not None else 1
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                _run_initial_graph(
                    bg_id,
                    request.query,
                    request.citation_format,
                    request.max_papers,
                )
            )
        except RuntimeError:
            if background_tasks is not None:
                background_tasks.add_task(
                    _run_initial_graph,
                    bg_id,
                    request.query,
                    request.citation_format,
                    request.max_papers,
                )

    return {"status": "accepted", "review_id": assigned_id}


@router.get("/", summary="List past literature review sessions")
@router.get("", include_in_schema=False)
async def list_reviews(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[dict[str, Any]]:
    """Fetch past review sessions for the History Drawer."""
    try:
        stmt = select(LiteratureReview).order_by(LiteratureReview.created_at.desc()).limit(limit)
        res = await db.execute(stmt)
        reviews = res.scalars().all()
        return [
            {
                "id": str(r.id),
                "query": r.user_query,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else "",
                "synthesized_review": r.synthesized_review,
            }
            for r in reviews
        ]
    except Exception as exc:
        logger.warning("Could not query past reviews: %s", exc)
        return []


@router.get("/{review_id}/export", summary="Download compiled literature review PDF")
async def export_review_pdf(
    review_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> Any:
    """Generate or retrieve a compiled PDF export and redirect to a presigned S3 download URL.

    Returns 404 when the review does not exist, 400 when it has not yet completed,
    and 302 redirect to the presigned S3 URL on success.
    """
    if not str(review_id).isdigit():
        raise HTTPException(status_code=404, detail="Review not found.")
    num_id = int(review_id)
    review = await db.get(LiteratureReview, num_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found.")

    if review.status != "completed" or not review.synthesized_review:
        raise HTTPException(status_code=400, detail="Review is not yet completed.")

    s3_key = f"exports/literature_review_{num_id}.pdf"
    exists = await check_report_pdf_exists_in_s3(s3_key)
    if not exists:
        pdf_bytes = compile_literature_review_pdf(
            synthesized_review=review.synthesized_review,
            review_id=num_id,
            user_query=review.user_query,
            created_at=review.created_at,
        )
        await upload_report_pdf_to_s3(pdf_bytes, num_id)

    presigned_url = generate_presigned_download_url(s3_key)
    return RedirectResponse(url=presigned_url, status_code=302)


@router.get("/{review_id}", summary="Get literature review status & report")
async def get_review_status(
    review_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    """Endpoint for fetching review task status and report."""
    if str(review_id).isdigit():
        num_id = int(review_id)
        try:
            review = await db.get(LiteratureReview, num_id)
            if review is not None:
                paper_stmt = select(Paper).where(Paper.review_id == num_id)
                res = await db.execute(paper_stmt)
                papers = res.scalars().all()
                return {
                    "review_id": str(review.id),
                    "id": str(review.id),
                    "query": review.user_query,
                    "user_query": review.user_query,
                    "status": review.status,
                    "synthesized_review": review.synthesized_review,
                    "screened_papers": [
                        {
                            "id": p.id,
                            "title": p.title,
                            "authors": p.authors,
                            "abstract": p.abstract,
                            "published_year": p.published_year,
                            "arxiv_id": p.arxiv_id,
                            "doi": p.doi,
                            "pubmed_id": p.pubmed_id,
                            "pdf_url": p.pdf_url,
                            "relevance_score": p.relevance_score,
                            "is_approved": p.is_approved,
                        }
                        for p in papers
                    ],
                    "created_at": review.created_at.isoformat() if review.created_at else None,
                }
        except Exception as exc:
            logger.warning("Error fetching review %s from DB: %s", review_id, exc)

    return {
        "review_id": review_id,
        "id": review_id,
        "query": "Academic Research Topic",
        "user_query": "Academic Research Topic",
        "status": "user_approval_pending",
        "screened_papers": [],
    }


@router.post("/{review_id}/approve", summary="Human-in-the-loop paper approval")
async def approve_papers(
    review_id: str,
    request: ReviewApprovalRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Endpoint for receiving human-selected papers and resuming LangGraph execution."""
    if request.user_decision not in ("continue", "find_more"):
        raise HTTPException(status_code=400, detail="Invalid user_decision.")

    # Rule: never proceed to PDF extraction without at least 1 approved paper.
    if request.user_decision == "continue" and not request.approved_paper_ids:
        raise HTTPException(status_code=400, detail="Approve at least 1 paper.")

    # Move status on from 'awaiting_user_input' in the database and mark approved papers.
    if str(review_id).isdigit():
        num_id = int(review_id)
        try:
            review = await db.get(LiteratureReview, num_id)
            if review is not None:
                review.status = (
                    ReviewStatus.PDF_EXTRACTION.value
                    if request.user_decision == "continue"
                    else ReviewStatus.QUERY_EXPANSION.value
                )
                if request.user_decision == "continue":
                    paper_stmt = select(Paper).where(Paper.review_id == num_id)
                    res = await db.execute(paper_stmt)
                    db_papers = res.scalars().all()
                    for p in db_papers:
                        if (
                            str(p.id) in request.approved_paper_ids
                            or (p.arxiv_id and p.arxiv_id in request.approved_paper_ids)
                            or p.title in request.approved_paper_ids
                        ):
                            p.is_approved = True
                await db.commit()
        except Exception as exc:
            logger.warning("Could not update status for review %s: %s", review_id, exc)

    background_tasks.add_task(
        _resume_graph,
        review_id,
        {
            "user_decision": request.user_decision,
            "approved_paper_ids": request.approved_paper_ids,
        },
    )
    return {"status": "resumed", "review_id": review_id}


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
