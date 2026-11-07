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
from app.services.pdf_service import (
    _is_safe_pdf_url,
    download_and_extract_pdf,
    resolve_biorxiv_pdf_url,
    resolve_pubmed_pdf_url,
    resolve_unpaywall_pdf_url,
)

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
    """Return the deterministic cache key for a paper."""
    if paper.get("arxiv_id"):
        return str(paper["arxiv_id"]).strip()
    if paper.get("pubmed_id"):
        return f"pmid_{str(paper['pubmed_id']).strip()}"
    if paper.get("doi"):
        return f"doi_{str(paper['doi']).strip()}"
    return paper.get("title")


async def _get_pdf_url(paper: Dict[str, Any]) -> str:
    """Return the PDF URL for a paper, resolving multi-source URLs if needed."""
    pdf_url = paper.get("pdf_url")
    if pdf_url and isinstance(pdf_url, str) and pdf_url.strip():
        cand = pdf_url.strip()
        if _is_safe_pdf_url(cand):
            return cand

    arxiv_id = paper.get("arxiv_id")
    if arxiv_id:
        return f"https://arxiv.org/pdf/{arxiv_id}.pdf"

    doi = paper.get("doi")
    source = (paper.get("source") or "").lower()

    if doi and (source in ("biorxiv", "medrxiv") or str(doi).strip().startswith("10.1101/")):
        resolved_biorxiv = await resolve_biorxiv_pdf_url(str(doi))
        if resolved_biorxiv:
            return resolved_biorxiv

    pubmed_id = paper.get("pubmed_id")
    if pubmed_id:
        resolved = await resolve_pubmed_pdf_url(str(pubmed_id), doi)
        if resolved:
            return resolved

    if doi:
        resolved_doi = await resolve_unpaywall_pdf_url(str(doi))
        if resolved_doi:
            return resolved_doi

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

    pdf_url = await _get_pdf_url(paper)

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
