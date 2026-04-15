"""Unit tests for the CSV exporter service."""

import csv
import io
from datetime import datetime, timezone

from app.models.snapshot import ProductSnapshot
from app.services.csv_exporter import CSV_COLUMNS, export_snapshots_csv


def _make_snapshot(**overrides) -> ProductSnapshot:
    """Create a lightweight ProductSnapshot instance for testing."""
    defaults = {
        "id": 1,
        "product_id": 1,
        "current_price": 29.99,
        "currency": "AED",
        "list_price": 39.99,
        "rating": 4.5,
        "review_count": 120,
        "seller_info": "Amazon.ae",
        "bullet_points": ["Feature A", "Feature B"],
        "crawl_timestamp": datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
    }
    defaults.update(overrides)
    snap = ProductSnapshot.__new__(ProductSnapshot)
    for k, v in defaults.items():
        object.__setattr__(snap, k, v)
    return snap


def _parse_csv(csv_string: str) -> list[list[str]]:
    """Parse a CSV string into a list of rows."""
    reader = csv.reader(io.StringIO(csv_string))
    return list(reader)


class TestExportSnapshotsCsv:
    """Tests for export_snapshots_csv()."""

    def test_empty_list_returns_headers_only(self):
        result = export_snapshots_csv([])
        rows = _parse_csv(result)
        assert len(rows) == 1
        assert rows[0] == CSV_COLUMNS

    def test_single_snapshot_produces_header_and_one_row(self):
        snap = _make_snapshot()
        result = export_snapshots_csv([snap])
        rows = _parse_csv(result)
        assert len(rows) == 2
        assert rows[0] == CSV_COLUMNS

    def test_headers_match_csv_columns(self):
        result = export_snapshots_csv([_make_snapshot()])
        rows = _parse_csv(result)
        assert rows[0] == CSV_COLUMNS

    def test_timestamp_iso8601_utc(self):
        ts = datetime(2025, 6, 1, 8, 30, 0, tzinfo=timezone.utc)
        snap = _make_snapshot(crawl_timestamp=ts)
        result = export_snapshots_csv([snap])
        rows = _parse_csv(result)
        assert "2025-06-01T08:30:00+00:00" == rows[1][0]

    def test_rows_ordered_by_crawl_timestamp_ascending(self):
        ts1 = datetime(2025, 3, 1, tzinfo=timezone.utc)
        ts2 = datetime(2025, 1, 1, tzinfo=timezone.utc)
        ts3 = datetime(2025, 2, 1, tzinfo=timezone.utc)
        snaps = [
            _make_snapshot(crawl_timestamp=ts1),
            _make_snapshot(crawl_timestamp=ts2),
            _make_snapshot(crawl_timestamp=ts3),
        ]
        result = export_snapshots_csv(snaps)
        rows = _parse_csv(result)
        timestamps = [r[0] for r in rows[1:]]
        assert timestamps == sorted(timestamps)

    def test_bullet_points_joined_with_semicolons(self):
        snap = _make_snapshot(bullet_points=["A", "B", "C"])
        result = export_snapshots_csv([snap])
        rows = _parse_csv(result)
        bp_idx = CSV_COLUMNS.index("bullet_points")
        assert rows[1][bp_idx] == "A;B;C"

    def test_none_bullet_points_produces_empty_string(self):
        snap = _make_snapshot(bullet_points=None)
        result = export_snapshots_csv([snap])
        rows = _parse_csv(result)
        bp_idx = CSV_COLUMNS.index("bullet_points")
        assert rows[1][bp_idx] == ""

    def test_none_fields_produce_empty_strings(self):
        snap = _make_snapshot(
            current_price=None,
            currency=None,
            list_price=None,
            rating=None,
            review_count=None,
            seller_info=None,
        )
        result = export_snapshots_csv([snap])
        rows = _parse_csv(result)
        # All value columns (index 1-8) should be empty strings
        for val in rows[1][1:]:
            assert val == ""

    def test_numeric_values_preserved(self):
        snap = _make_snapshot(current_price=199.50, list_price=249.00, rating=3.8, review_count=5000)
        result = export_snapshots_csv([snap])
        rows = _parse_csv(result)
        price_idx = CSV_COLUMNS.index("current_price")
        list_idx = CSV_COLUMNS.index("list_price")
        rating_idx = CSV_COLUMNS.index("rating")
        review_idx = CSV_COLUMNS.index("review_count")
        assert rows[1][price_idx] == "199.5"
        assert rows[1][list_idx] == "249.0"
        assert rows[1][rating_idx] == "3.8"
        assert rows[1][review_idx] == "5000"

    def test_row_count_matches_snapshot_count(self):
        snaps = [
            _make_snapshot(crawl_timestamp=datetime(2025, 1, i + 1, tzinfo=timezone.utc))
            for i in range(5)
        ]
        result = export_snapshots_csv(snaps)
        rows = _parse_csv(result)
        # 1 header + 5 data rows
        assert len(rows) == 6
