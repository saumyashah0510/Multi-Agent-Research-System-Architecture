"""Pydantic schemas for Academic Paper data transfer objects."""

from pydantic import BaseModel


class PaperResponse(BaseModel):
    """Schema for paper detail responses."""

    title: str
    authors: list[str]
    abstract: str
    arxiv_id: str | None = None
    relevance_score: float | None = None
    is_approved: bool = False
