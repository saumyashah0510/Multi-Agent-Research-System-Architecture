"""Unit tests for Agent 07: Methodology Comparison & Gap Analysis Node."""

from unittest.mock import MagicMock, patch

import pytest
from app.agents.nodes.gap_analysis_node import gap_analysis_node
from app.core.config import settings


@pytest.mark.asyncio
async def test_gap_analysis_node_success(monkeypatch):
    """Verify gap_analysis_node generates a structured methodology matrix and research gaps."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-gemini-key")

    mock_response = MagicMock()
    mock_response.text = (
        '{"methodology_matrix": ['
        '  {"method_name": "Variational Quantum Eigensolver (VQE)", '
        '   "papers_used": ["VQE for Oncology Kinase Inhibitors"], '
        '   "strengths": ["Near-term NISQ hardware compatibility", "Chemical precision for ground states"], '
        '   "limitations": ["Susceptible to barren plateaus", "Limited active space qubit scaling"]}'
        "],"
        '"research_gaps": ['
        '  "Lack of validation on non-simulated clinical tissue biopsy datasets.",'
        '  "Absence of standardized quantum noise mitigation protocols across hybrid pipelines."'
        "]}"
    )

    with patch("app.agents.nodes.gap_analysis_node.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client

        state = {
            "user_query": "Quantum Machine Learning in Cancer Drug Discovery",
            "approved_papers": [
                {
                    "title": "VQE for Oncology Kinase Inhibitors",
                    "abstract": "We apply VQE to simulate molecular docking for lung cancer kinase targets.",
                }
            ],
            "extracted_pdf_contents": {
                "VQE for Oncology Kinase Inhibitors": {
                    "methodology": "Mapped molecular Hamiltonian on 16 qubits using Jordan-Wigner transform.",
                    "results": "Achieved 1.4 kcal/mol accuracy in binding free energy.",
                }
            },
        }

        result = await gap_analysis_node(state)

        assert len(result["methodology_matrix"]) == 1
        method = result["methodology_matrix"][0]
        assert method["method_name"] == "Variational Quantum Eigensolver (VQE)"
        assert "VQE for Oncology Kinase Inhibitors" in method["papers_used"]
        assert len(method["strengths"]) == 2
        assert len(method["limitations"]) == 2

        assert len(result["research_gaps"]) == 2
        assert "clinical tissue biopsy" in result["research_gaps"][0]
        assert result["current_step"] == "gap_analysis_completed"


@pytest.mark.asyncio
async def test_gap_analysis_node_empty_papers():
    """Verify clean empty returns when no approved papers or extracted contents exist."""
    state = {
        "user_query": "Quantum Computing",
        "approved_papers": [],
        "extracted_pdf_contents": {},
    }
    result = await gap_analysis_node(state)

    assert result["methodology_matrix"] == []
    assert result["research_gaps"] == []
    assert result["current_step"] == "gap_analysis_completed"


@pytest.mark.asyncio
async def test_gap_analysis_node_missing_api_key_fail_fast(monkeypatch):
    """Verify fail-fast RuntimeError when GEMINI_API_KEY is not configured."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")

    state = {
        "user_query": "Quantum Computing",
        "approved_papers": [{"title": "Paper A", "abstract": "Abstract A"}],
    }

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY is not configured"):
        await gap_analysis_node(state)


@pytest.mark.asyncio
async def test_gap_analysis_node_api_failure_fail_fast(monkeypatch):
    """Verify fail-fast RuntimeError when all Gemini models fail."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-gemini-key")

    with patch("app.agents.nodes.gap_analysis_node.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = RuntimeError("Service Outage")
        mock_client_cls.return_value = mock_client

        state = {
            "user_query": "Quantum Computing",
            "approved_papers": [{"title": "Paper A", "abstract": "Abstract A"}],
        }

        with pytest.raises(RuntimeError, match="Gap analysis failed due to LLM error"):
            await gap_analysis_node(state)


def test_gap_analysis_schema_validation():
    """Verify GapAnalysisOutput schema enforces validation and rejects malformed objects."""
    from app.schemas.agent_outputs import GapAnalysisOutput, MethodologyItem
    from pydantic import ValidationError

    valid_item = MethodologyItem(
        method_name="Graph Neural Networks",
        papers_used=["Paper 1"],
        strengths=["Scalable"],
        limitations=["Memory intensive"],
    )
    output = GapAnalysisOutput(
        methodology_matrix=[valid_item],
        research_gaps=["Gap 1"],
    )
    assert len(output.methodology_matrix) == 1
    assert output.methodology_matrix[0].method_name == "Graph Neural Networks"

    # Missing required field method_name should raise ValidationError
    with pytest.raises(ValidationError):
        MethodologyItem(papers_used=["Paper 1"])
