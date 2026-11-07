"""Unit tests for Agent 03: Screening and Relevance Scoring Node."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.agents.nodes.screening_node import screening_node, verify_paper_full_text
from app.core.config import settings


@pytest.mark.asyncio
async def test_screening_node_success(monkeypatch):
    """Verify papers scoring >= 0.6 are accepted with reasons, and < 0.6 are excluded."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-gemini-key")

    mock_response = MagicMock()
    mock_response.text = (
        '{"decisions": ['
        '  {"paper_id_or_title": "[1]", "relevance_score": 0.92, "reason": "Directly analyzes quantum VQE algorithms for oncology.", "accepted": true},'
        '  {"paper_id_or_title": "[2]", "relevance_score": 0.25, "reason": "Unrelated topic on baking bread.", "accepted": false}'
        "]}"
    )

    with patch("app.agents.nodes.screening_node.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client

        state = {
            "user_query": "Quantum Computing in Cancer Drug Discovery",
            "discovered_papers": [
                {
                    "title": "VQE for Oncology Kinase Inhibitors",
                    "abstract": "Applying variational quantum eigensolvers to molecular docking.",
                },
                {
                    "title": "Baking Sourdough Bread at Home",
                    "abstract": "A guide to bread fermentation temperature.",
                },
            ],
        }

        result = await screening_node(state)

        # Only the relevant paper should be retained
        assert len(result["screened_papers"]) == 1
        accepted_paper = result["screened_papers"][0]
        assert accepted_paper["title"] == "VQE for Oncology Kinase Inhibitors"
        assert accepted_paper["relevance_score"] == 0.92
        assert "quantum VQE" in accepted_paper["screening_reason"]
        assert result["current_step"] == "screening_completed"


@pytest.mark.asyncio
async def test_screening_node_empty_discovered_papers():
    """Verify clean empty list returned when no candidate papers exist."""
    state = {"user_query": "Quantum Error Correction", "discovered_papers": []}
    result = await screening_node(state)

    assert result["screened_papers"] == []
    assert result["current_step"] == "screening_completed"


@pytest.mark.asyncio
async def test_screening_node_missing_api_key_fail_fast(monkeypatch):
    """Verify fail-fast RuntimeError when GEMINI_API_KEY is not configured."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")

    state = {
        "user_query": "Quantum Computing",
        "discovered_papers": [{"title": "Sample Paper", "abstract": "Sample abstract"}],
    }

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY is not configured"):
        await screening_node(state)


@pytest.mark.asyncio
async def test_screening_node_api_failure_fail_fast(monkeypatch):
    """Verify fail-fast RuntimeError when Gemini API throws an exception."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-gemini-key")

    with patch("app.agents.nodes.screening_node.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = RuntimeError("API Quota Exceeded")
        mock_client_cls.return_value = mock_client

        state = {
            "user_query": "Quantum Computing",
            "discovered_papers": [{"title": "Sample Paper", "abstract": "Sample abstract"}],
        }

        with pytest.raises(RuntimeError, match="Paper screening failed due to LLM error"):
            await screening_node(state)


@pytest.mark.asyncio
async def test_verify_paper_full_text_direct_pdf_url():
    """Direct PDF URL should be immediately returned without network lookup."""
    paper = {"title": "Direct PDF Paper", "pdf_url": "https://example.com/paper.pdf"}
    url = await verify_paper_full_text(paper)
    assert url == "https://example.com/paper.pdf"


@pytest.mark.asyncio
async def test_verify_paper_full_text_arxiv():
    """Paper with arxiv_id should construct arxiv PDF link."""
    paper = {"title": "ArXiv Paper", "arxiv_id": "2401.12345"}
    url = await verify_paper_full_text(paper)
    assert url == "https://arxiv.org/pdf/2401.12345.pdf"


@pytest.mark.asyncio
async def test_verify_paper_full_text_biorxiv():
    """bioRxiv paper should resolve through biorxiv resolver."""
    paper = {
        "title": "BioRxiv Paper",
        "doi": "10.1101/2020.01.31.929042",
        "source": "biorxiv",
    }
    with patch(
        "app.agents.nodes.screening_node.resolve_biorxiv_pdf_url",
        new=AsyncMock(
            return_value="https://www.biorxiv.org/content/10.1101/2020.01.31.929042.full.pdf"
        ),
    ):
        url = await verify_paper_full_text(paper)
        assert url == "https://www.biorxiv.org/content/10.1101/2020.01.31.929042.full.pdf"


@pytest.mark.asyncio
async def test_verify_paper_full_text_pubmed():
    """PubMed paper should resolve through pubmed resolver."""
    paper = {
        "title": "PubMed Paper",
        "pubmed_id": "33887588",
        "doi": "10.1038/s41586-021-03529-1",
        "source": "pubmed",
    }
    with patch(
        "app.agents.nodes.screening_node.resolve_pubmed_pdf_url",
        new=AsyncMock(return_value="https://www.nature.com/articles/s41586-021-03529-1.pdf"),
    ):
        url = await verify_paper_full_text(paper)
        assert url == "https://www.nature.com/articles/s41586-021-03529-1.pdf"


@pytest.mark.asyncio
async def test_verify_paper_full_text_paywalled_returns_none():
    """Paywalled paper lacking open access resolution must return None."""
    paper = {
        "title": "Paywalled Paper",
        "doi": "10.1016/j.cell.2023.01.001",
        "source": "crossref",
    }
    with patch(
        "app.agents.nodes.screening_node.resolve_unpaywall_pdf_url",
        new=AsyncMock(return_value=None),
    ):
        url = await verify_paper_full_text(paper)
        assert url is None


@pytest.mark.asyncio
async def test_screening_node_filters_paywalled_papers(monkeypatch):
    """Screening node must discard papers that pass relevance threshold but are paywalled."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-gemini-key")

    mock_response = MagicMock()
    mock_response.text = (
        '{"decisions": ['
        '  {"paper_id_or_title": "[1]", "relevance_score": 0.95, "reason": "Highly relevant open access paper.", "accepted": true},'
        '  {"paper_id_or_title": "[2]", "relevance_score": 0.90, "reason": "Highly relevant but paywalled paper.", "accepted": true}'
        "]}"
    )

    with patch("app.agents.nodes.screening_node.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client

        with patch(
            "app.agents.nodes.screening_node.verify_paper_full_text",
            side_effect=[
                "https://open-access.org/paper1.pdf",  # Paper 1 has full text
                None,  # Paper 2 is paywalled
            ],
        ):
            state = {
                "user_query": "CRISPR Therapeutics",
                "discovered_papers": [
                    {
                        "title": "Open Access CRISPR Discovery",
                        "abstract": "Breakthrough CRISPR cas9 in vivo therapy.",
                        "doi": "10.1371/journal.pbio.3000349",
                    },
                    {
                        "title": "Paywalled Closed CRISPR Study",
                        "abstract": "Proprietary CRISPR trial data behind paywall.",
                        "doi": "10.1016/paywalled.2023",
                    },
                ],
            }

            result = await screening_node(state)

            # Only Paper 1 should be retained; Paper 2 filtered out by gatekeeper
            assert len(result["screened_papers"]) == 1
            accepted = result["screened_papers"][0]
            assert accepted["title"] == "Open Access CRISPR Discovery"
            assert accepted["pdf_url"] == "https://open-access.org/paper1.pdf"
            assert accepted["has_full_text"] is True
            assert accepted["relevance_score"] == 0.95
