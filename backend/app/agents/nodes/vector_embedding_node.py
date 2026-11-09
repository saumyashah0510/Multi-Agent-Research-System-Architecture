"""Agent 06: Vector Chunking and pgvector Embedding Node.

Assignee Task (Issue AI-07):
- Read extracted_pdf_contents and review_id from AgentState
- Segment section text into overlapping passages (500 chars, 50 overlap)
- Generate 384D local embeddings (all-MiniLM-L6-v2)
- Store PaperChunk records in Neon PostgreSQL
- Return updated state dict with vector_embedding_completed
"""

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.state import AgentState
from app.db.session import AsyncSessionLocal
from app.models.paper import Paper
from app.services.vector_service import is_embedding_model_available, store_paper_chunks

logger = logging.getLogger(__name__)


def _normalize_identifier(val: Optional[str]) -> str:
    """Normalize identifiers (arXiv IDs, DOIs, PubMed IDs, canonical URLs) for robust lookup."""
    if not val:
        return ""
    s = str(val).strip().lower()

    # Strip arXiv URL prefixes and remove .pdf extension if present
    for arxiv_prefix in (
        "https://arxiv.org/abs/",
        "http://arxiv.org/abs/",
        "https://arxiv.org/pdf/",
        "http://arxiv.org/pdf/",
    ):
        if s.startswith(arxiv_prefix):
            s = s[len(arxiv_prefix) :].rstrip("/").strip()
            if s.endswith(".pdf"):
                s = s[:-4].strip()
            break

    # Strip DOI URL prefixes (preserve DOI suffixes including any periods or .pdf)
    for doi_prefix in (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
    ):
        if s.startswith(doi_prefix):
            s = s[len(doi_prefix) :].rstrip("/").strip()
            break

    for prefix in ("arxiv:", "doi:", "pmid:"):
        if s.startswith(prefix):
            s = s[len(prefix) :].strip()
    return s


def _strip_version(val: str) -> str:
    """Strip arXiv version suffix (e.g. '2301.12345v2' -> '2301.12345')."""
    return re.sub(r"v\d+$", "", val)


def _normalize_title(val: Optional[str]) -> str:
    """Normalize paper title for clean matching (lowercase, alphanumeric + spaces only)."""
    if not val:
        return ""
    cleaned = re.sub(r"[^\w\s]", "", str(val).lower())
    return " ".join(cleaned.split())


def _build_paper_index(
    papers: List[Paper],
) -> Tuple[
    Dict[str, Paper],
    Dict[str, Paper],
    Dict[str, Paper],
    Dict[str, Paper],
    Dict[int, Paper],
    Set[str],
]:
    """Index database papers by arxiv_id, doi, pubmed_id, normalized title, and id.

    Tracks duplicate normalized titles within the scoped review to prevent ambiguous
    misattribution.
    """
    arxiv_map: Dict[str, Paper] = {}
    doi_map: Dict[str, Paper] = {}
    pubmed_map: Dict[str, Paper] = {}
    title_map: Dict[str, Paper] = {}
    id_map: Dict[int, Paper] = {}
    ambiguous_titles: Set[str] = set()

    for p in papers:
        id_map[p.id] = p
        if p.arxiv_id:
            norm_arx = _normalize_identifier(p.arxiv_id)
            if norm_arx:
                arxiv_map[norm_arx] = p
                arxiv_map[_strip_version(norm_arx)] = p
        if p.doi:
            norm_doi = _normalize_identifier(p.doi)
            if norm_doi:
                doi_map[norm_doi] = p
        if p.pubmed_id:
            norm_pm = _normalize_identifier(p.pubmed_id)
            if norm_pm:
                pubmed_map[norm_pm] = p
        if p.title:
            norm_t = _normalize_title(p.title)
            if norm_t:
                if norm_t in ambiguous_titles:
                    # Title was already detected as duplicate
                    pass
                elif norm_t in title_map:
                    # Duplicate title detected within this review; mark ambiguous and remove from unique map
                    prior_paper = title_map[norm_t]
                    logger.warning(
                        "Ambiguous paper title detected in review: '%s' matches multiple papers "
                        "(id=%s and id=%s). Title-only resolution will be rejected.",
                        p.title,
                        prior_paper.id,
                        p.id,
                    )
                    del title_map[norm_t]
                    ambiguous_titles.add(norm_t)
                else:
                    title_map[norm_t] = p

    return arxiv_map, doi_map, pubmed_map, title_map, id_map, ambiguous_titles


def _resolve_paper(
    paper_key: Any,
    content: Any,
    approved_papers: List[Dict[str, Any]],
    arxiv_map: Dict[str, Paper],
    doi_map: Dict[str, Paper],
    pubmed_map: Dict[str, Paper],
    title_map: Dict[str, Paper],
    id_map: Dict[int, Paper],
    ambiguous_titles: Set[str],
    review_id: Optional[int] = None,
) -> Optional[Paper]:
    """Resolve an extracted paper key and its content dictionary to a database Paper record.

    Prioritizes strong, unique identifiers (arXiv ID, DOI, PubMed ID).
    Rejects ambiguous title-only matches rather than arbitrarily selecting a paper.
    Never assumes arbitrary numeric dictionary keys represent database IDs.
    """
    key_str = str(paper_key).strip() if paper_key is not None else ""
    norm_key = _normalize_identifier(key_str)

    # 1. Match paper_key against strongest unique identifiers: arxiv_id
    if norm_key in arxiv_map:
        return arxiv_map[norm_key]
    if _strip_version(norm_key) in arxiv_map:
        return arxiv_map[_strip_version(norm_key)]

    # 2. Match paper_key against doi
    if norm_key in doi_map:
        return doi_map[norm_key]

    # 3. Match paper_key against pubmed_id
    if norm_key in pubmed_map:
        return pubmed_map[norm_key]

    # 4. Match paper_key against title (with ambiguity detection)
    norm_title = _normalize_title(key_str)
    if norm_title in ambiguous_titles:
        logger.warning(
            "Paper key '%s' matches ambiguous title shared by multiple papers in review_id=%s. "
            "Title-only resolution rejected; seeking stronger metadata.",
            key_str,
            review_id,
        )
    elif norm_title and norm_title in title_map:
        return title_map[norm_title]

    # 5. Check content metadata if content is a dictionary
    if isinstance(content, dict):
        # 5a. Strong identifier: arxiv_id in content
        if content.get("arxiv_id"):
            norm_c_arx = _normalize_identifier(str(content["arxiv_id"]))
            if norm_c_arx in arxiv_map:
                return arxiv_map[norm_c_arx]
            if _strip_version(norm_c_arx) in arxiv_map:
                return arxiv_map[_strip_version(norm_c_arx)]

        # 5b. Strong identifier: doi in content
        if content.get("doi"):
            norm_c_doi = _normalize_identifier(str(content["doi"]))
            if norm_c_doi in doi_map:
                return doi_map[norm_c_doi]

        # 5c. Strong identifier: pubmed_id in content
        if content.get("pubmed_id"):
            norm_c_pm = _normalize_identifier(str(content["pubmed_id"]))
            if norm_c_pm in pubmed_map:
                return pubmed_map[norm_c_pm]

        # 5d. Explicit paper_id in content (must be valid integer belonging to scoped review)
        if content.get("paper_id") is not None:
            raw_id = content["paper_id"]
            try:
                parsed_id = int(raw_id)
                if parsed_id in id_map:
                    return id_map[parsed_id]
                logger.warning(
                    "Explicit paper_id=%s in content does not belong to review_id=%s. Rejected.",
                    raw_id,
                    review_id,
                )
            except (ValueError, TypeError):
                logger.warning("Invalid non-integer paper_id=%r in content. Ignored.", raw_id)

        # 5e. Title in content (must not be ambiguous)
        if content.get("title"):
            norm_c_t = _normalize_title(str(content["title"]))
            if norm_c_t in ambiguous_titles:
                logger.warning(
                    "Content title '%s' is ambiguous in review_id=%s. Rejected.",
                    content["title"],
                    review_id,
                )
            elif norm_c_t and norm_c_t in title_map:
                return title_map[norm_c_t]

    # 6. Cross-reference approved_papers list from state
    for ap in approved_papers:
        ap_title = str(ap.get("title") or "")
        ap_arxiv = str(ap.get("arxiv_id") or "")
        ap_doi = str(ap.get("doi") or "")

        # Check if approved_paper matches the current key
        matches_ap = False
        if norm_key:
            norm_ap_arx = _normalize_identifier(ap_arxiv)
            if (
                norm_key == norm_ap_arx
                or _strip_version(norm_key) == _strip_version(norm_ap_arx)
                or norm_key == _normalize_identifier(ap_doi)
            ):
                matches_ap = True
        if (
            not matches_ap
            and norm_title
            and norm_title not in ambiguous_titles
            and norm_title == _normalize_title(ap_title)
        ):
            matches_ap = True

        if matches_ap:
            if ap_arxiv:
                norm_a = _normalize_identifier(ap_arxiv)
                if norm_a in arxiv_map:
                    return arxiv_map[norm_a]
                if _strip_version(norm_a) in arxiv_map:
                    return arxiv_map[_strip_version(norm_a)]
            if ap_doi:
                norm_d = _normalize_identifier(ap_doi)
                if norm_d in doi_map:
                    return doi_map[norm_d]
            if ap_title:
                norm_at = _normalize_title(ap_title)
                if norm_at not in ambiguous_titles and norm_at in title_map:
                    return title_map[norm_at]
            if ap.get("id") is not None:
                try:
                    ap_id = int(ap["id"])
                    if ap_id in id_map:
                        return id_map[ap_id]
                except (ValueError, TypeError):
                    pass

    return None


def _extract_paper_sections_and_text(
    content: Any,
    paper: Optional[Paper] = None,
) -> Tuple[Dict[str, str], str]:
    """Extract section dictionary and full-text from content, falling back to Paper model if empty."""
    sections: Dict[str, str] = {}
    full_text: str = ""

    if isinstance(content, dict):
        if "sections" in content and isinstance(content["sections"], dict):
            sections = {str(k): str(v) for k, v in content["sections"].items() if v}
            full_text = str(content.get("full_text") or content.get("text") or "")
        else:
            for k, v in content.items():
                if k in ("full_text", "text") and isinstance(v, str):
                    full_text = v
                elif (
                    isinstance(v, str)
                    and v.strip()
                    and k not in ("arxiv_id", "title", "doi", "pubmed_id", "paper_id", "url")
                ):
                    sections[str(k)] = v
    elif isinstance(content, str):
        full_text = content

    # Fallback to Paper record attributes if content was empty
    if not sections and not full_text and paper is not None:
        if paper.sections and isinstance(paper.sections, dict):
            sections = {str(k): str(v) for k, v in paper.sections.items() if v}
        elif paper.abstract:
            sections = {"Abstract": paper.abstract}

    return sections, full_text


async def _process_and_store_embeddings(
    db: AsyncSession,
    review_id: Optional[int],
    extracted_pdf_contents: Dict[str, Any],
    approved_papers: List[Dict[str, Any]],
    commit_on_complete: bool = False,
) -> Dict[str, Any]:
    """Query scoped papers, resolve identities, chunk text, and persist PaperChunk records."""
    if review_id is None:
        raise ValueError("review_id is required to scope paper resolution and chunk replacement")
    stmt = select(Paper).where(Paper.review_id == review_id)
    # Order by Paper.id deterministically to prevent locking deadlocks across concurrent runs
    stmt = stmt.order_by(Paper.id)
    res = await db.execute(stmt)
    db_papers = list(res.scalars().all())

    arxiv_map, doi_map, pubmed_map, title_map, id_map, ambiguous_titles = _build_paper_index(
        db_papers
    )

    # Group extracted contents by resolved paper to guarantee a single replacement per paper
    # and preserve content across multiple sources (e.g. sections and full-text).
    grouped_papers: Dict[int, Dict[str, Any]] = {}

    for paper_key, content in extracted_pdf_contents.items():
        paper = _resolve_paper(
            paper_key=paper_key,
            content=content,
            approved_papers=approved_papers,
            arxiv_map=arxiv_map,
            doi_map=doi_map,
            pubmed_map=pubmed_map,
            title_map=title_map,
            id_map=id_map,
            ambiguous_titles=ambiguous_titles,
            review_id=review_id,
        )

        if not paper:
            logger.warning(
                "Could not resolve paper in database for extracted content key '%s' "
                "(review_id=%s). Skipping chunk persistence for this entry.",
                paper_key,
                review_id,
            )
            continue

        item_sections, item_full_text = _extract_paper_sections_and_text(content, paper=None)

        if paper.id not in grouped_papers:
            grouped_papers[paper.id] = {
                "paper": paper,
                "sections": {},
                "full_texts": [],
            }

        group = grouped_papers[paper.id]

        for sec_name, sec_text in item_sections.items():
            clean_sec = sec_text.strip()
            if not clean_sec:
                continue
            if sec_name not in group["sections"]:
                group["sections"][sec_name] = clean_sec
            elif clean_sec not in group["sections"][sec_name]:
                # Append distinct content under existing section name
                group["sections"][sec_name] = f"{group['sections'][sec_name]}\n\n{clean_sec}"

        if item_full_text and item_full_text.strip():
            clean_ft = item_full_text.strip()
            if clean_ft not in group["full_texts"]:
                group["full_texts"].append(clean_ft)

    total_chunks_stored = 0

    for group in grouped_papers.values():
        paper = group["paper"]
        sections = group["sections"]
        full_text = "\n\n".join(group["full_texts"]).strip()

        # Fallback to Paper record attributes if neither sections nor full_text were in extracted content
        if not sections and not full_text:
            if paper.sections and isinstance(paper.sections, dict):
                sections = {str(k): str(v) for k, v in paper.sections.items() if v}
            elif paper.abstract:
                sections = {"Abstract": paper.abstract}

        if not sections and not full_text:
            logger.warning(
                "No textual content or sections found for resolved paper id=%s ('%s'). Skipping.",
                paper.id,
                paper.title,
            )
            continue

        # When a paper has both sections and full_text from mixed entries, include distinct
        # full_text under a dedicated section so chunk_paper_sections chunks both.
        if sections and full_text:
            combined_sec = " ".join(sections.values())
            if full_text.strip() not in combined_sec:
                sec_name = "Main Body" if "Main Body" not in sections else "Full Text"
                sections[sec_name] = full_text

        stored = await store_paper_chunks(
            db=db,
            paper_id=paper.id,
            full_text=full_text,
            sections=sections,
            chunk_size=500,
            overlap=50,
            allow_fallback=False,
            replace_existing=True,
        )
        total_chunks_stored += len(stored)

    if commit_on_complete:
        await db.commit()
    else:
        await db.flush()

    logger.info(
        "Vector embedding completed: %d total chunks stored for review_id=%s.",
        total_chunks_stored,
        review_id,
    )

    return {
        "current_step": "vector_embedding_completed",
        "chunks_stored_count": total_chunks_stored,
    }


async def vector_embedding_node(
    state: AgentState,
    db: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """Segment paper sections, generate 384D embeddings, and persist to pgvector.

    1. Read extracted_pdf_contents and review_id from state.
    2. Validate extracted content; if empty, return early with 0 chunks stored.
    3. Ensure sentence-transformers embedding model is available (all-MiniLM-L6-v2, 384D).
    4. Query database for papers scoped to review_id.
    5. Resolve each extracted paper key to its actual Paper.id record.
    6. Chunk sections into 500-char sliding windows with 50-char overlap.
    7. Generate 384D semantic embeddings and store PaperChunk records linked to Paper.id.
    8. Return {"current_step": "vector_embedding_completed", "chunks_stored_count": total_chunks}.
    """
    extracted_pdf_contents: Dict[str, Any] = state.get("extracted_pdf_contents") or {}
    review_id: Optional[int] = state.get("review_id")
    approved_papers: List[Dict[str, Any]] = state.get("approved_papers") or []

    # Fast-return if no extracted contents provided
    if not extracted_pdf_contents:
        logger.info("No extracted_pdf_contents found in state. Skipping vector chunking.")
        return {
            "current_step": "vector_embedding_completed",
            "chunks_stored_count": 0,
        }

    # Strict check: verify SentenceTransformers model is available
    if not is_embedding_model_available():
        error_msg = (
            "SentenceTransformer model ('all-MiniLM-L6-v2') is unavailable. "
            "Cannot generate 384D semantic vector embeddings."
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    # Use provided db session or manage a new AsyncSession
    if db is not None:
        return await _process_and_store_embeddings(
            db=db,
            review_id=review_id,
            extracted_pdf_contents=extracted_pdf_contents,
            approved_papers=approved_papers,
            commit_on_complete=False,
        )

    async with AsyncSessionLocal() as session:
        return await _process_and_store_embeddings(
            db=session,
            review_id=review_id,
            extracted_pdf_contents=extracted_pdf_contents,
            approved_papers=approved_papers,
            commit_on_complete=True,
        )
