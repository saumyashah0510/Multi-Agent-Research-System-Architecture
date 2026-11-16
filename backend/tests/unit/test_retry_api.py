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
        self.added = []

    async def get(self, model, review_id, **kwargs):
        assert model is reviews_api.LiteratureReview
        assert review_id == self.review.id

        # The retry task uses with_for_update=True to protect against
        # concurrent/stale retries. Other retry pipeline stages use a
        # normal session.get() without the lock.
        if kwargs.get("with_for_update") is True:
            assert self.review is not None

        return self.review

    def add(self, value):
        self.added.append(value)


class FakeSessionContext:
    """Async context manager matching AsyncSessionLocal usage."""

    def __init__(self, review):
        self.session = FakeSession(review)

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


async def run_retry_task(monkeypatch, review, graph):
    """Execute the retry background task with isolated fake dependencies."""
    monkeypatch.setattr(reviews_api, "graph", graph)
    monkeypatch.setattr(
        reviews_api,
        "AsyncSessionLocal",
        lambda: FakeSessionContext(review),
    )

    publish_event = AsyncMock()
    monkeypatch.setattr(reviews_api, "publish_review_event", publish_event)

    await reviews_api._retry_failed_review(str(review.id))

    return publish_event


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
    """Verify that an already completed review cannot be retried."""
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
        "Cannot retry review with status 'completed'. " "Only failed reviews can be resumed."
    )
    assert background_tasks.tasks == []


@pytest.mark.asyncio
async def test_retry_awaiting_user_input_review_returns_400():
    """Verify that a paused human-approval review cannot be retried."""
    review = SimpleNamespace(
        id=123,
        status=ReviewStatus.AWAITING_USER_INPUT.value,
        user_id=None,
    )
    db = FakeDB(review)
    background_tasks = FakeBackgroundTasks()

    with pytest.raises(HTTPException) as exc_info:
        await reviews_api.retry_review(123, background_tasks, db, None)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == (
        "Cannot retry review with status 'awaiting_user_input'. "
        "Only failed reviews can be resumed."
    )
    assert background_tasks.tasks == []


@pytest.mark.asyncio
async def test_retry_running_review_returns_400():
    """Verify that an actively running review cannot be retried."""
    review = SimpleNamespace(
        id=123,
        status=ReviewStatus.QUERY_EXPANSION.value,
        user_id=None,
    )
    db = FakeDB(review)
    background_tasks = FakeBackgroundTasks()

    with pytest.raises(HTTPException) as exc_info:
        await reviews_api.retry_review(123, background_tasks, db, None)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == (
        "Cannot retry review with status 'query_expansion'. " "Only failed reviews can be resumed."
    )
    assert background_tasks.tasks == []


@pytest.mark.asyncio
async def test_retry_failed_review_is_scheduled():
    """Verify that a failed review is accepted and queued for background retry."""
    review = SimpleNamespace(
        id=123,
        status=ReviewStatus.FAILED.value,
        user_id=None,
    )
    db = FakeDB(review)
    background_tasks = FakeBackgroundTasks()

    result = await reviews_api.retry_review(123, background_tasks, db, None)

    assert result == {
        "status": "resuming",
        "review_id": 123,
        "message": "Review pipeline resumption initiated from checkpoint.",
    }
    assert background_tasks.tasks == [
        (reviews_api._retry_failed_review, ("123",), {}),
    ]


@pytest.mark.asyncio
async def test_retry_failed_review_resumes_final_stage(monkeypatch):
    """Verify that a failed final-stage review resumes and completes."""
    review = SimpleNamespace(
        id=123,
        status=ReviewStatus.FAILED.value,
        user_id=None,
        synthesized_review=None,
    )

    class FakeGraph:
        async def aget_state(self, config):
            assert config == {"configurable": {"thread_id": "123"}}
            return SimpleNamespace(next=("report_synthesis",), values={})

        async def astream(self, value, config, stream_mode):
            assert value is None
            assert config == {"configurable": {"thread_id": "123"}}
            assert stream_mode == "updates"

            yield {
                "report_synthesis": {
                    "synthesized_review": {
                        "summary": "retry succeeded",
                    }
                }
            }

    publish_event = await run_retry_task(monkeypatch, review, FakeGraph())

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


@pytest.mark.asyncio
async def test_retry_failed_early_query_expansion_resumes(monkeypatch):
    """Verify that an early query-expansion failure is resumed correctly."""
    review = SimpleNamespace(
        id=123,
        status=ReviewStatus.FAILED.value,
        user_id=None,
    )

    class FakeGraph:
        async def aget_state(self, config):
            return SimpleNamespace(next=("query_expansion",), values={})

        async def astream(self, value, config, stream_mode):
            assert value is None

            yield {
                "query_expansion": {
                    "search_queries": [
                        "query one",
                        "query two",
                    ]
                }
            }

    publish_event = await run_retry_task(monkeypatch, review, FakeGraph())

    assert review.status == ReviewStatus.PAPER_DISCOVERY.value

    publish_event.assert_any_call(
        123,
        {
            "event": "stage_update",
            "stage": "QUERY_EXPANSION",
            "status": "running",
            "message": "Resuming literature review from query expansion...",
            "review_id": "123",
        },
    )

    publish_event.assert_any_call(
        123,
        {
            "event": "stage_completed",
            "stage": "QUERY_EXPANSION",
            "status": "completed",
            "message": "Expanded into 2 academic queries",
            "data": {
                "sub_queries": [
                    "query one",
                    "query two",
                ],
                "queries": [
                    "query one",
                    "query two",
                ],
            },
            "review_id": "123",
        },
    )


@pytest.mark.asyncio
async def test_retry_failed_early_paper_discovery_resumes(monkeypatch):
    """Verify that an early paper-discovery failure is resumed correctly."""
    review = SimpleNamespace(
        id=123,
        status=ReviewStatus.FAILED.value,
        user_id=None,
    )

    class FakeGraph:
        async def aget_state(self, config):
            return SimpleNamespace(next=("paper_discovery",), values={})

        async def astream(self, value, config, stream_mode):
            assert value is None

            yield {
                "paper_discovery": {
                    "discovered_papers": [
                        {"title": "Paper A"},
                        {"title": "Paper B"},
                    ]
                }
            }

    publish_event = await run_retry_task(monkeypatch, review, FakeGraph())

    assert review.status == ReviewStatus.SCREENING.value

    publish_event.assert_any_call(
        123,
        {
            "event": "stage_completed",
            "stage": "PAPER_DISCOVERY",
            "status": "completed",
            "message": "Discovered 2 candidate papers",
            "data": {
                "total_count": 2,
                "count": 2,
            },
            "review_id": "123",
        },
    )


@pytest.mark.asyncio
async def test_retry_failed_screening_resumes_to_approval(monkeypatch):
    """Verify that a screening failure persists papers and pauses for approval."""
    review = SimpleNamespace(
        id=123,
        status=ReviewStatus.FAILED.value,
        user_id=None,
    )

    class FakePaper:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            self.id = 456

    class FakeGraph:
        async def aget_state(self, config):
            return SimpleNamespace(next=("screening",), values={})

        async def astream(self, value, config, stream_mode):
            assert value is None

            yield {
                "screening": {
                    "screened_papers": [
                        {
                            "title": "Paper A",
                            "relevance_score": 0.91,
                        },
                        {
                            "title": "Paper B",
                            "relevance_score": 0.88,
                        },
                    ]
                }
            }

    monkeypatch.setattr(reviews_api, "Paper", FakePaper)

    publish_event = await run_retry_task(
        monkeypatch,
        review,
        FakeGraph(),
    )

    assert review.status == ReviewStatus.AWAITING_USER_INPUT.value

    publish_event.assert_any_call(
        123,
        {
            "event": "awaiting_user_input",
            "stage": "AWAITING_USER_INPUT",
            "status": "paused",
            "message": "Awaiting human-in-the-loop candidate paper selection",
            "data": {
                "screened_papers": [
                    {
                        "title": "Paper A",
                        "relevance_score": 0.91,
                        "id": "456",
                        "paper_id": "456",
                    },
                    {
                        "title": "Paper B",
                        "relevance_score": 0.88,
                        "id": "456",
                        "paper_id": "456",
                    },
                ],
                "total_screened": 2,
            },
            "review_id": "123",
        },
    )


@pytest.mark.asyncio
async def test_retry_failed_human_interrupt_restores_approval_state(monkeypatch):
    """Verify that a failed record at human_interrupt is restored to approval state."""
    review = SimpleNamespace(
        id=123,
        status=ReviewStatus.FAILED.value,
        user_id=None,
    )

    screened = [
        {
            "id": "456",
            "title": "Paper A",
        }
    ]

    class FakeGraph:
        async def aget_state(self, config):
            return SimpleNamespace(
                next=("human_interrupt",),
                values={
                    "screened_papers": screened,
                },
            )

        async def astream(self, *args, **kwargs):
            raise AssertionError("human_interrupt must not be resumed automatically")
            yield  # pragma: no cover

    publish_event = await run_retry_task(
        monkeypatch,
        review,
        FakeGraph(),
    )

    assert review.status == ReviewStatus.AWAITING_USER_INPUT.value

    publish_event.assert_awaited_once_with(
        123,
        {
            "event": "awaiting_user_input",
            "stage": "AWAITING_USER_INPUT",
            "status": "paused",
            "message": "Awaiting human-in-the-loop candidate paper selection",
            "data": {
                "screened_papers": screened,
                "total_screened": 1,
            },
            "review_id": "123",
        },
    )


@pytest.mark.asyncio
async def test_retry_does_not_overwrite_review_completed_before_background_task(
    monkeypatch,
):
    """Verify that a stale retry task cannot overwrite a completed review."""
    review = SimpleNamespace(
        id=123,
        status=ReviewStatus.COMPLETED.value,
        user_id=None,
        synthesized_review={
            "summary": "already done",
        },
    )

    class FakeGraph:
        async def aget_state(self, config):
            return SimpleNamespace(
                next=("report_synthesis",),
                values={},
            )

        async def astream(self, *args, **kwargs):
            raise AssertionError("stale retry must not execute the graph")
            yield  # pragma: no cover

    publish_event = await run_retry_task(
        monkeypatch,
        review,
        FakeGraph(),
    )

    assert review.status == ReviewStatus.COMPLETED.value
    assert review.synthesized_review == {
        "summary": "already done",
    }
    publish_event.assert_not_awaited()
