"""Agent 09: Structured Synthesis Report Generation Node.

Assignee Task (Issue AI-10):
- Read user_query, approved_papers, methodology_matrix, research_gaps, and verified_references from AgentState
- Read audit trail (rejected_claims, has_hallucinations, verification_summary) to safeguard against hallucination resurgence
- Call Gemini LLM with structured output schema (SynthesizedReviewOutput)
- Produce comprehensive academic literature review report (executive summary, thematic clusters, methodology matrix, research gaps, conclusion, references)
- Export robust markdown formatting helper for multi-format downstream consumption (with pipe escaping)
- Update state["synthesized_review"] and set current_step to "synthesis_completed"
"""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Set

from google import genai

from app.agents.state import AgentState
from app.core.config import settings
from app.schemas.agent_outputs import (
    ReferenceItem,
    SynthesizedReviewOutput,
)

logger = logging.getLogger(__name__)

SYNTHESIS_SYSTEM_PROMPT = """You are an elite academic researcher and principal literature review synthesizer.
Your task is to synthesize an exhaustive, publication-grade, long-form academic literature review report based on the provided approved research corpus, comparative methodology findings, verified citations, and research gaps.

CRITICAL SYNTHESIS GUIDELINES FOR HIGH-IMPACT, COMPREHENSIVE REVIEWS:
1. Title: Formulate an authoritative, publication-ready academic title reflecting the synthesis topic.
2. Executive Summary:
   - Provide an extensive, rigorous multi-paragraph academic synthesis (3 to 4 substantial paragraphs separated by double newline '\\n\\n' characters for clean readability).
   - Paragraph 1: Problem scope, theoretical motivations, and foundational paradigms.
   - Paragraph 2: Comprehensive synthesis of dominant architectural, algorithmic, or experimental approaches across the reviewed corpus.
   - Paragraph 3: Key empirical breakthroughs, benchmark comparisons, performance trade-offs, and emerging consensus.
   - Paragraph 4: Critical tensions, limitations, and cross-cutting challenges.
   - PARAGRAPH FORMATTING (MANDATORY): Always separate paragraphs with two newline characters ('\\n\\n'). Never output as a single unbroken wall of text.
3. Thematic Clusters & Deep Comparative Analysis:
   - Group the literature into comprehensive thematic chapters (typically 5 to 8 exhaustive chapters for large corpora, or 3 to 5 for smaller corpora).
   - Each thematic chapter MUST provide substantive, multi-paragraph comparative discourse. Use double newlines ('\\n\\n') between analytical arguments for clean readability.
   - Do NOT provide superficial one-line summaries. Instead, conduct rigorous comparative analysis contrasting underlying mechanisms, architectural trade-offs, datasets, theoretical formulations, and empirical findings.
   - MANDATORY CORPUS COVERAGE: Every approved paper provided in the corpus MUST be evaluated and cited in-text across the thematic chapters using standard bracketed citation keys (e.g. '[Author, Year]'). Ensure complete, comprehensive coverage of the literature.
   - Ensure the 'citations' list for each cluster explicitly enumerates the citation keys or paper titles evaluated in that chapter.
4. Comparative Methodology Matrix:
   - Synthesize a comprehensive comparative matrix mapping all distinct methodology paradigms represented across the corpus (typically 5 to 10 distinct methodologies for comprehensive corpora).
   - Ensure 'papers_used' lists the exact paper titles from the corpus that employed or evaluated each method.
   - Provide concrete, technical strengths and limitations for each paradigm.
5. Research Gaps & Open Challenges:
   - Articulate 5 to 8 concrete, deeply analyzed literature research gaps.
   - Detail specific technical bottlenecks, conflicting benchmark results, failure modes, scalability constraints, or missing theoretical frameworks.
   - Frame each gap with theoretical motivation and actionable research questions.
6. Conclusion & Strategic Roadmap:
   - Formulate an authoritative, multi-paragraph academic conclusion separated by double newlines ('\n\n').
   - Synthesize architectural recommendations, cross-domain translation horizons, and methodological standards for future research.
7. References & Bibliography:
   - Include a complete, rigorous bibliography covering the evaluated literature with full metadata:
     * title: Canonical paper title.
     * citation_key: Author-year or identifier citation key without outer brackets (e.g. 'Vaswani et al., 2017' or 'Chase et al., 2024').
     * authors: List of author names from provided metadata.
     * year: Publication year if provided.
     * url: Canonical arXiv / DOI link if available.
     * matched_passage: Verbatim grounding quote copied ONLY from the provided VERIFIED CITATIONS or paper excerpts proving claims. If no exact quote is in the provided context, leave empty ("").
     * summary: Clear 1-2 sentence statement of the paper's specific contribution to this review.
8. Citation & Evidence Grounding (STRICT):
   - Use ONLY verified citations and approved papers as factual evidence.
   - Never fabricate DOIs, URLs, publication venues, authors, quotes, or experimental results.
   - Any matched_passage must directly originate from the provided verified citations or paper excerpts; do not invent or hallucinate quotes.
   - If an unverified assertion was explicitly rejected in the audit trail, do not present it as substantiated fact.

Rigorously adhere to academic publication depth and output strictly conforming to the requested JSON schema.
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

    def _norm_ws(text: str) -> str:
        return " ".join(text.lower().split())

    # Build per-paper source text and verified passage mapping
    paper_buckets: List[Dict[str, Any]] = []

    for p in approved_papers:
        identifiers: Set[str] = set()
        title = p.get("title")
        if title:
            identifiers.add(_norm_ws(title))
        if p.get("arxiv_id"):
            identifiers.add(_norm_ws(p["arxiv_id"]))
            identifiers.add(_norm_ws(f"arxiv:{p['arxiv_id']}"))
            identifiers.add(_norm_ws(f"arxiv_{p['arxiv_id']}"))
        if p.get("doi"):
            identifiers.add(_norm_ws(p["doi"]))
            identifiers.add(_norm_ws(f"doi:{p['doi']}"))
            identifiers.add(_norm_ws(f"doi_{p['doi']}"))
        if p.get("pubmed_id"):
            identifiers.add(_norm_ws(str(p["pubmed_id"])))
            identifiers.add(_norm_ws(f"pmid_{p['pubmed_id']}"))
            identifiers.add(_norm_ws(f"pubmed_{p['pubmed_id']}"))
        if p.get("url"):
            identifiers.add(_norm_ws(p["url"]))
        if p.get("pdf_url"):
            identifiers.add(_norm_ws(p["pdf_url"]))

        src_texts = []
        if p.get("abstract"):
            src_texts.append(_norm_ws(p["abstract"]))

        paper_buckets.append(
            {
                "paper": p,
                "identifiers": identifiers,
                "source_texts": src_texts,
                "verified_passages": [],
            }
        )

    def _find_matching_bucket(target: str) -> Optional[Dict[str, Any]]:
        clean_target = _norm_ws(target)
        if not clean_target:
            return None

        # 1. Exact match pass against bucket identifiers
        for b in paper_buckets:
            if clean_target in b["identifiers"]:
                return b

        # 2. Substring fallback pass (only if unambiguous: exactly one bucket matches)
        substring_matches = []
        for b in paper_buckets:
            for ident in b["identifiers"]:
                if len(clean_target) >= 4 and len(ident) >= 4:
                    if clean_target in ident or ident in clean_target:
                        substring_matches.append(b)
                        break

        if len(substring_matches) == 1:
            return substring_matches[0]

        return None

    # Associate extracted_pdf_contents to the appropriate paper bucket
    for paper_key, content in (extracted_pdf_contents or {}).items():
        matched_bucket = _find_matching_bucket(str(paper_key))
        if not matched_bucket and isinstance(content, dict):
            for field in ("title", "arxiv_id", "doi"):
                val = content.get(field)
                if val:
                    matched_bucket = _find_matching_bucket(str(val))
                    if matched_bucket:
                        break

        if matched_bucket:
            if isinstance(content, dict):
                for sec_t in (content.get("sections") or {}).values():
                    if isinstance(sec_t, str) and sec_t.strip():
                        matched_bucket["source_texts"].append(_norm_ws(sec_t))
                for k, v in content.items():
                    if (
                        k not in ("sections", "title", "arxiv_id", "doi", "pubmed_id", "url")
                        and isinstance(v, str)
                        and v.strip()
                    ):
                        matched_bucket["source_texts"].append(_norm_ws(v))
            elif isinstance(content, str) and content.strip():
                matched_bucket["source_texts"].append(_norm_ws(content))

    # Associate verified_references from Agent 08 to the appropriate paper bucket
    for vr in verified_references:
        vr_target = _norm_ws(str(vr.get("paper_id_or_title") or ""))
        raw_vp = (vr.get("matched_passage") or "").strip()
        if not vr_target or not raw_vp:
            continue

        matched_b = _find_matching_bucket(vr_target)
        if matched_b:
            matched_b["verified_passages"].append(raw_vp)

    sanitized: List[Dict[str, Any]] = []
    for ref in references:
        ref_dict = ref.model_dump()
        passage = (ref_dict.get("matched_passage") or "").strip()
        ref_title = _norm_ws(ref_dict.get("title") or "")
        ref_key = _norm_ws(ref_dict.get("citation_key") or "")

        # Find the specific paper bucket corresponding to this reference (exact first, unambiguous fallback)
        target_bucket = _find_matching_bucket(ref_title)
        if not target_bucket and ref_key:
            target_bucket = _find_matching_bucket(ref_key)

        # If reference cannot be matched to an approved paper, do not fall back to global corpus
        if not target_bucket:
            ref_dict["matched_passage"] = ""
            sanitized.append(ref_dict)
            continue

        paper_sources = target_bucket["source_texts"]
        paper_vps = target_bucket["verified_passages"]

        if passage:
            norm_p = _norm_ws(passage)

            # Check if the complete quote occurs in this paper's verified citations or source texts
            is_grounded = any(norm_p in _norm_ws(vp) for vp in paper_vps if vp) or any(
                norm_p in st for st in paper_sources if st
            )

            # If not grounded as a whole, check if the quote contains a verified citation
            # belonging to this paper with fabricated extensions
            if not is_grounded:
                trimmed_to_vp = None
                for raw_vp in paper_vps:
                    if raw_vp and _norm_ws(raw_vp) in norm_p:
                        trimmed_to_vp = raw_vp
                        break

                if trimmed_to_vp:
                    ref_dict["matched_passage"] = trimmed_to_vp
                    is_grounded = True
                else:
                    logger.warning(
                        "Dropping unverified/hallucinated matched_passage for reference '%s': '%s'",
                        ref_dict.get("title"),
                        passage[:80],
                    )
                    ref_dict["matched_passage"] = ""

        # Backfill matched_passage only if an exact verbatim quote from this cited paper exists
        if not ref_dict.get("matched_passage"):
            for raw_vp in paper_vps:
                norm_vr_p = _norm_ws(raw_vp)
                if any(norm_vr_p in st for st in paper_sources):
                    ref_dict["matched_passage"] = raw_vp
                    break

        sanitized.append(ref_dict)

    return sanitized


def _resolve_paper_extracted_content(
    paper: Dict[str, Any], extracted_pdf_contents: Dict[str, Any]
) -> Dict[str, Any]:
    """Resolve extracted PDF sections for a paper across various identifier formats."""
    if not extracted_pdf_contents:
        return {}

    candidates = []
    if paper.get("arxiv_id"):
        aid = str(paper["arxiv_id"]).strip()
        candidates.extend([aid, f"arxiv_{aid}", aid.lower(), f"arxiv_{aid.lower()}"])
    if paper.get("doi"):
        doi = str(paper["doi"]).strip()
        candidates.extend([doi, f"doi_{doi}", doi.lower(), f"doi_{doi.lower()}"])
    if paper.get("pubmed_id"):
        pmid = str(paper["pubmed_id"]).strip()
        candidates.extend([pmid, f"pmid_{pmid}", f"pubmed_{pmid}"])
    if paper.get("title"):
        title = str(paper["title"]).strip()
        candidates.extend([title, title.lower()])

    for c in candidates:
        if c in extracted_pdf_contents and isinstance(extracted_pdf_contents[c], dict):
            return extracted_pdf_contents[c]
    return {}


def _generate_citation_key(paper: Dict[str, Any]) -> str:
    """Generate a clean Author-Year citation key (e.g. 'Vaswani et al., 2017')."""
    authors = paper.get("authors") or []
    if isinstance(authors, str):
        authors = [a.strip() for a in authors.split(",") if a.strip()]
    year = paper.get("year")
    year_str = str(year) if year else "n.d."

    if not authors:
        return f"Anon, {year_str}"

    first_author = authors[0].strip()
    if "," in first_author:
        surname = first_author.split(",")[0].strip()
    else:
        parts = first_author.split()
        surname = parts[-1].strip() if parts else "Anon"

    if len(authors) > 2:
        return f"{surname} et al., {year_str}"
    elif len(authors) == 2:
        sec_author = authors[1].strip()
        sec_surname = (
            sec_author.split(",")[0].strip()
            if "," in sec_author
            else (sec_author.split()[-1].strip() if sec_author.split() else "")
        )
        return (
            f"{surname} & {sec_surname}, {year_str}"
            if sec_surname
            else f"{surname} et al., {year_str}"
        )
    else:
        return f"{surname}, {year_str}"


def _enrich_bibliography_with_approved_papers(
    sanitized_refs: List[Dict[str, Any]],
    approved_papers: List[Dict[str, Any]],
    user_query: str = "",
) -> List[Dict[str, Any]]:
    """Ensure all approved papers evaluated during the review are included in the bibliography."""
    if not approved_papers:
        return sanitized_refs

    def _norm(s: str) -> str:
        return " ".join(str(s or "").lower().split())

    seen_identifiers: Set[str] = set()
    for ref in sanitized_refs:
        ref_title = _norm(ref.get("title") or "")
        if ref_title:
            seen_identifiers.add(ref_title)
        ref_key = _norm(ref.get("citation_key") or "")
        if ref_key:
            seen_identifiers.add(ref_key)

    enriched = list(sanitized_refs)
    for p in approved_papers:
        p_title = (p.get("title") or "").strip()
        if not p_title:
            continue
        norm_title = _norm(p_title)
        if norm_title in seen_identifiers:
            continue

        # Check if any seen title is substring / fuzzy match to avoid duplicates
        already_present = False
        for seen in seen_identifiers:
            if len(norm_title) >= 10 and len(seen) >= 10:
                if norm_title in seen or seen in norm_title:
                    already_present = True
                    break
        if already_present:
            continue

        authors = p.get("authors") or []
        if isinstance(authors, str):
            authors = [a.strip() for a in authors.split(",") if a.strip()]
        year = p.get("year")
        url = p.get("url") or p.get("pdf_url") or ""
        if not url and p.get("arxiv_id"):
            url = f"https://arxiv.org/abs/{p['arxiv_id']}"
        elif not url and p.get("doi"):
            url = f"https://doi.org/{p['doi']}"

        cite_key = _generate_citation_key(p)
        abstract = (p.get("abstract") or "").strip()
        summary = (
            (abstract[:180] + "...")
            if len(abstract) > 180
            else (abstract or f"Evaluated research paper in {user_query or 'literature review'}.")
        )

        enriched.append(
            {
                "title": p_title,
                "citation_key": cite_key,
                "summary": summary,
                "authors": authors,
                "year": year,
                "url": url,
                "matched_passage": "",
            }
        )
        seen_identifiers.add(norm_title)

    return enriched


def _extract_retry_delay(err: Exception) -> float:
    """Extract recommended retry delay seconds from Google RPC 429 quota failure, defaulting to 42.0s."""
    err_str = str(err)
    match = re.search(r"retry in (\d+(?:\.\d+)?)s", err_str, re.IGNORECASE)
    if match:
        return float(match.group(1)) + 2.0
    match = re.search(r"retryDelay': '(\d+)s'", err_str)
    if match:
        return float(match.group(1)) + 2.0
    return 42.0


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

    # 3. Assemble synthesis input prompt payload (complete approved corpus)
    papers_context = []
    for idx, p in enumerate(approved_papers, start=1):
        title = p.get("title", "Untitled").strip()
        authors = p.get("authors")
        year = p.get("year")
        abstract = (p.get("abstract") or "").strip()
        url = p.get("url") or p.get("pdf_url") or ""
        doi = p.get("doi") or ""
        arxiv_id = p.get("arxiv_id") or ""

        header_parts = [f"[{idx}] Paper: {title}"]
        if authors:
            auth_str = ", ".join(authors) if isinstance(authors, list) else str(authors)
            header_parts.append(f"Authors: {auth_str}")
        if year:
            header_parts.append(f"Year: {year}")
        if arxiv_id:
            header_parts.append(f"arXiv: {arxiv_id}")
        if doi:
            header_parts.append(f"DOI: {doi}")
        if url:
            header_parts.append(f"URL: {url}")

        header = " | ".join(header_parts)
        abstract_excerpt = str(abstract)[:1200] if abstract else "No abstract provided."
        paper_block = [header, f"Abstract: {abstract_excerpt}"]

        # Attach extracted section excerpts directly to this paper
        content = _resolve_paper_extracted_content(p, extracted_pdf_contents)
        if isinstance(content, dict) and content:
            methodology = (
                content.get("methodology")
                or content.get("methods")
                or (content.get("sections") or {}).get("methods", "")
                or (content.get("sections") or {}).get("methodology", "")
            )
            results = content.get("results") or (content.get("sections") or {}).get("results", "")
            if methodology:
                paper_block.append(f"Methodology Excerpt: {str(methodology)[:500]}")
            if results:
                paper_block.append(f"Results Excerpt: {str(results)[:500]}")

        papers_context.append("\n".join(paper_block))

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
    for r in verified_references:
        claim = r.get("claim", "")
        quote = r.get("matched_passage", "")
        p_title = r.get("paper_id_or_title", "")
        if claim:
            refs_context.append(f'- [{p_title}] Claim: {claim} (Grounding Quote: "{quote}")')

    # Audit Trail Context from Agent 08 (safeguard against unverified assertions)
    audit_context = []
    if has_hallucinations or rejected_claims:
        audit_context.append("PRIOR VERIFICATION AUDIT TRAIL:")
        audit_context.append("- Status: Preliminary assertions evaluated for grounding.")
        if verification_summary:
            audit_context.append(f"- Verifier Assessment: {verification_summary}")
        if rejected_claims:
            audit_context.append(
                "- REJECTED ASSERTIONS (DO NOT PRESENT AS FACT IN FINAL SYNTHESIS):"
            )
            for rc in rejected_claims:
                rc_claim = rc.get("claim", "")
                if rc_claim:
                    audit_context.append(f'  * "{rc_claim}"')

    num_approved = len(approved_papers)
    target_clusters = (
        "5 to 8" if num_approved >= 15 else ("3 to 5" if num_approved >= 5 else "2 to 4")
    )
    scale_instruction = (
        f"CORPUS SCALE: {num_approved} Approved Research Papers.\n"
        f"REQUIREMENT: Synthesize an exhaustive academic literature review spanning "
        f"{target_clusters} detailed thematic chapters with multi-paragraph comparative depth. "
        f"EVERY approved paper in the corpus must be evaluated and cited in-text using [Author, Year] "
        f"across the thematic clusters and included in the references bibliography."
    )

    user_content_sections = [
        f"RESEARCH TOPIC / USER QUERY:\n{user_query}",
        scale_instruction,
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
        "Synthesize a cohesive, comprehensive, publication-grade academic literature review adhering strictly to the guidelines.\n"
        "MANDATORY FORMATTING: Separate distinct paragraphs in executive_summary, thematic cluster summaries, and conclusion with double newlines ('\\n\\n') to ensure high visual readability."
    )

    user_content = "\n\n".join(user_content_sections)

    try:
        # 4. Call Google Gemini LLM with structured Pydantic schema and model fallback cascade
        client = genai.Client(
            api_key=settings.GEMINI_API_KEY,
            http_options={"api_version": "v1beta"},
        )
        candidate_models = settings.gemini_model_candidates

        parsed_output = None
        last_model_error = None
        model_errors: list[str] = []

        for model_name in candidate_models:
            max_model_retries = 2
            for attempt in range(max_model_retries + 1):
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=[SYNTHESIS_SYSTEM_PROMPT, user_content],
                        config={
                            "response_mime_type": "application/json",
                            "response_schema": SynthesizedReviewOutput,
                            "max_output_tokens": 8192,
                        },
                    )
                    parsed_output = SynthesizedReviewOutput.model_validate_json(response.text)
                    break
                except Exception as model_err:
                    err_str = str(model_err)
                    is_rate_limit = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str
                    if is_rate_limit and attempt < max_model_retries:
                        delay = _extract_retry_delay(model_err)
                        logger.warning(
                            f"Gemini Free Tier TPM rate limit reached on '{model_name}' "
                            f"(attempt {attempt + 1}/{max_model_retries + 1}). "
                            f"Pausing for {delay:.1f}s until token quota resets..."
                        )
                        await asyncio.sleep(delay)
                        continue

                    logger.warning(
                        f"Gemini model '{model_name}' failed during report synthesis ({model_err}); trying fallback."
                    )
                    model_errors.append(f"{model_name}: {model_err}")
                    last_model_error = model_err
                    break

            if parsed_output is not None:
                break

        if parsed_output is None:
            details_str = " | ".join(model_errors) if model_errors else str(last_model_error)
            raise RuntimeError(
                f"All configured Gemini models {candidate_models} failed during report synthesis. Details: {details_str}"
            )

        # 5. Validate and ground references before publishing
        sanitized_refs = _sanitize_references(
            references=parsed_output.references,
            verified_references=verified_references,
            approved_papers=approved_papers,
            extracted_pdf_contents=extracted_pdf_contents,
        )

        # 6. Enrich bibliography to ensure all evaluated approved papers are represented
        complete_refs = _enrich_bibliography_with_approved_papers(
            sanitized_refs=sanitized_refs,
            approved_papers=approved_papers,
            user_query=user_query,
        )

        synthesized_dict = {
            "title": parsed_output.title,
            "executive_summary": parsed_output.executive_summary,
            "thematic_clusters": [tc.model_dump() for tc in parsed_output.thematic_clusters],
            "methodology_matrix": [mm.model_dump() for mm in parsed_output.methodology_matrix],
            "research_gaps": parsed_output.research_gaps,
            "conclusion": parsed_output.conclusion,
            "references": complete_refs,
        }

        logger.info(
            f"Successfully synthesized literature review: '{parsed_output.title}' with "
            f"{len(parsed_output.thematic_clusters)} thematic clusters, {len(parsed_output.research_gaps)} gaps, "
            f"and {len(complete_refs)} bibliography references."
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
