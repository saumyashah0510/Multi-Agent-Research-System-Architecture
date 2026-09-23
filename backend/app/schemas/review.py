"""Pydantic schemas for Literature Review request/response."""

from pydantic import BaseModel


class ReviewCreateRequest(BaseModel):
    """Schema for initiating a new literature review task."""

    query: str
    max_papers: int = 20
