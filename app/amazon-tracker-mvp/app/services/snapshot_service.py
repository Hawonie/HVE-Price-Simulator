"""Snapshot storage and retrieval using SQLAlchemy async sessions."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.snapshot import ProductSnapshot

logger = logging.getLogger(__name__)


async def save_snapshot(
    session: AsyncSession,
    product_id: int,
    *,
    current_price: float | None = None,
    currency: str | None = None,
    list_price: float | None = None,
    rating: float | None = None,
    review_count: int | None = None,
    availability_text: str | None = None,
    seller_info: str | None = None,
    bullet_points: list[str] | None = None,
    crawl_timestamp: datetime | None = None,
) -> ProductSnapshot:
    """Insert a single snapshot record for a crawl.

    If *crawl_timestamp* is not provided it defaults to the current UTC time.
    Creates a new :class:`ProductSnapshot`, adds it to *session*, flushes to
    obtain the generated ``id``, and returns the persisted instance.
    """
    if crawl_timestamp is None:
        crawl_timestamp = datetime.now(timezone.utc)
    snapshot = ProductSnapshot(
        product_id=product_id,
        current_price=current_price,
        currency=currency,
        list_price=list_price,
        rating=rating,
        review_count=review_count,
        availability_text=availability_text,
        seller_info=seller_info,
        bullet_points=bullet_points,
        crawl_timestamp=crawl_timestamp,
    )
    session.add(snapshot)
    await session.flush()
    logger.info("Saved snapshot for product_id=%d at %s", product_id, crawl_timestamp)
    return snapshot


async def get_latest_snapshot(
    session: AsyncSession,
    product_id: int,
) -> ProductSnapshot | None:
    """Fetch the most recent snapshot for a product, or ``None``."""
    stmt = (
        select(ProductSnapshot)
        .where(ProductSnapshot.product_id == product_id)
        .order_by(ProductSnapshot.crawl_timestamp.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_snapshot_history(
    session: AsyncSession,
    product_id: int,
) -> list[ProductSnapshot]:
    """Return all snapshots for a product ordered by crawl_timestamp ascending."""
    stmt = (
        select(ProductSnapshot)
        .where(ProductSnapshot.product_id == product_id)
        .order_by(ProductSnapshot.crawl_timestamp.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
