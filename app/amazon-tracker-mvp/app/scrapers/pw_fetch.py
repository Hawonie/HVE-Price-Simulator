"""Standalone Playwright script — runs as a subprocess to fetch rendered HTML.

Usage: python -m app.scrapers.pw_fetch <url>
Prints the rendered HTML to stdout.
"""

import sys
import time
from playwright.sync_api import sync_playwright


def fetch_rendered_html(url: str, timeout: int = 25000) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="en-AU",
            timezone_id="Australia/Sydney",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=timeout)

        # Wait for buybox price area to load (AU renders price via JS)
        price_selectors = [
            "#corePriceDisplay_desktop_feature_div",
            "#corePrice_desktop",
            "#apex_desktop .a-price",
            "span.priceToPay",
            "#tp_price_block_total_price_ww",
        ]
        selector_str = ",".join(price_selectors)
        try:
            page.wait_for_selector(selector_str, timeout=12000)
        except Exception:
            # Extra wait — some AU pages are very slow
            time.sleep(3)

        html = page.content()
        browser.close()
        return html


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m app.scrapers.pw_fetch <url>", file=sys.stderr)
        sys.exit(1)
    html = fetch_rendered_html(sys.argv[1])
    sys.stdout.write(html)
