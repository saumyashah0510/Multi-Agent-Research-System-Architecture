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
