"""APScheduler integration — periodic crawl job for all tracked products."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.config import Settings
from app.scrapers.browser import BrowserManager
from app.scrapers.scraper import scrape_product
from app.services import product_service, snapshot_service
from app.services.change_detector import detect_changes

logger = logging.getLogger(__name__)


async def crawl_all_products(
    session_factory: async_sessionmaker[AsyncSession],
    browser_manager: BrowserManager,
    settings: Settings,
) -> None:
    """Crawl every tracked product, save snapshots, and detect changes.

    Each product is processed independently — an exception for one product is
    caught and logged so the remaining products are still crawled.
    """
    logger.info("Scheduled crawl started")

    async with session_factory() as session:
        products = await product_service.list_all_products(session)

    logger.info("Found %d tracked products to crawl", len(products))

    for product in products:
        try:
            parsed = await scrape_product(
                browser_manager,
                product.marketplace,
                product.asin,
                settings,
            )

            async with session_factory() as session:
                snapshot = await snapshot_service.save_snapshot(
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

                changes = await detect_changes(session, product.id, snapshot)
                if changes:
                    logger.info(
                        "Detected %d change(s) for %s/%s",
                        len(changes),
                        product.marketplace,
                        product.asin,
                    )

                await product_service.upsert_product(
                    session,
                    product.marketplace,
                    product.asin,
                    parsed.url,
                    title=parsed.title,
                    brand=parsed.brand,
                    main_image_url=parsed.main_image_url,
                )

                await session.commit()

            logger.info(
                "Crawl succeeded for %s/%s", product.marketplace, product.asin
            )
        except Exception:
            logger.exception(
                "Crawl failed for %s/%s — skipping",
                product.marketplace,
                product.asin,
            )

    logger.info("Scheduled crawl finished")


def setup_scheduler(
    session_factory: async_sessionmaker[AsyncSession],
    browser_manager: BrowserManager,
    settings: Settings,
) -> AsyncIOScheduler:
    """Create an :class:`AsyncIOScheduler` with the crawl job.

    The scheduler is returned *without* being started — the caller (e.g.
    ``main.py`` lifespan) is responsible for calling ``scheduler.start()``.
    """
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        crawl_all_products,
        trigger="interval",
        minutes=settings.crawl_interval_minutes,
        kwargs={
            "session_factory": session_factory,
            "browser_manager": browser_manager,
            "settings": settings,
        },
        id="crawl_all_products",
        name="Crawl all tracked products",
        replace_existing=True,
    )
    logger.info(
        "Scheduler configured with crawl interval of %d minutes",
        settings.crawl_interval_minutes,
    )
    return scheduler
