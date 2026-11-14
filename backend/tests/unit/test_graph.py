"""Unit tests for Citation Knowledge Graph Topology schema and service (Issue BE-18)."""

from app.schemas.graph import CitationGraphResponse, GraphLink, GraphNode


def test_citation_graph_schema_initialization():
    """Verify CitationGraphResponse schema serialization and constraints."""
    node_a = GraphNode(
        id="paper_1",
        label="Attention Is All You Need",
        type="paper",
        year=2017,
        authors=["Vaswani et al."],
        relevance_score=0.98,
        url="https://arxiv.org/abs/1706.03762",
    )
    node_b = GraphNode(
        id="paper_2",
        label="BERT: Pre-training of Deep Bidirectional Transformers",
        type="paper",
        year=2018,
        authors=["Devlin et al."],
        relevance_score=0.95,
        url="https://arxiv.org/abs/1810.04805",
    )
    link = GraphLink(
        source="paper_1",
        target="paper_2",
        type="thematic_similarity",
        weight=0.88,
    )

    response = CitationGraphResponse(
        review_id=42,
        nodes=[node_a, node_b],
        links=[link],
        total_nodes=2,
        total_links=1,
    )

    assert response.review_id == 42
    assert response.total_nodes == 2
    assert response.total_links == 1
    assert response.nodes[0].id == "paper_1"
    assert response.links[0].type == "thematic_similarity"


def test_empty_citation_graph_defaults():
    """Verify empty CitationGraphResponse initializes with empty lists and zero counts."""
    response = CitationGraphResponse(
        review_id=101,
        nodes=[],
        links=[],
        total_nodes=0,
        total_links=0,
    )
    assert response.review_id == 101
    assert len(response.nodes) == 0
    assert len(response.links) == 0
