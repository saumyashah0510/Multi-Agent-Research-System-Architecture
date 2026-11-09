"""Agent 09: Structured Synthesis Report Generation Node.

Assignee Task (Issue AI-10):
- Read user_query, approved_papers, methodology_matrix, research_gaps, and verified_references from AgentState
- Read audit trail (rejected_claims, has_hallucinations, verification_summary) to safeguard against hallucination resurgence
- Call Gemini LLM with structured output schema (SynthesizedReviewOutput)
- Produce comprehensive academic literature review report (executive summary, thematic clusters, methodology matrix, research gaps, conclusion, references)
- Export robust markdown formatting helper for multi-format downstream consumption (with pipe escaping)
- Update state["synthesized_review"] and set current_step to "synthesis_completed"
"""

import logging
from typing import Any, Dict, List

from google import genai

from app.agents.state import AgentState
from app.core.config import settings
from app.schemas.agent_outputs import (
    ReferenceItem,
    SynthesizedReviewOutput,
)

logger = logging.getLogger(__name__)

SYNTHESIS_SYSTEM_PROMPT = """You are an elite academic researcher and principal literature review synthesizer.
Your task is to synthesize a high-impact, publication-grade academic literature review report based on the provided approved research papers, comparative methodology findings, verified citations, and research gaps.

CRITICAL SYNTHESIS GUIDELINES:
1. Title: Formulate an authoritative, publication-ready academic title reflecting the synthesis topic.
2. Executive Summary: Provide an extensive, rigorous 2-3 paragraph academic synthesis structured into:
   - Problem scope & theoretical motivation
   - Synthesis of dominant paradigms and current state-of-the-art
   - Key breakthroughs, empirical performance benchmarks, and major consensus/trade-offs.
3. Thematic Clusters: Group the literature into 2 to 4 thematic chapters. Under each cluster, provide in-depth comparative analysis rather than simple isolated summaries, contrasting the strengths, empirical metrics, and methodologies of the evaluated papers. Include standard in-text citation keys (e.g. '[Author, Year]').
4. Methodology Matrix: Preserve or synthesize a comparative methodology breakdown mapping methods, papers used, strengths, and limitations. Ensure each method accurately references the papers that used it.
5. Research Gaps: Articulate 3 to 5 concrete, actionable research gaps detailing specific technical bottlenecks, evaluation deficiencies, or unresolved failure modes.
6. Conclusion & Recommendations: Formulate a definitive conclusion summarizing theoretical implications, architectural recommendations, and actionable future research horizons.
7. References: Include a curated bibliography listing the evaluated papers with complete bibliographic metadata:
   - title: Canonical paper title
   - citation_key: Author-year or identifier citation key without outer brackets (e.g. 'Chase et al., 2024' or 'Vaswani et al., 2017')
   - authors: List of author names from provided metadata
   - year: Publication year if provided
   - url: Canonical arXiv / DOI link if available
   - matched_passage: Verbatim grounding quote copied ONLY from the provided VERIFIED CITATIONS or paper excerpts proving claims. If no exact quote is in the provided context, leave empty ("").
   - summary: Brief 1-sentence relevance to this review.
8. Citation & Evidence Grounding (STRICT):
   - Use ONLY verified citations and approved papers as factual evidence.
   - Never fabricate DOIs, URLs, publication venues, authors, quotes, or experimental results.
   - Any matched_passage must directly originate from the provided verified citations or paper excerpts; do not invent or hallucinate quotes.
   - If any preliminary claim was flagged in the audit trail as a rejected/unsupported hallucination, STRICTLY EXCLUDE IT from the report.
   - Preserve the association between each methodology and its cited papers.

Rigorously ground all statements in the provided paper metadata, extracted contents, and verified citations. Output must strictly conform to the requested JSON schema.
"""


def _clean_table_cell(value: Any) -> str:
    """Format and escape values for safe Markdown table cells."""
    if isinstance(value, list):
        text = "<br>".join(str(item) for item in value if item)
    else:
        text = str(value or "")
    # Escape pipe characters to avoid corrupting Markdown tables
    escaped = text.replace("|", "\\|").replace("\n", "<br>").strip()
    return escaped or "N/A"


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
            m_name = _clean_table_cell(item.get("method_name", "N/A"))
            papers = _clean_table_cell(item.get("papers_used", []))
            strengths = _clean_table_cell(item.get("strengths", []))
            limitations = _clean_table_cell(item.get("limitations", []))
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
                cite_key = ref.get("citation_key")
                summary = ref.get("summary")
                claim = ref.get("claim")
                quote = ref.get("matched_passage")
                authors = ref.get("authors")
                year = ref.get("year")
                url = ref.get("url")

                ref_parts = [f"**{ref_title}**"]
                if authors:
                    auth_str = ", ".join(authors) if isinstance(authors, list) else str(authors)
                    ref_parts.append(f"by {auth_str}")
                if year:
                    ref_parts.append(f"({year})")
                if cite_key:
                    ck = str(cite_key).strip()
                    bracketed_key = ck if (ck.startswith("[") and ck.endswith("]")) else f"[{ck}]"
                    ref_parts.append(f"`{bracketed_key}`")
                if url:
                    ref_parts.append(f"<{url}>")
                if summary:
                    ref_parts.append(f"- {summary}")
                if claim and quote:
                    ref_parts.append(f'- *"{claim}"* (Grounding: *"{quote}"*)')
                elif quote:
                    ref_parts.append(f'(Grounding: *"{quote}"*)')

                lines.append(f"{idx}. {' '.join(ref_parts)}")
            else:
                lines.append(f"{idx}. {ref}")
        lines.append("")

    return "\n".join(lines).strip()


def _sanitize_references(
    references: List[ReferenceItem],
    verified_references: List[Dict[str, Any]],
    approved_papers: List[Dict[str, Any]],
    extracted_pdf_contents: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Verify and ground matched passages before publishing in synthesized review."""
    # 1. Collect verified reference passages from Agent 08
    verified_passages: List[str] = [
        str(r.get("matched_passage", "")).strip().lower()
        for r in verified_references
        if r.get("matched_passage")
    ]

    # 2. Collect paper source texts (abstracts and extracted sections)
    source_texts: List[str] = []
    for p in approved_papers:
        if p.get("abstract"):
            source_texts.append(str(p["abstract"]).lower())
    for content in (extracted_pdf_contents or {}).values():
        if isinstance(content, dict):
            for sec_t in (content.get("sections") or {}).values():
                if isinstance(sec_t, str):
                    source_texts.append(sec_t.lower())
            if content.get("full_text"):
                source_texts.append(str(content["full_text"]).lower())
        elif isinstance(content, str):
            source_texts.append(content.lower())

    sanitized: List[Dict[str, Any]] = []
    for ref in references:
        ref_dict = ref.model_dump()
        passage = (ref_dict.get("matched_passage") or "").strip()

        if passage:
            clean_p = passage.lower()
            # Check if passage matches any verified citation
            is_grounded = any(clean_p in vp or vp in clean_p for vp in verified_passages if vp)
            # If not in verified citations, check if substring exists in source texts
            if not is_grounded:
                probe = clean_p[:60] if len(clean_p) > 60 else clean_p
                if len(probe) >= 15:
                    is_grounded = any(probe in st for st in source_texts)

            if not is_grounded:
                logger.warning(
                    "Dropping unverified/hallucinated matched_passage for reference '%s': '%s'",
                    ref_dict.get("title"),
                    passage[:80],
                )
                ref_dict["matched_passage"] = ""

        # Backfill matched_passage from verified_references if LLM omitted it
        if not ref_dict.get("matched_passage"):
            ref_title = (ref_dict.get("title") or "").lower()
            for vr in verified_references:
                vr_passage = vr.get("matched_passage")
                vr_target = (vr.get("paper_id_or_title") or "").lower()
                if vr_passage and vr_target and (vr_target in ref_title or ref_title in vr_target):
                    ref_dict["matched_passage"] = vr_passage
                    break

        sanitized.append(ref_dict)

    return sanitized


async def report_synthesis_node(state: AgentState) -> Dict[str, Any]:
    """Generate final comprehensive literature review report using structured LLM output."""
    user_query = state.get("user_query", "Academic Research Review")
    approved_papers: List[Dict[str, Any]] = state.get("approved_papers") or []
    methodology_matrix: List[Dict[str, Any]] = state.get("methodology_matrix") or []
    research_gaps: List[str] = state.get("research_gaps") or []
    verified_references: List[Dict[str, Any]] = state.get("verified_references") or []
    extracted_pdf_contents: Dict[str, Any] = state.get("extracted_pdf_contents") or {}
    rejected_claims: List[Dict[str, Any]] = state.get("rejected_claims") or []
    has_hallucinations: bool = state.get("has_hallucinations", False)
    verification_summary: str = state.get("verification_summary", "")

    # 1. Graceful return if no inputs are available
    if not (approved_papers or methodology_matrix or research_gaps or verified_references):
        logger.info(
            "Insufficient literature or evidence to synthesize report; returning empty review."
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
    for p in approved_papers[:12]:
        title = p.get("title", "Untitled")
        authors = p.get("authors")
        year = p.get("year")
        abstract = p.get("abstract", "")
        url = p.get("url") or p.get("pdf_url") or ""
        doi = p.get("doi") or ""
        arxiv_id = p.get("arxiv_id") or ""

        header = f"Paper: {title}"
        if authors:
            auth_str = ", ".join(authors) if isinstance(authors, list) else str(authors)
            header += f" | Authors: {auth_str}"
        if year:
            header += f" ({year})"
        if arxiv_id:
            header += f" | arXiv:{arxiv_id}"
        if doi:
            header += f" | DOI:{doi}"
        if url:
            header += f" | URL: {url}"
        papers_context.append(f"{header}\nAbstract: {abstract}")

    # Map p_id to title if known so excerpts have full paper titles
    id_to_title: Dict[str, str] = {}
    for p in approved_papers:
        if p.get("arxiv_id"):
            id_to_title[str(p["arxiv_id"]).lower()] = p.get("title", "")
        if p.get("doi"):
            id_to_title[str(p["doi"]).lower()] = p.get("title", "")
        if p.get("title"):
            id_to_title[p["title"].strip().lower()] = p.get("title", "")

    # Include extracted sections if available
    for p_id, content in list(extracted_pdf_contents.items())[:8]:
        if isinstance(content, dict):
            sec_texts = []
            if content.get("methodology"):
                sec_texts.append(f"Methodology: {content['methodology'][:800]}")
            if content.get("results"):
                sec_texts.append(f"Results: {content['results'][:800]}")
            if sec_texts:
                resolved_title = id_to_title.get(str(p_id).lower(), p_id)
                papers_context.append(
                    f"Paper Excerpts ({resolved_title}):\n" + "\n".join(sec_texts)
                )

    matrix_context = []
    for m in methodology_matrix:
        name = m.get("method_name", "Method")
        papers = ", ".join(m.get("papers_used", [])) or "Unspecified"
        strengths = ", ".join(m.get("strengths", []))
        limits = ", ".join(m.get("limitations", []))
        matrix_context.append(
            f"- Method: {name}\n  Papers Used: [{papers}]\n  Strengths: [{strengths}]\n  Limitations: [{limits}]"
        )

    refs_context = []
    for r in verified_references[:10]:
        claim = r.get("claim", "")
        quote = r.get("matched_passage", "")
        p_title = r.get("paper_id_or_title", "")
        if claim:
            refs_context.append(f'- [{p_title}] Claim: {claim} (Grounding Quote: "{quote}")')

    # Audit Trail Context from Agent 08 (to explicitly warn Gemini of rejected assertions)
    audit_context = []
    if has_hallucinations or rejected_claims:
        audit_context.append("PRIOR VERIFICATION AUDIT TRAIL:")
        audit_context.append(
            "- Status: Hallucinated / unverified preliminary assertions were detected."
        )
        if verification_summary:
            audit_context.append(f"- Verifier Assessment: {verification_summary}")
        if rejected_claims:
            audit_context.append(
                "- REJECTED ASSERTIONS (DO NOT INCLUDE OR CITE IN FINAL SYNTHESIS):"
            )
            for rc in rejected_claims[:6]:
                rc_claim = rc.get("claim", "")
                if rc_claim:
                    audit_context.append(f'  * "{rc_claim}"')

    user_content_sections = [
        f"RESEARCH TOPIC / USER QUERY:\n{user_query}",
        "APPROVED PAPERS & LITERATURE EVIDENCE:\n"
        + ("\n\n---\n\n".join(papers_context) if papers_context else "No papers provided."),
        "EXISTING METHODOLOGY MATRIX:\n"
        + ("\n".join(matrix_context) if matrix_context else "None provided."),
        "IDENTIFIED RESEARCH GAPS:\n"
        + ("\n".join(f"- {g}" for g in research_gaps) if research_gaps else "None provided."),
        "VERIFIED CITATIONS (GROUND TRUTH):\n"
        + ("\n".join(refs_context) if refs_context else "None provided."),
    ]

    if audit_context:
        user_content_sections.append("\n".join(audit_context))

    user_content_sections.append(
        "Synthesize a cohesive, publication-grade academic literature review adhering strictly to the guidelines."
    )

    user_content = "\n\n".join(user_content_sections)

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

        # 5. Validate and ground references before publishing
        sanitized_refs = _sanitize_references(
            references=parsed_output.references,
            verified_references=verified_references,
            approved_papers=approved_papers,
            extracted_pdf_contents=extracted_pdf_contents,
        )

        synthesized_dict = {
            "title": parsed_output.title,
            "executive_summary": parsed_output.executive_summary,
            "thematic_clusters": [tc.model_dump() for tc in parsed_output.thematic_clusters],
            "methodology_matrix": [mm.model_dump() for mm in parsed_output.methodology_matrix],
            "research_gaps": parsed_output.research_gaps,
            "conclusion": parsed_output.conclusion,
            "references": sanitized_refs,
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
