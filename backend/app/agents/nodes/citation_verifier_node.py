"""Agent 08: Anti-Hallucination Citation Verifier Node."""

import logging
from typing import Any, Dict, List

from google import genai

from app.agents.state import AgentState
from app.core.config import settings
from app.schemas.agent_outputs import CitationVerificationOutput
from app.services.groq_service import call_groq_structured

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

    gemini_key = getattr(settings, "GEMINI_API_KEY", "")
    groq_key = getattr(settings, "GROQ_API_KEY", "")

    # 2. Strict Fail-Fast if neither Gemini nor Groq API key is configured
    if not gemini_key and not groq_key:
        error_msg = (
            "GEMINI_API_KEY is not configured (and GROQ_API_KEY fallback not configured); "
            "cannot execute citation verification."
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    # 3. Compile unified source paper knowledge base (deduplicated by paper)
    unique_sources: Dict[str, str] = {}
    for paper in approved_papers:
        title = paper.get("title", "").strip()
        if not title:
            continue
        abstract = paper.get("abstract", "").strip()
        content = _resolve_paper_extracted_content(paper, extracted_pdf_contents)

        sections = [f"Title: {title}"]
        chosen_abstract = (
            content.get("abstract")
            if (isinstance(content, dict) and content.get("abstract"))
            else abstract
        )
        if chosen_abstract:
            sections.append(f"Abstract: {chosen_abstract}")

        if isinstance(content, dict):
            methodology = (
                content.get("methodology")
                or content.get("methods")
                or (content.get("sections") or {}).get("methods", "")
                or (content.get("sections") or {}).get("methodology", "")
            )
            results = content.get("results") or (content.get("sections") or {}).get("results", "")
            if methodology:
                sections.append(f"Methodology: {str(methodology)[:1200]}")
            if results:
                sections.append(f"Results: {str(results)[:1000]}")

        unique_sources[title] = "\n".join(sections)

    # Include any extracted contents keyed by identifiers not already mapped
    for p_id, content in extracted_pdf_contents.items():
        if not isinstance(content, dict):
            continue
        p_title = content.get("title") or str(p_id)
        if p_title not in unique_sources:
            sections = [f"Title: {p_title}"]
            if content.get("abstract"):
                sections.append(f"Abstract: {content['abstract']}")
            methodology = (
                content.get("methodology")
                or content.get("methods")
                or (content.get("sections") or {}).get("methods", "")
            )
            results = content.get("results") or (content.get("sections") or {}).get("results", "")
            if methodology:
                sections.append(f"Methodology: {str(methodology)[:1200]}")
            if results:
                sections.append(f"Results: {str(results)[:1000]}")
            unique_sources[p_title] = "\n".join(sections)

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

    for gap in research_gaps:
        claims_to_verify.append(f"Paper: Cross-Study Analysis\nClaim: Research Gap: {gap}")

    if not claims_to_verify:
        return {
            "verified_references": [],
            "rejected_claims": [],
            "has_hallucinations": False,
            "verification_summary": "No claims formulated for citation verification.",
            "current_step": "citation_verification_completed",
        }

    # 5. Format prompt with claims and source paper text across all unique sources
    sources_text = "\n\n---\n\n".join(
        f"SOURCE PAPER: {k.upper()}\n{v}" for k, v in unique_sources.items()
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
        parsed_output = None
        last_model_error = None
        model_errors: list[str] = []

        # 6a. Attempt Google Gemini LLM cascade if configured
        if gemini_key:
            try:
                client = genai.Client(
                    api_key=gemini_key,
                    http_options={"api_version": "v1beta"},
                )
                candidate_models = getattr(
                    settings, "gemini_model_candidates", ["gemini-3.1-flash-lite"]
                )

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
                        parsed_output = CitationVerificationOutput.model_validate_json(
                            response.text
                        )
                        break
                    except Exception as model_err:
                        logger.warning(
                            f"Gemini model '{model_name}' failed during citation verification ({model_err}); trying fallback."
                        )
                        model_errors.append(f"{model_name}: {model_err}")
                        last_model_error = model_err
            except Exception as client_err:
                logger.warning(f"Gemini client initialization failed: {client_err}")
                model_errors.append(f"client_init: {client_err}")
                last_model_error = client_err

        # 6b. Fallback to Groq Cloud LLM if Gemini failed or was unconfigured
        if parsed_output is None and groq_key:
            logger.info("Attempting citation verification via Groq fallback LLM...")
            try:
                parsed_output = await call_groq_structured(
                    system_prompt=CITATION_VERIFICATION_PROMPT,
                    user_prompt=user_content,
                    response_schema=CitationVerificationOutput,
                )
            except Exception as groq_err:
                logger.warning(f"Groq fallback failed during citation verification: {groq_err}")
                model_errors.append(f"groq: {groq_err}")
                last_model_error = groq_err

        if parsed_output is None:
            details_str = " | ".join(model_errors) if model_errors else str(last_model_error)
            raise RuntimeError(f"All configured LLM providers failed. Details: {details_str}")

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
