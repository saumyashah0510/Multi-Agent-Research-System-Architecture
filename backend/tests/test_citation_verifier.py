"""Unit tests for Agent 08: Anti-Hallucination Citation Verifier Node."""

from unittest.mock import MagicMock, patch

import pytest
from app.agents.nodes.citation_verifier_node import citation_verification_node
from app.core.config import settings
from app.schemas.agent_outputs import CitationVerificationOutput, VerifiedCitationItem
from pydantic import ValidationError


@pytest.mark.asyncio
async def test_citation_verification_supported_claim(monkeypatch):
    """Verify factual claims backed by paper text are validated and retained in verified_references."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-gemini-key")

    mock_response = MagicMock()
    mock_response.text = (
        '{"verified_citations": ['
        '  {"claim": "VQE achieves 1.4 kcal/mol chemical accuracy on kinase targets.", '
        '   "paper_id_or_title": "VQE for Oncology Kinase Inhibitors", '
        '   "matched_passage": "Achieved ground-state energy convergence within 1.4 kcal/mol (chemical accuracy).", '
        '   "is_supported": true, '
        '   "confidence": 0.98}'
        "],"
        '"has_hallucinations": false,'
        '"verification_summary": "All assertions are strongly supported by extracted methodology excerpts."}'
    )

    with patch("app.agents.nodes.citation_verifier_node.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client

        state = {
            "methodology_matrix": [
                {
                    "method_name": "Variational Quantum Eigensolver (VQE)",
                    "papers_used": ["VQE for Oncology Kinase Inhibitors"],
                    "strengths": ["Ground-state energy convergence within 1.4 kcal/mol"],
                    "limitations": ["Barren plateau scaling"],
                }
            ],
            "extracted_pdf_contents": {
                "VQE for Oncology Kinase Inhibitors": {
                    "results": "Achieved ground-state energy convergence within 1.4 kcal/mol (chemical accuracy)."
                }
            },
        }

        result = await citation_verification_node(state)

        assert len(result["verified_references"]) == 1
        ref = result["verified_references"][0]
        assert ref["is_supported"] is True
        assert ref["confidence"] == 0.98
        assert "1.4 kcal/mol" in ref["matched_passage"]
        assert result["current_step"] == "citation_verification_completed"


@pytest.mark.asyncio
async def test_citation_verification_hallucinated_claim_flagged(monkeypatch):
    """Verify hallucinated/unsupported claims are filtered out of verified_references."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-gemini-key")

    mock_response = MagicMock()
    mock_response.text = (
        '{"verified_citations": ['
        '  {"claim": "VQE cured 99% of lung cancer tumors in clinical mouse models.", '
        '   "paper_id_or_title": "VQE for Oncology Kinase Inhibitors", '
        '   "matched_passage": "No supporting evidence found in source text.", '
        '   "is_supported": false, '
        '   "confidence": 0.15}'
        "],"
        '"has_hallucinations": true,'
        '"verification_summary": "Detected hallucinated biological efficacy claim not present in in-silico study."}'
    )

    with patch("app.agents.nodes.citation_verifier_node.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client

        state = {
            "methodology_matrix": [
                {
                    "method_name": "Variational Quantum Eigensolver (VQE)",
                    "papers_used": ["VQE for Oncology Kinase Inhibitors"],
                    "strengths": ["Cured 99% of lung cancer tumors in vivo"],
                }
            ],
            "extracted_pdf_contents": {
                "VQE for Oncology Kinase Inhibitors": {
                    "results": "Simulation was purely computational on simulated quantum hardware."
                }
            },
        }

        result = await citation_verification_node(state)

        # Hallucinated assertion must be excluded from verified_references
        assert len(result["verified_references"]) == 0
        assert result["current_step"] == "citation_verification_completed"


@pytest.mark.asyncio
async def test_citation_verification_empty_state_fallback():
    """Verify clean empty return when no methodology matrix or research gaps exist."""
    state = {
        "methodology_matrix": [],
        "research_gaps": [],
        "extracted_pdf_contents": {},
    }
    result = await citation_verification_node(state)

    assert result["verified_references"] == []
    assert result["current_step"] == "citation_verification_completed"


@pytest.mark.asyncio
async def test_citation_verification_missing_api_key_fail_fast(monkeypatch):
    """Verify fail-fast RuntimeError when GEMINI_API_KEY is not configured."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")

    state = {
        "methodology_matrix": [
            {
                "method_name": "VQE",
                "papers_used": ["Paper A"],
                "strengths": ["Fast"],
            }
        ],
        "extracted_pdf_contents": {"Paper A": {"results": "Fast results"}},
    }

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY is not configured"):
        await citation_verification_node(state)


@pytest.mark.asyncio
async def test_citation_verification_api_failure_fail_fast(monkeypatch):
    """Verify fail-fast RuntimeError when Gemini API throws an exception."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-gemini-key")

    with patch("app.agents.nodes.citation_verifier_node.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = RuntimeError("API Gateway 503")
        mock_client_cls.return_value = mock_client

        state = {
            "methodology_matrix": [
                {
                    "method_name": "VQE",
                    "papers_used": ["Paper A"],
                    "strengths": ["Fast"],
                }
            ],
            "extracted_pdf_contents": {"Paper A": {"results": "Fast results"}},
        }

        with pytest.raises(RuntimeError, match="Citation verification failed due to LLM error"):
            await citation_verification_node(state)


def test_citation_verification_schema_validation():
    """Verify CitationVerificationOutput and VerifiedCitationItem validate types and reject invalid schemas."""
    item = VerifiedCitationItem(
        claim="Tested on CCLE",
        paper_id_or_title="QCNN Paper",
        matched_passage="Dataset: CCLE benchmark",
        is_supported=True,
        confidence=0.95,
    )
    output = CitationVerificationOutput(
        verified_citations=[item],
        has_hallucinations=False,
        verification_summary="Factual",
    )
    assert len(output.verified_citations) == 1
    assert output.verified_citations[0].is_supported is True

    # Missing required field 'claim' must raise ValidationError
    with pytest.raises(ValidationError):
        VerifiedCitationItem(paper_id_or_title="Paper", is_supported=True)
