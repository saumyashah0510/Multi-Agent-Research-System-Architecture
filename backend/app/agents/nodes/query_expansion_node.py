"""Agent 01: Query Expansion and Domain Classifier Node.

Assignee Task (Issue AI-02):
- Read user_query from AgentState
- Invoke Gemini LLM with structured output prompt
- Extract 3-5 academic sub-queries and target domain classifications
- Return updated state dict with target_domains and search_queries
"""

from typing import Any, Dict

from app.agents.state import AgentState

# TODO (Assignee - AI-02): Define prompt for Query Expansion:
# QUERY_EXPANSION_SYSTEM_PROMPT = """..."""


async def query_expansion_node(state: AgentState) -> Dict[str, Any]:
    """Expand user research query into 3-5 targeted sub-queries and classify domains.

    TODO (Assignee - AI-02):
    1. Extract user_query from state (fallback if empty)
    2. Prompt Gemini LLM to generate 3-5 distinct sub-queries (synonyms, technical terms)
    3. Classify subject domains (e.g., cs.AI, q-bio)
    4. Return {"target_domains": domains, "search_queries": queries, "current_step": "query_expansion_completed"}
    """
    user_query = state.get("user_query", "")
    # Placeholder return for AI-02 starter
    return {
        "target_domains": ["Computer Science"],
        "search_queries": [user_query] if user_query else ["Academic Literature Review"],
        "current_step": "query_expansion_completed",
    }
