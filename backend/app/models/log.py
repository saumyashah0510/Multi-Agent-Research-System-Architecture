"""Agent execution log ORM model placeholder.

Assignee Task (Issue BE-03):
- Define columns: id (Integer primary key), agent_name (String), message (Text), timestamp (DateTime).
"""

from app.db.base import Base


# TODO (Assignee - Database Engineer): Define ExecutionLog model columns for agent audit logging
class ExecutionLog(Base):
    """Execution log table model placeholder."""

    __tablename__ = "execution_logs"
