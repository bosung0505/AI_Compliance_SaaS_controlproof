from __future__ import annotations

import json
from types import SimpleNamespace

from engine import cli
from engine.cli import main
from engine.runner import RunOrchestrator
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters


def _bundle(tmp_path):
    adapters, _ = make_adapters()
    runner = RunOrchestrator(load("scenarios/H-03.yaml"), adapters, tmp_path, clock=FakeClock())
    return runner.execute(runner.preflight("whyyou-local"))[2]


def test_show_contract_exposes_six_linked_assertions(tmp_path, capsys):
    bundle = _bundle(tmp_path)
    assert main(["show", str(bundle), "--json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["schema_version"] == "controlproof.cli.v1"
    assert output["projection_schema_version"] == "controlproof.review.v1"
    assert output["command"] == "show"
    assert output["implementation_status"] == "IMPLEMENTED"
    assert output["target_version"].startswith("target-snapshot:sha256:")
    assert len(output["assertions"]) == 6
    assert all(item["source_requirements"] for item in output["assertions"])
    assert all(item["evidence"] for item in output["assertions"])
    assert output["environment_restore_status"] == "SUCCEEDED"
    assert output["unverified_scope"]


def test_verify_contract_returns_exit_five_on_tamper(tmp_path, capsys):
    bundle = _bundle(tmp_path)
    next((bundle / "artifacts").glob("*.json")).write_text("tampered", encoding="utf-8")
    assert main(["verify", str(bundle), "--json"]) == 5
    output = json.loads(capsys.readouterr().out)
    assert output["schema_version"] == "controlproof.cli.v1"
    assert output["command"] == "verify"
    assert output["bundle_status"] == "INVALID"


def test_run_contract_keeps_cli_envelope_over_review_projection(tmp_path, monkeypatch, capsys):
    adapters, _ = make_adapters()
    runner = RunOrchestrator(load("scenarios/H-03.yaml"), adapters, tmp_path, clock=FakeClock())
    monkeypatch.setattr(cli, "_settings", lambda _args: SimpleNamespace(run_root=tmp_path))
    monkeypatch.setattr(cli, "create_runtime", lambda _settings, _path: runner)

    assert main(["run", "H-03", "--target", "whyyou-local", "--json"]) == 0
    output = json.loads(capsys.readouterr().out)

    assert output["schema_version"] == "controlproof.cli.v1"
    assert output["projection_schema_version"] == "controlproof.review.v1"
    assert output["command"] == "run"
