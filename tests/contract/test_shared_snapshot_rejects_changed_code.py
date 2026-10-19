"""Spec 009 plan Compatibility (b) — the shared snapshot pins `b76af4c` display code and refuses on this branch.

A new shared snapshot is built at Spec 009 closure (tasks T019); until then this refusal is the expected behaviour.
"""

from __future__ import annotations

import pytest

from engine.shared_records import DEFAULT_SNAPSHOT, SnapshotError, load_snapshot

pytestmark = pytest.mark.skipif(not DEFAULT_SNAPSHOT.is_file(), reason="review-data is not checked out")


def test_shared_snapshot_refuses_changed_display_code() -> None:
    with pytest.raises(SnapshotError) as error:
        load_snapshot(DEFAULT_SNAPSHOT)
    assert str(error.value).startswith("Snapshot display code/catalog differs")
