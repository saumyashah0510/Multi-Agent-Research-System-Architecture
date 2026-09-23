"""Main FastAPI application entry point skeleton.

Assignee Task (Issue #1):
- Initialize FastAPI application instance with metadata.
- Configure CORSMiddleware to support frontend integration.
- Mount health check router under API v1 prefix.
"""

from fastapi import FastAPI

from app.core.config import settings

# TODO (Assignee): Import CORSMiddleware and router from app.api.v1.health

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for Multi-Agent Academic Literature Review Assistant",
    version="1.0.0",
)

# TODO (Assignee): Add CORSMiddleware allowing cross-origin requests

# TODO (Assignee): Register health router with prefix=settings.API_V1_STR
