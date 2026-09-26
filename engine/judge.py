"""Evidence-only generic and H-03 judgement rules."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from engine.models import (
    AssertionResult,
    AssertionStatus,
    EvidenceArtifact,
    Finding,
    InconclusiveReason,
    IntegrityStatus,
    Judgement,
    Observation,
    Presence,
    RuleResult,
    Run,
    RunState,
    Verdict,
)
from engine.observations import conflicting_dimensions

_UNIT = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_duration(text: str) -> timedelta:
    value, unit = text[:-1], text[-1]
    if unit not in _UNIT:
        raise ValueError(f"unknown duration unit: {text}")
    return timedelta(seconds=float(value) * _UNIT[unit])


class ObservationSet:
    def __init__(self, observations: Sequence[Observation]) -> None:
        self.rows = tuple(observations)
        self._by_key: dict[str, list[Observation]] = defaultdict(list)
        for observation in observations:
            self._by_key[observation.key].append(observation)

    def latest(self, key: str, *, step_id: str | None = None) -> Observation | None:
        rows = self._by_key.get(key, [])
        if step_id:
            rows = [row for row in rows if row.step_id == step_id]
        return rows[-1] if rows else None

    def actual(self, key: str, *, step_id: str | None = None) -> Any:
        row = self.latest(key, step_id=step_id)
        if row is None or row.presence is Presence.UNAVAILABLE:
            return _Missing
        if row.presence is Presence.ABSENT:
            return None
        return row.value


class _MissingType:
    pass


_Missing = _MissingType()


def _generic_rule(rule: dict[str, Any], observations: ObservationSet) -> RuleResult:
    rule_type = rule["type"]
    if rule_type == "state_equals":
        key = rule["subject"]
        actual = observations.actual(key)
        if actual is _Missing:
            return RuleResult(
                rule_type=rule_type,
                passed=None,
                detail=f"{key} 관찰값 없음",
                missing_keys=(key,),
            )
        expected = rule["equals"]
        return RuleResult(
            rule_type=rule_type,
            passed=type(actual) is type(expected) and actual == expected,
            detail=f"{key}: 기대 {expected!r}, 관찰 {actual!r}",
            used_keys=(key,),
        )
    if rule_type in {"event_order", "time_limit"}:
        before = rule.get("before", rule.get("from"))
        after = rule.get("after", rule.get("to"))
        first = observations.latest(before)
        second = observations.latest(after)
        if first is None or second is None:
            missing = tuple(key for key, row in ((before, first), (after, second)) if row is None)
            return RuleResult(
                rule_type=rule_type,
                passed=None,
                detail=f"발생 시각 없음: {', '.join(missing)}",
                missing_keys=missing,
            )
        if rule_type == "event_order":
            strict = rule.get("strict", True)
            passed = (
                first.observed_at < second.observed_at
                if strict
                else first.observed_at <= second.observed_at
            )
        else:
            passed = second.observed_at - first.observed_at <= parse_duration(rule["within"])
        return RuleResult(
            rule_type=rule_type,
            passed=passed,
            detail=f"{before}={first.observed_at.isoformat()}, {after}={second.observed_at.isoformat()}",
            used_keys=(before, after),
        )
    if rule_type == "fields_present":
        present = tuple(rule.get("present", ()))
        absent = tuple(rule.get("absent", ()))
        missing: list[str] = []
        failed: list[str] = []
        for key in present:
            actual = observations.latest(key)
            if actual is None or actual.presence is Presence.UNAVAILABLE:
                missing.append(key)
            elif actual.presence is Presence.ABSENT:
                failed.append(f"{key} 없음(있어야 함)")
        for key in absent:
            actual = observations.latest(key)
            if actual is None or actual.presence is Presence.UNAVAILABLE:
                missing.append(key)
            elif actual.presence is Presence.PRESENT:
                failed.append(f"{key} 존재(없어야 함)")
        if missing:
            return RuleResult(
                rule_type=rule_type,
                passed=None,
                detail=f"확인 불가: {', '.join(missing)}",
                used_keys=present + absent,
                missing_keys=tuple(missing),
            )
        return RuleResult(
            rule_type=rule_type,
            passed=not failed,
            detail="; ".join(failed) if failed else "필수 항목 충족, 금지 항목 부재",
            used_keys=present + absent,
        )
    raise ValueError(f"unknown rule type: {rule_type}")


RULES = frozenset({"state_equals", "event_order", "time_limit", "fields_present"})


def judge(
    run: Run,
    rules: Sequence[dict[str, Any]],
    observations: Sequence[Observation],
    *,
    decided_at: datetime,
    no_test_target: bool = False,
    access_limited: bool = False,
) -> Judgement:
    """Generic rule evaluator retained for future N/E scenarios."""
    if no_test_target:
        return Judgement(
            run_id=run.run_id,
            scenario_id=run.scenario_id,
            verdict=Verdict.INCONCLUSIVE,
            reason_code=InconclusiveReason.NO_TEST_TARGET,
            decided_at=decided_at,
            summary="대상 기능이 존재하지 않아 시험할 수 없음",
        )
    if access_limited:
        return Judgement(
            run_id=run.run_id,
            scenario_id=run.scenario_id,
            verdict=Verdict.INCONCLUSIVE,
            reason_code=InconclusiveReason.ACCESS_LIMITED,
            decided_at=decided_at,
            summary="허용된 연결 방식으로 관찰할 수 없음",
        )
    conflicts = conflicting_dimensions(observations)
    if conflicts:
        keys = sorted({dimension[-1] for dimension in conflicts})
        return Judgement(
            run_id=run.run_id,
            scenario_id=run.scenario_id,
            verdict=Verdict.INCONCLUSIVE,
            reason_code=InconclusiveReason.EVIDENCE_CONFLICT,
            decided_at=decided_at,
            missing_evidence=tuple(keys),
            summary=f"관찰 결과 충돌: {', '.join(keys)}",
        )
    view = ObservationSet(observations)
    results = [_generic_rule(rule, view) for rule in rules]
    if any(result.passed is False for result in results):
        return Judgement(
            run_id=run.run_id,
            scenario_id=run.scenario_id,
            verdict=Verdict.FAIL,
            decided_at=decided_at,
            summary=" / ".join(result.detail for result in results if result.passed is False),
        )
    missing = tuple(sorted({key for result in results for key in result.missing_keys}))
    if missing:
        return Judgement(
            run_id=run.run_id,
            scenario_id=run.scenario_id,
            verdict=Verdict.INCONCLUSIVE,
            reason_code=InconclusiveReason.INSUFFICIENT_EVIDENCE,
            decided_at=decided_at,
            missing_evidence=missing,
            summary=f"증적 미확보: {', '.join(missing)}",
        )
    return Judgement(
        run_id=run.run_id,
        scenario_id=run.scenario_id,
        verdict=Verdict.PASS,
        decided_at=decided_at,
        summary="모든 규칙 충족",
    )


ASSERTION_EVIDENCE: dict[str, tuple[str, ...]] = {
    "H03-A1": ("EV-02", "EV-03"),
    "H03-A2": ("EV-03", "EV-04"),
    "H03-A3": ("EV-05",),
    "H03-A4": ("EV-01", "EV-06"),
    "H03-A5": ("EV-07",),
    "H03-A6": ("EV-08",),
}


def judge_h03(
    run: Run,
    observations: Sequence[Observation],
    artifacts: Sequence[EvidenceArtifact],
    *,
    integrity_ok: bool = True,
    unverified_scope: Sequence[str] = (
        "reporting retry exhaustion and DLQ",
        "generic stage-move bypass",
        "post-recovery idempotency",
    ),
) -> Judgement:
    view = ObservationSet(observations)
    artifacts_by_evidence: dict[str, list[EvidenceArtifact]] = defaultdict(list)
    for artifact in artifacts:
        for evidence_id in artifact.evidence_requirement_ids:
            artifacts_by_evidence[evidence_id].append(artifact)
    conflicts = conflicting_dimensions(observations)
    conflict_keys = {dimension[-1] for dimension in conflicts}

    results = (
        _a1(view, artifacts_by_evidence, conflict_keys),
        _a2(view, artifacts_by_evidence, conflict_keys),
        _a3(view, artifacts_by_evidence, conflict_keys),
        _a4(view, artifacts_by_evidence, conflict_keys),
        _a5(view, artifacts_by_evidence, conflict_keys),
        _a6(view, artifacts_by_evidence, conflict_keys),
    )
    findings: list[Finding] = []
    for result in results:
        if result.status is AssertionStatus.FAIL:
            findings.append(
                Finding(
                    code=f"{result.assertion_id}_FAILED",
                    severity="HIGH",
                    detail=result.detail,
                    assertion_id=result.assertion_id,
                    artifact_ids=result.artifact_ids,
                )
            )
    processing = view.actual("report.processing_recovery", step_id="restore-environment")
    if processing in {"FAILED", "TIMEOUT"}:
        findings.append(
            Finding(
                code="REPORT_PROCESSING_RECOVERY_INCOMPLETE",
                severity="MEDIUM",
                detail=f"환경 복구 후 리포트 처리 결과: {processing}",
                assertion_id="H03-A6",
            )
        )

    all_required = {f"EV-{index:02d}" for index in range(1, 10)}
    missing_evidence = sorted(
        evidence_id
        for evidence_id in all_required
        if not artifacts_by_evidence[evidence_id]
        or any(
            artifact.integrity_status is not IntegrityStatus.VERIFIED
            for artifact in artifacts_by_evidence[evidence_id]
        )
    )
    if not integrity_ok:
        missing_evidence.append("BUNDLE_INTEGRITY")

    safety_inconclusive = any(
        result.status is AssertionStatus.INCONCLUSIVE
        for result in results
        if result.assertion_id in {"H03-A1", "H03-A6"}
    )
    if run.state in {RunState.ABORTED, RunState.RESTORE_FAILED} or safety_inconclusive:
        verdict = Verdict.INCONCLUSIVE
        reason = InconclusiveReason.INSUFFICIENT_EVIDENCE
        summary = "시험 유효성 또는 안전한 환경 복구를 확인하지 못했습니다."
    elif conflict_keys:
        verdict = Verdict.INCONCLUSIVE
        reason = InconclusiveReason.EVIDENCE_CONFLICT
        summary = f"같은 관찰 차원의 증적이 충돌합니다: {', '.join(sorted(conflict_keys))}"
    elif any(result.status is AssertionStatus.FAIL for result in results):
        verdict = Verdict.FAIL
        reason = None
        summary = next(result.detail for result in results if result.status is AssertionStatus.FAIL)
    elif missing_evidence or any(
        result.status is AssertionStatus.INCONCLUSIVE for result in results
    ):
        verdict = Verdict.INCONCLUSIVE
        reason = InconclusiveReason.INSUFFICIENT_EVIDENCE
        summary = "필수 관찰 또는 증적이 부족해 결론을 확정할 수 없습니다."
    else:
        verdict = Verdict.PASS
        reason = None
        summary = "리포트 장애 중 결정 안전성과 환경 복구가 모두 확인되었습니다."
    return Judgement(
        run_id=run.run_id,
        scenario_id=run.scenario_id,
        verdict=verdict,
        reason_code=reason,
        assertion_results=results,
        findings=tuple(findings),
        missing_evidence=tuple(dict.fromkeys(missing_evidence)),
        unverified_scope=tuple(unverified_scope),
        summary=summary,
    )


def _evidence(
    evidence_ids: Sequence[str],
    by_evidence: dict[str, list[EvidenceArtifact]],
) -> tuple[UUID, ...]:
    return tuple(
        artifact.artifact_id
        for evidence_id in evidence_ids
        for artifact in by_evidence[evidence_id]
    )


def _required_missing(
    keys: Sequence[str],
    view: ObservationSet,
    conflicts: set[str],
) -> InconclusiveReason | None:
    if any(key in conflicts for key in keys):
        return InconclusiveReason.EVIDENCE_CONFLICT
    if any(
        view.latest(key) is None or view.latest(key).presence is Presence.UNAVAILABLE
        for key in keys
    ):
        return InconclusiveReason.INSUFFICIENT_EVIDENCE
    return None


def _result(
    assertion_id: str,
    status: AssertionStatus,
    expected: Any,
    actual: Any,
    detail: str,
    view: ObservationSet,
    keys: Sequence[str],
    by_evidence: dict[str, list[EvidenceArtifact]],
    reason: InconclusiveReason | None = None,
) -> AssertionResult:
    observations = tuple(
        row.observation_id for key in keys if (row := view.latest(key)) is not None
    )
    return AssertionResult(
        assertion_id=assertion_id,
        subject_ref="candidate-01",
        status=status,
        expected=expected,
        actual=actual,
        observation_ids=observations,
        artifact_ids=_evidence(ASSERTION_EVIDENCE[assertion_id], by_evidence),
        reason_code=reason,
        detail=detail,
        source_requirements=(assertion_id,),
    )


def _a1(view, evidence, conflicts) -> AssertionResult:
    keys = ("fault.marker.applied", "fault.effect.receipt_match")
    reason = _required_missing(keys, view, conflicts)
    actual = {key: view.actual(key) for key in keys}
    if reason:
        return _result(
            "H03-A1",
            AssertionStatus.INCONCLUSIVE,
            {key: True for key in keys},
            actual,
            "장애의 실제 발동을 확인하지 못했습니다.",
            view,
            keys,
            evidence,
            reason,
        )
    passed = all(actual[key] is True for key in keys)
    status = AssertionStatus.PASS if passed else AssertionStatus.INCONCLUSIVE
    return _result(
        "H03-A1",
        status,
        {key: True for key in keys},
        actual,
        "장애 적용 marker와 일치하는 worker receipt가 확인되었습니다."
        if passed
        else "장애 적용 또는 실제 발동이 확인되지 않았습니다.",
        view,
        keys,
        evidence,
        None if passed else InconclusiveReason.INSUFFICIENT_EVIDENCE,
    )


def _a2(view, evidence, conflicts) -> AssertionResult:
    keys = (
        "report.api.presence",
        "report.api.status",
        "report.ui.ready_content_visible",
        "report.ui.status_class",
    )
    reason = _required_missing(keys, view, conflicts)
    actual = {key: view.actual(key) for key in keys}
    if reason:
        return _result(
            "H03-A2",
            AssertionStatus.INCONCLUSIVE,
            "failed_or_delayed",
            actual,
            "담당자 표시 상태를 평가할 수 없습니다.",
            view,
            keys,
            evidence,
            reason,
        )
    passed = (
        actual["report.api.presence"] == "ABSENT"
        and actual["report.ui.ready_content_visible"] is False
        and actual["report.ui.status_class"] in {"failed", "delayed", "failed_or_delayed"}
    )
    return _result(
        "H03-A2",
        AssertionStatus.PASS if passed else AssertionStatus.FAIL,
        "failed_or_delayed",
        actual,
        "리포트 미준비 상태와 지연/실패가 담당자에게 드러납니다."
        if passed
        else "담당자 화면이 실패 또는 장기 지연을 명확히 드러내지 않습니다.",
        view,
        keys,
        evidence,
    )


def _a3(view, evidence, conflicts) -> AssertionResult:
    keys = (
        "decision.attempt.accepted",
        "decision.attempt.reason_present",
        "decision.attempt.reason_code",
    )
    reason = _required_missing(keys, view, conflicts)
    actual = {key: view.actual(key) for key in keys}
    if reason:
        return _result(
            "H03-A3",
            AssertionStatus.INCONCLUSIVE,
            {"accepted": False, "reason_code": "REPORT_NOT_AVAILABLE"},
            actual,
            "최종결정 응답을 평가할 수 없습니다.",
            view,
            keys,
            evidence,
            reason,
        )
    passed = (
        actual["decision.attempt.accepted"] is False
        and actual["decision.attempt.reason_present"] is True
        and actual["decision.attempt.reason_code"] == "REPORT_NOT_AVAILABLE"
    )
    return _result(
        "H03-A3",
        AssertionStatus.PASS if passed else AssertionStatus.FAIL,
        {"accepted": False, "reason_code": "REPORT_NOT_AVAILABLE"},
        actual,
        "리포트 부재 이유와 함께 최종결정이 거부되었습니다."
        if passed
        else "최종결정이 수락되었거나 대상이 리포트 부재 이유를 명시하지 않았습니다.",
        view,
        keys,
        evidence,
    )


def _a4(view, evidence, conflicts) -> AssertionResult:
    keys = (
        "invitation.status",
        "recruiting.stage_id",
        "pipeline.row_version",
        "final_decision.count",
        "final_decision.latest_actor_type",
    )
    if any(key in conflicts for key in keys):
        return _result(
            "H03-A4",
            AssertionStatus.INCONCLUSIVE,
            "baseline equals post",
            {},
            "상태 증적이 충돌합니다.",
            view,
            keys,
            evidence,
            InconclusiveReason.EVIDENCE_CONFLICT,
        )
    baseline = {key: view.actual(key, step_id="capture-baseline") for key in keys}
    post = {key: view.actual(key, step_id="capture-post-decision-state") for key in keys}
    if any(value is _Missing for value in (*baseline.values(), *post.values())):
        return _result(
            "H03-A4",
            AssertionStatus.INCONCLUSIVE,
            baseline,
            post,
            "기준선 또는 결정 시도 후 상태가 부족합니다.",
            view,
            keys,
            evidence,
            InconclusiveReason.INSUFFICIENT_EVIDENCE,
        )
    passed = all(
        type(baseline[key]) is type(post[key]) and baseline[key] == post[key] for key in keys
    )
    return _result(
        "H03-A4",
        AssertionStatus.PASS if passed else AssertionStatus.FAIL,
        baseline,
        post,
        "거부된 결정 시도 뒤 부분 변경이 없습니다."
        if passed
        else "거부된 결정 시도 뒤 상태 일부가 변경되었습니다.",
        view,
        keys,
        evidence,
    )


def _a5(view, evidence, conflicts) -> AssertionResult:
    keys = (
        "invitation.status",
        "recruiting.stage_id",
        "pipeline.row_version",
        "final_decision.count",
        "final_decision.latest_actor_type",
    )
    rows = {key: view.actual(key, step_id="observe-automatic-decision-window") for key in keys}
    if any(value is _Missing for value in rows.values()) or any(key in conflicts for key in keys):
        reason = (
            InconclusiveReason.EVIDENCE_CONFLICT
            if any(key in conflicts for key in keys)
            else InconclusiveReason.INSUFFICIENT_EVIDENCE
        )
        return _result(
            "H03-A5",
            AssertionStatus.INCONCLUSIVE,
            {"final_decision.count": 0},
            rows,
            "자동결정 부재 관찰을 완료하지 못했습니다.",
            view,
            keys,
            evidence,
            reason,
        )
    passed = rows["final_decision.count"] == 0 and rows["final_decision.latest_actor_type"] is None
    return _result(
        "H03-A5",
        AssertionStatus.PASS if passed else AssertionStatus.FAIL,
        {"final_decision.count": 0, "latest_actor": None},
        rows,
        "관찰 창에 자동 최종결정이 없습니다."
        if passed
        else "사람 요청 없는 최종결정 또는 상태 변화가 관찰되었습니다.",
        view,
        keys,
        evidence,
    )


def _a6(view, evidence, conflicts) -> AssertionResult:
    keys = ("fault.environment_restore", "report.processing_recovery")
    reason = _required_missing(keys, view, conflicts)
    actual = {key: view.actual(key) for key in keys}
    if reason:
        return _result(
            "H03-A6",
            AssertionStatus.INCONCLUSIVE,
            "SUCCEEDED",
            actual,
            "환경 복구를 확인하지 못했습니다.",
            view,
            keys,
            evidence,
            reason,
        )
    passed = actual["fault.environment_restore"] == "SUCCEEDED"
    return _result(
        "H03-A6",
        AssertionStatus.PASS if passed else AssertionStatus.INCONCLUSIVE,
        "SUCCEEDED",
        actual,
        "marker 비활성 및 worker 정상 상태가 확인되었습니다."
        if passed
        else "환경이 안전하게 복구되었는지 확인하지 못했습니다.",
        view,
        keys,
        evidence,
        None if passed else InconclusiveReason.INSUFFICIENT_EVIDENCE,
    )
