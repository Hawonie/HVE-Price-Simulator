"""Unit tests for the scraping orchestrator parsing and extraction helpers."""

import pytest
from bs4 import BeautifulSoup

from app.scrapers.scraper import (
    ParsedProduct,
    _extract_bullet_points,
    _extract_image_src,
    _extract_text,
    parse_price,
    parse_rating,
    parse_review_count,
)


# ---------------------------------------------------------------------------
# parse_price
# ---------------------------------------------------------------------------

class TestParsePrice:
    def test_aed_price(self):
        assert parse_price("AED 199.00") == 199.0

    def test_sar_price_with_commas(self):
        assert parse_price("SAR 1,299.99") == 1299.99

    def test_aud_price(self):
        assert parse_price("A$49.95") == 49.95

    def test_plain_number(self):
        assert parse_price("25.50") == 25.50

    def test_none_input(self):
        assert parse_price(None) is None

    def test_empty_string(self):
        assert parse_price("") is None

    def test_no_digits(self):
        assert parse_price("N/A") is None

    def test_thousands_no_decimal(self):
        assert parse_price("AED 1,299") == 1299.0


# ---------------------------------------------------------------------------
# parse_rating
# ---------------------------------------------------------------------------

class TestParseRating:
    def test_standard_format(self):
        assert parse_rating("4.5 out of 5 stars") == 4.5

    def test_integer_rating(self):
        assert parse_rating("5 out of 5 stars") == 5.0

    def test_low_rating(self):
        assert parse_rating("1.0 out of 5 stars") == 1.0

    def test_none_input(self):
        assert parse_rating(None) is None

    def test_empty_string(self):
        assert parse_rating("") is None

    def test_out_of_range(self):
        assert parse_rating("6.0 out of 5 stars") is None

    def test_zero_rating(self):
        assert parse_rating("0.0 out of 5 stars") == 0.0


# ---------------------------------------------------------------------------
# parse_review_count
# ---------------------------------------------------------------------------

class TestParseReviewCount:
    def test_with_commas_and_text(self):
        assert parse_review_count("1,234 ratings") == 1234

    def test_plain_number(self):
        assert parse_review_count("500") == 500

    def test_none_input(self):
        assert parse_review_count(None) is None

    def test_empty_string(self):
        assert parse_review_count("") is None

    def test_no_digits(self):
        assert parse_review_count("ratings") is None

    def test_large_number(self):
        assert parse_review_count("12,345 ratings") == 12345


# ---------------------------------------------------------------------------
# _extract_text
# ---------------------------------------------------------------------------

class TestExtractText:
    def test_first_selector_matches(self):
        html = '<div><span id="productTitle">Test Product</span></div>'
        soup = BeautifulSoup(html, "lxml")
        assert _extract_text(soup, "title") == "Test Product"

    def test_fallback_selector(self):
        html = '<div><h1 class="product-title-word-break"><span>Fallback Title</span></h1></div>'
        soup = BeautifulSoup(html, "lxml")
        assert _extract_text(soup, "title") == "Fallback Title"

    def test_no_match_returns_none(self):
        html = "<div><p>Nothing here</p></div>"
        soup = BeautifulSoup(html, "lxml")
        assert _extract_text(soup, "title") is None

    def test_unknown_field_returns_none(self):
        html = "<div></div>"
        soup = BeautifulSoup(html, "lxml")
        assert _extract_text(soup, "nonexistent_field") is None


# ---------------------------------------------------------------------------
# _extract_image_src
# ---------------------------------------------------------------------------

class TestExtractImageSrc:
    def test_landing_image(self):
        html = '<div><img id="landingImage" src="https://images.amazon.com/test.jpg" /></div>'
        soup = BeautifulSoup(html, "lxml")
        assert _extract_image_src(soup) == "https://images.amazon.com/test.jpg"

    def test_fallback_image(self):
        html = '<div><img id="imgBlkFront" src="https://images.amazon.com/front.jpg" /></div>'
        soup = BeautifulSoup(html, "lxml")
        assert _extract_image_src(soup) == "https://images.amazon.com/front.jpg"

    def test_no_image_returns_none(self):
        html = "<div><p>No image</p></div>"
        soup = BeautifulSoup(html, "lxml")
        assert _extract_image_src(soup) is None


# ---------------------------------------------------------------------------
# _extract_bullet_points
# ---------------------------------------------------------------------------

class TestExtractBulletPoints:
    def test_extracts_bullets(self):
        html = """
        <div id="feature-bullets">
            <ul>
                <li><span>Feature one</span></li>
                <li><span>Feature two</span></li>
                <li><span>Feature three</span></li>
            </ul>
        </div>
        """
        soup = BeautifulSoup(html, "lxml")
        bullets = _extract_bullet_points(soup)
        assert bullets == ["Feature one", "Feature two", "Feature three"]

    def test_no_container_returns_empty(self):
        html = "<div><p>No bullets</p></div>"
        soup = BeautifulSoup(html, "lxml")
        assert _extract_bullet_points(soup) == []

    def test_empty_items_skipped(self):
        html = """
        <div id="feature-bullets">
            <ul>
                <li><span>Real feature</span></li>
                <li>   </li>
            </ul>
        </div>
        """
        soup = BeautifulSoup(html, "lxml")
        bullets = _extract_bullet_points(soup)
        assert bullets == ["Real feature"]


# ---------------------------------------------------------------------------
# ParsedProduct dataclass
# ---------------------------------------------------------------------------

class TestParsedProduct:
    def test_defaults(self):
        p = ParsedProduct(asin="B0TEST12AB", marketplace="AE", url="https://www.amazon.ae/dp/B0TEST12AB")
        assert p.title is None
        assert p.current_price is None
        assert p.bullet_points == []
        assert p.seller_info is None

    def test_all_fields(self):
        p = ParsedProduct(
            asin="B0TEST12AB",
            marketplace="AE",
            url="https://www.amazon.ae/dp/B0TEST12AB",
            title="Test",
            brand="Brand",
            current_price=99.99,
            currency="AED",
            list_price=129.99,
            rating=4.5,
            review_count=100,
            availability_text="In Stock",
            main_image_url="https://img.com/test.jpg",
            bullet_points=["a", "b"],
            seller_info="Amazon",
        )
        assert p.title == "Test"
        assert p.bullet_points == ["a", "b"]
