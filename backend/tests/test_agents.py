"""Tests for multi-agent LangGraph pipeline (Issue AI-01).

Assignee Task:
- Test that build_literature_review_graph compiles successfully
- Test that all 9 agent nodes exist in the compiled graph
- Test that conditional routing correctly branches on user_decision
"""

from app.agents.orchestrator import (
    build_literature_review_graph,
    route_after_human_interval,
)
from app.agents.state import AgentState


def test_build_literature_review_graph_compilation():
    """Verify that the 9-agent LangGraph pipeline compiles without errors."""
    app = build_literature_review_graph()
    assert app is not None
    assert hasattr(app, "nodes")


def test_graph_contains_all_nine_nodes():
    """Verify that all 9 academic research agents are registered in the graph topology."""
    app = build_literature_review_graph()
    node_names = set(app.nodes.keys())

    expected_nodes = {
        "query_expansion",
        "paper_discovery",
        "screening",
        "human_interrupt",
        "pdf_extraction",
        "vector_embedding",
        "gap_analysis",
        "citation_verification",
        "report_synthesis",
    }

    assert expected_nodes.issubset(node_names)


def test_conditional_routing_find_more():
    """Verify routing loops back to query_expansion when user selects 'find_more'."""
    state: AgentState = {"user_decision": "find_more"}
    next_node = route_after_human_interval(state)
    assert next_node == "query_expansion"


def test_conditional_routing_continue():
    """Verify routing advances to pdf_extraction when user selects 'continue'."""
    state: AgentState = {"user_decision": "continue"}
    next_node = route_after_human_interval(state)
    assert next_node == "pdf_extraction"


def test_conditional_routing_default_fallback():
    """Verify routing defaults safely to 'pdf_extraction' if user_decision is missing."""
    state: AgentState = {}
    next_node = route_after_human_interval(state)
    assert next_node == "pdf_extraction"
