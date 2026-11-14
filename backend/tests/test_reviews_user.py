"""Unit tests for user-review multi-tenant isolation and access control.

Verifies:
- Authenticated user reviews are linked to user_id.
- Unauthenticated reviews remain user_id = None.
- List reviews returns only reviews belonging to the authenticated user.
- Users cannot view, approve, chat, or export reviews belonging to another user (HTTP 403).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.api.deps import get_current_user_optional, get_db
from app.main import app
from app.models.review import LiteratureReview, ReviewStatus
from app.models.user import User
from fastapi.testclient import TestClient


def _make_test_user(user_id: int, email: str = "user@example.com") -> User:
    user = User(
        id=user_id,
        email=email,
        hashed_password="hashed_pw_dummy",
        is_active=True,
    )
    return user


@pytest.fixture(autouse=True)
def clean_dependency_overrides():
    yield
    app.dependency_overrides.clear()


def test_create_review_authenticated_links_user_id():
    """Verify POST /api/v1/reviews/ associates review.user_id with the authenticated user."""
    client = TestClient(app)
    user_a = _make_test_user(user_id=42, email="author@example.com")

    async def override_get_user():
        return user_a

    app.dependency_overrides[get_current_user_optional] = override_get_user

    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    with patch("app.api.v1.reviews._run_initial_graph", new_callable=AsyncMock):
        response = client.post(
            "/api/v1/reviews/",
            json={
                "query": "Deep learning architectures for graph neural networks",
                "max_papers": 10,
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    # Verify LiteratureReview was added with user_id = 42
    added_review = mock_db.add.call_args[0][0]
    assert isinstance(added_review, LiteratureReview)
    assert added_review.user_id == 42


def test_create_review_unauthenticated_sets_user_id_none():
    """Verify POST /api/v1/reviews/ sets review.user_id to None when unauthenticated."""
    client = TestClient(app)

    async def override_get_user():
        return None

    app.dependency_overrides[get_current_user_optional] = override_get_user

    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    with patch("app.api.v1.reviews._run_initial_graph", new_callable=AsyncMock):
        response = client.post(
            "/api/v1/reviews/",
            json={
                "query": "Deep learning architectures for graph neural networks",
                "max_papers": 10,
            },
        )

    assert response.status_code == 200
    added_review = mock_db.add.call_args[0][0]
    assert isinstance(added_review, LiteratureReview)
    assert added_review.user_id is None


def test_list_reviews_authenticated_filters_to_user_id():
    """Verify GET /api/v1/reviews/ filters results by current_user.id."""
    client = TestClient(app)
    user_a = _make_test_user(user_id=101, email="user101@example.com")

    async def override_get_user():
        return user_a

    app.dependency_overrides[get_current_user_optional] = override_get_user

    mock_rev = LiteratureReview(
        id=1,
        user_query="Quantum computing review",
        status=ReviewStatus.COMPLETED.value,
        user_id=101,
        synthesized_review={"title": "Quantum Review"},
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_rev]

    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result
    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/api/v1/reviews/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "1"
    assert data[0]["query"] == "Quantum computing review"


def test_get_review_status_forbidden_for_other_user():
    """Verify GET /api/v1/reviews/{id} returns HTTP 403 when accessed by another user."""
    client = TestClient(app)
    user_b = _make_test_user(user_id=999, email="attacker@example.com")

    async def override_get_user():
        return user_b

    app.dependency_overrides[get_current_user_optional] = override_get_user

    # Review belongs to user 101, not 999
    owned_review = LiteratureReview(
        id=5,
        user_query="Private research topic",
        status=ReviewStatus.COMPLETED.value,
        user_id=101,
    )

    mock_db = AsyncMock()
    mock_db.get.return_value = owned_review
    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/api/v1/reviews/5")
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


def test_get_review_status_allowed_for_owner():
    """Verify GET /api/v1/reviews/{id} returns HTTP 200 when accessed by owner."""
    client = TestClient(app)
    user_a = _make_test_user(user_id=101, email="owner@example.com")

    async def override_get_user():
        return user_a

    app.dependency_overrides[get_current_user_optional] = override_get_user

    owned_review = LiteratureReview(
        id=5,
        user_query="My research topic",
        status=ReviewStatus.COMPLETED.value,
        user_id=101,
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []

    mock_db = AsyncMock()
    mock_db.get.return_value = owned_review
    mock_db.execute.return_value = mock_result
    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/api/v1/reviews/5")
    assert response.status_code == 200
    assert response.json()["id"] == "5"


def test_approve_review_forbidden_for_other_user():
    """Verify POST /api/v1/reviews/{id}/approve returns 403 for unauthorized users."""
    client = TestClient(app)
    user_b = _make_test_user(user_id=999, email="other@example.com")

    async def override_get_user():
        return user_b

    app.dependency_overrides[get_current_user_optional] = override_get_user

    owned_review = LiteratureReview(
        id=7,
        user_query="Private topic",
        status=ReviewStatus.AWAITING_USER_INPUT.value,
        user_id=101,
    )

    mock_db = AsyncMock()
    mock_db.get.return_value = owned_review
    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.post(
        "/api/v1/reviews/7/approve",
        json={"user_decision": "continue", "approved_paper_ids": ["paper_1"]},
    )
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


def test_export_pdf_forbidden_for_other_user():
    """Verify GET /api/v1/reviews/{id}/export returns 403 when review belongs to another user."""
    client = TestClient(app)
    user_b = _make_test_user(user_id=999, email="intruder@example.com")

    async def override_get_user():
        return user_b

    app.dependency_overrides[get_current_user_optional] = override_get_user

    owned_review = LiteratureReview(
        id=12,
        user_query="Proprietary research",
        status=ReviewStatus.COMPLETED.value,
        synthesized_review={"title": "Report"},
        user_id=101,
    )

    mock_db = AsyncMock()
    mock_db.get.return_value = owned_review
    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/api/v1/reviews/12/export")
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


def test_chat_forbidden_for_other_user():
    """Verify POST /api/v1/reviews/{id}/chat returns 403 when review belongs to another user."""
    client = TestClient(app)
    user_b = _make_test_user(user_id=999, email="intruder@example.com")

    async def override_get_user():
        return user_b

    app.dependency_overrides[get_current_user_optional] = override_get_user

    owned_review = LiteratureReview(
        id=15,
        user_query="Proprietary graph embeddings",
        status=ReviewStatus.COMPLETED.value,
        user_id=101,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = owned_review

    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result
    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.post(
        "/api/v1/reviews/15/chat",
        json={"question": "What are the key methodologies?", "history": []},
    )
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


def test_retry_forbidden_for_other_user():
    """Verify POST /api/v1/reviews/{id}/retry returns 403 when review belongs to another user."""
    client = TestClient(app)
    user_b = _make_test_user(user_id=999, email="intruder@example.com")

    async def override_get_user():
        return user_b

    app.dependency_overrides[get_current_user_optional] = override_get_user

    owned_review = LiteratureReview(
        id=20,
        user_query="Resumable literature task",
        status=ReviewStatus.FAILED.value,
        user_id=101,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = owned_review

    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result
    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.post("/api/v1/reviews/20/retry")
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


def test_audit_forbidden_for_other_user():
    """Verify GET /api/v1/reviews/{id}/audit returns 403 when review belongs to another user."""
    client = TestClient(app)
    user_b = _make_test_user(user_id=999, email="intruder@example.com")

    async def override_get_user():
        return user_b

    app.dependency_overrides[get_current_user_optional] = override_get_user

    owned_review = LiteratureReview(
        id=25,
        user_query="Audit logs",
        status=ReviewStatus.COMPLETED.value,
        user_id=101,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = owned_review

    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result
    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/api/v1/reviews/25/audit")
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


def test_graph_forbidden_for_other_user():
    """Verify GET /api/v1/reviews/{id}/graph returns 403 when review belongs to another user."""
    client = TestClient(app)
    user_b = _make_test_user(user_id=999, email="intruder@example.com")

    async def override_get_user():
        return user_b

    app.dependency_overrides[get_current_user_optional] = override_get_user

    owned_review = LiteratureReview(
        id=30,
        user_query="Knowledge graph",
        status=ReviewStatus.COMPLETED.value,
        user_id=101,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = owned_review

    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result
    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/api/v1/reviews/30/graph")
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()
