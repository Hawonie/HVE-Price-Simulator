"""Playwright browser lifecycle management — uses sync API in a thread for Windows compatibility."""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from playwright.sync_api import Browser, BrowserContext, Playwright, sync_playwright

from app.config import MARKETPLACE_CONFIG, get_settings

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=1)


class BrowserManager:
    """Manages a single Playwright browser instance.

    Uses sync Playwright in a dedicated thread to avoid the Windows
    ``NotImplementedError`` with ``asyncio.create_subprocess_exec``.
    """

    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    def _start_sync(self) -> None:
        settings = get_settings()
        logger.info("Starting Playwright browser (headless=%s)", settings.playwright_headless)
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=settings.playwright_headless,
        )
        logger.info("Playwright browser started")

    async def start(self) -> None:
        """Launch headless Chromium browser in a background thread."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(_executor, self._start_sync)

    def _new_context_sync(self, marketplace: str) -> BrowserContext:
        if self._browser is None:
            raise RuntimeError("Browser not started. Call start() first.")
        if marketplace not in MARKETPLACE_CONFIG:
            raise ValueError(f"Unsupported marketplace: {marketplace}")
        config = MARKETPLACE_CONFIG[marketplace]
        return self._browser.new_context(
            locale=config["locale"],
            timezone_id=config["timezone"],
        )

    async def new_context(self, marketplace: str) -> BrowserContext:
        """Create a browser context in the background thread."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor, partial(self._new_context_sync, marketplace)
        )

    def _close_sync(self) -> None:
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None
            logger.info("Playwright stopped")

    async def close(self) -> None:
        """Close browser and Playwright in the background thread."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(_executor, self._close_sync)
