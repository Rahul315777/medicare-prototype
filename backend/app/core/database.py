"""
Async SQLAlchemy Database Configuration
- Async Engine
- Async Session
- Declarative Base
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings


# ==========================================================
# Database Engine Configuration
# ==========================================================

IS_SQLITE = "sqlite" in settings.DATABASE_URL.lower()

engine_options = {
    "echo": settings.DEBUG,
    "pool_pre_ping": True,
}

if not IS_SQLITE:
    # Connection pooling (with a real, size-bounded pool) applies to
    # Postgres/production.
    engine_options.update(
        {
            "pool_size": 10,
            "max_overflow": 20,
        }
    )
else:
    # SQLite doesn't benefit from a persistent connection pool the way
    # Postgres does, and a pooled aiosqlite connection is bound to whichever
    # asyncio event loop was running when it was opened. That's invisible in
    # production (uvicorn only ever runs one event loop), but under
    # pytest-asyncio — where each test function can get its own event loop —
    # reusing a pooled connection from a previous test's (now-closed) loop
    # raises "Event loop is closed". NullPool opens a fresh aiosqlite
    # connection per checkout and closes it afterwards instead of pooling it,
    # which sidesteps the issue entirely without touching production
    # (Postgres) behavior at all.
    engine_options["poolclass"] = NullPool

engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_options,
)


# ==========================================================
# Session Factory
# ==========================================================

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ==========================================================
# Base Model
# ==========================================================

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


# ==========================================================
# Database Dependency
# ==========================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.
    Automatically commits on success and rolls back on failure.
    """

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()

        except Exception:
            await session.rollback()
            raise

        finally:
            await session.close()