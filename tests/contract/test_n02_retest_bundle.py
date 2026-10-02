"""A child N-02 bundle links verified parent bytes without rewriting them."""

from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import uuid4

from engine import cli
from engine.evidence import verify_bundle
from engine.models import sha256_bytes
from tests.integration.test_n02_retest_lineage import _prepare, _runner


def _bytes_by_path(bundle):
    return {
        path.relative_to(bundle).as_posix(): sha256_bytes(path.read_bytes())
        for path in bundle.rglob("*") if path.is_file()
    }


def test_n02_child_links_parent_origin_and_preserves_parent_files(tmp_path):
    parent_runner = _runner(tmp_path)
    parent, _, parent_bundle = parent_runner.execute(parent_runner.preflight("whyyou-local"))
    original = _bytes_by_path(parent_bundle)
    child_runner = _runner(tmp_path)
    child_id = uuid4()
    inherited, _, records = _prepare(parent_bundle, child_runner, child_id)
    child, _, child_bundle = child_runner.execute(
        child_runner.preflight("whyyou-local"),
        parent_run_id=inherited.run_id,
        retest_records=records,
        run_id=child_id,
    )

    assert child.parent_run_id == parent.run_id
    assert _bytes_by_path(parent_bundle) == original
    assert verify_bundle(parent_bundle)["bundle_status"] == "VERIFIED"
    assert verify_bundle(child_bundle)["bundle_status"] == "VERIFIED"
    manifest = json.loads((child_bundle / "manifest.json").read_text(encoding="utf-8"))
    assert "file:retest-link.json" in manifest["required_evidence"]["EV3-10"]
    assert "file:retest-diff.json" in manifest["required_evidence"]["EV3-10"]
    link = json.loads((child_bundle / "retest-link.json").read_text(encoding="utf-8"))
    parent_manifest = json.loads((parent_bundle / "manifest.json").read_text(encoding="utf-8"))
    assert link["parent_run_id"] == str(parent.run_id)
    assert link["parent_bundle_digest"] == parent_manifest["bundle_digest"]
    assert (child_bundle / "retest-link.json").is_file()
    assert (child_bundle / "retest-diff.json").is_file()

    (parent_bundle / "judgement.json").write_bytes(b"{}")
    assert verify_bundle(child_bundle)["bundle_status"] == "INVALID"


def test_n02_cli_retest_dispatches_to_new_child_bundle(tmp_path, monkeypatch, capsys):
    parent_runner = _runner(tmp_path)
    parent, _, parent_bundle = parent_runner.execute(parent_runner.preflight("whyyou-local"))
    child_runner = _runner(tmp_path)
    monkeypatch.setattr(cli, "_settings", lambda _args: SimpleNamespace(run_root=tmp_path))
    monkeypatch.setattr(cli, "create_runtime", lambda _settings, _path: child_runner)

    code = cli.main(["retest", str(parent_bundle), "--target", "whyyou-local", "--json"])
    output = json.loads(capsys.readouterr().out)

    assert code == 0
    assert output["command"] == "retest"
    assert output["parent_run_id"] == str(parent.run_id)
    assert output["run_id"] != str(parent.run_id)
    assert verify_bundle(tmp_path / output["run_id"])["bundle_status"] == "VERIFIED"
