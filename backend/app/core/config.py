"""Core application configuration and environment variable loading placeholder.

Assignee Task (Issue #1):
- Configure BaseSettings loading project attributes and DATABASE_URL from .env file.
"""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings and environment variables."""

    PROJECT_NAME: str = "Multi-Agent Academic Research Assistant"
    API_V1_STR: str = "/api/v1"

    # TODO (Assignee): Verify DATABASE_URL reading from environment / .env file
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://user:pass@ep-cool-db.us-east-2.aws.neon.tech/neondb?sslmode=require",
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
