"""Agent 05: Full-Text PDF Extractor Node.

Assignee Task (Issue AI-06):
- Read approved_papers from AgentState
- Download PDFs and cache to AWS S3 (with safe local fallback)
- Extract scientific section headings (Methodology, Results, Limitations) using PyMuPDF
- Return updated state dict with extracted_pdf_contents
"""

import asyncio
import logging
from typing import Any, Dict, Optional, Tuple

from app.agents.state import AgentState
from app.services.pdf_service import download_and_extract_pdf

logger = logging.getLogger(__name__)

STANDARD_SECTIONS = (
    "abstract",
    "introduction",
    "methods",
    "results",
    "discussion",
    "limitations",
    "conclusion",
)


def _get_paper_key(paper: Dict[str, Any]) -> Optional[str]:
    """Return the dictionary key for a paper: arxiv_id, falling back to title."""
    return paper.get("arxiv_id") or paper.get("title")


def _get_pdf_url(paper: Dict[str, Any]) -> str:
    """Return the PDF URL for a paper, building an arXiv URL from arxiv_id if needed."""
    pdf_url = paper.get("pdf_url")
    if pdf_url:
        return pdf_url

    arxiv_id = paper.get("arxiv_id")
    if arxiv_id:
        return f"https://arxiv.org/pdf/{arxiv_id}.pdf"

    return ""


async def _extract_single_paper(
    paper: Dict[str, Any],
) -> Tuple[Optional[str], Dict[str, str]]:
    """Download one paper, cache it to S3 and return (paper_key, sections).

    Never raises: any failure falls back to the paper's abstract so the
    pipeline does not halt on paywalls or network drops.
    """
    paper_key = _get_paper_key(paper)
    fallback_sections = {"abstract": paper.get("abstract") or ""}

    if not paper_key:
        return None, fallback_sections

    pdf_url = _get_pdf_url(paper)

    try:
        data = await download_and_extract_pdf(pdf_url, cache_key=paper_key)
    except Exception as exc:  # noqa: BLE001 - never let one paper halt the pipeline
        logger.warning("PDF extraction failed for '%s': %s", paper_key, exc)
        return paper_key, fallback_sections

    all_sections = (data or {}).get("sections") or {}
    sections = {name: all_sections[name] for name in STANDARD_SECTIONS if all_sections.get(name)}

    if not sections:
        return paper_key, fallback_sections

    return paper_key, sections


MAX_CONCURRENT_PAPER_EXTRACTIONS = 5


async def pdf_extractor_node(state: AgentState) -> Dict[str, Any]:
    """Download approved papers and extract section text into dictionary."""

    approved_papers = state.get("approved_papers") or []
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_PAPER_EXTRACTIONS)

    async def _bounded_extract(
        paper: Dict[str, Any],
    ) -> Tuple[Optional[str], Dict[str, str]]:
        async with semaphore:
            return await _extract_single_paper(paper)

    results = await asyncio.gather(*(_bounded_extract(paper) for paper in approved_papers))

    extracted_sections: Dict[str, Any] = {}
    for paper_key, sections in results:
        if not paper_key:
            continue
        # Preserve full-text sections if a duplicate paper key fell back to abstract
        if (
            paper_key in extracted_sections
            and len(sections) <= 1
            and len(extracted_sections[paper_key]) > 1
        ):
            continue
        extracted_sections[paper_key] = sections

    return {
        "extracted_pdf_contents": extracted_sections,
        "current_step": "pdf_extraction_completed",
    }
