"""Unit tests for Google and GitHub OAuth 2.0 Integration (Issue BE-13)."""

import pytest
from app.schemas.oauth import GitHubAuthRequest, GoogleAuthRequest, OAuthUserProfile


def test_oauth_schemas_validation():
    """Verify that OAuth request schemas parse inputs properly."""
    google_req = GoogleAuthRequest(credential="fake-google-id-token-jwt")
    assert google_req.credential == "fake-google-id-token-jwt"

    github_req = GitHubAuthRequest(code="fake-github-auth-code")
    assert github_req.code == "fake-github-auth-code"

    profile = OAuthUserProfile(
        provider="google",
        provider_user_id="google-user-12345",
        email="researcher@scholaris.ai",
        name="Dr. Scholar",
        avatar_url="https://lh3.googleusercontent.com/photo.jpg",
    )
    assert profile.provider == "google"
    assert profile.email == "researcher@scholaris.ai"


@pytest.mark.skip(reason="Assignee will unskip upon implementing oauth_service.py in BE-13")
@pytest.mark.asyncio
async def test_verify_google_credential_mock(monkeypatch):
    """Verify Google token decoding with mocked httpx response."""

    # Assignee will mock httpx.AsyncClient.get returning valid tokeninfo payload
    pass


@pytest.mark.skip(reason="Assignee will unskip upon implementing oauth_service.py in BE-13")
@pytest.mark.asyncio
async def test_exchange_github_code_mock(monkeypatch):
    """Verify GitHub code exchange with mocked httpx access token and user profile."""

    # Assignee will mock httpx.AsyncClient.post and get returning GitHub token and profile
    pass
