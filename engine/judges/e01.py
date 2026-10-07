"""Evidence-only E-01 judgement (contracts/scenario-profile-v4.md).

E01-A1/A2 judge what the report worker stored for each citation mode, cross-checked against the fixed model's
own emission receipt. Contract reason codes that are not `InconclusiveReason` members are carried as a
`detail` prefix under `INSUFFICIENT_EVIDENCE` (ID-004-12): `PRECONDITION_NOT_MET`, `FIXTURE_EMISSION_MISMATCH`.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from uuid import UUID

from engine.models import (
    AssertionResult,
    AssertionStatus,
    ChangeInjection,
    ChangeInjectionState,
    CitationCase,
    CitationMode,
    CitationOutcome,
    EmissionStatus,
    InconclusiveReason,
    LaneCriterion,
    ModelEmissionReceipt,
    Presence,
    ReportLane,
    ReportReadSnapshot,
    ReportRecordSnapshot,
)

INVALID_MODES = (
    CitationMode.EMPTY,
    CitationMode.NONEXISTENT,
    CitationMode.OTHER_APPLICANT,
    CitationMode.OTHER_CRITERION,
)
EMPTY_TEXT_SHA256 = hashlib.sha256(b"").hexdigest()
PRECONDITION_NOT_MET = "PRECONDITION_NOT_MET"
FIXTURE_EMISSION_MISMATCH = "FIXTURE_EMISSION_MISMATCH"


def _item_for(record: ReportRecordSnapshot, criterion_id: UUID):
    return next((item for item in record.items if item.criterion_id == criterion_id), None)


def _evidence_for(record: ReportRecordSnapshot, criterion_id: UUID) -> tuple[UUID, ...]:
    return tuple(item.evidence_id for item in record.evidence if item.criterion_id == criterion_id)


def intended_quoted_ids(
    criterion: LaneCriterion, lane: ReportLane, record: ReportRecordSnapshot
) -> tuple[UUID, ...]:
    """What the fixture is meant to cite for this criterion (fixture contract marker table)."""
    mode = criterion.citation_mode or CitationMode.VALID
    if mode is CitationMode.VALID:
        return _evidence_for(record, criterion.criterion_id)[:1]
    if mode is CitationMode.EMPTY:
        return ()
    if mode in {CitationMode.NONEXISTENT, CitationMode.OTHER_APPLICANT}:
        return (UUID(str(criterion.mode_argument)),)
    referenced = UUID(str(criterion.mode_argument))
    return _evidence_for(record, referenced)[:1]


def build_citation_cases(
    *, lane: ReportLane, record: ReportRecordSnapshot, receipts: Iterable[ModelEmissionReceipt]
) -> tuple[CitationCase, ...]:
    by_criterion = {}
    for receipt in receipts:
        by_criterion.setdefault(receipt.criterion_id, receipt)
    cases = []
    for criterion in lane.criteria:
        mode = criterion.citation_mode or CitationMode.VALID
        item = (
            _item_for(record, criterion.criterion_id)
            if record.source_status is Presence.PRESENT
            else None
        )
        receipt = by_criterion.get(criterion.criterion_id)
        intended = intended_quoted_ids(criterion, lane, record) if item is not None else ()
        own = _evidence_for(record, criterion.criterion_id)
        if item is None:
            cases.append(
                CitationCase(
                    case_id=f"{lane.lane_id.value}:{criterion.code}",
                    mode=mode,
                    intended_quoted_ids=intended,
                    emission_receipt_id=receipt.receipt_id if receipt else None,
                    stored_axes=(),
                    stored_evidence_ids=(),
                    invalid_id_present=False,
                    rationale_present=False,
                    outcome=CitationOutcome.NOT_PRODUCED,
                )
            )
            continue
        quoted = {value for axis in item.axes for value in axis.quoted_evidence_ids}
        scored = any(axis.score is not None for axis in item.axes)
        rationale_present = all(axis.rationale_sha256 != EMPTY_TEXT_SHA256 for axis in item.axes)
        if mode is CitationMode.VALID:
            invalid = False
            valid = bool(item.axes) and all(
                axis.score is not None
                and axis.quoted_evidence_ids
                and set(axis.quoted_evidence_ids) <= set(own)
                for axis in item.axes
            )
            outcome = CitationOutcome.STORED_VALID if valid else CitationOutcome.EMPTIED
        else:
            # Scope is the criterion's own item: an OTHER_CRITERION ID legitimately belongs to the
            # VALID item and an OTHER_APPLICANT ID to the reference report (spec FR-011).
            invalid = bool(set(intended) & (quoted | set(own)))
            outcome = (
                CitationOutcome.STORED_INVALID if (scored or invalid) else CitationOutcome.EMPTIED
            )
        cases.append(
            CitationCase(
                case_id=f"{lane.lane_id.value}:{criterion.code}",
                mode=mode,
                intended_quoted_ids=intended,
                emission_receipt_id=receipt.receipt_id if receipt else None,
                stored_axes=item.axes,
                stored_evidence_ids=own,
                invalid_id_present=invalid,
                rationale_present=rationale_present,
                outcome=outcome,
            )
        )
    return tuple(cases)


def _receipt_problem(case: CitationCase, receipts: dict[UUID, ModelEmissionReceipt]) -> str | None:
    receipt = receipts.get(case.emission_receipt_id) if case.emission_receipt_id else None
    if receipt is None:
        return f"{FIXTURE_EMISSION_MISMATCH}: {case.mode.value} has no emission receipt"
    if receipt.mode_status is not EmissionStatus.EMITTED or receipt.mode.value != case.mode.value:
        return (
            f"{FIXTURE_EMISSION_MISMATCH}: {case.mode.value} receipt is {receipt.mode_status.value}"
        )
    if tuple(receipt.emitted_quoted_ids) != tuple(case.intended_quoted_ids):
        return (
            f"{FIXTURE_EMISSION_MISMATCH}: {case.mode.value} emitted other citations than intended"
        )
    if receipt.emitted_score is None:
        return f"{FIXTURE_EMISSION_MISMATCH}: {case.mode.value} emitted no score"
    return None


def _result(
    assertion_id: str,
    status: AssertionStatus,
    detail: str,
    actual: object,
    expected: object,
    sources,
):
    return AssertionResult(
        assertion_id=assertion_id,
        subject_ref="E01_CITATION_MATRIX",
        status=status,
        expected=expected,
        actual=actual,
        reason_code=InconclusiveReason.INSUFFICIENT_EVIDENCE
        if status is AssertionStatus.INCONCLUSIVE
        else None,
        detail=detail,
        source_requirements=sources,
    )


def judge_e01_citations(
    *,
    cases: tuple[CitationCase, ...],
    receipts: Iterable[ModelEmissionReceipt],
    reference_digests: tuple[str | None, str | None],
) -> tuple[AssertionResult, AssertionResult]:
    by_receipt = {receipt.receipt_id: receipt for receipt in receipts}
    by_mode = {case.mode: case for case in cases}
    actual = {case.mode.value: case.outcome.value for case in cases}

    failures, inconclusive = [], []
    for mode in INVALID_MODES:
        case = by_mode.get(mode)
        if case is None or case.outcome is CitationOutcome.NOT_PRODUCED:
            inconclusive.append(
                f"{PRECONDITION_NOT_MET}: {mode.value} report item was not produced"
            )
            continue
        if case.outcome is CitationOutcome.STORED_INVALID:
            failures.append(f"{mode.value} stored a score or an invalid citation")
        elif not case.rationale_present:
            failures.append(f"{mode.value} emptied the score without a reason")
        problem = _receipt_problem(case, by_receipt)
        if problem:
            inconclusive.append(problem)
    before, after = reference_digests
    if before is None or after is None:
        inconclusive.append(f"{PRECONDITION_NOT_MET}: reference report record unavailable")
    elif before != after:
        failures.append("the reference applicant's report changed")
    expected_a1 = {"invalid_modes": "EMPTIED", "reference": "UNCHANGED"}
    if failures:
        a1 = _result(
            "E01-A1", AssertionStatus.FAIL, "; ".join(failures), actual, expected_a1, ("FR-011",)
        )
    elif inconclusive:
        a1 = _result(
            "E01-A1",
            AssertionStatus.INCONCLUSIVE,
            "; ".join(inconclusive),
            actual,
            expected_a1,
            ("FR-010",),
        )
    else:
        a1 = _result(
            "E01-A1",
            AssertionStatus.PASS,
            "네 잘못된 인용 모드가 모두 작업자 검증에서 비워졌고 참조 보고서는 변하지 않았습니다.",
            actual,
            expected_a1,
            ("FR-010", "FR-011", "FR-012"),
        )

    valid = by_mode.get(CitationMode.VALID)
    expected_a2 = {"valid_mode": "STORED_VALID"}
    if valid is None or valid.outcome is CitationOutcome.NOT_PRODUCED:
        a2 = _result(
            "E01-A2",
            AssertionStatus.INCONCLUSIVE,
            f"{PRECONDITION_NOT_MET}: VALID report item was not produced",
            actual,
            expected_a2,
            ("FR-010",),
        )
    elif valid.outcome is not CitationOutcome.STORED_VALID:
        a2 = _result(
            "E01-A2",
            AssertionStatus.FAIL,
            "a valid citation was not stored",
            actual,
            expected_a2,
            ("FR-011",),
        )
    elif problem := _receipt_problem(valid, by_receipt):
        a2 = _result(
            "E01-A2", AssertionStatus.INCONCLUSIVE, problem, actual, expected_a2, ("FR-010",)
        )
    else:
        a2 = _result(
            "E01-A2",
            AssertionStatus.PASS,
            "유효한 인용의 점수·인용이 같은 항목의 Evidence로 저장됐습니다.",
            actual,
            expected_a2,
            ("FR-010", "FR-011"),
        )
    return a1, a2


# --- E01-A3/A4: evidence removal and restore (US2) ---------------------------------------------

UNSUPPORTED_STATES = {"insufficient_evidence", "needs_follow_up"}
AVAILABILITY_FIELDS = ("playable", "available", "transcript_available")


def _items(read: ReportReadSnapshot | None) -> dict[str, dict]:
    report = (read.report if read is not None else None) or {}
    return {str(item.get("report_item_id")): item for item in report.get("items") or ()}


def affected_scope(
    pre: ReportReadSnapshot, removed_segment_ids: set[str]
) -> tuple[set[str], set[str]]:
    """Evidence IDs on the removed segments and the items that own or cite them (PRE_REMOVAL)."""
    evidence_ids: set[str] = set()
    item_ids: set[str] = set()
    for item_id, item in _items(pre).items():
        for entry in item.get("evidence") or ():
            if str(entry.get("transcript_segment_id")) in removed_segment_ids:
                evidence_ids.add(str(entry.get("evidence_id")))
                item_ids.add(item_id)
    for item_id, item in _items(pre).items():
        for axis in item.get("axis_assessments") or ():
            if evidence_ids & {str(value) for value in axis.get("quoted_evidence_ids") or ()}:
                item_ids.add(item_id)
    return evidence_ids, item_ids


def _item_indicator(item: dict, evidence_ids: set[str]) -> str | None:
    if item.get("average_score") is None:
        return "average_null"
    if item.get("assessment_state") in UNSUPPORTED_STATES:
        return "state"
    for entry in item.get("evidence") or ():
        if str(entry.get("evidence_id")) in evidence_ids and any(
            entry.get(name) is False for name in AVAILABILITY_FIELDS
        ):
            return "availability"
    cited = [
        axis
        for axis in item.get("axis_assessments") or ()
        if evidence_ids & {str(value) for value in axis.get("quoted_evidence_ids") or ()}
    ]
    if cited and all(axis.get("score") is None for axis in cited):
        return "axis_null"
    return None


def _a3(status: AssertionStatus, detail: str, actual: object, sources=("FR-020",)):
    return AssertionResult(
        assertion_id="E01-A3",
        subject_ref="E01_EVIDENCE_REMOVAL",
        status=status,
        expected={"indicator": "H-4", "unaffected": "UNCHANGED"},
        actual=actual,
        reason_code=InconclusiveReason.INSUFFICIENT_EVIDENCE
        if status is AssertionStatus.INCONCLUSIVE
        else None,
        detail=detail,
        source_requirements=sources,
    )


def _removal_precondition(injection, pre, post) -> AssertionResult | None:
    if not isinstance(injection, ChangeInjection) or (
        injection.apply_receipt.get("absence_confirmed") is not True
    ):
        code = getattr(injection, "code", None) or "NOT_APPLIED"
        return _a3(
            AssertionStatus.INCONCLUSIVE,
            f"{PRECONDITION_NOT_MET}: evidence removal not confirmed ({code})",
            {"removal": code},
        )
    if pre is None or pre.status_code != 200 or not _items(pre):
        return _a3(
            AssertionStatus.INCONCLUSIVE,
            f"{PRECONDITION_NOT_MET}: PRE_REMOVAL report read failed",
            {"pre_status": None if pre is None else pre.status_code},
        )
    if post is None:
        return _a3(
            AssertionStatus.INCONCLUSIVE, f"{PRECONDITION_NOT_MET}: POST_REMOVAL not read", {}
        )
    if post.status_code >= 500:
        return _a3(
            AssertionStatus.FAIL,
            "REPORT_UNREADABLE_AFTER_REMOVAL: the report read failed after evidence removal",
            {"post_status": post.status_code},
            ("FR-021",),
        )
    unknown = sorted(set(pre.unknown_fields) | set(post.unknown_fields))
    if unknown:
        return _a3(
            AssertionStatus.INCONCLUSIVE,
            f"UNKNOWN_FIELDS: indicator judgement needs a scenario revision ({', '.join(unknown)})",
            {"unknown_fields": unknown},
        )
    if post.status_code != 200:
        return _a3(
            AssertionStatus.INCONCLUSIVE,
            f"{PRECONDITION_NOT_MET}: POST_REMOVAL read returned {post.status_code}",
            {"post_status": post.status_code},
        )
    return None


def judge_e01_removal(*, injection, pre, post) -> AssertionResult:
    """E01-A3: every affected axis/item shows an H-4 indicator; unaffected items are unchanged."""
    blocked = _removal_precondition(injection, pre, post)
    if blocked is not None:
        return blocked
    evidence_ids, affected = affected_scope(pre, {str(value) for value in injection.target_ids})
    if not affected:
        return _a3(
            AssertionStatus.INCONCLUSIVE,
            f"{PRECONDITION_NOT_MET}: no report item cites the removed segment",
            {"affected_items": 0},
        )
    before, after = _items(pre), _items(post)
    indicators: dict[str, str] = {}
    unexposed: list[str] = []
    changed_without: list[str] = []
    for item_id in sorted(affected):
        item = after.get(item_id)
        indicator = None if item is None else _item_indicator(item, evidence_ids)
        if indicator:
            indicators[item_id] = indicator
        elif item == before[item_id]:
            unexposed.append(item_id)
        else:
            changed_without.append(item_id)
    failures = []
    if unexposed:
        failures.append("P1: an affected item kept its score and citation after evidence removal")
    if any(after.get(key) != item for key, item in before.items() if key not in affected):
        failures.append("an item not citing the removed evidence changed")
    actual = {
        "indicators": indicators,
        "unexposed": unexposed,
        "changed_without_indicator": changed_without,
    }
    if failures:
        return _a3(AssertionStatus.FAIL, "; ".join(failures), actual, ("FR-020", "FR-021"))
    if changed_without:
        # Neither an H-4 indicator nor the P1 shape (ID-004-16).
        return _a3(
            AssertionStatus.INCONCLUSIVE,
            "INDICATOR_AMBIGUOUS: an affected item changed without an H-4 indicator",
            actual,
        )
    return _a3(
        AssertionStatus.PASS,
        "근거가 제거된 모든 축·항목이 근거 부족 지표를 보였고 다른 항목은 그대로였습니다.",
        actual,
        ("FR-020", "FR-021"),
    )


def judge_e01_restore(
    *, injection, pre_read, post_restore_read, pre_record, post_restore_record
) -> AssertionResult:
    """E01-A4: a safe restore brings back the PRE_REMOVAL read and record projections."""

    def result(status, detail, actual):
        return AssertionResult(
            assertion_id="E01-A4",
            subject_ref="E01_EVIDENCE_REMOVAL",
            status=status,
            expected={"post_restore": "EQUALS_PRE_REMOVAL"},
            actual=actual,
            reason_code=InconclusiveReason.INSUFFICIENT_EVIDENCE
            if status is AssertionStatus.INCONCLUSIVE
            else None,
            detail=detail,
            source_requirements=("FR-022",),
        )

    if not isinstance(injection, ChangeInjection) or (
        injection.state is not ChangeInjectionState.RESTORED
    ):
        state = getattr(getattr(injection, "state", None), "value", "NOT_APPLIED")
        return result(
            AssertionStatus.INCONCLUSIVE,
            f"{PRECONDITION_NOT_MET}: evidence restore not confirmed ({state})",
            {"restore": state},
        )
    reads = (pre_read, post_restore_read, pre_record, post_restore_record)
    if any(value is None for value in reads):
        return result(
            AssertionStatus.INCONCLUSIVE, f"{PRECONDITION_NOT_MET}: restore reads missing", {}
        )
    read_equal = (pre_read.status_code, pre_read.report) == (
        post_restore_read.status_code,
        post_restore_read.report,
    )
    record_equal = pre_record.state_digest == post_restore_record.state_digest
    actual = {"read_equal": read_equal, "record_equal": record_equal}
    if read_equal and record_equal:
        return result(
            AssertionStatus.PASS, "근거 복원 뒤 보고서 조회와 기록이 제거 전과 같습니다.", actual
        )
    return result(
        AssertionStatus.FAIL, "the restore was safe but the report differs from PRE_REMOVAL", actual
    )


# --- E01-D1: storage probe exposure (diagnostic only, never an assertion) ----------------------


def storage_probe_exposure(*, written_axes, read, report_item_id: str) -> list[dict]:
    """Per written axis: SHOWN_AS_WRITTEN, AXIS_DROPPED, SCORE_HIDDEN or READ_ERROR."""
    readable = getattr(read, "status_code", None) == 200
    item = _items(read).get(str(report_item_id)) if readable else None
    rows = []
    for axis in written_axes:
        if item is None:
            exposure = "READ_ERROR"
        else:
            shown = next(
                (
                    value
                    for value in item.get("axis_assessments") or ()
                    if value.get("axis") == axis["axis"]
                ),
                None,
            )
            if shown is None:
                exposure = "AXIS_DROPPED"
            elif shown.get("score") is None:
                exposure = "SCORE_HIDDEN"
            else:
                exposure = "SHOWN_AS_WRITTEN"
        rows.append({"mode": axis["mode"], "axis": axis["axis"], "exposure": exposure})
    return rows
