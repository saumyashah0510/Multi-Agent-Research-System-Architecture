"""Academic paper text chunk ORM model for pgvector storage."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.paper import Paper


class PaperChunk(Base):
    """Stores text chunks and vector embeddings of academic papers for pgvector RAG synthesis."""

    __tablename__ = "paper_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    section_name: Mapped[str] = mapped_column(String(150), nullable=False, default="Full Text")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(384), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    paper: Mapped["Paper"] = relationship("Paper", back_populates="chunks")

    def __repr__(self) -> str:
        return (
            f"<PaperChunk(id={self.id}, paper_id={self.paper_id}, "
            f"section='{self.section_name}', chunk_index={self.chunk_index})>"
        )
