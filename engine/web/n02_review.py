"""Readable projections of sealed N-02 facts. Missing data never becomes a successful claim."""

RULES = {
    "N02-A1": ("테스트 전 동의·처리 기록 없음", "새 지원자에게 동의와 처리 기록이 없어야 합니다."),
    "N02-A2": (
        "동의 없이 문서 분석 요청",
        "문서 분석 요청을 거부하고 처리를 시작하지 않아야 합니다.",
    ),
    "N02-A3": (
        "동의 없이 녹화 요청",
        "녹화 요청을 거부하고 세션·녹화 처리를 시작하지 않아야 합니다.",
    ),
    "N02-A4": (
        "동의 없이 AI 평가 요청",
        "작업자가 평가 요청을 거부하고 평가·보고서 생성을 시작하지 않아야 합니다.",
    ),
    "N02-A5": (
        "동의 저장 후 문서 분석·녹화·AI 평가 진행",
        "동의가 저장된 다음 각 처리의 요청·시작·결과 생성이 이어져야 합니다.",
    ),
    "N02-A6": (
        "동의 저장 장애가 발생한 경우",
        "동의가 저장되지 않으면 문서 분석·녹화·AI 평가도 시작되지 않아야 합니다.",
    ),
    "N02-A7": (
        "장애 해제 후 같은 지원자로 재시도",
        "동의가 한 번만 완료되고 세 처리가 정상 순서로 이어져야 합니다.",
    ),
}
SETUPS = {
    "N02-A1": "동의·제출·녹화·평가 이력이 없는 합성 지원자를 준비했습니다.",
    "N02-A2": "동의하지 않은 지원자로 문서 분석을 요청했습니다.",
    "N02-A3": "동의하지 않은 지원자로 녹화를 요청했습니다. 장비·전략 등 다른 준비 조건은 갖췄습니다.",
    "N02-A4": "동의하지 않은 지원자의 AI 평가 요청을 작업자에게 전달했습니다.",
    "N02-A5": "정상 동의를 저장하고 녹화·AI 평가·문서 분석을 요청했습니다.",
    "N02-A6": "동의 저장 중 장애를 발생시킨 뒤, 동의가 저장되지 않은 상태에서 세 처리를 요청했습니다.",
    "N02-A7": "장애를 해제하고 안전 상태를 확인한 뒤 같은 지원자로 동의와 처리를 재시도했습니다.",
}
GROUPS = {
    "N02-A1": "1. 새 지원자 준비",
    "N02-A2": "2. 동의하지 않은 상태", "N02-A3": "2. 동의하지 않은 상태", "N02-A4": "2. 동의하지 않은 상태",
    "N02-A5": "3. 동의 저장 후 처리",
    "N02-A6": "4. 동의 저장 장애와 복구", "N02-A7": "4. 동의 저장 장애와 복구",
}
PLAN = {
    "conditions": [
        "동의 없는 문서 분석·녹화·AI 평가 요청",
        "동의 후 처리 순서",
        "동의 저장 장애",
        "장애 해제 후 같은 지원자로 재시도",
    ],
    "stages": [
        {
            "title": "새 지원자와 동의 없는 요청",
            "text": "새 합성 지원자로 동의 없이 세 처리를 요청하고 차단 여부를 기록합니다.",
        },
        {
            "title": "정상 동의와 처리 결과",
            "text": "동의 저장 뒤 각 처리의 요청·시작·결과가 이어지는지 확인합니다.",
        },
        {
            "title": "동의 저장 장애와 재시도",
            "text": "동의 저장 실패 후 처리가 차단되는지 확인하고, 장애 해제 후 같은 지원자로 재시도합니다.",
        },
        {
            "title": "복구·정리와 증거 보존",
            "text": "임시 조건과 합성 데이터를 정리하고 동의·처리·복구 기록을 봉인합니다.",
        },
    ],
}


def path_facts(rule, events):
    lane = {"N02-A5": "NORMAL_ORDER", "N02-A7": "CONSENT_FAULT_RECOVERY"}.get(rule)
    if lane is None:
        return []
    scoped = [row for row in events if row.get("lane_id") == lane]
    result = []
    for path, label in [
        ("DOCUMENT_ANALYSIS", "문서 분석"),
        ("RECORDING", "녹화"),
        ("AI_ASSESSMENT", "AI 평가"),
    ]:
        kinds = {row.get("kind") for row in scoped if row.get("path_id") == path}
        checks = [
            ("PROCESSING_REQUESTED", "요청"),
            ("PROCESSING_STARTED", "시작"),
            ("RESULT_CREATED", "결과 생성"),
        ]
        value = " · ".join(
            f"{label_} {'기록 있음' if kind in kinds else '기록 없음'}" for kind, label_ in checks
        )
        result.append({"label": label, "value": value})
    return result


def observation(assertion):
    rule, actual = assertion["assertion_id"], assertion.get("actual")
    if not isinstance(actual, dict) or not actual:
        return "이 조건의 세부 관찰 기록이 없습니다.", []
    passed = assertion.get("status") == "PASS"
    rows = []

    def add(label, value):
        rows.append({"label": label, "value": value})

    def flag(key):
        return {True: "확인됨", False: "확인되지 않음"}.get(actual.get(key), "기록 없음")

    def count(key):
        value = actual.get(key)
        number = len(value) if isinstance(value, (list, tuple)) else value
        return f"{number}건" if type(number) is int else "기록 없음"

    if rule == "N02-A1":
        add("기존 처리 기록", count("protected_effect_count"))
        add("세 처리 경로 조회", flag("three_paths_queryable"))
        ok = (
            passed
            and actual.get("protected_effect_count") == 0
            and actual.get("three_paths_queryable") is True
        )
        return (
            "테스트 전 동의·처리 이력이 없는 시작 상태를 확인했습니다."
            if ok
            else "테스트 시작 상태가 비어 있는지 충분히 확인하지 못했습니다."
        ), rows
    if rule in {"N02-A2", "N02-A3", "N02-A4"}:
        name = {"N02-A2": "문서 분석", "N02-A3": "녹화", "N02-A4": "AI 평가"}[rule]
        refused = actual.get("response_class") == "DENIED" or bool(
            actual.get("refusal_receipt_ids")
        )
        response = (
            "요청 거부"
            if refused
            else {"ACCEPTED": "요청 수락", "SUBMITTED": "작업자에게 전달됨"}.get(
                actual.get("response_class"), "응답을 확정하지 못함"
            )
        )
        add("요청에 대한 반응", response)
        add("새 처리 기록", count("new_effect_ids"))
        add("처리 시작 기록", count("start_receipt_ids"))
        if passed and refused and actual.get("new_effect_ids") == []:
            return f"동의 없는 {name} 요청을 거부했고, 새 처리 결과가 생성되지 않았습니다.", rows
        if actual.get("new_effect_ids") or actual.get("start_receipt_ids"):
            return f"동의 없는 {name} 요청 뒤 새 처리 또는 시작 기록이 남았습니다.", rows
        return f"동의 없는 {name} 요청의 차단 여부를 확인하지 못했습니다.", rows
    if rule == "N02-A5":
        add("동의한 내용·처리 목적 일치", flag("policy_identity_matches"))
        add("기록된 동의·처리 단계", count("event_count"))
        add("단계의 선후 관계", count("edge_count"))
        proven = (
            passed
            and actual.get("causal_order") == "PROVEN"
            and actual.get("policy_identity_matches") is True
        )
        add(
            "동의 → 요청 → 시작 → 결과",
            "세 처리 경로에서 입증됨" if proven else "전체 순서를 입증하지 못함",
        )
        return (
            "동의 저장 뒤 문서 분석·녹화·AI 평가의 요청·시작·결과 생성이 이어졌습니다."
            if proven
            else "동의 저장부터 세 처리의 결과 생성까지 전체 순서를 확인하지 못했습니다."
        ), rows
    if rule == "N02-A6":
        add("저장 장애 발동", flag("receipt_present"))
        add("장애와 해당 요청 연결", flag("receipt_request_matches"))
        add(
            "동의 일부만 저장됨",
            {True: "있음", False: "없음"}.get(actual.get("partial_consent"), "기록 없음"),
        )
        add("동의 저장 실패 뒤 처리 기록", count("leaked_effect_ids"))
        proven = (
            passed
            and actual.get("receipt_present") is True
            and actual.get("receipt_request_matches") is True
            and actual.get("partial_consent") is False
            and actual.get("leaked_effect_ids") == []
        )
        return (
            "동의 저장이 실패하자 동의 완료 기록이 남지 않았고, 문서 분석·녹화·AI 평가도 차단됐습니다."
            if proven
            else "동의 저장이 실패했는데도 동의 일부가 저장되거나 후속 처리 기록이 남았습니다."
            if actual.get("partial_consent") is True or actual.get("leaked_effect_ids")
            else "동의 저장 장애 뒤 후속 처리가 모두 차단됐는지 확인하지 못했습니다."
        ), rows
    if rule == "N02-A7":
        add("저장된 동의", count("logical_consent_count"))
        add("동의 완료 이력", count("consent_completed_event_count"))
        add("정상 재시도 성공", flag("normal_retry_succeeded"))
        add("재시도 처리 순서", flag("processing_order_proven"))
        add(
            "복구 상태",
            {"SUCCEEDED": "안전한 복구 확인", "FAILED": "안전한 복구를 확정하지 못함"}.get(
                actual.get("restore_status"), "기록 없음"
            ),
        )
        proven = (
            passed
            and actual.get("restore_status") == "SUCCEEDED"
            and actual.get("normal_retry_succeeded") is True
            and actual.get("processing_order_proven") is True
            and actual.get("logical_consent_count") == 1
            and actual.get("consent_completed_event_count") == 1
        )
        return (
            "장애 해제 후 동의가 한 번만 완료됐고, 같은 지원자의 세 처리가 정상 순서로 이어졌습니다."
            if proven
            else "재시도 뒤 동의 또는 동의 완료 이력이 중복됐습니다."
            if any(type(actual.get(k)) is int and actual[k] > 1 for k in ("logical_consent_count", "consent_completed_event_count"))
            else "장애 해제 후 정상 재시도가 성공하지 못했습니다."
            if actual.get("normal_retry_succeeded") is False
            else "장애 해제 후 재시도의 동의·처리 순서와 안전한 복구를 모두 확인하지 못했습니다."
        ), rows
    return assertion.get("detail") or "세부 관찰 기록 없음", rows
