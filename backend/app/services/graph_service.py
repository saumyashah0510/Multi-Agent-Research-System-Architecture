"""Citation knowledge graph topology service."""

import re
from itertools import combinations
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paper import Paper
from app.models.review import LiteratureReview
from app.schemas.graph import CitationGraphResponse, GraphLink, GraphNode

# Match discovery_node's 70-paper cap. This limits pair scans to 2,415 and, with at most two
# relationship types per pair, bounds generated links at 4,830 per request.
MAX_APPROVED_GRAPH_NODES = 70


class GraphSizeLimitExceeded(ValueError):
    """Raised when an approved-paper set exceeds the bounded graph size."""


def _normalize_title(value: str) -> str:
    """Normalize citation and paper titles for case- and punctuation-insensitive matching."""
    return " ".join(re.findall(r"\w+", value.casefold().replace("_", " ")))


def _as_authors(value: Any) -> list[str]:
    """Return author names as strings from the JSON or legacy string representations."""
    if isinstance(value, str):
        return [author.strip() for author in value.split(",") if author.strip()]
    if isinstance(value, list):
        authors = []
        for author in value:
            if isinstance(author, str) and author.strip():
                authors.append(author.strip())
            elif isinstance(author, dict):
                name = author.get("name") or author.get("full_name")
                if isinstance(name, str) and name.strip():
                    authors.append(name.strip())
        return authors
    return []


def _cluster_memberships(
    synthesized_review: Any, papers: list[Paper]
) -> tuple[dict[int, set[int]], dict[int, str]]:
    """Resolve citations and retain each paper's unique cluster-index memberships."""
    if not isinstance(synthesized_review, dict):
        return {}, {}

    clusters = synthesized_review.get("thematic_clusters")
    if not isinstance(clusters, list):
        return {}, {}

    papers_by_title: dict[str, set[int]] = {}
    for paper in papers:
        normalized_title = _normalize_title(paper.title)
        if normalized_title:
            papers_by_title.setdefault(normalized_title, set()).add(paper.id)

    titles_by_citation_key: dict[str, set[str]] = {}
    references = synthesized_review.get("references", [])
    if isinstance(references, list):
        for reference in references:
            if not isinstance(reference, dict):
                continue
            citation_key = reference.get("citation_key")
            title = reference.get("title")
            if not isinstance(citation_key, str) or not isinstance(title, str):
                continue
            normalized_key = _normalize_title(citation_key)
            normalized_title = _normalize_title(title)
            if normalized_key and normalized_title:
                titles_by_citation_key.setdefault(normalized_key, set()).add(normalized_title)

    memberships: dict[int, set[int]] = {}
    themes_by_cluster: dict[int, str] = {}
    for index, cluster in enumerate(clusters):
        if not isinstance(cluster, dict):
            continue
        theme = cluster.get("theme") or cluster.get("name") or f"Cluster {index + 1}"
        if not isinstance(theme, str):
            theme = str(theme)
        themes_by_cluster[index] = theme
        citations = cluster.get("citations", [])
        if not isinstance(citations, list):
            continue
        for citation in citations:
            title: Optional[str] = None
            title_only = False
            if isinstance(citation, str):
                title = citation
            elif isinstance(citation, dict):
                if "paper_title" in citation:
                    candidate = citation.get("paper_title")
                    title_only = True
                else:
                    candidate = citation.get("title")
                if isinstance(candidate, str):
                    title = candidate
            if title:
                normalized = _normalize_title(title)
                if not normalized:
                    continue

                candidate_ids = set(papers_by_title.get(normalized, set()))
                if not title_only:
                    # Bare strings may be titles or citation keys. Combine both interpretations
                    # and accept only one approved-paper match. Explicit paper_title fields are
                    # title-only and never enter this citation-key path.
                    referenced_titles = titles_by_citation_key.get(normalized, set())
                    if len(referenced_titles) > 1:
                        continue
                    for referenced_title in referenced_titles:
                        candidate_ids.update(papers_by_title.get(referenced_title, set()))
                if len(candidate_ids) == 1:
                    paper_id = next(iter(candidate_ids))
                    memberships.setdefault(paper_id, set()).add(index)
    return memberships, themes_by_cluster


class CitationGraphService:
    """Construct an in-memory graph from approved papers and synthesized themes."""

    @staticmethod
    async def build_citation_graph(
        db: AsyncSession,
        review_id: int,
    ) -> CitationGraphResponse:
        """Build graph nodes and evidence-supported thematic and coauthor edges."""
        review_result = await db.execute(
            select(LiteratureReview).where(LiteratureReview.id == review_id)
        )
        review = review_result.scalar_one_or_none()
        if review is None:
            return CitationGraphResponse(review_id=review_id)

        papers_result = await db.execute(
            select(Paper)
            .where(
                Paper.review_id == review_id,
                Paper.is_approved.is_(True),
            )
            .limit(MAX_APPROVED_GRAPH_NODES + 1)
        )
        papers = list(papers_result.scalars().all())
        if len(papers) > MAX_APPROVED_GRAPH_NODES:
            raise GraphSizeLimitExceeded(
                "Citation graph exceeds the maximum of "
                f"{MAX_APPROVED_GRAPH_NODES} approved papers."
            )
        if not papers:
            return CitationGraphResponse(review_id=review_id)

        paper_clusters, themes_by_cluster = _cluster_memberships(review.synthesized_review, papers)
        nodes: list[GraphNode] = []
        paper_authors: dict[str, set[str]] = {}
        clusters_by_node: dict[str, set[str]] = {}
        for paper in papers:
            authors = _as_authors(paper.authors)
            node_id = f"paper_{paper.id}"
            memberships = paper_clusters.get(paper.id, set())
            primary_cluster = min(
                memberships,
                key=lambda cluster_id: (themes_by_cluster[cluster_id], cluster_id),
                default=None,
            )
            nodes.append(
                GraphNode(
                    id=node_id,
                    label=paper.title,
                    type="paper",
                    year=paper.published_year,
                    authors=authors or None,
                    relevance_score=paper.relevance_score,
                    cluster=(
                        themes_by_cluster.get(primary_cluster)
                        if primary_cluster is not None
                        else None
                    ),
                    url=paper.pdf_url
                    or (f"https://arxiv.org/abs/{paper.arxiv_id}" if paper.arxiv_id else None),
                )
            )
            paper_authors[node_id] = set(authors)
            clusters_by_node[node_id] = memberships

        links: list[GraphLink] = []
        seen_edges: set[tuple[str, str, str]] = set()

        def add_edge(source: str, target: str, edge_type: str, weight: float) -> None:
            if source == target:
                return
            key = (min(source, target), max(source, target), edge_type)
            if key in seen_edges:
                return
            seen_edges.add(key)
            links.append(GraphLink(source=key[0], target=key[1], type=edge_type, weight=weight))

        for first, second in combinations(nodes, 2):
            if clusters_by_node[first.id] & clusters_by_node[second.id]:
                add_edge(first.id, second.id, "thematic_similarity", 0.85)
            if paper_authors[first.id] & paper_authors[second.id]:
                add_edge(first.id, second.id, "co_authorship", 0.9)

        return CitationGraphResponse(
            review_id=review_id,
            nodes=nodes,
            links=links,
            total_nodes=len(nodes),
            total_links=len(links),
        )
