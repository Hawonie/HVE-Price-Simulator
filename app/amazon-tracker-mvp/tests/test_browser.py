"""Unit tests for BrowserManager."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.scrapers.browser import BrowserManager


class TestBrowserManager:
    """Tests for BrowserManager lifecycle and context creation."""

    def test_initial_state(self):
        """Browser and playwright are None before start()."""
        mgr = BrowserManager()
        assert mgr._browser is None
        assert mgr._playwright is None

    async def test_new_context_before_start_raises(self):
        """Calling new_context() before start() raises RuntimeError."""
        mgr = BrowserManager()
        with pytest.raises(RuntimeError, match="Browser not started"):
            await mgr.new_context("AE")

    async def test_new_context_unsupported_marketplace_raises(self):
        """Calling new_context() with unsupported marketplace raises ValueError."""
        mgr = BrowserManager()
        mgr._browser = MagicMock()  # fake a started browser
        with pytest.raises(ValueError, match="Unsupported marketplace"):
            await mgr.new_context("US")

    @patch("app.scrapers.browser.async_playwright")
    async def test_start_launches_chromium(self, mock_async_pw):
        """start() launches a headless Chromium browser."""
        mock_pw_instance = AsyncMock()
        mock_browser = AsyncMock()
        mock_pw_instance.chromium.launch.return_value = mock_browser

        mock_ctx_mgr = AsyncMock()
        mock_ctx_mgr.start.return_value = mock_pw_instance
        mock_async_pw.return_value = mock_ctx_mgr

        mgr = BrowserManager()
        await mgr.start()

        mock_ctx_mgr.start.assert_awaited_once()
        mock_pw_instance.chromium.launch.assert_awaited_once_with(headless=True)
        assert mgr._browser is mock_browser
        assert mgr._playwright is mock_pw_instance

    @patch("app.scrapers.browser.async_playwright")
    async def test_new_context_sets_locale_and_timezone(self, mock_async_pw):
        """new_context() passes correct locale and timezone_id for each marketplace."""
        mock_pw_instance = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_browser.new_context.return_value = mock_context
        mock_pw_instance.chromium.launch.return_value = mock_browser

        mock_ctx_mgr = AsyncMock()
        mock_ctx_mgr.start.return_value = mock_pw_instance
        mock_async_pw.return_value = mock_ctx_mgr

        mgr = BrowserManager()
        await mgr.start()

        expected = {
            "AE": ("en-AE", "Asia/Dubai"),
            "SA": ("en-SA", "Asia/Riyadh"),
            "AU": ("en-AU", "Australia/Sydney"),
        }

        for marketplace, (locale, tz) in expected.items():
            await mgr.new_context(marketplace)
            mock_browser.new_context.assert_called_with(
                locale=locale,
                timezone_id=tz,
            )

    @patch("app.scrapers.browser.async_playwright")
    async def test_close_cleans_up(self, mock_async_pw):
        """close() shuts down browser and playwright, resets state to None."""
        mock_pw_instance = AsyncMock()
        mock_browser = AsyncMock()
        mock_pw_instance.chromium.launch.return_value = mock_browser

        mock_ctx_mgr = AsyncMock()
        mock_ctx_mgr.start.return_value = mock_pw_instance
        mock_async_pw.return_value = mock_ctx_mgr

        mgr = BrowserManager()
        await mgr.start()
        await mgr.close()

        mock_browser.close.assert_awaited_once()
        mock_pw_instance.stop.assert_awaited_once()
        assert mgr._browser is None
        assert mgr._playwright is None

    async def test_close_when_not_started_is_safe(self):
        """close() on a never-started manager does nothing."""
        mgr = BrowserManager()
        await mgr.close()  # should not raise
        assert mgr._browser is None
        assert mgr._playwright is None
