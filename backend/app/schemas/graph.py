"""Pydantic schemas for Citation Knowledge Graph topology."""

from typing import List, Optional

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    """A node in the citation and thematic knowledge graph."""

    id: str = Field(..., description="Unique node identifier (e.g. paper_1, theme_0)")
    label: str = Field(..., description="Display title for the paper or thematic cluster")
    type: str = Field(default="paper", description="Node category: 'paper' or 'theme'")
    year: Optional[int] = Field(None, description="Publication year")
    authors: Optional[List[str]] = Field(default=None, description="List of paper authors")
    relevance_score: Optional[float] = Field(None, description="Relevance score (0.0 to 1.0)")
    cluster: Optional[str] = Field(None, description="Thematic cluster name or group identifier")
    url: Optional[str] = Field(None, description="Direct URL to ArXiv, PubMed, or PDF")
    citation_count: Optional[int] = Field(None, description="Reported or estimated citation count")


class GraphLink(BaseModel):
    """An edge/link connecting two nodes in the knowledge graph."""

    source: str = Field(..., description="ID of the source node")
    target: str = Field(..., description="ID of the target node")
    type: str = Field(
        default="thematic_similarity",
        description="Relationship type: 'thematic_similarity', 'co_authorship', or 'direct_citation'",
    )
    weight: float = Field(default=1.0, description="Normalized link strength between 0.0 and 1.0")


class CitationGraphResponse(BaseModel):
    """Complete network topology payload for D3.js force-directed visualization."""

    review_id: int = Field(..., description="Literature review session ID")
    nodes: List[GraphNode] = Field(default_factory=list, description="List of graph nodes")
    links: List[GraphLink] = Field(default_factory=list, description="List of topological links")
    total_nodes: int = Field(0, description="Total node count")
    total_links: int = Field(0, description="Total edge count")
