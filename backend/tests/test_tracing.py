"""Unit tests for LangSmith tracing helpers."""

from unittest.mock import MagicMock, patch

from app.agents.tracing import get_shared_run_url, is_langsmith_enabled


def test_is_langsmith_enabled_false_by_default(monkeypatch):
    """Ensure tracing is disabled when key is missing or toggle is false."""
    monkeypatch.setattr("app.core.config.settings.LANGCHAIN_TRACING_V2", "false")
    monkeypatch.setattr("app.core.config.settings.LANGCHAIN_API_KEY", "")
    assert is_langsmith_enabled() is False


def test_is_langsmith_enabled_true_when_configured(monkeypatch):
    """Ensure tracing is enabled when both flag and key are set."""
    monkeypatch.setattr("app.core.config.settings.LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setattr("app.core.config.settings.LANGCHAIN_API_KEY", "lsv2_pt_testkey123")
    assert is_langsmith_enabled() is True


def test_get_shared_run_url_returns_none_when_disabled(monkeypatch):
    """Return None if LangSmith is disabled."""
    monkeypatch.setattr("app.core.config.settings.LANGCHAIN_TRACING_V2", "false")
    assert get_shared_run_url("dummy-run-id") is None


def test_get_shared_run_url_success(monkeypatch):
    """Generate public shared URL when LangSmith is enabled."""
    monkeypatch.setattr("app.core.config.settings.LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setattr("app.core.config.settings.LANGCHAIN_API_KEY", "lsv2_pt_validkey")

    mock_client = MagicMock()
    mock_client.share_run.return_value = "https://smith.langchain.com/public/dummy-run-id/r"

    with patch("langsmith.Client", return_value=mock_client):
        url = get_shared_run_url("dummy-run-id")
        assert url == "https://smith.langchain.com/public/dummy-run-id/r"
        mock_client.share_run.assert_called_once_with("dummy-run-id")


def test_get_shared_run_url_handles_exception(monkeypatch):
    """Return None gracefully if LangSmith client encounters an error."""
    monkeypatch.setattr("app.core.config.settings.LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setattr("app.core.config.settings.LANGCHAIN_API_KEY", "lsv2_pt_validkey")

    with patch("langsmith.Client", side_effect=Exception("Network error")):
        url = get_shared_run_url("dummy-run-id")
        assert url is None
