"""Shared records must preserve original bytes and reject unsafe or incomplete exports."""

import json
import shutil

import pytest
import yaml

from engine.evidence import canonical_json_bytes, sha256_bytes
from engine.shared_records import (
    SnapshotError,
    build_snapshot,
    file_hashes,
    load_snapshot,
    safe_path,
)
from tests.fixtures import web_bundles as wb


@pytest.fixture
def source(tmp_path):
    built = wb.spec004_run(tmp_path / "actual", "E-02")
    repo = tmp_path / "repo"
    (repo / "catalog").mkdir(parents=True)
    catalog = {
        "scenarios": [
            {
                "official_status": {
                    "records": [
                        {
                            "run_id": built.run_id,
                            "role": "final",
                            "manifest_sha256": sha256_bytes(
                                (built.bundle / "manifest.json").read_bytes()
                            ),
                        },
                        {"run_id": "00000000-0000-4000-8000-000000000001", "role": "previous"},
                    ]
                }
            }
        ]
    }
    (repo / "catalog/mvp-scenarios.yaml").write_text(yaml.safe_dump(catalog), encoding="utf-8")
    return repo, built.bundle, tmp_path / "shared"


def test_snapshot_preserves_all_bytes_and_declares_missing(source):
    repo, bundle, out = source
    before = file_hashes(bundle)
    snapshot = build_snapshot([bundle, bundle], out, repo=repo)
    assert len(snapshot["records"]) == 1
    assert len(snapshot["missing_records"]) == 1
    assert load_snapshot(out / "snapshot.json", repo=repo) == snapshot
    assert file_hashes(out / "bundles" / bundle.name) == before == file_hashes(bundle)
    with pytest.raises(SnapshotError, match="must not exist"):
        build_snapshot([bundle], out, repo=repo)


@pytest.mark.parametrize("change", ["tamper", "missing", "extra", "code"])
def test_shared_export_rejects_changed_missing_extra_files_and_code(source, change):
    repo, bundle, out = source
    build_snapshot([bundle], out, repo=repo)
    run = out / "bundles" / bundle.name / "run.json"
    if change == "tamper":
        run.write_bytes(run.read_bytes() + b" ")
    elif change == "missing":
        run.unlink()
    elif change == "extra":
        (run.parent / "extra.json").write_text("{}")
    else:
        (repo / "catalog/mvp-scenarios.yaml").write_text("scenarios: []")
    with pytest.raises(SnapshotError):
        load_snapshot(out / "snapshot.json", repo=repo)


def test_conflicting_duplicate_is_rejected(source, tmp_path):
    repo, bundle, out = source
    other = tmp_path / "other" / bundle.name
    shutil.copytree(bundle, other)
    (other / "run.json").write_bytes((other / "run.json").read_bytes() + b" ")
    with pytest.raises(SnapshotError):
        build_snapshot([bundle, other], out, repo=repo, expected_invalid={bundle.name})
    assert not out.exists()


def test_secret_is_not_exported_even_if_invalid_is_explicitly_preserved(source):
    repo, bundle, out = source
    (bundle / "extra.json").write_text(
        '{"Authorization":"Bearer secret-value-12345678901234567890"}'
    )
    with pytest.raises(SnapshotError, match="scan failed"):
        build_snapshot([bundle], out, repo=repo, expected_invalid={bundle.name})
    assert not out.exists()


@pytest.mark.parametrize(
    "relative", ["../outside", "/outside", "C:/outside", "a\\b", "a//b", "./a"]
)
def test_relative_paths_cannot_escape_or_alias(tmp_path, relative):
    with pytest.raises(SnapshotError):
        safe_path(tmp_path, relative)


def test_resigned_index_cannot_introduce_path_traversal(source):
    repo, bundle, out = source
    snapshot = build_snapshot([bundle], out, repo=repo)
    snapshot["records"][0]["files"]["../secret.json"] = "0" * 64
    snapshot.pop("snapshot_digest")
    snapshot["snapshot_digest"] = sha256_bytes(canonical_json_bytes(snapshot))
    (out / "snapshot.json").write_text(json.dumps(snapshot))
    with pytest.raises(SnapshotError):
        load_snapshot(out / "snapshot.json", repo=repo)


def test_source_line_endings_do_not_change_code_identity(source):
    repo, bundle, out = source
    code = repo / "engine/example.py"
    code.parent.mkdir()
    code.write_bytes(b"# code\nvalue = 1\n")
    snapshot = build_snapshot([bundle], out, repo=repo)
    code.write_bytes(b"# code\r\nvalue = 1\r\n")
    assert load_snapshot(out / "snapshot.json", repo=repo) == snapshot


def test_json_review_ledger_is_part_of_the_frozen_display_context(source):
    repo, bundle, out = source
    ledger = repo / "scenarios/h02-reviewed-trees.json"
    ledger.parent.mkdir()
    ledger.write_text("{}")
    snapshot = build_snapshot([bundle], out, repo=repo)
    assert "scenarios/h02-reviewed-trees.json" in snapshot["display_files"]
    ledger.write_text('{"changed":true}')
    with pytest.raises(SnapshotError, match="code/catalog differs"):
        load_snapshot(out / "snapshot.json", repo=repo)
