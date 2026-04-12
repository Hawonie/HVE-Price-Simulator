"""Price analytics service: pure calculation functions and DB-backed queries.

Provides Was Price (90-day median), T30 (30-day minimum), period-filtered
snapshot retrieval, and price simulation without mutating stored data.
"""

import statistics
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.snapshot import ProductSnapshot
from app.schemas.product import SimulationResult


# ---------------------------------------------------------------------------
# Task 1.2 – Pure calculation functions (no DB dependency)
# ---------------------------------------------------------------------------


def compute_was_price(prices: list[float]) -> float | None:
    """Return the median of *prices*, or ``None`` when the list is empty."""
    if not prices:
        return None
    return statistics.median(prices)


def compute_t30(prices: list[float]) -> float | None:
    """Return the minimum of *prices*, or ``None`` when the list is empty."""
    if not prices:
        return None
    return min(prices)


# ---------------------------------------------------------------------------
# Task 3.1 – Filtered snapshot retrieval
# ---------------------------------------------------------------------------


async def get_filtered_snapshots(
    session: AsyncSession,
    product_id: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[ProductSnapshot]:
    """Return snapshots for *product_id* filtered by an optional date window.

    Results are ordered by ``crawl_timestamp`` ascending.  When *start_date*
    or *end_date* is ``None`` the corresponding bound is left open.
    """
    stmt = (
        select(ProductSnapshot)
        .where(ProductSnapshot.product_id == product_id)
    )
    if start_date is not None:
        stmt = stmt.where(ProductSnapshot.crawl_timestamp >= start_date)
    if end_date is not None:
        stmt = stmt.where(ProductSnapshot.crawl_timestamp <= end_date)
    stmt = stmt.order_by(ProductSnapshot.crawl_timestamp.asc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Task 3.2 – Was Price / T30 with DB look-up
# ---------------------------------------------------------------------------


def _make_naive(dt: datetime) -> datetime:
    """Strip timezone info for SQLite compatibility."""
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


async def get_was_price(
    session: AsyncSession,
    product_id: int,
    reference_date: date,
) -> tuple[float | None, int]:
    window_start = _make_naive(datetime(reference_date.year, reference_date.month, reference_date.day) - timedelta(days=90))
    window_end = _make_naive(datetime(reference_date.year, reference_date.month, reference_date.day, 23, 59, 59, 999999))

    stmt = (
        select(ProductSnapshot.current_price)
        .where(
            ProductSnapshot.product_id == product_id,
            ProductSnapshot.crawl_timestamp >= window_start,
            ProductSnapshot.crawl_timestamp <= window_end,
            ProductSnapshot.current_price.isnot(None),
        )
    )
    result = await session.execute(stmt)
    prices: list[float] = [row[0] for row in result.all()]
    return compute_was_price(prices), len(prices)


async def get_t30(
    session: AsyncSession,
    product_id: int,
    reference_date: date,
) -> tuple[float | None, int]:
    window_start = _make_naive(datetime(reference_date.year, reference_date.month, reference_date.day) - timedelta(days=30))
    window_end = _make_naive(datetime(reference_date.year, reference_date.month, reference_date.day, 23, 59, 59, 999999))

    stmt = (
        select(ProductSnapshot.current_price)
        .where(
            ProductSnapshot.product_id == product_id,
            ProductSnapshot.crawl_timestamp >= window_start,
            ProductSnapshot.crawl_timestamp <= window_end,
            ProductSnapshot.current_price.isnot(None),
        )
    )
    result = await session.execute(stmt)
    prices: list[float] = [row[0] for row in result.all()]
    return compute_t30(prices), len(prices)


# ---------------------------------------------------------------------------
# Task 3.3 – Price simulation (read-only, no DB mutation)
# ---------------------------------------------------------------------------


async def simulate_price(
    session: AsyncSession,
    product_id: int,
    simulation_date: date,
    simulation_price: float,
    evaluation_date: date,
) -> SimulationResult:
    """Simulate injecting *simulation_price* on *simulation_date* and evaluate.

    1. Fetch all snapshots with a non-null ``current_price`` that fall within
       the 90-day window ending on *evaluation_date* (the wider of the two
       look-back windows).
    2. Compute "before" Was Price and T30 from the original prices.
    3. Inject the virtual price into an in-memory copy and compute "after"
       Was Price and T30.
    4. Return a :class:`SimulationResult` – the actual DB is never modified.
    """
    # Widest window needed is 90 days for Was Price
    window_start = _make_naive(datetime(evaluation_date.year, evaluation_date.month, evaluation_date.day) - timedelta(days=90))
    window_end = _make_naive(datetime(evaluation_date.year, evaluation_date.month, evaluation_date.day, 23, 59, 59, 999999))

    stmt = (
        select(ProductSnapshot)
        .where(
            ProductSnapshot.product_id == product_id,
            ProductSnapshot.crawl_timestamp >= window_start,
            ProductSnapshot.crawl_timestamp <= window_end,
            ProductSnapshot.current_price.isnot(None),
        )
        .order_by(ProductSnapshot.crawl_timestamp.asc())
    )
    result = await session.execute(stmt)
    snapshots = list(result.scalars().all())

    eval_dt = window_end
    was_start = eval_dt - timedelta(days=90)
    t30_start = eval_dt - timedelta(days=30)

    was_prices_before: list[float] = []
    t30_prices_before: list[float] = []
    for snap in snapshots:
        ts = _make_naive(snap.crawl_timestamp) if snap.crawl_timestamp else snap.crawl_timestamp
        price = snap.current_price
        if price is None:
            continue
        if was_start <= ts <= eval_dt:
            was_prices_before.append(price)
        if t30_start <= ts <= eval_dt:
            t30_prices_before.append(price)

    before_was = compute_was_price(was_prices_before)
    before_t30 = compute_t30(t30_prices_before)

    sim_dt = _make_naive(datetime(simulation_date.year, simulation_date.month, simulation_date.day, 12, 0, 0))

    was_prices_after = list(was_prices_before)
    t30_prices_after = list(t30_prices_before)

    if was_start <= sim_dt <= eval_dt:
        was_prices_after.append(simulation_price)
    if t30_start <= sim_dt <= eval_dt:
        t30_prices_after.append(simulation_price)

    after_was = compute_was_price(was_prices_after)
    after_t30 = compute_t30(t30_prices_after)

    return SimulationResult(
        evaluation_date=evaluation_date,
        before_was_price=before_was,
        after_was_price=after_was,
        before_t30=before_t30,
        after_t30=after_t30,
        simulation_date=simulation_date,
        simulation_price=simulation_price,
    )


# ---------------------------------------------------------------------------
# Forecast – assume current price stays flat into the future
# ---------------------------------------------------------------------------


async def forecast_price(
    session: AsyncSession,
    product_id: int,
    current_price: float,
    days_ahead: int = 90,
    custom_price: float | None = None,
    custom_start_day: int = 0,
    custom_duration: int = 0,
) -> list[dict]:
    """Forecast Was Price and T30 for each day from today to today+days_ahead.

    - Assumes current_price every day (past and future) where no real data exists.
    - If custom_price is set, uses it during the custom window.
    - Past days without real snapshots are backfilled with current_price.
    """
    today = date.today()

    furthest = today + timedelta(days=days_ahead)
    # Need 90 days back from the furthest date for Was Price window
    window_start = _make_naive(datetime(furthest.year, furthest.month, furthest.day) - timedelta(days=90))

    stmt = (
        select(ProductSnapshot.current_price, ProductSnapshot.crawl_timestamp)
        .where(
            ProductSnapshot.product_id == product_id,
            ProductSnapshot.crawl_timestamp >= window_start,
            ProductSnapshot.current_price.isnot(None),
        )
        .order_by(ProductSnapshot.crawl_timestamp.asc())
    )
    result = await session.execute(stmt)
    existing = [(row[0], _make_naive(row[1]) if row[1] else row[1]) for row in result.all()]

    # Build a set of dates that have real data
    real_dates: set[date] = set()
    for _, ts in existing:
        if ts:
            real_dates.add(ts.date() if isinstance(ts, datetime) else ts)

    custom_start = custom_start_day if custom_price is not None else -1
    custom_end = custom_start + custom_duration - 1 if custom_price is not None and custom_duration > 0 else -1

    forecasts = []
    for offset in range(days_ahead + 1):
        eval_date = today + timedelta(days=offset)
        eval_dt = _make_naive(datetime(eval_date.year, eval_date.month, eval_date.day, 23, 59, 59, 999999))
        was_start = eval_dt - timedelta(days=90)
        t30_start = eval_dt - timedelta(days=30)

        was_prices: list[float] = []
        t30_prices: list[float] = []

        # Add real snapshot prices
        for price, ts in existing:
            if was_start <= ts <= eval_dt:
                was_prices.append(price)
            if t30_start <= ts <= eval_dt:
                t30_prices.append(price)

        # Backfill past days (before today) that have no real data with current_price
        was_start_date = (was_start.date() if isinstance(was_start, datetime) else was_start)
        t30_start_date = (t30_start.date() if isinstance(t30_start, datetime) else t30_start)
        for back_day in range(91):  # cover full 90-day window
            back_date = eval_date - timedelta(days=back_day)
            if back_date > today:
                continue  # future days handled below
            if back_date in real_dates:
                continue  # already have real data
            back_dt = _make_naive(datetime(back_date.year, back_date.month, back_date.day, 12, 0, 0))
            if was_start <= back_dt <= eval_dt:
                was_prices.append(current_price)
            if t30_start <= back_dt <= eval_dt:
                t30_prices.append(current_price)

        # Inject future prices (today onwards)
        for d in range(offset + 1):
            inject_date = today + timedelta(days=d)
            if inject_date in real_dates and d == 0:
                continue  # today already has real data from crawl
            inject_dt = _make_naive(datetime(inject_date.year, inject_date.month, inject_date.day, 12, 0, 0))
            if custom_start >= 0 and custom_start <= d <= custom_end:
                day_price = custom_price
            else:
                day_price = current_price
            if was_start <= inject_dt <= eval_dt:
                was_prices.append(day_price)
            if t30_start <= inject_dt <= eval_dt:
                t30_prices.append(day_price)

        # Determine assumed price for this day
        if custom_start >= 0 and custom_start <= offset <= custom_end:
            assumed = custom_price
        else:
            assumed = current_price

        forecasts.append({
            "date": eval_date.isoformat(),
            "was_price": compute_was_price(was_prices),
            "t30": compute_t30(t30_prices),
            "assumed_price": assumed,
        })

    return forecasts
