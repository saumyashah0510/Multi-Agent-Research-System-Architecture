"""Literature review task session ORM model."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.log import ReviewLog
    from app.models.paper import Paper
    from app.models.user import User


class ReviewStatus(str, Enum):
    """Lifecycle statuses for the literature review pipeline."""

    PENDING = "pending"
    QUERY_EXPANSION = "query_expansion"
    PAPER_DISCOVERY = "paper_discovery"
    SCREENING = "screening"
    AWAITING_USER_INPUT = "awaiting_user_input"
    PDF_EXTRACTION = "pdf_extraction"
    VECTOR_EMBEDDING = "vector_embedding"
    GAP_ANALYSIS = "gap_analysis"
    CITATION_VERIFICATION = "citation_verification"
    REPORT_SYNTHESIS = "report_synthesis"
    COMPLETED = "completed"
    FAILED = "failed"


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
    review_logs: Mapped[List["ReviewLog"]] = relationship(
        "ReviewLog",
        back_populates="review",
        cascade="all, delete-orphan",
        order_by="ReviewLog.created_at",
    )

    def __repr__(self) -> str:
        return f"<LiteratureReview(id={self.id}, status='{self.status}')>"
