from __future__ import annotations

import json
from types import SimpleNamespace

from engine import cli
from engine.runner import RunOrchestrator
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters


def test_retest_cli_outputs_parent_link_without_demanding_defect_variant(
    tmp_path,
    monkeypatch,
    capsys,
):
    scenario = load("scenarios/H-03.yaml")
    parent_adapters, _ = make_adapters()
    parent_runner = RunOrchestrator(scenario, parent_adapters, tmp_path, clock=FakeClock())
    parent, _, parent_bundle = parent_runner.execute(parent_runner.preflight("whyyou-local"))
    child_adapters, _ = make_adapters()
    child_runner = RunOrchestrator(scenario, child_adapters, tmp_path, clock=FakeClock())
    monkeypatch.setattr(cli, "_settings", lambda _args: SimpleNamespace(run_root=tmp_path))
    monkeypatch.setattr(cli, "create_runtime", lambda _settings, _path: child_runner)

    exit_code = cli.main(["retest", str(parent_bundle), "--target", "whyyou-local", "--json"])
    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["schema_version"] == "controlproof.cli.v1"
    assert output["projection_schema_version"] == "controlproof.review.v1"
    assert output["command"] == "retest"
    assert output["parent_run_id"] == str(parent.run_id)
    assert output["run_id"] != str(parent.run_id)
    diff = json.loads(
        (tmp_path / output["run_id"] / "retest-diff.json").read_text(encoding="utf-8")
    )
    assert diff["target"]["changed_fields"] == []
