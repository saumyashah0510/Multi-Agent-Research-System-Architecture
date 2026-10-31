"""Agent 07: Methodology Comparison & Gap Analysis Node."""

import logging
from typing import Any, Dict, List

from google import genai

from app.agents.state import AgentState
from app.core.config import settings
from app.schemas.agent_outputs import GapAnalysisOutput

logger = logging.getLogger(__name__)

GAP_ANALYSIS_SYSTEM_PROMPT = """You are a Distinguished Academic Research Methodologist and Systematic Review Director.
Your task is to conduct a comparative methodological analysis across a corpus of scientific papers and identify unaddressed literature gaps based on the researcher's topic.

Guidelines:
1. Methodology Matrix:
   - Identify distinct algorithmic architectures, experimental protocols, or theoretical frameworks used across the analyzed papers.
   - For each distinct methodology:
     - 'method_name': Precise technical label (e.g., 'Variational Quantum Eigensolver (VQE)', 'Graph Neural Networks (GNN)').
     - 'papers_used': List of titles of papers that employed or benchmarked this methodology.
     - 'strengths': 2-3 specific technical strengths, convergence properties, or benchmark advantages.
     - 'limitations': 2-3 bottlenecks, computational overheads, noise sensitivity, or scalability constraints.
2. Literature Research Gaps:
   - Identify 3 to 5 critical unaddressed challenges or research voids across the analyzed literature.
   - Focus on:
     * Discrepancies or conflicting findings across benchmark studies.
     * Theoretical vs. empirical gaps (e.g., lack of real-world biological validation vs. synthetic datasets).
     * Missing architectural integration or lack of standardized evaluation frameworks.
   - Formulate each gap as a clear, rigorous research question suitable for future doctoral or grant proposal investigation.
"""


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

    # 2. Strict Fail-Fast if GEMINI_API_KEY is not configured
    if not settings.GEMINI_API_KEY:
        error_msg = "GEMINI_API_KEY is not configured; cannot execute gap analysis."
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    # 3. Assemble paper text representations for the comparative prompt
    corpus_blocks = []
    for idx, paper in enumerate(approved_papers, 1):
        title = paper.get("title", f"Paper {idx}").strip()
        paper_id = paper.get("arxiv_id") or paper.get("doi") or title

        # Check if full section text exists in extracted_pdf_contents
        content = extracted_pdf_contents.get(paper_id) or extracted_pdf_contents.get(title) or {}
        if isinstance(content, dict) and content:
            methodology = content.get("methodology") or content.get("methods") or ""
            results = content.get("results") or ""
            abstract = content.get("abstract") or paper.get("abstract", "")
            block = (
                f"[{idx}] Title: {title}\n"
                f"Abstract: {abstract}\n"
                f"Methodology Excerpt: {methodology[:1200]}\n"
                f"Results Excerpt: {results[:800]}"
            )
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
        # 4. Call Google Gemini LLM with structured Pydantic schema and model fallback cascade
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        candidate_models = settings.gemini_model_candidates

        parsed_output = None
        last_model_error = None

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
                last_model_error = model_err

        if parsed_output is None:
            raise RuntimeError(
                f"All configured Gemini models {candidate_models} failed during gap analysis. Last error: {last_model_error}"
            )

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
