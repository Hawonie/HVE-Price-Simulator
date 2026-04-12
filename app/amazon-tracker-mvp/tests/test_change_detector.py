"""Unit tests for the change detection service."""

import pytest
from datetime import datetime, timezone

from app.models.product import Product
from app.models.snapshot import ProductSnapshot
from app.services.change_detector import (
    MONITORED_FIELDS,
    detect_changes,
    _values_differ,
    _to_str,
)


# ---------------------------------------------------------------------------
# Helper to create a product + snapshot pair quickly
# ---------------------------------------------------------------------------

async def _create_product(session) -> Product:
    product = Product(
        asin="B000TEST01",
        marketplace="AE",
        url="https://www.amazon.ae/dp/B000TEST01",
    )
    session.add(product)
    await session.flush()
    return product


async def _create_snapshot(
    session,
    product_id: int,
    *,
    current_price: float | None = 99.99,
    review_count: int | None = 100,
    availability_text: str | None = "In Stock",
    crawl_timestamp: datetime | None = None,
) -> ProductSnapshot:
    if crawl_timestamp is None:
        crawl_timestamp = datetime.now(timezone.utc)
    snap = ProductSnapshot(
        product_id=product_id,
        current_price=current_price,
        review_count=review_count,
        availability_text=availability_text,
        crawl_timestamp=crawl_timestamp,
    )
    session.add(snap)
    await session.flush()
    return snap


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_previous_snapshot_returns_empty(async_session):
    """First crawl — no previous snapshot exists, expect empty list."""
    product = await _create_product(async_session)
    snap = await _create_snapshot(async_session, product.id)

    changes = await detect_changes(async_session, product.id, snap)
    assert changes == []


@pytest.mark.asyncio
async def test_no_changes_returns_empty(async_session):
    """Two identical snapshots should produce zero change records."""
    product = await _create_product(async_session)
    ts1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    ts2 = datetime(2024, 1, 2, tzinfo=timezone.utc)

    await _create_snapshot(
        async_session, product.id,
        current_price=50.0, review_count=10, availability_text="In Stock",
        crawl_timestamp=ts1,
    )
    new_snap = await _create_snapshot(
        async_session, product.id,
        current_price=50.0, review_count=10, availability_text="In Stock",
        crawl_timestamp=ts2,
    )

    changes = await detect_changes(async_session, product.id, new_snap)
    assert changes == []


@pytest.mark.asyncio
async def test_price_change_detected(async_session):
    """A price change should produce exactly one change record."""
    product = await _create_product(async_session)
    ts1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    ts2 = datetime(2024, 1, 2, tzinfo=timezone.utc)

    await _create_snapshot(
        async_session, product.id,
        current_price=50.0, review_count=10, availability_text="In Stock",
        crawl_timestamp=ts1,
    )
    new_snap = await _create_snapshot(
        async_session, product.id,
        current_price=45.0, review_count=10, availability_text="In Stock",
        crawl_timestamp=ts2,
    )

    changes = await detect_changes(async_session, product.id, new_snap)
    assert len(changes) == 1
    assert changes[0].field_name == "current_price"
    assert changes[0].old_value == "50.0"
    assert changes[0].new_value == "45.0"
    assert changes[0].product_id == product.id


@pytest.mark.asyncio
async def test_multiple_fields_changed(async_session):
    """Changes in all three monitored fields should produce three records."""
    product = await _create_product(async_session)
    ts1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    ts2 = datetime(2024, 1, 2, tzinfo=timezone.utc)

    await _create_snapshot(
        async_session, product.id,
        current_price=50.0, review_count=10, availability_text="In Stock",
        crawl_timestamp=ts1,
    )
    new_snap = await _create_snapshot(
        async_session, product.id,
        current_price=60.0, review_count=20, availability_text="Out of Stock",
        crawl_timestamp=ts2,
    )

    changes = await detect_changes(async_session, product.id, new_snap)
    field_names = {c.field_name for c in changes}
    assert field_names == {"current_price", "review_count", "availability_text"}


@pytest.mark.asyncio
async def test_none_to_value_detected(async_session):
    """Going from None to a value should be detected as a change."""
    product = await _create_product(async_session)
    ts1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    ts2 = datetime(2024, 1, 2, tzinfo=timezone.utc)

    await _create_snapshot(
        async_session, product.id,
        current_price=None, review_count=None, availability_text=None,
        crawl_timestamp=ts1,
    )
    new_snap = await _create_snapshot(
        async_session, product.id,
        current_price=25.0, review_count=5, availability_text="In Stock",
        crawl_timestamp=ts2,
    )

    changes = await detect_changes(async_session, product.id, new_snap)
    assert len(changes) == 3
    price_change = next(c for c in changes if c.field_name == "current_price")
    assert price_change.old_value is None
    assert price_change.new_value == "25.0"


@pytest.mark.asyncio
async def test_value_to_none_detected(async_session):
    """Going from a value to None should be detected as a change."""
    product = await _create_product(async_session)
    ts1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    ts2 = datetime(2024, 1, 2, tzinfo=timezone.utc)

    await _create_snapshot(
        async_session, product.id,
        current_price=25.0, review_count=5, availability_text="In Stock",
        crawl_timestamp=ts1,
    )
    new_snap = await _create_snapshot(
        async_session, product.id,
        current_price=None, review_count=None, availability_text=None,
        crawl_timestamp=ts2,
    )

    changes = await detect_changes(async_session, product.id, new_snap)
    assert len(changes) == 3


# ---------------------------------------------------------------------------
# Pure-function unit tests
# ---------------------------------------------------------------------------


def test_values_differ_both_none():
    assert _values_differ(None, None) is False


def test_values_differ_one_none():
    assert _values_differ(None, 5) is True
    assert _values_differ(5, None) is True


def test_values_differ_same():
    assert _values_differ(10, 10) is False
    assert _values_differ("In Stock", "In Stock") is False


def test_values_differ_different():
    assert _values_differ(10, 20) is True
    assert _values_differ("In Stock", "Out of Stock") is True


def test_to_str():
    assert _to_str(None) is None
    assert _to_str(50.0) == "50.0"
    assert _to_str(100) == "100"
    assert _to_str("In Stock") == "In Stock"


def test_monitored_fields_list():
    assert MONITORED_FIELDS == ["current_price", "review_count", "availability_text"]
