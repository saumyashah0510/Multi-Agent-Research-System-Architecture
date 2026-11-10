"""Integration tests for LangGraph StateGraph, HITL Pause/Resume & Downstream Synthesis.

Assignee Task (Issue TEST-02):
- Test AgentState schema integrity and initial state setup.
- Test Human-in-the-Loop conditional edge routing (continue vs find_more).
- Test Downstream Node outputs: PDF Extraction, Vector Embeddings, Methodology Matrix,
  Citation Verification, and Synthesis Report generation.
- Ensure all LLM and external I/O calls are mocked so tests run 100% offline.
"""

import json
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock
from app.agents.orchestrator import route_after_human_interval

import pytest

import app.agents.nodes.gap_analysis_node as gap_module
import app.agents.nodes.citation_verifier_node as citation_module
import app.agents.nodes.report_synthesis_node as report_module

from app.agents.state import AgentState

# ==========================================
# 1. State Memory & Initialization Tests
# ==========================================



def test_agent_state_initialization():
    """Verify that AgentState initializes all required pipeline keys."""

    state: AgentState = {
        "review_id": "test-review-001",
        "user_query": "Fault-Tolerant Quantum Error Correction",
        "target_domains": ["Quantum Computing"],
        "search_queries": [],
        "discovered_papers": [],
        "screened_papers": [],
        "approved_papers": [],
        "extracted_pdf_contents": {},
        "chunks_stored_count": 0,
        "methodology_matrix": [],
        "research_gaps": [],
        "verified_references": [],
        "rejected_claims": [],
        "has_hallucinations": False,
        "verification_summary": "",
        "user_decision": "pending",
        "synthesized_review": {},
        "current_step": "START",
    }

    # Verify all 18 required state keys
    expected_keys = {
        "review_id", "user_query", "target_domains", "search_queries",
        "discovered_papers", "screened_papers", "approved_papers",
        "extracted_pdf_contents", "chunks_stored_count",
        "methodology_matrix", "research_gaps", "verified_references",
        "rejected_claims", "has_hallucinations", "verification_summary",
        "user_decision", "synthesized_review", "current_step",
    }

    assert expected_keys.issubset(state.keys())

    # Verify initial data types
    assert isinstance(state["user_query"], str)
    assert isinstance(state["target_domains"], list)
    assert isinstance(state["search_queries"], list)
    assert isinstance(state["discovered_papers"], list)
    assert isinstance(state["screened_papers"], list)
    assert isinstance(state["approved_papers"], list)
    assert isinstance(state["extracted_pdf_contents"], dict)
    assert isinstance(state["chunks_stored_count"], int)
    assert isinstance(state["methodology_matrix"], list)
    assert isinstance(state["research_gaps"], list)
    assert isinstance(state["verified_references"], list)
    assert isinstance(state["rejected_claims"], list)
    assert isinstance(state["has_hallucinations"], bool)
    assert isinstance(state["verification_summary"], str)
    assert isinstance(state["synthesized_review"], dict)
    assert state["user_decision"] == "pending"
    assert state["current_step"] == "START"


# ==========================================
# 2. HITL Conditional Routing Tests (Agent 04)
# ==========================================



# 2. HITL Conditional Routing Tests (Agent 04)

def test_hitl_conditional_routing_approval():
    """Verify routing to PDF extraction when user chooses continue."""

    state_approved: AgentState = {
        "user_decision": "continue",
        "approved_papers": [{"title": "Paper 1"}],
    }

    assert route_after_human_interval(state_approved) == "pdf_extraction"


def test_hitl_conditional_routing_find_more():
    """Verify routing to query expansion when user requests more papers."""

    state_more: AgentState = {
        "user_decision": "find_more",
        "approved_papers": [],
    }

    assert route_after_human_interval(state_more) == "query_expansion"

# ==========================================
# 3. Downstream Node Synthesis & Matrix Tests
# ==========================================

@pytest.mark.asyncio
async def test_methodology_matrix_schema_generation(monkeypatch):
    """Verify Agent 07 produces structured methodology matrix items."""
    # TODO (Assignee - TEST-02):
    mock_response = {
        "methodology_matrix": [
            {
                "method_name": "Surface Code",
                "papers_used": ["Surface Codes for QEC"],
                "strengths": ["Fault-tolerant quantum computation"],
                "limitations": ["High physical qubit overhead"],
            }
        ],
        "research_gaps": ["Reducing physical qubit overhead"],
    }

    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = SimpleNamespace(
        text=json.dumps(mock_response)
    )

    monkeypatch.setattr(
        gap_module,
        "genai",
        SimpleNamespace(Client=MagicMock(return_value=fake_client)),
    )

    monkeypatch.setattr(
        gap_module,
        "settings",
        SimpleNamespace(
            GEMINI_API_KEY="test-key",
            gemini_model_candidates=["test-model"],
        ),
    )

    state: AgentState = {
        "user_query": "Fault-Tolerant Quantum Error Correction",
        "approved_papers": [
            {
                "title": "Surface Codes for QEC",
                "abstract": "A study of quantum error correction.",
            }
        ],
        "extracted_pdf_contents": {},
    }

    result = await gap_module.gap_analysis_node(state)

    assert len(result["methodology_matrix"]) == 1

    row = result["methodology_matrix"][0]

    expected_fields = {
        "method_name",
        "papers_used",
        "strengths",
        "limitations",
    }

    assert expected_fields.issubset(row.keys())
    assert result["research_gaps"] == ["Reducing physical qubit overhead"]
    assert result["current_step"] == "gap_analysis_completed"

    fake_client.models.generate_content.assert_called_once()



@pytest.mark.asyncio
async def test_citation_verification_anti_hallucination(monkeypatch):
    """Verify Agent 08 identifies supported and unsupported claims."""

    mock_response = {
        "verified_citations": [
            {
                "claim": "Surface codes provide fault tolerance.",
                "paper_id_or_title": "Surface Codes for QEC",
                "matched_passage": "Surface codes provide fault-tolerant quantum computation.",
                "is_supported": True,
                "confidence": 0.95,
            },
            {
                "claim": "Surface codes eliminate decoherence at room temperature.",
                "paper_id_or_title": "Surface Codes for QEC",
                "matched_passage": "",
                "is_supported": False,
                "confidence": 0.20,
            },
        ],
        "has_hallucinations": True,
        "verification_summary": "One supported claim and one unsupported claim.",
    }

    # Mock Gemini
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = SimpleNamespace(
        text=json.dumps(mock_response)
    )

    monkeypatch.setattr(
        citation_module,
        "genai",
        SimpleNamespace(Client=MagicMock(return_value=fake_client)),
    )

    monkeypatch.setattr(
        citation_module,
        "settings",
        SimpleNamespace(
            GEMINI_API_KEY="test-key",
            gemini_model_candidates=["test-model"],
        ),
    )

    # Input state for Agent 08
    state: AgentState = {
        "approved_papers": [
            {
                "title": "Surface Codes for QEC",
                "abstract": "Surface codes provide fault-tolerant quantum computation.",
            }
        ],
        "extracted_pdf_contents": {
            "Surface Codes for QEC":
                "Surface codes provide fault-tolerant quantum computation."
        },
        "methodology_matrix": [
            {
                "method_name": "Surface Code",
                "papers_used": ["Surface Codes for QEC"],
                "strengths": ["Fault tolerance"],
                "limitations": ["High physical qubit overhead"],
            }
        ],
        "research_gaps": ["Reducing physical qubit overhead"],
    }

    result = await citation_module.citation_verification_node(state)

    # Verify supported and rejected claims
    assert len(result["verified_references"]) == 1
    assert len(result["rejected_claims"]) == 1
    assert result["has_hallucinations"] is True
    assert result["current_step"] == "citation_verification_completed"

    fake_client.models.generate_content.assert_called_once()




@pytest.mark.asyncio
async def test_report_synthesis_final_structure(monkeypatch):
    """Verify Agent 09 generates a structured literature review."""

    mock_response = {
        "title": "Comprehensive Survey of Fault-Tolerant Quantum Architectures",
        "executive_summary": (
            "This review synthesizes current quantum error correction "
            "methodologies and their limitations."
        ),
        "thematic_clusters": [
            {
                "theme": "Topological and Surface Codes",
                "summary": "Focuses on two-dimensional lattice stabilizers.",
                "citations": ["Surface Codes for QEC"],
            }
        ],
        "methodology_matrix": [
            {
                "method_name": "Surface Code",
                "papers_used": ["Surface Codes for QEC"],
                "strengths": ["Fault tolerance"],
                "limitations": ["High physical qubit overhead"],
            }
        ],
        "research_gaps": [
            "Reducing physical qubit overhead."
        ],
        "conclusion": "Further research is needed to improve scalability.",
        "references": [],
    }

    # Mock Gemini
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = SimpleNamespace(
        text=json.dumps(mock_response)
    )

    monkeypatch.setattr(
        report_module,
        "genai",
        SimpleNamespace(Client=MagicMock(return_value=fake_client)),
    )

    monkeypatch.setattr(
        report_module,
        "settings",
        SimpleNamespace(
            GEMINI_API_KEY="test-key",
            gemini_model_candidates=["test-model"],
        ),
    )

    # Prepare input state
    state: AgentState = {
        "user_query": "Fault-Tolerant Quantum Error Correction",
        "approved_papers": [
            {
                "title": "Surface Codes for QEC",
                "authors": ["John Smith"],
                "year": 2024,
                "abstract": "A study of quantum error correction.",
            }
        ],
        "methodology_matrix": [
            {
                "method_name": "Surface Code",
                "papers_used": ["Surface Codes for QEC"],
                "strengths": ["Fault tolerance"],
                "limitations": ["High physical qubit overhead"],
            }
        ],
        "research_gaps": ["Reducing physical qubit overhead."],
        "verified_references": [],
        "extracted_pdf_contents": {},
        "rejected_claims": [],
        "has_hallucinations": False,
        "verification_summary": "",
    }

    result = await report_module.report_synthesis_node(state)

    # Verify synthesized report structure
    review = result["synthesized_review"]

    assert "title" in review
    assert "executive_summary" in review
    assert len(review["thematic_clusters"]) > 0
    assert len(review["methodology_matrix"]) > 0
    assert len(review["research_gaps"]) > 0
    assert "conclusion" in review
    assert "references" in review
    assert result["current_step"] == "synthesis_completed"

    # Ensure mocked Gemini was called
    fake_client.models.generate_content.assert_called_once()
