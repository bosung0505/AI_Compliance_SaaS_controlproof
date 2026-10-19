"""N-01 notice judge: pure functions over sealed lane and policy-identifier rows (contracts/assertions-v9.md)."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from engine.models import AssertionResult, N01LaneId

NOTICE_ITEMS = ("ai_assist", "human_final", "recording_purpose", "retention", "deletion")
VIEWPORTS = {N01LaneId.PC: (1440, 900), N01LaneId.MOBILE: (390, 844)}
FLAGS = ("text_present", "in_viewport", "not_occluded", "no_horizontal_overflow")
REQUIRED_RESIDUE_TABLES = frozenset(
    {
        "invitations",
        "applicant_profiles",
        "applicant_access_tokens",
        "applicant_access_sessions",
        "consent_records",
        "invitation_state_history",
        "outbox_events",
        "processed_messages",
        "audit_events",
    }
)
#: The commit happens after measurement, so a commit failure is judged by N01-A3 only.
POST_MEASUREMENT_ERRORS = frozenset({"BROWSER_COMMIT_FAILED"})
SOURCE = ("V4-N01",)


class N01Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class N01Viewport(N01Model):
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class N01BBox(N01Model):
    x: float
    y: float
    width: float
    height: float


class N01Fragment(N01Model):
    fragment_id: str
    expected_text: str = Field(min_length=1)
    expected_text_digest: str
    text_present: bool
    bbox: N01BBox | None = None
    in_viewport: bool
    center_hit: bool
    not_occluded: bool
    doc_scroll_width: int
    doc_client_width: int
    el_scroll_width: int
    el_client_width: int
    no_horizontal_overflow: bool

    @model_validator(mode="after")
    def digest_matches_text(self) -> N01Fragment:
        if self.expected_text_digest != hashlib.sha256(self.expected_text.encode()).hexdigest():
            raise ValueError("expected_text_digest must be the SHA-256 of expected_text")
        return self

    def false_flags(self) -> tuple[str, ...]:
        return tuple(flag for flag in FLAGS if not getattr(self, flag))


class N01Item(N01Model):
    item_id: Literal["ai_assist", "human_final", "recording_purpose", "retention", "deletion"]
    fragments: tuple[N01Fragment, ...] = Field(min_length=1)


class N01Capture(N01Model):
    file: str | None = None  # the executor names the sealed file; the adapter returns digest and size only
    sha256: str
    bytes: int = Field(gt=0)


class N01Subject(N01Model):
    run_id: UUID
    lane_id: N01LaneId
    subject_ref: str
    invitation_id: UUID
    applicant_id: UUID


class N01LaneRecord(N01Model):
    lane: N01LaneId
    viewport: N01Viewport
    subject: N01Subject
    step_reached: Literal["exchange", "identity", "consent", "ready", "error"]
    capture: N01Capture | None = None
    token_absent_in_dom: bool | None = None
    operations: tuple[dict[str, Any], ...] = ()
    items: tuple[N01Item, ...] = ()
    measurement_error: str | None = None


class N01PolicyValue(N01Model):
    version: str
    digest: str


class N01StoredPolicy(N01Model):
    policy_version: str
    evidence_digest: str


class N01PolicyIdentifiers(N01Model):
    lane: N01LaneId
    subject_ref: str
    screen: N01PolicyValue | None = None
    server: N01PolicyValue | None = None
    stored: N01StoredPolicy | None = None
    consented_at: datetime | None = None
    commit_status: int | None = None


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


def assess_lane(record: N01LaneRecord) -> tuple[str, str]:
    expected = VIEWPORTS[record.lane]
    if (record.viewport.width, record.viewport.height) != expected or record.subject.lane_id != record.lane:
        return "INCONCLUSIVE", "화면 크기나 lane 기록이 계약과 다릅니다."
    if record.step_reached not in {"consent", "ready"}:
        return "INCONCLUSIVE", f"동의 단계에 도달하지 못했습니다({record.step_reached})."
    if record.measurement_error and record.measurement_error not in POST_MEASUREMENT_ERRORS:
        return "INCONCLUSIVE", f"화면 측정이 끝나지 않았습니다({record.measurement_error})."
    if record.capture is None:
        return "INCONCLUSIVE", "화면 캡처가 없습니다."
    ids = [item.item_id for item in record.items]
    if len(ids) != len(NOTICE_ITEMS) or set(ids) != set(NOTICE_ITEMS):
        return "INCONCLUSIVE", "다섯 고지 항목의 측정이 정확히 한 번씩 있지 않습니다."
    if record.token_absent_in_dom is not True:
        return "INCONCLUSIVE", "캡처 전 화면에 원시 토큰·세션 값이 없음을 확인하지 못했습니다."
    failures = [
        f"{item.item_id}/{fragment.fragment_id}({', '.join(fragment.false_flags())})"
        for item in record.items
        for fragment in item.fragments
        if fragment.false_flags()
    ]
    if failures:
        return "FAIL", f"읽을 수 있게 표시되지 않은 고지 조각이 있습니다: {'; '.join(failures)}."
    return "PASS", "다섯 고지 항목의 모든 조각이 화면 안에 가림·가로 넘침 없이 표시됐습니다."


def assess_identifiers(records: list[N01PolicyIdentifiers]) -> tuple[str, str]:
    if len(records) != 2 or {record.lane for record in records} != set(N01LaneId):
        return "INCONCLUSIVE", "두 lane의 정책 식별값 기록이 정확히 하나씩 있지 않습니다."
    if any(None in (record.screen, record.server, record.stored) for record in records):
        return "INCONCLUSIVE", "화면 값·서버 값·저장 기록 중 읽지 못한 값이 있습니다."
    mismatched = [
        record.lane.value
        for record in records
        if not (
            (record.screen.version, record.screen.digest)
            == (record.server.version, record.server.digest)
            == (record.stored.policy_version, record.stored.evidence_digest)
        )
    ]
    if mismatched:
        return "FAIL", f"화면·서버·저장 기록의 정책 식별값이 다른 lane이 있습니다: {', '.join(mismatched)}."
    return "PASS", "두 lane 모두 화면·서버·저장 기록의 정책 버전과 해시가 같습니다."


def _lane_actual(record: N01LaneRecord) -> dict[str, Any]:
    return {
        "step_reached": record.step_reached,
        "viewport": record.viewport.model_dump(),
        "capture": record.capture.model_dump() if record.capture else None,
        "token_absent_in_dom": record.token_absent_in_dom,
        "measurement_error": record.measurement_error,
        "items": [
            {
                "item_id": item.item_id,
                "fragments": [
                    {
                        "fragment_id": fragment.fragment_id,
                        "expected_text_digest": fragment.expected_text_digest,
                        **{flag: getattr(fragment, flag) for flag in FLAGS},
                    }
                    for fragment in item.fragments
                ],
            }
            for item in record.items
        ],
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


def assertions_for(lanes: list[dict], identifiers: list[dict], recovery: dict) -> tuple[AssertionResult, ...]:
    """Each assertion reads only its own rows; `recovery` is judged by `verdict_for`."""
    records = [N01LaneRecord.model_validate(row) for row in lanes]
    results = []
    for assertion_id, lane in (("N01-A1", N01LaneId.PC), ("N01-A2", N01LaneId.MOBILE)):
        width, height = VIEWPORTS[lane]
        expected = {"viewport": {"width": width, "height": height}, "items": list(NOTICE_ITEMS), "flags": list(FLAGS)}
        selected = [record for record in records if record.lane is lane]
        if len(selected) != 1:
            results.append(
                _result(assertion_id, lane.value, "INCONCLUSIVE", expected, None, f"{lane.value} 화면 기록이 하나가 아닙니다.")
            )
            continue
        status, detail = assess_lane(selected[0])
        results.append(_result(assertion_id, lane.value, status, expected, _lane_actual(selected[0]), detail))
    triples = [N01PolicyIdentifiers.model_validate(row) for row in identifiers]
    status, detail = assess_identifiers(triples)
    actual = [
        {
            "lane": triple.lane.value,
            "screen": triple.screen.model_dump() if triple.screen else None,
            "server": triple.server.model_dump() if triple.server else None,
            "stored": triple.stored.model_dump() if triple.stored else None,
        }
        for triple in triples
    ]
    results.append(
        _result("N01-A3", "policy-identifiers", status, {"screen == server == stored": True, "lanes": ["pc", "mobile"]}, actual, detail)
    )
    return tuple(results)


def verdict_for(assertions, recovery) -> str:
    if not cleanup_verified(recovery):
        return "INCONCLUSIVE"
    return aggregate([item.status.value for item in assertions])
