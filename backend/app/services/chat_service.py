"""RAG Literature Review Chat Service.

Assignee Task (Issue BE-10):
- Define RAG_CHAT_SYSTEM_PROMPT with strict anti-hallucination and citation rules
- Implement generate_rag_chat_response(question, contexts, history) calling Gemini LLM
"""

from typing import Any, Dict, List

# TODO (Assignee - BE-10): Define system prompt for RAG Literature Review Chat:
# RAG_CHAT_SYSTEM_PROMPT = """..."""


async def generate_rag_chat_response(
    question: str,
    contexts: List[Dict[str, Any]],
    history: List[Dict[str, str]],
) -> Dict[str, Any]:
    """Generate answer grounded in retrieved paper chunks.

    TODO (Assignee - BE-10):
    1. Format retrieved chunks into context string with paper titles & sections
    2. Build messages list including previous conversation history
    3. Call Gemini LLM (gemini-3.1-flash-lite)
    4. Return dict with 'answer' and 'citations'
    """
    # Placeholder return for BE-10 starter
    return {
        "answer": "This is a placeholder answer. Implement LLM generation in BE-10.",
        "citations": [],
    }
