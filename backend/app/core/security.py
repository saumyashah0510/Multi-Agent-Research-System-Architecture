"""Security and Cryptography Utilities for JWT & Password Hashing.

Assignee Task (Issue BE-12):
- Implement password hashing and verification using passlib (bcrypt).
- Implement JWT access token creation with expiration using pyjwt.
- Implement token decode and payload extraction with signature verification.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
import jwt
from passlib.context import CryptContext

from app.core.config import settings

# Ensure compatibility between passlib and bcrypt >= 4.1.0
if not hasattr(bcrypt, "__about__"):

    class _About:
        __version__ = getattr(bcrypt, "__version__", "4.0.1")

    bcrypt.__about__ = _About()

_orig_hashpw = bcrypt.hashpw


def _safe_hashpw(password: Any, salt: Any) -> Any:
    if isinstance(password, str):
        password = password.encode("utf-8")
    if len(password) > 72:
        password = password[:72]
    return _orig_hashpw(password, salt)


bcrypt.hashpw = _safe_hashpw

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hashed representation."""
    if len(plain_password.encode("utf-8")) > 72:
        return False
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password cannot exceed 72 bytes.")
    return pwd_context.hash(password)


def create_access_token(
    subject: str | int,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a signed JWT access token."""
    if expires_delta is not None:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    payload: Dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    if extra_claims:
        payload.update(extra_claims)

    encoded_jwt: str = jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT access token, returning payload dictionary or None if invalid."""
    try:
        decoded_payload: Dict[str, Any] = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return decoded_payload
    except jwt.PyJWTError:
        return None
