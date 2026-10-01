from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from engine.models import ExecutionProfile, N02LaneId, ScenarioProfile
from engine.scenario import (
    N02_CANONICAL_STEPS,
    N02_REQUIRED_CAPABILITIES,
    ScenarioDefinition,
)


def _payload() -> dict:
    profile = ScenarioProfile.canonical(ExecutionProfile.N02_CONSENT_ORDER_V1)
    evidence_ids = tuple(f"EV3-{index:02d}" for index in range(1, 11))
    return {
        "schema_version": "controlproof.scenario.v3",
        "scenario_id": "N-02",
        "version": "1.0.0",
        "execution_profile": "N02_CONSENT_ORDER_V1",
        "fault_variant": None,
        "bundle_profile_contract": "controlproof.bundle-profile.spec003.v1",
        "applicable_assertion_ids": list(profile.applicable_assertion_ids),
        "lanes": [lane.value for lane in N02LaneId],
        "title": "N-02 consent order",
        "control_intent": "prove consent precedes protected processing",
        "required_capabilities": N02_REQUIRED_CAPABILITIES,
        "preconditions": [],
        "steps": [
            {
                "step_id": step,
                "phase": "RECOVERED" if step in {
                    "restore-consent-fault",
                    "verify-safe-state",
                    "remove-fault-recording-overlay",
                    "remove-fault-assessment-overlay",
                    "verify-pristine-before-retry",
                    "teardown-subject-lanes",
                } else "INJECTED",
                "action": step,
                "always_run": step in {
                    "restore-consent-fault",
                    "verify-safe-state",
                    "remove-fault-recording-overlay",
                    "remove-fault-assessment-overlay",
                    "verify-pristine-before-retry",
                    "teardown-subject-lanes",
                },
            }
            for step in N02_CANONICAL_STEPS
        ],
        "assertions": [
            {
                "assertion_id": assertion_id,
                "description": assertion_id,
                "expectation": {"status": "PASS"},
                "required_observation_keys": [],
                "required_evidence_ids": [evidence_ids[index % len(evidence_ids)]],
                "source_requirements": ["HTTP"],
            }
            for index, assertion_id in enumerate(profile.applicable_assertion_ids)
        ],
        "required_evidence": [
            {"evidence_id": item, "description": item, "artifact_types": ["JSON"]}
            for item in evidence_ids
        ],
        "timing_policy": {
            "poll_seconds": 2,
            "stability_consecutive": 3,
            "stability_seconds": 4,
            "fault_ttl_seconds": 600,
            "environment_restore_deadline_seconds": 120,
            "run_deadline_seconds": 540,
            "bundle_verify_deadline_seconds": 60,
        },
        "restore_policy": {
            "mandatory": True,
            "action": "restore-consent-fault",
            "report_processing_result_field": "restore_status",
        },
        "observation_comparators": {},
        "source_requirements": ["HTTP", "DB", "FAULT"],
        "allowed_model_fixtures": {"n02-model-v1": "a" * 64},
        "excluded_scope": ["N-01", "N-03", "AWS"],
    }


def test_n02_v3_contract_is_exact_and_canonical() -> None:
    scenario = ScenarioDefinition.model_validate(_payload())
    assert scenario.execution_profile is ExecutionProfile.N02_CONSENT_ORDER_V1
    assert tuple(step.step_id for step in scenario.steps) == N02_CANONICAL_STEPS
    assert scenario.lanes == tuple(N02LaneId)
    assert scenario.timing_policy.run_deadline_seconds == 540
    assert scenario.timing_policy.bundle_verify_deadline_seconds == 60


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update(schema_version="controlproof.scenario.v2"),
        lambda value: value["lanes"].pop(),
        lambda value: value["steps"].reverse(),
        lambda value: value["required_evidence"].pop(),
        lambda value: value["timing_policy"].update(run_deadline_seconds=600),
    ],
)
def test_n02_v3_rejects_contract_drift(mutation) -> None:
    payload = copy.deepcopy(_payload())
    mutation(payload)
    with pytest.raises(ValidationError):
        ScenarioDefinition.model_validate(payload)


def test_n02_v3_rejects_n01_or_n03_steps() -> None:
    payload = _payload()
    payload["steps"][0]["action"] = "capture N-01 mobile viewport"
    with pytest.raises(ValidationError, match="N-01|N-03"):
        ScenarioDefinition.model_validate(payload)
