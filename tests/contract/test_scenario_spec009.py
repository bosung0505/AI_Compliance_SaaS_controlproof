"""T004 — Spec 009 scenario profile v9 (contracts/scenario-profile-v9.md; FR-002, FR-005, FR-055)."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from engine.models import (
    SPEC009_PROFILES,
    ExecutionProfile,
    N01LaneId,
    N03LaneId,
    ScenarioProfile,
    TargetAccessKind,
)
from engine.scenario import ScenarioDefinition, load, load_all

N01 = Path("scenarios/N-01.yaml")
N03 = Path("scenarios/N-03.yaml")
FIXTURES = {"n02-analysis-v1": "092de5950a39ba3a7255c8696ffb073cddc65cda4615237044e3d910e32f9828"}
EXPECTED = {
    "N-01": {
        "path": N01,
        "profile": ExecutionProfile.N01_NOTICE_V1,
        "target_access": (TargetAccessKind.SCREEN, TargetAccessKind.API),
        "lanes": (N01LaneId.PC, N01LaneId.MOBILE),
        "assertions": ("N01-A1", "N01-A2", "N01-A3"),
        "evidence": ("EV9-01", "EV9-02", "EV9-03", "EV9-04", "EV9-06", "EV9-07"),
        "steps": ("seed-invitations", "open-consent-screens", "complete-consent", "cleanup-owned-subjects"),
        "unverified": (),
        "limitations": (),
        "restore": ("n01.owned.cleanup", "n01.cleanup"),
        "capabilities": {
            "target.version.read": "v1",
            "target.environment.read": "v1",
            "applicant.screen.open": "v1",
            "browser.chromium.available": "v1",
            "n01.invitations.seed": "v1",
            "n01.invitations.teardown": "v1",
            "consent.policy.read": "v1",
            "consent.state.read": "v1",
        },
    },
    "N-03": {
        "path": N03,
        "profile": ExecutionProfile.N03_STALE_CONSENT_V1,
        "target_access": (TargetAccessKind.API,),
        "lanes": (N03LaneId.STALE, N03LaneId.PAST),
        "assertions": ("N03-A1", "N03-A2", "N03-A3"),
        "evidence": ("EV9-01", "EV9-02", "EV9-05", "EV9-06", "EV9-07"),
        "steps": ("seed-lanes", "submit-stale-consent", "reread-and-commit", "cleanup-owned-subjects"),
        "unverified": ("N03-U1", "N03-U2", "N03-U3"),
        "limitations": ("N03-L1",),
        "restore": ("n03.owned.cleanup", "n03.cleanup"),
        "capabilities": {
            "target.version.read": "v1",
            "target.environment.read": "v1",
            "n02.subjects.seed": "v1",
            "n02.subjects.teardown": "v1",
            "consent.policy.read": "v1",
            "consent.commit.write": "v1",
            "consent.state.read": "v1",
        },
    },
}


def _raw(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _rejects(raw: dict) -> None:
    with pytest.raises(ValidationError):
        ScenarioDefinition.model_validate(raw)


@pytest.mark.parametrize("scenario_id", sorted(EXPECTED))
def test_v9_definition_loads_with_fixed_contract(scenario_id: str) -> None:
    expected = EXPECTED[scenario_id]
    scenario = load(expected["path"])
    assert scenario.schema_version == "controlproof.scenario.v9"
    assert (scenario.scenario_id, scenario.version) == (scenario_id, "1.0.0")
    assert scenario.execution_profile is expected["profile"]
    assert scenario.bundle_profile_contract == "controlproof.bundle-profile.spec009.v1"
    assert scenario.target_access == expected["target_access"]
    assert scenario.lanes == expected["lanes"]
    assert tuple(item.assertion_id for item in scenario.assertions) == expected["assertions"]
    assert scenario.applicable_assertion_ids == expected["assertions"]
    assert tuple(item.evidence_id for item in scenario.required_evidence) == expected["evidence"]
    assert tuple(step.step_id for step in scenario.steps) == expected["steps"]
    assert scenario.steps[-1].always_run and not any(step.always_run for step in scenario.steps[:-1])
    assert scenario.allowed_model_fixtures == FIXTURES
    assert scenario.required_capabilities == expected["capabilities"]
    assert tuple(item.id for item in scenario.unverified_scope_items) == expected["unverified"]
    assert all(item.follow_up for item in scenario.unverified_scope_items)
    assert tuple(item.id for item in scenario.limitations) == expected["limitations"]
    assert all(item.follow_up is None for item in scenario.limitations)
    restore = scenario.restore_policy
    assert (restore.mandatory, restore.action, restore.report_processing_result_field) == (True, *expected["restore"])


@pytest.mark.parametrize("scenario_id", sorted(EXPECTED))
def test_canonical_profile_matches_contract(scenario_id: str) -> None:
    expected = EXPECTED[scenario_id]
    canonical = ScenarioProfile.canonical(expected["profile"])
    assert canonical.scenario_id == scenario_id and canonical.scenario_version == "1.0.0"
    assert canonical.fault_variant is None and canonical.timing_policy == {}
    assert canonical.applicable_assertion_ids == expected["assertions"]
    assert canonical.required_evidence == expected["evidence"]
    assert expected["profile"] in SPEC009_PROFILES


def test_spec009_profile_set_and_enums() -> None:
    assert SPEC009_PROFILES == {ExecutionProfile.N01_NOTICE_V1, ExecutionProfile.N03_STALE_CONSENT_V1}
    assert [item.value for item in TargetAccessKind] == ["SCREEN", "API", "SOURCE"]
    assert [item.value for item in N01LaneId] == ["pc", "mobile"]
    assert [item.value for item in N03LaneId] == ["stale", "past"]


@pytest.mark.parametrize(
    ("path", "mutate"),
    [
        (N01, lambda raw: raw.update(target_access=["API"])),
        (N01, lambda raw: raw.update(target_access=["API", "SCREEN"])),
        (N03, lambda raw: raw.update(target_access=["SCREEN", "API"])),
        (N01, lambda raw: raw.update(lanes=["mobile", "pc"])),
        (N03, lambda raw: raw.update(lanes=["pc", "mobile"])),
        (N01, lambda raw: raw.update(schema_version="controlproof.scenario.v6")),
        (N01, lambda raw: raw.update(bundle_profile_contract="controlproof.bundle-profile.spec006.v1")),
        (N01, lambda raw: raw.update(version="1.0.1")),
        (N03, lambda raw: raw.update(scenario_id="N-01")),
        (N01, lambda raw: raw["steps"].reverse()),
        (N03, lambda raw: raw["steps"][-1].update(always_run=False)),
        (N01, lambda raw: raw.update(allowed_model_fixtures={"h01-assistant-v1": "0" * 64})),
        (N03, lambda raw: raw["required_capabilities"].pop("consent.commit.write")),
        (N01, lambda raw: raw["required_evidence"].reverse()),
        (N03, lambda raw: raw.update(unverified_scope_items=raw["unverified_scope_items"][:2])),
        (N03, lambda raw: raw.update(limitations=[])),
        (N01, lambda raw: raw.update(limitations=[{"id": "N03-L1", "text": "x"}])),
        (N01, lambda raw: raw["steps"][1].update(action="policy swap")),
        (N03, lambda raw: raw["steps"][1].update(step_id="viewport-check")),
    ],
)
def test_v9_definition_rejects_contract_drift(path: Path, mutate) -> None:
    raw = copy.deepcopy(_raw(path))
    mutate(raw)
    _rejects(raw)


@pytest.mark.parametrize("field", ["target_access", "unverified_scope_items", "limitations"])
@pytest.mark.parametrize("name", ["H-01.yaml", "N-02.yaml", "E-01.yaml", "H-03.yaml"])
def test_non_spec009_definition_rejects_v9_fields(name: str, field: str) -> None:
    raw = _raw(Path("scenarios") / name)
    raw[field] = ["API"] if field == "target_access" else [{"id": "N03-U1", "text": "x", "follow_up": "y"}]
    _rejects(raw)


def test_every_existing_scenario_still_loads() -> None:
    loaded = {(item.scenario_id, item.execution_profile) for item in load_all()}
    assert ("N-01", ExecutionProfile.N01_NOTICE_V1) in loaded
    assert ("N-03", ExecutionProfile.N03_STALE_CONSENT_V1) in loaded
    for definition in load_all():
        if definition.execution_profile not in SPEC009_PROFILES:
            assert definition.target_access == ()
            assert definition.unverified_scope_items == () and definition.limitations == ()


def test_spec009_snapshot_carries_v9_fields_and_others_do_not() -> None:
    n01 = load(N01).snapshot().definition
    assert n01["target_access"] == ["SCREEN", "API"] and n01["lanes"] == ["pc", "mobile"]
    assert n01["bundle_profile_contract"] == "controlproof.bundle-profile.spec009.v1"
    n03 = load(N03).snapshot().definition
    assert [item["id"] for item in n03["unverified_scope_items"]] == ["N03-U1", "N03-U2", "N03-U3"]
    h01 = load(Path("scenarios/H-01.yaml")).snapshot().definition
    assert not {"target_access", "unverified_scope_items", "limitations"} & set(h01)
