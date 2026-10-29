"""Unit tests for Agent 01: Query Expansion and Domain Classifier Node."""

from unittest.mock import MagicMock, patch

import pytest
from app.agents.nodes.query_expansion_node import query_expansion_node
from app.core.config import settings


@pytest.mark.asyncio
async def test_query_expansion_node_success(monkeypatch):
    """Verify standard query expansion generates structured domains and 3-5 sub-queries."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-gemini-key")

    mock_response = MagicMock()
    mock_response.text = (
        '{"target_domains": ["cs.AI", "cs.LG", "quant-ph"], '
        '"search_queries": ["quantum machine learning", "variational quantum eigensolver", "quantum neural networks"]}'
    )

    with patch("app.agents.nodes.query_expansion_node.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client

        state = {"user_query": "Quantum Machine Learning in Cancer Drug Discovery"}
        result = await query_expansion_node(state)

        assert result["target_domains"] == ["cs.AI", "cs.LG", "quant-ph"]
        assert len(result["search_queries"]) == 3
        assert "quantum machine learning" in result["search_queries"]
        assert result["current_step"] == "query_expansion_completed"


@pytest.mark.asyncio
async def test_query_expansion_node_empty_query_fallback():
    """Verify fallback behavior when an empty or whitespace user query is provided."""
    state = {"user_query": "   "}
    result = await query_expansion_node(state)

    assert "Computer Science" in result["target_domains"]
    assert len(result["search_queries"]) > 0
    assert result["current_step"] == "query_expansion_completed"


@pytest.mark.asyncio
async def test_query_expansion_node_missing_api_key_fallback(monkeypatch):
    """Verify fallback behavior when GEMINI_API_KEY is not configured."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")

    state = {"user_query": "Deep Reinforcement Learning in Robotics"}
    result = await query_expansion_node(state)

    assert result["target_domains"] == ["Computer Science"]
    assert result["search_queries"] == ["Deep Reinforcement Learning in Robotics"]
    assert result["current_step"] == "query_expansion_completed"


@pytest.mark.asyncio
async def test_query_expansion_node_resilience_on_exception(monkeypatch):
    """Verify pipeline resiliency when Gemini API throws an unexpected exception."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-gemini-key")

    with patch("app.agents.nodes.query_expansion_node.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = RuntimeError("API quota exceeded")
        mock_client_cls.return_value = mock_client

        state = {"user_query": "Transformer Attention Sparsity"}
        result = await query_expansion_node(state)

        assert result["target_domains"] == ["Computer Science"]
        assert result["search_queries"] == ["Transformer Attention Sparsity"]
        assert result["current_step"] == "query_expansion_completed"
