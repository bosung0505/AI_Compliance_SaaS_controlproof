from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from uuid import UUID, uuid4

from engine.judges.n02 import N02FaultFailureCase, judge_n02_fault_recovery
from engine.models import (
    AssertionResult,
    AssertionStatus,
    InconclusiveReason,
    N02LaneId,
    Phase,
    Presence,
    ProcessingResponseClass,
    ProtectedPathId,
    RecoveryRecord,
    RecoveryStatus,
)
from tests.fixtures.fake_adapters import FakeN02Adapters


def _facts():
    fake = FakeN02Adapters()
    run_id = uuid4()
    lanes = fake.seed_lanes(run_id=str(run_id))
    lane = next(item for item in lanes if item.lane_id is N02LaneId.CONSENT_FAULT_RECOVERY)
    subject = lane.model_dump(mode="json")
    policy = fake.read_policy(subject=subject)
    fake.apply_consent_fault(
        run_id=str(run_id), subject=subject, expires_at=fake.now + timedelta(minutes=5)
    )
    failed = fake.commit(subject=subject, policy=policy, request_id="failed", trace_id="trace")
    state = fake.read_state(subject=subject, phase=Phase.INJECTED.value, step_id="failed")
    attempts = tuple(fake.attempt(path_id=path.value, subject=subject) for path in ProtectedPathId)
    effects = tuple(
        fake.read_effects(
            path_id=path.value,
            subject=subject,
            phase=Phase.INJECTED.value,
            step_id=f"failed-{path.value}",
        )
        for path in ProtectedPathId
    )
    receipt = fake.read_consent_fault_receipt(run_id=str(run_id), subject=subject)
    return N02FaultFailureCase(failed, receipt, state, attempts, effects, True), run_id


def _recovery(run_id: UUID, **updates) -> RecoveryRecord:
    values = {
        "run_id": run_id,
        "lane_id": N02LaneId.CONSENT_FAULT_RECOVERY,
        "subject_ref": "synthetic-recovered",
        "marker_removed": True,
        "consumed_token_removed": True,
        "hook_inactive": True,
        "condition_cleanup_succeeded": True,
        "safe_state_confirmed": True,
        "failed_request_effects_zero": True,
        "normal_retry_succeeded": True,
        "logical_consent_count": 1,
        "consent_completed_event_count": 1,
        "processing_order_proven": True,
        "restore_status": RecoveryStatus.SUCCEEDED,
        "manual_cleanup_required": False,
    }
    values.update(updates)
    return RecoveryRecord(**values)


def _order(subject_ref="synthetic-recovered") -> AssertionResult:
    return AssertionResult(
        assertion_id="N02-A5",
        subject_ref=subject_ref,
        status=AssertionStatus.PASS,
        expected={"causal_order": "PROVEN"},
        actual={"causal_order": "PROVEN"},
        detail="fixture",
    )


def test_missing_trigger_receipt_is_inconclusive() -> None:
    failure, run_id = _facts()
    a6, _ = judge_n02_fault_recovery(
        replace(failure, receipt=None), _recovery(run_id), _order()
    )
    assert a6.status is AssertionStatus.INCONCLUSIVE
    assert a6.reason_code is InconclusiveReason.INSUFFICIENT_EVIDENCE


def test_mismatched_trigger_request_and_incomplete_path_set_are_inconclusive() -> None:
    failure, run_id = _facts()
    mismatched = failure.receipt.model_copy(update={"request_id": "other-request"})
    request_a6, _ = judge_n02_fault_recovery(
        replace(failure, receipt=mismatched), _recovery(run_id), _order()
    )
    path_a6, _ = judge_n02_fault_recovery(
        replace(failure, attempts=failure.attempts[:2]),
        _recovery(run_id),
        _order(),
    )
    assert request_a6.status is AssertionStatus.INCONCLUSIVE
    assert path_a6.status is AssertionStatus.INCONCLUSIVE


def test_partial_consent_and_protected_effect_leakage_are_direct_failures() -> None:
    failure, run_id = _facts()
    consent_id = uuid4()
    partial = failure.consent_state.model_copy(
        update={
            "source_status": Presence.PRESENT,
            "invitation_status": "consented",
            "consent_record_ids": (consent_id,),
            "active_consent_count": 1,
        }
    )
    leaked_effect = failure.effects[0].model_copy(
        update={
            "source_status": Presence.PRESENT,
            "current_effect_ids": ("analysis:new",),
            "new_effect_ids": ("analysis:new",),
        }
    )
    partial_a6, _ = judge_n02_fault_recovery(
        replace(failure, consent_state=partial), _recovery(run_id), _order()
    )
    leaked_a6, _ = judge_n02_fault_recovery(
        replace(failure, effects=(leaked_effect, *failure.effects[1:])),
        _recovery(run_id),
        _order(),
    )
    assert partial_a6.status is AssertionStatus.FAIL
    assert leaked_a6.status is AssertionStatus.FAIL


def test_submitted_assessment_probe_requires_target_outcome_for_a6_fail() -> None:
    failure, run_id = _facts()
    submitted = failure.attempts[2].model_copy(
        update={"response_class": ProcessingResponseClass.SUBMITTED}
    )
    attempts = (*failure.attempts[:2], submitted)
    unresolved, _ = judge_n02_fault_recovery(
        replace(failure, attempts=attempts), _recovery(run_id), _order()
    )
    started = failure.effects[2].model_copy(
        update={"start_receipt_ids": ("target-start-1",)}
    )
    direct, _ = judge_n02_fault_recovery(
        replace(failure, attempts=attempts, effects=(*failure.effects[:2], started)),
        _recovery(run_id),
        _order(),
    )
    assert unresolved.status is AssertionStatus.INCONCLUSIVE
    assert direct.status is AssertionStatus.FAIL


def test_overlay_residue_and_restore_failure_require_manual_cleanup() -> None:
    failure, run_id = _facts()
    failed_restore = _recovery(
        run_id,
        marker_removed=False,
        consumed_token_removed=False,
        hook_inactive=False,
        failed_request_effects_zero=None,
        normal_retry_succeeded=None,
        logical_consent_count=None,
        consent_completed_event_count=None,
        processing_order_proven=None,
        restore_status=RecoveryStatus.FAILED,
        manual_cleanup_required=True,
    )
    residue_a6, _ = judge_n02_fault_recovery(
        replace(failure, overlay_cleanup_succeeded=False), failed_restore, None
    )
    _, failed_a7 = judge_n02_fault_recovery(failure, failed_restore, None)
    assert residue_a6.status is AssertionStatus.INCONCLUSIVE
    assert failed_a7.status is AssertionStatus.INCONCLUSIVE


def test_duplicate_recovered_consent_is_fail_even_when_restore_is_terminal() -> None:
    failure, run_id = _facts()
    duplicate = _recovery(
        run_id,
        logical_consent_count=2,
        consent_completed_event_count=2,
        restore_status=RecoveryStatus.FAILED,
        manual_cleanup_required=True,
    )
    _, a7 = judge_n02_fault_recovery(failure, duplicate, _order())
    assert a7.status is AssertionStatus.FAIL


def test_atomic_failure_and_exactly_once_recovery_pass_a6_and_a7() -> None:
    failure, run_id = _facts()
    a6, a7 = judge_n02_fault_recovery(failure, _recovery(run_id), _order())
    assert (a6.status, a7.status) == (AssertionStatus.PASS, AssertionStatus.PASS)
