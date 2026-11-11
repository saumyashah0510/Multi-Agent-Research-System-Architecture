"""Pytest configuration and test environment isolation fixtures."""

import pytest
from app.core.config import settings


@pytest.fixture(autouse=True)
def isolate_groq_api_key_for_unit_tests(monkeypatch):
    """Isolate GROQ_API_KEY during unit tests so tests do not make unintended external calls."""
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")
