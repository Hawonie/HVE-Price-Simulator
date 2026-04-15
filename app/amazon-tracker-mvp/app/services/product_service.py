"""Product CRUD operations using SQLAlchemy async sessions."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product

logger = logging.getLogger(__name__)


async def upsert_product(
    session: AsyncSession,
    marketplace: str,
    asin: str,
    url: str,
    *,
    title: str | None = None,
    brand: str | None = None,
    main_image_url: str | None = None,
) -> Product:
    """Create or update a Product record keyed by (marketplace, asin).

    If a product with the given marketplace/asin already exists, its metadata
    (url, title, brand, main_image_url, updated_at) is updated.  Otherwise a
    new row is inserted.

    Returns the persisted Product instance (attached to *session*).
    """
    stmt = select(Product).where(
        Product.marketplace == marketplace,
        Product.asin == asin,
    )
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()

    if product is not None:
        product.url = url
        product.title = title
        product.brand = brand
        product.main_image_url = main_image_url
        product.hidden = False
        product.updated_at = datetime.now(timezone.utc)
        logger.info("Updated product %s/%s", marketplace, asin)
    else:
        product = Product(
            marketplace=marketplace,
            asin=asin,
            url=url,
            title=title,
            brand=brand,
            main_image_url=main_image_url,
        )
        session.add(product)
        logger.info("Created product %s/%s", marketplace, asin)

    await session.flush()
    return product


async def get_product(
    session: AsyncSession,
    marketplace: str,
    asin: str,
) -> Product | None:
    """Fetch a single product by marketplace and asin, or ``None``."""
    stmt = select(Product).where(
        Product.marketplace == marketplace,
        Product.asin == asin,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_products(session: AsyncSession) -> list[Product]:
    """Return all visible (non-hidden) tracked products ordered by id."""
    stmt = select(Product).where(Product.hidden == False).order_by(Product.id)  # noqa: E712
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_all_products(session: AsyncSession) -> list[Product]:
    """Return ALL products (including hidden) for background crawling."""
    stmt = select(Product).order_by(Product.id)
    result = await session.execute(stmt)
    return list(result.scalars().all())
