"""Scraping orchestrator — fetches Amazon product pages via httpx and parses with BeautifulSoup."""

import logging
import re
from dataclasses import dataclass, field

import httpx
from bs4 import BeautifulSoup

from app.config import MARKETPLACE_CONFIG, Settings
from app.scrapers.selectors import SELECTOR_CONFIG
from app.utils.normalizer import build_canonical_url

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "max-age=0",
    "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


@dataclass
class ParsedProduct:
    """All fields extracted from a single Amazon product page."""
    asin: str
    marketplace: str
    url: str
    title: str | None = None
    brand: str | None = None
    current_price: float | None = None
    currency: str | None = None
    list_price: float | None = None
    rating: float | None = None
    review_count: int | None = None
    main_image_url: str | None = None
    bullet_points: list[str] = field(default_factory=list)
    seller_info: str | None = None


def _extract_text(soup: BeautifulSoup, field_name: str) -> str | None:
    field_selectors = SELECTOR_CONFIG.get(field_name)
    if field_selectors is None:
        return None
    for selector in field_selectors.selectors:
        element = soup.select_one(selector)
        if element is not None:
            text = element.get_text(strip=True)
            if text:
                return text
    return None


def _extract_image_src(soup: BeautifulSoup) -> str | None:
    field_selectors = SELECTOR_CONFIG.get("main_image_url")
    if field_selectors is None:
        return None
    for selector in field_selectors.selectors:
        element = soup.select_one(selector)
        if element is not None:
            src = element.get("src") or element.get("data-old-hires") or element.get("data-a-dynamic-image")
            if src and isinstance(src, str):
                if src.startswith("{"):
                    # data-a-dynamic-image is JSON, extract first URL
                    import json
                    try:
                        urls = json.loads(src)
                        return next(iter(urls.keys()), None)
                    except Exception:
                        pass
                return src
    return None


def _extract_bullet_points(soup: BeautifulSoup) -> list[str]:
    container = soup.select_one("#feature-bullets")
    if container is None:
        return []
    return [li.get_text(strip=True) for li in container.select("li") if li.get_text(strip=True)]


def parse_price(raw: str | None) -> float | None:
    if not raw:
        return None
    try:
        cleaned = re.sub(r"[^\d.,]", "", raw)
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            parts = cleaned.split(",")
            if len(parts[-1]) == 3:
                cleaned = cleaned.replace(",", "")
            else:
                cleaned = cleaned.replace(",", ".")
        return float(cleaned)
    except (ValueError, IndexError):
        return None


def parse_rating(raw: str | None) -> float | None:
    if not raw:
        return None
    try:
        match = re.search(r"(\d+\.?\d*)", raw)
        if match:
            value = float(match.group(1))
            if 0.0 <= value <= 5.0:
                return value
    except (ValueError, IndexError):
        pass
    return None


def parse_review_count(raw: str | None) -> int | None:
    if not raw:
        return None
    try:
        cleaned = re.sub(r"[^\d.,]", "", raw)
        cleaned = cleaned.replace(",", "").replace(".", "")
        return int(cleaned) if cleaned else None
    except (ValueError, IndexError):
        return None


async def _fetch_with_playwright(url: str) -> str | None:
    """Run Playwright in a subprocess to get JS-rendered HTML."""
    import asyncio
    import sys
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "app.scrapers.pw_fetch", url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode == 0 and stdout:
            return stdout.decode("utf-8", errors="replace")
        if stderr:
            logger.warning("Playwright subprocess stderr: %s", stderr.decode()[:200])
        return None
    except asyncio.TimeoutError:
        logger.warning("Playwright subprocess timed out")
        try:
            proc.kill()
        except Exception:
            pass
        return None
    except Exception as e:
        logger.warning("Playwright subprocess failed: %s", e)
        return None


async def scrape_product(
    browser_manager,  # unused now, kept for interface compat
    marketplace: str,
    asin: str,
    settings: Settings,
) -> ParsedProduct:
    """Fetch product page via httpx and extract fields with BeautifulSoup.

    No browser needed — uses plain HTTP with realistic headers.
    Retries up to settings.retry_count times.
    """
    url = build_canonical_url(marketplace, asin)
    logger.info("Scraping product: marketplace=%s asin=%s url=%s", marketplace, asin, url)

    mkt_config = MARKETPLACE_CONFIG.get(marketplace, {})
    currency = mkt_config.get("currency")

    html = None
    last_error = None

    # AU marketplace: try Playwright subprocess first, then proxy, then plain httpx
    if marketplace == "AU":
        html = await _fetch_with_playwright(url)
        if html and len(html) > 5000:
            logger.info("AU: got rendered HTML via Playwright (%d bytes)", len(html))
        else:
            logger.warning("AU: Playwright fetch failed, trying proxy/httpx")
            html = None

    if html is None:
        cookies = {
            "session-id": "000-0000000-0000000",
            "i18n-prefs": mkt_config.get("currency", "USD"),
            "sp-cdn": '"L5Z9:KR"',
            "lc-main": "en_US",
        }

        # Use proxy for AU if configured
        proxy_url = None
        if marketplace == "AU" and settings.au_proxy_url:
            proxy_url = settings.au_proxy_url
            logger.info("AU: using proxy %s", proxy_url.split("@")[-1] if "@" in proxy_url else proxy_url)

        async with httpx.AsyncClient(
            headers=HEADERS,
            cookies=cookies,
            follow_redirects=True,
            timeout=10,
            proxy=proxy_url,
        ) as client:
            for attempt in range(1, min(settings.retry_count, 2) + 1):
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    html = resp.text
                    break
                except Exception as e:
                    last_error = e
                    if attempt < min(settings.retry_count, 2):
                        import asyncio
                        delay = 1.0
                        logger.warning("Attempt %d failed for %s/%s: %s. Retrying in %.1fs...", attempt, marketplace, asin, e, delay)
                        await asyncio.sleep(delay)

    if html is None:
        logger.error("All attempts failed for %s/%s: %s", marketplace, asin, last_error)
        raise RuntimeError(f"Failed to fetch {url}: {last_error}")

    soup = BeautifulSoup(html, "lxml")

    title = _extract_text(soup, "title")
    brand = _extract_text(soup, "brand")
    seller_info = _extract_text(soup, "seller_info")

    raw_price = _extract_text(soup, "current_price")
    current_price = parse_price(raw_price)

    # Fallback: try buybox-specific selectors only (avoid recommendation section prices)
    if current_price is None:
        for sel in [
            "#corePriceDisplay_desktop_feature_div .a-price-whole",
            "#corePrice_desktop .a-price-whole",
            "#apex_desktop .a-price-whole",
            "#price",
            "#buyNewSection .a-color-price",
            "#newBuyBoxPrice",
        ]:
            el = soup.select_one(sel)
            if el:
                current_price = parse_price(el.get_text(strip=True))
                if current_price:
                    logger.info("Fallback price via %s: %s", sel, current_price)
                    break

    # If still no price and we haven't tried Playwright yet, try it now
    if current_price is None and marketplace != "AU":
        logger.info("No price from httpx for %s/%s, trying Playwright...", marketplace, asin)
        pw_html = await _fetch_with_playwright(url)
        if pw_html and len(pw_html) > 5000:
            soup = BeautifulSoup(pw_html, "lxml")
            title = _extract_text(soup, "title") or title
            brand = _extract_text(soup, "brand") or brand
            seller_info = _extract_text(soup, "seller_info") or seller_info
            raw_price = _extract_text(soup, "current_price")
            current_price = parse_price(raw_price)
            if current_price:
                logger.info("Playwright got price for %s/%s: %s", marketplace, asin, current_price)

    raw_list_price = _extract_text(soup, "list_price")
    list_price = parse_price(raw_list_price)

    raw_rating = _extract_text(soup, "rating")
    rating = parse_rating(raw_rating)

    raw_review_count = _extract_text(soup, "review_count")
    review_count = parse_review_count(raw_review_count)

    main_image_url = _extract_image_src(soup)
    bullet_points = _extract_bullet_points(soup)

    logger.info(
        "Scrape complete: marketplace=%s asin=%s title=%s price=%s",
        marketplace, asin,
        title[:50] if title else None,
        current_price,
    )

    return ParsedProduct(
        asin=asin,
        marketplace=marketplace,
        url=url,
        title=title,
        brand=brand,
        current_price=current_price,
        currency=currency,
        list_price=list_price,
        rating=rating,
        review_count=review_count,
        main_image_url=main_image_url,
        bullet_points=bullet_points,
        seller_info=seller_info,
    )
