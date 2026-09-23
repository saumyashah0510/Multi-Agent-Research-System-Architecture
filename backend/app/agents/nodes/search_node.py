"""Search and paper discovery agent node implementation placeholder.

Assignee Task (Issue AI-02):
- Read user_query from AgentState.
- Call academic search service wrapper (search_academic_papers).
- Update discovered_papers list and set current_step to "search_completed".
"""

from app.agents.state import AgentState


# TODO (Assignee - AI Engineer): Implement search agent node logic
async def search_agent_node(state: AgentState) -> dict:
    """Execute paper discovery across academic APIs."""
    return {"current_step": "search_completed"}
