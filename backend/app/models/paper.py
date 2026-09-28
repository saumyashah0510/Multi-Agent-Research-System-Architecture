"""Academic paper metadata and vector embedding ORM model.

Assignee Task (Issue BE-03):
- Define columns: id (Integer primary key), title (String), authors (String/JSON),
  abstract (Text), published_year (Integer), arxiv_id (String),
  relevance_score (Float), is_approved (Boolean),
  review_id (ForeignKey to literature_reviews.id).
"""

from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.review import LiteratureReview


class Paper(Base):
    """Academic paper metadata table storing retrieved paper details."""

    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    authors: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    arxiv_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    relevance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0.0)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    review_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("literature_reviews.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Relationships
    review: Mapped[Optional["LiteratureReview"]] = relationship(
        "LiteratureReview", back_populates="papers"
    )

    def __repr__(self) -> str:
        return f"<Paper(id={self.id}, title='{self.title[:30]}...', arxiv_id='{self.arxiv_id}')>"
