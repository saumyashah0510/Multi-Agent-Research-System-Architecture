"""Main FastAPI application entry point.

Assignee Task (Issue #1):
- Initialize FastAPI application instance with metadata.
- Configure CORSMiddleware to support frontend integration.
- Mount health check router under API v1 prefix.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.health import router as health_router
from app.api.v1.reviews import router as reviews_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for Multi-Agent Academic Literature Review Assistant",
    version="1.0.0",
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
