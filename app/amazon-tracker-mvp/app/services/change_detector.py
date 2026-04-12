"""Change detection logic — compares consecutive snapshots for monitored fields."""

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.change import ChangeRecord
from app.models.snapshot import ProductSnapshot
from app.services.snapshot_service import get_latest_snapshot

logger = logging.getLogger(__name__)

MONITORED_FIELDS = ["current_price", "review_count", "availability_text"]


async def detect_changes(
    session: AsyncSession,
    product_id: int,
    new_snapshot: ProductSnapshot,
) -> list[ChangeRecord]:
    """Compare *new_snapshot* against the previous snapshot for the same product.

    Returns a list of persisted :class:`ChangeRecord` instances for every
    monitored field that differs between the two snapshots.  Returns an empty
    list when no previous snapshot exists (first crawl).
    """
    previous = await get_latest_snapshot(session, product_id)

    if previous is None:
        logger.info(
            "No previous snapshot for product_id=%d — skipping change detection",
            product_id,
        )
        return []

    # Don't compare the snapshot against itself.
    if previous.id == new_snapshot.id:
        return []

    now = datetime.now(timezone.utc)
    changes: list[ChangeRecord] = []

    for field in MONITORED_FIELDS:
        old_val = getattr(previous, field, None)
        new_val = getattr(new_snapshot, field, None)

        if _values_differ(old_val, new_val):
            record = ChangeRecord(
                product_id=product_id,
                field_name=field,
                old_value=_to_str(old_val),
                new_value=_to_str(new_val),
                detected_at=now,
            )
            session.add(record)
            changes.append(record)
            logger.info(
                "Change detected for product_id=%d field=%s: %s -> %s",
                product_id,
                field,
                old_val,
                new_val,
            )

    if changes:
        await session.flush()

    return changes


def _values_differ(old, new) -> bool:
    """Return True when *old* and *new* represent different values."""
    if old is None and new is None:
        return False
    if old is None or new is None:
        return True
    # Use string comparison to handle float/int vs str edge cases consistently.
    return str(old) != str(new)


def _to_str(value) -> str | None:
    """Convert a field value to its string representation for storage."""
    if value is None:
        return None
    return str(value)
