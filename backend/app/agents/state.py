"""TypedDict schema representing global shared state memory across the 9-Agent pipeline."""

import operator
from typing import Annotated, Any, Dict, List, TypedDict


class AgentState(TypedDict, total=False):
    """Global state shared across all 9 agent nodes in the literature review pipeline."""

    review_id: int
    user_query: str
    target_domains: List[str]

    search_queries: List[str]
    discovered_papers: Annotated[List[dict], operator.add]
    screened_papers: List[dict]
    approved_papers: List[dict]
    extracted_pdf_contents: Dict[str, Any]
    methodology_matrix: List[dict]
    research_gaps: List[str]
    verified_references: List[dict]
    rejected_claims: List[dict]
    has_hallucinations: bool
    verification_summary: str
    user_decision: str
    synthesized_review: Dict[str, Any]
    current_step: str
