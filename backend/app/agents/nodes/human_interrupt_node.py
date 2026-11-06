"""Agent 04: Human Approval Interrupt Node."""

from typing import Any, Dict

from langgraph.types import interrupt

from app.agents.state import AgentState


def human_interrupt_node(state: AgentState) -> Dict[str, Any]:
    """Human-in-the-loop checkpoint pausing graph for user paper selection."""
    screened_papers = state.get("screened_papers") or []

    # Pause: payload has candidate papers with titles, abstracts, relevance scores
    response = interrupt(
        {
            "candidate_papers": [
                {
                    "id": p.get("arxiv_id") or p.get("title"),
                    "title": p.get("title"),
                    "abstract": p.get("abstract"),
                    "relevance_score": p.get("relevance_score"),
                }
                for p in screened_papers
            ]
        }
    )

    # Resumed with user input
    user_decision = response.get("user_decision", "continue")
    approved_paper_ids = response.get("approved_paper_ids") or []

    approved = []
    if user_decision == "continue":
        approved = [
            p
            for p in screened_papers
            if (p.get("arxiv_id") or p.get("title")) in approved_paper_ids
        ]

    return {
        "approved_papers": approved,
        "user_decision": user_decision,
        "current_step": "human_approval_completed",
    }
