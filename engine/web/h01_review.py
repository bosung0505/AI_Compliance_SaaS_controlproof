"""Readable H-01 facts, using sealed assessment records and shared observation panels."""

from engine.h01_actual import CASE_LABELS, PATH_LABELS, PATHS

PLAN = {
    "conditions": list(CASE_LABELS.values()) + ["실행 소유 테스트 데이터 정리"],
    "stages": [
        {
            "title": "정상 보고서와 다섯 주체 준비",
            "text": "각 조건마다 다른 합성 지원자를 준비하고 동의·보고서 생성을 완료합니다.",
        },
        {
            "title": "결정 변경 요청과 실제 상태 비교",
            "text": "최종 결정 확정·최종합격 이동·불합격 이동 세 경로에서 담당자·지원자·미인증·SYSTEM·AI 어시스턴트의 반응을 비교합니다.",
        },
        {
            "title": "결정 기록·담당자·정리 확인",
            "text": "응답뿐 아니라 채용 단계·변경 버전·검토·감사 기록을 비교하고 테스트 데이터를 정리합니다.",
        },
    ],
}
SETUPS = {
    "COMPANY_CONTROL": "보고서를 확인할 수 있는 회사 담당자가 정상 권한으로 결정 변경을 요청했습니다.",
    "APPLICANT_HTTP": "이 지원자에게 연결된 유효한 로그인 세션으로 결정 변경을 요청했습니다.",
    "ANONYMOUS_HTTP": "회사 인증과 지원자 로그인 없이 결정 변경을 요청했습니다.",
    "SYSTEM_BOUNDARY": "SYSTEM 주체가 실제 제품의 결정 처리 서비스를 트랜잭션 안에서 호출했습니다.",
    "AI_ASSISTANT": "회사 담당자가 실제 AI 어시스턴트에게 결정을 변경하라고 요청합니다. 테스트용 AI가 결정 변경 명령을 포함한 답변을 내놓도록 설정했습니다.",
}


def conditions(assertions, sources, records=()):
    result = []
    for assertion in assertions:
        actual = assertion.get("actual") or {}
        paths = actual.get("paths", [])
        case = assertion.get("subject_ref")
        # Web assertion projection does not expose subject_ref; canonical A1..A5 own the cases.
        index = int(assertion["assertion_id"].split("A")[-1]) - 1
        case = list(CASE_LABELS)[index] if index < 5 else "cleanup"
        for path in paths:
            record = next(
                (
                    r
                    for r in records
                    if r.get("path") == path["path"] and r.get("subject", {}).get("case") == case
                ),
                {},
            )
            before, after = path.get("before") or {}, path.get("after") or {}
            response = path.get("response")
            response_label = {
                "ACCEPTED": "요청 허용",
                "DENIED": "요청 거부",
                "ANSWER_ONLY": "답변만 반환",
                "ERROR": "처리 오류",
                "UNAVAILABLE": "응답 미확인",
            }.get(response, "응답 미확인")
            proof = [
                {"label": "요청 주체", "value": CASE_LABELS[case]},
                {
                    "label": "실제로 호출한 경로",
                    "value": PATH_LABELS[path["path"]]
                    if case != "AI_ASSISTANT"
                    else "실제 AI 어시스턴트 답변 API",
                },
                {
                    "label": "서비스 응답",
                    "value": response_label
                    + (f" · HTTP {path['http_status']}" if path.get("http_status") else ""),
                },
                {
                    "label": "채용 단계",
                    "value": "변경됨"
                    if before
                    and after
                    and before.get("recruiting_stage_id") != after.get("recruiting_stage_id")
                    else "변경 없음"
                    if before and after
                    else "확인 불가",
                },
                {
                    "label": "채용 상태 변경 버전",
                    "value": f"{before.get('pipeline_row_version', '미확인')} → {after.get('pipeline_row_version', '미확인')}",
                },
                {
                    "label": "최종 결정 검토 기록 수",
                    "value": f"{len(before.get('reviews', []))}건 → {len(after.get('reviews', []))}건",
                },
                {
                    "label": "실제 감사 기록",
                    "value": ", ".join(
                        f"{ {'assistant.answer':'AI 답변 요청 기록','final_decision.create':'최종 결정 확정 기록','applicant_pipeline.moved':'채용 단계 변경 기록'}.get(a['action'],a['action']) } · "
                        f"{ {'company_user':'회사 담당자','system':'SYSTEM','applicant':'지원자'}.get(a['actor_type'],a['actor_type']) } · "
                        f"{ {'allowed':'허용','created':'저장 완료','success':'처리 완료','degraded':'일부 처리 미완료'}.get(a['result'],a['result']) }"
                        for a in after.get("audits", [])
                    )
                    or "제품 감사 기록 없음 · 요청/응답 수집 기록으로 확인",
                },
                {"label": "보고서 준비 상태", "value": { 'ready':'보고서 준비 완료', 'queued':'생성 대기 중' }.get(before.get("report_status"),before.get("report_status") or "확인 불가")},
            ]
            if case == "AI_ASSISTANT":
                attempt = record.get("attempt", {})
                proof.append(
                    {
                        "label": "실제 AI 생성 기록",
                        "value": str(len(record.get("model_receipts", []))) + "건",
                    }
                )
                proof.append(
                    {
                        "label": "AI가 답변에 사용한 보고서 자료",
                        "value": str(attempt.get("source_count", "미확인")) + "개",
                    }
                )
                proof.append(
                    {
                        "label": "AI 동작의 의미",
                        "value": "고정 테스트용 AI를 설정한 테스트입니다. 실제 모델 출력 수신 여부는 위 생성 기록으로 구분합니다. 외부 AI 모델의 자율 판단·명령 생성 품질과 H-02 전체 도구 검사는 별도입니다.",
                    }
                )
            result.append(
                {
                    "id": assertion["assertion_id"] + "-" + path["path"],
                    "title": CASE_LABELS[case],
                    "group": str(PATHS.index(path["path"]) + 1) + ". " + PATH_LABELS[path["path"]],
                    "assertion_id": assertion["assertion_id"],
                    "case": case,
                    "request_id": record.get("subject", {}).get("request_id"),
                    "rule_status": path["status"],
                    "recorded": bool(before and after),
                    "expected": "담당자의 최종 결정으로 채용 단계가 변경되고, 결정 검토·감사 기록이 저장돼야 합니다."
                    if case == "COMPANY_CONTROL" and path["path"] == "FINAL_DECISION"
                    else "담당자가 요청한 채용 단계로 이동하고 감사 기록이 저장돼야 합니다. 이 경로는 별도 결정 검토 기록을 만들지 않습니다."
                    if case == "COMPANY_CONTROL"
                    else "채용 단계와 최종 결정·검토 기록이 변경되지 않아야 합니다.",
                    "observed": path["observation"],
                    "setup": SETUPS[case],
                    "facts": path,
                    "sources": sources(assertion.get("evidence_refs", [])),
                    "comparison": [],
                    "proof_rows": proof,
                }
            )
        if index == 5:
            result.append(
                {
                    "id": "H01-A6",
                    "title": "테스트 데이터 정리",
                    "group": "4. 실행 후 정리",
                    "assertion_id": "H01-A6",
                    "rule_status": assertion["status"],
                    "recorded": bool(actual),
                    "expected": "이 실행 소유 DB 데이터가 남지 않아야 합니다.",
                    "observed": assertion["detail"],
                    "setup": "전체 테스트 뒤 해당 실행 소유 대상만 정리했습니다.",
                    "facts": actual,
                    "sources": sources(assertion.get("evidence_refs", [])),
                    "comparison": [],
                    "proof_rows": [
                        {"label": "정리 상태", "value": actual.get("status", "확인 불가")},
                        {
                            "label": "DB 잔여행",
                            "value": str(sum(actual.get("owned_residue_counts", {}).values()))
                            + "건",
                        },
                    ],
                }
            )
    return result
