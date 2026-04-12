"""SQLAlchemy async engine, session factory, and FastAPI dependency."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy models."""

    pass


async def get_engine(database_url: str):
    """Create and return an async SQLAlchemy engine."""
    return create_async_engine(database_url, echo=False)


async def get_session_factory(engine) -> async_sessionmaker[AsyncSession]:
    """Create and return an async session factory bound to the given engine."""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Module-level references set during app startup (lifespan).
_session_factory: async_sessionmaker[AsyncSession] | None = None


def set_session_factory(factory: async_sessionmaker[AsyncSession]) -> None:
    """Store the session factory so get_db can use it."""
    global _session_factory
    _session_factory = factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an AsyncSession and closes it after use."""
    if _session_factory is None:
        raise RuntimeError("Session factory not initialised. Call set_session_factory() during app startup.")
    async with _session_factory() as session:
        yield session
