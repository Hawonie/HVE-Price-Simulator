"""Database initialisation script — creates all tables defined by SQLAlchemy models.

Usage:
    python -m scripts.init_db
"""

import asyncio
import logging
import sys

from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings
from app.database import Base

# Import all models so they register with Base.metadata
from app.models import ChangeRecord, Product, ProductSnapshot  # noqa: F401

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Create all database tables using the configured async engine."""
    settings = get_settings()
    logger.info("Connecting to database: %s", settings.database_url)

    engine = create_async_engine(settings.database_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()
    logger.info("All tables created successfully.")


if __name__ == "__main__":
    try:
        asyncio.run(init_db())
    except Exception as exc:
        logger.error("Failed to initialise database: %s", exc)
        sys.exit(1)
