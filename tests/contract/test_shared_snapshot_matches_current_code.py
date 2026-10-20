"""Spec 009 closure — the shared snapshot `shared-actual-20261020-r2` pins this branch's display code and loads.

Until the closure the snapshot pinned `b76af4c` and refused on this branch (plan Compatibility (b)); the closure rebuilt it
with the same 25 records byte-for-byte plus the three N-01/N-03 records. The closure follow-up (N-03 scenario screen scope
lines) re-pinned the display code as `-r2` with the same 28 records.
"""

from __future__ import annotations

import pytest

from engine.shared_records import DEFAULT_SNAPSHOT, display_hashes, load_snapshot

pytestmark = pytest.mark.skipif(not DEFAULT_SNAPSHOT.is_file(), reason="review-data is not checked out")


def test_shared_snapshot_loads_with_current_display_code() -> None:
    snapshot = load_snapshot(DEFAULT_SNAPSHOT)
    assert snapshot["snapshot_id"] == "shared-actual-20261020-r2"
    assert snapshot["display_files"] == display_hashes(DEFAULT_SNAPSHOT.parents[1])
    assert len(snapshot["records"]) == 28
    official = {record["run_id"] for record in snapshot["records"] if record["official"]}
    assert {
        "48a70f5e-aa62-41fc-bf58-3624a6102b4f",
        "d3aac7d9-0a52-4f9a-9c8f-f6e1f7b6de18",
        "f27b68e8-0df8-46b3-a198-c7917c2f08bb",
    } <= official
    assert [item["run_id"] for item in snapshot["missing_records"]] == ["7b59237e-0a96-403a-9add-28b91011e950"]
