"""T008 — CLI profile selection and registry for E-01/E-02 (contracts/controlproof-cli-v4.md).

Each RED test names the task that turns it green: T012 (enum), T020 (CLI table and scenario paths), T013
(scenario v4), T040/T057 (executor registration). The H-03/E-03/N-02 guards stay green.
"""

from __future__ import annotations

import argparse

import pytest

from engine import cli
from engine.models import ExecutionProfile
from engine.runner import PROFILE_REGISTRY, UnregisteredExecutionProfile, build_profile_runner
from engine.scenario import ScenarioDefinition
from tests.contract.test_scenario_profile_v4 import E01, E02, payload
from tests.fixtures.fake_adapters import FakeClock, make_adapters


def _select(scenario_id: str, profile: str | None):
    return cli._scenario_selection(
        argparse.Namespace(scenario_id=scenario_id, profile=profile, scenario_file=None)
    )


@pytest.mark.parametrize("scenario_id", ["E-01", "E-02"])
def test_spec004_scenarios_require_an_explicit_profile(scenario_id: str) -> None:
    with pytest.raises(cli.CliContractError) as exc:
        _select(scenario_id, None)
    assert exc.value.code == "PROFILE_REQUIRED"


@pytest.mark.parametrize(
    "scenario_id,profile,filename",
    [
        ("E-01", "E01_CITATION_EVIDENCE_V1", "E-01.yaml"),
        ("E-02", "E02_SCORING_FREEZE_V1", "E-02.yaml"),
    ],
)
def test_spec004_profile_selects_its_own_scenario_file(
    scenario_id: str, profile: str, filename: str
) -> None:
    path, selected = _select(scenario_id, profile)
    assert selected.value == profile
    assert path.name == filename


@pytest.mark.parametrize(
    "scenario_id,profile",
    [
        ("E-01", "E02_SCORING_FREEZE_V1"),
        ("E-02", "E01_CITATION_EVIDENCE_V1"),
        ("N-02", "E01_CITATION_EVIDENCE_V1"),
        ("E-03", "E02_SCORING_FREEZE_V1"),
    ],
)
def test_spec004_profiles_cannot_cross_scenarios(scenario_id: str, profile: str) -> None:
    ExecutionProfile(profile)
    with pytest.raises(cli.CliContractError) as exc:
        _select(scenario_id, profile)
    assert exc.value.code == "PROFILE_MISMATCH"


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="RED until T040 (E-01) and T057 (E-02) register executors (enum exists since T012)",
)
@pytest.mark.parametrize("profile", ["E01_CITATION_EVIDENCE_V1", "E02_SCORING_FREEZE_V1"])
def test_spec004_profiles_have_registered_executors(profile: str) -> None:
    assert getattr(ExecutionProfile, profile) in PROFILE_REGISTRY.registrations


@pytest.mark.xfail(
    strict=True,
    raises=UnregisteredExecutionProfile,
    reason="RED until T040/T057 register the executors (scenario v4 loads since T013)",
)
@pytest.mark.parametrize("spec", [E01, E02], ids=["E-01", "E-02"])
def test_non_ready_preflight_leaves_no_side_effects(tmp_path, spec) -> None:
    scenario = ScenarioDefinition.model_validate(payload(spec))
    adapters, _ = make_adapters(target_exists=False)
    before = {path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*")}
    runner = build_profile_runner(scenario, adapters, tmp_path / "runs", clock=FakeClock())
    readiness = runner.preflight("whyyou-local")
    assert readiness.status.value != "READY"
    assert readiness.operator_action
    after = {path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*")}
    assert after == before


@pytest.mark.parametrize(
    "scenario_id,profile,filename",
    [
        ("H-03", None, "H-03.yaml"),
        ("H-03", "H03_DLQ_V2", "H-03-DLQ.yaml"),
        ("E-03", "E03_BEFORE_V2", "E-03-BEFORE.yaml"),
        ("E-03", "E03_AFTER_V2", "E-03-AFTER.yaml"),
        ("N-02", "N02_CONSENT_ORDER_V1", "N-02.yaml"),
    ],
)
def test_existing_profile_selection_is_unchanged(
    scenario_id: str, profile: str | None, filename: str
) -> None:
    path, _ = _select(scenario_id, profile)
    assert path.name == filename


@pytest.mark.parametrize("scenario_id", ["E-03", "N-02"])
def test_existing_explicit_profile_rule_is_unchanged(scenario_id: str) -> None:
    with pytest.raises(cli.CliContractError) as exc:
        _select(scenario_id, None)
    assert exc.value.code == "PROFILE_REQUIRED"
