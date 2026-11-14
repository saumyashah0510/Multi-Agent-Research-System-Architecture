"""Unit tests for Groq Cloud LLM Service and Agent Node Fallback Cascade."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from app.agents.nodes.query_expansion_node import query_expansion_node
from app.agents.nodes.report_synthesis_node import report_synthesis_node
from app.agents.nodes.screening_node import screening_node
from app.core.config import settings
from app.schemas.agent_outputs import (
    PaperScreeningItem,
    QueryExpansionOutput,
    ScreeningOutput,
    SynthesizedReviewOutput,
)
from app.services.groq_service import _clean_json_string, call_groq_structured
from pydantic import BaseModel


class DummyOutput(BaseModel):
    summary: str
    score: int


def test_clean_json_string_variants():
    """Verify markdown fences and whitespace are stripped accurately."""
    assert _clean_json_string('{"a": 1}') == '{"a": 1}'
    assert _clean_json_string('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert _clean_json_string('```\n{"a": 1}\n```') == '{"a": 1}'
    assert _clean_json_string('  \n  {"a": 1}  \n ') == '{"a": 1}'


@pytest.mark.asyncio
async def test_groq_missing_api_key_raises_error(monkeypatch):
    """Verify RuntimeError is raised when GROQ_API_KEY is not set."""
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")
    with pytest.raises(RuntimeError, match="GROQ_API_KEY is not configured"):
        await call_groq_structured(
            system_prompt="Test system",
            user_prompt="Test user",
            response_schema=DummyOutput,
        )


@pytest.mark.asyncio
async def test_groq_call_structured_success(monkeypatch):
    """Verify successful invocation and Pydantic validation via mock httpx client."""
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test_key_12345")

    fake_response = MagicMock(spec=httpx.Response)
    fake_response.status_code = 200
    fake_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({"summary": "Valid Groq Output", "score": 95}),
                }
            }
        ]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = fake_response
        result = await call_groq_structured(
            system_prompt="System instructions",
            user_prompt="User input",
            response_schema=DummyOutput,
        )

        assert isinstance(result, DummyOutput)
        assert result.summary == "Valid Groq Output"
        assert result.score == 95
        assert mock_post.await_count == 1


@pytest.mark.asyncio
async def test_groq_call_structured_fallback_between_models(monkeypatch):
    """Verify that if the primary Groq model fails, it falls back to the secondary model."""
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test_key_12345")
    monkeypatch.setattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")
    monkeypatch.setattr(settings, "GROQ_FALLBACK_MODELS", "llama-3.1-8b-instant")

    fail_response = MagicMock(spec=httpx.Response)
    fail_response.status_code = 429
    fail_response.text = "Rate limit exceeded"

    success_response = MagicMock(spec=httpx.Response)
    success_response.status_code = 200
    success_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({"summary": "Fallback Success", "score": 88}),
                }
            }
        ]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [fail_response, success_response]
        result = await call_groq_structured(
            system_prompt="System",
            user_prompt="User",
            response_schema=DummyOutput,
        )

        assert result.summary == "Fallback Success"
        assert result.score == 88
        assert mock_post.await_count == 2


@pytest.mark.asyncio
async def test_groq_all_models_fail_raises_runtime_error(monkeypatch):
    """Verify RuntimeError is raised when all Groq models return errors."""
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test_key_12345")

    fail_response = MagicMock(spec=httpx.Response)
    fail_response.status_code = 500
    fail_response.text = "Internal Groq Error"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = fail_response
        with pytest.raises(RuntimeError, match="All configured Groq models .* failed"):
            await call_groq_structured(
                system_prompt="System",
                user_prompt="User",
                response_schema=DummyOutput,
            )


@pytest.mark.asyncio
async def test_query_expansion_node_falls_back_to_groq(monkeypatch):
    """Verify query_expansion_node seamlessly falls back to Groq when Gemini fails."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-gemini-key")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "mock-groq-key")

    mock_groq_output = QueryExpansionOutput(
        is_valid_academic_topic=True,
        target_domains=["cs.AI", "cs.RO"],
        search_queries=["reinforcement learning robotics", "sim-to-real transfer"],
    )

    with patch("app.agents.nodes.query_expansion_node.genai.Client") as mock_gemini_cls:
        mock_gemini = MagicMock()
        mock_gemini.models.generate_content.side_effect = RuntimeError("Gemini Quota 429")
        mock_gemini_cls.return_value = mock_gemini

        with patch(
            "app.agents.nodes.query_expansion_node.call_groq_structured",
            new_callable=AsyncMock,
        ) as mock_groq_call:
            mock_groq_call.return_value = mock_groq_output

            state = {"user_query": "Reinforcement Learning in Robotics"}
            result = await query_expansion_node(state)

            assert result["target_domains"] == ["cs.AI", "cs.RO"]
            assert len(result["search_queries"]) == 2
            assert result["current_step"] == "query_expansion_completed"
            assert mock_groq_call.await_count == 1


@pytest.mark.asyncio
async def test_screening_node_falls_back_to_groq(monkeypatch):
    """Verify screening_node seamlessly falls back to Groq when Gemini fails."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-gemini-key")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "mock-groq-key")

    decision = PaperScreeningItem(
        paper_id_or_title="Quantum Paper",
        relevance_score=0.92,
        accepted=True,
        reason="Addresses variational quantum algorithms directly",
    )
    mock_screening_output = ScreeningOutput(decisions=[decision])

    with patch("app.agents.nodes.screening_node.genai.Client") as mock_gemini_cls:
        mock_gemini = MagicMock()
        mock_gemini.models.generate_content.side_effect = RuntimeError("Gemini 503")
        mock_gemini_cls.return_value = mock_gemini

        with patch(
            "app.agents.nodes.screening_node.call_groq_structured",
            new_callable=AsyncMock,
        ) as mock_groq_call:
            mock_groq_call.return_value = mock_screening_output

            state = {
                "user_query": "Quantum Computing",
                "discovered_papers": [
                    {
                        "title": "Quantum Paper",
                        "abstract": "A study on variational quantum algorithms.",
                        "pdf_url": "https://arxiv.org/pdf/1234.5678.pdf",
                    }
                ],
            }
            result = await screening_node(state)

            assert len(result["screened_papers"]) == 1
            assert result["screened_papers"][0]["title"] == "Quantum Paper"
            assert result["screened_papers"][0]["relevance_score"] == 0.92
            assert result["current_step"] == "screening_completed"
            assert mock_groq_call.await_count == 1


@pytest.mark.asyncio
async def test_report_synthesis_node_falls_back_to_groq(monkeypatch):
    """Verify report_synthesis_node seamlessly falls back to Groq when Gemini models fail."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-gemini-key")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "mock-groq-key")

    mock_synthesis_output = SynthesizedReviewOutput(
        title="Literature Review on Distributed Machine Learning",
        executive_summary="This synthesis analyzes decentralized optimization methods...",
        thematic_clusters=[],
        methodology_matrix=[],
        research_gaps=["Asynchronous consensus under Byzantine faults"],
        conclusion="Decentralized paradigms exhibit robust scalability.",
        references=[],
    )

    with patch("app.agents.nodes.report_synthesis_node.genai.Client") as mock_gemini_cls:
        mock_gemini = MagicMock()
        mock_gemini.models.generate_content.side_effect = RuntimeError("Gemini Quota Exceeded")
        mock_gemini_cls.return_value = mock_gemini

        with patch(
            "app.agents.nodes.report_synthesis_node.call_groq_structured",
            new_callable=AsyncMock,
        ) as mock_groq_call:
            mock_groq_call.return_value = mock_synthesis_output

            state = {
                "user_query": "Distributed Machine Learning",
                "approved_papers": [
                    {
                        "title": "Paper 1",
                        "abstract": "Abstract of distributed optimization.",
                        "authors": ["Author One"],
                        "year": 2024,
                    }
                ],
                "methodology_matrix": [],
                "research_gaps": [],
                "verified_references": [],
            }
            result = await report_synthesis_node(state)

            assert result["current_step"] == "synthesis_completed"
            assert (
                result["synthesized_review"]["title"]
                == "Literature Review on Distributed Machine Learning"
            )
            assert mock_groq_call.await_count == 1
