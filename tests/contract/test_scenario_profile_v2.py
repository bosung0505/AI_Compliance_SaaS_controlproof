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
