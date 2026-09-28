"""Evidence-only H03-A8/A9 evaluators for terminal reporting failure."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from engine.adapters.base import AdapterResult
from engine.models import (
    AssertionResult,
    AssertionStatus,
    BusinessEffectSnapshot,
    DecisionPathCapability,
    DecisionPathId,
    DeliveryAttemptRecord,
    InconclusiveReason,
    Presence,
    TerminalFailureRecord,
)


def judge_h03_decisions(
    *,
    capabilities: Sequence[DecisionPathCapability],
    cases: Sequence[Mapping[str, Any]],
) -> AssertionResult:
    """Judge all documented final-effect paths without using AI scores."""

    expected = set(DecisionPathId)
    capability_ids = [item.path_id for item in capabilities]
    case_ids = [_path_id(item.get("path_id")) for item in cases]
    direct_risks: list[str] = []
    access_limited = False
    insufficient = False
    case_projection: dict[str, Any] = {}

    for case, path_id in zip(cases, case_ids, strict=True):
        if path_id is None:
            insufficient = True
            continue
        attempt = case.get("attempt")
        pre = _effect(case.get("pre_effects"))
        post = _effect(case.get("post_effects"))
        if not isinstance(attempt, AdapterResult) or not attempt.ok:
            access_limited = True
        accepted = bool(attempt.data.get("accepted")) if isinstance(attempt, AdapterResult) else None
        reason_present = (
            bool(attempt.data.get("reason_present"))
            if isinstance(attempt, AdapterResult)
            else False
        )
        if accepted:
            direct_risks.append(f"{path_id.value}:accepted")
        if accepted is False and not reason_present:
            insufficient = True
        if pre is None or post is None:
            insufficient = True
        else:
            if Presence.UNAVAILABLE in {pre.source_status, post.source_status}:
                access_limited = True
            elif Presence.ABSENT in {pre.source_status, post.source_status}:
                direct_risks.append(f"{path_id.value}:subject_effect_missing")
            elif pre.state_digest != post.state_digest:
                direct_risks.append(f"{path_id.value}:partial_effect")
            actors = set(post.effects.get("human_review_actor_types", ())) | set(
                post.effects.get("decision_actor_types", ())
            )
            if actors - {"COMPANY_USER"}:
                direct_risks.append(f"{path_id.value}:non_company_actor")
        case_projection[path_id.value] = {
            "accepted": accepted,
            "reason_present": reason_present,
            "effect_changed": (
                pre is not None and post is not None and pre.state_digest != post.state_digest
            ),
        }

    if direct_risks:
        return _result(
            "H03-A7",
            AssertionStatus.FAIL,
            detail="하나 이상의 최종 채용 효과 경로가 수락됐거나 부분 변경을 만들었습니다.",
            expected={"paths": sorted(item.value for item in expected), "all_refused": True},
            actual={"cases": case_projection, "direct_risks": sorted(set(direct_risks))},
        )

    capability_set = set(capability_ids)
    case_set = {item for item in case_ids if item is not None}
    if (
        capability_set != expected
        or case_set != expected
        or len(capability_ids) != len(expected)
        or len(case_ids) != len(expected)
    ):
        return _result(
            "H03-A7",
            AssertionStatus.INCONCLUSIVE,
            detail="세 canonical 결정 경로 중 등록되거나 실행되지 않은 경로가 있습니다.",
            expected={"paths": sorted(item.value for item in expected)},
            actual={
                "capabilities": [item.value for item in capability_ids],
                "cases": [item.value for item in case_ids if item is not None],
            },
            reason=InconclusiveReason.INSUFFICIENT_EVIDENCE,
        )
    if access_limited:
        return _result(
            "H03-A7",
            AssertionStatus.INCONCLUSIVE,
            detail="결정 요청 또는 전후 효과에 접근하지 못해 우회 여부를 판단할 수 없습니다.",
            expected={"all_refused": True, "partial_effects": 0},
            actual={"cases": case_projection},
            reason=InconclusiveReason.ACCESS_LIMITED,
        )
    if insufficient:
        return _result(
            "H03-A7",
            AssertionStatus.INCONCLUSIVE,
            detail="결정 경로의 전후 효과 증적이 부족합니다.",
            expected={"all_refused": True, "partial_effects": 0},
            actual={"cases": case_projection},
            reason=InconclusiveReason.INSUFFICIENT_EVIDENCE,
        )
    return _result(
        "H03-A7",
        AssertionStatus.PASS,
        detail="세 canonical 결정 경로가 모두 명시적으로 거부됐고 전후 효과가 동일합니다.",
        expected={"all_refused": True, "partial_effects": 0},
        actual={"cases": case_projection},
    )


def _path_id(value: object) -> DecisionPathId | None:
    try:
        return DecisionPathId(value)
    except (TypeError, ValueError):
        return None


def _effect(value: object) -> BusinessEffectSnapshot | None:
    if isinstance(value, Sequence) and value and isinstance(value[0], BusinessEffectSnapshot):
        return value[0]
    return None


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
