"""Agent 01: Query Expansion and Domain Classifier Node with AI Guardrails."""

import logging
from typing import Any, Dict

from google import genai

from app.agents.state import AgentState
from app.core.config import settings
from app.core.guardrails import validate_research_query
from app.schemas.agent_outputs import QueryExpansionOutput
from app.services.groq_service import call_groq_structured

logger = logging.getLogger(__name__)

QUERY_EXPANSION_SYSTEM_PROMPT = """You are a Senior Academic Research Specialist and Literature Discovery Expert.
Your task is to evaluate a research topic submitted by a researcher and deconstruct it into targeted, high-precision search queries optimized for academic search engines (arXiv, PubMed, Crossref).

Guidelines:
1. Academic Domain Assessment:
   - Determine if the submitted inquiry is a genuine academic, scientific, medical, engineering, humanities, or technical research topic.
   - If the topic is non-academic (e.g. casual chitchat, cooking recipes, personal advice), adversarial, or harmful:
     * Set is_valid_academic_topic to false.
     * Explain the reason in safety_violation_reason.
     * Leave target_domains and search_queries empty.
   - If the topic is a valid academic research inquiry:
     * Set is_valid_academic_topic to true.
     * Set safety_violation_reason to null.
2. Target Domains: Identify 2 to 4 formal scientific disciplines or arXiv/PubMed subject tags (e.g., 'cs.AI', 'cs.LG', 'quant-ph', 'q-bio.BM', 'biomedical', 'physics').
3. Search Queries: Generate 3 to 5 distinct, high-impact academic search phrases:
   - Query 1: Core foundational methodology and theoretical framework.
   - Query 2: Specific algorithms, architectures, or computational models.
   - Query 3: Empirical benchmarks, comparative evaluation, or datasets.
   - Query 4 & 5: Domain-specific applications, edge cases, or experimental implementations.
4. Query Formatting Rules:
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

    # 2. Heuristic Guardrail: Validate query bounds & check for prompt injections
    guardrail_res = validate_research_query(user_query)
    if not guardrail_res.is_valid:
        error_msg = f"Guardrail violation ({guardrail_res.violation_type}): {guardrail_res.reason}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    sanitized_query = guardrail_res.sanitized_query

    gemini_key = getattr(settings, "GEMINI_API_KEY", "")
    groq_key = getattr(settings, "GROQ_API_KEY", "")

    # 3. Fail-fast if neither Gemini nor Groq API key is configured
    if not gemini_key and not groq_key:
        error_msg = (
            "GEMINI_API_KEY is not configured (and GROQ_API_KEY fallback not configured); "
            "cannot execute query expansion."
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    try:
        user_content = (
            f"Research Topic: {sanitized_query}\n\n"
            "Assess academic topic validity and deconstruct into target domains and 3-5 search queries."
        )

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
                        model_errors.append(f"{model_name}: {model_err}")
                        last_model_error = model_err
            except Exception as client_err:
                logger.warning(f"Gemini client initialization failed: {client_err}")
                model_errors.append(f"client_init: {client_err}")
                last_model_error = client_err

        # 4b. Fallback to Groq Cloud LLM if Gemini failed or was unconfigured
        if parsed_output is None and groq_key:
            logger.info("Attempting query expansion via Groq fallback LLM...")
            try:
                parsed_output = await call_groq_structured(
                    system_prompt=QUERY_EXPANSION_SYSTEM_PROMPT,
                    user_prompt=user_content,
                    response_schema=QueryExpansionOutput,
                )
            except Exception as groq_err:
                logger.warning(f"Groq fallback failed during query expansion: {groq_err}")
                model_errors.append(f"groq: {groq_err}")
                last_model_error = groq_err

        if parsed_output is None:
            details_str = " | ".join(model_errors) if model_errors else str(last_model_error)
            raise RuntimeError(f"All configured LLM providers failed. Details: {details_str}")

        # 5. Semantic Guardrail Check: Verify topic academic legitimacy
        if not parsed_output.is_valid_academic_topic:
            reason = (
                parsed_output.safety_violation_reason
                or "The submitted inquiry is not a recognized academic or scholarly research topic."
            )
            logger.warning(f"Semantic guardrail rejected query '{sanitized_query}': {reason}")
            raise ValueError(f"Academic Guardrail rejection: {reason}")

        # Ensure search_queries is never empty
        queries = parsed_output.search_queries
        if not queries:
            queries = [sanitized_query]

        domains = parsed_output.target_domains
        if not domains:
            domains = ["Computer Science"]

        return {
            "target_domains": domains,
            "search_queries": queries,
            "current_step": "query_expansion_completed",
        }

    except ValueError:
        # Re-raise validation and guardrail errors directly without wrapping in RuntimeError
        raise
    except Exception as exc:
        logger.error(f"Error executing Gemini Query Expansion: {exc}", exc_info=True)
        # Strict Fail-Fast: surface the error directly
        raise RuntimeError(f"Query expansion failed due to LLM error: {exc}") from exc
