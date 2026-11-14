"""Citation Knowledge Graph Topology Service.

Assignee Task (Issue BE-18):
- Query approved papers for a given review_id from Neon PostgreSQL.
- Extract thematic clusters and citations from LiteratureReview.synthesized_review.
- Construct nodes for all approved papers and/or thematic clusters.
- Compute topological links:
  1. Thematic similarity links (papers appearing together in a thematic cluster).
  2. Co-authorship links (papers sharing common authors).
  3. Direct citation / reference links (where available in paper metadata).
- Return CitationGraphResponse schema with nodes and links ready for D3.js force simulation.
"""

import logging
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paper import Paper
from app.models.review import LiteratureReview
from app.schemas.graph import CitationGraphResponse, GraphLink, GraphNode

logger = logging.getLogger(__name__)


class CitationGraphService:
    """Service to construct citation and semantic topology graph for literature reviews."""

    @staticmethod
    async def build_citation_graph(
        db: AsyncSession,
        review_id: int,
    ) -> CitationGraphResponse:
        """Construct the citation knowledge graph topology for an approved literature review.

        Args:
            db: AsyncSession connection to PostgreSQL.
            review_id: ID of the literature review.

        Returns:
            CitationGraphResponse containing nodes and links.
        """
        # 1. Fetch Review
        review_result = await db.execute(
            select(LiteratureReview).where(LiteratureReview.id == review_id)
        )
        review = review_result.scalar_one_or_none()
        if not review:
            return CitationGraphResponse(
                review_id=review_id,
                nodes=[],
                links=[],
                total_nodes=0,
                total_links=0,
            )

        # 2. Fetch Approved Papers
        papers_result = await db.execute(
            select(Paper).where(
                Paper.review_id == review_id,
                Paper.is_approved.is_(True),
            )
        )
        papers: List[Paper] = list(papers_result.scalars().all())

        if not papers:
            return CitationGraphResponse(
                review_id=review_id,
                nodes=[],
                links=[],
                total_nodes=0,
                total_links=0,
            )

        # TODO (Assignee - BE-18):
        # 1. Map papers to GraphNode instances:
        #    - id: f"paper_{p.id}"
        #    - label: p.title
        #    - year: p.published_year
        #    - authors: parsed list of authors
        #    - relevance_score: p.relevance_score
        #    - url: p.pdf_url or arxiv URL
        # 2. Extract clusters from review.synthesized_review:
        #    - Map papers to clusters based on title similarity or citation list in clusters
        # 3. Create GraphLink instances:
        #    - Pairwise links for papers within the same thematic cluster
        #    - Pairwise links for papers sharing at least one author
        # 4. Filter duplicate links and return populated CitationGraphResponse.

        nodes: List[GraphNode] = []
        for p in papers:
            authors_list: Optional[List[str]] = None
            if isinstance(p.authors, list):
                authors_list = [str(a) for a in p.authors]
            elif isinstance(p.authors, str):
                authors_list = [a.strip() for a in p.authors.split(",") if a.strip()]

            nodes.append(
                GraphNode(
                    id=f"paper_{p.id}",
                    label=p.title,
                    type="paper",
                    year=p.published_year,
                    authors=authors_list,
                    relevance_score=p.relevance_score,
                    url=p.pdf_url
                    or (f"https://arxiv.org/abs/{p.arxiv_id}" if p.arxiv_id else None),
                )
            )

        links: List[GraphLink] = []

        # Placeholder baseline link creation between adjacent papers for skeleton topology
        if len(nodes) > 1:
            for i in range(len(nodes) - 1):
                links.append(
                    GraphLink(
                        source=nodes[i].id,
                        target=nodes[i + 1].id,
                        type="thematic_similarity",
                        weight=0.75,
                    )
                )

        return CitationGraphResponse(
            review_id=review_id,
            nodes=nodes,
            links=links,
            total_nodes=len(nodes),
            total_links=len(links),
        )
