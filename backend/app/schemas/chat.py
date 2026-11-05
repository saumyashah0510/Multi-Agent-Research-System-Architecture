"""Pydantic schemas for RAG Literature Review Chat endpoint."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Single chat turn in conversation history."""

    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1)


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
