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


def judge_e03_after(
    *,
    source_event_id: UUID,
    boundary: FaultBoundaryReceipt | None,
    duplicate_ack: AdapterResult | None,
    committed_effects: Sequence[BusinessEffectSnapshot],
    final_effects: Sequence[BusinessEffectSnapshot],
    dlq_presence: Presence,
    restore: AdapterResult,
) -> tuple[AssertionResult, AssertionResult, AssertionResult, AssertionResult]:
    """Judge the isolated commit-before-ack fault without borrowing BEFORE evidence."""

    committed = first_effect(committed_effects)
    final = first_effect(final_effects)
    return (
        _after_lineage(
            source_event_id,
            boundary,
            duplicate_ack,
            final,
            dlq_presence,
        ),
        _after_effects_exact(source_event_id, boundary, committed, final),
        _duplicate_short_circuit(source_event_id, boundary, duplicate_ack),
        _after_safe_restore(boundary, restore, dlq_presence),
    )


def _after_lineage(
    source_event_id: UUID,
    boundary: FaultBoundaryReceipt | None,
    duplicate_ack: AdapterResult | None,
    final: BusinessEffectSnapshot | None,
    dlq_presence: Presence,
) -> AssertionResult:
    if dlq_presence is Presence.UNAVAILABLE or source_unavailable(final):
        return _result(
            "E03-A1",
            AssertionStatus.INCONCLUSIVE,
            "AFTER 처리 계보 출처 중 하나에 접근할 수 없습니다.",
            InconclusiveReason.ACCESS_LIMITED,
        )
    if boundary is None:
        return _result(
            "E03-A1",
            AssertionStatus.INCONCLUSIVE,
            "commit 뒤 ack 전 장애 경계가 관찰되지 않았습니다.",
            InconclusiveReason.INSUFFICIENT_EVIDENCE,
        )
    receipt = dict(duplicate_ack.data.get("receipt", {})) if duplicate_ack else {}
    linked = (
        dlq_presence is Presence.ABSENT
        and duplicate_ack is not None
        and duplicate_ack.ok
        and boundary.outbox_event_id == source_event_id
        and receipt.get("outbox_event_id") == str(source_event_id)
        and final is not None
        and final.source_event_id == source_event_id
        and durable_reporting_effects(final).get("source_outbox_event_ids")
        == [str(source_event_id)]
    )
    return _result(
        "E03-A1",
        AssertionStatus.PASS if linked else AssertionStatus.FAIL,
        (
            "원 사건에서 AFTER 경계·중복 ack·최종 효과까지 계보가 연결됩니다."
            if linked
            else "조회는 완료됐지만 AFTER 처리 계보가 끊겼거나 예상 밖 DLQ가 관찰됐습니다."
        ),
    )


def _after_effects_exact(
    source_event_id: UUID,
    boundary: FaultBoundaryReceipt | None,
    committed: BusinessEffectSnapshot | None,
    final: BusinessEffectSnapshot | None,
) -> AssertionResult:
    if boundary is None:
        return _result(
            "E03-A5",
            AssertionStatus.INCONCLUSIVE,
            "AFTER 경계를 관찰하지 못해 commit 시점 효과를 판정할 수 없습니다.",
            InconclusiveReason.INSUFFICIENT_EVIDENCE,
        )
    if committed is None or final is None:
        return _result(
            "E03-A5",
            AssertionStatus.INCONCLUSIVE,
            "commit 직후 또는 중복 ack 뒤 효과 snapshot이 없습니다.",
            InconclusiveReason.INSUFFICIENT_EVIDENCE,
        )
    if source_unavailable(committed) or source_unavailable(final):
        return _result(
            "E03-A5",
            AssertionStatus.INCONCLUSIVE,
            "reporting 효과 출처에 접근할 수 없습니다.",
            InconclusiveReason.ACCESS_LIMITED,
        )
    committed_values = durable_reporting_effects(committed)
    final_values = durable_reporting_effects(final)
    passed = (
        _is_exact_reporting_set(committed_values, source_event_id)
        and _is_exact_reporting_set(final_values, source_event_id)
        and committed.state_digest == final.state_digest
        and committed_values == final_values
    )
    return _result(
        "E03-A5",
        AssertionStatus.PASS if passed else AssertionStatus.FAIL,
        (
            "commit 직후와 중복 ack 뒤 reporting 효과가 같은 한 논리 세트입니다."
            if passed
            else "report·projection·processed 효과가 누락·중복됐거나 재전달 뒤 달라졌습니다."
        ),
        actual={"committed": committed_values, "final": final_values},
    )


def _duplicate_short_circuit(
    source_event_id: UUID,
    boundary: FaultBoundaryReceipt | None,
    duplicate_ack: AdapterResult | None,
) -> AssertionResult:
    if boundary is None:
        return _result(
            "E03-A6",
            AssertionStatus.INCONCLUSIVE,
            "AFTER 경계를 관찰하지 못해 중복 재전달 분기를 판정할 수 없습니다.",
            InconclusiveReason.INSUFFICIENT_EVIDENCE,
        )
    if duplicate_ack is None:
        return _result(
            "E03-A6",
            AssertionStatus.INCONCLUSIVE,
            "중복 ack 관찰 결과가 없습니다.",
            InconclusiveReason.INSUFFICIENT_EVIDENCE,
        )
    if not duplicate_ack.ok and duplicate_ack.code.endswith("ACCESS_BLOCKED"):
        return _result(
            "E03-A6",
            AssertionStatus.INCONCLUSIVE,
            "중복 ack 증적 출처에 접근할 수 없습니다.",
            InconclusiveReason.ACCESS_LIMITED,
        )
    receipt = dict(duplicate_ack.data.get("receipt", {}))
    passed = bool(
        duplicate_ack.ok
        and receipt.get("outbox_event_id") == str(source_event_id)
        and receipt.get("consumer_name") == "reporting-worker"
        and receipt.get("handler_skipped") is True
        and receipt.get("acknowledged") is True
        and int(receipt.get("delivery_attempt", 0)) >= 2
    )
    return _result(
        "E03-A6",
        AssertionStatus.PASS if passed else AssertionStatus.FAIL,
        (
            "재전달이 handler를 건너뛰고 processed-message 분기에서 ack됐습니다."
            if passed
            else "재전달의 handler 생략과 ack를 함께 입증하지 못했습니다."
        ),
        actual=receipt,
    )


def _after_safe_restore(
    boundary: FaultBoundaryReceipt | None,
    restore: AdapterResult,
    dlq_presence: Presence,
) -> AssertionResult:
    if boundary is None or dlq_presence is Presence.UNAVAILABLE:
        return _result(
            "E03-A8",
            AssertionStatus.INCONCLUSIVE,
            "장애 경계 또는 DLQ 상태가 불확실해 환경 안전성을 확정할 수 없습니다.",
            InconclusiveReason.INSUFFICIENT_EVIDENCE,
        )
    if dlq_presence is Presence.PRESENT:
        return _result(
            "E03-A8",
            AssertionStatus.FAIL,
            "AFTER 일회성 재전달에서 기대하지 않은 DLQ 메시지가 관찰됐습니다.",
        )
    passed = bool(
        restore.ok
        and restore.data.get("marker_inactive") is True
        and restore.data.get("worker_healthy") is True
    )
    return _result(
        "E03-A8",
        AssertionStatus.PASS if passed else AssertionStatus.INCONCLUSIVE,
        (
            "일회성 marker가 해제되고 worker가 정상이며 DLQ는 비어 있습니다."
            if passed
            else "환경 복구를 확정할 수 없어 후속 장애 실행을 허용할 수 없습니다."
        ),
        None if passed else InconclusiveReason.INSUFFICIENT_EVIDENCE,
    )


def _is_exact_reporting_set(values: dict[str, object], source_event_id: UUID) -> bool:
    reports = list(values.get("logical_report_ids", []))
    documents = list(values.get("projection_document_ids", []))
    projection_reports = list(values.get("projection_report_ids", []))
    processed = list(values.get("processed_keys", []))
    outbox = list(values.get("source_outbox_event_ids", []))
    expected_key = {
        "consumer_name": "reporting-worker",
        "event_id": str(source_event_id),
        "event_version": 1,
    }
    return bool(
        len(reports) == 1
        and len(set(reports)) == 1
        and documents
        and len(documents) == len(set(documents))
        and len(projection_reports) == len(documents)
        and set(projection_reports) == {reports[0]}
        and processed == [expected_key]
        and outbox == [str(source_event_id)]
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
