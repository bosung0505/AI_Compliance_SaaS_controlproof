from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from engine import cli
from engine.models import ImplementationStatus, ReadinessStatus, ScenarioReadiness
from engine.scenario import load


@pytest.mark.parametrize(
    "status",
    [
        ReadinessStatus.RUNNER_NOT_READY,
        ReadinessStatus.ACCESS_BLOCKED,
        ReadinessStatus.NO_TEST_TARGET,
    ],
)
def test_non_ready_preflight_exits_two_and_creates_no_run(
    tmp_path,
    monkeypatch,
    capsys,
    status,
):
    run_root = tmp_path / "runs"
    scenario = load("scenarios/H-03.yaml")
    readiness = ScenarioReadiness(
        scenario_id=scenario.scenario_id,
        scenario_version=scenario.version,
        target_id="whyyou-local",
        implementation_status=ImplementationStatus.IMPLEMENTED,
        status=status,
        checks=(),
        operator_action="repair fixture",
    )
    runtime = SimpleNamespace(
        scenario=scenario,
        preflight=lambda _target: readiness,
    )
    monkeypatch.setattr(cli, "_settings", lambda _args: SimpleNamespace(run_root=run_root))
    monkeypatch.setattr(cli, "create_runtime", lambda _settings, _path: runtime)
    exit_code = cli.main(
        ["preflight", "H-03", "--target", "whyyou-local", "--run-root", str(run_root), "--json"]
    )
    output = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert output["readiness"] == status.value
    assert not list(run_root.iterdir())
