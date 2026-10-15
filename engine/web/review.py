"""Read-only, versioned presentation of recorded facts; never a verdict calculator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TITLES = {
    "E-01": "AI 점수의 인용 근거가 유효한가?",
    "E-02": "평가 기준이 바뀌어도 과거 결과를 설명할 수 있는가?",
}
RULES = {
    "E01-A1": ("잘못된 인용 차단", "잘못된 인용과 해당 항목의 점수를 비우고 사유를 남깁니다."),
    "E01-A2": ("정상 인용 저장", "유효한 점수와 같은 평가 항목의 근거를 정상 저장합니다."),
    "E01-A3": ("근거 제거 후 표시", "근거가 사라진 항목은 조회에서 근거 부족을 드러냅니다."),
    "E01-A4": ("근거 복원 확인", "근거 복원 후 조회·저장 기록이 제거 전과 같습니다."),
    "E02-A1": ("당시 입력·기준 보존", "첫 보고서가 생성 당시 입력·가중치·버전을 보존합니다."),
    "E02-A2": ("기준 변경 후 과거 결과 보존", "새 기준 발행과 새 평가 뒤에도 첫 보고서가 바뀌지 않습니다."),
    "E02-A3": ("저장 입력으로 점수 재계산", "저장된 입력으로 계산한 점수가 저장값·조회값과 일치합니다."),
}
E01_CASES = [
    ("empty", "EMPTY", "인용 근거 없음", "해당 점수와 인용을 비우고 사유를 남김", "E01-A1"),
    ("nonexistent", "NONEXISTENT", "존재하지 않는 근거", "잘못된 인용과 해당 점수를 비움", "E01-A1"),
    ("other-applicant", "OTHER_APPLICANT", "다른 지원자의 근거", "잘못된 인용과 해당 점수를 비움", "E01-A1"),
    ("other-criterion", "OTHER_CRITERION", "다른 평가 항목의 근거", "잘못된 인용과 해당 점수를 비움", "E01-A1"),
    ("valid", "VALID", "정상 인용 (대조)", "점수와 해당 항목의 근거를 정상 저장", "E01-A2"),
]
PLANS = {
    "E-01": {
        "conditions": [case[2] for case in E01_CASES] + ["인용한 근거 자료 제거", "제거한 근거 자료 복원"],
        "stages": [
            {"title": "시험 전 준비", "text": "합성 지원자와 정상 리포트를 준비하고 저장·조회 상태를 기록합니다."},
            {"title": "조건 적용·관찰", "text": "잘못된 인용 4유형과 정상 인용을 대조하고, 저장된 근거를 제거해 반응을 확인합니다."},
            {"title": "복원·정리", "text": "근거를 복원해 원래 상태와 비교하고, 시험 데이터를 정리합니다."},
        ],
    },
    "E-02": {
        "conditions": ["첫 평가의 입력·가중치·버전 보존", "새 기준 버전 발행 후 과거 결과 확인", "저장 입력으로 총점 재계산"],
        "stages": [
            {"title": "시험 전 준비", "text": "첫 기준으로 합성 지원자를 평가하고 보고서와 평가 입력을 기록합니다."},
            {"title": "조건 적용·관찰", "text": "새 기준을 발행하고 두 번째 지원자를 평가한 뒤 첫 결과와 점수 계산을 확인합니다."},
            {"title": "복원·정리", "text": "시험용 데이터 정리와 다른 포지션의 상태 보존을 확인합니다."},
        ],
    },
}


def test_plan(scenario_id: str, definition: dict[str, Any] | None) -> dict[str, Any]:
    definition = definition or {}
    if scenario_id in PLANS:
        return {"title": TITLES[scenario_id], **PLANS[scenario_id]}
    return {
        "title": definition.get("title") or scenario_id,
        "conditions": [item.get("description", "") for item in definition.get("assertions", [])],
        "stages": [
            {"title": "시험 전 준비", "text": "합성 대상을 준비하고 시험 전 상태를 기록합니다."},
            {"title": "조건 적용·관찰", "text": "정의된 시험 조건을 적용하고 대상 서비스의 반응을 기록합니다."},
            {"title": "복원·정리", "text": "적용한 조건을 해제하고 복구·정리 결과를 확인합니다."},
        ],
    }


def rule_display(assertion: dict[str, Any]) -> dict[str, str]:
    rule = assertion["assertion_id"]
    label, expected = RULES.get(rule, (rule, assertion.get("description") or "원본 규칙의 기대 동작 확인"))
    detail = assertion.get("detail")
    actual = assertion.get("actual")
    observed = detail if detail else ("관찰 기록 없음" if actual is None else json.dumps(actual, ensure_ascii=False))
    return {"label": label, "expected": expected, "observed": observed}


def _sources(refs: list[str], evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_ref = {item["ref"]: item for item in evidence}
    labels = {
        "file:citation-cases.jsonl": "조건별 인용 처리 결과",
        "file:model-emissions.jsonl": "시험에 넣은 고정 모델 출력",
        "file:report-records.jsonl": "처리 전후 리포트 저장 기록",
        "file:report-reads.jsonl": "근거 제거 전·후와 복원 후 조회 기록",
        "file:change-injections.jsonl": "근거 제거·복원 적용 기록",
        "file:subjects.json": "합성 시험 대상 기록",
    }
    ordered = list(dict.fromkeys(refs))
    ordered.sort(key=lambda ref: list(labels).index(ref) if ref in labels else len(labels))
    return [
        {"ref": ref, "label": labels.get(ref, by_ref[ref]["evidence_name"]), "sha256": by_ref[ref].get("sha256")}
        for ref in ordered if ref in by_ref
    ]


def _rows(path: Path) -> list[dict[str, Any]]:
    try:
        if path.stat().st_size > 256 * 1024:
            return []
        return [row for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and isinstance(row := json.loads(line), dict)]
    except (OSError, ValueError, UnicodeError):
        return []


def build_review(
    scenario_id: str, definition: dict[str, Any], assertions: list[dict[str, Any]],
    bundle: Path, evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    by_rule = {item["assertion_id"]: item for item in assertions}
    conditions: list[dict[str, Any]] = []
    if scenario_id == "E-01":
        # These files have already passed verify_bundle. Only selected non-sensitive facts are projected.
        cases = {row.get("mode"): row for row in _rows(bundle / "citation-cases.jsonl")}
        for row_id, mode, label, expected, rule in E01_CASES:
            assertion = by_rule.get(rule, {})
            source = cases.get(mode, {})
            facts = {key: source[key] for key in ("mode", "outcome", "rationale_present", "invalid_id_present") if key in source}
            outcome = source.get("outcome")
            if outcome == "EMPTIED":
                observed = "점수·인용 비움"
                if source.get("rationale_present") is True:
                    observed += ", 사유 보존"
            elif outcome == "STORED_VALID":
                observed = "유효한 점수·인용 저장"
            elif outcome is not None:
                observed = f"기대와 다른 처리 기록: {outcome}"
            else:
                observed = "조건별 관찰 기록 없음"
            if source.get("invalid_id_present") is True:
                observed += " · 잘못된 인용이 기록에 남음"
            conditions.append({
                "id": row_id, "title": label, "expected": expected, "observed": observed,
                "group": "인용 근거를 바꿔 넣은 시험", "assertion_id": rule,
                "rule_status": assertion.get("status"), "recorded": outcome is not None,
                "facts": facts, "sources": _sources(assertion.get("evidence_refs", []), evidence),
            })
        for row_id, rule, title in [
            ("removed", "E01-A3", "인용한 근거 자료 제거"),
            ("restored", "E01-A4", "제거한 근거 자료 복원"),
        ]:
            assertion = by_rule.get(rule, {})
            facts = assertion.get("actual") or {}
            if row_id == "removed":
                if facts.get("unexposed") or facts.get("changed_without_indicator"):
                    observed = "일부 항목에서 근거 부족이 드러나지 않거나 다른 항목도 변경됨"
                elif facts.get("indicators") and "unexposed" in facts:
                    observed = "영향받은 항목에 근거 부족 표시, 다른 항목 보존"
                else:
                    observed = assertion.get("detail") or "관찰 기록 없음"
                safe_facts = {key: facts[key] for key in ("unexposed", "changed_without_indicator") if key in facts}
            else:
                observed = (
                    "조회·저장 기록이 제거 전과 같음"
                    if facts.get("read_equal") is True and facts.get("record_equal") is True
                    else assertion.get("detail") or "관찰 기록 없음"
                )
                safe_facts = {key: facts[key] for key in ("read_equal", "record_equal") if key in facts}
            conditions.append({
                "id": row_id, "title": title, "expected": RULES[rule][1], "observed": observed,
                "group": "저장 후 근거 자료를 바꾼 시험", "assertion_id": rule,
                "rule_status": assertion.get("status"), "recorded": bool(facts),
                "facts": safe_facts, "sources": _sources(assertion.get("evidence_refs", []), evidence),
            })
    else:
        for assertion in assertions:
            display = rule_display(assertion)
            conditions.append({
                "id": assertion["assertion_id"], "title": display["label"],
                "expected": display["expected"], "observed": display["observed"],
                "group": "시험 조건과 관찰 결과", "assertion_id": assertion["assertion_id"],
                "rule_status": assertion["status"], "recorded": assertion.get("actual") is not None,
                "facts": assertion.get("actual"), "sources": _sources(assertion.get("evidence_refs", []), evidence),
            })
    return {
        "title": TITLES.get(scenario_id, definition.get("title") or scenario_id),
        "summary": (
            "잘못된 인용 4유형·정상 인용 대조와, 근거 제거·복원 후의 실제 관찰을 확인하세요."
            if scenario_id == "E-01" else definition.get("intent") or "이 실행에서 기록한 기대 동작과 실제 관찰을 확인하세요."
        ),
        "conditions": conditions, "rule_count": len(assertions),
        "passed_rule_count": sum(item["status"] == "PASS" for item in assertions),
    }
