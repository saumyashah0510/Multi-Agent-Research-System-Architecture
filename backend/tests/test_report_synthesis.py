"""Unit tests for Agent 09: Structured Synthesis Report Generation Node."""

import json
from unittest.mock import MagicMock, patch

import pytest
from app.agents.nodes.report_synthesis_node import (
    format_review_as_markdown,
    report_synthesis_node,
)
from app.core.config import settings
from app.schemas.agent_outputs import SynthesizedReviewOutput, ThematicClusterItem
from pydantic import ValidationError


@pytest.mark.asyncio
async def test_report_synthesis_node_success(monkeypatch):
    """Verify that report_synthesis_node generates a complete structured academic review."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-gemini-key")

    mock_review_json = json.dumps(
        {
            "title": "Quantum Machine Learning in Cancer Drug Discovery: A Comprehensive Synthesis",
            "executive_summary": (
                "This synthesis analyzes hybrid variational quantum eigensolvers applied to oncology drug discovery. "
                "Across the examined corpus, parameterized quantum circuits show convergence within chemical accuracy "
                "for kinase targets, though scalability is constrained by barren plateau phenomena."
            ),
            "thematic_clusters": [
                {
                    "theme": "Hybrid Quantum-Classical Optimization",
                    "summary": (
                        "VQE approaches map molecular Hamiltonians to qubits, optimizing ground-state energies "
                        "on simulated quantum hardware while delegating parameter updates to classical optimizers."
                    ),
                    "citations": ["VQE for Oncology Kinase Inhibitors"],
                }
            ],
            "methodology_matrix": [
                {
                    "method_name": "Variational Quantum Eigensolver (VQE)",
                    "papers_used": ["VQE for Oncology Kinase Inhibitors"],
                    "strengths": ["Achieved 1.4 kcal/mol chemical accuracy"],
                    "limitations": ["Optimization decay beyond 18 qubits"],
                }
            ],
            "research_gaps": [
                "Absence of fault-tolerant error correction benchmarking for complex multi-ligand binding.",
                "Lack of in vivo biological validation for computational quantum predictions.",
            ],
            "conclusion": (
                "Quantum machine learning demonstrates strong algorithmic viability for molecular modeling, "
                "but practical oncology translation requires fault-tolerant hardware and experimental co-design."
            ),
            "references": [
                {
                    "title": "VQE for Oncology Kinase Inhibitors",
                    "claim": "VQE achieves 1.4 kcal/mol chemical accuracy",
                    "matched_passage": "Achieved ground-state energy convergence within 1.4 kcal/mol.",
                }
            ],
        }
    )

    mock_response = MagicMock()
    mock_response.text = mock_review_json

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    state = {
        "user_query": "Quantum Machine Learning in Cancer Drug Discovery",
        "approved_papers": [
            {
                "title": "VQE for Oncology Kinase Inhibitors",
                "abstract": "We evaluate hybrid variational quantum eigensolvers for EGFR kinase docking.",
            }
        ],
        "methodology_matrix": [
            {
                "method_name": "Variational Quantum Eigensolver (VQE)",
                "papers_used": ["VQE for Oncology Kinase Inhibitors"],
                "strengths": ["Achieved 1.4 kcal/mol chemical accuracy"],
                "limitations": ["Optimization decay beyond 18 qubits"],
            }
        ],
        "research_gaps": [
            "Absence of fault-tolerant error correction benchmarking for complex multi-ligand binding."
        ],
        "verified_references": [
            {
                "claim": "VQE achieves 1.4 kcal/mol chemical accuracy",
                "paper_id_or_title": "VQE for Oncology Kinase Inhibitors",
                "matched_passage": "Achieved ground-state energy convergence within 1.4 kcal/mol.",
                "is_supported": True,
                "confidence": 0.98,
            }
        ],
        "extracted_pdf_contents": {
            "VQE for Oncology Kinase Inhibitors": {
                "abstract": "We evaluate hybrid variational quantum eigensolvers...",
                "methodology": "The Hamiltonian was mapped using Jordan-Wigner transform...",
                "results": "Achieved ground-state energy convergence within 1.4 kcal/mol.",
            }
        },
    }

    with patch("google.genai.Client", return_value=mock_client):
        result = await report_synthesis_node(state)

    assert result["current_step"] == "synthesis_completed"
    synthesis = result["synthesized_review"]

    assert (
        synthesis["title"]
        == "Quantum Machine Learning in Cancer Drug Discovery: A Comprehensive Synthesis"
    )
    assert "variational quantum eigensolvers" in synthesis["executive_summary"]
    assert len(synthesis["thematic_clusters"]) == 1
    assert synthesis["thematic_clusters"][0]["theme"] == "Hybrid Quantum-Classical Optimization"
    assert len(synthesis["methodology_matrix"]) == 1
    assert len(synthesis["research_gaps"]) == 2
    assert "fault-tolerant" in synthesis["conclusion"]
    assert len(synthesis["references"]) == 1


@pytest.mark.asyncio
async def test_report_synthesis_node_empty_state_fallback():
    """Verify that empty inputs gracefully return a valid structured placeholder review."""
    empty_state = {
        "user_query": "Unexplored Topic",
        "approved_papers": [],
        "methodology_matrix": [],
        "research_gaps": [],
    }

    result = await report_synthesis_node(empty_state)

    assert result["current_step"] == "synthesis_completed"
    synthesis = result["synthesized_review"]
    assert synthesis["title"] == "Literature Review: Unexplored Topic"
    assert "Insufficient paper data" in synthesis["executive_summary"]
    assert synthesis["thematic_clusters"] == []
    assert synthesis["methodology_matrix"] == []
    assert synthesis["research_gaps"] == []


@pytest.mark.asyncio
async def test_report_synthesis_node_missing_api_key_fail_fast(monkeypatch):
    """Verify fail-fast behavior when GEMINI_API_KEY is unset."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")

    state = {
        "user_query": "Deep Learning Review",
        "approved_papers": [{"title": "Paper A", "abstract": "Abstract A"}],
    }

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY is not configured"):
        await report_synthesis_node(state)


@pytest.mark.asyncio
async def test_report_synthesis_node_api_failure_fail_fast(monkeypatch):
    """Verify fail-fast behavior when all candidate Gemini models fail."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-gemini-key")

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("503 Service Unavailable")

    state = {
        "user_query": "Edge Computing",
        "approved_papers": [{"title": "Edge Paper", "abstract": "Abstract"}],
    }

    with patch("google.genai.Client", return_value=mock_client):
        with pytest.raises(RuntimeError, match="Report synthesis failed due to LLM error"):
            await report_synthesis_node(state)


def test_report_synthesis_schema_validation():
    """Verify Pydantic schema validation for SynthesizedReviewOutput."""
    # Valid schema test
    output = SynthesizedReviewOutput(
        title="Modern Federated Learning",
        executive_summary="Federated learning enables decentralized training.",
        thematic_clusters=[
            ThematicClusterItem(
                theme="Privacy Enhancements",
                summary="Differential privacy bounds information leakage.",
                citations=["Paper A"],
            )
        ],
        research_gaps=["Communication overhead under non-IID data"],
        conclusion="Privacy-preserving ML is advancing rapidly.",
    )
    assert output.title == "Modern Federated Learning"
    assert len(output.thematic_clusters) == 1

    # Missing mandatory title must raise ValidationError
    with pytest.raises(ValidationError):
        SynthesizedReviewOutput(
            executive_summary="Missing title should fail.",
        )


def test_format_review_as_markdown():
    """Verify that format_review_as_markdown produces clean GitHub-flavored Markdown."""
    review_dict = {
        "title": "Quantum ML in Oncology",
        "executive_summary": "Comprehensive overview of quantum computing in drug discovery.",
        "thematic_clusters": [
            {
                "theme": "Variational Algorithms",
                "summary": "VQE evaluates molecular ground states.",
                "citations": ["Paper 1", "Paper 2"],
            }
        ],
        "methodology_matrix": [
            {
                "method_name": "VQE | PQC Hybrid",
                "papers_used": ["Paper 1"],
                "strengths": ["Accurate"],
                "limitations": ["Barren plateaus | Scaling overhead"],
            }
        ],
        "research_gaps": ["Error correction", "Scalability"],
        "conclusion": "Quantum ML represents a promising frontier.",
        "references": [
            {
                "title": "Paper 1",
                "claim": "VQE is accurate",
                "matched_passage": "Within 1.4 kcal/mol",
            }
        ],
    }

    md_output = format_review_as_markdown(review_dict)

    assert "# Quantum ML in Oncology" in md_output
    assert "## Executive Summary" in md_output
    assert "## Thematic Clusters & Comparative Analysis" in md_output
    assert "### 1. Variational Algorithms" in md_output
    assert "## Comparative Methodology Matrix" in md_output
    assert (
        "| **VQE \\| PQC Hybrid** | Paper 1 | Accurate | Barren plateaus \\| Scaling overhead |"
        in md_output
    )
    assert "## Unresolved Research Gaps & Open Challenges" in md_output
    assert "1. Error correction" in md_output
    assert "## Conclusion & Future Directions" in md_output
    assert "## References & Bibliography" in md_output
