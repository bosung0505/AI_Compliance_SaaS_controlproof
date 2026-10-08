"""T007 — `evidence_index` in the review projection (FR-014, FR-015, SC-003, R-011). RED until T015.

Reference forms in sealed manifests: Spec 001 bare artifact IDs, Spec 002 `artifact:`/`file:`/`intrinsic:` plus cross-run
objects, Spec 004 `file:`/`intrinsic:`. Every resolved entry carries a `<run_root>/…` path, SHA-256, size and MIME.
"""

from __future__ import annotations

import hashlib
import json
import shutil

import yaml

from engine.presentation import load_bundle_summary
from tests.fixtures import web_bundles as wb

ENTRY_KEYS = {"ref", "relative_path", "sha256", "size_bytes", "mime_type", "evidence_requirement_ids"}


def _manifest(bundle):
    return json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))


def _snapshot_requirements(bundle):
    snapshot = yaml.safe_load((bundle / "scenario.snapshot.yaml").read_text(encoding="utf-8"))
    definition = snapshot.get("definition", snapshot)
    return {item["assertion_id"]: list(item.get("required_evidence_ids", [])) for item in definition["assertions"]}


def _check_shape(index, built, tmp_path):
    assert set(index) == {"files", "by_requirement", "by_assertion", "unresolved_refs"}
    for entry in index["files"]:
        assert ENTRY_KEYS <= set(entry)
        assert entry["relative_path"].startswith("<run_root>/")
        assert len(entry["sha256"]) == 64
    assert str(tmp_path) not in json.dumps(index)
    refs = {entry["ref"] for entry in index["files"]}
    for linked in index["by_requirement"].values():
        assert set(linked) <= refs


def test_spec001_bare_artifact_ids_resolve(tmp_path) -> None:
    built = wb.h03_case(tmp_path / "runs", "pass")
    index = load_bundle_summary(built.bundle)["evidence_index"]
    _check_shape(index, built, tmp_path)
    assert index["unresolved_refs"] == []
    manifest = _manifest(built.bundle)
    records = {record["artifact_id"]: record for record in manifest["files"] if record.get("artifact_id")}
    entries = {entry["ref"]: entry for entry in index["files"]}
    for evidence_id, references in manifest["required_evidence"].items():
        assert index["by_requirement"][evidence_id] == [f"artifact:{ref}" for ref in references]
        for ref in references:
            entry = entries[f"artifact:{ref}"]
            assert entry["relative_path"] == f"<run_root>/{built.run_id}/{records[ref]['path']}"
            assert entry["sha256"] == records[ref]["sha256"]
            assert evidence_id in entry["evidence_requirement_ids"]


def test_by_assertion_is_artifact_ids_union_snapshot_requirements(tmp_path) -> None:
    built = wb.h03_case(tmp_path / "runs", "pass")
    summary = load_bundle_summary(built.bundle)
    index = summary["evidence_index"]
    requirements = _snapshot_requirements(built.bundle)
    for assertion in summary["assertions"]:
        expected = {f"artifact:{item['artifact_id']}" for item in assertion["evidence"]}
        for evidence_id in requirements[assertion["assertion_id"]]:
            expected |= set(index["by_requirement"][evidence_id])
        got = index["by_assertion"][assertion["assertion_id"]]
        assert set(got["refs"]) == expected
        assert got["missing_requirement_ids"] == []


def test_spec002_file_intrinsic_and_cross_run_refs_resolve(tmp_path) -> None:
    root = tmp_path / "runs"
    parent, child = wb.e03_lineage(root)
    index = load_bundle_summary(child.bundle)["evidence_index"]
    _check_shape(index, child, tmp_path)
    assert index["unresolved_refs"] == []
    entries = {entry["ref"]: entry for entry in index["files"]}
    kinds = {ref.split(":", 1)[0] for ref in entries}
    assert {"artifact", "file", "intrinsic", "run"} <= kinds
    intrinsic = entries["intrinsic:sealed-manifest"]
    assert intrinsic["relative_path"] == f"<run_root>/{child.run_id}/manifest.json"
    assert intrinsic["sha256"] == hashlib.sha256((child.bundle / "manifest.json").read_bytes()).hexdigest()
    cross = [entry for ref, entry in entries.items() if ref.startswith("run:")]
    assert len(cross) == 1
    assert cross[0]["ref"].startswith(f"run:{parent.run_id}/artifact:")
    assert cross[0]["relative_path"].startswith(f"<run_root>/{parent.run_id}/")


def test_spec004_file_refs_resolve(tmp_path) -> None:
    _, child, _ = wb.e01_lineage(tmp_path / "runs")
    index = load_bundle_summary(child.bundle)["evidence_index"]
    _check_shape(index, child, tmp_path)
    assert index["unresolved_refs"] == []
    assert "file:report-reads.jsonl" in index["by_requirement"]["EV4-05"]
    for assertion_id, item in index["by_assertion"].items():
        assert item["missing_requirement_ids"] == [], assertion_id


def test_unresolved_references_are_listed_and_marked_missing(tmp_path) -> None:
    built = wb.spec004_run(tmp_path / "runs", "E-01")
    copy = tmp_path / "copy" / built.run_id
    shutil.copytree(built.bundle, copy)
    manifest = _manifest(copy)
    manifest["required_evidence"]["EV4-05"] = ["file:gone.jsonl"]
    manifest["required_evidence"]["EV4-09"] = [
        {"origin_run_id": "00000000-0000-4000-8000-000000000001", "artifact_id": "x", "artifact_digest": "0" * 64,
         "bundle_digest": "0" * 64}
    ]
    (copy / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    index = load_bundle_summary(copy)["evidence_index"]
    unresolved = {(item["requirement_id"], item["ref"]) for item in index["unresolved_refs"]}
    assert ("EV4-05", "file:gone.jsonl") in unresolved
    assert any(requirement == "EV4-09" and ref.startswith("run:") for requirement, ref in unresolved)
    assert index["by_requirement"]["EV4-05"] == []
    assert "EV4-05" in index["by_assertion"]["E01-A3"]["missing_requirement_ids"]
    assert "EV4-09" in index["by_assertion"]["E01-A3"]["missing_requirement_ids"]


def test_evidence_links_are_unchanged(tmp_path) -> None:
    for built in (wb.h03_case(tmp_path / "a", "fail"), wb.e03_lineage(tmp_path / "b")[1]):
        manifest = _manifest(built.bundle)
        by_artifact = {
            record["artifact_id"]: {
                "artifact_id": record["artifact_id"],
                "path": record["path"],
                "sha256": record["sha256"],
                "mime_type": record["mime_type"],
            }
            for record in manifest["files"]
            if record.get("artifact_id")
        }
        expected = {
            evidence_id: [
                by_artifact[ref.removeprefix("artifact:")]
                for ref in references
                if isinstance(ref, str) and ref.removeprefix("artifact:") in by_artifact
            ]
            for evidence_id, references in manifest["required_evidence"].items()
        }
        assert load_bundle_summary(built.bundle)["evidence_links"] == expected
