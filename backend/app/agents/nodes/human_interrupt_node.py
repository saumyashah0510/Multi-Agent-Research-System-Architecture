"""Agent 04: Human Approval Interrupt Node.

Assignee Task (Issue AI-05):
- Pause LangGraph execution using interrupt() or checkpoint pause
- Emit awaiting_user_input event with candidate paper options
- Filter approved_papers when user submits decision
"""

from typing import Any, Dict

from app.agents.state import AgentState


def human_interrupt_node(state: AgentState) -> Dict[str, Any]:
    """Human-in-the-loop checkpoint pausing graph for user paper selection.

    TODO (Assignee - AI-05):
    1. Read screened_papers from state
    2. Pause execution and prepare candidate papers payload
    3. When resumed with user input (approved_paper_ids, user_decision):
       - If user_decision == 'continue', filter screened_papers by approved_paper_ids
       - Return {"approved_papers": approved, "user_decision": decision, "current_step": "human_approval_completed"}
    """
    screened_papers = state.get("screened_papers") or []
    # Placeholder return for AI-05 starter
    return {
        "approved_papers": screened_papers,
        "user_decision": "continue",
        "current_step": "human_approval_completed",
    }
