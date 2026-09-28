"""Unit and integration tests for FastAPI core engine and endpoints.

Assignee Task (Issue #1 / Issue BE-02):
- Implement test_health_check_returns_200 verifying HTTP status 200 and healthy payload with database status.
"""

from unittest.mock import AsyncMock

import pytest
from app.db.session import get_db
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Fixture to provide a FastAPI TestClient with mocked database session."""

    async def override_get_db():
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health_check_returns_200(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """Verify GET /api/v1/health returns HTTP 200 and expected health check payload."""

    async def mock_redis_ok():
        return True

    monkeypatch.setattr("app.api.v1.health.check_redis_connection", mock_redis_ok)

    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "multi-agent-research-backend"
    assert data["version"] == "1.0.0"
    assert data["database"] == "connected"
    assert data["redis"] == "connected"


def test_health_check_db_disconnected(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """Verify GET /api/v1/health returns degraded status when database ping fails."""

    async def override_get_db_failure():
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("DB Connection Failed")
        yield mock_session

    async def mock_redis_ok():
        return True

    monkeypatch.setattr("app.api.v1.health.check_redis_connection", mock_redis_ok)
    app.dependency_overrides[get_db] = override_get_db_failure
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["database"] == "disconnected"
    assert data["redis"] == "connected"
    app.dependency_overrides.clear()


def test_create_review_task(client: TestClient):
    """Verify POST /api/v1/reviews/ accepts query and returns accepted review_id."""
    payload = {
        "query": "CRISPR Gene Editing in Cancer Therapy",
        "citation_format": "APA",
        "max_papers": 20,
    }
    response = client.post("/api/v1/reviews/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert "review_id" in data


def test_get_review_status(client: TestClient):
    """Verify GET /api/v1/reviews/{review_id} returns review status."""
    response = client.get("/api/v1/reviews/review-123")
    assert response.status_code == 200
    data = response.json()
    assert data["review_id"] == "review-123"
    assert data["status"] == "user_approval_pending"
    assert "screened_papers" in data


def test_approve_papers(client: TestClient):
    """Verify POST /api/v1/reviews/{review_id}/approve accepts approved paper IDs."""
    payload = {
        "user_decision": "continue",
        "approved_paper_ids": ["arxiv-2301.01234", "arxiv-2305.09876"],
    }
    response = client.post("/api/v1/reviews/review-123/approve", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"
    assert data["review_id"] == "review-123"
