"""Manual crawl script — run a single product scrape from the command line.

Usage:
    python -m scripts.manual_crawl --marketplace AE --asin B0DGHWT2ZJ
"""

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import asdict

from app.config import get_settings
from app.scrapers.browser import BrowserManager
from app.scrapers.scraper import scrape_product

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def run_crawl(marketplace: str, asin: str) -> None:
    """Start a browser, scrape a single product, and print the result."""
    settings = get_settings()
    browser_manager = BrowserManager()

    await browser_manager.start()
    try:
        result = await scrape_product(browser_manager, marketplace, asin, settings)
        print(json.dumps(asdict(result), indent=2, default=str))
    finally:
        await browser_manager.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a single Amazon product crawl.")
    parser.add_argument("--marketplace", required=True, help="Marketplace code (AE, SA, AU)")
    parser.add_argument("--asin", required=True, help="10-character Amazon ASIN")
    args = parser.parse_args()

    marketplace = args.marketplace.upper()
    asin = args.asin.upper()

    supported = get_settings().supported_marketplaces
    if marketplace not in supported:
        logger.error("Unsupported marketplace '%s'. Supported: %s", marketplace, ", ".join(supported))
        sys.exit(1)

    try:
        asyncio.run(run_crawl(marketplace, asin))
    except KeyboardInterrupt:
        logger.info("Crawl interrupted by user.")
        sys.exit(130)
    except Exception as exc:
        logger.error("Crawl failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
