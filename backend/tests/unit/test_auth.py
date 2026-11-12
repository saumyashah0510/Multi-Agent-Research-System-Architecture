"""Unit tests for Authentication, JWT Security, and Password Hashing (Issue BE-12)."""

import pytest
from app.schemas.auth import UserLoginRequest, UserRegisterRequest


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


@pytest.mark.skip(reason="Assignee will unskip upon implementing security.py in BE-12")
def test_password_hashing_and_verification():
    """Verify that bcrypt hashes correctly and verifies matching passwords."""
    from app.core.security import get_password_hash, verify_password

    password = "SuperSecretPassword123!"
    hashed = get_password_hash(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


@pytest.mark.skip(reason="Assignee will unskip upon implementing security.py in BE-12")
def test_jwt_access_token_creation_and_decoding():
    """Verify that JWT tokens encode subject and decode payload accurately."""
    from app.core.security import create_access_token, decode_access_token

    user_id = 42
    token = create_access_token(subject=user_id, extra_claims={"email": "researcher@example.com"})

    assert isinstance(token, str)
    assert len(token) > 20

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["email"] == "researcher@example.com"
    assert "exp" in payload
