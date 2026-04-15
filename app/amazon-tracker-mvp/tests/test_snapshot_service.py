"""Unit tests for app.services.snapshot_service."""

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.product_service import upsert_product
from app.services.snapshot_service import (
    get_latest_snapshot,
    get_snapshot_history,
    save_snapshot,
)


# ── helpers ─────────────────────────────────────────────────────────


async def _create_product(session: AsyncSession) -> int:
    """Create a product and return its id."""
    product = await upsert_product(
        session, "AE", "B0SNAP00001", "https://www.amazon.ae/dp/B0SNAP00001"
    )
    await session.commit()
    return product.id


# ── save_snapshot ───────────────────────────────────────────────────


async def test_save_snapshot_creates_record(async_session: AsyncSession):
    pid = await _create_product(async_session)
    ts = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    snap = await save_snapshot(
        async_session,
        pid,
        crawl_timestamp=ts,
        current_price=99.99,
        currency="AED",
    )
    await async_session.commit()

    assert snap.id is not None
    assert snap.product_id == pid
    assert snap.current_price == 99.99
    assert snap.currency == "AED"
    assert snap.crawl_timestamp == ts


async def test_save_snapshot_nullable_fields(async_session: AsyncSession):
    pid = await _create_product(async_session)
    ts = datetime(2024, 1, 2, tzinfo=timezone.utc)

    snap = await save_snapshot(async_session, pid, crawl_timestamp=ts)
    await async_session.commit()

    assert snap.current_price is None
    assert snap.list_price is None
    assert snap.rating is None
    assert snap.review_count is None
    assert snap.bullet_points is None


async def test_save_snapshot_with_all_fields(async_session: AsyncSession):
    pid = await _create_product(async_session)
    ts = datetime(2024, 3, 15, 8, 30, tzinfo=timezone.utc)

    snap = await save_snapshot(
        async_session,
        pid,
        crawl_timestamp=ts,
        current_price=149.50,
        currency="AED",
        list_price=199.00,
        rating=4.3,
        review_count=512,
        seller_info="Amazon.ae",
        bullet_points=["Feature A", "Feature B"],
    )
    await async_session.commit()

    assert snap.list_price == 199.00
    assert snap.rating == 4.3
    assert snap.review_count == 512
    assert snap.seller_info == "Amazon.ae"
    assert snap.bullet_points == ["Feature A", "Feature B"]


# ── get_latest_snapshot ─────────────────────────────────────────────


async def test_get_latest_snapshot_returns_most_recent(async_session: AsyncSession):
    pid = await _create_product(async_session)

    await save_snapshot(
        async_session, pid, crawl_timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc), current_price=10.0
    )
    await save_snapshot(
        async_session, pid, crawl_timestamp=datetime(2024, 6, 1, tzinfo=timezone.utc), current_price=20.0
    )
    await save_snapshot(
        async_session, pid, crawl_timestamp=datetime(2024, 3, 1, tzinfo=timezone.utc), current_price=15.0
    )
    await async_session.commit()

    latest = await get_latest_snapshot(async_session, pid)
    assert latest is not None
    assert latest.current_price == 20.0


async def test_get_latest_snapshot_none_when_no_snapshots(async_session: AsyncSession):
    pid = await _create_product(async_session)
    latest = await get_latest_snapshot(async_session, pid)
    assert latest is None


# ── get_snapshot_history ────────────────────────────────────────────


async def test_get_snapshot_history_ordered_ascending(async_session: AsyncSession):
    pid = await _create_product(async_session)

    await save_snapshot(
        async_session, pid, crawl_timestamp=datetime(2024, 3, 1, tzinfo=timezone.utc), current_price=30.0
    )
    await save_snapshot(
        async_session, pid, crawl_timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc), current_price=10.0
    )
    await save_snapshot(
        async_session, pid, crawl_timestamp=datetime(2024, 2, 1, tzinfo=timezone.utc), current_price=20.0
    )
    await async_session.commit()

    history = await get_snapshot_history(async_session, pid)
    assert len(history) == 3
    assert [s.current_price for s in history] == [10.0, 20.0, 30.0]


async def test_get_snapshot_history_empty(async_session: AsyncSession):
    pid = await _create_product(async_session)
    history = await get_snapshot_history(async_session, pid)
    assert history == []
