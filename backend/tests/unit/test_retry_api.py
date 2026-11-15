"""Unit tests for Mid-Pipeline Resume & Retry API (Issue BE-16)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

import app.api.v1.reviews as reviews_api
from app.models.review import ReviewStatus


class FakeResult:
    """Minimal async SQLAlchemy result used by the endpoint unit tests."""

    def __init__(self, review):
        self._review = review

    def scalar_one_or_none(self):
        return self._review


class FakeDB:
    """Minimal async database session used by the endpoint unit tests."""

    def __init__(self, review):
        self.review = review

    async def execute(self, _statement):
        return FakeResult(self.review)


class FakeBackgroundTasks:
    """Capture FastAPI background tasks without executing them automatically."""

    def __init__(self):
        self.tasks = []

    def add_task(self, func, *args, **kwargs):
        self.tasks.append((func, args, kwargs))


class FakeSession:
    """Minimal async session used by the retry background task."""

    def __init__(self, review):
        self.review = review
        self.commit = AsyncMock()

    async def get(self, model, review_id):
        assert model is reviews_api.LiteratureReview
        assert review_id == self.review.id
        return self.review


class FakeSessionContext:
    """Async context manager matching AsyncSessionLocal usage."""

    def __init__(self, review):
        self.session = FakeSession(review)

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_retry_nonexistent_review_returns_404():
    """Verify that retrying a non-existent review returns 404."""
    db = FakeDB(None)
    background_tasks = FakeBackgroundTasks()

    with pytest.raises(HTTPException) as exc_info:
        await reviews_api.retry_review(999999, background_tasks, db, None)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Literature review not found"
    assert background_tasks.tasks == []


@pytest.mark.asyncio
async def test_retry_completed_review_returns_400():
    """Verify that attempting to retry an already completed review returns 400 Bad Request."""
    review = SimpleNamespace(
        id=123,
        status=ReviewStatus.COMPLETED.value,
        user_id=None,
    )
    db = FakeDB(review)
    background_tasks = FakeBackgroundTasks()

    with pytest.raises(HTTPException) as exc_info:
        await reviews_api.retry_review(123, background_tasks, db, None)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == (
        "Cannot retry a review that has already completed successfully."
    )
    assert background_tasks.tasks == []


@pytest.mark.asyncio
async def test_retry_failed_review_resumes_execution(monkeypatch):
    """Verify that retrying a failed review resumes from its checkpoint and completes it."""
    review = SimpleNamespace(
        id=123,
        status=ReviewStatus.FAILED.value,
        user_id=None,
        synthesized_review=None,
    )
    db = FakeDB(review)
    background_tasks = FakeBackgroundTasks()

    result = await reviews_api.retry_review(123, background_tasks, db, None)

    assert result == {
        "status": "resuming",
        "review_id": 123,
        "message": "Review pipeline resumption initiated from checkpoint.",
    }
    assert len(background_tasks.tasks) == 1
    task, args, kwargs = background_tasks.tasks[0]
    assert task is reviews_api._retry_failed_review
    assert args == ("123",)
    assert kwargs == {}

    class FakeGraph:
        async def aget_state(self, config):
            assert config == {"configurable": {"thread_id": "123"}}
            return SimpleNamespace(next=("report_synthesis",))

        async def astream(self, value, config, stream_mode):
            assert value is None
            assert config == {"configurable": {"thread_id": "123"}}
            assert stream_mode == "updates"
            yield {
                "report_synthesis": {
                    "synthesized_review": {"summary": "retry succeeded"}
                }
            }

    monkeypatch.setattr(reviews_api, "graph", FakeGraph())
    monkeypatch.setattr(
        reviews_api,
        "AsyncSessionLocal",
        lambda: FakeSessionContext(review),
    )
    publish_event = AsyncMock()
    monkeypatch.setattr(reviews_api, "publish_review_event", publish_event)

    await task(*args, **kwargs)

    assert review.status == ReviewStatus.COMPLETED.value
    assert review.synthesized_review == {"summary": "retry succeeded"}
    publish_event.assert_any_call(
        123,
        {
            "event": "stage_update",
            "stage": "REPORT_SYNTHESIS",
            "status": "running",
            "message": "Resuming literature review from report synthesis...",
            "review_id": "123",
        },
    )
    publish_event.assert_any_call(
        123,
        {
            "event": "completed",
            "stage": "COMPLETED",
            "status": "completed",
            "message": "Literature review pipeline completed",
            "review_id": "123",
        },
    )
