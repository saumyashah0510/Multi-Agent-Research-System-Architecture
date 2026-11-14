"""Audit Logging Pydantic Schemas for Review Execution Timeline.

Assignee Task (Issue BE-17):
- Define ReviewLogItem representing an individual agent lifecycle event.
- Define ReviewAuditTimelineResponse wrapping the chronological event stream.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ReviewLogItem(BaseModel):
    """Individual agent execution log record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    review_id: int
    agent_name: str = Field(
        ..., description="Name of the agent or node (e.g. query_expansion, pdf_extractor)"
    )
    status: str = Field(..., description="Lifecycle status (started, running, completed, failed)")
    message: str = Field(..., description="Human-readable summary of what the agent performed")
    payload: Optional[Dict[str, Any]] = Field(
        None, description="Structured metrics, counts, or latency data"
    )
    created_at: datetime


class ReviewAuditTimelineResponse(BaseModel):
    """Full chronological audit timeline for a literature review session."""

    review_id: int
    total_events: int
    logs: List[ReviewLogItem]


class ExecutionLogItem(BaseModel):
    """System-wide operational diagnostic log record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_name: str
    message: str
    timestamp: datetime
