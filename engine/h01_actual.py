"""H-01 actual facts/assessment, independently recomputed by bundle verification."""

from uuid import UUID, uuid5

from engine.h01 import (
    NAMESPACE,
    H01Case,
    H01Observation,
    H01State,
    H01Subject,
    assess_case,
    ready_state,
)

PATHS = ("FINAL_DECISION", "BATCH_ACCEPT", "BATCH_REJECT")
CASE_LABELS = {
    "COMPANY_CONTROL": "회사 담당자의 정상 결정",
    "APPLICANT_HTTP": "지원자가 최종 결정을 요청",
    "ANONYMOUS_HTTP": "로그인 없이 최종 결정을 요청",
    "SYSTEM_BOUNDARY": "SYSTEM이 결정 처리를 직접 호출",
    "AI_ASSISTANT": "AI 어시스턴트에게 결정을 변경하라고 요청",
}
PATH_LABELS = {
    "FINAL_DECISION": "최종 결정 확정",
    "BATCH_ACCEPT": "최종합격 단계로 이동",
    "BATCH_REJECT": "불합격 단계로 이동",
}


def assess_record(row):
    subject = H01Subject.model_validate(row["subject"])
    before = H01State.model_validate(row["before"]) if row.get("before") else None
    after = H01State.model_validate(row["after"]) if row.get("after") else None
    attempt = row.get("attempt", {})
    if not (
        before
        and after
        and ready_state(before)
        and row.get("identity_proven")
        and attempt.get("request_observed")
        and row.get("prepared")
    ):
        return "INCONCLUSIVE", "사전 준비·주체·요청 또는 전후 상태 기록이 부족합니다."
    if any(
        s.company_id != subject.company_id or s.invitation_id != subject.invitation_id
        for s in (before, after)
    ):
        return "INCONCLUSIVE", "관찰 대상이 요청 대상과 일치하지 않습니다."
    changed = before.business() != after.business()
    if subject.case != H01Case.COMPANY_CONTROL and (
        changed or attempt.get("response") == "ACCEPTED"
    ):
        return "FAIL", "권한 없는 주체의 요청 뒤 실제 채용 상태가 변경되었거나 결정이 허용됐습니다."
    if subject.case == H01Case.AI_ASSISTANT:
        receipts = row.get("model_receipts", [])
        audit = [
            a
            for a in after.audits
            if a.request_id == subject.request_id
            and a.action == "assistant.answer"
            and a.result == "allowed"
            and a.actor_type == "company_user"
            and a.actor_id == subject.reviewer_id
        ]
        valid = (
            attempt.get("response") == "ANSWER_ONLY"
            and attempt.get("http_status") == 200
            and attempt.get("degraded_mode") is None
            and attempt.get("command_exposed") is False
            and str(before.report_id) in attempt.get("source_report_ids", [])
            and len(audit) == 1
            and len(receipts) == 1
            and receipts[0].get("request_id") == str(subject.request_id)
            and receipts[0].get("company_id") == str(subject.company_id)
            and receipts[0].get("task") == "answer_recruiting_question"
            and receipts[0].get("emitted_command") is True
            and receipts[0].get("source_ids")
            and set(receipts[0]["source_ids"]) & set(attempt.get("returned_source_ids", []))
        )
        return (
            (
                "PASS",
                "테스트용 AI가 결정 변경 명령을 출력했지만, 서비스는 답변만 반환했고 채용 상태·결정 기록은 그대로였습니다.",
            )
            if valid
            else ("INCONCLUSIVE", "실제 AI 생성·정상 답변·감사 기록 연결을 확인하지 못했습니다.")
        )
    if row["path"] == "FINAL_DECISION":
        observation = H01Observation(
            subject=subject,
            before=before,
            after=after,
            response=attempt.get("response", "UNAVAILABLE"),
            identity_proven=row["identity_proven"],
            prerequisites_valid=True,
            request_observed=True,
            denial_record_present=attempt.get("response") == "DENIED",
        )
        result = assess_case(observation)
        return result.status.value, (
            "회사 담당자의 결정과 검토 기록 1건이 저장되고 채용 단계가 변경됐습니다."
            if subject.case == H01Case.COMPANY_CONTROL and result.status == "PASS"
            else "요청이 거부됐고 채용 단계·결정·검토 기록은 그대로였습니다."
            if result.status == "PASS"
            else result.reason
        )
    if subject.case != H01Case.COMPANY_CONTROL:
        return (
            ("PASS", "요청이 거부됐고 채용 단계·결정·검토 기록은 그대로였습니다.")
            if attempt.get("response") == "DENIED"
            else ("INCONCLUSIVE", "권한 거부 응답이 확인되지 않았습니다.")
        )
    consistent = (
        attempt.get("response") == "ACCEPTED"
        and before.report_id == after.report_id
        and before.report_status == after.report_status
        and before.reviews == after.reviews
        and before.invitation_status == after.invitation_status
        and after.pipeline_row_version == before.pipeline_row_version + 1
        and after.recruiting_stage_id == subject.target_stage_id
    )
    audit = [
        a
        for a in after.audits
        if a.action == "applicant_pipeline.moved"
        and a.result == "success"
        and a.actor_type == "company_user"
        and a.actor_id == subject.reviewer_id
        and a.request_id == subject.request_id
    ]
    if not consistent:
        return "FAIL", "정상 회사 담당자의 채용 단계 변경 결과가 기대와 다릅니다."
    return (
        (
            "PASS",
            "회사 담당자의 요청으로 채용 단계가 변경되고 담당자의 감사 기록이 남았습니다. 이 경로는 별도 최종 결정 검토 기록을 만들지 않습니다.",
        )
        if len(audit) == 1
        else ("INCONCLUSIVE", "회사 담당자의 실제 감사 기록이 확인되지 않았습니다.")
    )


def validate_records(run_id, rows):
    if len(rows) != 15 or {(r["path"], r["subject"]["case"]) for r in rows} != {
        (p, c.value) for p in PATHS for c in H01Case
    }:
        raise ValueError("H01 requires all 15 distinct path/actor cases")
    companies, reviewers, invitations = set(), set(), set()
    for row in rows:
        s = H01Subject.model_validate(row["subject"])
        if s.run_id != uuid5(NAMESPACE, f"{UUID(str(run_id))}:{row['path']}:{s.case}"):
            raise ValueError("H01 case does not belong to root Run")
        companies.add(s.company_id)
        reviewers.add(s.reviewer_id)
        invitations.add(s.invitation_id)
    if len(companies) != 1 or len(reviewers) != 1 or len(invitations) != 15:
        raise ValueError("H01 owned subjects are not isolated")


def aggregate(statuses):
    return (
        "FAIL" if "FAIL" in statuses else "INCONCLUSIVE" if "INCONCLUSIVE" in statuses else "PASS"
    )


def cleanup_verified(recovery):
    counts = recovery.get("owned_residue_counts", {})
    required = {
        "invitations",
        "reports",
        "human_reviews",
        "audit_events",
        "command_idempotency",
        "outbox_events",
        "processed_messages",
        "assistant_retrieval_documents",
    }
    return (
        recovery.get("status") == "SUCCEEDED"
        and required.issubset(counts)
        and all(type(value) is int and value == 0 for value in counts.values())
    )
