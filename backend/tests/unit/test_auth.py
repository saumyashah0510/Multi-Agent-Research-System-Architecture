"""Unit tests for Authentication, JWT Security, and Password Hashing (Issue BE-12)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.api.deps import (
    get_current_active_user,
    get_current_user,
    get_db,
)
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from app.main import app
from app.models.user import User
from app.schemas.auth import UserLoginRequest, UserRegisterRequest
from app.services.auth_service import AuthService
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError


def _make_test_user(
    user_id: int = 1,
    email: str = "test@scholaris.ai",
    password: str = "ValidPassword123",
    name: str = "Dr. Jane Doe",
    is_active: bool = True,
    auth_provider: str = "local",
    hashed_password: str = None,
) -> User:
    """Helper to instantiate a User mock/model for unit testing."""
    user = User(
        id=user_id,
        email=email,
        name=name,
        hashed_password=hashed_password or get_password_hash(password),
        avatar_url=None,
        auth_provider=auth_provider,
        provider_user_id=None,
        is_active=is_active,
        created_at=datetime.now(timezone.utc),
    )
    return user


def test_auth_request_schema_validation():
    """Verify Pydantic validation on user registration and login payloads."""
    reg = UserRegisterRequest(
        email="test@scholaris.ai",
        password="ValidPassword123",
        name="Dr. Jane Doe",
    )
    assert reg.email == "test@scholaris.ai"
    assert reg.name == "Dr. Jane Doe"

    login = UserLoginRequest(
        email="test@scholaris.ai",
        password="ValidPassword123",
    )
    assert login.email == "test@scholaris.ai"


def test_password_hashing_and_verification():
    """Verify that bcrypt hashes correctly and verifies matching passwords."""
    password = "SuperSecretPassword123!"
    hashed = get_password_hash(password)

    assert hashed != password
    assert hashed.startswith("$2b$")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_password_longer_than_72_bytes_rejected():
    """Verify passwords exceeding 72 bytes are rejected by schema and security."""
    long_password = "A" * 73
    with pytest.raises(ValueError):
        UserRegisterRequest(
            email="toolong@scholaris.ai",
            password=long_password,
        )
    with pytest.raises(ValueError, match="cannot exceed 72 bytes"):
        get_password_hash(long_password)
    assert verify_password(long_password, "$2b$12$fakehash") is False


def test_jwt_access_token_creation_and_decoding():
    """Verify that JWT tokens encode subject and decode payload accurately."""
    user_id = 42
    token = create_access_token(subject=user_id, extra_claims={"email": "researcher@example.com"})

    assert isinstance(token, str)
    assert len(token) > 20

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["email"] == "researcher@example.com"
    assert "exp" in payload


def test_jwt_invalid_or_expired_token():
    """Verify that expired or tampered tokens return None safely."""
    # Expired token
    expired_token = create_access_token(
        subject=1,
        expires_delta=timedelta(seconds=-10),
    )
    assert decode_access_token(expired_token) is None

    # Malformed token
    assert decode_access_token("not.a.valid.jwt.token") is None
    assert decode_access_token("") is None


@pytest.mark.asyncio
async def test_auth_service_register_user_success():
    """Verify that AuthService creates a new user when email is unique."""
    mock_db = AsyncMock()

    # Simulate get_user_by_email returning None
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    req = UserRegisterRequest(
        email="newuser@scholaris.ai",
        password="SecurePassword456",
        name="Alice Smith",
    )

    async def fake_refresh(instance):
        instance.id = 99
        instance.created_at = datetime.now(timezone.utc)

    mock_db.refresh.side_effect = fake_refresh

    user = await AuthService.register_user(mock_db, req)

    assert user.email == "newuser@scholaris.ai"
    assert user.name == "Alice Smith"
    assert user.hashed_password.startswith("$2b$")
    assert user.auth_provider == "local"
    assert user.is_active is True
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_auth_service_register_user_duplicate_email():
    """Verify that duplicate email registration raises ValueError."""
    mock_db = AsyncMock()
    existing_user = _make_test_user(email="existing@scholaris.ai")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_user
    mock_db.execute.return_value = mock_result

    req = UserRegisterRequest(
        email="existing@scholaris.ai",
        password="SecurePassword456",
    )

    with pytest.raises(ValueError, match="An account with this email address already exists."):
        await AuthService.register_user(mock_db, req)


@pytest.mark.asyncio
async def test_auth_service_register_user_integrity_error_rollback():
    """Verify that IntegrityError on commit triggers rollback and raises ValueError."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    mock_db.commit.side_effect = IntegrityError("duplicate key", params=None, orig=Exception())

    req = UserRegisterRequest(
        email="concurrent@scholaris.ai",
        password="SecurePassword456",
    )

    with pytest.raises(ValueError, match="already exists"):
        await AuthService.register_user(mock_db, req)
    mock_db.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_auth_service_authenticate_user():
    """Verify credential verification for matching and mismatched passwords."""
    mock_db = AsyncMock()
    test_user = _make_test_user(email="user@scholaris.ai", password="CorrectPassword123")

    # 1. Matching credentials
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = test_user
    mock_db.execute.return_value = mock_result

    auth_user = await AuthService.authenticate_user(
        mock_db, "user@scholaris.ai", "CorrectPassword123"
    )
    assert auth_user is not None
    assert auth_user.id == test_user.id

    # 2. Wrong password
    fail_user = await AuthService.authenticate_user(mock_db, "user@scholaris.ai", "WrongPassword")
    assert fail_user is None

    # 3. Unregistered email
    mock_result.scalar_one_or_none.return_value = None
    not_found = await AuthService.authenticate_user(mock_db, "unknown@scholaris.ai", "Password")
    assert not_found is None

    # 4. OAuth user without password
    oauth_user = _make_test_user(email="oauth@scholaris.ai", auth_provider="google")
    oauth_user.hashed_password = None
    mock_result.scalar_one_or_none.return_value = oauth_user
    oauth_auth = await AuthService.authenticate_user(mock_db, "oauth@scholaris.ai", "AnyPassword")
    assert oauth_auth is None


@pytest.mark.asyncio
async def test_deps_get_current_active_user_inactive():
    """Verify that an inactive account raises 400 Bad Request."""
    inactive_user = _make_test_user(is_active=False)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_active_user(current_user=inactive_user)
    assert exc_info.value.status_code == 400
    assert "Inactive user account" in exc_info.value.detail


@pytest.fixture
def client():
    """Fixture providing a FastAPI TestClient with DB overrides cleared after each test."""
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_api_register_endpoint_success(client: TestClient):
    """POST /api/v1/auth/register returns 201 Created with valid JWT and sanitized user."""
    test_user = _make_test_user(user_id=10, email="alice@example.com")

    async def override_get_db():
        mock_session = AsyncMock()
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    with patch.object(AuthService, "register_user", new=AsyncMock(return_value=test_user)):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "alice@example.com",
                "password": "Password123!",
                "name": "Alice",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "alice@example.com"
    assert data["user"]["id"] == 10
    assert "hashed_password" not in data["user"]


def test_api_register_endpoint_duplicate_email(client: TestClient):
    """POST /api/v1/auth/register returns 400 Bad Request for duplicate email."""

    async def override_get_db():
        mock_session = AsyncMock()
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    with patch.object(
        AuthService,
        "register_user",
        new=AsyncMock(side_effect=ValueError("An account with this email address already exists.")),
    ):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "Password123!",
            },
        )

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_api_login_endpoint_success(client: TestClient):
    """POST /api/v1/auth/login returns 200 OK with valid JWT for valid credentials."""
    test_user = _make_test_user(user_id=12, email="bob@example.com")

    async def override_get_db():
        mock_session = AsyncMock()
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    with patch.object(AuthService, "authenticate_user", new=AsyncMock(return_value=test_user)):
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "bob@example.com",
                "password": "CorrectPassword!",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "bob@example.com"


def test_api_login_endpoint_invalid_credentials(client: TestClient):
    """POST /api/v1/auth/login returns 401 Unauthorized for wrong credentials."""

    async def override_get_db():
        mock_session = AsyncMock()
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    with patch.object(AuthService, "authenticate_user", new=AsyncMock(return_value=None)):
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "bob@example.com",
                "password": "WrongPassword!",
            },
        )

    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_api_login_endpoint_inactive_user(client: TestClient):
    """POST /api/v1/auth/login returns 401 Unauthorized for inactive user."""
    test_user = _make_test_user(user_id=14, email="inactive@example.com", is_active=False)

    async def override_get_db():
        mock_session = AsyncMock()
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    with patch.object(AuthService, "authenticate_user", new=AsyncMock(return_value=test_user)):
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "inactive@example.com",
                "password": "Password123!",
            },
        )

    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_api_get_me_endpoint_success(client: TestClient):
    """GET /api/v1/auth/me returns current user profile with valid Bearer token."""
    test_user = _make_test_user(user_id=15, email="me@example.com")
    token = create_access_token(subject=test_user.id)

    async def override_get_current_active_user():
        return test_user

    app.dependency_overrides[get_current_active_user] = override_get_current_active_user

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert data["id"] == 15


@pytest.mark.asyncio
async def test_deps_get_current_user_end_to_end():
    """Verify get_current_user extracts token and fetches user from DB."""
    test_user = _make_test_user(user_id=15, email="me@example.com")
    token = create_access_token(subject=test_user.id)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    mock_db = AsyncMock()
    with patch.object(AuthService, "get_user_by_id", new=AsyncMock(return_value=test_user)):
        user = await get_current_user(auth=credentials, db=mock_db)
        assert user.id == 15
        assert user.email == "me@example.com"


@pytest.mark.asyncio
async def test_deps_get_current_user_invalid():
    """Verify get_current_user raises 401 when token is invalid or missing."""
    mock_db = AsyncMock()
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(auth=None, db=mock_db)
    assert exc_info.value.status_code == 401


def test_api_get_me_endpoint_unauthorized(client: TestClient):
    """GET /api/v1/auth/me returns 401 Unauthorized without Bearer token or invalid token."""
    # No auth header
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401

    # Invalid token header
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.payload"},
    )
    assert response.status_code == 401
