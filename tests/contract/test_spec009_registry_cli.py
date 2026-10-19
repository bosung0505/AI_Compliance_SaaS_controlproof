"""T009 — Spec 009 registry, CLI profile/file selection and run/show/verify/retest over a fake runtime."""

from __future__ import annotations

import argparse
import json

import pytest

from engine import cli
from engine.executors.n01 import N01Executor
from engine.executors.n03 import N03Executor
from engine.models import ExecutionProfile
from engine.runner import PROFILE_REGISTRY, build_profile_runner
from engine.scenario import load
from tests.fixtures.fake_spec009 import make_spec009_adapters, ready, spec009_target


def _select(scenario_id: str, profile: str | None):
    return cli._scenario_selection(argparse.Namespace(scenario_id=scenario_id, profile=profile, scenario_file=None))


def test_registry_maps_both_profiles() -> None:
    assert PROFILE_REGISTRY.registrations[ExecutionProfile.N01_NOTICE_V1] is N01Executor
    assert PROFILE_REGISTRY.registrations[ExecutionProfile.N03_STALE_CONSENT_V1] is N03Executor


@pytest.mark.parametrize(
    ("scenario_id", "profile", "filename", "executor_type"),
    [("N-01", "N01_NOTICE_V1", "N-01.yaml", N01Executor), ("N-03", "N03_STALE_CONSENT_V1", "N-03.yaml", N03Executor)],
)
def test_profile_selects_its_yaml_and_executor(tmp_path, scenario_id, profile, filename, executor_type) -> None:
    path, selected = _select(scenario_id, profile)
    assert selected.value == profile and path.name == filename
    assert cli._profile_scenario_path(selected).name == filename
    runner = build_profile_runner(load(path), object(), tmp_path)
    assert isinstance(runner, executor_type)


@pytest.mark.parametrize("scenario_id", ["N-01", "N-03"])
def test_spec009_scenarios_require_an_explicit_profile(scenario_id) -> None:
    with pytest.raises(cli.CliContractError) as exc:
        _select(scenario_id, None)
    assert exc.value.code == "PROFILE_REQUIRED"


@pytest.mark.parametrize(
    ("scenario_id", "profile"),
    [("N-01", "N03_STALE_CONSENT_V1"), ("N-03", "N01_NOTICE_V1"), ("N-02", "N01_NOTICE_V1"), ("H-01", "N03_STALE_CONSENT_V1")],
)
def test_spec009_profiles_cannot_cross_scenarios(scenario_id, profile) -> None:
    with pytest.raises(cli.CliContractError) as exc:
        _select(scenario_id, profile)
    assert exc.value.code == "PROFILE_MISMATCH"


@pytest.fixture
def runtime_factory(tmp_path, target_snapshot, settings, monkeypatch):
    target = spec009_target(target_snapshot)
    built = {}

    def create_runtime(_settings, scenario_path):
        scenario = load(scenario_path)
        executor_type = N01Executor if scenario.scenario_id == "N-01" else N03Executor
        adapters, _backend, _store = make_spec009_adapters(tmp_path, target)
        executor = executor_type(scenario, adapters, _settings.run_root)
        executor.preflight = lambda target_id: ready(scenario, target)
        built["executor"] = executor
        return executor

    monkeypatch.setattr(cli, "create_runtime", create_runtime)
    monkeypatch.setattr(cli, "_settings", lambda args: __import__("dataclasses").replace(settings, run_root=tmp_path / "cli-runs"))
    return built


@pytest.mark.parametrize(("scenario_id", "profile"), [("N-01", "N01_NOTICE_V1"), ("N-03", "N03_STALE_CONSENT_V1")])
def test_run_show_verify_and_retest_over_the_cli(tmp_path, runtime_factory, capsys, scenario_id, profile) -> None:
    root = str(tmp_path / "cli-runs")
    code = cli.main(["run", scenario_id, "--target", "whyyou-local", "--profile", profile, "--run-root", root, "--json"])
    run_payload = json.loads(capsys.readouterr().out)
    assert code == 0, run_payload
    run_id = run_payload["run_id"]
    assert run_payload["verdict"] == "PASS" and run_payload["execution_profile"] == profile

    assert cli.main(["show", run_id, "--run-root", root, "--json"]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["scenario_id"] == scenario_id and shown["environment_restore_status"] == "SUCCEEDED"
    assert shown["evaluated_assertions"] == [f"{scenario_id.replace('-', '')}-A{i}" for i in (1, 2, 3)]

    assert cli.main(["verify", run_id, "--run-root", root, "--json"]) == 0
    verified = json.loads(capsys.readouterr().out)
    assert verified["bundle_status"] == "VERIFIED"
    assert verified["profile_contract"] == "controlproof.bundle-profile.spec009.v1"

    code = cli.main(["retest", run_id, "--target", "whyyou-local", "--run-root", root, "--json"])
    child = json.loads(capsys.readouterr().out)
    assert code == 0, child
    assert child["parent_run_id"] == run_id and child["run_id"] != run_id
