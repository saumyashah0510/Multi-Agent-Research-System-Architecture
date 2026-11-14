"""Agent execution and literature review checkpoint log ORM models."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.review import LiteratureReview


class ExecutionLog(Base):
    """Execution log table model storing agent lifecycle events and audit records."""

    __tablename__ = "execution_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    agent_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<ExecutionLog(id={self.id}, agent='{self.agent_name}')>"


class ReviewLog(Base):
    """Checkpoint log model storing the history of a literature review."""

    __tablename__ = "review_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("literature_reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    review: Mapped["LiteratureReview"] = relationship(
        "LiteratureReview", back_populates="review_logs"
    )

    def __repr__(self) -> str:
        return f"<ReviewLog(id={self.id}, review_id={self.review_id}, agent='{self.agent_name}')>"
