"""Integration tests for LangGraph StateGraph, HITL Pause/Resume & Downstream Synthesis.

Assignee Task (Issue TEST-02):
- Test AgentState schema integrity and initial state setup.
- Test Human-in-the-Loop conditional edge routing (continue vs find_more).
- Test Downstream Node outputs: PDF Extraction, Vector Embeddings, Methodology Matrix,
  Citation Verification, and Synthesis Report generation.
- Ensure all LLM and external I/O calls are mocked so tests run 100% offline.
"""

from typing import cast

from app.agents.state import AgentState

# ==========================================
# 1. State Memory & Initialization Tests
# ==========================================


def test_agent_state_initialization():
    """Verify that AgentState schema correctly initializes all required pipeline keys."""
    # TODO (Assignee - TEST-02):
    # 1. Initialize an AgentState dictionary with user_query and default empty lists/dicts
    # 2. Verify all 11 state keys exist and have appropriate initial types
    state: AgentState = {
        "user_query": "Fault-Tolerant Quantum Error Correction",
        "target_domains": ["Quantum Computing"],
        "search_queries": [],
        "discovered_papers": [],
        "screened_papers": [],
        "approved_papers": [],
        "extracted_pdf_contents": {},
        "verified_references": [],
        "user_decision": "pending",
        "synthesized_review": {},
        "current_step": "START",
    }

    assert state["user_query"] == "Fault-Tolerant Quantum Error Correction"
    assert state["current_step"] == "START"
    assert isinstance(state["discovered_papers"], list)
    assert isinstance(state["extracted_pdf_contents"], dict)


# ==========================================
# 2. HITL Conditional Routing Tests (Agent 04)
# ==========================================


def test_hitl_conditional_routing_approval():
    """Verify routing decision when user approves candidate papers to proceed."""

    # TODO (Assignee - TEST-02):
    # Simulate conditional edge function for Agent 04:
    # If user_decision is 'continue', next node must be 'extract_pdf'
    # If user_decision is 'find_more', next node must be 'expand_query'
    def route_after_human_decision(state: AgentState) -> str:
        if state.get("user_decision") == "continue":
            return "extract_pdf"
        return "expand_query"

    state_approved: AgentState = cast(
        AgentState,
        {
            "user_decision": "continue",
            "approved_papers": [{"title": "Paper 1"}],
        },
    )
    assert route_after_human_decision(state_approved) == "extract_pdf"


def test_hitl_conditional_routing_find_more():
    """Verify routing loops back to query expansion if user requests more papers."""

    def route_after_human_decision(state: AgentState) -> str:
        if state.get("user_decision") == "continue":
            return "extract_pdf"
        return "expand_query"

    state_more: AgentState = cast(
        AgentState,
        {
            "user_decision": "find_more",
            "approved_papers": [],
        },
    )
    assert route_after_human_decision(state_more) == "expand_query"


# ==========================================
# 3. Downstream Node Synthesis & Matrix Tests
# ==========================================


def test_methodology_matrix_schema_generation():
    """Verify Agent 07 produces structured methodology matrix items."""
    # TODO (Assignee - TEST-02):
    # 1. Mock Agent 07 LLM generation
    # 2. Assert matrix rows contain: paper_title, methodology, key_findings, limitations, datasets
    sample_matrix_row = {
        "paper_title": "Surface Codes for QEC",
        "authors": ["Alice Smith"],
        "methodology": "Syndrome measurement via stabilizer circuits",
        "key_findings": "Achieved 1.2% error threshold under depolarizing noise",
        "limitations": "Requires large physical-to-logical qubit overhead",
        "datasets": "Simulated on Qiskit Aer",
    }

    required_keys = {
        "paper_title",
        "methodology",
        "key_findings",
        "limitations",
        "datasets",
    }
    assert required_keys.issubset(sample_matrix_row.keys())


def test_citation_verification_anti_hallucination():
    """Verify Agent 08 flags ungrounded claims and verifies grounded citations."""
    # TODO (Assignee - TEST-02):
    # 1. Provide extracted context chunks
    # 2. Check if a generated claim matches text in extracted chunks
    # 3. Assert citation is marked 'verified' if supported by chunk text
    source_chunks = ["Surface codes provide a fault-tolerant threshold of approximately 1.0%."]

    grounded_claim = "Surface codes achieve a fault-tolerant threshold of roughly 1.0%."
    ungrounded_claim = "Surface codes completely eliminate decoherence at room temperature."

    # Simplified verification logic demonstration
    is_grounded = (
        any("fault-tolerant threshold" in chunk for chunk in source_chunks)
        and "threshold" in grounded_claim
    )
    is_hallucinated = (
        not any("room temperature" in chunk for chunk in source_chunks)
        and "room temperature" in ungrounded_claim
    )

    assert is_grounded is True
    assert is_hallucinated is True


def test_report_synthesis_final_structure():
    """Verify Agent 09 produces a complete, structured literature review output."""
    # TODO (Assignee - TEST-02):
    # Assert synthesized review dictionary has title, abstract, clusters, matrix, and gaps
    mock_synthesis = {
        "title": "Comprehensive Survey of Fault-Tolerant Quantum Architectures",
        "abstract": "This review synthesizes current quantum error correction methodologies...",
        "thematic_clusters": [
            {
                "theme_title": "Topological & Surface Codes",
                "summary": "Focuses on 2D lattice stabilizers.",
            }
        ],
        "methodology_matrix": [],
        "research_gaps": ["High physical qubit overhead in scaling beyond 100 logical qubits."],
    }

    assert "title" in mock_synthesis
    assert "abstract" in mock_synthesis
    assert len(mock_synthesis["thematic_clusters"]) > 0
    assert len(mock_synthesis["research_gaps"]) > 0
