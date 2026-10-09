"""T036 — evidence viewer (FR-015, FR-031, R-009 e). RED until T038/T040.

Only text, at most 256 KB, and only content that passes the strict (v2) scan is shown; otherwise a reason. An
integrity-failed Run never shows evidence.
"""

from __future__ import annotations

import json
import shutil

import pytest

from engine.evidence import canonical_json_bytes, sha256_bytes
from engine.web import readmodel
from engine.web.preflight import ReadinessStore
from tests.fixtures import web_bundles as wb


def _reader(root, tmp_path):
    return readmodel.WorkbenchReader(
        readmodel.load_catalog(), root, readiness=ReadinessStore(tmp_path / "preflight")
    )


def _with_extra_file(built, tmp_path, name, payload, mime="application/json"):
    target = tmp_path / "copy" / built.run_id
    shutil.copytree(built.bundle, target)
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    manifest.pop("bundle_digest")
    manifest.pop("redaction_profile", None)  # unmarked = sealed before T020 (v1); a leak then stays non-blocking
    (target / name).write_bytes(payload)
    manifest["files"].append({"path": name, "mime_type": mime, "size_bytes": len(payload), "sha256": sha256_bytes(payload)})
    manifest["files"].sort(key=lambda record: record["path"])
    manifest["bundle_digest"] = sha256_bytes(canonical_json_bytes(manifest))
    (target / "manifest.json").write_bytes(canonical_json_bytes(manifest))
    return target.parent


def test_text_evidence_is_shown_as_sealed(tmp_path) -> None:
    root = tmp_path / "runs"
    built = wb.spec004_run(root, "E-01")
    item = _reader(root, tmp_path).evidence(built.run_id, "file:report-reads.jsonl")
    assert item["viewable"] is True and item["reason"] is None
    assert item["text"] == (built.bundle / "report-reads.jsonl").read_text(encoding="utf-8")
    assert len(item["sha256"]) == 64 and item["evidence_name"]


def test_binary_evidence_is_not_shown(tmp_path) -> None:
    root = tmp_path / "runs"
    built = wb.h03_case(root, "pass")
    manifest = json.loads((built.bundle / "manifest.json").read_text(encoding="utf-8"))
    png = next(record for record in manifest["files"] if record["mime_type"] == "image/png")
    item = _reader(root, tmp_path).evidence(built.run_id, f"artifact:{png['artifact_id']}")
    assert (item["viewable"], item["text"]) == (False, None)
    assert item["reason"]


def test_large_text_is_not_shown(tmp_path) -> None:
    built = wb.h03_case(tmp_path / "runs", "pass")
    root = _with_extra_file(built, tmp_path, "big.json", json.dumps({"x": "a" * (256 * 1024)}).encode())
    item = _reader(root, tmp_path).evidence(built.run_id, "file:big.json")
    assert (item["viewable"], item["text"]) == (False, None)
    assert "256" in item["reason"]


def test_text_failing_the_strict_scan_is_not_shown(tmp_path) -> None:
    built = wb.h03_case(tmp_path / "runs", "pass")
    payload = json.dumps({"p": "C:\\Users\\alice\\runs\\abc"}).encode()
    root = _with_extra_file(built, tmp_path, "notes.json", payload)
    item = _reader(root, tmp_path).evidence(built.run_id, "file:notes.json")
    assert (item["viewable"], item["text"]) == (False, None)
    assert "alice" not in json.dumps(item)


def test_integrity_failed_run_blocks_evidence(tmp_path) -> None:
    root = tmp_path / "runs"
    built = wb.spec004_run(root, "E-01")
    wb.tampered(built)
    with pytest.raises(readmodel.IntegrityBlocked):
        _reader(root, tmp_path).evidence(built.run_id, "file:report-reads.jsonl")


def test_unknown_reference_is_not_found(tmp_path) -> None:
    root = tmp_path / "runs"
    built = wb.spec004_run(root, "E-01")
    for ref in ("file:nope.jsonl", "file:../run.json", "artifact:x"):
        with pytest.raises(readmodel.EvidenceNotFound):
            _reader(root, tmp_path).evidence(built.run_id, ref)


def test_run_view_marks_viewable_evidence(tmp_path) -> None:
    root = tmp_path / "runs"
    built = wb.h03_case(root, "pass")
    view = _reader(root, tmp_path).run(built.run_id)
    kinds = {item["mime_type"]: item["viewable"] for item in view["evidence"]}
    assert kinds["image/png"] is False
    assert kinds["application/json"] is True
