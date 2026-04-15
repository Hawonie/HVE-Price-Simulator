"""Daily crawl script — crawl all tracked products and save snapshots.

Run this via Windows Task Scheduler or cron:
    python -m scripts.daily_crawl

It does NOT require the FastAPI server to be running.
"""

import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    from app.config import get_settings
    from app.database import Base, get_engine, get_session_factory
    from app.models.product import Product  # noqa: F401
    from app.models.snapshot import ProductSnapshot  # noqa: F401
    from app.models.change import ChangeRecord  # noqa: F401
    from app.services import product_service, snapshot_service
    from app.services.change_detector import detect_changes
    from app.scrapers.scraper import scrape_product

    settings = get_settings()
    engine = await get_engine(settings.database_url)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = await get_session_factory(engine)

    # Get all tracked products
    async with session_factory() as session:
        products = await product_service.list_all_products(session)

    if not products:
        logger.info("No products to crawl. Add products first via the web UI.")
        await engine.dispose()
        return

    logger.info("Starting daily crawl for %d products", len(products))
    success = 0
    failed = 0

    for product in products:
        try:
            logger.info("Crawling %s/%s ...", product.marketplace, product.asin)
            parsed = await scrape_product(None, product.marketplace, product.asin, settings)

            async with session_factory() as session:
                snap = await snapshot_service.save_snapshot(
                    session,
                    product.id,
                    current_price=parsed.current_price,
                    currency=parsed.currency,
                    list_price=parsed.list_price,
                    rating=parsed.rating,
                    review_count=parsed.review_count,
                    seller_info=parsed.seller_info,
                    bullet_points=parsed.bullet_points,
                )
                await detect_changes(session, product.id, snap)
                await product_service.upsert_product(
                    session, product.marketplace, product.asin, parsed.url,
                    title=parsed.title,
                    brand=parsed.brand,
                    main_image_url=parsed.main_image_url,
                )
                await session.commit()

            logger.info(
                "  OK: %s/%s price=%s %s",
                product.marketplace, product.asin,
                parsed.currency, parsed.current_price,
            )
            success += 1
        except Exception as e:
            logger.error("  FAIL: %s/%s — %s", product.marketplace, product.asin, e)
            failed += 1

    await engine.dispose()
    logger.info("Daily crawl done: %d success, %d failed", success, failed)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted.")
        sys.exit(130)
