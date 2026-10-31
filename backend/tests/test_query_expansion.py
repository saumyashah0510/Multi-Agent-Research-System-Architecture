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
async def test_query_expansion_node_empty_query_fail_fast():
    """Verify ValueError is raised when an empty or whitespace user query is provided."""
    state = {"user_query": "   "}
    with pytest.raises(ValueError, match="user_query cannot be empty"):
        await query_expansion_node(state)


@pytest.mark.asyncio
async def test_query_expansion_node_missing_api_key_fail_fast(monkeypatch):
    """Verify RuntimeError is raised when GEMINI_API_KEY is not configured."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")

    state = {"user_query": "Deep Reinforcement Learning in Robotics"}
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY is not configured"):
        await query_expansion_node(state)


@pytest.mark.asyncio
async def test_query_expansion_node_api_failure_fail_fast(monkeypatch):
    """Verify RuntimeError is raised when Gemini API throws an exception."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-gemini-key")

    with patch("app.agents.nodes.query_expansion_node.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = RuntimeError("API quota exceeded")
        mock_client_cls.return_value = mock_client

        state = {"user_query": "Transformer Attention Sparsity"}
        with pytest.raises(RuntimeError, match="Query expansion failed due to LLM error"):
            await query_expansion_node(state)
