"""Literature review task session ORM model.

Assignee Task (Issue BE-03):
- Define columns: id (Integer/UUID primary key), user_query (String), status (String), created_at (DateTime).
"""

from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.paper import Paper


class LiteratureReview(Base):
    """Literature Review session model storing user research queries and pipeline state."""

    __tablename__ = "literature_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_query: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    papers: Mapped[List["Paper"]] = relationship(
        "Paper", back_populates="review", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<LiteratureReview(id={self.id}, status='{self.status}')>"
