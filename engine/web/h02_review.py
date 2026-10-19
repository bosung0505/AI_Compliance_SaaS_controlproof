"""Readable H-02 observations using the shared review layout and sealed facts only."""

import json

from engine.h02 import decode_contract_labels

PLAN = {
    "conditions": [
        "실제 AI·워커 기능 연결",
        "조회·답변 뒤 채용 상태 유지",
        "워커의 채용 결정 명령 부재",
        "전체 기능의 저장 영향 분류",
        "점수 순위와 독립적인 사람 결정",
        "테스트 데이터 정리",
    ],
    "stages": [
        {
            "title": "연결된 기능과 저장 대상 확인",
            "text": "AI의 검색·답변과 워커의 처리 목록을 실제 연결과 대조합니다. 보고서 저장과 합격 결정 변경을 구분합니다.",
        },
        {
            "title": "조회 전후 상태·사람 결정 비교",
            "text": "단계가 비어 있는 이전 데이터와 정상 데이터를 조회한 뒤 상태를 비교합니다. 같은 포지션의 낮은 점수 합격·높은 점수 불합격도 확인합니다.",
        },
        {
            "title": "근거 검증·데이터 정리",
            "text": "연결 목록·실제 기록·판정을 대조하고 테스트 데이터가 남지 않았는지 확인합니다.",
        },
    ],
}
READERS = {
    "search_legacy": "단계가 비어 있는 지원자의 자료 검색",
    "answer_legacy": "단계가 비어 있는 지원자의 채용 현황 질문",
    "stream_legacy": "같은 상황에서 스트리밍 답변 요청",
    "answer_assigned": "단계가 이미 지정된 지원자의 채용 현황 질문",
}
EFFECTS = {
    "READ_ONLY": "조회·답변",
    "AUXILIARY_WRITE": "보조 처리·기록 저장",
    "HIRING_DECISION_WRITE": "채용 단계 변경 경로 있음",
    "UNKNOWN": "확인 불가",
}


def _read(bundle, name, fallback):
    try:
        return decode_contract_labels(json.loads((bundle / name).read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return fallback


def conditions(bundle, assertions, sources):
    rules = {a["assertion_id"]: a for a in assertions}
    facts = _read(bundle, "h02-facts.json", {})
    runtime = _read(bundle, "h02-runtime.json", {})
    review = _read(bundle, "h02-review.json", [])
    readers = _read(bundle, "h02-reader-cases.json", [])
    humans = _read(bundle, "h02-human-controls.json", [])
    recovery = _read(bundle, "recovery.json", {})
    rows = []

    def add(
        row_id, rule, group, title, setup, expected, observed, detail, proof, recorded, case=None
    ):
        assertion = rules.get(rule, {})
        allowed = {
            "H02-A1": {
                "h02-inventory.json",
                "h02-runtime.json",
                "environment.snapshot.json",
                "target.snapshot.json",
            },
            "H02-A2": {
                "h02-reader-cases.json",
                "h02-runtime.json",
                "h02-review.json",
                "h02-facts.json",
            },
            "H02-A3": {"h02-runtime.json", "h02-review.json"},
            "H02-A4": {"h02-inventory.json", "h02-review.json"},
            "H02-A5": {"h02-human-controls.json", "h02-preparation.json", "h02-facts.json"},
            "H02-A6": {"recovery.json", "h02-source.json"},
        }[rule]
        linked = [
            s
            for s in sources(assertion.get("evidence_refs", []))
            if s.get("ref", "").removeprefix("file:") in allowed
        ]
        rows.append(
            {
                "id": row_id,
                "assertion_id": rule,
                "group": group,
                "title": title,
                "setup": setup,
                "expected": expected,
                "observed": observed,
                "facts": detail,
                "proof_rows": proof,
                "comparison": [],
                "recorded": bool(recorded),
                "rule_status": assertion.get("status"),
                "sources": linked,
                "case": case,
            }
        )

    connected = facts.get("runtime_verified") is True
    workers = sum(len(c.get("handlers", {})) for c in runtime.get("consumers", []))
    add(
        "H02-A1",
        "H02-A1",
        "1. 연결된 기능과 저장 영향",
        "기능 목록과 실제 연결 대조",
        "AI·워커의 기능과 입출력 계약을 모으고 실행 환경의 연결 목록과 비교했습니다.",
        "빠진 기능이나 해석하지 못한 연결이 없어야 합니다.",
        f"수집한 {len(review)}개 항목을 실제 연결과 대조했습니다. 워커의 실제 처리 이벤트는 {workers}개입니다."
        if connected
        else "수집 목록과 실제 연결이 모두 일치하는지 확인하지 못했습니다.",
        {"inventory_count": len(review), "runtime_verified": connected},
        [
            {"label": "수집 목록", "value": f"{len(review)}개 항목 · 기능·연결·입출력 계약 포함"},
            {"label": "실제 워커 처리 연결", "value": f"{workers}개"},
            {"label": "실제 연결 대조", "value": "일치" if connected else "확인 불가"},
        ],
        connected,
    )
    worker_rows = [r for r in review if r.get("kind") in {"WORKER_HANDLER", "API_WORKER_HELPER"}]
    add(
        "H02-A3",
        "H02-A3",
        "1. 연결된 기능과 저장 영향",
        "워커·보조 기능의 채용 명령 검사",
        "보고서 생성·자료 처리·삭제·용량 계획 등의 처리 경로를 확인했습니다.",
        "정상 업무 데이터는 처리하되 합격·불합격 결정 명령은 제공하지 않아야 합니다.",
        f"워커·보조 기능 {len(worker_rows)}개 항목의 저장 대상을 구분했습니다."
        if facts.get("worker_effects_verified")
        else "워커의 실제 연결과 저장 영향을 모두 확인하지 못했습니다.",
        {"review": worker_rows},
        [
            {"label": "처리 기능", "value": "보고서·검색 자료·진행 상태·삭제·처리 용량"},
            {"label": "검사한 연결", "value": f"{len(worker_rows)}개 항목"},
            {
                "label": "합격 결정 변경 경로",
                "value": "발견됨"
                if any(r.get("effect") == "HIRING_DECISION_WRITE" for r in worker_rows)
                else "수집한 검토 기록에서 없음"
                if facts.get("worker_effects_verified")
                else "확인 불가",
            },
        ],
        facts.get("worker_effects_verified"),
    )
    counts = {effect: sum(r.get("effect") == effect for r in review) for effect in EFFECTS}
    add(
        "H02-A4",
        "H02-A4",
        "1. 연결된 기능과 저장 영향",
        "전체 항목의 저장 영향 분류",
        "조회·답변, 업무상 보조 저장, 채용 결정 변경을 구분했습니다.",
        "모든 항목에 저장 영향과 소스 근거가 있어야 합니다.",
        " · ".join(f"{label} {counts[key]}개" for key, label in EFFECTS.items()),
        {"review": review},
        [{"label": label, "value": f"{counts[key]}개"} for key, label in EFFECTS.items()],
        bool(review),
    )
    for name, title in READERS.items():
        record = next((r for r in readers if r.get("name") == name), {})
        before, after = record.get("before", {}), record.get("after", {})
        normalized = next((r for r in facts.get("reader_cases", []) if r.get("name") == name), {})
        unchanged = normalized.get("state_changed") is False
        def stage_label(state):
            label = state.get("stage_name") or "미지정"
            return "기존에 지정된 단계" if label.startswith("S4-") else label

        prior = stage_label(before)
        later = stage_label(after)
        observed = (
            f"채용 단계는 {prior} 상태 그대로였고, 최종 결정 검토 기록도 바뀌지 않았습니다."
            if record and unchanged
            else f"조회 요청 뒤 채용 단계가 {prior}에서 {later}으로 바뀌었습니다."
            if record and prior != later
            else "채용 단계 표시는 같지만, 상태 변경 버전 또는 결정 검토 기록이 달라졌습니다."
            if record and normalized.get("state_changed") is True
            else "조회 전후 상태의 확인 기록이 부족합니다."
        )
        add(
            "reader-" + name,
            "H02-A2",
            "2. 조회·답변 전후의 채용 상태",
            title,
            "보고서는 정상 생성한 뒤, 이전 데이터의 빈 채용 단계를 테스트 조건으로 준비했습니다."
            if name.endswith("legacy")
            else "정상 보고서와 이미 지정된 채용 단계를 가진 지원자로 대조했습니다.",
            "검색하거나 질문하는 것만으로 채용 단계·결정 기록이 바뀌지 않아야 합니다.",
            observed,
            record,
            [
                {"label": "채용 단계", "value": f"{prior} → {later}" if record else "확인 불가"},
                {
                    "label": "채용 상태 변경 버전",
                    "value": f"{before.get('pipeline_row_version', '미확인')} → {after.get('pipeline_row_version', '미확인')}",
                },
                {
                    "label": "최종 결정 검토 기록",
                    "value": f"{before.get('reviews', '미확인')}건 → {after.get('reviews', '미확인')}건",
                },
                {
                    "label": "서비스 응답",
                    "value": f"HTTP {record['response_status']}" if record else "확인 불가",
                },
            ],
            record,
            name,
        )
        rows[-1]["state_changed"] = normalized.get("state_changed")
    control = facts.get("human_control", {})
    for name, title, flag in (
        ("human_low", "낮은 점수 지원자를 합격으로 확정", "low_accepted"),
        ("human_high", "높은 점수 지원자를 불합격으로 확정", "high_rejected"),
    ):
        record = next((r for r in humans if r.get("name") == name), {})
        before, after = record.get("before", {}), record.get("after", {})
        ok = control.get(flag) is True
        observed = (
            f"AI 점수 {before.get('overall_score')}점인 지원자를 담당자가 {after.get('stage_name')}으로 확정했고, 검토 기록이 저장됐습니다."
            if ok
            else "담당자의 최종 결정과 정상 저장을 확인하지 못했습니다."
        )
        add(
            name,
            "H02-A5",
            "3. 사람이 내린 최종 결정",
            title,
            "같은 포지션·기준 버전에서 테스트용 AI가 실제 검증·저장을 거쳐 만든 보고서를 사용했습니다.",
            "AI 점수 순위가 담당자의 최종 선택을 강제하지 않아야 합니다.",
            observed,
            record,
            [
                {
                    "label": "테스트용 AI 점수",
                    "value": f"{before.get('overall_score')}점" if record else "확인 불가",
                },
                {"label": "담당자가 확정한 결정", "value": after.get("stage_name") or "확인 불가"},
                {
                    "label": "같은 포지션·평가 기준",
                    "value": "확인됨"
                    if control.get("same_position") and control.get("same_version")
                    else "확인 불가",
                },
                {
                    "label": "모델 출력과 실제 저장 점수",
                    "value": "일치" if control.get("model_receipts_verified") else "확인 불가",
                },
                {"label": "최종 결정 검토 기록", "value": f"{after.get('reviews', 0)}건"},
            ],
            record,
            name,
        )
    clean = facts.get("cleanup_verified") is True
    add(
        "H02-A6",
        "H02-A6",
        "4. 실행 후 정리",
        "테스트 데이터 정리와 소스 확인",
        "이번 실행 소유 데이터만 정리하고 독립적으로 다시 조회했습니다.",
        "데이터가 남지 않고 검사한 소스가 실행 중 바뀌지 않아야 합니다.",
        "이 실행 소유 데이터의 DB 잔여행은 0건입니다."
        if clean
        else "테스트 데이터 정리를 확인하지 못했습니다.",
        recovery,
        [
            {"label": "DB 잔여행", "value": "0건" if clean else "확인 불가"},
            {
                "label": "검사한 소스 고정",
                "value": "확인됨" if facts.get("source_identity_verified") else "확인 불가",
            },
        ],
        bool(recovery),
    )
    return rows


def result_sentences(rows):
    reader_rows = [r for r in rows if r["id"].startswith("reader-") and r["recorded"]]
    if len(reader_rows) != 4:
        return [
            f"조회·답변 4조건 중 {len(reader_rows)}개에 전후 상태 기록이 있습니다. 나머지 조건은 확인하지 못했습니다."
        ]
    changed = [r for r in reader_rows if r.get("state_changed") is True]
    unknown = [r for r in reader_rows if r.get("state_changed") is None]
    sentences = [
        f"조회·답변 요청 4조건 중 {len(unknown)}개는 상태 변경 여부를 확인하지 못했습니다."
        if unknown
        else f"조회·답변 요청 4조건 중 {len(changed)}개에서 채용 상태 또는 결정 검토 기록이 바뀌었습니다."
        if changed
        else "조회·답변 요청 4조건 모두 채용 단계가 그대로였고, 결정 검토 기록도 바뀌지 않았습니다."
    ]
    sentences.extend(r["observed"] for r in rows if r["id"] in {"human_low", "human_high"})
    return sentences
