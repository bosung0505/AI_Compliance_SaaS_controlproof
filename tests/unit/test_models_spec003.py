from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from engine.models import (
    BaselineKind,
    CausalEdge,
    CausalEdgeStatus,
    CausalEvent,
    CausalEventKind,
    CausalRelation,
    ConsentFaultBoundary,
    ConsentFaultReceipt,
    ConsentFaultVariant,
    ConsentPolicySnapshot,
    ConsentPurpose,
    ConsentStateSnapshot,
    N02EffectGroup,
    N02LaneId,
    Phase,
    Presence,
    ProcessingAttemptReceipt,
    ProcessingEntryKind,
    ProcessingResponseClass,
    ProtectedEffectSnapshot,
    ProtectedPathId,
    RecoveryRecord,
    RecoveryStatus,
    RunSubjectLane,
)

NOW = datetime(2026, 10, 1, tzinfo=UTC)
SHA = "a" * 64


def _lane(lane_id: N02LaneId, *, fixture: bool = False) -> RunSubjectLane:
    run_id = uuid4()
    return RunSubjectLane(
        run_id=run_id,
        lane_id=lane_id,
        subject_ref=f"synthetic-{lane_id.value.casefold()}",
        invitation_id=uuid4(),
        applicant_id=uuid4(),
        baseline_kind=(BaselineKind.PREREQUISITE_FIXTURE if fixture else BaselineKind.PRISTINE),
        fixture_kind="recording-equipment-strategy-v1" if fixture else None,
        fixture_digest=SHA if fixture else None,
        allowed_preexisting_effects={"equipment": 1, "strategy": 1} if fixture else {},
        target_effect_groups=(N02EffectGroup.RECORDING,),
        trace_namespace=f"controlproof:{run_id}:{lane_id.value}",
        seed_correlation_id=f"seed-{lane_id.value.casefold()}",
    )


def test_canonical_six_lanes_enforce_pristine_and_fixture_boundaries() -> None:
    pristine = {
        N02LaneId.PRISTINE_BASELINE,
        N02LaneId.DOCUMENT_BYPASS,
        N02LaneId.NORMAL_ORDER,
        N02LaneId.CONSENT_FAULT_RECOVERY,
    }
    lanes = [_lane(lane) for lane in pristine]
    lanes += [
        _lane(N02LaneId.RECORDING_BOUNDARY_PROBE, fixture=True),
        _lane(N02LaneId.ASSESSMENT_BOUNDARY_PROBE, fixture=True).model_copy(
            update={
                "fixture_kind": "assessment-completed-session-v1",
                "allowed_preexisting_effects": {"completed_session": 1, "final_turn": 1},
                "target_effect_groups": (N02EffectGroup.AI_ASSESSMENT,),
            }
        ),
    ]
    assert {lane.lane_id for lane in lanes} == set(N02LaneId)
    assert all(lane.fixture_digest is None for lane in lanes if lane.lane_id in pristine)

    with pytest.raises(ValidationError, match="pristine lane"):
        _lane(N02LaneId.DOCUMENT_BYPASS).model_copy(
            update={"fixture_kind": "forbidden", "fixture_digest": SHA}
        ).model_validate(
            _lane(N02LaneId.DOCUMENT_BYPASS).model_dump()
            | {"fixture_kind": "forbidden", "fixture_digest": SHA}
        )


def test_policy_consent_presence_and_effect_delta_are_explicit() -> None:
    policy = ConsentPolicySnapshot(
        policy_version="2026-08-v1",
        content_digest=SHA,
        required_purposes=tuple(ConsentPurpose),
        retention_days=365,
        received_at=NOW,
        request_id=uuid4(),
        source_ref="artifact:policy-http",
    )
    assert set(policy.required_purposes) == set(ConsentPurpose)

    absent = ConsentStateSnapshot(
        run_id=uuid4(),
        lane_id=N02LaneId.PRISTINE_BASELINE,
        subject_ref="synthetic-pristine",
        phase=Phase.BASELINE,
        step_id="capture-pristine-baseline",
        attempt=1,
        invitation_status="identity_verified",
        invitation_row_version=1,
        source_status=Presence.ABSENT,
        state_digest=SHA,
        captured_at=NOW,
    )
    assert absent.active_consent_count == 0
    with pytest.raises(ValidationError, match="UNAVAILABLE"):
        ConsentStateSnapshot.model_validate(
            absent.model_dump() | {"source_status": Presence.UNAVAILABLE}
        )

    effect = ProtectedEffectSnapshot(
        run_id=absent.run_id,
        lane_id=N02LaneId.DOCUMENT_BYPASS,
        subject_ref="synthetic-document",
        path_id=ProtectedPathId.DOCUMENT_ANALYSIS,
        phase=Phase.INJECTED,
        step_id="capture-document-effects",
        attempt=1,
        effect_group=N02EffectGroup.DOCUMENT_ANALYSIS,
        request_ids=("request-1",),
        baseline_effect_ids=("fixture-1",),
        fixture_effect_ids=("fixture-1",),
        current_effect_ids=("fixture-1", "result-1"),
        new_effect_ids=("result-1",),
        source_status=Presence.PRESENT,
        state_digest=SHA,
        captured_at=NOW,
    )
    assert effect.new_effect_ids == ("result-1",)
    with pytest.raises(ValidationError, match="delta"):
        ProtectedEffectSnapshot.model_validate(
            effect.model_dump() | {"new_effect_ids": ()}
        )


def test_attempt_causality_fault_and_recovery_cardinality() -> None:
    run_id = uuid4()
    attempt = ProcessingAttemptReceipt(
        run_id=run_id,
        lane_id=N02LaneId.CONSENT_FAULT_RECOVERY,
        subject_ref="synthetic-fault",
        path_id=ProtectedPathId.DOCUMENT_ANALYSIS,
        entry_kind=ProcessingEntryKind.HTTP,
        operation_id="createSubmissionUploadIntent",
        request_id=str(uuid4()),
        trace_id_digest=SHA,
        sent_at=NOW,
        response_at=NOW,
        response_class=ProcessingResponseClass.DENIED,
        status_code=403,
        sanitized_reason_code="CONSENT_REQUIRED",
        source_ref="artifact:document-attempt",
    )
    assert attempt.response_class is ProcessingResponseClass.DENIED

    first = CausalEvent(
        kind=CausalEventKind.CONSENT_COMMITTED,
        run_id=run_id,
        lane_id=N02LaneId.NORMAL_ORDER,
        subject_ref="synthetic-normal",
        domain_identity={"consent_id": str(uuid4())},
        occurred_at=NOW,
        observed_at=NOW,
        source_type="DB",
        source_ref="policy-and-consent.json",
    )
    second = CausalEvent(
        kind=CausalEventKind.PROCESSING_REQUESTED,
        run_id=run_id,
        lane_id=N02LaneId.NORMAL_ORDER,
        subject_ref="synthetic-normal",
        path_id=ProtectedPathId.DOCUMENT_ANALYSIS,
        domain_identity={"request_id": str(uuid4())},
        occurred_at=NOW,
        observed_at=NOW,
        source_type="HTTP",
        source_ref="bypass-attempts.jsonl",
    )
    edge = CausalEdge(
        run_id=run_id,
        lane_id=N02LaneId.NORMAL_ORDER,
        subject_ref="synthetic-normal",
        from_event_id=first.causal_event_id,
        to_event_id=second.causal_event_id,
        relation=CausalRelation.PROGRAM_ORDER,
        proof_refs=("artifact:consent-response",),
        status=CausalEdgeStatus.PROVEN,
    )
    assert edge.from_event_id != edge.to_event_id

    receipt = ConsentFaultReceipt(
        run_id=run_id,
        lane_id=N02LaneId.CONSENT_FAULT_RECOVERY,
        subject_ref="synthetic-fault",
        invitation_id=uuid4(),
        applicant_id=uuid4(),
        fault_variant=ConsentFaultVariant.AFTER_CONSENT_RECORD_BEFORE_STATE,
        boundary=ConsentFaultBoundary.AFTER_CONSENT_RECORD_BEFORE_INVITATION_STATE,
        request_id=str(uuid4()),
        triggered_at=NOW,
        one_shot_consumed=True,
    )
    assert receipt.one_shot_consumed

    recovery = RecoveryRecord(
        run_id=run_id,
        lane_id=N02LaneId.CONSENT_FAULT_RECOVERY,
        subject_ref="synthetic-fault",
        marker_removed=True,
        consumed_token_removed=True,
        hook_inactive=True,
        condition_cleanup_succeeded=True,
        safe_state_confirmed=True,
        failed_request_effects_zero=True,
        normal_retry_succeeded=True,
        logical_consent_count=1,
        consent_completed_event_count=1,
        processing_order_proven=True,
        restore_status=RecoveryStatus.SUCCEEDED,
        manual_cleanup_required=False,
    )
    assert recovery.logical_consent_count == recovery.consent_completed_event_count == 1
    # ID-003-14: SUCCEEDED means restore safety; the retry outcome is A7's to judge.
    with pytest.raises(ValidationError, match="every safety proof"):
        RecoveryRecord.model_validate(recovery.model_dump() | {"safe_state_confirmed": None})
    duplicate = RecoveryRecord.model_validate(
        recovery.model_dump() | {"logical_consent_count": 2, "processing_order_proven": False}
    )
    assert duplicate.restore_status is RecoveryStatus.SUCCEEDED
