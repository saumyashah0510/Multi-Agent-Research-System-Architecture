"""Core application configuration and environment variable loading.

Assignee Task (Issue #1):
- Configure BaseSettings loading project attributes and DATABASE_URL from .env file.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Locate root directory .env file (4 levels up from backend/app/core/config.py)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_FILE = ROOT_DIR / ".env"

# Load environment variables from root .env file
load_dotenv(dotenv_path=ENV_FILE)


class Settings(BaseSettings):
    """Application settings and environment variables."""

    PROJECT_NAME: str = "Multi-Agent Academic Research Assistant"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/multi_agent_db",
    )

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
