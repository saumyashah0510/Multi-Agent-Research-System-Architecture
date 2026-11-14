"""Database session management and async engine setup for Neon PostgreSQL.

Assignee Task (Issue BE-02):
- Configure Async SQLAlchemy engine for Neon PostgreSQL.
- Setup AsyncSessionLocal session factory.
- Implement get_db async dependency generator.
"""

import socket
from collections.abc import AsyncGenerator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Fallback DNS resolution for restricted/campus networks where local DNS refuses Neon host
try:
    import dns.resolver

    _orig_getaddrinfo = socket.getaddrinfo

    def _resilient_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        try:
            return _orig_getaddrinfo(host, port, family, type, proto, flags)
        except socket.gaierror:
            try:
                resolver = dns.resolver.Resolver()
                resolver.nameservers = ["8.8.8.8", "1.1.1.1"]
                answers = resolver.resolve(host, "A")
                if answers:
                    ip = str(answers[0])
                    return _orig_getaddrinfo(ip, port, family, type, proto, flags)
            except Exception:
                pass
            raise

    socket.getaddrinfo = _resilient_getaddrinfo
except ImportError:
    pass

raw_url = settings.DATABASE_URL or "postgresql://postgres:postgres@localhost:5432/multi_agent_db"
if raw_url.startswith("postgresql://"):
    raw_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif raw_url.startswith("postgres://"):
    raw_url = raw_url.replace("postgres://", "postgresql+asyncpg://", 1)


# Parse and sanitize URL query parameters for asyncpg compatibility
parsed = urlparse(raw_url)
if parsed.query:
    params = parse_qs(parsed.query)
    # Map sslmode to ssl
    if "sslmode" in params and "ssl" not in params:
        params["ssl"] = params.pop("sslmode")
    else:
        params.pop("sslmode", None)
    # Remove asyncpg-incompatible parameters (e.g., channel_binding, target_session_attrs)
    params.pop("channel_binding", None)
    params.pop("target_session_attrs", None)
    params.pop("gssencmode", None)

    new_query = urlencode(params, doseq=True)
    database_url = urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment,
        )
    )
else:
    database_url = raw_url


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
