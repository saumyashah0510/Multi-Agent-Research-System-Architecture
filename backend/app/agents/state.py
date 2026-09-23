"""TypedDict schema placeholder representing shared state of the human-in-the-loop multi-agent pipeline.

Assignee Task (Issue AI-01):
- Define AgentState TypedDict with keys:
  * user_query: str
  * discovered_papers: List[dict] (Raw papers from Search Agent)
  * screened_papers: List[dict] (Relevance-filtered papers from Screening Agent)
  * approved_papers: List[dict] (Papers selected/approved by Human User on UI)
  * user_decision: str ("continue" or "find_more")
  * synthesized_review: dict (Structured JSON report: title, summary, themes, methodology_matrix, research_gaps, references)
  * current_step: str
"""

import operator
from typing import Annotated, Any, Dict, List, TypedDict


# TODO (Assignee - AI Engineer): Define AgentState TypedDict schema
class AgentState(TypedDict):
    """Global state shared across all agent nodes."""

    user_query: str
    discovered_papers: Annotated[List[dict], operator.add]
    screened_papers: List[dict]
    approved_papers: List[dict]
    user_decision: str
    synthesized_review: Dict[str, Any]
    current_step: str
