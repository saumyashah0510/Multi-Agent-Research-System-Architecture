"""Groq Cloud LLM Service for fallback inference and structured outputs."""

import json
import logging
from typing import Any, Dict, List, Optional, Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"


def _clean_json_string(raw_text: str) -> str:
    """Strip markdown code block fences and surrounding whitespace."""
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


async def call_groq_structured(
    system_prompt: str,
    user_prompt: str,
    response_schema: Type[T],
    models: Optional[List[str]] = None,
    max_tokens: int = 4096,
    temperature: float = 0.2,
) -> T:
    """Call Groq API with candidate model cascade and return validated Pydantic model.

    Args:
        system_prompt: Guiding system instructions.
        user_prompt: User/context prompt to evaluate.
        response_schema: Target Pydantic model class to validate output against.
        models: Optional list of Groq model IDs. Defaults to settings.groq_model_candidates.
        max_tokens: Maximum tokens in generated completion.
        temperature: Sampling temperature (lower = more deterministic).

    Returns:
        Validated instance of response_schema (T).

    Raises:
        RuntimeError: If GROQ_API_KEY is unset or all candidate models fail.
    """
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured; cannot call Groq.")

    candidate_models = models or settings.groq_model_candidates
    schema_dict = response_schema.model_json_schema()

    augmented_system = (
        f"{system_prompt}\n\n"
        f"MANDATORY OUTPUT FORMAT: You MUST return a single, valid JSON object that strictly adheres "
        f"to the following JSON Schema:\n"
        f"{json.dumps(schema_dict, indent=2)}\n\n"
        f"CRITICAL: Do not enclose your response in Markdown backticks (e.g. ```json). "
        f"Do not output any preamble, explanation, or notes. Output ONLY the raw JSON object."
    )

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY.strip()}",
        "Content-Type": "application/json",
    }

    last_error: Optional[Exception] = None
    model_errors: List[str] = []

    for model_name in candidate_models:
        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": augmented_system},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    GROQ_CHAT_COMPLETIONS_URL,
                    headers=headers,
                    json=payload,
                )

                if response.status_code != 200:
                    err_msg = f"Groq HTTP {response.status_code}: {response.text}"
                    logger.warning(f"Groq model '{model_name}' failed: {err_msg}")
                    model_errors.append(f"{model_name}: {err_msg}")
                    last_error = RuntimeError(err_msg)
                    continue

                data = response.json()
                choices = data.get("choices", [])
                if not choices:
                    err_msg = f"Groq response contained no choices: {data}"
                    logger.warning(err_msg)
                    model_errors.append(f"{model_name}: {err_msg}")
                    last_error = RuntimeError(err_msg)
                    continue

                raw_content = choices[0].get("message", {}).get("content", "")
                cleaned_json = _clean_json_string(raw_content)

                try:
                    parsed = response_schema.model_validate_json(cleaned_json)
                    logger.info(
                        f"Successfully generated structured response via Groq model '{model_name}'."
                    )
                    return parsed
                except ValidationError as val_err:
                    err_msg = f"Groq output validation failed for model '{model_name}': {val_err}"
                    logger.warning(err_msg)
                    model_errors.append(f"{model_name}: {err_msg}")
                    last_error = val_err
                    continue

        except Exception as exc:
            err_msg = f"Groq invocation error for '{model_name}': {exc}"
            logger.warning(err_msg)
            model_errors.append(f"{model_name}: {err_msg}")
            last_error = exc

    summary_errors = " | ".join(model_errors) if model_errors else str(last_error)
    raise RuntimeError(
        f"All configured Groq models {candidate_models} failed. Details: {summary_errors}"
    )
