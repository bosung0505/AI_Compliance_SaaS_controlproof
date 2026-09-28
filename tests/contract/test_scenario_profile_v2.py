from __future__ import annotations

import pytest
from pydantic import ValidationError

from engine.models import ExecutionProfile, FaultVariant, ScenarioProfile
from engine.scenario import load


def test_v1_h03_loads_without_v2_fields_and_keeps_profile_identity():
    scenario = load("scenarios/H-03.yaml")
    assert scenario.execution_profile is None
    assert scenario.snapshot().definition.get("execution_profile") is None


def test_canonical_v2_profile_requires_exact_fault_assertions_and_evidence():
    profile = ScenarioProfile.canonical(ExecutionProfile.E03_AFTER_V2)
    assert profile.fault_variant is FaultVariant.AFTER_RESULT_DURABLE_BEFORE_COMPLETION
    assert profile.applicable_assertion_ids == ("E03-A1", "E03-A5", "E03-A6", "E03-A8")
    with pytest.raises(ValidationError):
        ScenarioProfile(
            **{
                **profile.model_dump(),
                "fault_variant": FaultVariant.BEFORE_RESULT_DURABLE,
            }
        )


def test_profile_snapshot_includes_timing_and_contract_identity():
    profile = ScenarioProfile.canonical(ExecutionProfile.H03_DLQ_V2)
    first = profile.snapshot_digest
    second = profile.model_copy().snapshot_digest
    assert first == second
    assert len(first) == 64


def test_h03_dlq_scenario_matches_the_canonical_profile_and_restore_contract():
    scenario = load("scenarios/H-03-DLQ.yaml")
    assert scenario.execution_profile is ExecutionProfile.H03_DLQ_V2
    assert scenario.fault_variant is FaultVariant.BEFORE_RESULT_DURABLE
    assert scenario.applicable_assertion_ids == tuple(f"H03-A{i}" for i in range(1, 10))
    assert tuple(item.assertion_id for item in scenario.assertions) == (
        scenario.applicable_assertion_ids
    )
    assert {item.evidence_id for item in scenario.required_evidence} == {
        *(f"EV-{i:02d}" for i in range(1, 10)),
        *(f"EV2-{i:02d}" for i in range(1, 10)),
        "EV2-12",
    }
    assert scenario.timing_policy.expected_queue == {
        "max_receive_count": 3,
        "visibility_timeout_seconds": 5,
    }
    assert scenario.restore_policy.mandatory is True
    assert [step.step_id for step in scenario.steps[-2:]] == [
        "restore-marker",
        "redrive-terminal-failure",
    ]
    assert all(step.always_run for step in scenario.steps[-2:])
