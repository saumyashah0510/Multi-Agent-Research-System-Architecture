"""Authentication Service Layer handling user registration, credential check, and lookups.

Assignee Task (Issue BE-12):
- Implement register_user with duplicate email detection and password hashing.
- Implement authenticate_user verifying email existence and bcrypt password.
- Implement get_user_by_id and get_user_by_email queries.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.auth import UserRegisterRequest


class AuthService:
    """Authentication and user management service layer."""

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """Fetch a user record by email address."""
        # TODO (Assignee - BE-12): Execute select(User).where(User.email == email.lower().strip())
        stmt = select(User).where(User.email == email.lower().strip())
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        """Fetch a user record by primary key ID."""
        # TODO (Assignee - BE-12): Execute select(User).where(User.id == user_id)
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def register_user(db: AsyncSession, req: UserRegisterRequest) -> User:
        """Create a new user account with hashed password.

        Raises:
            ValueError: If the email is already registered.
        """
        # TODO (Assignee - BE-12):
        # 1. Check if user already exists via get_user_by_email; raise ValueError if found
        # 2. Hash password with get_password_hash(req.password)
        # 3. Create User record with email, hashed_password, name, auth_provider="local", is_active=True
        # 4. db.add(new_user), await db.commit(), await db.refresh(new_user)
        # 5. Return new_user
        raise NotImplementedError("Implement register_user in BE-12")

    @staticmethod
    async def authenticate_user(
        db: AsyncSession, email: str, plain_password: str
    ) -> Optional[User]:
        """Validate user email and password credentials.

        Returns:
            User record if valid, None if invalid or password does not match.
        """
        # TODO (Assignee - BE-12):
        # 1. Look up user by email via get_user_by_email
        # 2. If user is None or user.hashed_password is None (e.g. OAuth user), return None
        # 3. Verify password via verify_password(plain_password, user.hashed_password)
        # 4. Return user if valid, else None
        raise NotImplementedError("Implement authenticate_user in BE-12")
