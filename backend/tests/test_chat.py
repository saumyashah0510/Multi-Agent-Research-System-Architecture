"""Unit and integration tests for RAG Chat API endpoint."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.db.session import get_db
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def mock_db_session():
    """Provide a mocked asynchronous database session."""
    return AsyncMock()


@pytest.fixture
def client(mock_db_session, mock_rate_limiters):
    """Provide a test client with database and rate limiters overridden."""

    async def override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_db, None)


def test_chat_invalid_review_returns_404(client, mock_db_session):
    """Verify chat returns 404 when the review does not exist."""

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    response = client.post(
        "/api/v1/reviews/999999/chat",
        json={"question": "What are the main findings?"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Literature review not found"


def test_chat_empty_question_returns_422(client):
    """Verify an empty question is rejected by request validation."""

    response = client.post(
        "/api/v1/reviews/1/chat",
        json={"question": ""},
    )

    assert response.status_code == 422


def test_chat_valid_question_returns_answer_and_citations(
    client,
    mock_db_session,
    monkeypatch,
):
    """Verify a valid question returns a grounded answer and citations."""

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = object()
    mock_db_session.execute.return_value = mock_result

    mock_chunks = [
        {
            "paper_id": 1,
            "section_name": "Methodology",
            "chunk_index": 0,
            "content": "The study uses a randomized controlled trial.",
            "similarity": 0.92,
            "distance": 0.08,
        }
    ]

    mock_similarity_search = AsyncMock(return_value=mock_chunks)

    mock_chat_service = AsyncMock(
        return_value={
            "answer": "The study uses a randomized controlled trial.",
            "citations": [
                {
                    "paper_id": 1,
                    "section_name": "Methodology",
                    "chunk_index": 0,
                    "snippet": "The study uses a randomized controlled trial.",
                }
            ],
        }
    )

    monkeypatch.setattr(
        "app.api.v1.reviews.similarity_search",
        mock_similarity_search,
    )
    monkeypatch.setattr(
        "app.api.v1.reviews.generate_rag_chat_response",
        mock_chat_service,
    )

    response = client.post(
        "/api/v1/reviews/1/chat",
        json={
            "question": "What methodology was used?",
            "history": [],
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["answer"] == "The study uses a randomized controlled trial."
    assert len(data["citations"]) == 1
    assert data["citations"][0]["paper_id"] == 1
    assert data["citations"][0]["section_name"] == "Methodology"

    mock_similarity_search.assert_awaited_once_with(
        mock_db_session,
        query_text="What methodology was used?",
        review_id=1,
        top_k=4,
    )

    mock_chat_service.assert_awaited_once_with(
        "What methodology was used?",
        mock_chunks,
        [],
    )
