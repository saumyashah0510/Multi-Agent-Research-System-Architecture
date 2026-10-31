"""Unit tests for Agent 03: Screening and Relevance Scoring Node."""

from unittest.mock import MagicMock, patch

import pytest
from app.agents.nodes.screening_node import screening_node
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
