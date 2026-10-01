from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import timedelta
from uuid import uuid4

import pytest

from engine.config import ConfigError, Settings
from engine.models import (
    ImplementationStatus,
    N02LaneId,
    Phase,
    Presence,
    ProcessingResponseClass,
    ProtectedPathId,
    ReadinessStatus,
)
from engine.readiness import evaluate_readiness
from engine.scenario import N02_REQUIRED_CAPABILITIES, ScenarioDefinition
from tests.contract.test_scenario_profile_v3 import _payload
from tests.fixtures.fake_adapters import FakeN02Adapters, make_adapters


@dataclass
class _Capability:
    status: ReadinessStatus
    action: str

    @property
    def registrations(self):
        return N02_REQUIRED_CAPABILITIES

    def probe(self, capability):
        from engine.adapters.base import CapabilityProbeResult

        return CapabilityProbeResult(capability, self.status, "sanitized", self.action)


def test_adapter_set_accepts_all_service_neutral_n02_capabilities() -> None:
    adapters, _ = make_adapters()
    composed = replace(
        adapters,
        n02_consent=object(),
        n02_seed=object(),
        n02_processing=object(),
        n02_causality=object(),
        n02_fault=object(),
        n02_observer=object(),
    )
    assert composed.n02_consent is not None
    assert composed.n02_fault is not None


def test_readiness_precedence_and_operator_action_are_exact(target_snapshot) -> None:
    scenario = ScenarioDefinition.model_validate(_payload())
    access = _Capability(ReadinessStatus.ACCESS_BLOCKED, "grant local DB read access")
    result = evaluate_readiness(
        scenario,
        target_id="whyyou-local",
        registrations=access.registrations,
        probe_results=[access.probe(item) for item in N02_REQUIRED_CAPABILITIES],
        target_feature_exists=True,
        target_snapshot=target_snapshot,
    )
    assert result.status is ReadinessStatus.ACCESS_BLOCKED
    assert result.operator_action == "grant local DB read access"
    assert result.implementation_status is ImplementationStatus.IMPLEMENTED

    missing = evaluate_readiness(
        scenario,
        target_id="whyyou-local",
        registrations=access.registrations,
        probe_results=[access.probe(item) for item in N02_REQUIRED_CAPABILITIES],
        target_feature_exists=False,
        target_snapshot=target_snapshot,
    )
    assert missing.status is ReadinessStatus.NO_TEST_TARGET
    assert missing.operator_action


def _settings(tmp_path, **overrides):
    environment = {
        "WHYYOU_BASE_URL": "http://localhost:8000",
        "WHYYOU_CONSOLE_URL": "http://localhost:5173",
        "WHYYOU_DATABASE_URL": "postgresql+psycopg://local:local@localhost/test",
        "WHYYOU_COMPANY_TOKEN": "local-test-token",
        "WHYYOU_REPO_PATH": str(tmp_path / "whyyou"),
        "CONTROLPROOF_FAULT_ROOT": str(tmp_path / "faults"),
        "CONTROLPROOF_OBSERVER_ROOT": str(tmp_path / "observers"),
        "CONTROLPROOF_TEST_HOOKS_ENABLED": "true",
        "CONTROLPROOF_OBSERVER_ENABLED": "true",
        "CONTROLPROOF_MODEL_SUBSTITUTE_ENABLED": "true",
        "CONTROLPROOF_MODEL_FIXTURE_ID": "n02-model-v1",
        "CONTROLPROOF_MODEL_FIXTURE_DIGEST": "a" * 64,
        **overrides,
    }
    return Settings.from_env(environment)


def test_n02_safety_requires_clean_personal_target_and_enabled_local_controls(tmp_path) -> None:
    settings = _settings(tmp_path)
    settings.validate_n02_safety(
        controlproof_branch="003-n02-consent-order",
        controlproof_dirty=False,
        whyyou_branch="bosung/controlproof-n02-integration",
        whyyou_dirty=False,
    )
    with pytest.raises(ConfigError, match="main branch"):
        settings.validate_n02_safety(
            controlproof_branch="003-n02-consent-order",
            controlproof_dirty=False,
            whyyou_branch="main",
            whyyou_dirty=False,
        )


def test_n02_safety_denies_external_ai(tmp_path) -> None:
    with pytest.raises(ConfigError, match="external AI"):
        _settings(tmp_path, CONTROLPROOF_EXTERNAL_AI_ALLOWED="true")


def test_fake_n02_adapters_keep_path_effect_causality_fault_and_restore_independent() -> None:
    run_id = uuid4()
    fake = FakeN02Adapters(
        responses={
            ProtectedPathId.DOCUMENT_ANALYSIS: ProcessingResponseClass.DENIED,
            ProtectedPathId.RECORDING: ProcessingResponseClass.ACCEPTED,
            ProtectedPathId.AI_ASSESSMENT: ProcessingResponseClass.DENIED,
        },
        new_effects={
            ProtectedPathId.DOCUMENT_ANALYSIS: (),
            ProtectedPathId.RECORDING: ("session-1",),
            ProtectedPathId.AI_ASSESSMENT: (),
        },
        unavailable_paths=frozenset({ProtectedPathId.AI_ASSESSMENT}),
    )
    lanes = fake.seed_lanes(run_id=str(run_id))
    assert len(lanes) == 6
    lane = next(item for item in lanes if item.lane_id is N02LaneId.RECORDING_BOUNDARY_PROBE)
    subject = lane.model_dump(mode="json")
    attempt = fake.attempt(path_id="RECORDING", subject=subject)
    effects = fake.read_effects(
        path_id="RECORDING",
        subject=subject,
        phase=Phase.INJECTED.value,
        step_id="capture-recording-effects",
    )
    assert attempt.response_class is ProcessingResponseClass.ACCEPTED
    assert effects.new_effect_ids == ("session-1",)

    assessment_lane = next(
        item for item in lanes if item.lane_id is N02LaneId.ASSESSMENT_BOUNDARY_PROBE
    )
    unavailable = fake.read_effects(
        path_id="AI_ASSESSMENT",
        subject=assessment_lane.model_dump(mode="json"),
        phase=Phase.INJECTED.value,
        step_id="capture-assessment-effects",
    )
    assert unavailable.source_status is Presence.UNAVAILABLE

    fault_lane = next(
        item for item in lanes if item.lane_id is N02LaneId.CONSENT_FAULT_RECOVERY
    )
    fault_subject = fault_lane.model_dump(mode="json")
    applied = fake.apply_consent_fault(
        run_id=str(run_id),
        subject=fault_subject,
        expires_at=fake.now + timedelta(minutes=5),
    )
    policy = fake.read_policy(subject=fault_subject)
    failed = fake.commit(
        subject=fault_subject,
        policy=policy,
        request_id="fault-request",
        trace_id="fixture-trace",
    )
    receipt = fake.read_consent_fault_receipt(
        run_id=str(run_id), subject=fault_subject
    )
    recovery = fake.restore_consent_fault(run_id=str(run_id), subject=fault_subject)
    assert applied.ok and not failed.ok and receipt.one_shot_consumed
    assert recovery.ok and recovery.data["hook_inactive"] is True
