"""Tests for the academic paper search service."""

import httpx
import pytest
from app.services.search_service import (
    _request_with_retries,
    search_academic_papers,
)


@pytest.mark.asyncio
async def test_search_empty_query():
    """Empty queries should return an empty list."""
    result = await search_academic_papers("")

    assert result == []


@pytest.mark.asyncio
async def test_search_uses_cached_results(monkeypatch):
    """Cached results should be returned without calling external APIs."""

    cached_results = [
        {
            "title": "Cached Paper",
            "authors": ["Test Author"],
            "abstract": "Cached abstract",
            "publication_date": "2026-01-01",
            "arxiv_id": "1234.5678",
            "doi": None,
            "pdf_url": "https://arxiv.org/pdf/1234.5678",
            "source": "arxiv",
        }
    ]

    async def fake_get_cached_query(key, as_json=False):
        return cached_results

    monkeypatch.setattr(
        "app.services.search_service.get_cached_query",
        fake_get_cached_query,
    )

    result = await search_academic_papers("machine learning")

    assert result == cached_results


@pytest.mark.asyncio
async def test_search_invalid_source():
    """Unknown sources should return an empty list."""

    result = await search_academic_papers(
        "machine learning",
        sources=["unknown"],
    )

    assert result == []


@pytest.mark.asyncio
async def test_request_with_retries_on_rate_limit(monkeypatch):
    """HTTP 429 should be retried before succeeding."""

    class FakeResponse:
        def __init__(self, status_code):
            self.status_code = status_code

        def raise_for_status(self):
            if self.status_code >= 400:
                raise httpx.HTTPStatusError(
                    "HTTP error",
                    request=httpx.Request(
                        "GET",
                        "https://example.com",
                    ),
                    response=httpx.Response(
                        self.status_code,
                    ),
                )

    responses = [
        FakeResponse(429),
        FakeResponse(200),
    ]

    async def fake_get(url, params=None):
        return responses.pop(0)

    async def fake_sleep(delay):
        pass

    class FakeClient:
        async def get(self, url, params=None):
            return await fake_get(url, params)

    monkeypatch.setattr(
        "app.services.search_service.asyncio.sleep",
        fake_sleep,
    )

    client = FakeClient()

    response = await _request_with_retries(
        client,
        "https://example.com",
        params={},
    )

    assert response.status_code == 200
    assert len(responses) == 0
