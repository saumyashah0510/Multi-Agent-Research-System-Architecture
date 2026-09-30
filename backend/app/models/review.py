"""Literature review task session ORM model.

Assignee Task (Issue BE-03):
- Define columns: id (Integer/UUID primary key), user_query (String), status (String), created_at (DateTime).
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.paper import Paper
    from app.models.user import User


class LiteratureReview(Base):
    """Literature Review session model storing user research queries and pipeline state."""

    __tablename__ = "literature_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_query: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    synthesized_review: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="reviews")
    papers: Mapped[List["Paper"]] = relationship(
        "Paper", back_populates="review", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<LiteratureReview(id={self.id}, status='{self.status}')>"
