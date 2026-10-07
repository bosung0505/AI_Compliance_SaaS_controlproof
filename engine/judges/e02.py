"""Evidence-only E-02 judgement (T058, contracts/scenario-profile-v4.md).

E02-A1 checks the first report's frozen input set against the v1 snapshot, E02-A2 that publishing v2 left the first
report's record and read unchanged (given the second report is bound to v2), E02-A3 that recomputing with the
pinned WhyYou scoring copy reproduces the five comparison targets of both reports.
"""

from __future__ import annotations

from typing import Any

from engine.judges.e02_scoring import (
    PINNED_SOURCES,
    RULE_COPY_ID,
    Aggregate,
    criterion_aggregate,
    report_aggregate,
)
from engine.models import (
    SPEC004_RECOMPUTE_TOLERANCE,
    AssertionResult,
    AssertionStatus,
    CompetencyVersionStatus,
    CriteriaVersionSnapshot,
    FrozenInputSet,
    InconclusiveReason,
    Presence,
    RecomputeComparison,
    RecomputeRecord,
    RecomputeTarget,
    ReportReadSnapshot,
    ReportRecordSnapshot,
)

PRECONDITION_NOT_MET = "PRECONDITION_NOT_MET"


def _result(assertion_id, status, detail, actual, expected, sources) -> AssertionResult:
    return AssertionResult(
        assertion_id=assertion_id,
        subject_ref="E02_FIRST_APPLICANT" if assertion_id != "E02-A3" else "E02_REPORTS",
        status=status,
        expected=expected,
        actual=actual,
        reason_code=InconclusiveReason.INSUFFICIENT_EVIDENCE
        if status is AssertionStatus.INCONCLUSIVE
        else None,
        detail=detail,
        source_requirements=sources,
    )


def _present(record: ReportRecordSnapshot | None) -> bool:
    return record is not None and record.source_status is Presence.PRESENT


# --- E02-A1 -------------------------------------------------------------------------------------


def frozen_input_set(
    record: ReportRecordSnapshot, version: CriteriaVersionSnapshot
) -> FrozenInputSet:
    missing = [
        name
        for name in ("model_version", "prompt_version", "config_version")
        if not getattr(record, name)
    ]
    if not record.scoring_inputs:
        missing.append("scoring_inputs")
    if not record.items:
        missing.append("items")
    version_ids = {item.competency_model_version_id for item in record.items}
    criterion_weights = {str(item.criterion_id): item.criterion_weight for item in record.items}
    axis_weights = {str(item.criterion_id): dict(item.axis_weights) for item in record.items}
    expected_weights = {str(item.criterion_id): item.weight for item in version.criteria}
    matches = (
        version_ids == {version.competency_model_version_id}
        and criterion_weights == expected_weights
        and all(weights == version.axis_weights for weights in axis_weights.values())
    )
    return FrozenInputSet(
        report_id=record.report_id,
        competency_model_version_id=next(iter(version_ids), version.competency_model_version_id),
        model_version=record.model_version or "",
        prompt_version=record.prompt_version or "",
        config_version=record.config_version or "",
        criterion_weights=criterion_weights,
        axis_weights=axis_weights,
        scoring_inputs_present=bool(record.scoring_inputs),
        missing_fields=tuple(missing),
        matches_version_snapshot=matches,
    )


def judge_e02_frozen(*, first: ReportRecordSnapshot | None, v1: CriteriaVersionSnapshot | None):
    expected = {"frozen": "MATCHES_V1"}
    if not _present(first) or v1 is None:
        return _result(
            "E02-A1",
            AssertionStatus.INCONCLUSIVE,
            f"{PRECONDITION_NOT_MET}: first report or v1 snapshot unavailable",
            {},
            expected,
            ("FR-030",),
        )
    frozen = frozen_input_set(first, v1)
    actual = frozen.model_dump(mode="json")
    if frozen.missing_fields or not frozen.matches_version_snapshot:
        return _result(
            "E02-A1",
            AssertionStatus.FAIL,
            "the first report does not carry the v1 frozen input set",
            actual,
            expected,
            ("FR-030", "FR-033"),
        )
    return _result(
        "E02-A1",
        AssertionStatus.PASS,
        "첫 보고서가 v1 버전·가중치·점수 입력을 스스로 보존합니다.",
        actual,
        expected,
        ("FR-030", "FR-033"),
    )


# --- E02-A2 -------------------------------------------------------------------------------------


def judge_e02_unchanged(
    *, v2, published_v2_id, second, pre_record, post_record, pre_read, post_read
):
    expected = {"first_report": "UNCHANGED"}
    bound = (
        isinstance(v2, CriteriaVersionSnapshot)
        and str(v2.competency_model_version_id) == str(published_v2_id)
        and v2.status is CompetencyVersionStatus.PUBLISHED
        and _present(second)
        and frozen_input_set(second, v2).matches_version_snapshot
    )
    if not bound:
        return _result(
            "E02-A2",
            AssertionStatus.INCONCLUSIVE,
            f"{PRECONDITION_NOT_MET}: the second report is not bound to the published v2",
            {"second_bound_to_v2": False},
            expected,
            ("FR-031",),
        )
    if not (_present(pre_record) and _present(post_record)) or pre_read is None or post_read is None:
        return _result(
            "E02-A2",
            AssertionStatus.INCONCLUSIVE,
            f"{PRECONDITION_NOT_MET}: first report PRE/POST_CHANGE reads unavailable",
            {},
            expected,
            ("FR-031",),
        )
    record_equal = pre_record.state_digest == post_record.state_digest
    read_equal = (pre_read.status_code, pre_read.report) == (post_read.status_code, post_read.report)
    actual = {"record_equal": record_equal, "read_equal": read_equal, "second_bound_to_v2": True}
    if record_equal and read_equal:
        return _result(
            "E02-A2",
            AssertionStatus.PASS,
            "v2 발행과 두 번째 보고서 생성 뒤에도 첫 보고서의 기록과 조회가 같습니다.",
            actual,
            expected,
            ("FR-031", "FR-032"),
        )
    return _result(
        "E02-A2",
        AssertionStatus.FAIL,
        "the first report changed after v2 was published",
        actual,
        expected,
        ("FR-031", "FR-032"),
    )


# --- E02-A3 -------------------------------------------------------------------------------------


def _equal(expected: Any, observed: Any) -> bool:
    if isinstance(expected, bool) or isinstance(observed, bool):
        return expected is observed
    if isinstance(expected, int) and isinstance(observed, int):
        return expected == observed
    if isinstance(expected, (int, float)) and isinstance(observed, (int, float)):
        return abs(float(expected) - float(observed)) <= SPEC004_RECOMPUTE_TOLERANCE
    if isinstance(expected, dict) and isinstance(observed, dict):
        return expected.keys() == observed.keys() and all(
            _equal(expected[key], observed[key]) for key in expected
        )
    if isinstance(expected, (list, tuple)) and isinstance(observed, (list, tuple)):
        return len(expected) == len(observed) and all(
            _equal(left, right) for left, right in zip(expected, observed, strict=True)
        )
    return expected == observed


def _items(record: ReportRecordSnapshot) -> list[dict[str, Any]]:
    return [
        {
            "criterion_id": str(item.criterion_id),
            "criterion_weight": item.criterion_weight,
            "axis_weights": dict(item.axis_weights),
            "axes": [(axis.axis, axis.score) for axis in item.axes],
        }
        for item in record.items
    ]


def _contributions(value: Aggregate) -> list[dict[str, Any]]:
    return [
        {
            "criterion_id": item.key,
            "score": item.score,
            "weight": item.weight,
            "normalized_weight": item.normalized_weight,
            "contribution": item.contribution,
        }
        for item in value.contributions
    ]


def recompute(
    *,
    record: ReportRecordSnapshot | None,
    read: ReportReadSnapshot | None,
    target_blob_shas: dict[str, str],
) -> RecomputeRecord | None:
    if not _present(record) or read is None or read.status_code != 200 or not read.report:
        return None
    config = record.config_version or ""
    computed = report_aggregate(_items(record), config)
    stored = record.scoring_inputs or {}
    body = read.report
    breakdown = body.get("scoring_breakdown") or {}
    comparisons = [
        RecomputeComparison(
            target=RecomputeTarget.STORED_OVERALL_SCORE,
            field_path="overall_score",
            expected=computed.score,
            observed=record.overall_score,
            equal=_equal(computed.score, record.overall_score),
        )
    ]
    expected_inputs = {
        "numerator": computed.numerator,
        "denominator": computed.denominator,
        "criteria": _contributions(computed),
    }
    for name, value in expected_inputs.items():
        comparisons.append(
            RecomputeComparison(
                target=RecomputeTarget.SCORING_INPUTS,
                field_path=f"scoring_inputs.{name}",
                expected=value,
                observed=stored.get(name),
                equal=_equal(value, stored.get(name)),
            )
        )
    comparisons.append(
        RecomputeComparison(
            target=RecomputeTarget.API_OVERALL_SCORE,
            field_path="report.overall_score",
            expected=computed.score,
            observed=body.get("overall_score"),
            equal=_equal(computed.score, body.get("overall_score")),
        )
    )
    api_contributions = [
        {
            "criterion_id": item.get("key"),
            "score": item.get("score"),
            "weight": item.get("weight"),
            "normalized_weight": item.get("normalized_weight"),
            "contribution": item.get("contribution"),
        }
        for item in breakdown.get("contributions") or ()
    ]
    for name, expected, observed in (
        ("numerator", computed.numerator, breakdown.get("numerator")),
        ("denominator", computed.denominator, breakdown.get("denominator")),
        ("contributions", _contributions(computed), api_contributions),
    ):
        comparisons.append(
            RecomputeComparison(
                target=RecomputeTarget.API_SCORING_BREAKDOWN,
                field_path=f"report.scoring_breakdown.{name}",
                expected=expected,
                observed=observed,
                equal=_equal(expected, observed),
            )
        )
    served = {str(item.get("criterion_id")): item for item in body.get("items") or ()}
    for item in _items(record):
        # The report read drops an axis that has a score but no citation (WhyYou `_restored_axes`).
        axes = [(axis, score) for axis, score in item["axes"]]
        quoted = {
            axis.axis: bool(axis.quoted_evidence_ids)
            for value in record.items
            if str(value.criterion_id) == item["criterion_id"]
            for axis in value.axes
        }
        readable = [(axis, score) for axis, score in axes if score is None or quoted.get(axis)]
        expected = criterion_aggregate(readable, item["axis_weights"], config).score
        observed = (served.get(item["criterion_id"]) or {}).get("average_score")
        comparisons.append(
            RecomputeComparison(
                target=RecomputeTarget.API_ITEM_AVERAGE_SCORE,
                field_path=f"report.items[{item['criterion_id']}].average_score",
                expected=expected,
                observed=observed,
                equal=_equal(expected, observed),
            )
        )
    return RecomputeRecord(
        report_id=record.report_id,
        rule_copy_id=RULE_COPY_ID,
        rule_source=tuple(
            {"path": item["path"], "blob_sha": item["blob_sha"]} for item in PINNED_SOURCES
        ),
        target_source_blob_shas=tuple(
            target_blob_shas.get(item["path"], "") for item in PINNED_SOURCES
        ),
        inputs={"config_version": config, "items": _items(record)},
        computed={
            "score": computed.score,
            "numerator": computed.numerator,
            "denominator": computed.denominator,
        },
        comparisons=tuple(comparisons),
        tolerance=SPEC004_RECOMPUTE_TOLERANCE,
    )


def judge_e02_recompute(*, records: tuple[RecomputeRecord | None, ...]) -> AssertionResult:
    expected = {"comparisons": "ALL_EQUAL"}
    if not records or any(item is None for item in records):
        return _result(
            "E02-A3",
            AssertionStatus.INCONCLUSIVE,
            f"{PRECONDITION_NOT_MET}: a report to recompute is unavailable",
            {"recomputed": sum(item is not None for item in records)},
            expected,
            ("FR-033",),
        )
    unequal = [
        f"{item.target.value}:{item.field_path}"
        for record in records
        for item in record.comparisons
        if not item.equal
    ]
    actual = {"unequal": unequal, "reports": len(records)}
    if unequal:
        return _result(
            "E02-A3",
            AssertionStatus.FAIL,
            "recomputed score differs from stored or served values",
            actual,
            expected,
            ("FR-033", "FR-034"),
        )
    return _result(
        "E02-A3",
        AssertionStatus.PASS,
        "저장 입력으로 다시 계산한 총점·기여·항목 평균이 저장값·조회값과 모두 같습니다.",
        actual,
        expected,
        ("FR-033", "FR-034"),
    )
