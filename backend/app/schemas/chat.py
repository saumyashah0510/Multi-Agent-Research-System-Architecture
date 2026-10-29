"""Pydantic schemas for RAG Literature Review Chat endpoint.

Assignee Task (Issue BE-10):
- Define ChatMessage schema for conversation history
- Define ChatRequest schema with question and optional history
- Define CitationSource schema for retrieved paper chunks
- Define ChatResponse schema with answer and citations list
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Single chat turn in conversation history."""

    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Text content of message")


class CitationSource(BaseModel):
    """Source paper chunk citation retrieved via pgvector."""

    paper_id: int
    title: Optional[str] = None
    section_name: str
    chunk_index: int
    snippet: str


class ChatRequest(BaseModel):
    """Incoming user chat query."""

    question: str = Field(..., min_length=1, description="User question about the review")
    history: List[ChatMessage] = Field(
        default_factory=list, description="Previous conversation turns"
    )


class ChatResponse(BaseModel):
    """RAG chat answer generated from paper contexts."""

    answer: str
    citations: List[CitationSource] = Field(default_factory=list)
