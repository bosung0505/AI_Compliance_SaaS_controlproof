"""Spec 009 plan Compatibility (a) — every shared bundle keeps its recorded verification result.

`scripts.share_records --verify` refuses on this branch because the snapshot pins `b76af4c` display code; this is the
real regression gate (analysis A1, resolution 1).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.shared_records import verification

REVIEW_DATA = Path("review-data")
SNAPSHOT = REVIEW_DATA / "snapshot.json"

pytestmark = pytest.mark.skipif(not SNAPSHOT.is_file(), reason="review-data is not checked out")


def _records() -> list[dict]:
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))["records"] if SNAPSHOT.is_file() else []


def test_snapshot_lists_twenty_five_records() -> None:
    records = _records()
    assert len(records) == 25
    statuses = [record["verification"]["bundle_status"] for record in records]
    assert statuses.count("VERIFIED") == 24 and statuses.count("INVALID") == 1


@pytest.mark.parametrize("record", _records(), ids=lambda record: record["run_id"])
def test_bundle_verification_matches_snapshot_record(record: dict) -> None:
    assert verification(REVIEW_DATA / "bundles" / record["run_id"]) == record["verification"]
