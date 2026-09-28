"""Database session management and async engine setup for Neon PostgreSQL.

Assignee Task (Issue BE-02):
- Configure Async SQLAlchemy engine for Neon PostgreSQL.
- Setup AsyncSessionLocal session factory.
- Implement get_db async dependency generator.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

database_url = settings.DATABASE_URL
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)

engine = create_async_engine(
    database_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency generator for async database sessions."""
    session: AsyncSession = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()
