"""OAuth 2.0 Pydantic Schemas for Google and GitHub Authentication.

Assignee Task (Issue BE-13):
- Define request payloads for Google (token/code) and GitHub (code).
- Define normalized OAuthUserProfile data class.
"""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class GoogleAuthRequest(BaseModel):
    """Payload sent by frontend after user signs in with Google."""

    credential: Optional[str] = Field(
        None, description="Google ID Token JWT returned by Google One Tap / Sign In button"
    )
    code: Optional[str] = Field(
        None, description="Google OAuth Authorization Code (if using popup redirect flow)"
    )
    redirect_uri: Optional[str] = Field(
        None, description="Redirect URI passed in the initial Google authorization request"
    )


class GitHubAuthRequest(BaseModel):
    """Payload sent by frontend after user authorizes through GitHub."""

    code: str = Field(..., description="Authorization code returned by GitHub OAuth callback")


class OAuthUserProfile(BaseModel):
    """Normalized profile extracted from third-party identity providers."""

    provider: str  # 'google' or 'github'
    provider_user_id: str
    email: EmailStr
    name: Optional[str] = None
    avatar_url: Optional[str] = None
