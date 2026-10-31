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
            "current_step": "citation_verification_completed",
        }

    # 2. Strict Fail-Fast if GEMINI_API_KEY is not configured
    if not settings.GEMINI_API_KEY:
        error_msg = "GEMINI_API_KEY is not configured; cannot execute citation verification."
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    # 3. Compile source paper knowledge base
    paper_sources: Dict[str, str] = {}
    for paper in approved_papers:
        title = paper.get("title", "").strip()
        abstract = paper.get("abstract", "").strip()
        if title:
            paper_sources[title.lower()] = f"Title: {title}\nAbstract: {abstract}"

    for p_id, content in extracted_pdf_contents.items():
        if isinstance(content, dict):
            sections = []
            if content.get("abstract"):
                sections.append(f"Abstract: {content['abstract']}")
            if content.get("methodology"):
                sections.append(f"Methodology: {content['methodology'][:1200]}")
            if content.get("results"):
                sections.append(f"Results: {content['results'][:1000]}")
            text_rep = "\n".join(sections)
            paper_sources[p_id.lower()] = text_rep

    # 4. Formulate claims to verify from methodology matrix and gaps
    claims_to_verify = []
    for m in methodology_matrix:
        method = m.get("method_name", "Method")
        papers = m.get("papers_used", [])
        strengths = m.get("strengths", [])
        limitations = m.get("limitations", [])

        target_paper = papers[0] if papers else "General Literature"
        if strengths:
            claims_to_verify.append(
                f"Paper: {target_paper}\nClaim: {method} exhibits strength: {'; '.join(strengths)}"
            )
        if limitations:
            claims_to_verify.append(
                f"Paper: {target_paper}\nClaim: {method} exhibits limitation: {'; '.join(limitations)}"
            )

    for gap in research_gaps[:3]:
        claims_to_verify.append(f"Paper: Cross-Study Analysis\nClaim: Research Gap: {gap}")

    if not claims_to_verify:
        return {
            "verified_references": [],
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

        # 7. Retain only substantiated citations to protect downstream report synthesis
        verified_refs = [
            citation.model_dump()
            for citation in parsed_output.verified_citations
            if citation.is_supported
        ]

        logger.info(
            f"Citation verification complete: {len(verified_refs)} of "
            f"{len(parsed_output.verified_citations)} claims verified (Hallucinations detected: {parsed_output.has_hallucinations})."
        )

        return {
            "verified_references": verified_refs,
            "current_step": "citation_verification_completed",
        }

    except Exception as exc:
        logger.error(f"Error executing Gemini Citation Verification: {exc}", exc_info=True)
        raise RuntimeError(f"Citation verification failed due to LLM error: {exc}") from exc


# Alias for flexible naming
citation_verifier_node = citation_verification_node
