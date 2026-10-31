"""Agent 09: Structured Synthesis Report Generation Node.

Assignee Task (Issue AI-10):
- Read user_query, approved_papers, methodology_matrix, research_gaps, and verified_references from AgentState
- Call Gemini LLM with structured output schema (SynthesizedReviewOutput)
- Produce comprehensive academic literature review report (executive summary, thematic clusters, methodology matrix, research gaps, conclusion, references)
- Export markdown formatting helper for multi-format downstream consumption
- Update state["synthesized_review"] and set current_step to "synthesis_completed"
"""

import logging
from typing import Any, Dict, List

from google import genai

from app.agents.state import AgentState
from app.core.config import settings
from app.schemas.agent_outputs import (
    SynthesizedReviewOutput,
)

logger = logging.getLogger(__name__)

SYNTHESIS_SYSTEM_PROMPT = """You are an elite academic researcher and principal literature review synthesizer.
Your task is to synthesize a high-impact, publication-grade academic literature review report based on the provided approved research papers, comparative methodology findings, verified citations, and research gaps.

CRITICAL SYNTHESIS GUIDELINES:
1. Title: Formulate an authoritative, publication-ready academic title reflecting the synthesis.
2. Executive Summary: Provide an extensive, rigorous multi-paragraph synthesis of the overarching domain, architectural paradigms, empirical performance trends, and primary open challenges.
3. Thematic Clusters: Group the literature into 2 to 4 thematic clusters (e.g., architectural paradigms, benchmark evaluation, optimization trade-offs). Under each cluster, provide in-depth comparative analysis rather than simple isolated summaries, referencing relevant papers.
4. Methodology Matrix: Preserve or synthesize a comparative methodology breakdown mapping methods, papers used, strengths, and limitations.
5. Research Gaps: Articulate 3 to 5 actionable research gaps, unresolved contradictions, or engineering bottlenecks that future research must address.
6. Conclusion: Formulate a definitive conclusion summarizing theoretical implications and the next frontier for the domain.
7. References: Include a curated bibliography listing the evaluated papers and verified citations.

Rigorously ground all statements in the provided paper metadata, extracted contents, and verified citations. Output must strictly conform to the requested JSON schema.
"""


def format_review_as_markdown(review: Dict[str, Any]) -> str:
    """Format a synthesized review dictionary into clean GitHub-flavored Markdown."""
    title = review.get("title", "Literature Review Synthesis")
    executive_summary = review.get("executive_summary", "")
    thematic_clusters = review.get("thematic_clusters", [])
    methodology_matrix = review.get("methodology_matrix", [])
    research_gaps = review.get("research_gaps", [])
    conclusion = review.get("conclusion", "")
    references = review.get("references", [])

    lines = [
        f"# {title}",
        "",
        "## Executive Summary",
        executive_summary,
        "",
    ]

    if thematic_clusters:
        lines.append("## Thematic Clusters & Comparative Analysis")
        for idx, cluster in enumerate(thematic_clusters, 1):
            theme_name = cluster.get("theme", f"Theme {idx}")
            summary = cluster.get("summary", "")
            citations = cluster.get("citations", [])
            lines.append(f"### {idx}. {theme_name}")
            lines.append(summary)
            if citations:
                lines.append("")
                lines.append(f"**Cited Literature:** {', '.join(citations)}")
            lines.append("")

    if methodology_matrix:
        lines.append("## Comparative Methodology Matrix")
        lines.append("| Methodology | Papers Evaluated | Strengths | Limitations |")
        lines.append("| :--- | :--- | :--- | :--- |")
        for item in methodology_matrix:
            m_name = item.get("method_name", "N/A")
            papers = "<br>".join(item.get("papers_used", [])) or "N/A"
            strengths = "<br>".join(item.get("strengths", [])) or "N/A"
            limitations = "<br>".join(item.get("limitations", [])) or "N/A"
            lines.append(f"| **{m_name}** | {papers} | {strengths} | {limitations} |")
        lines.append("")

    if research_gaps:
        lines.append("## Unresolved Research Gaps & Open Challenges")
        for idx, gap in enumerate(research_gaps, 1):
            lines.append(f"{idx}. {gap}")
        lines.append("")

    if conclusion:
        lines.append("## Conclusion & Future Directions")
        lines.append(conclusion)
        lines.append("")

    if references:
        lines.append("## References & Bibliography")
        for idx, ref in enumerate(references, 1):
            if isinstance(ref, dict):
                ref_title = ref.get("title") or ref.get("paper_id_or_title") or f"Reference {idx}"
                claim = ref.get("claim")
                quote = ref.get("matched_passage")
                if claim and quote:
                    lines.append(f'{idx}. **{ref_title}** - *"{claim}"* (Grounding: *"{quote}"*)')
                else:
                    lines.append(f"{idx}. **{ref_title}**")
            else:
                lines.append(f"{idx}. {ref}")
        lines.append("")

    return "\n".join(lines).strip()


async def report_synthesis_node(state: AgentState) -> Dict[str, Any]:
    """Generate final comprehensive literature review report using structured LLM output."""
    user_query = state.get("user_query", "Academic Research Review")
    approved_papers: List[Dict[str, Any]] = state.get("approved_papers") or []
    methodology_matrix: List[Dict[str, Any]] = state.get("methodology_matrix") or []
    research_gaps: List[str] = state.get("research_gaps") or []
    verified_references: List[Dict[str, Any]] = state.get("verified_references") or []
    extracted_pdf_contents: Dict[str, Any] = state.get("extracted_pdf_contents") or {}

    # 1. Graceful return if no papers or matrix available
    if not approved_papers and not methodology_matrix and not research_gaps:
        logger.info(
            "Insufficient literature or matrix items to synthesize report; returning empty review."
        )
        empty_review = {
            "title": f"Literature Review: {user_query}",
            "executive_summary": "Insufficient paper data or approved literature available to generate a synthesis review.",
            "thematic_clusters": [],
            "methodology_matrix": [],
            "research_gaps": [],
            "conclusion": "No literature available to draw conclusions.",
            "references": [],
        }
        return {
            "synthesized_review": empty_review,
            "current_step": "synthesis_completed",
        }

    # 2. Strict Fail-Fast if GEMINI_API_KEY is not configured
    if not settings.GEMINI_API_KEY:
        error_msg = "GEMINI_API_KEY is not configured; cannot generate synthesis report."
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    # 3. Assemble synthesis input prompt payload
    papers_context = []
    for p in approved_papers[:10]:
        title = p.get("title", "Untitled")
        abstract = p.get("abstract", "")
        papers_context.append(f"Paper: {title}\nAbstract: {abstract}")

    # Include extracted sections if available
    for p_id, content in list(extracted_pdf_contents.items())[:5]:
        if isinstance(content, dict):
            sec_texts = []
            if content.get("methodology"):
                sec_texts.append(f"Methodology: {content['methodology'][:800]}")
            if content.get("results"):
                sec_texts.append(f"Results: {content['results'][:800]}")
            if sec_texts:
                papers_context.append(f"Paper Excerpts ({p_id}):\n" + "\n".join(sec_texts))

    matrix_context = []
    for m in methodology_matrix:
        name = m.get("method_name", "Method")
        strengths = ", ".join(m.get("strengths", []))
        limits = ", ".join(m.get("limitations", []))
        matrix_context.append(
            f"- Method: {name} | Strengths: [{strengths}] | Limitations: [{limits}]"
        )

    refs_context = []
    for r in verified_references[:8]:
        claim = r.get("claim", "")
        quote = r.get("matched_passage", "")
        p_title = r.get("paper_id_or_title", "")
        if claim:
            refs_context.append(f'- [{p_title}] Claim: {claim} (Grounding Quote: "{quote}")')

    user_content = (
        f"RESEARCH TOPIC / USER QUERY:\n{user_query}\n\n"
        f"APPROVED PAPERS & LITERATURE EVIDENCE:\n\n"
        + ("\n\n---\n\n".join(papers_context) if papers_context else "No papers provided.")
        + "\n\n"
        "EXISTING METHODOLOGY MATRIX:\n"
        + ("\n".join(matrix_context) if matrix_context else "None provided.")
        + "\n\n"
        "IDENTIFIED RESEARCH GAPS:\n"
        + ("\n".join(f"- {g}" for g in research_gaps) if research_gaps else "None provided.")
        + "\n\n"
        "VERIFIED CITATIONS (GROUND TRUTH):\n"
        + ("\n".join(refs_context) if refs_context else "None provided.")
        + "\n\n"
        "Synthesize a cohesive, high-impact academic literature review following the instructions."
    )

    try:
        # 4. Call Google Gemini LLM with structured Pydantic schema and model fallback cascade
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        candidate_models = settings.gemini_model_candidates

        parsed_output = None
        last_model_error = None

        for model_name in candidate_models:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[SYNTHESIS_SYSTEM_PROMPT, user_content],
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": SynthesizedReviewOutput,
                    },
                )
                parsed_output = SynthesizedReviewOutput.model_validate_json(response.text)
                break
            except Exception as model_err:
                logger.warning(
                    f"Gemini model '{model_name}' failed during report synthesis ({model_err}); trying fallback."
                )
                last_model_error = model_err

        if parsed_output is None:
            raise RuntimeError(
                f"All configured Gemini models {candidate_models} failed during report synthesis. Last error: {last_model_error}"
            )

        # 5. Construct synthesized review dictionary
        synthesized_dict = {
            "title": parsed_output.title,
            "executive_summary": parsed_output.executive_summary,
            "thematic_clusters": [tc.model_dump() for tc in parsed_output.thematic_clusters],
            "methodology_matrix": [mm.model_dump() for mm in parsed_output.methodology_matrix],
            "research_gaps": parsed_output.research_gaps,
            "conclusion": parsed_output.conclusion,
            "references": [ref.model_dump() for ref in parsed_output.references],
        }

        logger.info(
            f"Successfully synthesized literature review: '{parsed_output.title}' with "
            f"{len(parsed_output.thematic_clusters)} thematic clusters and {len(parsed_output.research_gaps)} gaps."
        )

        return {
            "synthesized_review": synthesized_dict,
            "current_step": "synthesis_completed",
        }

    except Exception as exc:
        logger.error(f"Error executing Gemini Report Synthesis: {exc}", exc_info=True)
        raise RuntimeError(f"Report synthesis failed due to LLM error: {exc}") from exc


# Aliases for flexible node mapping in orchestrator and legacy imports
synthesis_node = report_synthesis_node
synthesis_agent_node = report_synthesis_node
