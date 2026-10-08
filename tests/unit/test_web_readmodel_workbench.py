"""T023 — workbench read model (FR-001~007, FR-030, SC-001, SC-011, R-005, R-006). RED until T029.

The view copies statuses from the catalog and sealed bundles; it never computes a verdict.
"""

from __future__ import annotations

import copy
import json
import os

import pytest

from engine.web import readmodel
from engine.web.preflight import ReadinessStore
from tests.fixtures import web_bundles as wb

NON_PASS = {"NOT_RUN", "INCONCLUSIVE"}


@pytest.fixture(scope="module")
def catalog():
    return readmodel.load_catalog()


def _rows(view):
    return {row["id"]: row for group in view["groups"] for row in group["scenarios"]}


def _reader(catalog, root, tmp_path, **kwargs):
    return readmodel.WorkbenchReader(
        catalog, root, readiness=ReadinessStore(tmp_path / "preflight"), **kwargs
    )


def _with_official(catalog, scenario_id, records):
    patched = copy.deepcopy(catalog)
    for entry in patched["scenarios"]:
        if entry["id"] == scenario_id:
            entry["official_status"]["records"] = records
    return patched


def _readiness(store, scenario_id, profile, value, checked_at):
    store.write(
        {
            "scenario_id": scenario_id,
            "execution_profile": profile,
            "result_kind": "READINESS",
            "readiness": value,
            "error_kind": None,
            "checked_at": checked_at,
            "exit_code": 0 if value == "READY" else 2,
            "stored_payload": {"readiness": value, "target_version": "target-snapshot:sha256:" + "a" * 64},
        }
    )


def test_header_counts_and_groups_copy_the_catalog(catalog, tmp_path) -> None:
    view = _reader(catalog, tmp_path / "runs", tmp_path).workbench()
    assert view["schema_version"] == "controlproof.web.v1" and view["view"] == "workbench"
    assert (view["environment_kind"], view["aws_deployment_status"]) == ("LOCAL_EMULATED", "NOT_RUN")
    assert (view["data_origin"], view["demo"]) == ("ACTUAL", False)
    counts = view["counts"]
    assert (counts["PASS"], counts["FAIL"], counts["NOT_RUN"]) == (4, 0, 4)
    assert counts["INCONCLUSIVE"]["by_reason"] == {
        "INSUFFICIENT_EVIDENCE": 1, "NO_TEST_TARGET": 3, "ACCESS_LIMITED": 0, "EVIDENCE_CONFLICT": 0,
    }
    assert counts["INCONCLUSIVE"]["total"] == sum(counts["INCONCLUSIVE"]["by_reason"].values()) == 4
    assert [group["control"] for group in view["groups"]] == ["N", "H", "E", "A"]
    rows = _rows(view)
    assert len(rows) == 12
    for entry in catalog["scenarios"]:
        assert rows[entry["id"]]["official"]["result"] == entry["official_status"]["result"]


def test_no_pass_badge_on_not_run_no_target_or_inconclusive_rows(catalog, tmp_path) -> None:
    for row in _rows(_reader(catalog, tmp_path / "runs", tmp_path).workbench()).values():
        if row["official"]["result"] in NON_PASS:
            assert row["official"]["badge"] != "pass", row["id"]
        if row["mvp_treatment"] == "NO_TEST_TARGET":
            assert (row["official"]["badge"], row["readiness"]["badge"]) == (
                "reason_no_test_target", "readiness_no_test_target",
            )
        if row["mvp_treatment"] == "NOT_RUN":
            assert row["official"]["badge"] == "not_run"
            assert row["readiness"]["badge"] == "runner_not_ready"


def test_readiness_common_time_and_differing_rows(catalog, tmp_path) -> None:
    store = ReadinessStore(tmp_path / "preflight")
    for entry in catalog["scenarios"]:
        for profile in entry["profiles"]:
            checked = "2026-10-08T09:05:00+00:00" if entry["id"] == "N-02" else "2026-10-08T10:12:00+00:00"
            _readiness(store, entry["id"], profile["execution_profile"], "READY", checked)
    view = _reader(catalog, tmp_path / "runs", tmp_path).workbench()
    assert view["readiness_checked_at"] == "2026-10-08T10:12:00+00:00"
    rows = _rows(view)
    flagged = sorted(scenario_id for scenario_id, row in rows.items() if row["readiness"].get("differs_from_common"))
    assert flagged == ["N-02"]
    assert rows["E-01"]["readiness"]["value"] == "READY"
    assert view["target"]["target_version"].startswith("target-snapshot:sha256:")


def test_usage_error_is_a_tool_error_not_readiness(catalog, tmp_path) -> None:
    store = ReadinessStore(tmp_path / "preflight")
    store.write(
        {
            "scenario_id": "E-02", "execution_profile": "E02_SCORING_FREEZE_V1", "result_kind": "ERROR",
            "readiness": None, "error_kind": "USAGE", "checked_at": "2026-10-08T10:00:00+00:00",
            "exit_code": 2, "stored_payload": {},
        }
    )
    row = _rows(_reader(catalog, tmp_path / "runs", tmp_path).workbench())["E-02"]
    assert row["readiness"]["value"] is None
    assert row["readiness"]["badge"] == "tool_error"


def test_missing_official_bundle_shows_no_record_never_not_run(catalog, tmp_path) -> None:
    row = _rows(_reader(catalog, tmp_path / "runs", tmp_path).workbench())["E-02"]
    assert row["official"]["result"] == "PASS"
    assert row["records_on_this_pc"]["official_present"] is False
    assert row["records_on_this_pc"]["note"] == "이 화면에 기록 없음"
    assert row["records_on_this_pc"]["validation_ref"].startswith("specs/004-")


def test_mismatch_when_official_bundle_verdict_differs(catalog, tmp_path) -> None:
    root = tmp_path / "runs"
    built = wb.spec004_run(root, "E-02")
    failing = wb.spec004_run(root, "E-01")
    patched = _with_official(
        catalog, "E-02", [{"role": "final", "run_id": built.run_id, "result": "PASS"}]
    )
    patched = _with_official(patched, "E-01", [{"role": "final", "run_id": failing.run_id, "result": "PASS"}])
    rows = _rows(_reader(patched, root, tmp_path).workbench())
    assert rows["E-02"]["records_on_this_pc"]["official_present"] is True
    assert rows["E-02"]["mismatch"] is None
    assert rows["E-01"]["mismatch"] == {
        "run_id": failing.run_id, "bundle_verdict": failing.verdict, "catalog_result": "PASS",
    }
    assert rows["E-01"]["official"]["result"] == "PASS"  # the catalog value is shown, never replaced


def test_web_validation_runs_are_counted_separately(catalog, tmp_path) -> None:
    root = tmp_path / "runs"
    wb.spec004_run(root, "E-02")
    row = _rows(_reader(catalog, root, tmp_path).workbench())["E-02"]
    assert row["records_on_this_pc"]["web_validation_runs"] == 1
    assert row["records_on_this_pc"]["official_present"] is False


def test_demo_and_actual_never_share_a_view(catalog, tmp_path) -> None:
    actual_root, demo_root = tmp_path / "runs", tmp_path / "demo"
    wb.spec004_run(actual_root, "E-02")
    wb.spec004_run(demo_root, "E-02")
    wb.spec004_run(demo_root, "E-02")
    demo = _reader(catalog, demo_root, tmp_path, origin="DEMO").workbench()
    actual = _reader(catalog, actual_root, tmp_path).workbench()
    assert (demo["data_origin"], demo["demo"]) == ("DEMO", True)
    assert _rows(demo)["E-02"]["records_on_this_pc"]["web_validation_runs"] == 2
    assert _rows(actual)["E-02"]["records_on_this_pc"]["web_validation_runs"] == 1
    assert demo["counts"] == actual["counts"]


def test_preserved_first_failures_and_retest_needed(catalog, tmp_path) -> None:
    view = _reader(catalog, tmp_path / "runs", tmp_path).workbench()
    assert view["retest_needed"] == []
    lineages = {(item["scenario_id"], item["parent_run_id"]) for item in view["preserved_first_failures"]}
    assert ("E-01", "09c9d9bb-82a3-4485-9c9d-e9721f2452e4") in lineages
    for item in view["preserved_first_failures"]:
        assert item["parent_result"] == "FAIL" and item["child_run_id"]


def test_changed_file_after_cached_verify_is_reverified_as_integrity_failure(catalog, tmp_path) -> None:
    root = tmp_path / "runs"
    built = wb.spec004_run(root, "E-02")
    patched = _with_official(catalog, "E-02", [{"role": "final", "run_id": built.run_id, "result": "PASS"}])
    cache = readmodel.VerifyCache()
    reader = _reader(patched, root, tmp_path, cache=cache)
    first = _rows(reader.workbench())["E-02"]["records_on_this_pc"]["official"][0]
    assert first["integrity"] == "VERIFIED"
    misses = cache.misses
    _rows(reader.workbench())
    assert cache.misses == misses  # unchanged files: served from cache
    target = built.bundle / "judgement.json"
    payload = json.loads(target.read_text(encoding="utf-8"))
    payload["summary"] = "changed after seal"
    stat = target.stat()
    target.write_text(json.dumps(payload), encoding="utf-8")
    os.utime(target, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
    after = _rows(reader.workbench())["E-02"]
    assert after["records_on_this_pc"]["official"][0]["integrity"] == "INVALID"
    assert after["mismatch"] is None
