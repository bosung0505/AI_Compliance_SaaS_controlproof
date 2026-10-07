"""T033 — E01-A1/A2 evidence-only judgement (contracts/scenario-profile-v4.md).

RED until T041 creates `engine/judges/e01.py` (strict xfail, ID-004-01). Contract reason codes that are not
`InconclusiveReason` members are carried as a `detail` prefix under `INSUFFICIENT_EVIDENCE` (ID-004-12).
"""

from __future__ import annotations

import hashlib
from importlib import import_module
from uuid import UUID

import pytest

from engine.models import (
    AssertionStatus,
    CitationMode,
    InconclusiveReason,
    ModelEmissionReceipt,
    ReportRecordSnapshot,
)
from tests.fixtures import spec004 as fx

EMPTY_SHA = hashlib.sha256(b"").hexdigest()
REFERENCE_EVIDENCE = fx.uuid7_at(fx.FIXED_AT, 90)


def e01():
    return import_module("engine.judges.e01")


def _matrix():
    from engine.models import ReportLane

    return ReportLane.model_validate(
        fx.report_lane(
            "E01_CITATION_MATRIX", fx.matrix_criteria(reference_evidence_id=REFERENCE_EVIDENCE)
        )
    )


def _record(lane, *, stored: dict[str, dict]) -> ReportRecordSnapshot:
    """A matrix report record; `stored[mode]` overrides that criterion's axis score/quotes."""
    items, evidence = [], []
    for criterion in lane.criteria:
        mode = criterion.citation_mode.value
        own = str(fx.uuid7_at(fx.FIXED_AT, 1 + list(fx.CITATION_MODES).index(mode)))
        override = stored.get(mode, {})
        valid = mode == "VALID"
        score = override.get("score", 72 if valid else None)
        quoted = override.get("quoted", [own] if valid else [])
        item_id = str(fx.sid("item", criterion.criterion_id))
        items.append(
            {
                "report_item_id": item_id,
                "criterion_id": str(criterion.criterion_id),
                "competency_model_version_id": str(lane.competency_model_version_id),
                "assessment_state": "confirmed",
                "criterion_weight": criterion.weight,
                "axis_weights": {},
                "axes": [
                    fx.stored_axis(axis, score=score, quoted=quoted, unverified=not valid)
                    | override.get("axis", {})
                    for axis in fx.AXES
                ],
                "observation_sha256": fx.TEXT_DIGEST,
                "rationale_sha256": fx.TEXT_DIGEST,
                "uncertainty_sha256": fx.TEXT_DIGEST,
            }
        )
        rows = [own, *override.get("extra_evidence", [])]
        for evidence_id in rows:
            evidence.append(
                {
                    "evidence_id": evidence_id,
                    "report_item_id": item_id,
                    "criterion_id": str(criterion.criterion_id),
                    "competency_model_version_id": str(lane.competency_model_version_id),
                    "answer_turn_id": str(criterion.answer_turn_id),
                    "transcript_segment_id": str(criterion.transcript_segment_id),
                    "video_start_ms": 1000,
                    "video_end_ms": 9000,
                    "sufficiency": "direct",
                    "observation_sha256": fx.TEXT_DIGEST,
                    "rationale_sha256": fx.TEXT_DIGEST,
                }
            )
    return ReportRecordSnapshot.model_validate(
        fx.report_record(
            "E01_CITATION_MATRIX", "GENERATED", items, overall_score=72, scoring_inputs={}
        )
        | {"evidence": evidence, "report_id": str(fx.sid("report", "matrix"))}
    )


def _receipts(lane, record, *, overrides: dict[str, dict] | None = None):
    overrides = overrides or {}
    receipts = []
    for criterion in lane.criteria:
        mode = criterion.citation_mode.value
        intended = e01().intended_quoted_ids(criterion, lane, record)
        receipts.append(
            ModelEmissionReceipt.model_validate(
                fx.emission_receipt(
                    str(criterion.criterion_id),
                    mode=mode,
                    provided=[
                        str(item.evidence_id)
                        for item in record.evidence
                        if item.criterion_id == criterion.criterion_id
                    ],
                    quoted=[str(value) for value in intended],
                )
                | overrides.get(mode, {})
            )
        )
    return tuple(receipts)


def _judge(record, receipts, lane, *, reference=("a" * 64, "a" * 64)):
    module = e01()
    cases = module.build_citation_cases(lane=lane, record=record, receipts=receipts)
    return module.judge_e01_citations(cases=cases, receipts=receipts, reference_digests=reference)


def test_intended_ids_follow_the_marker_rules() -> None:
    lane = _matrix()
    record = _record(lane, stored={})
    by_mode = {item.citation_mode: item for item in lane.criteria}
    module = e01()
    valid_item = next(
        item
        for item in record.evidence
        if item.criterion_id == by_mode[CitationMode.VALID].criterion_id
    )
    assert module.intended_quoted_ids(by_mode[CitationMode.EMPTY], lane, record) == ()
    assert module.intended_quoted_ids(by_mode[CitationMode.OTHER_APPLICANT], lane, record) == (
        REFERENCE_EVIDENCE,
    )
    assert module.intended_quoted_ids(by_mode[CitationMode.OTHER_CRITERION], lane, record) == (
        valid_item.evidence_id,
    )
    assert module.intended_quoted_ids(by_mode[CitationMode.NONEXISTENT], lane, record) == (
        UUID(by_mode[CitationMode.NONEXISTENT].mode_argument),
    )


def test_worker_emptied_invalid_citations_pass_a1_and_valid_passes_a2() -> None:
    lane = _matrix()
    record = _record(lane, stored={})
    a1, a2 = _judge(record, _receipts(lane, record), lane)
    assert a1.status is AssertionStatus.PASS, a1.detail
    assert a2.status is AssertionStatus.PASS, a2.detail


@pytest.mark.parametrize("mode", fx.INVALID_MODES)
def test_a_residual_score_fails_a1(mode: str) -> None:
    lane = _matrix()
    record = _record(lane, stored={mode: {"score": 72}})
    a1, _ = _judge(record, _receipts(lane, record), lane)
    assert a1.status is AssertionStatus.FAIL
    assert mode in a1.detail


@pytest.mark.parametrize("mode", ["NONEXISTENT", "OTHER_APPLICANT", "OTHER_CRITERION"])
def test_an_invalid_id_left_in_the_item_fails_a1(mode: str) -> None:
    lane = _matrix()
    clean = _record(lane, stored={})
    criterion = next(item for item in lane.criteria if item.citation_mode.value == mode)
    invalid = [str(value) for value in e01().intended_quoted_ids(criterion, lane, clean)]
    record = _record(lane, stored={mode: {"quoted": invalid}})
    a1, _ = _judge(record, _receipts(lane, record), lane)
    assert a1.status is AssertionStatus.FAIL


def test_an_invalid_id_stored_as_an_item_evidence_row_fails_a1() -> None:
    lane = _matrix()
    record = _record(
        lane, stored={"OTHER_APPLICANT": {"extra_evidence": [str(REFERENCE_EVIDENCE)]}}
    )
    a1, _ = _judge(record, _receipts(lane, record), lane)
    assert a1.status is AssertionStatus.FAIL


def test_other_criterion_id_in_its_own_item_is_not_a_violation() -> None:
    """ID-004 scope rule: the referenced VALID item legitimately holds that Evidence row."""
    lane = _matrix()
    record = _record(lane, stored={})
    a1, _ = _judge(record, _receipts(lane, record), lane)
    assert a1.status is AssertionStatus.PASS


def test_reference_report_change_fails_a1() -> None:
    lane = _matrix()
    record = _record(lane, stored={})
    a1, _ = _judge(record, _receipts(lane, record), lane, reference=("a" * 64, "b" * 64))
    assert a1.status is AssertionStatus.FAIL


@pytest.mark.parametrize(
    "overrides,prefix",
    [
        ({"EMPTY": {"emitted_quoted_ids": [str(REFERENCE_EVIDENCE)]}}, "FIXTURE_EMISSION_MISMATCH"),
        (
            {
                "OTHER_CRITERION": {
                    "mode_status": "MODE_SOURCE_MISSING",
                    "emitted_quoted_ids": [],
                    "emitted_score": None,
                }
            },
            "FIXTURE_EMISSION_MISMATCH",
        ),
    ],
)
def test_receipt_mismatch_is_inconclusive(overrides, prefix) -> None:
    lane = _matrix()
    record = _record(lane, stored={})
    a1, _ = _judge(record, _receipts(lane, record, overrides=overrides), lane)
    assert a1.status is AssertionStatus.INCONCLUSIVE
    assert a1.reason_code is InconclusiveReason.INSUFFICIENT_EVIDENCE
    assert a1.detail.startswith(prefix)


def test_missing_receipts_or_report_are_inconclusive() -> None:
    lane = _matrix()
    record = _record(lane, stored={})
    a1, a2 = _judge(record, (), lane)
    assert a1.status is AssertionStatus.INCONCLUSIVE
    assert a2.status is AssertionStatus.INCONCLUSIVE
    absent = ReportRecordSnapshot.model_validate(
        fx.report_record(
            "E01_CITATION_MATRIX", "GENERATED", [], overall_score=None, scoring_inputs={}
        )
        | {"report_id": None, "source_status": "ABSENT"}
    )
    a1, a2 = _judge(absent, (), lane)
    assert a1.detail.startswith("PRECONDITION_NOT_MET")
    assert a2.status is AssertionStatus.INCONCLUSIVE


def test_a_direct_violation_outranks_missing_evidence() -> None:
    lane = _matrix()
    record = _record(lane, stored={"EMPTY": {"score": 72}})
    receipts = tuple(item for item in _receipts(lane, record) if item.mode.value != "NONEXISTENT")
    a1, _ = _judge(record, receipts, lane)
    assert a1.status is AssertionStatus.FAIL


def test_unverified_notice_is_recorded_but_not_required() -> None:
    lane = _matrix()
    record = _record(lane, stored={"EMPTY": {"axis": {"rationale_is_unverified_notice": False}}})
    a1, _ = _judge(record, _receipts(lane, record), lane)
    assert a1.status is AssertionStatus.PASS


def test_an_empty_rationale_fails_the_reason_preservation_rule() -> None:
    lane = _matrix()
    record = _record(lane, stored={"EMPTY": {"axis": {"rationale_sha256": EMPTY_SHA}}})
    a1, _ = _judge(record, _receipts(lane, record), lane)
    assert a1.status is AssertionStatus.FAIL


def test_a_valid_citation_emptied_by_the_worker_fails_a2() -> None:
    lane = _matrix()
    record = _record(lane, stored={"VALID": {"score": None, "quoted": []}})
    _, a2 = _judge(record, _receipts(lane, record), lane)
    assert a2.status is AssertionStatus.FAIL
