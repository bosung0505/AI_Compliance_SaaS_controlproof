"""T006 — scenario v4 contract for E-01/E-02 (contracts/scenario-profile-v4.md).

The E-01/E-02 tests are RED until T013 (engine/scenario.py v4) and T012 (profile enum). Canonical sets are
written here, not imported, so the contract is pinned independently of the implementation. Drift tests first
prove the canonical payload loads, so they cannot pass vacuously before the profile exists. The v1~v3 guard at
the end must stay green.
"""

from __future__ import annotations

import copy
from importlib import import_module

import pytest
from pydantic import ValidationError

from engine.scenario import ScenarioDefinition, load

COMMON_CAPABILITIES = {
    "target.version.read": "v1",
    "target.environment.read": "v1",
    "model.fixture.read": "v1",
    "spec004.lanes.seed": "v1",
    "spec004.lanes.teardown": "v1",
    "consent.policy.read": "v1",
    "consent.commit.write": "v1",
    "consent.state.read": "v1",
    "report.generation.request": "v1",
    "report.processing.receipts.read": "v1",
    "report.records.read": "v1",
    "report.api.read": "v1",
}
E01_CAPABILITIES = COMMON_CAPABILITIES | {
    "model.emission.read": "v1",
    "timeline.api.read": "v1",
    "evidence.segment.remove": "v1",
    "evidence.segment.restore": "v1",
    "report.axes.probe_write": "v1",
    "report.axes.probe_restore": "v1",
}
E02_CAPABILITIES = COMMON_CAPABILITIES | {
    "criteria.version.create": "v1",
    "criteria.version.publish": "v1",
    "criteria.version.read": "v1",
    "scoring.rule.source.read": "v1",
}
E01_STEPS = (
    "capture-environment",
    "capture-capabilities",
    "seed-report-lanes",
    "commit-lane-consents",
    "request-lane-reports",
    "capture-reference-report",
    "seed-citation-matrix",
    "commit-matrix-consent",
    "request-matrix-report",
    "capture-citation-cases",
    "capture-removal-baseline",
    "apply-evidence-removal",
    "capture-post-removal",
    "restore-evidence-removal",
    "verify-removal-restored",
    "capture-post-restore",
    "capture-probe-baseline",
    "apply-storage-probe",
    "capture-storage-probe-reads",
    "restore-storage-probe",
    "verify-storage-probe-restored",
    "recapture-reference-report",
    "teardown-report-lanes",
)
E01_ALWAYS = {
    "restore-evidence-removal",
    "verify-removal-restored",
    "restore-storage-probe",
    "verify-storage-probe-restored",
    "teardown-report-lanes",
}
E02_STEPS = (
    "capture-environment",
    "capture-capabilities",
    "capture-scoring-rule-source",
    "seed-e02-position",
    "create-publish-v1",
    "seed-first-applicant",
    "commit-first-consent",
    "request-first-report",
    "capture-pre-change",
    "recompute-first-report",
    "create-publish-v2",
    "capture-version-change",
    "seed-second-applicant",
    "commit-second-consent",
    "request-second-report",
    "capture-second-report",
    "capture-post-change",
    "recompute-second-report",
    "compare-first-report",
    "teardown-e02-position",
    "verify-other-positions-unchanged",
)
E02_ALWAYS = {"teardown-e02-position", "verify-other-positions-unchanged"}
TIMING = {
    "poll_seconds": 2,
    "stability_consecutive": 3,
    "stability_seconds": 4,
    "environment_restore_deadline_seconds": 120,
    "run_deadline_seconds": 540,
    "bundle_verify_deadline_seconds": 60,
    "expected_queue": {},
}
FIXTURE = {"spec004-report-v1": "e15ec3790b64b2fba10e0caa9372f08c917edbbaa99ce308076952b838668b3f"}
E01 = {
    "scenario_id": "E-01",
    "profile": "E01_CITATION_EVIDENCE_V1",
    "assertions": ("E01-A1", "E01-A2", "E01-A3", "E01-A4"),
    "evidence": ("EV4-01", "EV4-02", "EV4-03", "EV4-04", "EV4-05", "EV4-09", "EV4-10"),
    "lanes": ("E01_REFERENCE", "E01_CITATION_MATRIX", "E01_EVIDENCE_REMOVAL", "E01_STORAGE_PROBE"),
    "capabilities": E01_CAPABILITIES,
    "steps": E01_STEPS,
    "always": E01_ALWAYS,
    "preconditions": ("source-clean", "fixture-spec004", "external-ai-blocked"),
}
E02 = {
    "scenario_id": "E-02",
    "profile": "E02_SCORING_FREEZE_V1",
    "assertions": ("E02-A1", "E02-A2", "E02-A3"),
    "evidence": ("EV4-01", "EV4-02", "EV4-04", "EV4-06", "EV4-07", "EV4-08", "EV4-09", "EV4-10"),
    "lanes": ("E02_FIRST_APPLICANT", "E02_SECOND_APPLICANT"),
    "capabilities": E02_CAPABILITIES,
    "steps": E02_STEPS,
    "always": E02_ALWAYS,
    "preconditions": ("source-clean", "fixture-spec004", "scoring-source-pinned"),
}


def payload(spec: dict) -> dict:
    return {
        "schema_version": "controlproof.scenario.v4",
        "scenario_id": spec["scenario_id"],
        "version": "1.0.0",
        "execution_profile": spec["profile"],
        "bundle_profile_contract": "controlproof.bundle-profile.spec004.v1",
        "applicable_assertion_ids": list(spec["assertions"]),
        "lanes": list(spec["lanes"]),
        "title": spec["scenario_id"],
        "control_intent": "Spec 004 contract fixture",
        "required_capabilities": dict(spec["capabilities"]),
        "preconditions": [
            {"precondition_id": item, "kind": "target", "description": item}
            for item in spec["preconditions"]
        ],
        "steps": [
            {
                "step_id": step,
                "phase": "RECOVERED" if step in spec["always"] else "INJECTED",
                "action": step,
                "always_run": step in spec["always"],
            }
            for step in spec["steps"]
        ],
        "assertions": [
            {
                "assertion_id": assertion_id,
                "description": assertion_id,
                "expectation": {"status": "PASS"},
                "required_observation_keys": [],
                "required_evidence_ids": [spec["evidence"][0]],
                "source_requirements": ["FR-040"],
            }
            for assertion_id in spec["assertions"]
        ],
        "required_evidence": [
            {"evidence_id": item, "description": item, "artifact_types": ["JSON"]}
            for item in spec["evidence"]
        ],
        "timing_policy": dict(TIMING),
        "restore_policy": {
            "mandatory": True,
            "action": "restore-change-injections-and-teardown",
            "report_processing_result_field": "change_injection_restore_status",
        },
        "observation_comparators": {},
        "source_requirements": ["FR-040"],
        "allowed_model_fixtures": dict(FIXTURE),
        "excluded_scope": ["AWS", "N-01", "N-03"],
    }


@pytest.mark.parametrize("spec", [E01, E02], ids=["E-01", "E-02"])
def test_canonical_v4_payload_loads(spec) -> None:
    scenario = ScenarioDefinition.model_validate(payload(spec))
    assert scenario.execution_profile.value == spec["profile"]
    assert tuple(step.step_id for step in scenario.steps) == spec["steps"]
    assert tuple(lane.value for lane in scenario.lanes) == spec["lanes"]
    assert len(scenario.required_capabilities) == (18 if spec is E01 else 16)
    assert scenario.timing_policy.fault_ttl_seconds is None


def test_module_exports_the_canonical_sets() -> None:
    scenario = import_module("engine.scenario")
    assert scenario.E01_CANONICAL_STEPS == E01_STEPS
    assert scenario.E02_CANONICAL_STEPS == E02_STEPS
    assert scenario.E01_REQUIRED_CAPABILITIES == E01_CAPABILITIES
    assert scenario.E02_REQUIRED_CAPABILITIES == E02_CAPABILITIES


def _drop_first_step(value):
    value["steps"].pop(0)


def _reverse_steps(value):
    value["steps"].reverse()


def _always_off(value):
    value["steps"][-1]["always_run"] = False


def _extra_capability(value):
    value["required_capabilities"]["consent.fault.inject"] = "v1"


def _wrong_lane(value):
    value["lanes"][0] = "PRISTINE_BASELINE"


def _wrong_evidence(value):
    value["required_evidence"].pop()


def _timing_drift(value):
    value["timing_policy"]["run_deadline_seconds"] = 600


def _fault_ttl(value):
    value["timing_policy"]["fault_ttl_seconds"] = 600


def _second_fixture(value):
    value["allowed_model_fixtures"]["h03-report-v1"] = "c" * 64


def _schema_v3(value):
    value["schema_version"] = "controlproof.scenario.v3"


def _forbidden_step(value):
    value["steps"][0]["action"] = "capture N-01 mobile viewport"


def _product_deletion_step(value):
    value["steps"][0]["action"] = "submit privacy deletion request"


DRIFTS = [
    _drop_first_step,
    _reverse_steps,
    _always_off,
    _extra_capability,
    _wrong_lane,
    _wrong_evidence,
    _timing_drift,
    _fault_ttl,
    _second_fixture,
    _schema_v3,
    _forbidden_step,
    _product_deletion_step,
]


@pytest.mark.parametrize("spec", [E01, E02], ids=["E-01", "E-02"])
@pytest.mark.parametrize("drift", DRIFTS, ids=lambda item: item.__name__.lstrip("_"))
def test_v4_rejects_contract_drift(spec, drift) -> None:
    ScenarioDefinition.model_validate(payload(spec))
    mutated = copy.deepcopy(payload(spec))
    drift(mutated)
    with pytest.raises(ValidationError):
        ScenarioDefinition.model_validate(mutated)


def test_e02_requires_the_scoring_source_precondition() -> None:
    ScenarioDefinition.model_validate(payload(E02))
    mutated = payload(E02)
    mutated["preconditions"] = [
        item
        for item in mutated["preconditions"]
        if item["precondition_id"] != "scoring-source-pinned"
    ]
    with pytest.raises(ValidationError, match="scoring-source-pinned"):
        ScenarioDefinition.model_validate(mutated)


def test_v4_profiles_cannot_borrow_each_others_lanes() -> None:
    ScenarioDefinition.model_validate(payload(E01))
    mutated = payload(E01)
    mutated["lanes"] = list(E02["lanes"])
    with pytest.raises(ValidationError):
        ScenarioDefinition.model_validate(mutated)


@pytest.mark.parametrize(
    "path,profile",
    [
        ("scenarios/H-03.yaml", None),
        ("scenarios/H-03-DLQ.yaml", "H03_DLQ_V2"),
        ("scenarios/E-03-BEFORE.yaml", "E03_BEFORE_V2"),
        ("scenarios/E-03-AFTER.yaml", "E03_AFTER_V2"),
        ("scenarios/N-02.yaml", "N02_CONSENT_ORDER_V1"),
    ],
)
def test_existing_v1_v2_v3_scenarios_still_load(path: str, profile: str | None) -> None:
    scenario = load(path)
    assert (scenario.execution_profile.value if scenario.execution_profile else None) == profile
