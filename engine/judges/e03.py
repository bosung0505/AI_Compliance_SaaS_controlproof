"""Evidence-only E-03 BEFORE evaluators."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from engine.adapters.base import AdapterResult
from engine.judges.common import (
    durable_reporting_effects,
    first_effect,
    has_durable_reporting_effect,
    source_unavailable,
)
from engine.models import (
    AssertionResult,
    AssertionStatus,
    BusinessEffectSnapshot,
    DeliveryAttemptRecord,
    FaultBoundaryReceipt,
    InconclusiveReason,
    Presence,
    RedriveReceipt,
    TerminalFailureRecord,
)


def judge_e03_before(
    *,
    source_event_id: UUID,
    boundary: FaultBoundaryReceipt | None,
    attempts: Sequence[DeliveryAttemptRecord],
    attempts_presence: Presence,
    terminal: TerminalFailureRecord | None,
    dlq_presence: Presence,
    injected_effects: Sequence[BusinessEffectSnapshot],
    recovered_effects: Sequence[BusinessEffectSnapshot],
    restore: AdapterResult,
    redrive: RedriveReceipt | None,
    expected_receive_count: int,
) -> tuple[AssertionResult, AssertionResult, AssertionResult, AssertionResult, AssertionResult]:
    injected = first_effect(injected_effects)
    recovered = first_effect(recovered_effects)
    return (
        _lineage(
            source_event_id,
            boundary,
            attempts,
            attempts_presence,
            terminal,
            dlq_presence,
            redrive,
            recovered,
        ),
        _retry_transition(
            source_event_id,
            attempts,
            attempts_presence,
            terminal,
            dlq_presence,
            expected_receive_count,
        ),
        _injected_absence(boundary, injected),
        _recovered_exactly_once(source_event_id, recovered),
        _safe_recovery(restore, redrive),
    )


def _lineage(
    source_event_id: UUID,
    boundary: FaultBoundaryReceipt | None,
    attempts: Sequence[DeliveryAttemptRecord],
    attempts_presence: Presence,
    terminal: TerminalFailureRecord | None,
    dlq_presence: Presence,
    redrive: RedriveReceipt | None,
    recovered: BusinessEffectSnapshot | None,
) -> AssertionResult:
    if (
        attempts_presence is Presence.UNAVAILABLE
        or dlq_presence is Presence.UNAVAILABLE
        or source_unavailable(recovered)
    ):
        return _result(
            "E03-A1",
            AssertionStatus.INCONCLUSIVE,
            "처리 계보 출처 중 하나에 접근할 수 없습니다.",
            InconclusiveReason.ACCESS_LIMITED,
        )
    if boundary is None or redrive is None:
        return _result(
            "E03-A1",
            AssertionStatus.INCONCLUSIVE,
            "장애 경계 또는 복구 영수증이 없어 전체 계보를 연결할 수 없습니다.",
            InconclusiveReason.INSUFFICIENT_EVIDENCE,
        )
    if recovered is None:
        return _result(
            "E03-A1",
            AssertionStatus.INCONCLUSIVE,
            "복구 효과 snapshot이 없어 전체 계보를 연결할 수 없습니다.",
            InconclusiveReason.INSUFFICIENT_EVIDENCE,
        )
    outbox_ids = durable_reporting_effects(recovered).get(
        "source_outbox_event_ids", []
    )
    linked = (
        boundary.outbox_event_id == source_event_id
        and bool(attempts)
        and all(item.source_event_id == source_event_id for item in attempts)
        and terminal is not None
        and terminal.source_event_id == source_event_id
        and redrive.source_event_id == source_event_id
        and recovered is not None
        and recovered.source_event_id == source_event_id
        and outbox_ids == [str(source_event_id)]
    )
    return _result(
        "E03-A1",
        AssertionStatus.PASS if linked else AssertionStatus.FAIL,
        (
            "원 Outbox 사건부터 복구 효과까지 같은 사건으로 연결됩니다."
            if linked
            else "조회는 완료됐지만 처리 계보의 식별 관계가 끊겼습니다."
        ),
    )


def _retry_transition(
    source_event_id: UUID,
    attempts: Sequence[DeliveryAttemptRecord],
    attempts_presence: Presence,
    terminal: TerminalFailureRecord | None,
    dlq_presence: Presence,
    expected_receive_count: int,
) -> AssertionResult:
    if Presence.UNAVAILABLE in {attempts_presence, dlq_presence}:
        return _result(
            "E03-A2",
            AssertionStatus.INCONCLUSIVE,
            "전달 시도 또는 DLQ에 접근할 수 없습니다.",
            InconclusiveReason.ACCESS_LIMITED,
        )
    expected = list(range(1, expected_receive_count + 1))
    observed = [item.delivery_attempt for item in attempts]
    passed = (
        observed == expected
        and terminal is not None
        and terminal.source_event_id == source_event_id
        and terminal.last_delivery_attempt == expected_receive_count
        and dlq_presence is Presence.PRESENT
    )
    return _result(
        "E03-A2",
        AssertionStatus.PASS if passed else AssertionStatus.FAIL,
        (
            "재시도 한도와 실제 시도, 최종 DLQ 전이가 일치합니다."
            if passed
            else "재시도 시계열이나 최종 실패 전이가 설정과 일치하지 않습니다."
        ),
        actual={"attempts": observed, "expected": expected},
    )


def _injected_absence(
    boundary: FaultBoundaryReceipt | None,
    injected: BusinessEffectSnapshot | None,
) -> AssertionResult:
    if boundary is None:
        return _result(
            "E03-A3",
            AssertionStatus.INCONCLUSIVE,
            "BEFORE 장애 경계를 관찰하지 못했습니다.",
            InconclusiveReason.INSUFFICIENT_EVIDENCE,
        )
    if injected is None:
        return _result(
            "E03-A3",
            AssertionStatus.INCONCLUSIVE,
            "장애 중 효과 snapshot이 없습니다.",
            InconclusiveReason.INSUFFICIENT_EVIDENCE,
        )
    if source_unavailable(injected):
        return _result(
            "E03-A3",
            AssertionStatus.INCONCLUSIVE,
            "장애 중 reporting 효과 출처에 접근할 수 없습니다.",
            InconclusiveReason.ACCESS_LIMITED,
        )
    absent = not has_durable_reporting_effect(injected)
    return _result(
        "E03-A3",
        AssertionStatus.PASS if absent else AssertionStatus.FAIL,
        (
            "BEFORE 장애 중 report·projection·processed 효과가 0건입니다."
            if absent
            else "BEFORE 장애 경계 이전이어야 하는데 일부 reporting 효과가 기록됐습니다."
        ),
        actual=durable_reporting_effects(injected),
    )


def _recovered_exactly_once(
    source_event_id: UUID,
    recovered: BusinessEffectSnapshot | None,
) -> AssertionResult:
    if recovered is None:
        return _result(
            "E03-A4",
            AssertionStatus.INCONCLUSIVE,
            "복구 효과 snapshot이 없습니다.",
            InconclusiveReason.INSUFFICIENT_EVIDENCE,
        )
    if source_unavailable(recovered):
        return _result(
            "E03-A4",
            AssertionStatus.INCONCLUSIVE,
            "복구 효과 출처에 접근할 수 없습니다.",
            InconclusiveReason.ACCESS_LIMITED,
        )
    effects = durable_reporting_effects(recovered)
    reports = effects.get("logical_report_ids", [])
    documents = effects.get("projection_document_ids", [])
    projection_reports = effects.get("projection_report_ids", [])
    processed = effects.get("processed_keys", [])
    outbox = effects.get("source_outbox_event_ids", [])
    expected_key = {
        "consumer_name": "reporting-worker",
        "event_id": str(source_event_id),
        "event_version": 1,
    }
    passed = (
        len(reports) == 1
        and len(set(reports)) == 1
        and bool(documents)
        and len(documents) == len(set(documents))
        and len(projection_reports) == len(documents)
        and set(projection_reports) == {reports[0]}
        and processed == [expected_key]
        and outbox == [str(source_event_id)]
    )
    return _result(
        "E03-A4",
        AssertionStatus.PASS if passed else AssertionStatus.FAIL,
        (
            "복구 후 report·projection·processed marker가 정확히 한 논리 세트입니다."
            if passed
            else "조회는 완료됐지만 복구 효과가 누락·중복되었거나 서로 불일치합니다."
        ),
        actual=effects,
    )


def _safe_recovery(
    restore: AdapterResult,
    redrive: RedriveReceipt | None,
) -> AssertionResult:
    passed = bool(
        restore.ok
        and restore.data.get("marker_inactive") is True
        and restore.data.get("worker_healthy") is True
        and redrive is not None
        and redrive.send_succeeded
        and redrive.delete_succeeded
    )
    if passed:
        return _result(
            "E03-A8",
            AssertionStatus.PASS,
            "marker 해제 뒤 안전한 send-before-delete 복구가 완료됐습니다.",
        )
    return _result(
        "E03-A8",
        AssertionStatus.INCONCLUSIVE,
        "환경 복구 또는 DLQ 삭제 완료를 확정할 수 없어 후속 장애 실행을 허용할 수 없습니다.",
        InconclusiveReason.INSUFFICIENT_EVIDENCE,
    )


def _result(
    assertion_id: str,
    status: AssertionStatus,
    detail: str,
    reason: InconclusiveReason | None = None,
    *,
    actual: object | None = None,
) -> AssertionResult:
    return AssertionResult(
        assertion_id=assertion_id,
        subject_ref="candidate-01",
        status=status,
        expected=None,
        actual=actual,
        reason_code=reason,
        detail=detail,
        source_requirements=(assertion_id,),
    )
