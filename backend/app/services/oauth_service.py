"""OAuth 2.0 Integration Service handling Google and GitHub identity verification.

Assignee Task (Issue BE-13):
- Implement Google token verification using Google's tokeninfo API via httpx.
- Implement GitHub authorization code exchange and user profile fetch via httpx.
- Implement authenticate_or_register_oauth_user finding or creating the user in Neon DB.
"""

import inspect
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User
from app.schemas.oauth import OAuthUserProfile


class OAuthService:
    """Service for validating OAuth tokens and linking third-party accounts."""

    @staticmethod
    async def verify_google_credential(credential: str) -> OAuthUserProfile:
        """Verify Google ID token via Google's tokeninfo endpoint and return normalized profile.

        Raises:
            ValueError: If the token is invalid or does not belong to this application's CLIENT_ID.
        """
        if not credential or not credential.strip():
            raise ValueError("Google ID token credential must not be empty.")

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.get(
                    "https://oauth2.googleapis.com/tokeninfo",
                    params={"id_token": credential},
                )
            except Exception as exc:
                raise ValueError(
                    f"Failed to communicate with Google authentication server: {exc}"
                ) from exc

        if res.status_code != 200:
            raise ValueError("Invalid Google ID token.")

        payload: Dict[str, Any] = res.json()

        # Verify token audience if GOOGLE_CLIENT_ID is configured
        if settings.GOOGLE_CLIENT_ID:
            aud = payload.get("aud")
            if aud != settings.GOOGLE_CLIENT_ID:
                raise ValueError("Google ID token audience mismatch.")

        sub = payload.get("sub")
        email = payload.get("email")
        if not sub or not email:
            raise ValueError("Google ID token missing required subject or email.")

        return OAuthUserProfile(
            provider="google",
            provider_user_id=str(sub),
            email=email,
            name=payload.get("name"),
            avatar_url=payload.get("picture"),
        )

    @staticmethod
    async def exchange_github_code(code: str) -> OAuthUserProfile:
        """Exchange GitHub authorization code for access token, fetch profile, and return normalized profile.

        Raises:
            ValueError: If code exchange fails or profile cannot be fetched.
        """
        if not code or not code.strip():
            raise ValueError("GitHub authorization code must not be empty.")

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                token_res = await client.post(
                    "https://github.com/login/oauth/access_token",
                    json={
                        "client_id": settings.GITHUB_CLIENT_ID,
                        "client_secret": settings.GITHUB_CLIENT_SECRET,
                        "code": code,
                    },
                    headers={"Accept": "application/json"},
                )
            except Exception as exc:
                raise ValueError(
                    f"Failed to communicate with GitHub OAuth token endpoint: {exc}"
                ) from exc

            if token_res.status_code != 200:
                raise ValueError("GitHub code exchange failed.")

            token_data: Dict[str, Any] = token_res.json()
            access_token = token_data.get("access_token")
            if not access_token:
                error_desc = (
                    token_data.get("error_description")
                    or token_data.get("error")
                    or "GitHub code exchange failed."
                )
                raise ValueError(error_desc)

            auth_headers = {
                "Authorization": f"Bearer {access_token}",
                "User-Agent": "Scholaris-Research-Assistant",
                "Accept": "application/json",
            }

            try:
                user_res = await client.get(
                    "https://api.github.com/user",
                    headers=auth_headers,
                )
            except Exception as exc:
                raise ValueError(f"Failed to fetch GitHub user profile: {exc}") from exc

            if user_res.status_code != 200:
                raise ValueError("Failed to fetch GitHub user profile.")

            user_data: Dict[str, Any] = user_res.json()
            user_id = user_data.get("id")
            if not user_id:
                raise ValueError("GitHub user profile missing ID.")

            primary_email: Optional[str] = user_data.get("email")
            if not primary_email:
                try:
                    emails_res = await client.get(
                        "https://api.github.com/user/emails",
                        headers=auth_headers,
                    )
                    if emails_res.status_code == 200:
                        emails_list: List[Dict[str, Any]] = emails_res.json()
                        if isinstance(emails_list, list):
                            for em in emails_list:
                                if em.get("primary") and em.get("verified"):
                                    primary_email = em.get("email")
                                    break
                            if not primary_email:
                                for em in emails_list:
                                    if em.get("verified"):
                                        primary_email = em.get("email")
                                        break
                            if not primary_email and emails_list:
                                primary_email = emails_list[0].get("email")
                except Exception:
                    pass

            if not primary_email:
                raise ValueError("Could not obtain verified email address from GitHub account.")

        return OAuthUserProfile(
            provider="github",
            provider_user_id=str(user_id),
            email=primary_email,
            name=user_data.get("name") or user_data.get("login"),
            avatar_url=user_data.get("avatar_url"),
        )

    @staticmethod
    async def authenticate_or_register_oauth_user(
        db: AsyncSession, profile: OAuthUserProfile
    ) -> User:
        """Find existing user by provider ID or email, or create a new user record.

        Returns:
            User: Authenticated or newly created user ORM instance.
        """
        # 1. Search User by provider_user_id
        stmt = select(User).where(User.provider_user_id == str(profile.provider_user_id))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        # 2. If not found, search User by normalized email
        if user is None:
            stmt = select(User).where(User.email == profile.email.lower().strip())
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

        if user is not None:
            # Update missing provider or profile metadata without duplicating row
            if not user.provider_user_id:
                user.provider_user_id = str(profile.provider_user_id)
            if not user.avatar_url and profile.avatar_url:
                user.avatar_url = profile.avatar_url
            if not user.name and profile.name:
                user.name = profile.name

            commit_fn = getattr(db, "commit", None)
            if commit_fn is not None:
                commit_res = commit_fn()
                if inspect.isawaitable(commit_res):
                    await commit_res

            refresh_fn = getattr(db, "refresh", None)
            if refresh_fn is not None:
                refresh_res = refresh_fn(user)
                if inspect.isawaitable(refresh_res):
                    await refresh_res

            return user

        # 3. Register brand-new OAuth user
        new_user = User(
            email=profile.email.lower().strip(),
            name=profile.name.strip() if profile.name else None,
            avatar_url=profile.avatar_url,
            auth_provider=profile.provider,
            provider_user_id=str(profile.provider_user_id),
            hashed_password=None,
            is_active=True,
        )

        add_fn = getattr(db, "add", None)
        if add_fn is not None:
            add_res = add_fn(new_user)
            if inspect.isawaitable(add_res):
                await add_res

        try:
            commit_fn = getattr(db, "commit", None)
            if commit_fn is not None:
                commit_res = commit_fn()
                if inspect.isawaitable(commit_res):
                    await commit_res
        except IntegrityError:
            # Handle concurrent race condition for duplicate email
            rollback_fn = getattr(db, "rollback", None)
            if rollback_fn is not None:
                rollback_res = rollback_fn()
                if inspect.isawaitable(rollback_res):
                    await rollback_res

            stmt = select(User).where(User.email == profile.email.lower().strip())
            res = await db.execute(stmt)
            existing_user = res.scalar_one_or_none()
            if existing_user is not None:
                return existing_user
            raise

        refresh_fn = getattr(db, "refresh", None)
        if refresh_fn is not None:
            refresh_res = refresh_fn(new_user)
            if inspect.isawaitable(refresh_res):
                await refresh_res

        return new_user
