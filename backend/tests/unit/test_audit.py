"""Unit tests for Agent Audit Logging & Timeline Endpoint (Issue BE-17)."""

from datetime import datetime, timezone

import pytest
from app.schemas.audit import ReviewAuditTimelineResponse, ReviewLogItem


def test_review_log_item_schema_validation():
    """Verify that ReviewLogItem validates milestone payload accurately."""
    item = ReviewLogItem(
        id=1,
        review_id=181,
        agent_name="query_expansion",
        status="completed",
        message="Expanded 5 search queries",
        payload={"queries_count": 5, "duration_s": 1.2},
        created_at=datetime.now(timezone.utc),
    )
    assert item.review_id == 181
    assert item.agent_name == "query_expansion"
    assert item.payload["queries_count"] == 5


def test_timeline_response_schema_validation():
    """Verify that ReviewAuditTimelineResponse aggregates logs properly."""
    now = datetime.now(timezone.utc)
    item1 = ReviewLogItem(
        id=1,
        review_id=181,
        agent_name="query_expansion",
        status="completed",
        message="Expanded queries",
        payload={"count": 5},
        created_at=now,
    )
    item2 = ReviewLogItem(
        id=2,
        review_id=181,
        agent_name="pdf_extraction",
        status="completed",
        message="Extracted PDFs",
        payload={"count": 21},
        created_at=now,
    )

    response = ReviewAuditTimelineResponse(
        review_id=181,
        total_events=2,
        logs=[item1, item2],
    )
    assert response.review_id == 181
    assert response.total_events == 2
    assert len(response.logs) == 2


@pytest.mark.skip(reason="Assignee will unskip upon implementing DB audit query in BE-17")
@pytest.mark.asyncio
async def test_audit_timeline_database_persistence():
    """Verify that AuditService inserts and retrieves chronological logs from Neon DB."""
    pass
