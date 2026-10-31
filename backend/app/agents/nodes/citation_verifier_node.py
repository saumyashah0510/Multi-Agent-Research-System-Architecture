"""Agent 08: Anti-Hallucination Citation Verifier Node."""

import logging
from typing import Any, Dict, List

from google import genai

from app.agents.state import AgentState
from app.core.config import settings
from app.schemas.agent_outputs import CitationVerificationOutput

logger = logging.getLogger(__name__)

CITATION_VERIFICATION_PROMPT = """You are an Adversarial Academic Fact-Checker and Citation Verification Auditor.
Your sole purpose is to rigorously detect and eliminate hallucinated citations, fabricated statistics, and unsupported assertions in scientific literature reviews.

Guidelines:
1. Strict Natural Language Inference (NLI):
   - A claim is 'is_supported = True' IF AND ONLY IF the source text explicitly corroborates the methodology, quantitative metrics, or empirical findings stated in the claim.
   - If the source text does not mention the claim, contradicts it, or if the paper never tested what is claimed, set 'is_supported = False'.
2. Evidence Extraction ('matched_passage'):
   - If supported, extract a direct verbatim or near-verbatim quote from the provided source text that substantiates the assertion.
   - If unsupported, set 'matched_passage' to 'No supporting evidence found in source text.'
3. Confidence Scoring:
   - 0.90 - 1.00: Direct verbatim or quantitative evidence matches claim precisely.
   - 0.70 - 0.89: Strongly entailed or paraphrased by the source text.
   - 0.00 - 0.69: Weak inference, partial contradiction, or ungrounded assertion.
4. Hallucination Flagging:
   - Set 'has_hallucinations' to True if ANY claim is unsupported.
   - Provide a concise 'verification_summary' assessing the fidelity of the claims.
"""


async def citation_verification_node(state: AgentState) -> Dict[str, Any]:
    """Verify synthesized claims against source paper texts to prevent hallucinations."""
    methodology_matrix: List[Dict[str, Any]] = state.get("methodology_matrix") or []
    research_gaps: List[str] = state.get("research_gaps") or []
    extracted_pdf_contents: Dict[str, Any] = state.get("extracted_pdf_contents") or {}
    approved_papers: List[Dict[str, Any]] = state.get("approved_papers") or []

    # 1. Clean return if no source materials are available
    if not methodology_matrix and not research_gaps:
        logger.info("No claims or methodology matrix available for citation verification.")
        return {
            "verified_references": [],
            "rejected_claims": [],
            "has_hallucinations": False,
            "verification_summary": "No claims or methodology matrix available for citation verification.",
            "current_step": "citation_verification_completed",
        }

    # 2. Strict Fail-Fast if GEMINI_API_KEY is not configured
    if not settings.GEMINI_API_KEY:
        error_msg = "GEMINI_API_KEY is not configured; cannot execute citation verification."
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    # 3. Compile unified source paper knowledge base (linking IDs and titles)
    id_to_paper: Dict[str, Dict[str, Any]] = {}
    for paper in approved_papers:
        if paper.get("arxiv_id"):
            id_to_paper[str(paper["arxiv_id"]).lower()] = paper
        if paper.get("doi"):
            id_to_paper[str(paper["doi"]).lower()] = paper
        if paper.get("title"):
            id_to_paper[paper["title"].strip().lower()] = paper

    paper_sources: Dict[str, str] = {}
    for paper in approved_papers:
        title = paper.get("title", "").strip()
        abstract = paper.get("abstract", "").strip()
        p_id = paper.get("arxiv_id") or paper.get("doi") or title

        # Check extracted content by ID or title
        content = (
            extracted_pdf_contents.get(p_id)
            or extracted_pdf_contents.get(str(paper.get("arxiv_id", "")))
            or extracted_pdf_contents.get(title)
            or extracted_pdf_contents.get(title.lower())
            or {}
        )

        sections = [f"Title: {title}"]
        if abstract or (isinstance(content, dict) and content.get("abstract")):
            chosen_abstract = (
                content.get("abstract")
                if isinstance(content, dict) and content.get("abstract")
                else abstract
            )
            sections.append(f"Abstract: {chosen_abstract}")
        if isinstance(content, dict):
            methodology = content.get("methodology") or content.get("methods") or ""
            results = content.get("results") or ""
            if methodology:
                sections.append(f"Methodology: {methodology[:1200]}")
            if results:
                sections.append(f"Results: {results[:1000]}")

        text_rep = "\n".join(sections)
        if title:
            paper_sources[title.lower()] = text_rep
        if paper.get("arxiv_id"):
            paper_sources[str(paper["arxiv_id"]).lower()] = text_rep
        if paper.get("doi"):
            paper_sources[str(paper["doi"]).lower()] = text_rep

    # Include any extracted contents keyed by identifiers not already mapped
    for p_id, content in extracted_pdf_contents.items():
        norm_pid = str(p_id).lower()
        if norm_pid not in paper_sources and isinstance(content, dict):
            matched_paper = id_to_paper.get(norm_pid)
            p_title = matched_paper.get("title", p_id) if matched_paper else p_id
            sections = [f"Title: {p_title}"]
            if content.get("abstract"):
                sections.append(f"Abstract: {content['abstract']}")
            if content.get("methodology"):
                sections.append(f"Methodology: {content['methodology'][:1200]}")
            if content.get("results"):
                sections.append(f"Results: {content['results'][:1000]}")
            paper_sources[norm_pid] = "\n".join(sections)

    # 4. Formulate claims to verify from methodology matrix and gaps
    claims_to_verify = []
    for m in methodology_matrix:
        method = m.get("method_name", "Method")
        papers = m.get("papers_used", [])
        strengths = m.get("strengths", [])
        limitations = m.get("limitations", [])

        target_paper = ", ".join(papers) if papers else "General Literature"
        for strength in strengths:
            if strength and strength.strip():
                claims_to_verify.append(
                    f"Paper: {target_paper}\nClaim: {method} exhibits strength: {strength.strip()}"
                )
        for limitation in limitations:
            if limitation and limitation.strip():
                claims_to_verify.append(
                    f"Paper: {target_paper}\nClaim: {method} exhibits limitation: {limitation.strip()}"
                )

    for gap in research_gaps[:3]:
        claims_to_verify.append(f"Paper: Cross-Study Analysis\nClaim: Research Gap: {gap}")

    if not claims_to_verify:
        return {
            "verified_references": [],
            "rejected_claims": [],
            "has_hallucinations": False,
            "verification_summary": "No claims formulated for citation verification.",
            "current_step": "citation_verification_completed",
        }

    # 5. Format prompt with claims and source paper text
    sources_text = "\n\n---\n\n".join(
        f"SOURCE PAPER: {k.upper()}\n{v}" for k, v in list(paper_sources.items())[:6]
    )
    claims_text = "\n\n".join(f"[{idx}] {c}" for idx, c in enumerate(claims_to_verify, 1))

    user_content = (
        f"SOURCE TEXT EXCERPTS:\n\n{sources_text}\n\n"
        f"CLAIMS TO VERIFY:\n\n{claims_text}\n\n"
        "Audit each claim against the source text excerpts. "
        "Strictly enforce source attribution: evidence from one paper cannot substantiate a claim attributed to a different paper. "
        "Extract verbatim quotes for supported claims and flag any unsupported or fabricated assertions."
    )

    try:
        # 6. Call Google Gemini LLM with structured Pydantic schema and model fallback cascade
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        candidate_models = settings.gemini_model_candidates

        parsed_output = None
        last_model_error = None

        for model_name in candidate_models:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[CITATION_VERIFICATION_PROMPT, user_content],
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": CitationVerificationOutput,
                    },
                )
                parsed_output = CitationVerificationOutput.model_validate_json(response.text)
                break
            except Exception as model_err:
                logger.warning(
                    f"Gemini model '{model_name}' failed during citation verification ({model_err}); trying fallback."
                )
                last_model_error = model_err

        if parsed_output is None:
            raise RuntimeError(
                f"All configured Gemini models {candidate_models} failed during citation verification. Last error: {last_model_error}"
            )

        # 7. Retain substantiated citations and record rejected claims for audit trail
        verified_refs = [
            citation.model_dump()
            for citation in parsed_output.verified_citations
            if citation.is_supported and citation.confidence >= 0.70
        ]
        rejected_claims = [
            citation.model_dump()
            for citation in parsed_output.verified_citations
            if not citation.is_supported or citation.confidence < 0.70
        ]

        has_hallucinations = parsed_output.has_hallucinations or len(rejected_claims) > 0

        logger.info(
            f"Citation verification complete: {len(verified_refs)} verified, "
            f"{len(rejected_claims)} rejected (Hallucinations: {has_hallucinations})."
        )

        return {
            "verified_references": verified_refs,
            "rejected_claims": rejected_claims,
            "has_hallucinations": has_hallucinations,
            "verification_summary": parsed_output.verification_summary,
            "current_step": "citation_verification_completed",
        }

    except Exception as exc:
        logger.error(f"Error executing Gemini Citation Verification: {exc}", exc_info=True)
        raise RuntimeError(f"Citation verification failed due to LLM error: {exc}") from exc


# Alias for flexible naming
citation_verifier_node = citation_verification_node
