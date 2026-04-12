"""Shared test fixtures — async SQLite session for service-layer tests."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base


@pytest.fixture
async def async_session():
    """Yield an AsyncSession backed by an in-memory SQLite database.

    Tables are created fresh for every test and torn down afterwards.
    """
    engine = create_async_engine("sqlite+aiosqlite:///", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
