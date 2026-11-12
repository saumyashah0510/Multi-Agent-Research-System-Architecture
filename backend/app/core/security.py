"""Security and Cryptography Utilities for JWT & Password Hashing.

Assignee Task (Issue BE-12):
- Implement password hashing and verification using passlib (bcrypt).
- Implement JWT access token creation with expiration using pyjwt.
- Implement token decode and payload extraction with signature verification.
"""

from datetime import timedelta
from typing import Any, Dict, Optional

from passlib.context import CryptContext

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hashed representation."""
    # TODO (Assignee - BE-12): Implement password verification using pwd_context.verify
    raise NotImplementedError("Implement verify_password in BE-12")


def get_password_hash(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    # TODO (Assignee - BE-12): Implement password hashing using pwd_context.hash
    raise NotImplementedError("Implement get_password_hash in BE-12")


def create_access_token(
    subject: str | int,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a signed JWT access token."""
    # TODO (Assignee - BE-12):
    # 1. Determine expiration time (now + expires_delta or default from settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # 2. Build payload with 'sub' (subject as str), 'exp', and 'iat'
    # 3. Merge extra_claims if provided
    # 4. Encode token with settings.JWT_SECRET_KEY and settings.JWT_ALGORITHM
    raise NotImplementedError("Implement create_access_token in BE-12")


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT access token, returning payload dictionary or None if invalid."""
    # TODO (Assignee - BE-12):
    # 1. Decode token using settings.JWT_SECRET_KEY and algorithms=[settings.JWT_ALGORITHM]
    # 2. Return payload dict if valid, catch jwt.PyJWTError and return None
    raise NotImplementedError("Implement decode_access_token in BE-12")
