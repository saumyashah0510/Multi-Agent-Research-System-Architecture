"""Authentication Service Layer handling user registration, credential check, and lookups.

Assignee Task (Issue BE-12):
- Implement register_user with duplicate email detection and password hashing.
- Implement authenticate_user verifying email existence and bcrypt password.
- Implement get_user_by_id and get_user_by_email queries.
"""

import asyncio
import inspect
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.auth import UserRegisterRequest


class AuthService:
    """Authentication and user management service layer."""

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """Fetch a user record by email address."""
        stmt = select(User).where(User.email == email.lower().strip())
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        """Fetch a user record by primary key ID."""
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def register_user(db: AsyncSession, req: UserRegisterRequest) -> User:
        """Create a new user account with hashed password.

        Raises:
            ValueError: If the email is already registered.
        """
        existing_user = await AuthService.get_user_by_email(db, req.email)
        if existing_user is not None:
            raise ValueError("An account with this email address already exists.")

        hashed_password = await asyncio.to_thread(get_password_hash, req.password)
        new_user = User(
            email=req.email.lower().strip(),
            hashed_password=hashed_password,
            name=req.name.strip() if req.name else None,
            auth_provider="local",
            is_active=True,
        )
        add_res = db.add(new_user)
        if inspect.isawaitable(add_res):
            await add_res

        try:
            commit_res = db.commit()
            if inspect.isawaitable(commit_res):
                await commit_res
        except IntegrityError as exc:
            rollback_fn = getattr(db, "rollback", None)
            if rollback_fn is not None:
                rollback_res = rollback_fn()
                if inspect.isawaitable(rollback_res):
                    await rollback_res
            raise ValueError("An account with this email address already exists.") from exc

        refresh_fn = getattr(db, "refresh", None)
        if refresh_fn is not None:
            refresh_res = refresh_fn(new_user)
            if inspect.isawaitable(refresh_res):
                await refresh_res

        return new_user

    @staticmethod
    async def authenticate_user(
        db: AsyncSession, email: str, plain_password: str
    ) -> Optional[User]:
        """Validate user email and password credentials.

        Returns:
            User record if valid, None if invalid or password does not match.
        """
        user = await AuthService.get_user_by_email(db, email)
        if user is None or user.hashed_password is None:
            return None

        is_valid = await asyncio.to_thread(verify_password, plain_password, user.hashed_password)
        if not is_valid:
            return None

        return user
