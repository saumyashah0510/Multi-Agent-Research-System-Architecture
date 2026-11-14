"""Agent 02: Multi-Source Paper Discovery Node."""

import asyncio
import logging
import re
from typing import Any

from app.agents.state import AgentState
from app.services.search_service import search_academic_papers

logger = logging.getLogger(__name__)


def _normalize_identifier(value: Any) -> str:
    """Normalize DOI, PubMed, or arXiv identifiers."""
    if not value:
        return ""

    identifier = str(value).strip().lower()
    identifier = re.sub(r"^https?://(dx\.)?doi\.org/", "", identifier)
    identifier = re.sub(r"^doi:\s*", "", identifier)
    identifier = re.sub(r"^pmid:\s*", "", identifier)
    identifier = re.sub(r"^pubmed:\s*", "", identifier)

    return identifier.rstrip("/")


def _normalize_title(title: Any) -> str:
    """Normalize paper titles for duplicate detection."""
    if not title:
        return ""

    title = str(title).casefold()
    title = re.sub(r"[^\w\s]", " ", title)

    return " ".join(title.split())


def _normalize_paper(paper: Any) -> dict[str, Any] | None:
    """Normalize metadata returned by academic search services."""
    if hasattr(paper, "model_dump"):
        paper = paper.model_dump()

    if not isinstance(paper, dict):
        return None

    title = str(paper.get("title") or "").strip()
    abstract = str(paper.get("abstract") or "").strip()

    # Ignore papers without a title or abstract.
    if not title or not abstract:
        return None

    authors = paper.get("authors") or []

    if isinstance(authors, str):
        authors = [authors]

    publication_date = paper.get("publication_date") or ""
    year = paper.get("year") or paper.get("published_year")

    if year is None:
        match = re.search(r"\b\d{4}\b", str(publication_date))
        year = int(match.group()) if match else None

    pubmed_id = paper.get("pubmed_id")
    if pubmed_id is not None:
        pubmed_id = str(pubmed_id).strip()
        if not pubmed_id:
            pubmed_id = None

    return {
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "year": year,
        "arxiv_id": paper.get("arxiv_id"),
        "doi": paper.get("doi"),
        "pdf_url": paper.get("pdf_url"),
        "source": paper.get("source", "unknown"),
        "pubmed_id": pubmed_id,
    }


def _get_deduplication_keys(paper: dict[str, Any]) -> set[str]:
    """Generate unique identifiers for duplicate detection."""
    keys = set()

    arxiv_id = _normalize_identifier(paper.get("arxiv_id"))
    doi = _normalize_identifier(paper.get("doi"))
    pubmed_id = _normalize_identifier(paper.get("pubmed_id"))
    title = _normalize_title(paper.get("title"))

    if arxiv_id:
        keys.add(f"arxiv:{arxiv_id}")

    if doi:
        keys.add(f"doi:{doi}")

    if pubmed_id:
        keys.add(f"pubmed:{pubmed_id}")

    if title:
        keys.add(f"title:{title}")

    return keys


async def discovery_node(state: AgentState) -> dict[str, Any]:
    """Discover and deduplicate academic papers from multiple queries."""
    search_queries = state.get("search_queries") or [state.get("user_query", "")]

    queries = list(
        dict.fromkeys(
            query.strip() for query in search_queries if isinstance(query, str) and query.strip()
        )
    )

    if not queries:
        logger.warning("No valid search queries provided.")

        return {
            "discovered_papers": [],
            "current_step": "paper_discovery_completed",
        }

    # Execute all expanded queries concurrently.
    tasks = [search_academic_papers(query, max_results=10) for query in queries]

    results = await asyncio.gather(
        *tasks,
        return_exceptions=True,
    )

    all_papers = []

    for query, result in zip(queries, results, strict=True):
        if isinstance(result, BaseException):
            logger.warning(
                "Search failed for query '%s': %s",
                query,
                result,
            )
            continue

        if isinstance(result, list):
            all_papers.extend(result)

    # Normalize and remove duplicate papers.
    discovered_papers = []
    seen_keys = set()

    for raw_paper in all_papers:
        paper = _normalize_paper(raw_paper)

        if paper is None:
            continue

        paper_keys = _get_deduplication_keys(paper)

        if not paper_keys or paper_keys & seen_keys:
            continue

        seen_keys.update(paper_keys)
        discovered_papers.append(paper)

    # Cap discovered papers to prevent excessive downstream token consumption
    max_discovered_cap = 70
    if len(discovered_papers) > max_discovered_cap:
        logger.info(
            "Capping discovered papers from %d to %d to manage token budgets.",
            len(discovered_papers),
            max_discovered_cap,
        )
        discovered_papers = discovered_papers[:max_discovered_cap]

    logger.info(
        "Discovery completed: %d unique papers from %d queries.",
        len(discovered_papers),
        len(queries),
    )

    return {
        "discovered_papers": discovered_papers,
        "current_step": "paper_discovery_completed",
    }
