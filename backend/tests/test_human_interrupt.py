"""Unit tests for Agent 04: Human Approval Interrupt Node."""

from app.agents.nodes.human_interrupt_node import human_interrupt_node
from app.agents.orchestrator import route_after_human_interval
from app.agents.state import AgentState
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

SCREENED_PAPERS = [
    {
        "arxiv_id": "2301.0001",
        "title": "Paper One",
        "abstract": "Abstract one.",
        "relevance_score": 0.9,
    },
    {
        "arxiv_id": "2301.0002",
        "title": "Paper Two",
        "abstract": "Abstract two.",
        "relevance_score": 0.8,
    },
    {
        "arxiv_id": "2301.0003",
        "title": "Paper Three",
        "abstract": "Abstract three.",
        "relevance_score": 0.7,
    },
]


def _build_graph():
    """Tiny graph with only the interrupt node, so we can test pause/resume."""
    workflow = StateGraph(AgentState)
    workflow.add_node("human_interrupt", human_interrupt_node)
    workflow.add_edge(START, "human_interrupt")
    workflow.add_edge("human_interrupt", END)
    return workflow.compile(checkpointer=MemorySaver())


def _run_until_pause(graph, thread_id):
    config = {"configurable": {"thread_id": thread_id}}
    graph.invoke({"screened_papers": SCREENED_PAPERS}, config=config)
    return config


def test_human_interrupt_preserves_candidate_papers():
    """The graph pauses and exposes all candidate papers for user selection."""
    graph = _build_graph()
    config = _run_until_pause(graph, "test-pause")

    snapshot = graph.get_state(config)
    assert snapshot.next == ("human_interrupt",)

    payload = snapshot.tasks[0].interrupts[0].value
    candidates = payload["candidate_papers"]
    assert len(candidates) == 3
    assert candidates[0]["title"] == "Paper One"
    assert candidates[0]["abstract"] == "Abstract one."
    assert candidates[0]["relevance_score"] == 0.9


def test_resume_continue_populates_approved_papers():
    """Resuming with 'continue' keeps only the papers the user selected."""
    graph = _build_graph()
    config = _run_until_pause(graph, "test-continue")

    result = graph.invoke(
        Command(
            resume={
                "user_decision": "continue",
                "approved_paper_ids": ["2301.0001", "2301.0003"],
            }
        ),
        config=config,
    )

    assert [p["arxiv_id"] for p in result["approved_papers"]] == ["2301.0001", "2301.0003"]
    assert result["user_decision"] == "continue"
    assert result["current_step"] == "human_approval_completed"
    assert route_after_human_interval(result) == "pdf_extraction"


def test_resume_find_more_sets_loop_back_state():
    """Resuming with 'find_more' approves nothing and routes back to query expansion."""
    graph = _build_graph()
    config = _run_until_pause(graph, "test-find-more")

    result = graph.invoke(
        Command(resume={"user_decision": "find_more", "approved_paper_ids": []}),
        config=config,
    )

    assert result["approved_papers"] == []
    assert result["user_decision"] == "find_more"
    assert route_after_human_interval(result) == "query_expansion"
