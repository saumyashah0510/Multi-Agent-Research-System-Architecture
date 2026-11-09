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


def test_reference_item_bibliographic_metadata_and_markdown():
    """Verify ReferenceItem handles authors, year, url, and matched_passage."""
    from app.schemas.agent_outputs import ReferenceItem

    ref = ReferenceItem(
        title="Attention Is All You Need",
        citation_key="Vaswani et al., 2017",
        authors=["Ashish Vaswani", "Noam Shazeer"],
        year=2017,
        url="https://arxiv.org/abs/1706.03762",
        matched_passage="The dominant sequence transduction models are based on complex recurrent or convolutional neural networks.",
        summary="Foundational transformer architecture paper.",
    )

    assert ref.title == "Attention Is All You Need"
    assert ref.year == 2017
    assert len(ref.authors) == 2
    assert "arxiv.org" in ref.url

    review_dict = {
        "title": "Transformer Survey",
        "executive_summary": "Transformers have reshaped deep learning.",
        "references": [ref.model_dump()],
    }

    md = format_review_as_markdown(review_dict)
    assert "**Attention Is All You Need**" in md
    assert "by Ashish Vaswani, Noam Shazeer" in md
    assert "(2017)" in md
    assert "`[Vaswani et al., 2017]`" in md
    assert "<https://arxiv.org/abs/1706.03762>" in md
    assert "Foundational transformer architecture paper." in md
    # Assert grounding quote is rendered even when summary exists (CodeRabbit Item 1)
    assert "The dominant sequence transduction models" in md


def test_markdown_citation_key_preserves_single_brackets():
    """Verify citation keys with or without brackets render cleanly as `[Key]` (no double brackets)."""
    ref_with_brackets = {
        "title": "Paper One",
        "citation_key": "[Vaswani et al., 2017]",
    }
    ref_without_brackets = {
        "title": "Paper Two",
        "citation_key": "Chase et al., 2024",
    }
    review = {"references": [ref_with_brackets, ref_without_brackets]}
    md = format_review_as_markdown(review)

    assert "`[Vaswani et al., 2017]`" in md
    assert "`[[Vaswani et al., 2017]]`" not in md
    assert "`[Chase et al., 2024]`" in md
    assert "`[[Chase et al., 2024]]`" not in md


def test_sanitize_references_drops_hallucinated_quotes_and_preserves_grounded():
    """Verify _sanitize_references drops ungrounded quotes, preserves verified quotes, and backfills."""
    from app.agents.nodes.report_synthesis_node import _sanitize_references
    from app.schemas.agent_outputs import ReferenceItem

    verified_refs = [
        {
            "paper_id_or_title": "Attention Is All You Need",
            "claim": "Transformers replace recurrence",
            "matched_passage": "The dominant sequence transduction models are based on complex recurrent networks.",
        },
        {
            "paper_id_or_title": "Paraphrased Paper",
            "claim": "Paraphrase claim",
            "matched_passage": "Supported paraphrase summary but not verbatim text in source.",
        },
    ]

    approved = [
        {
            "title": "Attention Is All You Need",
            "arxiv_id": "2301.12345",
            "abstract": "The dominant sequence transduction models are based on complex recurrent networks. We propose the Transformer.",
        },
        {
            "title": "Paraphrased Paper",
            "abstract": "Completely different words in abstract.",
        },
    ]

    extracted_pdf = {
        "2301.12345": {
            "results": "Empirical accuracy improved by 14.2% on WMT 2014 English-to-German.",
            "methodology": "Scaled dot-product attention compute Q, K, V dot products.",
        }
    }

    # Ref 1: grounded passage from verified_references
    ref1 = ReferenceItem(
        title="Attention Is All You Need",
        citation_key="Vaswani et al., 2017",
        matched_passage="The dominant sequence transduction models are based on complex recurrent networks.",
    )

    # Ref 2: hallucinated quote not present in verified citations, abstracts, or results
    ref2 = ReferenceItem(
        title="Fabricated Paper",
        citation_key="Unknown, 2025",
        matched_passage="This is a completely fabricated quotation never written in any paper.",
    )

    # Ref 3: empty quote, backfills from verified_refs because it verbatim matches source text
    ref3 = ReferenceItem(
        title="Attention Is All You Need",
        citation_key="Vaswani et al., 2017",
        matched_passage="",
    )

    # Ref 4: quote from extracted_pdf_contents["results"] (Comment 1 test)
    ref4 = ReferenceItem(
        title="Attention Is All You Need",
        citation_key="Vaswani et al., 2017",
        matched_passage="Empirical accuracy improved by 14.2% on WMT 2014 English-to-German.",
    )

    # Ref 5: quote with verified passage prefix plus hallucinated extension (Comment 2 test)
    ref5 = ReferenceItem(
        title="Attention Is All You Need",
        citation_key="Vaswani et al., 2017",
        matched_passage="The dominant sequence transduction models are based on complex recurrent networks. AND THIS PART IS HALLUCINATED NONSENSE.",
    )

    # Ref 6: empty quote for Paraphrased Paper (Comment 3 test - paraphrase should NOT be backfilled)
    ref6 = ReferenceItem(
        title="Paraphrased Paper",
        citation_key="Paraphrase, 2024",
        matched_passage="",
    )

    sanitized = _sanitize_references(
        references=[ref1, ref2, ref3, ref4, ref5, ref6],
        verified_references=verified_refs,
        approved_papers=approved,
        extracted_pdf_contents=extracted_pdf,
    )

    # Ref 1 kept
    assert sanitized[0]["matched_passage"] == ref1.matched_passage
    # Ref 2 hallucinated quote safely dropped
    assert sanitized[1]["matched_passage"] == ""
    # Ref 3 backfilled from verified citation
    assert sanitized[2]["matched_passage"] == verified_refs[0]["matched_passage"]
    # Ref 4 results quote preserved
    assert sanitized[3]["matched_passage"] == ref4.matched_passage
    # Ref 5 hallucinated extension trimmed to verified passage
    assert sanitized[4]["matched_passage"] == verified_refs[0]["matched_passage"]
    # Ref 6 paraphrase not backfilled because it is not verbatim in source
    assert sanitized[5]["matched_passage"] == ""


def test_whitespace_normalization_and_paper_scoped_trimming():
    """Verify whitespace normalization handles PDF line wraps and trimming respects cited paper."""
    from app.agents.nodes.report_synthesis_node import _sanitize_references
    from app.schemas.agent_outputs import ReferenceItem

    verified_refs = [
        {
            "paper_id_or_title": "Paper A",
            "matched_passage": "Paper A verified excerpt.",
        },
        {
            "paper_id_or_title": "Paper B",
            "matched_passage": "Paper B verified excerpt.",
        },
    ]

    approved = [
        {
            "title": "Paper A",
            # Source text has hard newline breaks from PDF extraction
            "abstract": "The dominant sequence\ntransduction models are based\non complex recurrence.",
        },
        {
            "title": "Paper B",
            "abstract": "Deep learning architectures for vision.",
        },
    ]

    # Ref A: LLM quoted without newlines (spaces only) -> matches via whitespace normalization
    ref_a = ReferenceItem(
        title="Paper A",
        citation_key="Paper A, 2024",
        matched_passage="The dominant sequence transduction models are based on complex recurrence.",
    )

    # Ref B: contains Paper A's quote but belongs to Paper B -> must NOT trim to Paper A's passage!
    ref_b = ReferenceItem(
        title="Paper B",
        citation_key="Paper B, 2024",
        matched_passage="Paper A verified excerpt plus hallucination.",
    )

    sanitized = _sanitize_references(
        references=[ref_a, ref_b],
        verified_references=verified_refs,
        approved_papers=approved,
        extracted_pdf_contents={},
    )

    # Ref A preserved through whitespace normalization despite source hard line breaks
    assert sanitized[0]["matched_passage"] == ref_a.matched_passage
    # Ref B dropped rather than incorrectly assigned Paper A's quote
    assert sanitized[1]["matched_passage"] == ""


def test_cross_paper_quote_cleared_when_cited_by_different_paper():
    """Verify that when Paper B cites an exact quote found only in Paper A, it is cleared."""
    from app.agents.nodes.report_synthesis_node import _sanitize_references
    from app.schemas.agent_outputs import ReferenceItem

    approved = [
        {
            "title": "Paper A",
            "abstract": "Exact unique quote belonging strictly to Paper A.",
        },
        {
            "title": "Paper B",
            "abstract": "Different content belonging to Paper B.",
        },
    ]

    # Reference is for Paper B, but quotes text found only in Paper A
    ref_b = ReferenceItem(
        title="Paper B",
        citation_key="Paper B, 2024",
        matched_passage="Exact unique quote belonging strictly to Paper A.",
    )

    sanitized = _sanitize_references(
        references=[ref_b],
        verified_references=[],
        approved_papers=approved,
        extracted_pdf_contents={},
    )

    # Scoped grounding must clear the quote because Paper B's source does not contain it
    assert sanitized[0]["matched_passage"] == ""
