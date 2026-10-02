"""Evidence-only N-02 evaluators.

The evaluator never infers safety from an HTTP status alone.  A1 establishes a
queryable pristine baseline; A2-A4 require both a denied boundary attempt and a
zero scoped effect delta.  Any observed prohibited effect is a direct FAIL.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from engine.adapters.base import AdapterResult
from engine.models import (
    SPEC003_UNVERIFIED_SCOPE,
    AssertionResult,
    AssertionStatus,
    CausalEdge,
    CausalEdgeStatus,
    CausalEvent,
    CausalEventKind,
    ConsentFaultReceipt,
    ConsentPolicySnapshot,
    ConsentPurpose,
    ConsentStateSnapshot,
    InconclusiveReason,
    Judgement,
    N02LaneId,
    Presence,
    ProcessingAttemptReceipt,
    ProcessingResponseClass,
    ProtectedEffectSnapshot,
    ProtectedPathId,
    RecoveryRecord,
    RecoveryStatus,
    RunState,
    Verdict,
)

N02_ASSERTION_IDS = tuple(f"N02-A{index}" for index in range(1, 8))


def judge_n02_run(
    *,
    run_id: UUID,
    assertion_results: tuple[AssertionResult, ...],
    run_state: RunState,
    baseline_valid: bool,
    bundle_verified: bool,
    decided_at: datetime,
) -> Judgement:
    """Combine the seven independent facts without masking a direct violation."""
    by_id = {item.assertion_id: item for item in assertion_results}
    if len(by_id) != len(assertion_results) or set(by_id) - set(N02_ASSERTION_IDS):
        raise ValueError("N-02 aggregate requires unique canonical assertions")
    if not baseline_valid and "N02-A1" in by_id:
        a1 = by_id["N02-A1"]
        by_id["N02-A1"] = AssertionResult(
            assertion_id="N02-A1",
            subject_ref=a1.subject_ref,
            status=AssertionStatus.INCONCLUSIVE,
            expected=a1.expected,
            actual=a1.actual,
            reason_code=InconclusiveReason.INSUFFICIENT_EVIDENCE,
            detail="pristine 기준선이 유효하지 않아 대상 통제를 판정하지 않았습니다.",
            source_requirements=a1.source_requirements,
        )
    ordered = tuple(
        by_id.get(assertion_id)
        or AssertionResult(
            assertion_id=assertion_id,
            subject_ref="synthetic-unassessed",
            status=AssertionStatus.INCONCLUSIVE,
            expected={"evaluated": True},
            actual={"evaluated": False},
            reason_code=InconclusiveReason.INSUFFICIENT_EVIDENCE,
            detail="이 assertion은 실행 또는 필수 증적이 없어 평가하지 못했습니다.",
            source_requirements=("EV3-10",),
        )
        for assertion_id in N02_ASSERTION_IDS
    )
    direct_fail = any(item.status is AssertionStatus.FAIL for item in ordered)
    inconclusive = [item for item in ordered if item.status is AssertionStatus.INCONCLUSIVE]
    if run_state is RunState.RESTORE_FAILED or not baseline_valid:
        verdict = Verdict.INCONCLUSIVE
        reason = InconclusiveReason.INSUFFICIENT_EVIDENCE
        summary = "복구 또는 시험 기준선을 확정하지 못해 제품 전체 결과를 판정하지 않았습니다."
    elif direct_fail:
        verdict = Verdict.FAIL
        reason = None
        summary = "동의 전 보호 대상 처리 또는 복구의 직접 위반이 관찰되었습니다."
    elif inconclusive or not bundle_verified:
        verdict = Verdict.INCONCLUSIVE
        reason = (
            InconclusiveReason.EVIDENCE_CONFLICT
            if any(item.reason_code is InconclusiveReason.EVIDENCE_CONFLICT for item in inconclusive)
            else InconclusiveReason.INSUFFICIENT_EVIDENCE
        )
        summary = "필수 증적이 부족하거나 충돌하여 전체 PASS를 확정하지 않았습니다."
    else:
        verdict = Verdict.PASS
        reason = None
        summary = "N02-A1~A7과 해당 실행 증적이 모두 확인되었습니다."
    return Judgement(
        run_id=run_id,
        scenario_id="N-02",
        verdict=verdict,
        reason_code=reason,
        assertion_results=ordered,
        missing_evidence=tuple(item.assertion_id for item in inconclusive),
        unverified_scope=tuple(sorted(SPEC003_UNVERIFIED_SCOPE)),
        summary=summary,
        decided_at=decided_at,
    )

_CASE_LANES = {
    ProtectedPathId.DOCUMENT_ANALYSIS: N02LaneId.DOCUMENT_BYPASS,
    ProtectedPathId.RECORDING: N02LaneId.RECORDING_BOUNDARY_PROBE,
    ProtectedPathId.AI_ASSESSMENT: N02LaneId.ASSESSMENT_BOUNDARY_PROBE,
}


class N02BaselinePreconditionError(RuntimeError):
    """Raised before attempts when the baseline cannot prove a pristine subject."""


@dataclass(frozen=True, slots=True)
class N02BypassCase:
    path_id: ProtectedPathId
    lane_id: N02LaneId
    attempt: ProcessingAttemptReceipt
    effects: ProtectedEffectSnapshot


@dataclass(frozen=True, slots=True)
class N02NormalOrderCase:
    policy: ConsentPolicySnapshot
    consent_state: ConsentStateSnapshot
    attempts: tuple[ProcessingAttemptReceipt, ...]
    effects: tuple[ProtectedEffectSnapshot, ...]
    events: tuple[CausalEvent, ...]
    edges: tuple[CausalEdge, ...]


@dataclass(frozen=True, slots=True)
class N02FaultFailureCase:
    failed_commit: AdapterResult
    receipt: ConsentFaultReceipt | None
    consent_state: ConsentStateSnapshot
    attempts: tuple[ProcessingAttemptReceipt, ...]
    effects: tuple[ProtectedEffectSnapshot, ...]
    overlay_cleanup_succeeded: bool


def validate_n02_baseline(baseline: tuple[ProtectedEffectSnapshot, ...]) -> None:
    if {item.path_id for item in baseline} != set(ProtectedPathId) or len(baseline) != 3:
        raise N02BaselinePreconditionError("baseline must cover the exact three paths")
    run_ids = {item.run_id for item in baseline}
    subjects = {item.subject_ref for item in baseline}
    if len(run_ids) != 1 or len(subjects) != 1:
        raise N02BaselinePreconditionError("baseline paths must share one Run and subject")
    for item in baseline:
        if item.lane_id is not N02LaneId.PRISTINE_BASELINE:
            raise N02BaselinePreconditionError("baseline must use PRISTINE_BASELINE lane")
        if item.source_status is Presence.UNAVAILABLE:
            raise N02BaselinePreconditionError("baseline source is unavailable")
        if item.current_effect_ids or item.new_effect_ids:
            raise N02BaselinePreconditionError("baseline contains protected effects")


def judge_n02_bypass(
    baseline: tuple[ProtectedEffectSnapshot, ...],
    cases: tuple[N02BypassCase, ...],
) -> tuple[AssertionResult, ...]:
    validate_n02_baseline(baseline)
    if {case.path_id for case in cases} != set(ProtectedPathId) or len(cases) != 3:
        raise ValueError("N-02 bypass cases must cover the exact three paths")
    baseline_run = baseline[0].run_id
    by_path = {case.path_id: case for case in cases}
    for path, expected_lane in _CASE_LANES.items():
        case = by_path[path]
        if case.lane_id is not expected_lane:
            raise ValueError(f"{path.value} is bound to the wrong lane")
        if (
            case.attempt.run_id != baseline_run
            or case.effects.run_id != baseline_run
            or case.attempt.path_id is not path
            or case.effects.path_id is not path
            or case.attempt.lane_id is not expected_lane
            or case.effects.lane_id is not expected_lane
            or case.attempt.subject_ref != case.effects.subject_ref
        ):
            raise ValueError("attempt/effect identity crosses a Run, lane, path or subject")

    results = [
        AssertionResult(
            assertion_id="N02-A1",
            subject_ref=baseline[0].subject_ref,
            status=AssertionStatus.PASS,
            expected={"three_paths_queryable": True, "protected_effect_count": 0},
            actual={
                "three_paths_queryable": True,
                "protected_effect_count": sum(
                    len(item.current_effect_ids) for item in baseline
                ),
            },
            detail="독립 pristine 지원자에서 세 보호 처리 효과가 모두 0임을 확인했습니다.",
            source_requirements=("EV3-03",),
        )
    ]
    for index, path in enumerate(ProtectedPathId, start=2):
        results.append(_judge_bypass_case(f"N02-A{index}", by_path[path]))
    return tuple(results)


def _judge_bypass_case(assertion_id: str, case: N02BypassCase) -> AssertionResult:
    expected = {
        "response_class": ProcessingResponseClass.DENIED.value,
        "new_effect_count": 0,
    }
    actual = {
        "response_class": case.attempt.response_class.value,
        "new_effect_ids": case.effects.new_effect_ids,
        "start_receipt_ids": case.effects.start_receipt_ids,
        "source_status": case.effects.source_status.value,
    }
    if case.effects.source_status is Presence.UNAVAILABLE:
        return AssertionResult(
            assertion_id=assertion_id,
            subject_ref=case.attempt.subject_ref,
            status=AssertionStatus.INCONCLUSIVE,
            expected=expected,
            actual=actual,
            reason_code=InconclusiveReason.INSUFFICIENT_EVIDENCE,
            detail="처리 후 효과 원장을 읽지 못해 차단 여부를 단정할 수 없습니다.",
            source_requirements=("EV3-04", "EV3-05"),
        )
    if case.effects.new_effect_ids or case.effects.start_receipt_ids:
        status = AssertionStatus.FAIL
        detail = "동의 전 직접 시도 뒤 금지된 신규 처리 효과 또는 실제 처리 시작이 확인되었습니다."
    elif case.attempt.response_class is ProcessingResponseClass.DENIED:
        status = AssertionStatus.PASS
        detail = "동의 전 직접 시도가 거부되었고 신규 처리 효과도 없습니다."
    elif case.attempt.response_class is ProcessingResponseClass.SUBMITTED:
        return AssertionResult(
            assertion_id=assertion_id,
            subject_ref=case.attempt.subject_ref,
            status=AssertionStatus.INCONCLUSIVE,
            expected=expected,
            actual=actual,
            reason_code=InconclusiveReason.INSUFFICIENT_EVIDENCE,
            detail="시험 입력은 제출됐지만 대상의 거부 또는 처리 시작 결과가 확인되지 않았습니다.",
            source_requirements=("EV3-04", "EV3-05"),
        )
    else:
        status = AssertionStatus.FAIL
        detail = "동의 전 직접 시도가 거부되지 않아 보호 경계가 열려 있습니다."
    return AssertionResult(
        assertion_id=assertion_id,
        subject_ref=case.attempt.subject_ref,
        status=status,
        expected=expected,
        actual=actual,
        detail=detail,
        source_requirements=("EV3-04", "EV3-05"),
    )


def judge_n02_normal_order(case: N02NormalOrderCase) -> AssertionResult:
    """Evaluate A5 from durable policy/consent facts and explicit causal edges."""

    expected = {
        "policy_identity_matches": True,
        "paths": tuple(path.value for path in ProtectedPathId),
        "causal_chain": "CONSENT_COMMITTED→REQUESTED→STARTED→RESULT_CREATED",
    }
    actual = {
        "consent_source_status": case.consent_state.source_status.value,
        "attempted_paths": tuple(sorted(item.path_id.value for item in case.attempts)),
        "event_count": len(case.events),
        "edge_count": len(case.edges),
    }
    if case.consent_state.source_status is Presence.UNAVAILABLE:
        return _a5_inconclusive(
            case,
            expected,
            actual,
            InconclusiveReason.INSUFFICIENT_EVIDENCE,
            "동의 응답 이후 서버의 내구성 있는 상태를 읽지 못해 처리를 허용할 수 없습니다.",
        )
    policy_matches = (
        case.consent_state.source_status is Presence.PRESENT
        and case.consent_state.invitation_status == "consented"
        and case.consent_state.active_consent_count == 1
        and case.consent_state.consent_policy_versions == (case.policy.policy_version,)
        and case.consent_state.consent_content_digests == (case.policy.content_digest,)
        and len(case.consent_state.accepted_purpose_sets) == 1
        and set(case.consent_state.accepted_purpose_sets[0]) == set(ConsentPurpose)
        and len(case.consent_state.consented_state_change_ids) == 1
        and len(case.consent_state.consent_completed_event_ids) == 1
    )
    if not policy_matches:
        return AssertionResult(
            assertion_id="N02-A5",
            subject_ref=case.consent_state.subject_ref,
            status=AssertionStatus.FAIL,
            expected=expected,
            actual=actual | {"policy_identity_matches": False},
            detail="동의 트랜잭션의 정책 식별값·목적·상태 전이·완료 사건이 정확히 일치하지 않습니다.",
            source_requirements=("EV3-02", "EV3-06"),
        )
    if any(
        item.response_class in {ProcessingResponseClass.DENIED, ProcessingResponseClass.ERROR}
        for item in case.attempts
    ):
        return AssertionResult(
            assertion_id="N02-A5",
            subject_ref=case.consent_state.subject_ref,
            status=AssertionStatus.FAIL,
            expected=expected,
            actual=actual | {"permanently_blocked": True},
            detail="유효한 동의가 확정된 뒤에도 하나 이상의 보호 대상 경로가 열리지 않았습니다.",
            source_requirements=("EV3-02", "EV3-06"),
        )
    if any(item.source_status is Presence.UNAVAILABLE for item in case.effects):
        return _a5_inconclusive(
            case,
            expected,
            actual,
            InconclusiveReason.INSUFFICIENT_EVIDENCE,
            "처리 효과 출처를 읽지 못해 정상 결과까지의 계보를 완성할 수 없습니다.",
        )
    if any(edge.status is CausalEdgeStatus.CONFLICTING for edge in case.edges):
        return _a5_inconclusive(
            case,
            expected,
            actual,
            InconclusiveReason.EVIDENCE_CONFLICT,
            "같은 사건의 인과 관계를 나타내는 증적이 서로 충돌합니다.",
        )

    by_id = {event.causal_event_id: event for event in case.events}
    proven = {
        (edge.from_event_id, edge.to_event_id)
        for edge in case.edges
        if edge.status is CausalEdgeStatus.PROVEN
    }
    consent_events = [
        event for event in case.events if event.kind is CausalEventKind.CONSENT_COMMITTED
    ]
    if len(consent_events) != 1:
        return _a5_inconclusive(
            case,
            expected,
            actual,
            InconclusiveReason.INSUFFICIENT_EVIDENCE,
            "내구성 있는 동의 완료 사건을 하나로 식별하지 못했습니다.",
        )
    consent = consent_events[0]
    policy_events = [
        event for event in case.events if event.kind is CausalEventKind.POLICY_RECEIVED
    ]
    if (
        len(policy_events) != 1
        or (policy_events[0].causal_event_id, consent.causal_event_id) not in proven
    ):
        return _a5_inconclusive(
            case,
            expected,
            actual,
            InconclusiveReason.INSUFFICIENT_EVIDENCE,
            "정책 수신부터 동의 완료까지의 명시적 인과 edge가 없습니다.",
        )
    for edge in case.edges:
        source = by_id.get(edge.from_event_id)
        target = by_id.get(edge.to_event_id)
        if (
            edge.status is CausalEdgeStatus.PROVEN
            and source is not None
            and target is not None
            and source.kind in {
                CausalEventKind.PROCESSING_REQUESTED,
                CausalEventKind.PROCESSING_STARTED,
                CausalEventKind.RESULT_CREATED,
            }
            and target.kind is CausalEventKind.CONSENT_COMMITTED
        ):
            return AssertionResult(
                assertion_id="N02-A5",
                subject_ref=case.consent_state.subject_ref,
                status=AssertionStatus.FAIL,
                expected=expected,
                actual=actual | {"direct_order_violation": source.kind.value},
                detail="보호 대상 처리 사건이 동의 완료보다 앞선 직접 순서 위반을 확인했습니다.",
                source_requirements=("EV3-02", "EV3-06"),
            )

    for path in ProtectedPathId:
        kinds = {
            kind: [
                event
                for event in case.events
                if event.path_id is path and event.kind is kind
            ]
            for kind in (
                CausalEventKind.PROCESSING_REQUESTED,
                CausalEventKind.PROCESSING_STARTED,
                CausalEventKind.RESULT_CREATED,
            )
        }
        if any(len(values) != 1 for values in kinds.values()):
            return _a5_inconclusive(
                case,
                expected,
                actual | {"missing_path": path.value},
                InconclusiveReason.INSUFFICIENT_EVIDENCE,
                f"{path.value} 경로의 요청·시작·결과 사건 중 일부가 없습니다.",
            )
        request = kinds[CausalEventKind.PROCESSING_REQUESTED][0]
        started = kinds[CausalEventKind.PROCESSING_STARTED][0]
        result = kinds[CausalEventKind.RESULT_CREATED][0]
        if not {
            (consent.causal_event_id, request.causal_event_id),
            (request.causal_event_id, started.causal_event_id),
            (started.causal_event_id, result.causal_event_id),
        } <= proven:
            return _a5_inconclusive(
                case,
                expected,
                actual | {"broken_path": path.value},
                InconclusiveReason.INSUFFICIENT_EVIDENCE,
                f"{path.value} 경로의 명시적 인과 edge가 끊겨 있습니다.",
            )
    return AssertionResult(
        assertion_id="N02-A5",
        subject_ref=case.consent_state.subject_ref,
        status=AssertionStatus.PASS,
        expected=expected,
        actual=actual | {"policy_identity_matches": True, "causal_order": "PROVEN"},
        detail=(
            "내구성 있는 동의 완료 뒤 세 보호 대상 경로의 요청·시작·결과가 명시적 edge로 연결되었습니다. "
            "알림 전달 시각은 판정 기준으로 사용하지 않았습니다."
        ),
        source_requirements=("EV3-02", "EV3-06"),
    )


def _a5_inconclusive(
    case: N02NormalOrderCase,
    expected,
    actual,
    reason: InconclusiveReason,
    detail: str,
) -> AssertionResult:
    return AssertionResult(
        assertion_id="N02-A5",
        subject_ref=case.consent_state.subject_ref,
        status=AssertionStatus.INCONCLUSIVE,
        expected=expected,
        actual=actual,
        reason_code=reason,
        detail=detail,
        source_requirements=("EV3-02", "EV3-06"),
    )


def judge_n02_fault_recovery(
    failure: N02FaultFailureCase,
    recovery: RecoveryRecord,
    recovered_order: AssertionResult | None,
) -> tuple[AssertionResult, AssertionResult]:
    """Evaluate atomic failed consent (A6) and same-subject recovery (A7)."""

    a6_expected = {
        "fault_triggered": True,
        "failed_consent_effect_count": 0,
        "three_paths_denied": True,
        "protected_effect_delta": 0,
    }
    partial_consent = bool(
        failure.consent_state.consent_record_ids
        or failure.consent_state.active_consent_count
        or failure.consent_state.consented_state_change_ids
        or failure.consent_state.consent_completed_event_ids
        or failure.consent_state.invitation_status == "consented"
    )
    leaked_effects = tuple(
        effect_id for effect in failure.effects for effect_id in effect.new_effect_ids
    )
    started_receipts = tuple(
        receipt_id for effect in failure.effects for receipt_id in effect.start_receipt_ids
    )
    accepted_paths = tuple(
        item.path_id.value
        for item in failure.attempts
        if item.response_class is ProcessingResponseClass.ACCEPTED
    )
    unresolved_paths = tuple(
        item.path_id.value
        for item in failure.attempts
        if item.response_class in {
            ProcessingResponseClass.SUBMITTED,
            ProcessingResponseClass.NO_RESPONSE,
            ProcessingResponseClass.ERROR,
        }
    )
    a6_actual = {
        "commit_code": failure.failed_commit.code,
        "receipt_present": failure.receipt is not None,
        "receipt_request_matches": (
            None
            if failure.receipt is None
            else failure.receipt.request_id
            == failure.failed_commit.data.get("request_id")
        ),
        "attempted_paths": tuple(item.path_id.value for item in failure.attempts),
        "partial_consent": partial_consent,
        "accepted_paths": accepted_paths,
        "leaked_effect_ids": leaked_effects,
        "started_receipt_ids": started_receipts,
        "unresolved_paths": unresolved_paths,
        "overlay_cleanup_succeeded": failure.overlay_cleanup_succeeded,
    }
    if partial_consent or leaked_effects or started_receipts or accepted_paths or failure.failed_commit.ok:
        a6 = AssertionResult(
            assertion_id="N02-A6",
            subject_ref=failure.consent_state.subject_ref,
            status=AssertionStatus.FAIL,
            expected=a6_expected,
            actual=a6_actual,
            detail="장애 요청 뒤 부분 동의 또는 보호 대상 처리 효과가 직접 관찰되었습니다.",
            source_requirements=("EV3-07", "EV3-08"),
        )
    elif (
        failure.receipt is None
        or failure.receipt.request_id != failure.failed_commit.data.get("request_id")
        or len(failure.attempts) != len(ProtectedPathId)
        or {item.path_id for item in failure.attempts} != set(ProtectedPathId)
        or len(failure.effects) != len(ProtectedPathId)
        or {item.path_id for item in failure.effects} != set(ProtectedPathId)
        or failure.consent_state.source_status is Presence.UNAVAILABLE
        or any(item.source_status is Presence.UNAVAILABLE for item in failure.effects)
        or unresolved_paths
    ):
        a6 = AssertionResult(
            assertion_id="N02-A6",
            subject_ref=failure.consent_state.subject_ref,
            status=AssertionStatus.INCONCLUSIVE,
            expected=a6_expected,
            actual=a6_actual,
            reason_code=InconclusiveReason.INSUFFICIENT_EVIDENCE,
            detail="fault 발동 receipt 또는 실패 뒤 상태·효과 증적이 부족합니다.",
            source_requirements=("EV3-07", "EV3-08"),
        )
    elif not failure.overlay_cleanup_succeeded:
        a6 = AssertionResult(
            assertion_id="N02-A6",
            subject_ref=failure.consent_state.subject_ref,
            status=AssertionStatus.INCONCLUSIVE,
            expected=a6_expected,
            actual=a6_actual,
            reason_code=InconclusiveReason.INSUFFICIENT_EVIDENCE,
            detail="임시 deep-boundary overlay를 안전하게 제거하지 못했습니다.",
            source_requirements=("EV3-07", "EV3-08"),
        )
    else:
        a6 = AssertionResult(
            assertion_id="N02-A6",
            subject_ref=failure.consent_state.subject_ref,
            status=AssertionStatus.PASS,
            expected=a6_expected,
            actual=a6_actual,
            detail="실제 fault가 발동했고 동의·상태·Outbox·세 보호 경로 효과가 모두 0입니다.",
            source_requirements=("EV3-07", "EV3-08"),
        )

    a7_expected = {
        "restore_status": RecoveryStatus.SUCCEEDED.value,
        "logical_consent_count": 1,
        "consent_completed_event_count": 1,
        "processing_order": "PROVEN",
    }
    a7_actual = recovery.model_dump(mode="json")
    known_duplicate = (
        recovery.logical_consent_count is not None
        and recovery.consent_completed_event_count is not None
        and (recovery.logical_consent_count, recovery.consent_completed_event_count)
        != (1, 1)
    )
    known_order_violation = recovery.processing_order_proven is False
    if known_duplicate or known_order_violation:
        a7 = AssertionResult(
            assertion_id="N02-A7",
            subject_ref=recovery.subject_ref,
            status=AssertionStatus.FAIL,
            expected=a7_expected,
            actual=a7_actual,
            detail="복구 뒤 중복 동의 효과 또는 처리 순서 위반이 직접 확인되었습니다.",
            source_requirements=("EV3-09", "EV3-06"),
        )
    elif recovery.restore_status is not RecoveryStatus.SUCCEEDED:
        a7 = AssertionResult(
            assertion_id="N02-A7",
            subject_ref=recovery.subject_ref,
            status=AssertionStatus.INCONCLUSIVE,
            expected=a7_expected,
            actual=a7_actual,
            reason_code=InconclusiveReason.INSUFFICIENT_EVIDENCE,
            detail="복구가 안전하게 끝나지 않아 수동 정리가 필요합니다.",
            source_requirements=("EV3-09",),
        )
    elif recovered_order is None or recovered_order.status is not AssertionStatus.PASS:
        reason = (
            recovered_order.reason_code
            if recovered_order is not None
            and recovered_order.status is AssertionStatus.INCONCLUSIVE
            else InconclusiveReason.INSUFFICIENT_EVIDENCE
        )
        a7 = AssertionResult(
            assertion_id="N02-A7",
            subject_ref=recovery.subject_ref,
            status=AssertionStatus.INCONCLUSIVE,
            expected=a7_expected,
            actual=a7_actual,
            reason_code=reason,
            detail="정상 재시도 뒤 A5 처리 순서를 PASS로 확인하지 못했습니다.",
            source_requirements=("EV3-09", "EV3-06"),
        )
    else:
        a7 = AssertionResult(
            assertion_id="N02-A7",
            subject_ref=recovery.subject_ref,
            status=AssertionStatus.PASS,
            expected=a7_expected,
            actual=a7_actual,
            detail="fault를 제거한 같은 지원자에서 동의 효과 한 세트와 정상 처리 순서를 확인했습니다.",
            source_requirements=("EV3-09", "EV3-06"),
        )
    return a6, a7
