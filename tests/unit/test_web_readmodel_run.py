"""T035 — run view (FR-013~020, SC-002, R-003; ID-005-01). RED until T038.

Integrity first; everything shown is copied from the sealed bundle through `verify_bundle` and `load_bundle_summary`.
ID-005-01: an ABORTED Run whose only problem is missing required-evidence links shows "봉인 무결성 확인됨 + 중단으로 빠진
증적 목록" with the run state first; a COMPLETED Run with a missing link and any hash mismatch are integrity failures. The
CLI `verify` result never changes.
"""

from __future__ import annotations

import copy
import json
import shutil
import uuid

import pytest

from engine.evidence import canonical_json_bytes, sha256_bytes, verify_bundle
from engine.models import InconclusiveReason
from engine.presentation import load_bundle_summary
from engine.web import readmodel
from engine.web.preflight import ReadinessStore
from tests.fixtures import web_bundles as wb

FORBIDDEN_PLAIN = ("h03-report-v1", "spec004-report-v1", "fixture", "manifest", ".json", ".jsonl", "bundle")


@pytest.fixture(scope="module")
def catalog():
    return readmodel.load_catalog()


def _reader(catalog, root, tmp_path, **kwargs):
    return readmodel.WorkbenchReader(catalog, root, readiness=ReadinessStore(tmp_path / "preflight"), **kwargs)


def _plain(view):
    texts = [view["verdict"]["plain_meaning"], view["verdict"]["impact"] or ""]
    texts += [item["plain_meaning"] for item in view["assertions"]]
    return " ".join(texts)


def _drop_link(built, tmp_path, evidence_id):
    """A copy whose manifest no longer links one required evidence, resealed so hashes and digest still match."""
    copy_dir = tmp_path / "copy" / built.run_id
    shutil.copytree(built.bundle, copy_dir)
    manifest = json.loads((copy_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest.pop("bundle_digest")
    manifest["required_evidence"][evidence_id] = []
    manifest["bundle_digest"] = sha256_bytes(canonical_json_bytes(manifest))
    (copy_dir / "manifest.json").write_bytes(canonical_json_bytes(manifest))
    return copy_dir


@pytest.mark.parametrize("case", ["pass", "fail", "missing"])
def test_verified_run_copies_verdict_assertions_and_reason_codes(catalog, tmp_path, case) -> None:
    root = tmp_path / "runs"
    built = wb.h03_case(root, case)
    view = _reader(catalog, root, tmp_path).run(built.run_id)
    summary = load_bundle_summary(built.bundle)
    assert (view["schema_version"], view["view"]) == ("controlproof.web.v1", "run")
    assert view["integrity"] == {"status": "VERIFIED", "problems": [], "aborted_missing_evidence": []}
    assert (view["verdict"]["value"], view["verdict"]["reason_code"]) == (summary["verdict"], summary["reason_code"])
    assert view["verdict"]["summary"] == summary["summary"]
    shown = [(item["assertion_id"], item["status"], item["reason_code"]) for item in view["assertions"]]
    assert shown == [(item["assertion_id"], item["status"], item["reason_code"]) for item in summary["assertions"]]
    for item, source in zip(view["assertions"], summary["assertions"], strict=True):
        assert (item["expected"], item["actual"], item["detail"]) == (source["expected"], source["actual"], source["detail"])
    for word in FORBIDDEN_PLAIN:
        assert word not in _plain(view), word


def test_every_pass_or_fail_assertion_reaches_evidence_with_sha256(catalog, tmp_path) -> None:
    root = tmp_path / "runs"
    for built in (wb.h03_case(root, "fail"), wb.spec004_run(root, "E-01")):
        view = _reader(catalog, root, tmp_path).run(built.run_id)
        by_ref = {item["ref"]: item for item in view["evidence"]}
        for assertion in view["assertions"]:
            if assertion["status"] in {"PASS", "FAIL"}:
                linked = [by_ref[ref] for ref in assertion["evidence_refs"] if ref in by_ref]
                assert linked and all(len(item["sha256"]) == 64 for item in linked), assertion["assertion_id"]
        for item in view["evidence"]:
            assert item["evidence_name"] and item["relative_path"].startswith("<run_root>/")
            assert {"mime_type", "size_bytes", "sha256", "phase", "evidence_requirement_ids", "viewable"} <= set(item)


def test_inconclusive_reason_code_is_copied(catalog, tmp_path) -> None:
    root = tmp_path / "runs"
    built = wb.h03_inconclusive(root, InconclusiveReason.ACCESS_LIMITED)
    view = _reader(catalog, root, tmp_path).run(built.run_id)
    assert (view["verdict"]["value"], view["verdict"]["reason_code"]) == ("INCONCLUSIVE", "ACCESS_LIMITED")
    assert view["verdict"]["badge"] == "access_limited"


def test_restore_failed_shows_safety_badge_before_verdict(catalog, tmp_path) -> None:
    root = tmp_path / "runs"
    built = wb.h03_case(root, "restore_failed")
    view = _reader(catalog, root, tmp_path).run(built.run_id)
    assert view["run"]["run_state"] == "RESTORE_FAILED"
    assert view["display_order"][0] == "safety" and view["safety_badges"] == ["restore_failed"]
    assert view["verdict"]["target_verdict"] is False
    assert view["restore"]["manual_cleanup_required"] is True


def test_id_005_01_case1_aborted_with_only_missing_links_is_verified_with_missing_list(catalog, tmp_path) -> None:
    root = tmp_path / "runs"
    built = wb.h03_aborted(root)
    view = _reader(catalog, root, tmp_path).run(built.run_id)
    assert view["run"]["run_state"] == "ABORTED"
    assert view["display_order"][0] == "run_state"
    assert view["integrity"]["status"] == "VERIFIED"
    assert view["integrity"]["aborted_missing_evidence"] == ["EV-06", "EV-07"]
    assert view["verdict"]["value"] == built.verdict and view["verdict"]["target_verdict"] is False
    assert view["assertions"] is not None and view["evidence"] is not None
    assert verify_bundle(built.bundle)["bundle_status"] == "INVALID"  # the CLI verify result is unchanged


def test_id_005_01_case2_completed_with_missing_link_is_integrity_failure(catalog, tmp_path) -> None:
    built = wb.h03_case(tmp_path / "runs", "pass")
    copy_dir = _drop_link(built, tmp_path, "EV-01")
    view = _reader(catalog, copy_dir.parent, tmp_path).run(built.run_id)
    assert view["run"]["run_state"] == "COMPLETED"
    assert view["integrity"]["status"] == "INVALID"
    assert "evidence:EV-01" in view["integrity"]["problems"]
    assert (view["verdict"], view["assertions"], view["evidence"]) == (None, None, None)
    assert view["display_order"][0] == "integrity"


def test_id_005_01_case3_hash_mismatch_is_integrity_failure(catalog, tmp_path) -> None:
    root = tmp_path / "runs"
    built = wb.h03_case(root, "pass")
    wb.tampered(built)
    view = _reader(catalog, root, tmp_path).run(built.run_id)
    assert view["integrity"]["status"] == "INVALID"
    assert "judgement.json" in view["integrity"]["problems"]
    assert (view["verdict"], view["assertions"], view["evidence"]) == (None, None, None)


def test_aborted_with_hash_mismatch_is_integrity_failure(catalog, tmp_path) -> None:
    root = tmp_path / "runs"
    built = wb.h03_aborted(root)
    wb.tampered(built)
    view = _reader(catalog, root, tmp_path).run(built.run_id)
    assert view["integrity"]["status"] == "INVALID"
    assert view["verdict"] is None


def test_unreadable_bundle(catalog, tmp_path) -> None:
    root = tmp_path / "runs"
    built = wb.h03_case(root, "pass")
    wb.unreadable(built)
    view = _reader(catalog, root, tmp_path).run(built.run_id)
    assert view["integrity"]["status"] == "UNREADABLE"
    assert (view["verdict"], view["assertions"], view["evidence"]) == (None, None, None)


def test_restore_timing_is_copied_not_computed(catalog, tmp_path) -> None:
    root = tmp_path / "runs"
    spec004 = _reader(catalog, root, tmp_path).run(wb.spec004_run(root, "E-01").run_id)
    assert (spec004["restore"]["seconds"], spec004["restore"]["deadline_seconds"]) == (0.0, 120.0)
    assert spec004["restore"]["within_deadline"] is True
    h03 = _reader(catalog, root, tmp_path).run(wb.h03_case(root, "pass").run_id)
    assert (h03["restore"]["seconds"], h03["restore"]["within_deadline"]) == (None, None)
    assert h03["restore"]["deadline_seconds"] == 120
    assert h03["restore"]["status"] == "SUCCEEDED"


def test_record_origin_and_role(catalog, tmp_path) -> None:
    root = tmp_path / "runs"
    official, other = wb.spec004_run(root, "E-02"), wb.spec004_run(root, "E-02")
    patched = copy.deepcopy(catalog)
    for entry in patched["scenarios"]:
        if entry["id"] == "E-02":
            entry["official_status"]["records"] = [{"role": "final", "run_id": official.run_id, "result": "PASS"}]
    reader = _reader(patched, root, tmp_path)
    assert (reader.run(official.run_id)["run"]["record_origin"], reader.run(official.run_id)["run"]["record_role"]) == (
        "ACTUAL", "OFFICIAL",
    )
    assert reader.run(other.run_id)["run"]["record_role"] == "WEB_VALIDATION"
    demo = _reader(patched, root, tmp_path, origin="DEMO").run(official.run_id)
    assert (demo["run"]["record_origin"], demo["run"]["record_role"], demo["demo"]) == ("DEMO", "OTHER", True)


def test_assertion_evidence_refs_and_missing_ids_come_from_the_index(catalog, tmp_path) -> None:
    root = tmp_path / "runs"
    built = wb.spec004_run(root, "E-01")
    view = _reader(catalog, root, tmp_path).run(built.run_id)
    index = load_bundle_summary(built.bundle)["evidence_index"]
    for item in view["assertions"]:
        assert item["evidence_refs"] == index["by_assertion"][item["assertion_id"]]["refs"]
        assert item["missing_evidence_ids"] == index["by_assertion"][item["assertion_id"]]["missing_requirement_ids"]
        assert item["description"] and isinstance(item["required_evidence_ids"], list)


def test_unknown_or_malformed_run_id_is_not_found(catalog, tmp_path) -> None:
    reader = _reader(catalog, tmp_path / "runs", tmp_path)
    for run_id in (str(uuid.uuid4()), "../etc", "not-a-uuid"):
        with pytest.raises(readmodel.RunNotFound):
            reader.run(run_id)
