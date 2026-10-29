"""LangGraph pipeline graph orchestrator definition."""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.agents.nodes.citation_verifier_node import citation_verification_node
from app.agents.nodes.discovery_node import discovery_node
from app.agents.nodes.gap_analysis_node import gap_analysis_node
from app.agents.nodes.human_interrupt_node import human_interrupt_node
from app.agents.nodes.pdf_extractor_node import pdf_extractor_node
from app.agents.nodes.query_expansion_node import query_expansion_node
from app.agents.nodes.report_synthesis_node import report_synthesis_node
from app.agents.nodes.screening_node import screening_node
from app.agents.nodes.vector_embedding_node import vector_embedding_node
from app.agents.state import AgentState


def route_after_human_interval(state: AgentState) -> str:
    """Evaluate human-in-the-loop approval decision.

    If user clicked 'find_more', route back to query expansion.
    Otherwise ('continue'), proceed to deep PDF extraction.
    """

    decision = state.get("user_decision", "continue")
    if decision == "find_more":
        return "query_expansion"

    return "pdf_extraction"


def build_literature_review_graph():
    """Construct and compile the 9-Agent execution StateGraph."""
    workflow = StateGraph(AgentState)

    workflow.add_node("query_expansion", query_expansion_node)
    workflow.add_node("paper_discovery", discovery_node)
    workflow.add_node("screening", screening_node)
    workflow.add_node("human_interrupt", human_interrupt_node)
    workflow.add_node("pdf_extraction", pdf_extractor_node)
    workflow.add_node("vector_embedding", vector_embedding_node)
    workflow.add_node("gap_analysis", gap_analysis_node)
    workflow.add_node("citation_verification", citation_verification_node)
    workflow.add_node("report_synthesis", report_synthesis_node)

    workflow.set_entry_point("query_expansion")

    workflow.add_edge("query_expansion", "paper_discovery")
    workflow.add_edge("paper_discovery", "screening")
    workflow.add_edge("screening", "human_interrupt")

    workflow.add_conditional_edges(
        "human_interrupt",
        route_after_human_interval,
        {"query_expansion": "query_expansion", "pdf_extraction": "pdf_extraction"},
    )

    workflow.add_edge("pdf_extraction", "vector_embedding")
    workflow.add_edge("vector_embedding", "gap_analysis")
    workflow.add_edge("gap_analysis", "citation_verification")
    workflow.add_edge("citation_verification", "report_synthesis")
    workflow.add_edge("report_synthesis", END)

    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)
