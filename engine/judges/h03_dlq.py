"""Evidence-only H03-A8/A9 evaluators for terminal reporting failure."""

from __future__ import annotations

from collections.abc import Sequence

from engine.models import (
    AssertionResult,
    AssertionStatus,
    DeliveryAttemptRecord,
    InconclusiveReason,
    Presence,
    TerminalFailureRecord,
)


def judge_h03_dlq(
    *,
    attempts: Sequence[DeliveryAttemptRecord],
    attempts_presence: Presence = Presence.PRESENT,
    terminal: TerminalFailureRecord | None,
    dlq_presence: Presence,
    ui_status: str | None,
    api_status: str | None,
    operator_locator: str | None,
    evidence_conflict: bool = False,
    expected_receive_count: int = 3,
) -> tuple[AssertionResult, AssertionResult]:
    """Judge failure preservation and visibility without performing target I/O."""

    if evidence_conflict:
        return (
            _result(
                "H03-A8",
                AssertionStatus.INCONCLUSIVE,
                detail="재시도 소진과 DLQ 증적이 서로 충돌합니다.",
                reason=InconclusiveReason.EVIDENCE_CONFLICT,
            ),
            _result(
                "H03-A9",
                AssertionStatus.INCONCLUSIVE,
                detail="최종 실패 표시와 운영 증적이 서로 충돌합니다.",
                reason=InconclusiveReason.EVIDENCE_CONFLICT,
            ),
        )
    a8 = _judge_preservation(
        attempts,
        attempts_presence,
        terminal,
        dlq_presence,
        expected_receive_count,
    )
    a9 = _judge_visibility(
        dlq_presence=dlq_presence,
        ui_status=ui_status,
        api_status=api_status,
        operator_locator=operator_locator,
    )
    return a8, a9


def _judge_preservation(
    attempts: Sequence[DeliveryAttemptRecord],
    attempts_presence: Presence,
    terminal: TerminalFailureRecord | None,
    dlq_presence: Presence,
    expected_receive_count: int,
) -> AssertionResult:
    actual = {
        "attempts": [item.delivery_attempt for item in attempts],
        "attempts_presence": attempts_presence.value,
        "dlq_presence": dlq_presence.value,
        "terminal_event": str(terminal.source_event_id) if terminal else None,
    }
    if Presence.UNAVAILABLE in {attempts_presence, dlq_presence}:
        return _result(
            "H03-A8",
            AssertionStatus.INCONCLUSIVE,
            detail="DLQ 접근에 실패해 실패 건 보존 여부를 판단할 수 없습니다.",
            expected={"attempts": list(range(1, expected_receive_count + 1)), "dlq": "PRESENT"},
            actual=actual,
            reason=InconclusiveReason.ACCESS_LIMITED,
        )
    expected_attempts = list(range(1, expected_receive_count + 1))
    attempt_numbers = [item.delivery_attempt for item in attempts]
    one_event = {item.source_event_id for item in attempts}
    linked = (
        terminal is not None
        and len(one_event) == 1
        and terminal.source_event_id in one_event
        and terminal.last_delivery_attempt == expected_receive_count
    )
    passed = (
        dlq_presence is Presence.PRESENT
        and terminal is not None
        and attempt_numbers == expected_attempts
        and linked
    )
    return _result(
        "H03-A8",
        AssertionStatus.PASS if passed else AssertionStatus.FAIL,
        expected={"attempts": expected_attempts, "dlq": "PRESENT"},
        actual=actual,
        detail=(
            "실제 전달 시도와 원 사건에 연결된 LocalStack DLQ 실패 건을 확인했습니다."
            if passed
            else "조회는 완료됐지만 재시도 시계열 또는 원 사건과 연결된 DLQ 실패 건이 없습니다."
        ),
    )


def _judge_visibility(
    *,
    dlq_presence: Presence,
    ui_status: str | None,
    api_status: str | None,
    operator_locator: str | None,
) -> AssertionResult:
    actual = {
        "ui_status": ui_status,
        "api_status": api_status,
        "operator_locator": operator_locator,
    }
    if dlq_presence is Presence.UNAVAILABLE or ui_status is None or api_status is None:
        return _result(
            "H03-A9",
            AssertionStatus.INCONCLUSIVE,
            detail="담당자 또는 운영자 실패 표시를 끝까지 관찰하지 못했습니다.",
            expected={"ui_status": "final_failed", "operator_locator": "present"},
            actual=actual,
            reason=(
                InconclusiveReason.ACCESS_LIMITED
                if dlq_presence is Presence.UNAVAILABLE
                else InconclusiveReason.INSUFFICIENT_EVIDENCE
            ),
        )
    passed = (
        dlq_presence is Presence.PRESENT
        and ui_status == "final_failed"
        and api_status in {"failed", "final_failed"}
        and bool(operator_locator)
    )
    return _result(
        "H03-A9",
        AssertionStatus.PASS if passed else AssertionStatus.FAIL,
        expected={"ui_status": "final_failed", "operator_locator": "present"},
        actual=actual,
        detail=(
            "최종 실패가 처리 중·준비 완료와 구분되고 운영자가 실패 건을 추적할 수 있습니다."
            if passed
            else "담당자 표시가 최종 실패를 구분하지 못하거나 운영자 추적 위치가 없습니다."
        ),
    )


def _result(
    assertion_id: str,
    status: AssertionStatus,
    *,
    detail: str,
    expected: object | None = None,
    actual: object | None = None,
    reason: InconclusiveReason | None = None,
) -> AssertionResult:
    return AssertionResult(
        assertion_id=assertion_id,
        subject_ref="candidate-01",
        status=status,
        expected=expected,
        actual=actual,
        reason_code=reason,
        detail=detail,
        source_requirements=(assertion_id,),
    )
