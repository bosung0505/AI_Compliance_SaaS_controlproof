"""판정 엔진.

규칙 타입은 네 가지뿐이다. 새 시나리오가 이 넷으로 표현되지 않으면
그때 다섯 번째를 추가한다 — 그것이 엔진을 고쳐야 하는 몇 안 되는 사유다.

핵심 원칙: 근거가 부족하면 PASS 가 아니라 INCONCLUSIVE 다.
  - 관찰했고 기대와 다름        -> FAIL
  - 관찰 자체를 못 함            -> INCONCLUSIVE (INSUFFICIENT_EVIDENCE)
  - 같은 키에 모순된 관찰이 있음 -> INCONCLUSIVE (EVIDENCE_CONFLICT)
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from engine.models import (
    InconclusiveReason,
    Judgement,
    Observation,
    RuleResult,
    Run,
    Verdict,
)

_UNIT = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_duration(text: str) -> timedelta:
    """'5m', '2h', '90s' -> timedelta"""
    value, unit = text[:-1], text[-1]
    if unit not in _UNIT:
        raise ValueError(f"unknown duration unit: {text}")
    return timedelta(seconds=float(value) * _UNIT[unit])


class ObservationSet:
    """한 실행에서 수집한 관찰값 모음.

    같은 키에 서로 다른 값이 들어오면 충돌로 기록한다. 덮어쓰지 않는다.
    """

    def __init__(self, observations: Sequence[Observation]) -> None:
        self._by_key: dict[str, list[Observation]] = {}
        for obs in observations:
            self._by_key.setdefault(obs.key, []).append(obs)

    def has(self, key: str) -> bool:
        return key in self._by_key

    def conflicts(self, key: str) -> bool:
        rows = self._by_key.get(key, [])
        if len(rows) < 2:
            return False
        return len({(r.value, r.absent) for r in rows}) > 1

    def one(self, key: str) -> Observation | None:
        rows = self._by_key.get(key)
        return rows[0] if rows else None

    def value(self, key: str) -> Any:
        obs = self.one(key)
        return None if obs is None else obs.value

    def is_absent(self, key: str) -> bool | None:
        """조회했고 없으면 True, 있으면 False, 조회 못 했으면 None."""
        obs = self.one(key)
        return None if obs is None else obs.absent

    def when(self, key: str) -> datetime | None:
        obs = self.one(key)
        return None if obs is None else obs.occurred_at


# --- 규칙 4타입 -------------------------------------------------------------


def _state_equals(rule: dict, obs: ObservationSet) -> RuleResult:
    key = rule["subject"]
    expected = rule["equals"]
    if not obs.has(key):
        return RuleResult(
            rule_type="state_equals", passed=None,
            detail=f"{key} 관찰값 없음", missing_keys=(key,),
        )
    actual = obs.value(key)
    ok = actual == expected
    return RuleResult(
        rule_type="state_equals", passed=ok,
        detail=f"{key}: 기대 {expected!r}, 관찰 {actual!r}",
        used_keys=(key,),
    )


def _event_order(rule: dict, obs: ObservationSet) -> RuleResult:
    before, after = rule["before"], rule["after"]
    strict = rule.get("strict", True)
    missing = tuple(k for k in (before, after) if obs.when(k) is None)
    if missing:
        return RuleResult(
            rule_type="event_order", passed=None,
            detail=f"발생 시각 없음: {', '.join(missing)}", missing_keys=missing,
        )
    t1, t2 = obs.when(before), obs.when(after)
    ok = t1 < t2 if strict else t1 <= t2
    sign = "<" if strict else "<="
    return RuleResult(
        rule_type="event_order", passed=ok,
        detail=f"{before}({t1.isoformat()}) {sign} {after}({t2.isoformat()})",
        used_keys=(before, after),
    )


def _time_limit(rule: dict, obs: ObservationSet) -> RuleResult:
    start, end = rule["from"], rule["to"]
    limit = parse_duration(rule["within"])
    missing = tuple(k for k in (start, end) if obs.when(k) is None)
    if missing:
        return RuleResult(
            rule_type="time_limit", passed=None,
            detail=f"발생 시각 없음: {', '.join(missing)}", missing_keys=missing,
        )
    elapsed = obs.when(end) - obs.when(start)
    ok = elapsed <= limit
    return RuleResult(
        rule_type="time_limit", passed=ok,
        detail=f"{start}→{end} {elapsed} (제한 {limit})",
        used_keys=(start, end),
    )


def _fields_present(rule: dict, obs: ObservationSet) -> RuleResult:
    present = list(rule.get("present", []))
    absent = list(rule.get("absent", []))
    missing: list[str] = []
    failed: list[str] = []

    for key in present:
        state = obs.is_absent(key)
        if state is None:
            missing.append(key)
        elif state is True:
            failed.append(f"{key} 없음(있어야 함)")

    for key in absent:
        state = obs.is_absent(key)
        if state is None:
            # 없어야 할 것을 '조회하지 못한' 경우다. 없다고 단정할 수 없다.
            missing.append(key)
        elif state is False:
            failed.append(f"{key} 존재(없어야 함)")

    if missing:
        return RuleResult(
            rule_type="fields_present", passed=None,
            detail=f"확인 불가: {', '.join(missing)}",
            used_keys=tuple(present + absent), missing_keys=tuple(missing),
        )
    return RuleResult(
        rule_type="fields_present", passed=not failed,
        detail="; ".join(failed) if failed else "필수 항목 충족, 금지 항목 부재",
        used_keys=tuple(present + absent),
    )


RULES = {
    "state_equals": _state_equals,
    "event_order": _event_order,
    "time_limit": _time_limit,
    "fields_present": _fields_present,
}


# --- 판정 -------------------------------------------------------------------


def judge(
    run: Run,
    rules: Sequence[dict],
    observations: Sequence[Observation],
    *,
    decided_at: datetime,
    no_test_target: bool = False,
    access_limited: bool = False,
) -> Judgement:
    """규칙을 평가해 판정한다.

    no_test_target / access_limited 는 전제조건 점검 결과로 미리 판단된다.
    대상이 없으면 규칙을 평가하지 않는다 — 없는 것을 통과시키지 않기 위해서다.
    """
    if no_test_target:
        return Judgement(
            run_id=run.run_id, scenario_id=run.scenario_id,
            verdict=Verdict.INCONCLUSIVE,
            reason=InconclusiveReason.NO_TEST_TARGET,
            decided_at=decided_at,
            summary="대상 기능이 존재하지 않아 시험할 수 없음",
        )
    if access_limited:
        return Judgement(
            run_id=run.run_id, scenario_id=run.scenario_id,
            verdict=Verdict.INCONCLUSIVE,
            reason=InconclusiveReason.ACCESS_LIMITED,
            decided_at=decided_at,
            summary="허용된 연결 방식으로 관찰할 수 없음",
        )

    obs = ObservationSet(observations)

    conflicted = sorted({o.key for o in observations if obs.conflicts(o.key)})
    if conflicted:
        return Judgement(
            run_id=run.run_id, scenario_id=run.scenario_id,
            verdict=Verdict.INCONCLUSIVE,
            reason=InconclusiveReason.EVIDENCE_CONFLICT,
            decided_at=decided_at,
            missing_evidence=tuple(conflicted),
            summary=f"관찰 결과 충돌: {', '.join(conflicted)}",
        )

    results = [RULES[r["type"]](r, obs) for r in rules]

    # FAIL 이 INCONCLUSIVE 보다 우선한다.
    # 관찰된 실패는 다른 관찰값을 못 얻었다고 해서 사라지지 않는다.
    if any(r.passed is False for r in results):
        failed = [r.detail for r in results if r.passed is False]
        return Judgement(
            run_id=run.run_id, scenario_id=run.scenario_id,
            verdict=Verdict.FAIL, rule_results=tuple(results),
            decided_at=decided_at, summary=" / ".join(failed),
        )

    missing = tuple(sorted({k for r in results for k in r.missing_keys}))
    if missing:
        return Judgement(
            run_id=run.run_id, scenario_id=run.scenario_id,
            verdict=Verdict.INCONCLUSIVE,
            reason=InconclusiveReason.INSUFFICIENT_EVIDENCE,
            rule_results=tuple(results), missing_evidence=missing,
            decided_at=decided_at,
            summary=f"증적 미확보: {', '.join(missing)}",
        )

    return Judgement(
        run_id=run.run_id, scenario_id=run.scenario_id,
        verdict=Verdict.PASS, rule_results=tuple(results),
        decided_at=decided_at, summary="모든 규칙 충족",
    )
