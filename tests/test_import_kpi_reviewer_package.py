from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from scripts import import_kpi_reviewer_package as importer


def test_parse_timestamp_requires_timezone() -> None:
    with pytest.raises(ValueError, match="review_timestamp_timezone_missing"):
        importer._parse_timestamp(
            "2026-08-03T12:00:00", case_id="case-1", field="start"
        )


def test_split_answer_deduplicates_and_sorts() -> None:
    assert importer._split_answer("b|a|b") == ["a", "b"]


def test_overlapping_review_intervals_are_detectable() -> None:
    start = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)
    intervals = [
        importer.ReviewedInterval("case-1", start, start + timedelta(seconds=2)),
        importer.ReviewedInterval(
            "case-2", start + timedelta(seconds=1), start + timedelta(seconds=3)
        ),
    ]

    ordered = sorted(intervals, key=lambda item: item.start)

    assert ordered[1].start < ordered[0].end
