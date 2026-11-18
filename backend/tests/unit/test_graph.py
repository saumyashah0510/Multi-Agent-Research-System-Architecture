"""Tests for Citation Knowledge Graph schemas and topology service."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.schemas.graph import CitationGraphResponse, GraphLink, GraphNode
from app.services.graph_service import CitationGraphService


def _paper(paper_id, title, authors, **overrides):
    values = {
        "id": paper_id,
        "title": title,
        "authors": authors,
        "published_year": 2024,
        "relevance_score": 0.8,
        "pdf_url": None,
        "arxiv_id": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _result(value):
    result = MagicMock()
    if isinstance(value, list):
        result.scalars.return_value.all.return_value = value
    else:
        result.scalar_one_or_none.return_value = value
    return result


def test_citation_graph_schema_initialization():
    node = GraphNode(id="paper_1", label="Paper", authors=["Ada Lovelace"])
    link = GraphLink(source="paper_1", target="paper_2", weight=0.85)
    response = CitationGraphResponse(
        review_id=42,
        nodes=[node],
        links=[link],
        total_nodes=1,
        total_links=1,
    )

    assert response.review_id == 42
    assert response.nodes[0].id == "paper_1"
    assert response.links[0].weight == 0.85
    assert response.total_nodes == 1


@pytest.mark.asyncio
async def test_build_graph_matches_cluster_titles_and_creates_pairwise_edges():
    review = SimpleNamespace(
        synthesized_review={
            "thematic_clusters": [
                {
                    "theme": "Graph Learning",
                    "citations": ["  a STUDY:   on Graphs  ", "Paper B"],
                },
                {"theme": "Other", "citations": ["Paper C"]},
            ]
        }
    )
    papers = [
        _paper(1, "A Study on Graphs", ["Ada Lovelace", "Grace Hopper"]),
        _paper(2, "Paper B", "Grace Hopper, Alan Turing", arxiv_id="1234.5678"),
        _paper(3, "Paper C", ["Alan Turing"], pdf_url="https://example.test/paper-c"),
        _paper(4, "Unclustered", []),
    ]
    db = AsyncMock()
    db.execute.side_effect = [_result(review), _result(papers)]

    graph = await CitationGraphService.build_citation_graph(db, 7)

    assert graph.total_nodes == 4
    assert [node.cluster for node in graph.nodes] == [
        "Graph Learning",
        "Graph Learning",
        "Other",
        None,
    ]
    assert graph.nodes[1].url == "https://arxiv.org/abs/1234.5678"
    assert graph.nodes[2].url == "https://example.test/paper-c"
    assert {(edge.source, edge.target, edge.type, edge.weight) for edge in graph.links} == {
        ("paper_1", "paper_2", "thematic_similarity", 0.85),
        ("paper_1", "paper_2", "co_authorship", 0.9),
        ("paper_2", "paper_3", "co_authorship", 0.9),
    }
    assert all(edge.source != edge.target for edge in graph.links)
    assert graph.total_links == len(graph.links)


@pytest.mark.asyncio
async def test_citation_key_resolves_through_reference_title_and_direct_title_still_matches():
    review = SimpleNamespace(
        synthesized_review={
            "thematic_clusters": [
                {"theme": "Keyed Theme", "citations": ["smith et al., 2024"]},
                {"theme": "Direct Theme", "citations": ["Direct Paper"]},
            ],
            "references": [
                {
                    "title": "A Paper About Graphs",
                    "citation_key": "Smith et al. 2024",
                    "authors": ["A. Smith"],
                    "year": 2024,
                    "url": "https://example.test/a-paper",
                }
            ],
        }
    )
    papers = [
        _paper(1, "A Paper About Graphs", []),
        _paper(2, "  direct   PAPER! ", []),
        _paper(3, "Unmentioned", []),
    ]
    db = AsyncMock()
    db.execute.side_effect = [_result(review), _result(papers)]

    graph = await CitationGraphService.build_citation_graph(db, 9)

    assert [node.cluster for node in graph.nodes] == ["Keyed Theme", "Direct Theme", None]


@pytest.mark.asyncio
async def test_unknown_citation_key_is_ignored_safely():
    review = SimpleNamespace(
        synthesized_review={
            "thematic_clusters": [{"theme": "Theme", "citations": ["unknown, 2024"]}],
            "references": [],
        }
    )
    papers = [_paper(1, "A Paper", [])]
    db = AsyncMock()
    db.execute.side_effect = [_result(review), _result(papers)]

    graph = await CitationGraphService.build_citation_graph(db, 10)

    assert graph.nodes[0].cluster is None
    assert graph.links == []


@pytest.mark.asyncio
async def test_ambiguous_title_or_citation_key_does_not_select_arbitrary_paper():
    review = SimpleNamespace(
        synthesized_review={
            "thematic_clusters": [{"theme": "Theme", "citations": ["shared paper", "key 2024"]}],
            "references": [{"title": "Shared Paper", "citation_key": "Key 2024"}],
        }
    )
    papers = [_paper(1, "Shared Paper", []), _paper(2, "shared   PAPER", [])]
    db = AsyncMock()
    db.execute.side_effect = [_result(review), _result(papers)]

    graph = await CitationGraphService.build_citation_graph(db, 11)

    assert [node.cluster for node in graph.nodes] == [None, None]
    assert graph.links == []


@pytest.mark.asyncio
async def test_citation_key_with_multiple_reference_titles_is_ambiguous():
    review = SimpleNamespace(
        synthesized_review={
            "thematic_clusters": [{"theme": "Theme", "citations": ["Lee 2024"]}],
            "references": [
                {"title": "Paper A", "citation_key": "Lee 2024"},
                {"title": "Paper B", "citation_key": "Lee 2024"},
            ],
        }
    )
    papers = [_paper(1, "Paper A", [])]
    db = AsyncMock()
    db.execute.side_effect = [_result(review), _result(papers)]

    graph = await CitationGraphService.build_citation_graph(db, 16)

    assert graph.nodes[0].cluster is None
    assert graph.links == []


@pytest.mark.asyncio
async def test_paper_in_multiple_clusters_connects_to_each_cluster_membership_once():
    review = SimpleNamespace(
        synthesized_review={
            "thematic_clusters": [
                {"theme": "Cluster A", "citations": ["Paper A", "Shared Paper"]},
                {"theme": "Cluster B", "citations": ["Shared Paper", "Paper B"]},
            ]
        }
    )
    papers = [
        _paper(1, "Paper A", []),
        _paper(2, "Shared Paper", []),
        _paper(3, "Paper B", []),
    ]
    db = AsyncMock()
    db.execute.side_effect = [_result(review), _result(papers)]

    graph = await CitationGraphService.build_citation_graph(db, 12)

    thematic_edges = [edge for edge in graph.links if edge.type == "thematic_similarity"]
    assert {(edge.source, edge.target, edge.weight) for edge in thematic_edges} == {
        ("paper_1", "paper_2", 0.85),
        ("paper_2", "paper_3", 0.85),
    }
    assert len(thematic_edges) == 2


@pytest.mark.asyncio
async def test_papers_sharing_multiple_clusters_get_one_thematic_edge_and_stable_primary():
    review = SimpleNamespace(
        synthesized_review={
            "thematic_clusters": [
                {"theme": "Zeta", "citations": ["Paper A", "Paper B"]},
                {"theme": "Alpha", "citations": ["Paper A", "Paper B"]},
            ]
        }
    )
    papers = [_paper(1, "Paper A", []), _paper(2, "Paper B", [])]
    db = AsyncMock()
    db.execute.side_effect = [_result(review), _result(papers)]

    graph = await CitationGraphService.build_citation_graph(db, 13)

    thematic_edges = [edge for edge in graph.links if edge.type == "thematic_similarity"]
    assert len(thematic_edges) == 1
    assert thematic_edges[0].weight == 0.85
    assert [node.cluster for node in graph.nodes] == ["Alpha", "Alpha"]
    assert all(edge.source != edge.target for edge in graph.links)
    assert len({(edge.source, edge.target, edge.type) for edge in graph.links}) == len(graph.links)


@pytest.mark.asyncio
async def test_papers_sharing_a_cluster_connect_when_other_clusters_differ():
    review = SimpleNamespace(
        synthesized_review={
            "thematic_clusters": [
                {"theme": "Shared", "citations": ["Paper A", "Paper B"]},
                {"theme": "Only A", "citations": ["Paper A"]},
                {"theme": "Only B", "citations": ["Paper B"]},
            ]
        }
    )
    papers = [_paper(1, "Paper A", []), _paper(2, "Paper B", [])]
    db = AsyncMock()
    db.execute.side_effect = [_result(review), _result(papers)]

    graph = await CitationGraphService.build_citation_graph(db, 14)

    assert [(edge.source, edge.target, edge.type) for edge in graph.links] == [
        ("paper_1", "paper_2", "thematic_similarity")
    ]


@pytest.mark.asyncio
async def test_duplicate_node_ids_do_not_create_self_loops():
    review = SimpleNamespace(
        synthesized_review={"thematic_clusters": [{"theme": "Shared", "citations": ["Paper"]}]}
    )
    papers = [_paper(1, "Paper", ["Shared Author"]), _paper(1, "Paper", ["Shared Author"])]
    db = AsyncMock()
    db.execute.side_effect = [_result(review), _result(papers)]

    graph = await CitationGraphService.build_citation_graph(db, 17)

    assert all(edge.source != edge.target for edge in graph.links)


@pytest.mark.asyncio
async def test_coauthorship_edges_remain_pairwise_and_same_pair_keeps_both_types():
    review = SimpleNamespace(
        synthesized_review={
            "thematic_clusters": [{"theme": "Shared", "citations": ["Paper A", "Paper B"]}]
        }
    )
    papers = [
        _paper(1, "Paper A", ["Shared Author"]),
        _paper(2, "Paper B", ["Shared Author", "Second Author"]),
        _paper(3, "Paper C", ["Second Author"]),
    ]
    db = AsyncMock()
    db.execute.side_effect = [_result(review), _result(papers)]

    graph = await CitationGraphService.build_citation_graph(db, 15)

    assert {(edge.source, edge.target, edge.type, edge.weight) for edge in graph.links} == {
        ("paper_1", "paper_2", "thematic_similarity", 0.85),
        ("paper_1", "paper_2", "co_authorship", 0.9),
        ("paper_2", "paper_3", "co_authorship", 0.9),
    }


@pytest.mark.asyncio
async def test_build_graph_does_not_match_partial_titles_or_create_placeholder_edges():
    review = SimpleNamespace(
        synthesized_review={"thematic_clusters": [{"theme": "Theme", "citations": ["Paper"]}]}
    )
    papers = [_paper(1, "Paper One", []), _paper(2, "Paper Two", [])]
    db = AsyncMock()
    db.execute.side_effect = [_result(review), _result(papers)]

    graph = await CitationGraphService.build_citation_graph(db, 8)

    assert len(graph.nodes) == 2
    assert graph.links == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "review,papers", [(None, None), (SimpleNamespace(synthesized_review={}), [])]
)
async def test_build_graph_returns_expected_empty_graph(review, papers):
    db = AsyncMock()
    db.execute.side_effect = (
        [_result(review)] if review is None else [_result(review), _result(papers)]
    )

    graph = await CitationGraphService.build_citation_graph(db, 101)

    assert graph.review_id == 101
    assert graph.nodes == []
    assert graph.links == []
    assert graph.total_nodes == 0
    assert graph.total_links == 0
