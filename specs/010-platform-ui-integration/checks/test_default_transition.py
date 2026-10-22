"""Stage7 release bytes, preserved baseline and fail-closed candidate source selection."""

from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path

import pytest

from engine.shared_records import DEFAULT_SNAPSHOT, load_snapshot

builder = importlib.import_module("specs.010-platform-ui-integration.checks.build_candidate")
FEATURE = Path(__file__).resolve().parents[1]
BASELINE = json.loads((FEATURE / "baseline.json").read_text(encoding="utf-8"))
ARCHIVE = DEFAULT_SNAPSHOT.with_name("snapshot.shared-actual-20261020-r2.json")


def test_reviewed_stage6_release_is_preserved_and_current_default_loads():
    stage6 = DEFAULT_SNAPSHOT.with_name("snapshot.shared-ui-stage6-20261021-r3.json")
    assert hashlib.sha256(stage6.read_bytes()).hexdigest() == (
        "011ce767128cc96c05b21416ef0bf742b916bee0063183c8389fb9c2bad95e21"
    )
    assert json.loads(stage6.read_text(encoding="utf-8"))["snapshot_digest"] == (
        "5c1cfd81dd20a4d441141f889ae9837eac32be453620f1e25d0f938ff625a8ad"
    )
    assert hashlib.sha256(DEFAULT_SNAPSHOT.read_bytes()).hexdigest() == (
        "aec6ca6284e0a9cfead97b73193a9e63e840c498415777f7a945959a205c2197"
    )
    current = load_snapshot()
    assert current["snapshot_id"] == "shared-ui-main-20261022-r2"
    assert current["snapshot_digest"] == "d282eb49e1fa448715a307f2879b3ef75a9f5d51ed2231a3de603658ef007788"
    presentation = DEFAULT_SNAPSHOT.with_name("snapshot.shared-ui-presentation-20261022-r1.json")
    assert hashlib.sha256(presentation.read_bytes()).hexdigest() == (
        "a7545eeffdb977760a595b4e9a6193a1b83c0ecc8e82a0a06d9871604056a39e"
    )


def test_previous_snapshot_preserves_exact_bytes_and_all_record_facts():
    assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() == BASELINE["snapshot"]["file_sha256"]
    old = json.loads(ARCHIVE.read_text(encoding="utf-8"))
    new = json.loads(DEFAULT_SNAPSHOT.read_text(encoding="utf-8"))
    for field in ("records", "missing_records", "target"):
        assert new[field] == old[field]
    pngs = {digest for record in new["records"] for name, digest in record["files"].items() if name.endswith(".png")}
    assert pngs == {image["sha256"] for image in BASELINE["reviewed_png_files"]}
    assert len(new["records"]) == 28
    assert sum(len(record["files"]) for record in new["records"]) == 652
    assert builder.frozen_source(DEFAULT_SNAPSHOT, BASELINE["snapshot"]) == ARCHIVE


@pytest.mark.parametrize("state", ["original", "archived", "missing", "tampered"])
def test_candidate_source_uses_only_exact_frozen_bytes(tmp_path, state):
    source = tmp_path / "snapshot.json"
    archived = tmp_path / "snapshot.frozen-id.json"
    frozen = b'{"snapshot_id":"frozen-id"}'
    baseline = {"snapshot_id": "frozen-id", "file_sha256": hashlib.sha256(frozen).hexdigest()}
    source.write_bytes(frozen if state == "original" else b"new default")
    if state in {"archived", "tampered"}:
        archived.write_bytes(frozen if state == "archived" else b"changed archive")
    if state in {"missing", "tampered"}:
        with pytest.raises(ValueError, match="Frozen source snapshot"):
            builder.frozen_source(source, baseline)
    else:
        assert builder.frozen_source(source, baseline) == (source if state == "original" else archived)
