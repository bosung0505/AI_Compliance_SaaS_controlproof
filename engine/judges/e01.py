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
    CitationCase,
    CitationMode,
    CitationOutcome,
    EmissionStatus,
    InconclusiveReason,
    LaneCriterion,
    ModelEmissionReceipt,
    Presence,
    ReportLane,
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
