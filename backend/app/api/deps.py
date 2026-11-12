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

from app.db.session import get_db
from app.models.user import User

# HTTP Bearer scheme with auto_error=False for flexible optional/required auth
security_bearer = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Extract and validate current user from JWT token if present, returning None if unauthenticated."""
    # TODO (Assignee - BE-12):
    # 1. If not auth or not auth.credentials, return None
    # 2. Decode token using decode_access_token(auth.credentials)
    # 3. If payload is None or "sub" not present, return None
    # 4. Fetch user from db using AuthService.get_user_by_id(db, int(payload["sub"]))
    # 5. Return user
    return None


async def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Enforce authenticated user via Bearer JWT token.

    Raises:
        HTTPException 401 if token is missing, expired, or invalid.
    """
    # TODO (Assignee - BE-12):
    # Call get_current_user_optional(auth, db)
    # If user is None, raise HTTPException 401 UNAUTHORIZED
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
    # TODO (Assignee - BE-12):
    # Check current_user.is_active. If False, raise 400 Bad Request
    if not getattr(current_user, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account.",
        )
    return current_user
