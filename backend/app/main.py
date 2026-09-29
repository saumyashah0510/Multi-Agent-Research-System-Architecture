"""Main FastAPI application entry point.

Assignee Task (Issue #1):
- Initialize FastAPI application instance with metadata.
- Configure CORSMiddleware to support frontend integration.
- Mount health check router under API v1 prefix.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

import app.models  # noqa: F401
from app.api.v1.health import router as health_router
from app.api.v1.reviews import router as reviews_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager ensuring DB tables and pgvector extension exist in Neon PostgreSQL on startup."""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        print(f"LIFESPAN DB INIT NOTICE: Could not initialize DB tables on startup ({e})")
    yield
    try:
        await engine.dispose()
    except Exception:
        pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for Multi-Agent Academic Literature Review Assistant",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix=settings.API_V1_STR, tags=["health"])
app.include_router(reviews_router, prefix=f"{settings.API_V1_STR}/reviews", tags=["reviews"])
