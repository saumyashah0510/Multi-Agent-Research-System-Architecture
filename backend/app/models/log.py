"""Agent execution log ORM model.

Assignee Task (Issue BE-03):
- Define columns: id (Integer primary key), agent_name (String), message (Text), timestamp (DateTime).
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


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
