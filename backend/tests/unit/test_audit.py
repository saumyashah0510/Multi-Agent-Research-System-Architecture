"""Unit tests for Agent Audit Logging & Timeline Endpoint (Issue BE-17)."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import app.api.v1.reviews as reviews_api
import pytest
from app.models.log import ReviewLog
from app.schemas.audit import ReviewAuditTimelineResponse, ReviewLogItem
from app.services.audit_service import AuditService
from fastapi import HTTPException


class FakeResult:
    """Minimal async SQLAlchemy scalar result."""

    def __init__(self, items):
        self._items = items

    def scalar_one_or_none(self):
        return (
            self._items
            if not isinstance(self._items, list)
            else (self._items[0] if self._items else None)
        )

    def scalars(self):
        class ScalarMock:
            def __init__(self, items):
                self._items = (
                    items if isinstance(items, list) else ([items] if items is not None else [])
                )

            def all(self):
                return self._items

        return ScalarMock(self._items)


class FakeDB:
    """Minimal async database session for unit tests."""

    def __init__(self, review=None, logs=None):
        self.review = review
        self.logs = logs or []
        self.added = []
        self.commit = AsyncMock()
        self.refresh = AsyncMock()
        self.rollback = AsyncMock()

    def add(self, item):
        self.added.append(item)

    async def execute(self, statement):
        sql_str = str(statement).lower()
        if "from review_logs" in sql_str:
            return FakeResult(self.logs)
        return FakeResult(self.review)


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


@pytest.mark.asyncio
async def test_audit_timeline_database_persistence():
    """Verify that AuditService inserts and retrieves chronological logs from Neon DB."""
    db = FakeDB()

    # 1. Test record_review_event inserts record and commits
    log_entry = await AuditService.record_review_event(
        db=db,
        review_id=181,
        agent_name="query_expansion",
        status="completed",
        message="Expanded 5 search queries",
        payload={"queries_count": 5, "duration_s": 1.2},
    )

    assert log_entry is not None
    assert log_entry.review_id == 181
    assert log_entry.agent_name == "query_expansion"
    assert log_entry.status == "completed"
    assert log_entry.message == "Expanded 5 search queries"
    assert log_entry.payload == {"queries_count": 5, "duration_s": 1.2}
    assert log_entry in db.added
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(log_entry)

    # 2. Test get_review_audit_timeline retrieves records
    db.logs = [log_entry]
    timeline = await AuditService.get_review_audit_timeline(db=db, review_id=181)
    assert len(timeline) == 1
    assert timeline[0].review_id == 181
    assert timeline[0].agent_name == "query_expansion"


@pytest.mark.asyncio
async def test_audit_service_handles_db_failure_gracefully():
    """Verify that AuditService catches exceptions without breaking the pipeline."""
    failing_db = AsyncMock()
    failing_db.add = MagicMock()
    failing_db.commit = AsyncMock(side_effect=Exception("Neon DB connection timeout"))
    failing_db.rollback = AsyncMock()

    result = await AuditService.record_review_event(
        db=failing_db,
        review_id=181,
        agent_name="pdf_extraction",
        status="completed",
        message="Extracted PDFs",
    )
    assert result is None
    failing_db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_audit_service_handles_invalid_review_id():
    """Verify that AuditService safely handles non-integer review IDs."""
    db = FakeDB()
    result = await AuditService.record_review_event(
        db=db,
        review_id="not-a-number",  # type: ignore[arg-type]
        agent_name="screening",
        status="completed",
        message="Test",
    )
    assert result is None

    timeline = await AuditService.get_review_audit_timeline(db=db, review_id="not-a-number")  # type: ignore[arg-type]
    assert timeline == []


@pytest.mark.asyncio
async def test_get_review_audit_endpoint_not_found():
    """Verify that GET /reviews/{id}/audit returns 404 for nonexistent review."""
    db = FakeDB(review=None)

    with pytest.raises(HTTPException) as exc_info:
        await reviews_api.get_review_audit(review_id=999999, db=db, current_user=None)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Literature review not found"


@pytest.mark.asyncio
async def test_get_review_audit_endpoint_success(monkeypatch):
    """Verify that GET /reviews/{id}/audit returns 200 with chronological audit timeline."""
    review = SimpleNamespace(id=181, user_id=None)
    now = datetime.now(timezone.utc)
    log1 = ReviewLog(
        id=1,
        review_id=181,
        agent_name="query_expansion",
        status="completed",
        message="Expanded 5 queries",
        payload={"count": 5},
        created_at=now,
    )
    log2 = ReviewLog(
        id=2,
        review_id=181,
        agent_name="pdf_extraction",
        status="completed",
        message="Extracted 10 PDFs",
        payload={"count": 10},
        created_at=now,
    )

    db = FakeDB(review=review, logs=[log1, log2])

    response = await reviews_api.get_review_audit(review_id=181, db=db, current_user=None)

    assert isinstance(response, ReviewAuditTimelineResponse)
    assert response.review_id == 181
    assert response.total_events == 2
    assert len(response.logs) == 2
    assert response.logs[0].agent_name == "query_expansion"
    assert response.logs[1].agent_name == "pdf_extraction"
    assert response.logs[1].status == "completed"
    assert response.logs[1].payload == {"count": 10}
