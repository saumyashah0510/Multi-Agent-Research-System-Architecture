"""Unit and mocked tests for Paper Discovery & Screening Pipeline (Agents 01-03).

Assignee Task (Issue TEST-01):
- Test Query Expansion (Agent 01): verify query variations generation and JSON formatting.
- Test Academic Paper Discovery (Agent 02): mock arXiv, PubMed, and Semantic Scholar responses.
- Test Relevance Screening (Agent 03): verify scoring threshold filtering and paper retention.
"""

from unittest.mock import AsyncMock, patch

import app.agents.nodes.discovery_node as discovery_module
import pytest
from app.schemas.paper import PaperResponse

# ==========================================
# Agent 01: Query Expansion Tests
# ==========================================


def test_query_expansion_prompt_structure():
    """Verify that Query Expansion generates meaningful search keywords and sub-queries."""
    # TODO (Assignee - TEST-01):
    # 1. Provide a base academic query (e.g., 'Quantum Error Correction')
    # 2. Assert query is stripped and non-empty
    # 3. Verify sub-queries contain domain-specific terms
    base_query = "Quantum Error Correction"
    assert len(base_query.strip()) > 0
    # Starter placeholder assertion
    expanded_terms = [base_query, "Surface Codes", "Fault-tolerant Quantum Computing"]
    assert len(expanded_terms) >= 3


def test_query_expansion_fallback_on_empty():
    """Verify Query Expansion falls back gracefully when given empty or whitespace queries."""
    # TODO (Assignee - TEST-01):
    # Test that empty string query returns empty list or default fallback
    empty_query = "   "
    assert len(empty_query.strip()) == 0


# ==========================================
# Agent 02: Multi-Source Paper Discovery Tests
# ==========================================


@pytest.mark.asyncio
async def test_academic_search_arxiv_mock():
    """Verify academic search handles arXiv XML/JSON responses and parses paper metadata."""
    # TODO (Assignee - TEST-01):
    # 1. Mock external HTTP GET call to arXiv API using unittest.mock.AsyncMock
    # 2. Return sample XML containing title, authors, abstract, and arxiv_id
    # 3. Assert search service returns structured list of PaperResponse items
    mock_papers = [
        PaperResponse(
            title="Fault-Tolerant Surface Codes for Quantum Computing",
            authors=["Alice Smith", "Bob Jones"],
            abstract="We investigate threshold theorems for surface codes under depolarizing noise.",
            arxiv_id="2602.01234",
            relevance_score=0.92,
        )
    ]

    with patch(
        "app.services.search_service.search_academic_papers", new_callable=AsyncMock
    ) as mock_search:
        mock_search.return_value = mock_papers
        result = await mock_search("Quantum Error Correction")
        assert len(result) == 1
        assert result[0].arxiv_id == "2602.01234"


@pytest.mark.asyncio
async def test_academic_search_handles_api_failure_gracefully():
    """Verify that if one academic API fails (e.g. 500 error), other sources continue."""
    # TODO (Assignee - TEST-01):
    # 1. Simulate an HTTP 500 exception on arXiv
    # 2. Simulate HTTP 200 on Semantic Scholar
    # 3. Assert pipeline aggregates valid results without crashing
    with patch(
        "app.services.search_service.search_academic_papers", new_callable=AsyncMock
    ) as mock_search:
        mock_search.return_value = []
        result = await mock_search("quantum computing")
        assert result == []


# ==========================================
# Agent 03: Relevance Screening Tests
# ==========================================


def test_relevance_screening_score_threshold():
    """Verify papers scoring above threshold are retained and low-scoring papers are filtered."""
    # TODO (Assignee - TEST-01):
    # 1. Create candidate papers with relevance scores >= 0.70 (Pass) and < 0.70 (Filter)
    # 2. Verify filtering logic produces expected subset
    threshold = 0.70

    candidates = [
        PaperResponse(
            title="Relevant Quantum Paper",
            authors=["Alice Smith"],
            abstract="Quantum error correction with surface codes",
            relevance_score=0.88,
        ),
        PaperResponse(
            title="Irrelevant Cooking Recipe Paper",
            authors=["Chef Pierre"],
            abstract="Baking French bread at home",
            relevance_score=0.25,
        ),
        PaperResponse(
            title="Borderline Quantum Architecture Paper",
            authors=["Bob Jones"],
            abstract="Hardware noise modeling",
            relevance_score=0.72,
        ),
    ]

    approved = [p for p in candidates if (p.relevance_score or 0.0) >= threshold]
    assert len(approved) == 2
    assert all((p.relevance_score or 0.0) >= threshold for p in approved)


# ==========================================
# Agent 02: Discovery Node Tests (AI-03)
# ==========================================


@pytest.mark.asyncio
async def test_discovery_returns_normalized_papers(monkeypatch):
    mock_search = AsyncMock(
        return_value=[
            {
                "title": "Quantum Machine Learning",
                "authors": ["Alice Smith"],
                "abstract": "Research on quantum machine learning.",
                "publication_date": "2025-06-10",
                "arxiv_id": "2506.12345",
                "doi": "10.1234/example",
                "source": "arxiv",
            }
        ]
    )

    monkeypatch.setattr(discovery_module, "search_academic_papers", mock_search)

    result = await discovery_module.discovery_node({"search_queries": ["Quantum ML"]})

    assert len(result["discovered_papers"]) == 1
    assert result["discovered_papers"][0]["year"] == 2025
    assert result["current_step"] == "paper_discovery_completed"


@pytest.mark.asyncio
async def test_discovery_deduplicates_by_arxiv_id(monkeypatch):
    mock_search = AsyncMock(
        side_effect=[
            [
                {
                    "title": "Quantum Computing",
                    "abstract": "First abstract.",
                    "arxiv_id": "2501.12345",
                }
            ],
            [
                {
                    "title": "Different title",
                    "abstract": "Second abstract.",
                    "arxiv_id": "2501.12345",
                }
            ],
        ]
    )

    monkeypatch.setattr(discovery_module, "search_academic_papers", mock_search)

    result = await discovery_module.discovery_node(
        {"search_queries": ["Quantum", "Quantum Algorithms"]}
    )

    assert len(result["discovered_papers"]) == 1
    assert mock_search.await_count == 2


@pytest.mark.asyncio
async def test_discovery_deduplicates_by_doi(monkeypatch):
    mock_search = AsyncMock(
        return_value=[
            {
                "title": "First Paper",
                "abstract": "First abstract.",
                "doi": "10.1234/duplicate",
            },
            {
                "title": "Second Paper",
                "abstract": "Second abstract.",
                "doi": "https://doi.org/10.1234/duplicate",
            },
        ]
    )

    monkeypatch.setattr(discovery_module, "search_academic_papers", mock_search)

    result = await discovery_module.discovery_node({"search_queries": ["Research"]})

    assert len(result["discovered_papers"]) == 1


@pytest.mark.asyncio
async def test_discovery_deduplicates_normalized_titles(monkeypatch):
    mock_search = AsyncMock(
        return_value=[
            {
                "title": "Quantum: Machine Learning!",
                "abstract": "First abstract.",
            },
            {
                "title": "quantum machine learning",
                "abstract": "Second abstract.",
            },
        ]
    )

    monkeypatch.setattr(discovery_module, "search_academic_papers", mock_search)

    result = await discovery_module.discovery_node({"search_queries": ["Quantum ML"]})

    assert len(result["discovered_papers"]) == 1


@pytest.mark.asyncio
async def test_discovery_filters_incomplete_papers(monkeypatch):
    mock_search = AsyncMock(
        return_value=[
            {"title": "", "abstract": "Missing title."},
            {"title": "Missing abstract", "abstract": ""},
            {
                "title": "Valid Paper",
                "abstract": "Valid abstract.",
            },
        ]
    )

    monkeypatch.setattr(discovery_module, "search_academic_papers", mock_search)

    result = await discovery_module.discovery_node({"search_queries": ["Research"]})

    assert len(result["discovered_papers"]) == 1
    assert result["discovered_papers"][0]["title"] == "Valid Paper"


@pytest.mark.asyncio
async def test_discovery_falls_back_to_user_query(monkeypatch):
    mock_search = AsyncMock(return_value=[])

    monkeypatch.setattr(discovery_module, "search_academic_papers", mock_search)

    await discovery_module.discovery_node(
        {
            "search_queries": [],
            "user_query": "Quantum Computing",
        }
    )

    mock_search.assert_awaited_once_with("Quantum Computing", max_results=10)


@pytest.mark.asyncio
async def test_discovery_continues_after_query_failure(monkeypatch):
    mock_search = AsyncMock(
        side_effect=[
            RuntimeError("API unavailable"),
            [
                {
                    "title": "Successful Paper",
                    "abstract": "Successful abstract.",
                }
            ],
        ]
    )

    monkeypatch.setattr(discovery_module, "search_academic_papers", mock_search)

    result = await discovery_module.discovery_node({"search_queries": ["Failed", "Successful"]})

    assert len(result["discovered_papers"]) == 1
    assert result["discovered_papers"][0]["title"] == "Successful Paper"


@pytest.mark.asyncio
async def test_discovery_handles_empty_queries(monkeypatch):
    mock_search = AsyncMock()

    monkeypatch.setattr(discovery_module, "search_academic_papers", mock_search)

    result = await discovery_module.discovery_node({"search_queries": [], "user_query": ""})

    assert result["discovered_papers"] == []
    assert result["current_step"] == "paper_discovery_completed"
    mock_search.assert_not_awaited()
