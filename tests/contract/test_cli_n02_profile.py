from __future__ import annotations

import argparse

import pytest

from engine import cli
from engine.models import ExecutionProfile, RunState, Verdict
from engine.runner import build_profile_runner
from engine.scenario import ScenarioDefinition
from tests.contract.test_scenario_profile_v3 import _payload
from tests.fixtures.fake_adapters import FakeClock, make_adapters


def test_n02_requires_explicit_profile() -> None:
    with pytest.raises(cli.CliContractError) as exc:
        cli._scenario_selection(
            argparse.Namespace(scenario_id="N-02", profile=None, scenario_file=None)
        )
    assert exc.value.code == "PROFILE_REQUIRED"


def test_n02_profile_selects_v3_scenario_without_semantic_override() -> None:
    path, profile = cli._scenario_selection(
        argparse.Namespace(
            scenario_id="N-02",
            profile="N02_CONSENT_ORDER_V1",
            scenario_file=None,
        )
    )
    assert profile is ExecutionProfile.N02_CONSENT_ORDER_V1
    assert path.name == "N-02.yaml"
    assert cli._run_exit(RunState.COMPLETED, Verdict.PASS) == 0
    assert cli._run_exit(RunState.COMPLETED, Verdict.FAIL) == 3
    assert cli._run_exit(RunState.COMPLETED, Verdict.INCONCLUSIVE) == 4


def test_non_ready_preflight_has_no_run_subject_marker_or_event_side_effect(tmp_path) -> None:
    scenario = ScenarioDefinition.model_validate(_payload())
    adapters, _ = make_adapters(target_exists=False)
    run_root = tmp_path / "runs"
    before = {path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*")}
    runner = build_profile_runner(scenario, adapters, run_root, clock=FakeClock())
    readiness = runner.preflight("whyyou-local")
    assert readiness.status.value == "NO_TEST_TARGET"
    after = {path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*")}
    assert after == before
