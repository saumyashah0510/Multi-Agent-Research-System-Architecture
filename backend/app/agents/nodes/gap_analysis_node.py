"""Agent 07: Methodology Comparison & Gap Analysis Node."""

import logging
from typing import Any, Dict, List

from google import genai

from app.agents.state import AgentState
from app.core.config import settings
from app.schemas.agent_outputs import GapAnalysisOutput
from app.services.groq_service import call_groq_structured

logger = logging.getLogger(__name__)

GAP_ANALYSIS_SYSTEM_PROMPT = """You are a Distinguished Academic Research Methodologist and Systematic Review Director.
Your task is to conduct an exhaustive comparative methodological analysis across a corpus of scientific papers and identify unaddressed literature gaps based on the researcher's topic.

Guidelines:
1. Methodology Matrix:
   - Identify distinct algorithmic architectures, experimental protocols, or theoretical frameworks used across the analyzed papers (typically 5 to 10 distinct methodologies for comprehensive corpora).
   - For each distinct methodology:
     - 'method_name': Precise technical label (e.g., 'Multi-Agent Reinforcement Learning with Communication', 'Neuro-Symbolic Automated Theorem Proving').
     - 'papers_used': List of titles of papers that employed, benchmarked, or introduced this methodology.
     - 'strengths': 2-4 specific technical strengths, convergence properties, or benchmark advantages.
     - 'limitations': 2-4 bottlenecks, computational overheads, noise sensitivity, or scalability constraints.
2. Literature Research Gaps:
   - Identify 5 to 8 critical unaddressed challenges or research voids across the analyzed literature (or 3 to 5 for smaller corpora).
   - Focus on:
     * Discrepancies or conflicting findings across benchmark studies.
     * Theoretical vs. empirical gaps (e.g., lack of real-world physical/clinical validation vs. synthetic benchmarks).
     * Missing architectural integration, safety/alignment failures, or lack of standardized evaluation frameworks.
   - Formulate each gap as a clear, rigorous research question suitable for doctoral or grant proposal investigation.
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


async def gap_analysis_node(state: AgentState) -> Dict[str, Any]:
    """Compare methodologies across approved papers and identify literature gaps."""
    user_query = state.get("user_query", "").strip()
    approved_papers: List[Dict[str, Any]] = state.get("approved_papers") or []
    extracted_pdf_contents: Dict[str, Any] = state.get("extracted_pdf_contents") or {}

    # 1. Clean return if neither approved_papers nor extracted contents exist
    if not approved_papers and not extracted_pdf_contents:
        logger.info("No approved papers or extracted PDF contents found for gap analysis.")
        return {
            "methodology_matrix": [],
            "research_gaps": [],
            "current_step": "gap_analysis_completed",
        }

    gemini_key = getattr(settings, "GEMINI_API_KEY", "")
    groq_key = getattr(settings, "GROQ_API_KEY", "")

    # 2. Strict Fail-Fast if neither Gemini nor Groq API key is configured
    if not gemini_key and not groq_key:
        error_msg = (
            "GEMINI_API_KEY is not configured (and GROQ_API_KEY fallback not configured); "
            "cannot execute gap analysis."
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    # 3. Assemble paper text representations for the comparative prompt
    corpus_blocks = []
    for idx, paper in enumerate(approved_papers, 1):
        title = paper.get("title", f"Paper {idx}").strip()
        content = _resolve_paper_extracted_content(paper, extracted_pdf_contents)

        if isinstance(content, dict) and content:
            methodology = (
                content.get("methodology")
                or content.get("methods")
                or (content.get("sections") or {}).get("methods", "")
                or (content.get("sections") or {}).get("methodology", "")
            )
            results = content.get("results") or (content.get("sections") or {}).get("results", "")
            abstract = content.get("abstract") or paper.get("abstract", "")
            block_parts = [f"[{idx}] Title: {title}", f"Abstract: {abstract}"]
            if methodology:
                block_parts.append(f"Methodology Excerpt: {str(methodology)[:1200]}")
            if results:
                block_parts.append(f"Results Excerpt: {str(results)[:800]}")
            block = "\n".join(block_parts)
        else:
            abstract = paper.get("abstract") or "No abstract provided."
            block = f"[{idx}] Title: {title}\nAbstract: {abstract}"
        corpus_blocks.append(block)

    # Handle edge case where extracted_pdf_contents has papers not in approved_papers list
    if not corpus_blocks and extracted_pdf_contents:
        for p_id, content in extracted_pdf_contents.items():
            if isinstance(content, dict):
                abstract = content.get("abstract", "")
                methods = content.get("methodology", "")
                corpus_blocks.append(
                    f"Title/ID: {p_id}\nAbstract: {abstract}\nMethods: {methods[:1000]}"
                )

    user_content = (
        f"Research Topic: {user_query}\n\n"
        f"Analyzed Scientific Literature ({len(corpus_blocks)} papers):\n\n"
        + "\n\n".join(corpus_blocks)
        + "\n\nGenerate the structured methodology matrix and 3-5 literature research gaps."
    )

    try:
        parsed_output = None
        last_model_error = None
        model_errors: list[str] = []

        # 4a. Attempt Google Gemini LLM cascade if configured
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
                            contents=[GAP_ANALYSIS_SYSTEM_PROMPT, user_content],
                            config={
                                "response_mime_type": "application/json",
                                "response_schema": GapAnalysisOutput,
                            },
                        )
                        parsed_output = GapAnalysisOutput.model_validate_json(response.text)
                        break
                    except Exception as model_err:
                        logger.warning(
                            f"Gemini model '{model_name}' failed during gap analysis ({model_err}); trying fallback."
                        )
                        model_errors.append(f"{model_name}: {model_err}")
                        last_model_error = model_err
            except Exception as client_err:
                logger.warning(f"Gemini client initialization failed: {client_err}")
                model_errors.append(f"client_init: {client_err}")
                last_model_error = client_err

        # 4b. Fallback to Groq Cloud LLM if Gemini failed or was unconfigured
        if parsed_output is None and groq_key:
            logger.info("Attempting gap analysis via Groq fallback LLM...")
            try:
                parsed_output = await call_groq_structured(
                    system_prompt=GAP_ANALYSIS_SYSTEM_PROMPT,
                    user_prompt=user_content,
                    response_schema=GapAnalysisOutput,
                )
            except Exception as groq_err:
                logger.warning(f"Groq fallback failed during gap analysis: {groq_err}")
                model_errors.append(f"groq: {groq_err}")
                last_model_error = groq_err

        if parsed_output is None:
            details_str = " | ".join(model_errors) if model_errors else str(last_model_error)
            raise RuntimeError(f"All configured LLM providers failed. Details: {details_str}")

        matrix_dicts = [item.model_dump() for item in parsed_output.methodology_matrix]
        gaps_list = parsed_output.research_gaps

        logger.info(
            f"Gap analysis complete: identified {len(matrix_dicts)} methodologies and {len(gaps_list)} research gaps."
        )

        return {
            "methodology_matrix": matrix_dicts,
            "research_gaps": gaps_list,
            "current_step": "gap_analysis_completed",
        }

    except Exception as exc:
        logger.error(f"Error executing Gemini Gap Analysis: {exc}", exc_info=True)
        raise RuntimeError(f"Gap analysis failed due to LLM error: {exc}") from exc
