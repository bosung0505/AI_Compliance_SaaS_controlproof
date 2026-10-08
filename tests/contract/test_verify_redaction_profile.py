"""T008 — verify judges with the scanner recorded at seal time (FR-036, R-012). RED until T017; sealing v2 is T020.

No `redaction_profile` in the manifest means v1. v2 findings on a v1 bundle are reported only in the non-blocking
`strict_scan_findings` (path, rule, count; never values) and never change `bundle_status`.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from engine.evidence import canonical_json_bytes, sha256_bytes, verify_bundle
from tests.fixtures import web_bundles as wb

PARENT = Path(".controlproof/runs/15cef078-ee24-4f0e-91ef-381e0f7a1cc2")
LEAK = json.dumps({"p": "C:\\Users\\alice\\runs\\abc"}).encode()


def _reseal(directory: Path, *, extra: bytes | None = None, profile: str | None = None) -> None:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    manifest.pop("bundle_digest")
    if extra is not None:
        (directory / "notes.json").write_bytes(extra)
        manifest["files"].append(
            {"path": "notes.json", "mime_type": "application/json", "size_bytes": len(extra),
             "sha256": sha256_bytes(extra)}
        )
        manifest["files"].sort(key=lambda record: record["path"])
    if profile is not None:
        manifest["redaction_profile"] = profile
    manifest["bundle_digest"] = sha256_bytes(canonical_json_bytes(manifest))
    (directory / "manifest.json").write_bytes(canonical_json_bytes(manifest))


def _copy(tmp_path, built) -> Path:
    target = tmp_path / "copy" / built.run_id
    shutil.copytree(built.bundle, target)
    return target


def test_unmarked_bundle_verifies_with_v1(tmp_path) -> None:
    built = wb.h03_case(tmp_path / "runs", "pass")
    result = verify_bundle(built.bundle)
    assert result["bundle_status"] == "VERIFIED"
    assert result["redaction_profile"] == "controlproof.redaction.v1"
    assert result["strict_scan_findings"] == []


def test_v2_findings_on_v1_bundle_are_non_blocking(tmp_path) -> None:
    copy = _copy(tmp_path, wb.h03_case(tmp_path / "runs", "pass"))
    _reseal(copy, extra=LEAK)
    result = verify_bundle(copy)
    assert result["bundle_status"] == "VERIFIED"
    assert result["strict_scan_findings"] == [{"path": "notes.json", "rule": "user_path", "count": 1}]
    assert "alice" not in json.dumps(result)


def test_v2_marked_bundle_is_judged_with_v2(tmp_path) -> None:
    built = wb.h03_case(tmp_path / "runs", "pass")
    clean = _copy(tmp_path, built)
    _reseal(clean, profile="controlproof.redaction.v2")
    result = verify_bundle(clean)
    assert (result["bundle_status"], result["redaction_profile"]) == ("VERIFIED", "controlproof.redaction.v2")
    leaky = tmp_path / "leaky" / built.run_id
    shutil.copytree(built.bundle, leaky)
    _reseal(leaky, extra=LEAK, profile="controlproof.redaction.v2")
    result = verify_bundle(leaky)
    assert result["bundle_status"] == "INVALID"
    assert "notes.json:redaction" in result["mismatched_files"]
    assert "alice" not in json.dumps(result)


def test_unknown_redaction_profile_is_invalid(tmp_path) -> None:
    copy = _copy(tmp_path, wb.h03_case(tmp_path / "runs", "pass"))
    _reseal(copy, profile="controlproof.redaction.v9")
    result = verify_bundle(copy)
    assert result["bundle_status"] == "INVALID"
    assert "manifest.json:redaction_profile" in result["mismatched_files"]


def test_tracked_parent_stays_verified() -> None:
    result = verify_bundle(PARENT)
    assert result["bundle_status"] == "VERIFIED"
    assert result["redaction_profile"] == "controlproof.redaction.v1"


@pytest.mark.xfail(strict=True, reason="RED until T020 (sealing switches to v2)")
def test_new_seals_write_v2(tmp_path) -> None:
    built = wb.h03_case(tmp_path / "runs", "pass")
    manifest = json.loads((built.bundle / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["redaction_profile"] == "controlproof.redaction.v2"
