"""Unit tests for Mid-Pipeline Resume & Retry API (Issue BE-16)."""

import pytest


@pytest.mark.skip(reason="Assignee will unskip upon implementing background retry in BE-16")
@pytest.mark.asyncio
async def test_retry_nonexistent_review_returns_404():
    """Verify that retrying a non-existent review returns 404."""
    pass


@pytest.mark.skip(reason="Assignee will unskip upon implementing background retry in BE-16")
@pytest.mark.asyncio
async def test_retry_completed_review_returns_400():
    """Verify that attempting to retry an already completed review returns 400 Bad Request."""
    pass


@pytest.mark.skip(reason="Assignee will unskip upon implementing background retry in BE-16")
@pytest.mark.asyncio
async def test_retry_failed_review_resumes_execution():
    """Verify that retrying a failed review resumes background task and returns 200."""
    pass
