"""Unit tests for Neon PostgreSQL async database engine and session management.

Assignee Task (Issue BE-02):
- Implement test_database_url_async_format asserting engine.url driver scheme.
- Implement test_get_db_generator verifying session creation and lifecycle.
"""

import pytest
from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine, get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase


def test_database_url_async_format():
    """Verify that the engine URL starts with the asyncpg driver prefix."""
    assert str(engine.url).startswith("postgresql+asyncpg://")


@pytest.mark.asyncio
async def test_get_db_generator():
    """Verify that get_db yields an active AsyncSession and closes it on completion."""
    db_gen = get_db()
    session = await anext(db_gen)

    assert isinstance(session, AsyncSession)
    assert session.is_active

    # Closing generator to execute finally block
    try:
        await anext(db_gen)
    except StopAsyncIteration:
        pass


def test_declarative_base():
    """Verify that Base is a subclass of SQLAlchemy DeclarativeBase."""
    assert issubclass(Base, DeclarativeBase)


def test_async_session_factory():
    """Verify that AsyncSessionLocal is properly configured with AsyncSession."""
    session = AsyncSessionLocal()
    assert isinstance(session, AsyncSession)


def test_orm_models_instantiation():
    """Verify BE-03 ORM models (User, LiteratureReview, Paper, ExecutionLog) can be instantiated."""
    from app.models import ExecutionLog, LiteratureReview, Paper, User

    user = User(email="test@example.com", hashed_password="hashed_secret")
    assert user.email == "test@example.com"

    review = LiteratureReview(user_query="CRISPR Gene Editing", status="pending")
    assert review.user_query == "CRISPR Gene Editing"

    paper = Paper(
        title="CRISPR Advances",
        arxiv_id="2301.01234",
        relevance_score=0.95,
        review=review,
    )
    assert paper.title == "CRISPR Advances"
    assert paper.review == review

    log = ExecutionLog(agent_name="SearchAgent", message="Search completed")
    assert log.agent_name == "SearchAgent"
