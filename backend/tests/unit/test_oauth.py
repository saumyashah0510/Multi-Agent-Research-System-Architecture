"""Unit tests for Google and GitHub OAuth 2.0 Integration (Issue BE-13)."""

from datetime import datetime, timezone
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from app.api.deps import get_db
from app.core.config import settings
from app.main import app
from app.models.user import User
from app.schemas.oauth import GitHubAuthRequest, GoogleAuthRequest, OAuthUserProfile
from app.services.oauth_service import OAuthService
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError


def _make_test_user(
    user_id: int = 1,
    email: str = "researcher@scholaris.ai",
    name: Optional[str] = "Dr. Scholar",
    is_active: bool = True,
    auth_provider: str = "google",
    provider_user_id: Optional[str] = "google-user-12345",
    avatar_url: Optional[str] = None,
    hashed_password: Optional[str] = None,
) -> User:
    """Helper to instantiate a User mock/model for OAuth unit testing."""
    return User(
        id=user_id,
        email=email,
        name=name,
        hashed_password=hashed_password,
        avatar_url=avatar_url,
        auth_provider=auth_provider,
        provider_user_id=provider_user_id,
        is_active=is_active,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def client():
    """Fixture providing a FastAPI TestClient with DB overrides cleared after each test."""
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# =========================================================================
# 1. Pydantic Schemas Validation
# =========================================================================


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


# =========================================================================
# 2. Google Token Verification Tests
# =========================================================================


@pytest.mark.asyncio
async def test_verify_google_credential_mock(monkeypatch):
    """Verify Google token decoding with mocked httpx response."""
    expected_aud = settings.GOOGLE_CLIENT_ID or "scholaris-google-client-id"
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", expected_aud)

    google_payload = {
        "aud": expected_aud,
        "sub": "google-user-12345",
        "email": "ada.lovelace@scholaris.ai",
        "name": "Ada Lovelace",
        "picture": "https://example.com/ada.jpg",
    }

    async def mock_get(self, url, *args, **kwargs):
        req = httpx.Request("GET", url)
        return httpx.Response(200, json=google_payload, request=req)

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    profile = await OAuthService.verify_google_credential("valid-google-id-token")
    assert profile.provider == "google"
    assert profile.provider_user_id == "google-user-12345"
    assert profile.email == "ada.lovelace@scholaris.ai"
    assert profile.name == "Ada Lovelace"
    assert profile.avatar_url == "https://example.com/ada.jpg"


@pytest.mark.asyncio
async def test_verify_google_credential_empty_credential():
    """Verify that empty or whitespace credential raises ValueError."""
    with pytest.raises(ValueError, match="Google ID token credential must not be empty"):
        await OAuthService.verify_google_credential("")

    with pytest.raises(ValueError, match="Google ID token credential must not be empty"):
        await OAuthService.verify_google_credential("   ")


@pytest.mark.asyncio
async def test_verify_google_credential_invalid_token(monkeypatch):
    """Verify that a non-200 response from Google raises ValueError."""

    async def mock_get(self, url, *args, **kwargs):
        req = httpx.Request("GET", url)
        return httpx.Response(400, json={"error_description": "Invalid Value"}, request=req)

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    with pytest.raises(ValueError, match="Invalid Google ID token"):
        await OAuthService.verify_google_credential("invalid-token")


@pytest.mark.asyncio
async def test_verify_google_credential_audience_mismatch(monkeypatch):
    """Verify that audience mismatch against GOOGLE_CLIENT_ID raises ValueError."""
    monkeypatch.setattr(
        settings, "GOOGLE_CLIENT_ID", "expected-client-id.apps.googleusercontent.com"
    )

    google_payload = {
        "aud": "rogue-client-id.apps.googleusercontent.com",
        "sub": "google-user-12345",
        "email": "hacker@example.com",
    }

    async def mock_get(self, url, *args, **kwargs):
        req = httpx.Request("GET", url)
        return httpx.Response(200, json=google_payload, request=req)

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    with pytest.raises(ValueError, match="Google ID token audience mismatch"):
        await OAuthService.verify_google_credential("mismatched-aud-token")


@pytest.mark.asyncio
async def test_verify_google_credential_missing_sub_or_email(monkeypatch):
    """Verify that missing sub or email in Google payload raises ValueError."""
    google_payload = {
        "aud": settings.GOOGLE_CLIENT_ID,
        "name": "Anonymous",
    }

    async def mock_get(self, url, *args, **kwargs):
        req = httpx.Request("GET", url)
        return httpx.Response(200, json=google_payload, request=req)

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    with pytest.raises(ValueError, match="Google ID token missing required subject or email"):
        await OAuthService.verify_google_credential("missing-claims-token")


@pytest.mark.asyncio
async def test_verify_google_credential_network_failure(monkeypatch):
    """Verify that connection failure raises ValueError."""

    async def mock_get(self, url, *args, **kwargs):
        raise httpx.ConnectError("Network unreachable")

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    with pytest.raises(ValueError, match="Failed to communicate with Google authentication server"):
        await OAuthService.verify_google_credential("any-token")


# =========================================================================
# 3. GitHub Code Exchange Tests
# =========================================================================


@pytest.mark.asyncio
async def test_exchange_github_code_mock(monkeypatch):
    """Verify GitHub code exchange with mocked httpx access token and user profile."""
    github_token_payload = {"access_token": "gho_mock_access_token_12345", "token_type": "bearer"}
    github_user_payload = {
        "id": 987654,
        "login": "octocat",
        "name": "Monalisa Octocat",
        "avatar_url": "https://github.com/images/error/octocat_happy.gif",
        "email": None,
    }
    github_emails_payload = [
        {"email": "unverified@example.com", "primary": False, "verified": False},
        {"email": "octocat@github.com", "primary": True, "verified": True},
    ]

    async def mock_post(self, url, *args, **kwargs):
        req = httpx.Request("POST", url)
        return httpx.Response(200, json=github_token_payload, request=req)

    async def mock_get(self, url, *args, **kwargs):
        req = httpx.Request("GET", url)
        if "emails" in url:
            return httpx.Response(200, json=github_emails_payload, request=req)
        return httpx.Response(200, json=github_user_payload, request=req)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    profile = await OAuthService.exchange_github_code("valid-github-code")
    assert profile.provider == "github"
    assert profile.provider_user_id == "987654"
    assert profile.email == "octocat@github.com"
    assert profile.name == "Monalisa Octocat"
    assert profile.avatar_url == "https://github.com/images/error/octocat_happy.gif"


@pytest.mark.asyncio
async def test_exchange_github_code_empty_code():
    """Verify empty code raises ValueError."""
    with pytest.raises(ValueError, match="GitHub authorization code must not be empty"):
        await OAuthService.exchange_github_code("")

    with pytest.raises(ValueError, match="GitHub authorization code must not be empty"):
        await OAuthService.exchange_github_code("   ")


@pytest.mark.asyncio
async def test_exchange_github_code_failed_token_exchange(monkeypatch):
    """Verify that a failure during GitHub token exchange raises ValueError."""

    async def mock_post(self, url, *args, **kwargs):
        req = httpx.Request("POST", url)
        return httpx.Response(
            200,
            json={
                "error": "bad_verification_code",
                "error_description": "The code passed is incorrect or has expired.",
            },
            request=req,
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    with pytest.raises(ValueError, match="The code passed is incorrect or has expired."):
        await OAuthService.exchange_github_code("expired-code")


@pytest.mark.asyncio
async def test_exchange_github_code_failed_profile_fetch(monkeypatch):
    """Verify that failure when fetching user profile raises ValueError."""

    async def mock_post(self, url, *args, **kwargs):
        req = httpx.Request("POST", url)
        return httpx.Response(200, json={"access_token": "valid_token"}, request=req)

    async def mock_get(self, url, *args, **kwargs):
        req = httpx.Request("GET", url)
        return httpx.Response(401, json={"message": "Bad credentials"}, request=req)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    with pytest.raises(ValueError, match="Failed to fetch GitHub user profile"):
        await OAuthService.exchange_github_code("some-code")


@pytest.mark.asyncio
async def test_exchange_github_code_no_email_available(monkeypatch):
    """Verify error when GitHub profile and /user/emails return no email."""

    async def mock_post(self, url, *args, **kwargs):
        req = httpx.Request("POST", url)
        return httpx.Response(200, json={"access_token": "valid_token"}, request=req)

    async def mock_get(self, url, *args, **kwargs):
        req = httpx.Request("GET", url)
        if "emails" in url:
            return httpx.Response(200, json=[], request=req)
        return httpx.Response(
            200,
            json={"id": 12345, "login": "noemailuser", "email": None},
            request=req,
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    with pytest.raises(
        ValueError, match="Could not obtain verified email address from GitHub account"
    ):
        await OAuthService.exchange_github_code("no-email-code")


# =========================================================================
# 4. Account Linking & Registration Tests
# =========================================================================


@pytest.mark.asyncio
async def test_authenticate_or_register_oauth_user_new_user():
    """Verify creating a new user when neither provider_user_id nor email exists."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    profile = OAuthUserProfile(
        provider="google",
        provider_user_id="google-new-999",
        email="newuser@scholaris.ai",
        name="New Scholar",
        avatar_url="https://example.com/new.png",
    )

    created_user = await OAuthService.authenticate_or_register_oauth_user(mock_db, profile)

    assert created_user.email == "newuser@scholaris.ai"
    assert created_user.auth_provider == "google"
    assert created_user.provider_user_id == "google-new-999"
    assert created_user.hashed_password is None
    assert created_user.is_active is True
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_authenticate_or_register_oauth_user_existing_by_provider_id():
    """Verify finding existing user by provider_user_id and updating missing metadata."""
    mock_db = AsyncMock()
    existing_user = _make_test_user(
        user_id=5,
        email="existing@scholaris.ai",
        name=None,
        avatar_url=None,
        auth_provider="google",
        provider_user_id="google-id-555",
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_user
    mock_db.execute.return_value = mock_result

    profile = OAuthUserProfile(
        provider="google",
        provider_user_id="google-id-555",
        email="existing@scholaris.ai",
        name="Updated Name",
        avatar_url="https://example.com/avatar555.png",
    )

    user = await OAuthService.authenticate_or_register_oauth_user(mock_db, profile)
    assert user.id == 5
    assert user.name == "Updated Name"
    assert user.avatar_url == "https://example.com/avatar555.png"
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_authenticate_or_register_oauth_user_linking_by_email():
    """Verify linking OAuth provider_user_id to existing local user with matching email."""
    mock_db = AsyncMock()
    existing_local_user = _make_test_user(
        user_id=10,
        email="local@scholaris.ai",
        name="Local User",
        auth_provider="local",
        provider_user_id=None,
        hashed_password="$2b$12$securepasswordhash",
    )

    # First lookup by provider_user_id returns None, second lookup by email returns existing_local_user
    mock_res_provider = MagicMock()
    mock_res_provider.scalar_one_or_none.return_value = None
    mock_res_email = MagicMock()
    mock_res_email.scalar_one_or_none.return_value = existing_local_user

    mock_db.execute.side_effect = [mock_res_provider, mock_res_email]

    profile = OAuthUserProfile(
        provider="github",
        provider_user_id="github-uid-888",
        email="local@scholaris.ai",
        name="Local User",
        avatar_url="https://github.com/avatar.png",
    )

    user = await OAuthService.authenticate_or_register_oauth_user(mock_db, profile)
    assert user.id == 10
    assert user.provider_user_id == "github-uid-888"
    assert user.hashed_password == "$2b$12$securepasswordhash"  # Password is preserved
    assert user.avatar_url == "https://github.com/avatar.png"
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_authenticate_or_register_oauth_user_integrity_error_recovery():
    """Verify handling concurrent insertion race condition via rollback and lookup."""
    mock_db = AsyncMock()
    mock_result_none = MagicMock()
    mock_result_none.scalar_one_or_none.return_value = None

    existing_user = _make_test_user(user_id=22, email="concurrent@scholaris.ai")
    mock_result_existing = MagicMock()
    mock_result_existing.scalar_one_or_none.return_value = existing_user

    # Lookups: 1) provider_id -> None, 2) email -> None, 3) post-IntegrityError email lookup -> existing_user
    mock_db.execute.side_effect = [mock_result_none, mock_result_none, mock_result_existing]
    mock_db.commit.side_effect = IntegrityError(
        "duplicate key value", params=None, orig=Exception()
    )

    profile = OAuthUserProfile(
        provider="google",
        provider_user_id="google-concurrent-22",
        email="concurrent@scholaris.ai",
    )

    user = await OAuthService.authenticate_or_register_oauth_user(mock_db, profile)
    assert user.id == 22
    assert user.email == "concurrent@scholaris.ai"
    mock_db.rollback.assert_awaited_once()


# =========================================================================
# 5. FastAPI Endpoints Tests (/api/v1/auth/google & /github)
# =========================================================================


def test_api_google_auth_endpoint_success(client: TestClient, monkeypatch):
    """POST /api/v1/auth/google returns 200 with JWT and user object on valid credential."""
    test_user = _make_test_user(user_id=1, email="googleuser@scholaris.ai")

    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db

    mock_profile = OAuthUserProfile(
        provider="google",
        provider_user_id="google-123",
        email="googleuser@scholaris.ai",
    )

    monkeypatch.setattr(
        OAuthService, "verify_google_credential", AsyncMock(return_value=mock_profile)
    )
    monkeypatch.setattr(
        OAuthService, "authenticate_or_register_oauth_user", AsyncMock(return_value=test_user)
    )

    response = client.post("/api/v1/auth/google", json={"credential": "valid_token"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "googleuser@scholaris.ai"


def test_api_google_auth_endpoint_missing_credential(client: TestClient):
    """POST /api/v1/auth/google returns 400 when credential is missing or empty."""

    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db

    response = client.post("/api/v1/auth/google", json={"credential": ""})
    assert response.status_code == 400
    assert "Google ID token credential is required" in response.json()["detail"]


def test_api_google_auth_endpoint_invalid_token(client: TestClient, monkeypatch):
    """POST /api/v1/auth/google returns 400 when token verification fails."""

    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db

    monkeypatch.setattr(
        OAuthService,
        "verify_google_credential",
        AsyncMock(side_effect=ValueError("Invalid Google ID token.")),
    )

    response = client.post("/api/v1/auth/google", json={"credential": "bad_token"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid Google ID token."


def test_api_google_auth_endpoint_inactive_user(client: TestClient, monkeypatch):
    """POST /api/v1/auth/google returns 401 when matched user account is inactive."""
    inactive_user = _make_test_user(is_active=False)

    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db

    mock_profile = OAuthUserProfile(
        provider="google",
        provider_user_id="google-123",
        email="inactive@scholaris.ai",
    )
    monkeypatch.setattr(
        OAuthService, "verify_google_credential", AsyncMock(return_value=mock_profile)
    )
    monkeypatch.setattr(
        OAuthService, "authenticate_or_register_oauth_user", AsyncMock(return_value=inactive_user)
    )

    response = client.post("/api/v1/auth/google", json={"credential": "valid_token"})
    assert response.status_code == 401
    assert "User account is inactive" in response.json()["detail"]


def test_api_github_auth_endpoint_success(client: TestClient, monkeypatch):
    """POST /api/v1/auth/github returns 200 with JWT and user on valid code."""
    test_user = _make_test_user(user_id=2, email="githubuser@scholaris.ai", auth_provider="github")

    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db

    mock_profile = OAuthUserProfile(
        provider="github",
        provider_user_id="github-456",
        email="githubuser@scholaris.ai",
    )

    monkeypatch.setattr(OAuthService, "exchange_github_code", AsyncMock(return_value=mock_profile))
    monkeypatch.setattr(
        OAuthService, "authenticate_or_register_oauth_user", AsyncMock(return_value=test_user)
    )

    response = client.post("/api/v1/auth/github", json={"code": "valid_github_code"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "githubuser@scholaris.ai"


def test_api_github_auth_endpoint_missing_code(client: TestClient):
    """POST /api/v1/auth/github returns 400 when code is empty."""

    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db

    response = client.post("/api/v1/auth/github", json={"code": "   "})
    assert response.status_code == 400
    assert "GitHub authorization code is required" in response.json()["detail"]


def test_api_github_auth_endpoint_failed_exchange(client: TestClient, monkeypatch):
    """POST /api/v1/auth/github returns 400 when code exchange raises ValueError."""

    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db

    monkeypatch.setattr(
        OAuthService,
        "exchange_github_code",
        AsyncMock(side_effect=ValueError("GitHub code exchange failed.")),
    )

    response = client.post("/api/v1/auth/github", json={"code": "bad_code"})
    assert response.status_code == 400
    assert response.json()["detail"] == "GitHub code exchange failed."
