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
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    GEMINI_FALLBACK_MODELS: str = os.getenv(
        "GEMINI_FALLBACK_MODELS", "gemini-2.5-flash,gemini-2.0-flash,gemini-1.5-flash"
    )

    # LangSmith Observability & Tracing
    LANGCHAIN_TRACING_V2: str = os.getenv("LANGCHAIN_TRACING_V2", "false")
    LANGCHAIN_API_KEY: str = os.getenv("LANGCHAIN_API_KEY", "")
    LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "multi-agent-literature-review")
    LANGCHAIN_ENDPOINT: str = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")

    # AWS S3 PDF Storage
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_SESSION_TOKEN: str = os.getenv("AWS_SESSION_TOKEN", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "ap-south-1")
    AWS_S3_BUCKET: str = os.getenv("AWS_S3_BUCKET", "multi-agent-research-pdf-bucket")

    # Hugging Face Hub (Authenticated weights download & high rate limits)
    HF_TOKEN: str = os.getenv("HF_TOKEN", "")

    # Groq Cloud Fallback LLM
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    GROQ_FALLBACK_MODELS: str = os.getenv(
        "GROQ_FALLBACK_MODELS",
        "openai/gpt-oss-20b,llama-3.3-70b-versatile,llama-3.1-8b-instant",
    )

    # JWT Authentication Settings
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY", "scholaris-insecure-secret-key-change-in-production"
    )
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

    @property
    def groq_model_candidates(self) -> list[str]:
        """Return ordered list of Groq models: primary first, followed by fallbacks."""
        primary = self.GROQ_MODEL.strip() if self.GROQ_MODEL else "openai/gpt-oss-120b"
        fallbacks = [
            m.strip()
            for m in self.GROQ_FALLBACK_MODELS.split(",")
            if m.strip() and m.strip() != primary
        ]
        return [primary] + fallbacks

    @property
    def gemini_model_candidates(self) -> list[str]:
        """Return ordered list of Gemini models: primary first, followed by fallbacks."""
        primary = self.GEMINI_MODEL.strip() if self.GEMINI_MODEL else "gemini-3.1-flash-lite"
        fallbacks = [
            m.strip()
            for m in self.GEMINI_FALLBACK_MODELS.split(",")
            if m.strip() and m.strip() != primary
        ]
        return [primary] + fallbacks

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
