"""FastAPI router with all REST API endpoints for the Amazon Tracker."""

import csv
import io
import logging
import random
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.schemas.product import (
    AddProductRequest,
    PriceIndicatorsResponse,
    ProductResponse,
    SimulationRequest,
    SimulationResult,
    SnapshotResponse,
    T30Response,
    WasPriceResponse,
)
from app.services import csv_exporter, price_analytics, product_service, snapshot_service
from app.services.change_detector import detect_changes
from app.utils.normalizer import normalize_input

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")


@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_product(
    body: AddProductRequest,
    session: AsyncSession = Depends(get_db),
):
    """Add a product for tracking by URL or ASIN + marketplace."""
    try:
        if body.url:
            normalized = normalize_input(body.url)
        elif body.asin:
            normalized = normalize_input(body.asin, marketplace=body.marketplace)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'url' or 'asin' must be provided.",
            )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    product = await product_service.upsert_product(
        session,
        marketplace=normalized.marketplace,
        asin=normalized.asin,
        url=normalized.url,
    )
    await session.commit()
    logger.info("Added/updated product %s/%s", normalized.marketplace, normalized.asin)

    # Auto-crawl after adding
    try:
        from app.scrapers.scraper import scrape_product
        settings = get_settings()
        parsed = await scrape_product(None, normalized.marketplace, normalized.asin, settings)
        await snapshot_service.save_snapshot(
            session, product.id,
            current_price=parsed.current_price, currency=parsed.currency,
            list_price=parsed.list_price, rating=parsed.rating,
            review_count=parsed.review_count, availability_text=parsed.availability_text,
            seller_info=parsed.seller_info, bullet_points=parsed.bullet_points,
        )
        await product_service.upsert_product(
            session, normalized.marketplace, normalized.asin, parsed.url,
            title=parsed.title, brand=parsed.brand, main_image_url=parsed.main_image_url,
        )
        await session.commit()
        logger.info("Auto-crawled %s/%s: %s %s", normalized.marketplace, normalized.asin, parsed.currency, parsed.current_price)
    except Exception as e:
        logger.warning("Auto-crawl failed for %s/%s: %s", normalized.marketplace, normalized.asin, e)

    # Re-fetch to get updated data
    product = await product_service.get_product(session, normalized.marketplace, normalized.asin)
    return product


@router.get("/products", response_model=list[ProductResponse])
async def list_products(
    session: AsyncSession = Depends(get_db),
):
    """List all tracked products."""
    products = await product_service.list_products(session)
    return products


@router.get(
    "/products/{marketplace}/{asin}/latest",
    response_model=SnapshotResponse,
)
async def get_latest_snapshot(
    marketplace: str,
    asin: str,
    session: AsyncSession = Depends(get_db),
):
    """Return the latest snapshot for a product."""
    product = await product_service.get_product(session, marketplace.upper(), asin.upper())
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {marketplace.upper()}/{asin.upper()} not found.",
        )

    snapshot = await snapshot_service.get_latest_snapshot(session, product.id)
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No snapshots found for product {marketplace.upper()}/{asin.upper()}.",
        )
    return snapshot


@router.get(
    "/products/{marketplace}/{asin}/history",
    response_model=list[SnapshotResponse],
)
async def get_snapshot_history(
    marketplace: str,
    asin: str,
    period: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    session: AsyncSession = Depends(get_db),
):
    """Return snapshots for a product, optionally filtered by date range.

    Query parameters:
    - period: preset period (1d, 7d, 30d, 60d, 90d)
    - start_date / end_date: custom date range (YYYY-MM-DD)
    Custom date range takes priority over period preset.
    """
    product = await product_service.get_product(session, marketplace.upper(), asin.upper())
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {marketplace.upper()}/{asin.upper()} not found.",
        )

    # Determine effective date window
    effective_start: datetime | None = None
    effective_end: datetime | None = None

    if start_date is not None or end_date is not None:
        # Custom date range takes priority
        if start_date is not None:
            effective_start = datetime(
                start_date.year, start_date.month, start_date.day,
                tzinfo=timezone.utc,
            )
        if end_date is not None:
            effective_end = datetime(
                end_date.year, end_date.month, end_date.day,
                23, 59, 59, 999999,
                tzinfo=timezone.utc,
            )
    elif period is not None:
        period_days = {"1d": 1, "7d": 7, "30d": 30, "60d": 60, "90d": 90}
        days = period_days.get(period)
        if days is not None:
            now = datetime.now(timezone.utc)
            effective_start = now - timedelta(days=days)
            effective_end = now

    if effective_start is not None or effective_end is not None:
        snapshots = await price_analytics.get_filtered_snapshots(
            session, product.id, start_date=effective_start, end_date=effective_end,
        )
    else:
        snapshots = await snapshot_service.get_snapshot_history(session, product.id)

    return snapshots


@router.get("/products/{marketplace}/{asin}/export")
async def export_csv(
    marketplace: str,
    asin: str,
    session: AsyncSession = Depends(get_db),
):
    """Download all snapshots for a product as a CSV file."""
    product = await product_service.get_product(session, marketplace.upper(), asin.upper())
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {marketplace.upper()}/{asin.upper()} not found.",
        )

    snapshots = await snapshot_service.get_snapshot_history(session, product.id)
    csv_content = csv_exporter.export_snapshots_csv(snapshots)

    filename = f"{marketplace.upper()}_{asin.upper()}_history.csv"
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/products/{marketplace}/{asin}/was-price",
    response_model=WasPriceResponse,
)
async def get_was_price(
    marketplace: str,
    asin: str,
    reference_date: date,
    session: AsyncSession = Depends(get_db),
):
    """Return the Was Price (90-day median) for a product."""
    product = await product_service.get_product(session, marketplace.upper(), asin.upper())
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {marketplace.upper()}/{asin.upper()} not found.",
        )

    was_price, data_points = await price_analytics.get_was_price(
        session, product.id, reference_date,
    )
    return WasPriceResponse(
        reference_date=reference_date,
        was_price=was_price,
        data_points=data_points,
    )


@router.get(
    "/products/{marketplace}/{asin}/t30",
    response_model=T30Response,
)
async def get_t30(
    marketplace: str,
    asin: str,
    reference_date: date,
    session: AsyncSession = Depends(get_db),
):
    """Return the T30 (30-day minimum) for a product."""
    product = await product_service.get_product(session, marketplace.upper(), asin.upper())
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {marketplace.upper()}/{asin.upper()} not found.",
        )

    t30, data_points = await price_analytics.get_t30(
        session, product.id, reference_date,
    )
    return T30Response(
        reference_date=reference_date,
        t30=t30,
        data_points=data_points,
    )


@router.get(
    "/products/{marketplace}/{asin}/price-indicators",
    response_model=PriceIndicatorsResponse,
)
async def get_price_indicators(
    marketplace: str,
    asin: str,
    reference_date: date,
    session: AsyncSession = Depends(get_db),
):
    """Return Was Price and T30 combined for a product."""
    product = await product_service.get_product(session, marketplace.upper(), asin.upper())
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {marketplace.upper()}/{asin.upper()} not found.",
        )

    was_price, was_dp = await price_analytics.get_was_price(
        session, product.id, reference_date,
    )
    t30, t30_dp = await price_analytics.get_t30(
        session, product.id, reference_date,
    )
    return PriceIndicatorsResponse(
        reference_date=reference_date,
        was_price=was_price,
        was_price_data_points=was_dp,
        t30=t30,
        t30_data_points=t30_dp,
    )


@router.post(
    "/products/{marketplace}/{asin}/simulate",
    response_model=SimulationResult,
)
async def simulate_price(
    marketplace: str,
    asin: str,
    body: SimulationRequest,
    session: AsyncSession = Depends(get_db),
):
    """Simulate injecting a virtual price and evaluate Was Price / T30."""
    if body.simulation_date > body.evaluation_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Simulation date must be on or before evaluation date.",
        )

    product = await product_service.get_product(session, marketplace.upper(), asin.upper())
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {marketplace.upper()}/{asin.upper()} not found.",
        )

    result = await price_analytics.simulate_price(
        session,
        product.id,
        simulation_date=body.simulation_date,
        simulation_price=body.simulation_price,
        evaluation_date=body.evaluation_date,
    )
    return result


@router.post("/products/{marketplace}/{asin}/crawl")
async def crawl_product(
    marketplace: str,
    asin: str,
    session: AsyncSession = Depends(get_db),
):
    """Trigger a crawl for a specific product using httpx."""
    mkt = marketplace.upper()
    asin_upper = asin.upper()

    product = await product_service.get_product(session, mkt, asin_upper)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {mkt}/{asin_upper} not found. Add it first.",
        )

    from app.scrapers.scraper import scrape_product
    settings = get_settings()

    try:
        parsed = await scrape_product(None, mkt, asin_upper, settings)
    except Exception as e:
        logger.error("Crawl failed for %s/%s: %s", mkt, asin_upper, e)
        raise HTTPException(status_code=500, detail=f"Crawl failed: {e}")

    # Save snapshot
    snap = await snapshot_service.save_snapshot(
        session,
        product.id,
        current_price=parsed.current_price,
        currency=parsed.currency,
        list_price=parsed.list_price,
        rating=parsed.rating,
        review_count=parsed.review_count,
        availability_text=parsed.availability_text,
        seller_info=parsed.seller_info,
        bullet_points=parsed.bullet_points,
    )

    # Detect changes
    await detect_changes(session, product.id, snap)

    # Update product metadata
    await product_service.upsert_product(
        session, mkt, asin_upper, parsed.url,
        title=parsed.title,
        brand=parsed.brand,
        main_image_url=parsed.main_image_url,
    )
    await session.commit()

    return {
        "status": "ok",
        "asin": asin_upper,
        "marketplace": mkt,
        "title": parsed.title,
        "price": parsed.current_price,
        "currency": parsed.currency,
        "rating": parsed.rating,
        "review_count": parsed.review_count,
        "image": parsed.main_image_url,
    }


@router.post("/products/{marketplace}/{asin}/seed")
async def seed_demo_data(
    marketplace: str,
    asin: str,
    days: int = 90,
    session: AsyncSession = Depends(get_db),
):
    """Generate demo price history for testing. Creates one snapshot per day."""
    mkt = marketplace.upper()
    asin_upper = asin.upper()

    product = await product_service.get_product(session, mkt, asin_upper)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {mkt}/{asin_upper} not found. Add it first.",
        )

    from app.config import MARKETPLACE_CONFIG
    currency = MARKETPLACE_CONFIG.get(mkt, {}).get("currency", "USD")
    base_price = random.uniform(50, 500)
    now = datetime.now(timezone.utc)

    count = 0
    for i in range(days, 0, -1):
        ts = now - timedelta(days=i)
        fluctuation = 1 + random.uniform(-0.15, 0.15)
        price = round(base_price * fluctuation, 2)
        await snapshot_service.save_snapshot(
            session,
            product.id,
            current_price=price,
            currency=currency,
            crawl_timestamp=ts,
        )
        count += 1

    await session.commit()
    return {"status": "ok", "snapshots_created": count, "base_price": round(base_price, 2)}


@router.get("/products/{marketplace}/{asin}/forecast")
async def forecast_price_endpoint(
    marketplace: str,
    asin: str,
    forecast_date: date | None = None,
    custom_price: float | None = None,
    custom_start_date: date | None = None,
    custom_duration: int = 0,
    session: AsyncSession = Depends(get_db),
):
    """Forecast Was Price and T30 up to forecast_date."""
    mkt = marketplace.upper()
    asin_upper = asin.upper()

    product = await product_service.get_product(session, mkt, asin_upper)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {mkt}/{asin_upper} not found.")

    latest = await snapshot_service.get_latest_snapshot(session, product.id)
    if latest is None or latest.current_price is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No price data for {mkt}/{asin_upper}. Crawl first.")

    from datetime import date as date_type
    today = date_type.today()
    if forecast_date is None:
        forecast_date = today + timedelta(days=90)
    days_ahead = max(1, (forecast_date - today).days)

    custom_start_day = 0
    if custom_start_date is not None:
        custom_start_day = max(0, (custom_start_date - today).days)

    forecasts = await price_analytics.forecast_price(
        session, product.id, latest.current_price,
        days_ahead=min(days_ahead, 365),
        custom_price=custom_price,
        custom_start_day=custom_start_day,
        custom_duration=custom_duration,
    )
    return {
        "asin": asin_upper,
        "marketplace": mkt,
        "current_price": latest.current_price,
        "custom_price": custom_price,
        "custom_start_date": custom_start_date.isoformat() if custom_start_date else None,
        "custom_start_day": custom_start_day,
        "custom_duration": custom_duration,
        "forecast_date": forecast_date.isoformat(),
        "currency": latest.currency,
        "days": len(forecasts),
        # Final day values = Was Price / T30 at forecast date
        "final_was_price": forecasts[-1]["was_price"] if forecasts else None,
        "final_t30": forecasts[-1]["t30"] if forecasts else None,
        "forecast": forecasts,
    }


@router.get("/exchange-rate")
async def get_exchange_rate(
    from_currency: str = "AED",
    to_currency: str = "USD",
):
    """Fetch live exchange rate using a free API."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/{from_currency.lower()}.json"
            )
            resp.raise_for_status()
            data = resp.json()
            rates = data.get(from_currency.lower(), {})
            rate = rates.get(to_currency.lower())
            if rate is None:
                raise HTTPException(status_code=404, detail=f"Rate not found: {from_currency} → {to_currency}")
            return {"from": from_currency.upper(), "to": to_currency.upper(), "rate": rate}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Exchange rate API error: {e}")


@router.post("/crawl-all")
async def crawl_all_products(
    session: AsyncSession = Depends(get_db),
):
    """Crawl all tracked products sequentially."""
    products = await product_service.list_products(session)
    if not products:
        return {"status": "ok", "crawled": 0, "message": "No products to crawl."}

    from app.scrapers.scraper import scrape_product
    settings = get_settings()
    results = []

    for product in products:
        try:
            parsed = await scrape_product(None, product.marketplace, product.asin, settings)
            await snapshot_service.save_snapshot(
                session, product.id,
                current_price=parsed.current_price, currency=parsed.currency,
                list_price=parsed.list_price, rating=parsed.rating,
                review_count=parsed.review_count, availability_text=parsed.availability_text,
                seller_info=parsed.seller_info, bullet_points=parsed.bullet_points,
            )
            await product_service.upsert_product(
                session, product.marketplace, product.asin, parsed.url,
                title=parsed.title, brand=parsed.brand, main_image_url=parsed.main_image_url,
            )
            results.append({"asin": product.asin, "marketplace": product.marketplace, "price": parsed.current_price, "status": "ok"})
        except Exception as e:
            logger.error("Crawl failed for %s/%s: %s", product.marketplace, product.asin, e)
            results.append({"asin": product.asin, "marketplace": product.marketplace, "status": "failed", "error": str(e)})

    await session.commit()
    return {"status": "ok", "crawled": len(results), "results": results}


@router.post("/simulations/save")
async def save_simulation(
    body: dict,
    session: AsyncSession = Depends(get_db),
):
    """Save a simulation record to the database."""
    from app.models.simulation import SimulationRecord
    record = SimulationRecord(
        asin=body.get("asin", ""),
        marketplace=body.get("marketplace", ""),
        current_price=body.get("current_price"),
        custom_price=body.get("custom_price"),
        custom_start_day=body.get("custom_start_day"),
        custom_duration=body.get("custom_duration"),
        currency=body.get("currency"),
        forecast_days=body.get("forecast_days"),
        forecast_data=body.get("forecast"),
    )
    session.add(record)
    await session.flush()
    await session.commit()
    return {"status": "ok", "id": record.id}


@router.get("/simulations")
async def list_simulations(
    marketplace: str | None = None,
    asin: str | None = None,
    session: AsyncSession = Depends(get_db),
):
    """List saved simulations with optional filters."""
    from sqlalchemy import select
    from app.models.simulation import SimulationRecord
    stmt = select(SimulationRecord).order_by(SimulationRecord.created_at.desc())
    if marketplace:
        stmt = stmt.where(SimulationRecord.marketplace == marketplace.upper())
    if asin:
        stmt = stmt.where(SimulationRecord.asin == asin.upper())
    result = await session.execute(stmt)
    records = result.scalars().all()
    return [
        {
            "id": r.id, "asin": r.asin, "marketplace": r.marketplace,
            "current_price": r.current_price, "custom_price": r.custom_price,
            "custom_start_day": r.custom_start_day, "custom_duration": r.custom_duration,
            "currency": r.currency, "forecast_days": r.forecast_days,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]


@router.get("/simulations/export")
async def export_simulations(
    marketplace: str | None = None,
    asin: str | None = None,
    session: AsyncSession = Depends(get_db),
):
    """Export simulation records as CSV."""
    from sqlalchemy import select
    from app.models.simulation import SimulationRecord
    stmt = select(SimulationRecord).order_by(SimulationRecord.created_at.desc())
    if marketplace:
        stmt = stmt.where(SimulationRecord.marketplace == marketplace.upper())
    if asin:
        stmt = stmt.where(SimulationRecord.asin == asin.upper())
    result = await session.execute(stmt)
    records = result.scalars().all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ID", "ASIN", "Marketplace", "Currency", "Current Price", "Custom Price",
                      "Custom Start Day", "Custom Duration", "Forecast Days", "Created At",
                      "Day", "Was Price", "T30"])
    for r in records:
        if r.forecast_data:
            for day_data in r.forecast_data:
                writer.writerow([
                    r.id, r.asin, r.marketplace, r.currency, r.current_price,
                    r.custom_price, r.custom_start_day, r.custom_duration,
                    r.forecast_days, r.created_at.isoformat() if r.created_at else "",
                    day_data.get("date", ""), day_data.get("was_price", ""), day_data.get("t30", ""),
                ])
        else:
            writer.writerow([
                r.id, r.asin, r.marketplace, r.currency, r.current_price,
                r.custom_price, r.custom_start_day, r.custom_duration,
                r.forecast_days, r.created_at.isoformat() if r.created_at else "",
                "", "", "",
            ])

    filename = f"simulations_{marketplace or 'all'}_{asin or 'all'}.csv"
    return StreamingResponse(
        io.StringIO(buf.getvalue()),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
