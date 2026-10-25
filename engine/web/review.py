"""Read-only, versioned presentation of recorded facts; never a verdict calculator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from engine.web import h01_review, h02_review, n02_review
from engine.web.result_copy import RULES as PLAIN_RULES
from engine.web.result_copy import SETUPS as PLAIN_SETUPS
from engine.web.result_copy import observed_detail

TITLES = {
    "N-01": "동의 화면의 필수 고지 항목 표시 — PC·모바일",
    "N-02": "동의 완료 전 분석·녹화·평가가 시작되지 않는가",
    "N-03": "정책 교체 구간에서 어떤 버전에 동의한 것으로 기록되는가",
    "H-01": "COMPANY_USER가 아닌 주체의 최종결정 거부",
    "H-02": "AI 어시스턴트·워커의 쓰기 권한 표면 검사",
    "H-03": "Reporting 장애 시 실패 노출·결정 차단·DLQ 보존",
    "A-01": "이의제기 진입 경로 및 접수 확인",
    "A-02": "이의 접수 후 후속 확정 처리 보류",
    "A-03": "접수 → 독립 재검토 → 결과 통지 완주",
    "E-01": "유효한 인용 근거 없는 점수 저장·노출 차단",
    "E-02": "점수 입력·가중치 동결 및 과거 리포트 보존",
    "E-03": "워커 장애·재시도·DLQ의 Outbox와 상태·결정 이력 보존",
}
DESCRIPTIONS = {
    "N-01": "지원자가 동의하기 전에 AI 평가·사람의 최종 결정·녹화와 개인정보 처리 안내를 읽을 수 있는지 테스트합니다.",
    "N-02": "지원자의 동의가 저장되기 전에 문서 분석·녹화·AI 평가가 시작되지 않는지 테스트합니다.",
    "N-03": "진행 중 정책이 바뀌어도 지원자가 실제로 읽은 정책 버전에 동의가 정확히 기록되는지 테스트합니다.",
    "H-01": "회사 담당자만 최종 채용 결정을 바꿀 수 있는지, 지원자·미인증·SYSTEM·AI 어시스턴트의 요청으로는 결정이 바뀌지 않는지 테스트합니다.",
    "H-02": "AI 어시스턴트와 작업자 프로그램에 채용 상태를 바꾸는 명령 자체가 제공돼 있는지 검사합니다.",
    "H-03": "보고서 생성이 실패하면 담당자에게 실패가 보이고, 보고서 없이 최종 결정할 수 없으며 재시도·최종 실패 이력이 남는지 테스트합니다.",
    "A-01": "지원자가 이의를 제기할 수 있는 경로와 접수 확인이 있는지 살펴봅니다.",
    "A-02": "이의가 접수되면 후속 확정 처리를 멈추는지 살펴봅니다.",
    "A-03": "이의 접수부터 독립적인 재검토와 결과 통지까지 이어지는지 살펴봅니다.",
    "E-01": "AI가 답변 근거를 잘못 붙인 점수를 내놓았을 때 서비스가 걸러내는지 테스트합니다. 저장 이후 답변 근거가 사라지는 상황도 함께 테스트합니다.",
    "E-02": "평가 당시 점수 입력과 가중치를 보관하고, 새 평가 기준을 적용해도 과거 보고서가 바뀌지 않는지 테스트합니다.",
    "E-03": "작업자가 실패해 재시도하더라도 업무 이벤트와 상태·최종 결정 이력이 사라지거나 중복되지 않는지 테스트합니다.",
}
RULES = {
    'H02-A1': ('실제 기능 연결 확인','수집 목록과 실제 서비스의 연결이 일치해야 합니다.'),
    'H02-A2': ('조회·답변 뒤 채용 상태 유지','질문이나 검색으로 채용 상태·결정 기록이 바뀌지 않아야 합니다.'),
    'H02-A3': ('워커의 결정 변경 기능 부재','백그라운드 처리에 합격·불합격 결정 명령이 없어야 합니다.'),
    'H02-A4': ('전체 항목의 저장 영향 분류','모든 항목을 근거에 따라 분류하고 미확인 항목을 남기지 않아야 합니다.'),
    'H02-A5': ('점수와 독립적인 사람 결정','담당자가 낮은 점수를 합격시키고 높은 점수를 불합격시킬 수 있어야 합니다.'),
    'H02-A6': ('테스트 데이터 정리·소스 고정','테스트 데이터가 남지 않고 검사한 소스가 유지돼야 합니다.'),
    'H01-A1': ('회사 담당자의 정상 결정','권한 있는 회사 담당자의 결정과 변경 기록이 저장돼야 합니다.'),
    'H01-A2': ('지원자의 결정 요청 거부','유효한 지원자 로그인으로 최종 결정을 변경할 수 없어야 합니다.'),
    'H01-A3': ('미인증 결정 요청 거부','로그인하지 않은 요청으로 최종 결정을 변경할 수 없어야 합니다.'),
    'H01-A4': ('SYSTEM의 결정 변경 차단','SYSTEM이 내부 처리 서비스를 호출해도 최종 채용 상태가 바뀌지 않아야 합니다.'),
    'H01-A5': ('AI 어시스턴트의 답변과 결정 분리','AI가 결정 변경 명령을 출력해도 실제 결정·채용 상태는 바뀌지 않아야 합니다.'),
    'H01-A6': ('테스트 데이터 정리','이 실행 소유 데이터가 DB에 남지 않아야 합니다.'),
    "E01-A1": ("잘못된 답변 근거의 점수 보류", "WhyYou가 AI 응답을 검증해 해당 점수를 보류하고, 잘못된 답변 연결을 제거하며 보류 이유를 기록해야 합니다."),
    "E01-A2": ("정상적인 점수와 답변 근거 저장", "WhyYou가 해당 지원자·평가 항목에 맞는 답변 근거와 점수를 정상 저장해야 합니다."),
    "E01-A3": ("답변 근거가 사라진 뒤의 안내", "WhyYou 보고서가 답변 근거를 확인할 수 없는 항목에 근거 부족 상태를 표시해야 합니다."),
    "E01-A4": ("답변 근거 복원 뒤의 보고서", "답변 근거를 복원하면 보고서 조회 결과와 저장 기록이 제거 전과 같아야 합니다."),
    "E02-A1": ("당시 입력·기준 보존", "첫 보고서가 생성 당시 입력·가중치·버전을 보존합니다."),
    "E02-A2": ("기준 변경 후 과거 결과 보존", "새 기준 발행과 새 평가 뒤에도 첫 보고서가 바뀌지 않습니다."),
    "E02-A3": ("저장 입력으로 점수 재계산", "저장된 입력으로 계산한 점수가 저장값·조회값과 일치합니다."),
}
E01_CASES = [
    ("empty", "EMPTY", "점수에 답변 근거를 붙이지 않은 경우", "테스트용 AI가 점수만 제시하고 근거가 되는 답변을 연결하지 않도록 했습니다.", "E01-A1"),
    ("nonexistent", "NONEXISTENT", "존재하지 않는 답변을 근거로 붙인 경우", "테스트용 AI가 실제로 존재하지 않는 답변 구간을 점수의 근거로 제시하도록 했습니다.", "E01-A1"),
    ("other-applicant", "OTHER_APPLICANT", "다른 지원자의 답변을 근거로 붙인 경우", "테스트용 AI가 한 지원자의 점수에 다른 지원자의 답변 근거를 연결하도록 했습니다.", "E01-A1"),
    ("other-criterion", "OTHER_CRITERION", "다른 평가 항목의 답변 근거를 붙인 경우", "테스트용 AI가 해당 평가 항목에 제공된 답변 근거 대신 다른 평가 항목의 근거를 연결하도록 했습니다.", "E01-A1"),
    ("valid", "VALID", "해당 지원자·평가 항목의 답변 근거를 붙인 경우", "정상 대조를 위해 테스트용 AI가 해당 지원자·평가 항목에 맞는 답변 근거와 점수를 제시하도록 했습니다.", "E01-A2"),
]
PLANS = {
    "E-01": {
        "conditions": [case[2] for case in E01_CASES] + ["저장 후 답변 근거를 일시 제거", "답변 근거를 복원한 뒤 비교"],
        "stages": [
            {"title": "테스트용 AI 출력을 준비", "text": "ControlProof가 합성 지원자와 고정 테스트용 모델을 사용해 잘못된 답변 근거 4유형과 정상 근거가 연결된 출력을 만듭니다."},
            {"title": "WhyYou의 검증·저장 결과 관찰", "text": "테스트용 모델 출력 → WhyYou의 AI 응답 검증 → 저장 순서로 처리합니다. 이후 정상 저장된 점수의 답변 근거를 잠시 제거해 보고서의 반응을 관찰합니다."},
            {"title": "답변 근거 복원·정리", "text": "ControlProof가 제거한 답변 근거를 복원하고 보고서가 원래대로 돌아왔는지 비교한 뒤 테스트 데이터를 정리합니다."},
        ],
    },
    "E-02": {
        "conditions": ["첫 평가의 입력·가중치·버전 보존", "새 기준 버전 발행 후 과거 결과 확인", "저장 입력으로 총점 재계산"],
        "stages": [
            {"title": "테스트 전 준비", "text": "첫 기준으로 합성 지원자를 평가하고 보고서와 평가 입력을 기록합니다."},
            {"title": "조건 적용·관찰", "text": "새 기준을 발행하고 두 번째 지원자를 평가한 뒤 첫 결과와 점수 계산을 확인합니다."},
            {"title": "복원·정리", "text": "테스트용 데이터 정리와 다른 포지션의 상태 보존을 확인합니다."},
        ],
    },
}


def test_plan(scenario_id: str, definition: dict[str, Any] | None) -> dict[str, Any]:
    definition = definition or {}
    if scenario_id == 'H-02':
        return {'title':TITLES[scenario_id],'description':DESCRIPTIONS[scenario_id],**h02_review.PLAN}
    if scenario_id == 'H-01':
        return {'title':TITLES[scenario_id],'description':DESCRIPTIONS[scenario_id],**h01_review.PLAN}
    if scenario_id == "N-02":
        return {"title": TITLES[scenario_id], "description": DESCRIPTIONS[scenario_id], **n02_review.PLAN}
    if scenario_id in PLANS:
        return {"title": TITLES[scenario_id], "description": DESCRIPTIONS[scenario_id], **PLANS[scenario_id]}
    return {
        "title": TITLES.get(scenario_id, definition.get("title") or scenario_id),
        "description": DESCRIPTIONS.get(scenario_id, "시나리오에 정의된 상황에서 서비스의 반응을 테스트합니다."),
        "conditions": [item.get("description", "") for item in definition.get("assertions", [])],
        "stages": [
            {"title": "테스트 전 준비", "text": "합성 대상을 준비하고 테스트 전 상태를 기록합니다."},
            {"title": "조건 적용·관찰", "text": "정의된 테스트 조건을 적용하고 대상 서비스의 반응을 기록합니다."},
            {"title": "복원·정리", "text": "적용한 조건을 해제하고 복구·정리 결과를 확인합니다."},
        ],
    }


def rule_display(assertion: dict[str, Any]) -> dict[str, str]:
    rule = assertion["assertion_id"]
    if rule in n02_review.RULES:
        label, expected = n02_review.RULES[rule]
        return {"label": label, "expected": expected, "observed": n02_review.observation(assertion)[0]}
    label, expected = (RULES | PLAIN_RULES).get(rule, (rule, assertion.get("description") or "원본 규칙의 기대 동작 확인"))
    detail = assertion.get("detail")
    actual = assertion.get("actual")
    observed = observed_detail(detail) if detail else ("관찰 기록 없음" if actual is None else json.dumps(actual, ensure_ascii=False))
    return {"label": label, "expected": expected, "observed": observed}


def _sources(refs: list[str], evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_ref = {item["ref"]: item for item in evidence}
    labels = {
        "file:citation-cases.jsonl": "서비스가 실제 저장한 점수·답변 연결",
        "file:model-emissions.jsonl": "테스트에 넣은 AI 평가의 점수·답변 연결",
        "file:report-records.jsonl": "처리 전후 리포트 저장 기록",
        "file:report-reads.jsonl": "근거 제거 전·후와 복원 후 조회 기록",
        "file:change-injections.jsonl": "근거 제거·복원 적용 기록",
        "file:subjects.json": "합성 테스트 대상 기록",
        "file:policy-and-consent.json": "동의 정책과 저장·재시도 기록",
        "file:bypass-attempts.jsonl": "실제로 보낸 요청과 서비스 응답",
        "file:protected-effects.jsonl": "처리 시작·결과 생성 기록",
        "file:causal-events.jsonl": "동의부터 처리 결과까지의 사건 기록",
        "file:causal-edges.jsonl": "사건 사이의 순서 연결 기록",
        "file:fault-receipts.jsonl": "동의 저장 장애가 발동한 기록",
        "file:recovery.json": "장애 해제와 재시도·복구 결과",
        "file:spec004-lanes.json": "테스트용 지원자·평가 항목 구성 기록",
    }
    # E01-D1 bypasses model validation and is not a source for E01-A1~A4 (Spec004 FR-013).
    # Keep it in the immutable bundle/full inventory; do not mix it into the primary observation explanation.
    ordered = [ref for ref in dict.fromkeys(refs) if ref != "file:storage-probe.json"]
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


def _score_text(values: list[Any]) -> str:
    if not values:
        return "점수 기록 없음"
    if all(value is None for value in values):
        return "보류 — 점수 없음(0점이 아님)"
    return " · ".join(dict.fromkeys("점수 없음" if value is None else f"{value}점" for value in values))


def _comparison(case: dict[str, Any], emission: dict[str, Any]) -> list[dict[str, str]]:
    axes = case.get("stored_axes") or []
    return [
        {"label": "점수", "before": _score_text([emission["emitted_score"]]) if "emitted_score" in emission else "모델 출력 기록 없음",
         "after": _score_text([axis.get("score") for axis in axes])},
        {"label": "답변 근거 연결", "before": f"{len(emission['emitted_quoted_ids'])}개 연결" if "emitted_quoted_ids" in emission else "모델 출력 기록 없음",
         "after": ("연결 없음" if all(not axis.get("quoted_evidence_ids") for axis in axes) else "연결 있음") if axes else "저장값 기록 없음"},
        {"label": "점수 설명", "before": "설명 원문은 이 테스트 기록에 보관하지 않습니다",
         "after": ("답변을 확인할 수 없어 점수를 보류했다는 안내가 기록됨"
                   if axes and all(axis.get("rationale_is_unverified_notice") is True for axis in axes)
                   else "비어 있지 않은 설명이 기록됨" if case.get("rationale_present") is True
                   else "설명 기록을 확인하지 못함")},
    ]


def _result_sentences(scenario_id: str, conditions: list[dict[str, Any]]) -> list[str]:
    if scenario_id == 'H-02':
        return h02_review.result_sentences(conditions)
    if scenario_id == 'H-01':
        rows=[r for r in conditions if r['assertion_id']!='H01-A6']
        if len(rows)==15 and all(r['rule_status']=='PASS' for r in rows):
            return ['회사 담당자의 정상 결정·단계 변경 3건이 저장됐습니다. 지원자·미인증·SYSTEM의 변경 요청 9건은 거부됐고, AI 어시스턴트 3건은 답변만 반환했습니다.',
                    '권한 없는 요청으로 채용 단계나 최종 결정·검토 기록이 바뀐 경우는 없었습니다.']
        return [f"세 결정 경로의 주체별 테스트 {len(rows)}건 중 통과 {sum(r['rule_status']=='PASS' for r in rows)}건, 실패 {sum(r['rule_status']=='FAIL' for r in rows)}건, 판정 불가 {sum(r['rule_status']=='INCONCLUSIVE' for r in rows)}건입니다.",
                '회사 담당자의 정상 변경과 지원자·미인증·SYSTEM·AI 어시스턴트의 변경 시도를 구분해 기록했습니다.']
    if scenario_id == "N-02":
        return [f"{row['title']}: {row['observed']}" for row in conditions if row["assertion_id"] != "N02-A1"] or ["이 실행의 세부 관찰 기록이 없습니다."]
    if scenario_id not in {"E-01", "E-02"}:
        passed = sum(row["rule_status"] == "PASS" for row in conditions)
        failed = sum(row["rule_status"] == "FAIL" for row in conditions)
        unknown = sum(row["rule_status"] == "INCONCLUSIVE" for row in conditions)
        return [f"이 실행의 원본 검증 규칙 {len(conditions)}개 중 {passed}개가 통과, {failed}개가 실패, {unknown}개가 판정 불가로 기록됐습니다.",
                "아래에 각 규칙의 기대 반응과 실제 관찰 기록을 함께 표시합니다."]
    if scenario_id != "E-01":
        sentences = []
        for row in conditions:
            if not row["recorded"]:
                sentences.append(f"{row['title']}: 세부 관찰 기록이 없습니다.")
            else:
                status = {"PASS": "통과", "FAIL": "실패", "INCONCLUSIVE": "판정 불가"}.get(row["rule_status"], "판정 기록 없음")
                sentences.append(f"{row['title']} — {status}. {row['observed']}")
        return sentences or ["이 실행의 세부 관찰 기록이 없습니다."]
    invalid = conditions[:4]
    recorded = [row for row in invalid if row["recorded"]]
    withheld = sum(row["facts"].get("outcome") == "EMPTIED" for row in recorded)
    if len(recorded) < 4:
        first = f"잘못된 답변 근거 4유형 중 {len(recorded)}개에만 세부 처리 기록이 있습니다. 기록이 없는 조건의 동작은 확인하지 못했습니다."
    elif withheld == 4:
        first = "잘못된 답변 근거가 연결된 네 가지 경우 모두, WhyYou가 AI 응답 검증 과정에서 해당 점수를 보류했습니다."
    else:
        first = f"잘못된 답변 근거 4유형 중 {withheld}개는 점수가 보류됐고, 나머지는 기대와 다른 처리 결과가 기록됐습니다."
    if recorded and all(row["facts"].get("withheld_notice_confirmed") is True for row in recorded):
        first += " 해당 점수를 보류한 이유도 기록됐습니다."
    elif recorded and all(row["facts"].get("rationale_present") is True for row in recorded):
        first += " 해당 항목의 점수 설명도 기록됐습니다."
    elif recorded:
        first += " 일부 항목은 점수 설명이 남았는지 확인하지 못했습니다."
    valid, removed, restored = conditions[4:]
    second = ("정상적인 답변 근거가 연결된 점수는 정상 저장됐습니다."
              if valid["facts"].get("outcome") == "STORED_VALID"
              else "정상적인 답변 근거를 넣은 대조 테스트: " + valid["observed"])
    return [first, second, removed["observed"], restored["observed"]]


def build_review(
    scenario_id: str, definition: dict[str, Any], assertions: list[dict[str, Any]],
    bundle: Path, evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    by_rule = {item["assertion_id"]: item for item in assertions}
    conditions: list[dict[str, Any]] = []
    if scenario_id == 'H-01':
        try:
            recorded_cases=json.loads((bundle/'h01-cases.json').read_text(encoding='utf-8'))
        except (OSError,ValueError):
            recorded_cases=[]
        conditions = h01_review.conditions(assertions,lambda refs:_sources(refs,evidence),recorded_cases)
    elif scenario_id == 'H-02':
        conditions = h02_review.conditions(bundle,assertions,lambda refs:_sources(refs,evidence))
    elif scenario_id == "E-01":
        # These files have already passed verify_bundle. Only selected non-sensitive facts are projected.
        cases = {row.get("mode"): row for row in _rows(bundle / "citation-cases.jsonl")}
        emissions = {row.get("receipt_id"): row for row in _rows(bundle / "model-emissions.jsonl")}
        for row_id, mode, label, setup, rule in E01_CASES:
            assertion = by_rule.get(rule, {})
            source = cases.get(mode, {})
            facts = {key: source[key] for key in ("mode", "outcome", "rationale_present", "invalid_id_present") if key in source}
            if source.get("stored_axes"):
                facts["withheld_notice_confirmed"] = all(axis.get("rationale_is_unverified_notice") is True for axis in source["stored_axes"])
            outcome = source.get("outcome")
            if outcome == "EMPTIED":
                observed = "WhyYou가 AI 응답 검증 과정에서 해당 점수를 보류하고, 점수에 붙은 답변 연결을 제거했습니다."
                if source.get("rationale_present") is True:
                    axes = source.get("stored_axes") or []
                    observed += (" 점수를 보류한 이유가 기록됐습니다."
                                 if axes and all(axis.get("rationale_is_unverified_notice") is True for axis in axes)
                                 else " 비어 있지 않은 설명이 기록됐습니다.")
            elif outcome == "STORED_VALID":
                observed = "WhyYou가 AI 응답을 검증한 뒤, 해당 지원자·평가 항목에 맞는 답변 근거와 점수를 정상 저장했습니다."
            elif outcome == "STORED_INVALID":
                observed = "WhyYou의 처리 뒤에도 점수 또는 잘못 연결된 답변 근거가 저장 기록에 남았습니다."
            elif outcome == "NOT_PRODUCED":
                observed = "이 조건의 보고서 항목이 생성되지 않아 처리 결과를 확인하지 못했습니다."
            elif outcome is not None:
                observed = f"기대와 다른 처리 기록: {outcome}"
            else:
                observed = "조건별 관찰 기록 없음"
            if source.get("invalid_id_present") is True:
                observed += " 잘못된 답변 연결이 남아 있습니다."
            conditions.append({
                "id": row_id, "title": label, "setup": setup, "expected": RULES[rule][1], "observed": observed,
                "group": "AI가 잘못된 답변 근거를 제시했을 때", "assertion_id": rule,
                "rule_status": assertion.get("status"), "recorded": outcome is not None,
                "facts": facts, "sources": _sources(assertion.get("evidence_refs", []), evidence),
                "comparison": _comparison(source, emissions.get(source.get("emission_receipt_id"), {})),
            })
        for row_id, rule, title in [
            ("removed", "E01-A3", "저장된 점수의 답변 근거를 일시 제거"),
            ("restored", "E01-A4", "답변 근거를 복원한 뒤 비교"),
        ]:
            assertion = by_rule.get(rule, {})
            facts = assertion.get("actual") or {}
            if row_id == "removed":
                if facts.get("unexposed") or facts.get("changed_without_indicator"):
                    observed = "저장된 점수의 답변 근거를 제거했지만, 일부 항목에서 근거 부족이 드러나지 않거나 영향받지 않아야 할 다른 항목도 변경됐습니다."
                elif facts.get("indicators") and "unexposed" in facts:
                    observed = "저장된 점수의 답변 근거를 제거하자 WhyYou 보고서에 근거 부족 상태가 표시됐습니다. 다른 항목은 그대로였습니다."
                else:
                    observed = assertion.get("detail") or "관찰 기록 없음"
                safe_facts = {key: facts[key] for key in ("unexposed", "changed_without_indicator") if key in facts}
            else:
                observed = (
                    "답변 근거를 복원하자 보고서 조회 결과와 저장 기록이 제거 전과 같아졌습니다."
                    if facts.get("read_equal") is True and facts.get("record_equal") is True
                    else "답변 근거 복원 뒤 보고서 조회 결과나 저장 기록이 원래대로 돌아온 것을 확인하지 못했습니다." if facts
                    else "답변 근거 복원 뒤의 관찰 기록 없음"
                )
                safe_facts = {key: facts[key] for key in ("read_equal", "record_equal") if key in facts}
            conditions.append({
                "id": row_id, "title": title, "expected": RULES[rule][1], "observed": observed,
                "setup": ("ControlProof가 정상 저장된 점수의 답변 근거에 해당하는 테스트용 자막 구간을 잠시 제거했습니다."
                          if row_id == "removed" else "ControlProof가 일시 제거한 테스트용 답변 근거를 같은 값으로 복원했습니다."),
                "group": "저장된 점수의 답변 근거가 사라졌을 때", "assertion_id": rule,
                "rule_status": assertion.get("status"), "recorded": bool(facts),
                "facts": safe_facts, "sources": _sources(assertion.get("evidence_refs", []), evidence),
                "comparison": [],
            })
    else:
        for assertion in assertions:
            display = rule_display(assertion)
            conditions.append({
                "id": assertion["assertion_id"], "title": display["label"],
                "expected": display["expected"], "observed": display["observed"],
                "group": n02_review.GROUPS.get(assertion["assertion_id"], "테스트 조건과 관찰 결과"), "assertion_id": assertion["assertion_id"],
                "rule_status": assertion["status"], "recorded": assertion.get("actual") is not None,
                "observation_source": "SEALED_DETAIL" if scenario_id != "N-02" and assertion.get("detail") else "ACTUAL_VALUES",
                "facts": assertion.get("actual"), "sources": _sources(assertion.get("evidence_refs", []), evidence),
                "setup": (n02_review.SETUPS | PLAIN_SETUPS).get(assertion["assertion_id"], display["expected"]), "comparison": [],
                "proof_rows": (n02_review.observation(assertion)[1] + n02_review.path_facts(assertion["assertion_id"], _rows(bundle / "causal-events.jsonl"))) if scenario_id == "N-02" else [],
            })
    sentences = _result_sentences(scenario_id, conditions)
    return {
        "title": TITLES.get(scenario_id, definition.get("title") or scenario_id),
        "description": DESCRIPTIONS.get(scenario_id),
        "summary": " ".join(sentences), "summary_sentences": sentences,
        "process": ("테스트 경로: 고정 테스트용 모델 출력 → WhyYou의 AI 응답 검증 → 보고서 저장. 합성 지원자와 정해진 테스트용 출력을 사용하며, 실제 외부 AI 모델의 자율 생성 행동·품질은 평가하지 않습니다."
                    if scenario_id == "E-01" else "합성 지원자·문서와 고정 테스트용 AI를 사용해 WhyYou의 동의 확인·처리 순서·검증·저장 과정을 실행했습니다." if scenario_id == "N-02" else "합성 테스트 데이터로 기록한 결과입니다. 실행한 규칙과 수집된 확인 자료에만 판정이 적용됩니다."),
        "conditions": conditions, "rule_count": len(assertions),
        "passed_rule_count": sum(item["status"] == "PASS" for item in assertions),
    }
