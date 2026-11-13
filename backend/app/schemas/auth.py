"""Authentication Pydantic schemas for request validation and API responses.

Assignee Task (Issue BE-12):
- Define UserRegisterRequest, UserLoginRequest.
- Define UserResponse, TokenResponse, and TokenPayload.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserRegisterRequest(BaseModel):
    """Payload for registering a new user with email and password."""

    email: EmailStr = Field(..., description="Unique user email address")
    password: str = Field(..., min_length=6, max_length=128, description="User plaintext password")
    name: Optional[str] = Field(None, max_length=255, description="User full display name")

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password cannot exceed 72 bytes.")
        return v


class UserLoginRequest(BaseModel):
    """Payload for logging in with email and password."""

    email: EmailStr = Field(..., description="Registered user email address")
    password: str = Field(..., description="User plaintext password")

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password cannot exceed 72 bytes.")
        return v


class UserResponse(BaseModel):
    """Public user profile data returned to frontend."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    auth_provider: str = "local"
    is_active: bool = True
    created_at: datetime


class TokenResponse(BaseModel):
    """JWT Bearer token response."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenPayload(BaseModel):
    """Decoded JWT payload data."""

    sub: Optional[str] = None
    exp: Optional[int] = None
