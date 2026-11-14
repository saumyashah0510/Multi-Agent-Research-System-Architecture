"""Common FastAPI dependencies for database sessions, current user, and authentication.

Assignee Task (Issue BE-12):
- Implement get_current_user dependency that extracts and validates Bearer JWT.
- Implement get_current_active_user checking is_active status.
- Re-export get_db from app.db.session for clean unified imports.
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import AuthService

# HTTP Bearer scheme with auto_error=False for flexible optional/required auth
security_bearer = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Extract and validate current user from JWT token if present, returning None if unauthenticated."""
    if not auth or not auth.credentials:
        return None

    payload = decode_access_token(auth.credentials)
    if not payload or "sub" not in payload or not payload["sub"]:
        return None

    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        return None

    user = await AuthService.get_user_by_id(db, user_id)
    return user


async def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Enforce authenticated user via Bearer JWT token.

    Raises:
        HTTPException 401 if token is missing, expired, or invalid.
    """
    user = await get_current_user_optional(auth, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials or session has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure the authenticated user account is active."""
    if not getattr(current_user, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account.",
        )
    return current_user
