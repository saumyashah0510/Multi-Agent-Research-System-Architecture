"""TypedDict schema representing global shared state memory across the 9-Agent pipeline."""

import operator
from typing import Annotated, Any, Dict, List, TypedDict


class AgentState(TypedDict):
    """Global state shared across all 9 agent nodes in the literature review pipeline."""

    user_query: str
    target_domains: List[str]
    search_queries: List[str]
    discovered_papers: Annotated[List[dict], operator.add]
    screened_papers: List[dict]
    approved_papers: List[dict]
    extracted_pdf_contents: Dict[str, Any]
    verified_references: List[dict]
    user_decision: str
    synthesized_review: Dict[str, Any]
    current_step: str
