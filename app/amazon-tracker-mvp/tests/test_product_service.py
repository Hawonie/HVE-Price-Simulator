"""Unit tests for app.services.product_service."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.services.product_service import get_product, list_products, upsert_product


# ── upsert_product ──────────────────────────────────────────────────


async def test_upsert_creates_new_product(async_session: AsyncSession):
    product = await upsert_product(
        async_session, "AE", "B0TEST0001", "https://www.amazon.ae/dp/B0TEST0001"
    )
    await async_session.commit()

    assert product.id is not None
    assert product.marketplace == "AE"
    assert product.asin == "B0TEST0001"
    assert product.url == "https://www.amazon.ae/dp/B0TEST0001"


async def test_upsert_updates_existing_product(async_session: AsyncSession):
    await upsert_product(
        async_session,
        "SA",
        "B0TEST0002",
        "https://www.amazon.sa/dp/B0TEST0002",
        title="Old Title",
    )
    await async_session.commit()

    updated = await upsert_product(
        async_session,
        "SA",
        "B0TEST0002",
        "https://www.amazon.sa/dp/B0TEST0002",
        title="New Title",
        brand="BrandX",
    )
    await async_session.commit()

    assert updated.title == "New Title"
    assert updated.brand == "BrandX"


async def test_upsert_idempotent_single_row(async_session: AsyncSession):
    """Upserting the same (marketplace, asin) twice must not create a duplicate."""
    await upsert_product(
        async_session, "AU", "B0TEST0003", "https://www.amazon.com.au/dp/B0TEST0003"
    )
    await async_session.commit()

    await upsert_product(
        async_session, "AU", "B0TEST0003", "https://www.amazon.com.au/dp/B0TEST0003", title="T"
    )
    await async_session.commit()

    products = await list_products(async_session)
    au_products = [p for p in products if p.asin == "B0TEST0003"]
    assert len(au_products) == 1


async def test_upsert_metadata_optional(async_session: AsyncSession):
    product = await upsert_product(
        async_session, "AE", "B0TEST0004", "https://www.amazon.ae/dp/B0TEST0004"
    )
    await async_session.commit()

    assert product.title is None
    assert product.brand is None
    assert product.main_image_url is None


# ── get_product ─────────────────────────────────────────────────────


async def test_get_product_found(async_session: AsyncSession):
    await upsert_product(
        async_session, "AE", "B0TEST0005", "https://www.amazon.ae/dp/B0TEST0005", title="Found"
    )
    await async_session.commit()

    product = await get_product(async_session, "AE", "B0TEST0005")
    assert product is not None
    assert product.title == "Found"


async def test_get_product_not_found(async_session: AsyncSession):
    product = await get_product(async_session, "AE", "ZZZZZZZZZZ")
    assert product is None


# ── list_products ───────────────────────────────────────────────────


async def test_list_products_empty(async_session: AsyncSession):
    products = await list_products(async_session)
    assert products == []


async def test_list_products_returns_all(async_session: AsyncSession):
    await upsert_product(async_session, "AE", "B0TEST0010", "https://www.amazon.ae/dp/B0TEST0010")
    await upsert_product(async_session, "SA", "B0TEST0011", "https://www.amazon.sa/dp/B0TEST0011")
    await async_session.commit()

    products = await list_products(async_session)
    assert len(products) == 2
