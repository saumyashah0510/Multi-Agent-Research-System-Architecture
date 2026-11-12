"""OAuth 2.0 Integration Service handling Google and GitHub identity verification.

Assignee Task (Issue BE-13):
- Implement Google token verification using Google's tokeninfo API via httpx.
- Implement GitHub authorization code exchange and user profile fetch via httpx.
- Implement authenticate_or_register_oauth_user finding or creating the user in Neon DB.
"""

from sqlalchemy.ext.asyncio import AsyncSession

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
        # TODO (Assignee - BE-13):
        # 1. Call GET https://oauth2.googleapis.com/tokeninfo?id_token={credential} using httpx.AsyncClient
        # 2. Verify res.status_code == 200
        # 3. Verify data.get('aud') matches settings.GOOGLE_CLIENT_ID
        # 4. Extract sub, email, name, picture
        # 5. Return OAuthUserProfile(provider="google", provider_user_id=sub, email=email, name=name, avatar_url=picture)
        raise NotImplementedError("Implement verify_google_credential in BE-13")

    @staticmethod
    async def exchange_github_code(code: str) -> OAuthUserProfile:
        """Exchange GitHub authorization code for access token, fetch profile, and return normalized profile.

        Raises:
            ValueError: If code exchange fails or profile cannot be fetched.
        """
        # TODO (Assignee - BE-13):
        # 1. POST https://github.com/login/oauth/access_token with client_id, client_secret, code, headers={"Accept": "application/json"}
        # 2. Extract access_token from response
        # 3. GET https://api.github.com/user with Authorization: Bearer {access_token}
        # 4. If email is null in /user, GET https://api.github.com/user/emails to find primary verified email
        # 5. Return OAuthUserProfile(provider="github", provider_user_id=str(id), email=email, name=name, avatar_url=avatar_url)
        raise NotImplementedError("Implement exchange_github_code in BE-13")

    @staticmethod
    async def authenticate_or_register_oauth_user(
        db: AsyncSession, profile: OAuthUserProfile
    ) -> User:
        """Find existing user by provider ID or email, or create a new user record.

        Returns:
            User: Authenticated or newly created user ORM instance.
        """
        # TODO (Assignee - BE-13):
        # 1. Search User by provider_user_id: select(User).where(User.provider_user_id == profile.provider_user_id)
        # 2. If not found, search User by email: select(User).where(User.email == profile.email.lower().strip())
        # 3. If found:
        #    - Update provider_user_id and auth_provider if not previously set
        #    - Update avatar_url or name if null
        #    - await db.commit(), await db.refresh(user)
        # 4. If not found:
        #    - Create new User(email=profile.email, name=profile.name, avatar_url=profile.avatar_url,
        #                     auth_provider=profile.provider, provider_user_id=profile.provider_user_id,
        #                     hashed_password=None, is_active=True)
        #    - db.add, await db.commit(), await db.refresh
        raise NotImplementedError("Implement authenticate_or_register_oauth_user in BE-13")
