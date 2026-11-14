"""Pytest configuration and test environment isolation fixtures."""

import pytest
from app.core.config import settings


@pytest.fixture(autouse=True)
def isolate_groq_api_key_for_unit_tests(monkeypatch):
    """Prevent unit tests from making unintended external Groq API calls."""
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")


@pytest.fixture
def mock_rate_limiters():
    """Bypass Redis rate limiting in endpoint tests that do not test BE-14."""

    from app.api.v1.reviews import (
        chat_review_rate_limiter,
        create_review_rate_limiter,
    )
    from app.main import app

    async def allow_request():
        return True

    limiters = (
        create_review_rate_limiter,
        chat_review_rate_limiter,
    )

    # Preserve any existing overrides.
    previous = {limiter: app.dependency_overrides.get(limiter) for limiter in limiters}

    for limiter in limiters:
        app.dependency_overrides[limiter] = allow_request

    yield

    # Restore the original overrides.
    for limiter, original in previous.items():
        if original is None:
            app.dependency_overrides.pop(limiter, None)
        else:
            app.dependency_overrides[limiter] = original
