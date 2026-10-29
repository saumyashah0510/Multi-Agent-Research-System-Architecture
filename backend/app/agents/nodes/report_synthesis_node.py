"""Agent 09: Structured Synthesis Report Generation Node.

Assignee Task (Issue AI-10):
- Read user_query, approved_papers, methodology_matrix, research_gaps, and verified_references from AgentState
- Call Gemini LLM with structured output schema (SynthesizedReviewOutput)
- Produce comprehensive academic literature review report (executive summary, thematic clusters, methodology matrix, research gaps, conclusion, references)
- Optionally generate PDF document and upload to AWS S3 (reports/review_{id}.pdf) with local fallback
- Update state["synthesized_review"] and set current_step to "synthesis_completed"
"""

from typing import Any, Dict

from app.agents.state import AgentState

# TODO (Assignee - AI-10): Define system prompt for Academic Synthesis Report:
# SYNTHESIS_SYSTEM_PROMPT = """..."""


async def report_synthesis_node(state: AgentState) -> Dict[str, Any]:
    """Generate final comprehensive literature review report using structured LLM output.

    TODO (Assignee - AI-10):
    1. Extract user_query, approved_papers, methodology_matrix, research_gaps, verified_references from state
    2. Call Gemini LLM with structured schema (SynthesizedReviewOutput)
    3. Construct synthesized review dictionary:
       {
           "title": output.title,
           "executive_summary": output.executive_summary,
           "thematic_clusters": [tc.dict() for tc in output.thematic_clusters],
           "methodology_matrix": [mm.dict() for mm in output.methodology_matrix],
           "research_gaps": output.research_gaps,
           "conclusion": output.conclusion,
           "references": output.references,
       }
    4. Generate PDF artifact and upload to AWS S3 bucket under reports/review_{review_id}.pdf
    5. Return {
           "synthesized_review": synthesized_dict,
           "current_step": "synthesis_completed"
       }
    """
    user_query = state.get("user_query", "Academic Research Review")
    methodology_matrix = state.get("methodology_matrix") or []
    research_gaps = state.get("research_gaps") or []
    verified_references = state.get("verified_references") or []

    # Placeholder return for AI-10 starter
    return {
        "synthesized_review": {
            "title": f"Literature Review: {user_query}",
            "executive_summary": "Placeholder executive summary for literature review.",
            "thematic_clusters": [],
            "methodology_matrix": methodology_matrix,
            "research_gaps": research_gaps,
            "conclusion": "Placeholder conclusion.",
            "references": verified_references,
        },
        "current_step": "synthesis_completed",
    }


# Aliases for backward compatibility
synthesis_node = report_synthesis_node
synthesis_agent_node = report_synthesis_node
