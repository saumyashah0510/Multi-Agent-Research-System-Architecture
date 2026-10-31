"""Agent 01: Query Expansion and Domain Classifier Node."""

import logging
from typing import Any, Dict

from google import genai

from app.agents.state import AgentState
from app.core.config import settings
from app.schemas.agent_outputs import QueryExpansionOutput

logger = logging.getLogger(__name__)

QUERY_EXPANSION_SYSTEM_PROMPT = """You are a Senior Academic Research Specialist and Literature Discovery Expert.
Your task is to take a research topic submitted by a researcher and deconstruct it into targeted, high-precision search queries optimized for academic search engines (arXiv, PubMed, Semantic Scholar, Crossref).

Guidelines:
1. Target Domains: Identify 2 to 4 formal scientific disciplines or arXiv/PubMed subject tags (e.g., 'cs.AI', 'cs.LG', 'quant-ph', 'q-bio.BM', 'biomedical', 'physics').
2. Search Queries: Generate 3 to 5 distinct, high-impact academic search phrases:
   - Query 1: Core foundational methodology and theoretical framework.
   - Query 2: Specific algorithms, architectures, or computational models.
   - Query 3: Empirical benchmarks, comparative evaluation, or datasets.
   - Query 4 & 5: Domain-specific applications, edge cases, or experimental implementations.
3. Query Formatting Rules:
   - Use technical academic vocabulary and standard scientific acronyms (e.g., 'VQE molecular docking', 'transformer attention sparsity').
   - NEVER use conversational filler words (do NOT include 'papers about', 'find recent work', 'a study of').
   - Keep each query between 3 to 8 words for optimal retrieval against academic paper titles and abstracts.
"""


async def query_expansion_node(state: AgentState) -> Dict[str, Any]:
    """Expand user research query into 3-5 targeted sub-queries and classify domains."""
    user_query = state.get("user_query", "").strip()

    # 1. Fail-fast if query is empty or whitespace
    if not user_query:
        error_msg = "user_query cannot be empty. Please provide a research topic."
        logger.error(error_msg)
        raise ValueError(error_msg)

    # 2. Fail-fast if Gemini API key is missing
    if not settings.GEMINI_API_KEY:
        error_msg = "GEMINI_API_KEY is not configured; cannot execute query expansion."
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    try:
        # 3. Call Google Gemini LLM with structured Pydantic schema and model fallback cascade
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        candidate_models = settings.gemini_model_candidates
        user_content = (
            f"Research Topic: {user_query}\n\n"
            "Deconstruct this topic into academic target domains and 3-5 search queries."
        )

        parsed_output = None
        last_model_error = None

        for model_name in candidate_models:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[QUERY_EXPANSION_SYSTEM_PROMPT, user_content],
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": QueryExpansionOutput,
                    },
                )
                parsed_output = QueryExpansionOutput.model_validate_json(response.text)
                break
            except Exception as model_err:
                logger.warning(
                    f"Gemini model '{model_name}' failed during query expansion ({model_err}); trying fallback."
                )
                last_model_error = model_err

        if parsed_output is None:
            raise RuntimeError(
                f"All configured Gemini models {candidate_models} failed. Last error: {last_model_error}"
            )

        # Ensure search_queries is never empty
        queries = parsed_output.search_queries
        if not queries:
            queries = [user_query]

        domains = parsed_output.target_domains
        if not domains:
            domains = ["Computer Science"]

        return {
            "target_domains": domains,
            "search_queries": queries,
            "current_step": "query_expansion_completed",
        }

    except Exception as exc:
        logger.error(f"Error executing Gemini Query Expansion: {exc}", exc_info=True)
        # Strict Fail-Fast: surface the error directly
        raise RuntimeError(f"Query expansion failed due to LLM error: {exc}") from exc
