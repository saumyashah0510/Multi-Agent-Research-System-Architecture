"""Agent 03: Screening and Relevance Scoring Node.

Assignee Task (Issue AI-04):
- Read user_query and discovered_papers from AgentState
- Score relevance of paper abstracts against user_query using Gemini LLM (0.0 to 1.0)
- Filter papers meeting minimum threshold (score >= 0.6)
- Return updated state dict with screened_papers list
"""

from typing import Any, Dict

from app.agents.state import AgentState

# TODO (Assignee - AI-04): Define system prompt for abstract relevance screening:
# SCREENING_SYSTEM_PROMPT = """..."""


async def screening_node(state: AgentState) -> Dict[str, Any]:
    """Score paper abstracts and filter by relevance threshold (>= 0.6).

    TODO (Assignee - AI-04):
    1. Extract discovered_papers and user_query from state
    2. Prompt Gemini LLM to score each paper abstract (0.0 - 1.0) with a brief justification
    3. Filter out papers below 0.6 threshold
    4. Attach 'relevance_score' and 'screening_reason' to each accepted paper dict
    5. Return {"screened_papers": screened_papers, "current_step": "screening_completed"}
    """
    discovered_papers = state.get("discovered_papers") or []
    # Placeholder return for AI-04 starter
    return {
        "screened_papers": discovered_papers,
        "current_step": "screening_completed",
    }


# Alias for backward compatibility
screening_agent_node = screening_node
