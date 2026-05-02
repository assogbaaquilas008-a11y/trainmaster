"""
Async database setup using SQLAlchemy 2.x.

Uses aiosqlite for local dev and asyncpg for PostgreSQL in production.
Switch by changing DATABASE_URL in .env — no code changes needed.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
# connect_args only needed for SQLite (disables same-thread check for async)
connect_args = {}
if "sqlite" in settings.DATABASE_URL:
    connect_args = {"check_same_thread": False}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=(settings.ENV == "development"),
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


async def init_db() -> None:
    """Create all tables on startup (dev convenience). Use Alembic in prod."""
    async with engine.begin() as conn:
        # Import models so Base.metadata is populated
        from app import models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------
async def get_db() -> AsyncSession:  # type: ignore[return]
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
