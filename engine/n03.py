"""N-03 stale-consent judge: pure functions over sealed attempt and projection rows (contracts/assertions-v9.md).

N03-U1~U3 and N03-L1 are never judged here; the executor carries them in Judgement.unverified_scope.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from engine.models import AssertionResult, ConsentStateSnapshot, N03LaneId, Presence

REQUIRED_RESIDUE_TABLES = frozenset(
    {
        "invitations",
        "applicant_profiles",
        "applicant_access_sessions",
        "consent_records",
        "invitation_state_history",
        "outbox_events",
        "processed_messages",
        "audit_events",
    }
)
REJECTED_CODES = frozenset({"CONSENT_POLICY_MISMATCH", "CONSENT_COMMIT_REJECTED"})
TRANSPORT_CODES = frozenset({"CONSENT_COMMIT_TRANSPORT_UNAVAILABLE", "CONSENT_COMMIT_RESPONSE_UNKNOWN"})
SOURCE = ("V4-N03",)


class N03Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class N03Identifier(N03Model):
    version: str
    digest: str


class N03Subject(N03Model):
    run_id: UUID
    lane_id: N03LaneId
    subject_ref: str
    invitation_id: UUID
    applicant_id: UUID | None = None


class N03StoredPolicy(N03Model):
    policy_version: str
    evidence_digest: str


class N03StaleAttempt(N03Model):
    subject: N03Subject
    current: N03Identifier
    submitted: N03Identifier
    response_status: int | None = None
    adapter_code: str
    durable_state: str


class N03LatestCommit(N03Model):
    subject: N03Subject
    reread: N03Identifier
    response_status: int | None = None
    adapter_code: str
    stored: N03StoredPolicy | None = None
    consent_record_id: UUID | None = None


def aggregate(statuses):
    return (
        "FAIL" if "FAIL" in statuses else "INCONCLUSIVE" if "INCONCLUSIVE" in statuses else "PASS"
    )


def cleanup_verified(recovery):
    counts = recovery.get("owned_residue_counts", {})
    return (
        recovery.get("status") == "SUCCEEDED"
        and REQUIRED_RESIDUE_TABLES.issubset(counts)
        and all(type(value) is int and value == 0 for value in counts.values())
    )


def _success(status: int | None) -> bool:
    return status is not None and 200 <= status < 300


def _readable(state: ConsentStateSnapshot | None) -> bool:
    return state is not None and state.source_status is not Presence.UNAVAILABLE


def assess_stale(
    attempt: N03StaleAttempt, before: ConsentStateSnapshot | None, after: ConsentStateSnapshot | None
) -> tuple[str, str]:
    if attempt.submitted.version == attempt.current.version or attempt.submitted.digest == attempt.current.digest:
        return "INCONCLUSIVE", "실행기 결함: 이전 식별값이 현재와 같음."
    if not (_readable(before) and _readable(after)):
        return "INCONCLUSIVE", "이전 식별값 제출 전후의 동의 상태를 읽지 못했습니다."
    if _success(attempt.response_status):
        return "FAIL", f"이전 정책 식별값 제출이 성공 응답({attempt.response_status})을 받았습니다."
    if before.state_digest != after.state_digest:
        return "FAIL", "이전 정책 식별값 제출 뒤 동의 기록·초대 상태·상태 이력·outbox가 바뀌었습니다."
    if attempt.adapter_code in TRANSPORT_CODES:
        return "INCONCLUSIVE", f"제출 응답을 받지 못했습니다({attempt.adapter_code})."
    if attempt.adapter_code in REJECTED_CODES:
        return "PASS", f"이전 정책 식별값 제출이 거부({attempt.response_status})됐고 동의 상태가 그대로입니다."
    return "INCONCLUSIVE", f"제출 결과를 거부로 확인하지 못했습니다({attempt.adapter_code})."


def assess_latest(commit: N03LatestCommit) -> tuple[str, str]:
    if commit.stored is None or commit.response_status is None:
        return "INCONCLUSIVE", "재조회 값으로 낸 동의의 응답이나 저장 기록을 읽지 못했습니다."
    if (
        _success(commit.response_status)
        and commit.stored.policy_version == commit.reread.version
        and commit.stored.evidence_digest == commit.reread.digest
    ):
        return "PASS", "재조회한 정책 값으로 동의가 저장됐고 저장 기록의 버전·해시가 같습니다."
    return "FAIL", f"재조회 값 제출이 저장되지 않았거나({commit.response_status}) 저장 기록 값이 다릅니다."


def assess_past(before: ConsentStateSnapshot | None, after: ConsentStateSnapshot | None) -> tuple[str, str]:
    if not (_readable(before) and _readable(after)):
        return "INCONCLUSIVE", "과거 동의 기록의 전후를 읽지 못했습니다."
    if (
        before.source_status is Presence.PRESENT
        and after.source_status is Presence.PRESENT
        and before.state_digest == after.state_digest
        and before.consent_record_ids == after.consent_record_ids
    ):
        return "PASS", "이미 완료된 과거 동의 기록이 시험 전과 같습니다."
    return "FAIL", "이미 완료된 과거 동의 기록이 시험 전과 다릅니다."


def _state(row: dict | None) -> ConsentStateSnapshot | None:
    return ConsentStateSnapshot.model_validate(row) if row is not None else None


def _digest(state: ConsentStateSnapshot | None) -> dict[str, Any] | None:
    if state is None:
        return None
    return {
        "source_status": state.source_status.value,
        "state_digest": state.state_digest,
        "consent_record_ids": [str(value) for value in state.consent_record_ids],
    }


def _result(assertion_id, subject_ref, status, expected, actual, detail) -> AssertionResult:
    return AssertionResult(
        assertion_id=assertion_id,
        subject_ref=subject_ref,
        status=status,
        expected=expected,
        actual=actual,
        reason_code="INSUFFICIENT_EVIDENCE" if status == "INCONCLUSIVE" else None,
        detail=detail,
        source_requirements=SOURCE,
    )


def assertions_for(
    stale_attempt, stale_before, stale_after, latest_commit, past_before, past_after, recovery
) -> tuple[AssertionResult, ...]:
    """Each assertion reads only its own rows; `recovery` is judged by `verdict_for`."""
    attempt = N03StaleAttempt.model_validate(stale_attempt)
    before, after = _state(stale_before), _state(stale_after)
    commit = N03LatestCommit.model_validate(latest_commit)
    past = (_state(past_before), _state(past_after))
    stale = assess_stale(attempt, before, after)
    latest = assess_latest(commit)
    unchanged = assess_past(*past)
    return (
        _result(
            "N03-A1",
            "stale",
            stale[0],
            {"response": "non-2xx", "state": "unchanged", "submitted_differs_from_current": True},
            {
                "submitted": attempt.submitted.model_dump(),
                "current": attempt.current.model_dump(),
                "response_status": attempt.response_status,
                "adapter_code": attempt.adapter_code,
                "before": _digest(before),
                "after": _digest(after),
            },
            stale[1],
        ),
        _result(
            "N03-A2",
            "stale",
            latest[0],
            {"response": "2xx", "stored == reread": True},
            {
                "reread": commit.reread.model_dump(),
                "response_status": commit.response_status,
                "stored": commit.stored.model_dump() if commit.stored else None,
            },
            latest[1],
        ),
        _result(
            "N03-A3",
            "past",
            unchanged[0],
            {"state": "unchanged"},
            {"before": _digest(past[0]), "after": _digest(past[1])},
            unchanged[1],
        ),
    )


def verdict_for(assertions, recovery) -> str:
    if not cleanup_verified(recovery):
        return "INCONCLUSIVE"
    return aggregate([item.status.value for item in assertions])
