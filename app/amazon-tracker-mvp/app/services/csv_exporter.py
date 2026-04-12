"""CSV export for product snapshot data."""

import csv
import io
from datetime import timezone

from app.models.snapshot import ProductSnapshot

CSV_COLUMNS = [
    "crawl_timestamp",
    "current_price",
    "currency",
    "list_price",
    "rating",
    "review_count",
    "availability_text",
    "seller_info",
    "bullet_points",
]


def export_snapshots_csv(snapshots: list[ProductSnapshot]) -> str:
    """Generate CSV string from snapshot records.

    Headers match snapshot field names.  Rows are ordered by
    *crawl_timestamp* ascending.  Timestamps are formatted in ISO 8601 UTC.
    Returns a headers-only CSV when *snapshots* is empty.
    """
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(CSV_COLUMNS)

    sorted_snapshots = sorted(snapshots, key=lambda s: s.crawl_timestamp)

    for snap in sorted_snapshots:
        ts = snap.crawl_timestamp
        # Ensure UTC and format as ISO 8601
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        iso_ts = ts.astimezone(timezone.utc).isoformat()

        # Join bullet_points list with semicolons; empty string for None
        bp = ""
        if snap.bullet_points:
            bp = ";".join(str(b) for b in snap.bullet_points)

        writer.writerow([
            iso_ts,
            snap.current_price if snap.current_price is not None else "",
            snap.currency or "",
            snap.list_price if snap.list_price is not None else "",
            snap.rating if snap.rating is not None else "",
            snap.review_count if snap.review_count is not None else "",
            snap.availability_text or "",
            snap.seller_info or "",
            bp,
        ])

    return buf.getvalue()
