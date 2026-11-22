"""Unit tests for Agent Audit Logging & Timeline Endpoint (Issue BE-17)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.api.deps import get_current_user_optional, get_db
from app.api.v1.reviews import _safe_record_audit_event
from app.main import app
from app.models.log import ExecutionLog, ReviewLog
from app.models.review import LiteratureReview
from app.models.user import User
from app.schemas.audit import ReviewAuditTimelineResponse, ReviewLogItem
from app.services.audit_service import AuditService
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def clean_dependency_overrides():
    """Ensure FastAPI dependency overrides do not leak between tests."""
    yield
    app.dependency_overrides.clear()


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


class FakeAuditDB:
    """In-memory async database session for testing AuditService persistence."""

    def __init__(self):
        self.logs: list[ReviewLog] = []
        self.execution_logs: list[ExecutionLog] = []
        self.added = []
        self._next_id = 1
        self.commit = AsyncMock()
        self.rollback = AsyncMock()

    def add(self, item):
        self.added.append(item)
        if isinstance(item, ReviewLog):
            if item.id is None:
                item.id = self._next_id
                self._next_id += 1
            if getattr(item, "created_at", None) is None:
                item.created_at = datetime.now(timezone.utc)
            self.logs.append(item)
        elif isinstance(item, ExecutionLog):
            if item.id is None:
                item.id = self._next_id
                self._next_id += 1
            if getattr(item, "timestamp", None) is None:
                item.timestamp = datetime.now(timezone.utc)
            self.execution_logs.append(item)

    async def refresh(self, item):
        # Emulate DB refresh assigning id and created_at if unset
        if item.id is None:
            item.id = self._next_id
            self._next_id += 1
        if isinstance(item, ReviewLog) and getattr(item, "created_at", None) is None:
            item.created_at = datetime.now(timezone.utc)

    async def execute(self, statement):
        mock_result = MagicMock()
        # Sort logs chronologically
        sorted_logs = sorted(
            [log for log in self.logs],
            key=lambda entry: (entry.created_at or datetime.min, entry.id or 0),
        )
        mock_result.scalars.return_value.all.return_value = sorted_logs
        return mock_result


@pytest.mark.asyncio
async def test_audit_timeline_database_persistence():
    """Verify that AuditService inserts and retrieves chronological logs from Neon DB."""
    fake_db = FakeAuditDB()
    base_time = datetime(2026, 11, 22, 10, 0, 0, tzinfo=timezone.utc)

    # 1. Record stage 1: query_expansion
    log1 = await AuditService.record_review_event(
        db=fake_db,
        review_id=42,
        agent_name="query_expansion",
        status="completed",
        message="Expanded into 4 academic sub-queries",
        payload={"sub_queries": ["q1", "q2", "q3", "q4"], "duration_s": 1.2},
    )
    assert log1 is not None
    assert log1.review_id == 42
    assert log1.agent_name == "query_expansion"
    log1.created_at = base_time

    # 2. Record stage 2: paper_discovery
    log2 = await AuditService.record_review_event(
        db=fake_db,
        review_id=42,
        agent_name="paper_discovery",
        status="completed",
        message="Discovered 30 papers across arXiv and PubMed",
        payload={"total_count": 30, "arxiv_count": 20, "pubmed_count": 10},
    )
    assert log2 is not None
    assert log2.review_id == 42
    assert log2.agent_name == "paper_discovery"
    log2.created_at = base_time + timedelta(seconds=10)

    # 3. Record stage 3: screening
    log3 = await AuditService.record_review_event(
        db=fake_db,
        review_id=42,
        agent_name="screening",
        status="completed",
        message="Screened 15 relevant papers",
        payload={"screened_count": 15, "passed_count": 15, "failed_count": 15},
    )
    assert log3 is not None
    log3.created_at = base_time + timedelta(seconds=20)

    # 4. Record stage 4: human_interrupt
    log4 = await AuditService.record_review_event(
        db=fake_db,
        review_id=42,
        agent_name="human_interrupt",
        status="paused",
        message="Awaiting human-in-the-loop candidate paper selection",
        payload={"candidate_count": 15},
    )
    assert log4 is not None
    log4.created_at = base_time + timedelta(seconds=30)

    # 5. Retrieve audit timeline
    timeline = await AuditService.get_review_audit_timeline(db=fake_db, review_id=42)

    assert len(timeline) == 4
    assert [entry.agent_name for entry in timeline] == [
        "query_expansion",
        "paper_discovery",
        "screening",
        "human_interrupt",
    ]
    assert (
        timeline[0].created_at
        <= timeline[1].created_at
        <= timeline[2].created_at
        <= timeline[3].created_at
    )
    assert timeline[0].payload["duration_s"] == 1.2
    assert timeline[1].payload["arxiv_count"] == 20
    fake_db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_record_review_event_db_failure_recovers_gracefully():
    """Verify that transient database failures are handled safely without crashing."""
    mock_db = MagicMock()
    mock_db.commit = AsyncMock(side_effect=Exception("Neon DB connection timeout"))
    mock_db.rollback = AsyncMock()

    result = await AuditService.record_review_event(
        db=mock_db,
        review_id=99,
        agent_name="pdf_extraction",
        status="completed",
        message="Extracted sections from 5 papers",
        payload={"cached_count": 5},
    )

    # Should catch gracefully and return None
    assert result is None
    mock_db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_and_get_system_execution_logs():
    """Verify global ExecutionLog persistence and chronological retrieval."""
    mock_db = MagicMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    # Test insertion
    log = await AuditService.record_execution_event(
        db=mock_db,
        agent_name="system_monitor",
        message="System check passed",
    )
    assert log is not None
    assert log.agent_name == "system_monitor"
    assert log.message == "System check passed"
    mock_db.commit.assert_awaited_once()

    # Test retrieval
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [log]
    mock_db.execute = AsyncMock(return_value=mock_result)

    logs = await AuditService.get_system_execution_logs(db=mock_db, limit=10)
    assert len(logs) == 1
    assert logs[0].agent_name == "system_monitor"


def test_get_review_audit_endpoint_not_found():
    """Calling GET /api/v1/reviews/{id}/audit on non-existent review returns 404."""
    client = TestClient(app)

    async def override_get_db():
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    response = client.get("/api/v1/reviews/99999/audit")
    assert response.status_code == 404
    assert response.json()["detail"] == "Literature review not found"


def test_get_review_audit_endpoint_success():
    """Calling GET /api/v1/reviews/{id}/audit on existing review returns 200 with timeline."""
    client = TestClient(app)
    now = datetime.now(timezone.utc)

    test_review = LiteratureReview(
        id=123,
        user_query="Quantum Error Correction",
        status="completed",
        user_id=None,
        created_at=now,
    )

    log_entry_1 = ReviewLog(
        id=1,
        review_id=123,
        agent_name="query_expansion",
        status="completed",
        message="Expanded 5 search queries",
        payload={"queries_count": 5, "duration_s": 1.1},
        created_at=now,
    )
    log_entry_2 = ReviewLog(
        id=2,
        review_id=123,
        agent_name="report_synthesis",
        status="completed",
        message="Literature review synthesized",
        payload={"chapters_generated": 6},
        created_at=now + timedelta(seconds=15),
    )

    async def override_get_db():
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = test_review
        mock_db.execute = AsyncMock(return_value=mock_result)
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    with patch.object(
        AuditService,
        "get_review_audit_timeline",
        new=AsyncMock(return_value=[log_entry_1, log_entry_2]),
    ):
        response = client.get("/api/v1/reviews/123/audit")
        assert response.status_code == 200
        data = response.json()
        assert data["review_id"] == 123
        assert data["total_events"] == 2
        assert len(data["logs"]) == 2
        assert data["logs"][0]["agent_name"] == "query_expansion"
        assert data["logs"][0]["status"] == "completed"
        assert data["logs"][0]["payload"]["queries_count"] == 5
        assert data["logs"][1]["agent_name"] == "report_synthesis"
        assert data["logs"][1]["payload"]["chapters_generated"] == 6


def test_get_review_audit_endpoint_access_control_forbidden():
    """Users cannot view audit timeline for reviews owned by other users (403 Forbidden)."""
    client = TestClient(app)
    now = datetime.now(timezone.utc)

    # Review belongs to user 10
    review_user_10 = LiteratureReview(
        id=200,
        user_query="Deep Learning",
        status="completed",
        user_id=10,
        created_at=now,
    )

    # Current authenticated user is user 99
    current_user_99 = User(
        id=99,
        email="intruder@example.com",
        name="Intruder",
        hashed_password="pw",
        is_active=True,
    )

    async def override_get_db():
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = review_user_10
        mock_db.execute = AsyncMock(return_value=mock_result)
        yield mock_db

    async def override_get_user():
        return current_user_99

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_optional] = override_get_user

    response = client.get("/api/v1/reviews/200/audit")
    assert response.status_code == 403
    assert response.json()["detail"] == "You do not have permission to access this review."


@pytest.mark.asyncio
async def test_safe_record_audit_event_resilience(monkeypatch):
    """Verify that _safe_record_audit_event suppresses any underlying session or DB exception."""
    mock_session_context = MagicMock()
    mock_session_context.__aenter__ = AsyncMock(side_effect=Exception("Database pool down"))
    mock_session_context.__aexit__ = AsyncMock(return_value=False)

    monkeypatch.setattr(
        "app.api.v1.reviews.AsyncSessionLocal",
        lambda: mock_session_context,
    )

    # Must complete safely without raising an exception
    await _safe_record_audit_event(
        review_id=999,
        agent_name="screening",
        status="completed",
        message="Screened papers",
        payload={"count": 10},
    )
