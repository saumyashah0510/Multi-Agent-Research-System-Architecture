"""Agent 07: Methodology Comparison & Gap Analysis Node.

Assignee Task (Issue AI-08):
- Read extracted_pdf_contents and approved_papers from AgentState
- Construct multi-paper comparison prompt for Gemini LLM
- Extract structured methodology matrix (approaches, benchmarks, limitations)
- Identify 3-5 open research gaps and unaddressed questions
- Return updated state dict with methodology_matrix and research_gaps
"""

from typing import Any, Dict

from app.agents.state import AgentState

# TODO (Assignee - AI-08): Define prompt for Methodology Comparison & Gap Analysis:
# GAP_ANALYSIS_SYSTEM_PROMPT = """..."""


async def gap_analysis_node(state: AgentState) -> Dict[str, Any]:
    """Compare methodologies across approved papers and identify literature gaps.

    TODO (Assignee - AI-08):
    1. Extract extracted_pdf_contents and approved_papers from state
    2. Format paper abstracts, methods, and results into a comparative LLM prompt
    3. Call Gemini LLM with structured output (GapAnalysisOutput schema)
    4. Extract methodology_matrix items (method_name, papers_used, strengths, limitations)
    5. Extract research_gaps list (unaddressed challenges, conflicting findings)
    6. Return {
           "methodology_matrix": methodology_matrix,
           "research_gaps": research_gaps,
           "current_step": "gap_analysis_completed"
       }
    """
    _approved_papers = state.get("approved_papers") or []
    _extracted_pdf_contents = state.get("extracted_pdf_contents") or {}

    # Placeholder return for AI-08 starter
    return {
        "methodology_matrix": [],
        "research_gaps": [],
        "current_step": "gap_analysis_completed",
    }
