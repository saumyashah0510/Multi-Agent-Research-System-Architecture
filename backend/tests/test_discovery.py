"""Unit and mocked tests for Paper Discovery & Screening Pipeline (Agents 01-03).

All LLM and network calls are mocked, so these tests are fast, free and
deterministic.

Issue TEST-01 coverage:
- Agent 01 (Query Expansion): sub-query generation, empty-input handling, fallback.
- Agent 02 (Paper Discovery): metadata normalization, failure isolation,
  deduplication.
- Agent 03 (Relevance Screening): score threshold filtering and edge cases.
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import app.agents.nodes.discovery_node as discovery_module
import app.agents.nodes.query_expansion_node as expansion_module
import app.agents.nodes.screening_node as screening_module
import pytest
from app.schemas.paper import PaperResponse


def _patch_gemini(monkeypatch, module, payload: dict) -> MagicMock:
    """Replace the Gemini client and settings inside a node module with fakes."""
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = MagicMock(text=json.dumps(payload))
    monkeypatch.setattr(
        module, "genai", SimpleNamespace(Client=MagicMock(return_value=fake_client))
    )
    monkeypatch.setattr(
        module,
        "settings",
        SimpleNamespace(GEMINI_API_KEY="test-key", gemini_model_candidates=["test-model"]),
    )
    return fake_client


# ==========================================
# Schema check
# ==========================================


def test_paper_response_schema_defaults():
    """PaperResponse exposes the expected fields and safe defaults."""
    paper = PaperResponse(title="T", authors=["A"], abstract="Abs")

    assert paper.arxiv_id is None
    assert paper.relevance_score is None
    assert paper.is_approved is False


# ==========================================
# Agent 01: Query Expansion Tests
# ==========================================


@pytest.mark.asyncio
async def test_query_expansion_prompt_structure(monkeypatch):
    """Expansion returns multiple sub-queries and the topic reaches the LLM prompt."""
    fake_client = _patch_gemini(
        monkeypatch,
        expansion_module,
        {
            "target_domains": ["quant-ph", "cs.IT"],
            "search_queries": [
                "surface codes threshold theorem",
                "fault-tolerant quantum computation",
                "quantum error correction benchmarks",
            ],
        },
    )

    result = await expansion_module.query_expansion_node({"user_query": "Quantum Error Correction"})

    assert len(result["search_queries"]) >= 3
    assert all(q.strip() for q in result["search_queries"])
    assert result["target_domains"] == ["quant-ph", "cs.IT"]
    assert result["current_step"] == "query_expansion_completed"

    fake_client.models.generate_content.assert_called_once()
    contents = fake_client.models.generate_content.call_args.kwargs["contents"]
    assert "Quantum Error Correction" in contents[1]


@pytest.mark.asyncio
@pytest.mark.parametrize("empty_query", ["", "   ", "\n\t"])
async def test_query_expansion_fallback_on_empty(monkeypatch, empty_query):
    """Empty or whitespace input fails fast and never calls the LLM."""
    fake_client = _patch_gemini(
        monkeypatch,
        expansion_module,
        {"target_domains": ["x"], "search_queries": ["x"]},
    )

    with pytest.raises(ValueError, match="cannot be empty"):
        await expansion_module.query_expansion_node({"user_query": empty_query})

    fake_client.models.generate_content.assert_not_called()


@pytest.mark.asyncio
async def test_query_expansion_falls_back_to_user_query_when_llm_returns_none(monkeypatch):
    """If the LLM returns no queries, the original topic is used as the query."""
    _patch_gemini(
        monkeypatch,
        expansion_module,
        {"target_domains": [], "search_queries": []},
    )

    result = await expansion_module.query_expansion_node({"user_query": "Quantum Computing"})

    assert result["search_queries"] == ["Quantum Computing"]
    assert result["target_domains"] == ["Computer Science"]


# ==========================================
# Agent 02: Multi-Source Paper Discovery Tests
# ==========================================


@pytest.mark.asyncio
async def test_academic_search_arxiv_mock(monkeypatch):
    """arXiv-style metadata is normalized into the discovered paper schema."""
    mock_search = AsyncMock(
        return_value=[
            {
                "title": "Fault-Tolerant Surface Codes for Quantum Computing",
                "authors": ["Alice Smith", "Bob Jones"],
                "abstract": "We investigate threshold theorems for surface codes.",
                "publication_date": "2026-02-03",
                "arxiv_id": "2602.01234",
                "source": "arxiv",
            }
        ]
    )
    monkeypatch.setattr(discovery_module, "search_academic_papers", mock_search)

    result = await discovery_module.discovery_node({"search_queries": ["Quantum Error Correction"]})

    papers = result["discovered_papers"]
    assert len(papers) == 1
    assert papers[0]["arxiv_id"] == "2602.01234"
    assert papers[0]["title"].startswith("Fault-Tolerant")
    assert papers[0]["authors"] == ["Alice Smith", "Bob Jones"]
    assert papers[0]["year"] == 2026
    assert papers[0]["source"] == "arxiv"
    mock_search.assert_awaited_once()


@pytest.mark.asyncio
async def test_academic_search_handles_api_failure_gracefully(monkeypatch):
    """A query failing with an HTTP 500 must not stop results from the other query."""
    mock_search = AsyncMock(
        side_effect=[
            RuntimeError("500 Server Error from arXiv"),
            [
                {
                    "title": "Semantic Scholar Paper",
                    "abstract": "Valid abstract from the working source.",
                    "source": "semantic_scholar",
                }
            ],
        ]
    )
    monkeypatch.setattr(discovery_module, "search_academic_papers", mock_search)

    result = await discovery_module.discovery_node(
        {"search_queries": ["arxiv query", "semantic scholar query"]}
    )

    assert mock_search.await_count == 2
    assert len(result["discovered_papers"]) == 1
    assert result["discovered_papers"][0]["title"] == "Semantic Scholar Paper"
    assert result["current_step"] == "paper_discovery_completed"


# ==========================================
# Agent 03: Relevance Screening Tests
# ==========================================


def _decisions(scores: dict[str, float]) -> dict:
    """Build a fake Gemini screening response from {title: score}."""
    return {
        "decisions": [
            {
                "paper_id_or_title": title,
                "relevance_score": score,
                "accepted": score >= 0.60,
                "reason": f"Scored {score}",
            }
            for title, score in scores.items()
        ]
    }


@pytest.mark.asyncio
async def test_relevance_screening_score_threshold(monkeypatch):
    """Papers scoring >= 0.60 are kept, lower ones are dropped (boundary included)."""
    scores = {
        "Relevant Quantum Paper": 0.88,
        "Borderline Quantum Paper": 0.72,
        "Exactly At Threshold": 0.60,
        "Just Below Threshold": 0.59,
        "Irrelevant Cooking Paper": 0.25,
    }
    _patch_gemini(monkeypatch, screening_module, _decisions(scores))

    state = {
        "user_query": "Quantum Error Correction",
        "discovered_papers": [
            {"title": title, "abstract": f"Abstract of {title}"} for title in scores
        ],
    }

    result = await screening_module.screening_node(state)

    kept = {p["title"]: p for p in result["screened_papers"]}
    assert set(kept) == {
        "Relevant Quantum Paper",
        "Borderline Quantum Paper",
        "Exactly At Threshold",
    }
    assert kept["Relevant Quantum Paper"]["relevance_score"] == 0.88
    assert kept["Exactly At Threshold"]["screening_reason"] == "Scored 0.6"
    assert result["current_step"] == "screening_completed"


@pytest.mark.asyncio
async def test_relevance_screening_skips_llm_when_no_papers(monkeypatch):
    """With no discovered papers, screening returns empty without calling the LLM."""
    fake_client = _patch_gemini(monkeypatch, screening_module, _decisions({}))

    result = await screening_module.screening_node(
        {"user_query": "Quantum", "discovered_papers": []}
    )

    assert result["screened_papers"] == []
    assert result["current_step"] == "screening_completed"
    fake_client.models.generate_content.assert_not_called()


@pytest.mark.asyncio
async def test_relevance_screening_requires_api_key(monkeypatch):
    """Screening fails fast with a clear error if the Gemini key is missing."""
    monkeypatch.setattr(
        screening_module,
        "settings",
        SimpleNamespace(GEMINI_API_KEY="", gemini_model_candidates=["m"]),
    )

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        await screening_module.screening_node(
            {"user_query": "Quantum", "discovered_papers": [{"title": "T", "abstract": "A"}]}
        )


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


@pytest.mark.asyncio
async def test_discovery_caps_papers_at_70(monkeypatch):
    """Verify that discovered papers are hard-capped at 70 to protect downstream token limits."""
    bulk_papers = [
        {"title": f"Unique Paper {i}", "abstract": f"Abstract {i}", "doi": f"10.1000/{i}"}
        for i in range(100)
    ]
    mock_search = AsyncMock(return_value=bulk_papers)
    monkeypatch.setattr(discovery_module, "search_academic_papers", mock_search)

    result = await discovery_module.discovery_node({"search_queries": ["AI"]})

    assert len(result["discovered_papers"]) == 70
    assert result["current_step"] == "paper_discovery_completed"
