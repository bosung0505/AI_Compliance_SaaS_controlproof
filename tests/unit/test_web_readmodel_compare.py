"""T053 — compare view ④ (FR-021~023, SC-005). RED until T055.

`parent_unchanged` compares the parent digest recorded by the child with the parent's current `bundle_digest`. Sources:
`RETEST_LINK` (Spec 003·004 retest-link.json), `CROSS_RUN_REFERENCE` (Spec 002 child manifest), `NONE_LEGACY` (Spec 001;
`parent_unchanged: null`, parent integrity shown, not a lineage problem).
"""

from __future__ import annotations

import json

import pytest

from engine.evidence import canonical_json_bytes, sha256_bytes
from engine.web import readmodel
from engine.web.preflight import ReadinessStore
from tests.fixtures import web_bundles as wb


@pytest.fixture(scope="module")
def catalog():
    return readmodel.load_catalog()


def _reader(catalog, root, tmp_path):
    return readmodel.WorkbenchReader(catalog, root, readiness=ReadinessStore(tmp_path / "preflight"))


def _reseal_with_new_digest(bundle):
    """Keep the parent VERIFIED but change its bundle digest (a re-sealed parent)."""
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    manifest.pop("bundle_digest")
    manifest["sealed_at"] = "2030-01-01T00:00:00+00:00"
    manifest["bundle_digest"] = sha256_bytes(canonical_json_bytes(manifest))
    (bundle / "manifest.json").write_bytes(canonical_json_bytes(manifest))


def test_spec004_lineage_from_retest_link(catalog, tmp_path) -> None:
    root = tmp_path / "runs"
    parent, child, _grandchild = wb.e01_lineage(root)
    view = _reader(catalog, root, tmp_path).compare(child.run_id)
    assert (view["schema_version"], view["view"]) == ("controlproof.web.v1", "compare")
    assert (view["parent"]["run_id"], view["child"]["run_id"]) == (parent.run_id, child.run_id)
    assert (view["parent"]["verdict"], view["child"]["verdict"]) == ("FAIL", "PASS")
    assert (view["parent_integrity_source"], view["parent_unchanged"], view["lineage_problem"]) == ("RETEST_LINK", True, None)
    link = json.loads((child.bundle / "retest-link.json").read_text(encoding="utf-8"))
    assert view["changed_dimensions"] == link["changed_dimensions"]
    changes = {item["assertion_id"]: item for item in view["assertion_changes"]}
    assert changes["E01-A3"]["before"] == "FAIL" and changes["E01-A3"]["after"] == "PASS"
    assert changes["E01-A3"]["before_evidence"] and changes["E01-A3"]["after_evidence"]
    assert all(len(item["sha256"]) == 64 for item in changes["E01-A3"]["after_evidence"])
    assert view["remaining_failures"] == []
    assert [item["run_id"] for item in view["lineage"]] == [parent.run_id, child.run_id]
    assert view["retest_command"].startswith("python -m engine.cli retest ")


def test_grandchild_lineage_lists_all_generations(catalog, tmp_path) -> None:
    root = tmp_path / "runs"
    parent, child, grandchild = wb.e01_lineage(root)
    view = _reader(catalog, root, tmp_path).compare(grandchild.run_id)
    assert view["parent"]["run_id"] == child.run_id
    assert [item["run_id"] for item in view["lineage"]] == [parent.run_id, child.run_id, grandchild.run_id]


def test_spec002_lineage_from_cross_run_reference(catalog, tmp_path) -> None:
    root = tmp_path / "runs"
    _parent, child = wb.e03_lineage(root)
    view = _reader(catalog, root, tmp_path).compare(child.run_id)
    assert (view["parent_integrity_source"], view["parent_unchanged"], view["lineage_problem"]) == (
        "CROSS_RUN_REFERENCE", True, None,
    )


def test_spec001_lineage_is_legacy_not_a_problem(catalog, tmp_path) -> None:
    root = tmp_path / "runs"
    _parent, child = wb.h03_lineage(root)
    view = _reader(catalog, root, tmp_path).compare(child.run_id)
    assert (view["parent_integrity_source"], view["parent_unchanged"], view["lineage_problem"]) == ("NONE_LEGACY", None, None)
    assert view["parent"]["integrity"] == "VERIFIED"
    assert view["assertion_changes"]


def test_changed_parent_digest_is_a_lineage_problem(catalog, tmp_path) -> None:
    root = tmp_path / "runs"
    parent, child, _ = wb.e01_lineage(root)
    _reseal_with_new_digest(parent.bundle)
    view = _reader(catalog, root, tmp_path).compare(child.run_id)
    assert view["parent"]["integrity"] == "VERIFIED"
    assert view["parent_unchanged"] is False
    assert view["lineage_problem"]["code"] == "PARENT_DIGEST_CHANGED"
    assert (view["assertion_changes"], view["changed_dimensions"], view["remaining_failures"]) == (None, None, None)


def test_invalid_parent_is_a_lineage_problem(catalog, tmp_path) -> None:
    root = tmp_path / "runs"
    parent, child, _ = wb.e01_lineage(root)
    wb.tampered(parent)
    view = _reader(catalog, root, tmp_path).compare(child.run_id)
    assert view["parent"]["integrity"] == "INVALID" and view["parent"]["verdict"] is None
    assert view["lineage_problem"]["code"] == "PARENT_NOT_VERIFIED"
    assert view["assertion_changes"] is None


def test_remaining_failures(catalog, tmp_path) -> None:
    root = tmp_path / "runs"
    _parent, child = wb.h03_lineage(root)
    view = _reader(catalog, root, tmp_path).compare(child.run_id)
    after = {item["assertion_id"]: item["after"] for item in view["assertion_changes"]}
    assert view["remaining_failures"] == sorted(key for key, value in after.items() if value in {"FAIL", "INCONCLUSIVE"})


def test_not_a_retest_or_unknown_is_not_found(catalog, tmp_path) -> None:
    root = tmp_path / "runs"
    parent, _child, _ = wb.e01_lineage(root)
    reader = _reader(catalog, root, tmp_path)
    for run_id in (parent.run_id, "00000000-0000-4000-8000-000000000000"):
        with pytest.raises(readmodel.RunNotFound):
            reader.compare(run_id)
