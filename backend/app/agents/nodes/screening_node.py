"""Agent 03: Screening and Relevance Scoring Node."""

import logging
from typing import Any, Dict, List

from google import genai

from app.agents.state import AgentState
from app.core.config import settings
from app.schemas.agent_outputs import ScreeningOutput

logger = logging.getLogger(__name__)

SCREENING_SYSTEM_PROMPT = """You are a Senior Academic Peer Reviewer and Literature Screening Specialist.
Your task is to evaluate candidate scientific papers for inclusion or exclusion in a systematic literature review based on the researcher's topic.

Guidelines:
1. Relevance Scoring (0.0 to 1.0):
   - 0.85 - 1.00: Highly relevant; directly addresses the core methodologies, novel architectures, or key benchmark datasets of the topic.
   - 0.60 - 0.84: Moderately relevant; provides adjacent theoretical frameworks, empirical comparisons, or domain-specific applications.
   - 0.00 - 0.59: Irrelevant or tangential; discusses peripheral topics, wrong domain, or mentions keywords only in passing.
2. Acceptance Threshold:
   - Set 'accepted' to True if and only if relevance_score >= 0.60.
   - Set 'accepted' to False if relevance_score < 0.60.
3. Rationale:
   - Provide a concise, rigorous 1-sentence justification ('reason') explaining why the paper was accepted or excluded based on its methodology, domain, or objectives.
"""


async def screening_node(state: AgentState) -> Dict[str, Any]:
    """Score candidate paper abstracts and filter out those below the 0.6 threshold."""
    user_query = state.get("user_query", "").strip()
    discovered_papers: List[Dict[str, Any]] = state.get("discovered_papers") or []

    # 1. Fallback if no candidate papers were discovered
    if not discovered_papers:
        logger.warning("No discovered_papers found in AgentState for screening.")
        return {
            "screened_papers": [],
            "current_step": "screening_completed",
        }

    # 2. Strict Fail-Fast if GEMINI_API_KEY is not configured
    if not settings.GEMINI_API_KEY:
        error_msg = "GEMINI_API_KEY is not configured; cannot execute paper screening."
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    try:
        # 3. Format candidate papers for the LLM prompt
        papers_context_blocks = []
        for idx, paper in enumerate(discovered_papers, 1):
            title = paper.get("title", f"Paper {idx}").strip()
            abstract = paper.get("abstract", "No abstract available.").strip()
            papers_context_blocks.append(f"[{idx}] Title: {title}\nAbstract: {abstract}")

        candidate_text = "\n\n".join(papers_context_blocks)
        user_content = (
            f"Research Topic: {user_query}\n\n"
            f"Candidate Papers to Screen ({len(discovered_papers)} total):\n\n"
            f"{candidate_text}\n\n"
            "Evaluate each candidate paper against the research topic and provide structured screening decisions."
        )

        # 4. Call Google Gemini LLM with structured Pydantic schema and model fallback cascade
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        candidate_models = settings.gemini_model_candidates

        parsed_output = None
        last_model_error = None

        for model_name in candidate_models:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[SCREENING_SYSTEM_PROMPT, user_content],
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": ScreeningOutput,
                    },
                )
                parsed_output = ScreeningOutput.model_validate_json(response.text)
                break
            except Exception as model_err:
                logger.warning(
                    f"Gemini model '{model_name}' failed during screening ({model_err}); trying fallback."
                )
                last_model_error = model_err

        if parsed_output is None:
            raise RuntimeError(
                f"All configured Gemini models {candidate_models} failed. Last error: {last_model_error}"
            )

        # 5. Map decisions by index or normalized title back to original papers
        decision_map = {}
        for decision in parsed_output.decisions:
            norm_key = decision.paper_id_or_title.strip().lower()
            decision_map[norm_key] = decision

        screened_papers: List[Dict[str, Any]] = []
        for idx, paper in enumerate(discovered_papers, 1):
            title = paper.get("title", "").strip()
            norm_title = title.lower()

            # Attempt to match by exact title, paper index marker, or list index
            decision = (
                decision_map.get(norm_title)
                or decision_map.get(f"[{idx}]")
                or decision_map.get(f"paper {idx}")
                or (
                    parsed_output.decisions[idx - 1]
                    if idx - 1 < len(parsed_output.decisions)
                    else None
                )
            )

            score = decision.relevance_score if decision else 0.5
            reason = decision.reason if decision else "No detailed evaluation returned by model."
            is_accepted = score >= 0.60

            if is_accepted:
                p_copy = dict(paper)
                p_copy["relevance_score"] = round(score, 3)
                p_copy["screening_reason"] = reason
                screened_papers.append(p_copy)

        logger.info(
            f"Screening complete: {len(screened_papers)} of {len(discovered_papers)} papers accepted (>= 0.60)."
        )

        return {
            "screened_papers": screened_papers,
            "current_step": "screening_completed",
        }

    except Exception as exc:
        logger.error(f"Error during Gemini paper screening: {exc}", exc_info=True)
        # Strict Fail-Fast: surface the error directly so pipeline execution halts cleanly
        raise RuntimeError(f"Paper screening failed due to LLM error: {exc}") from exc


# Alias for backward compatibility
screening_agent_node = screening_node
