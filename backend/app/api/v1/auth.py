"""Authentication API Endpoints (Register, Login, Me).

Assignee Task (Issue BE-12):
- Implement POST /register: creates user, returns token and user payload.
- Implement POST /login: authenticates credentials, returns JWT token.
- Implement GET /me: returns authenticated user profile.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.schemas.oauth import GitHubAuthRequest, GoogleAuthRequest
from app.services.auth_service import AuthService
from app.services.oauth_service import OAuthService

router = APIRouter()


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    payload: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Create a new user account with email and password, issuing a JWT access token."""
    try:
        user = await AuthService.register_user(db, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    token = create_access_token(subject=user.id)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate user and obtain JWT token",
)
async def login(
    payload: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Validate email and password, returning a signed JWT access token."""
    user = await AuthService.authenticate_user(db, payload.email, payload.password)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(subject=user.id)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile",
)
async def get_me(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """Fetch the authenticated user's profile details."""
    return UserResponse.model_validate(current_user)


@router.post(
    "/google",
    response_model=TokenResponse,
    summary="Authenticate with Google OAuth ID token or authorization code",
)
async def google_auth(
    payload: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Verify Google ID token or exchange authorization code, link or create user, and issue application JWT token."""
    has_credential = bool(payload.credential and payload.credential.strip())
    has_code = bool(payload.code and payload.code.strip())

    if not has_credential and not has_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google ID token credential or authorization code is required.",
        )

    try:
        if has_code:
            profile = await OAuthService.exchange_google_code(
                code=payload.code.strip(),
                redirect_uri=payload.redirect_uri.strip() if payload.redirect_uri else None,
            )
        else:
            profile = await OAuthService.verify_google_credential(payload.credential.strip())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    user = await OAuthService.authenticate_or_register_oauth_user(db, profile)
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(subject=user.id)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/github",
    response_model=TokenResponse,
    summary="Authenticate with GitHub OAuth authorization code",
)
async def github_auth(
    payload: GitHubAuthRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Exchange GitHub OAuth authorization code for profile, link or create user, and issue JWT."""
    if not payload.code or not payload.code.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub authorization code is required.",
        )

    try:
        profile = await OAuthService.exchange_github_code(payload.code)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    user = await OAuthService.authenticate_or_register_oauth_user(db, profile)
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(subject=user.id)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )
