from __future__ import annotations

import json
import shutil

import pytest

from engine.evidence import verify_bundle
from engine.models import canonical_json_bytes, sha256_bytes
from engine.runner import RunOrchestrator
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters


@pytest.fixture
def bundle(tmp_path):
    adapters, _ = make_adapters()
    runner = RunOrchestrator(load("scenarios/H-03.yaml"), adapters, tmp_path, clock=FakeClock())
    return runner.execute(runner.preflight("whyyou-local"))[2]


def test_verify_is_read_only_and_detects_changed_file(bundle):
    manifest_before = (bundle / "manifest.json").read_bytes()
    artifact = next((bundle / "artifacts").glob("*.json"))
    artifact.write_text("{}", encoding="utf-8")
    result = verify_bundle(bundle)
    assert result["bundle_status"] == "INVALID"
    assert (bundle / "manifest.json").read_bytes() == manifest_before


def test_missing_and_unregistered_files_are_invalid(bundle):
    victim = next((bundle / "artifacts").glob("*.json"))
    victim.unlink()
    (bundle / "extra.txt").write_text("unregistered", encoding="utf-8")
    result = verify_bundle(bundle)
    assert result["bundle_status"] == "INVALID"
    assert result["missing_files"]
    assert "extra.txt" in result["unregistered_files"]


def test_path_traversal_record_is_invalid_without_reading_outside(bundle, tmp_path):
    copy = tmp_path / "copy"
    shutil.copytree(bundle, copy)
    manifest = json.loads((copy / "manifest.json").read_text(encoding="utf-8"))
    manifest["files"][0]["path"] = "../outside.json"
    (copy / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    result = verify_bundle(copy)
    assert result["bundle_status"] == "INVALID"
    assert any(":path" in item or "bundle_digest" in item for item in result["mismatched_files"])


def test_malformed_artifact_envelope_is_invalid_even_with_updated_file_hash(bundle):
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    record = next(item for item in manifest["files"] if item.get("artifact_id"))
    path = bundle / record["path"]
    path.write_text(json.dumps({"artifact_id": record["artifact_id"]}), encoding="utf-8")
    payload = path.read_bytes()
    record["size_bytes"] = len(payload)
    record["sha256"] = sha256_bytes(payload)
    unsigned = {key: value for key, value in manifest.items() if key != "bundle_digest"}
    manifest["bundle_digest"] = sha256_bytes(canonical_json_bytes(unsigned))
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    result = verify_bundle(bundle)
    assert result["bundle_status"] == "INVALID"
    assert f"{record['path']}:envelope" in result["mismatched_files"]
