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

from app.core.config import settings


# ==========================================================
# Database Engine Configuration
# ==========================================================

IS_SQLITE = "sqlite" in settings.DATABASE_URL.lower()

engine_options = {
    "echo": settings.DEBUG,
    "pool_pre_ping": True,
}

# Connection pooling is not supported by SQLite
if not IS_SQLITE:
    engine_options.update(
        {
            "pool_size": 10,
            "max_overflow": 20,
        }
    )

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