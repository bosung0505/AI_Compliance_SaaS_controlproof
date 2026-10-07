"""T005 — Spec 004 model contract (data-model.md §1~§12).

RED until T012: every test resolves its model through `engine.models` at call time, so a missing symbol
fails as `AttributeError` (the intended reason) instead of breaking collection. ID-004-01 records the
strict-xfail convention; T012 removes the markers in the change that makes these pass.
"""

from __future__ import annotations

from importlib import import_module

import pytest
from pydantic import ValidationError

from tests.fixtures import spec004 as fx

pytestmark = pytest.mark.xfail(
    strict=True,
    raises=AttributeError,
    reason="RED until T012 implements the Spec 004 entities in engine/models.py",
)


def m(name: str):
    return getattr(import_module("engine.models"), name)


def test_profiles_are_registered_with_canonical_contracts() -> None:
    profile = m("ExecutionProfile")
    canonical = m("ScenarioProfile").canonical
    e01 = canonical(profile.E01_CITATION_EVIDENCE_V1)
    e02 = canonical(profile.E02_SCORING_FREEZE_V1)
    assert e01.scenario_id == "E-01"
    assert e01.applicable_assertion_ids == ("E01-A1", "E01-A2", "E01-A3", "E01-A4")
    assert e01.required_evidence == (
        "EV4-01",
        "EV4-02",
        "EV4-03",
        "EV4-04",
        "EV4-05",
        "EV4-09",
        "EV4-10",
    )
    assert e02.scenario_id == "E-02"
    assert e02.applicable_assertion_ids == ("E02-A1", "E02-A2", "E02-A3")
    assert e02.required_evidence == (
        "EV4-01",
        "EV4-02",
        "EV4-04",
        "EV4-06",
        "EV4-07",
        "EV4-08",
        "EV4-09",
        "EV4-10",
    )
    for item in (e01, e02):
        assert item.fault_variant is None
        assert item.timing_policy == {
            "poll_seconds": 2,
            "stability_consecutive": 3,
            "stability_seconds": 4,
            "environment_restore_deadline_seconds": 120,
            "run_deadline_seconds": 540,
            "bundle_verify_deadline_seconds": 60,
        }


def test_lane_enums_are_exact_and_ordered() -> None:
    assert tuple(lane.value for lane in m("E01LaneId")) == fx.E01_LANES
    assert tuple(lane.value for lane in m("E02LaneId")) == fx.E02_LANES


@pytest.mark.parametrize("mode", fx.CITATION_MODES)
def test_lane_criterion_accepts_every_mode_with_its_argument_rule(mode: str) -> None:
    argument = None if mode in {"VALID", "EMPTY"} else str(fx.sid("arg", mode))
    criterion = m("LaneCriterion").model_validate(
        fx.lane_criterion(
            "E01_CITATION_MATRIX",
            f"e01-{mode.casefold()}",
            citation_mode=mode,
            mode_argument=argument,
        )
    )
    assert criterion.citation_mode.value == mode


@pytest.mark.parametrize(
    "updates",
    [
        {"citation_mode": "NONEXISTENT", "mode_argument": None},
        {"citation_mode": "VALID", "mode_argument": "00000000-0000-0000-0000-000000000001"},
        {"citation_mode": "OTHER_APPLICANT", "mode_argument": "not-a-uuid"},
        {"fixture_score": 101},
        {"marker": "no marker at the start"},
    ],
)
def test_lane_criterion_rejects_inconsistent_mode_argument_score_or_marker(updates) -> None:
    payload = fx.lane_criterion("E01_CITATION_MATRIX", "e01-x") | updates
    with pytest.raises(ValidationError):
        m("LaneCriterion").model_validate(payload)


def test_matrix_lane_requires_code_order_and_an_earlier_valid_reference() -> None:
    lane = m("ReportLane")
    criteria = fx.matrix_criteria(reference_evidence_id=fx.uuid7_at(fx.FIXED_AT, 9))
    assert len(lane.model_validate(fx.report_lane("E01_CITATION_MATRIX", criteria)).criteria) == 5
    reordered = [criteria[4], *criteria[:4]]
    reordered[0] = reordered[0] | {"code": "e01-0-other-criterion"}
    with pytest.raises(ValidationError, match="code order|earlier"):
        lane.model_validate(fx.report_lane("E01_CITATION_MATRIX", reordered))


def test_e02_lanes_bind_to_the_latest_published_version_and_need_scores() -> None:
    lane = m("ReportLane")
    criteria = [fx.lane_criterion("E02_FIRST_APPLICANT", "e02-a", fixture_score=72, weight=50.0)]
    lane.model_validate(fx.report_lane("E02_FIRST_APPLICANT", criteria))
    with pytest.raises(ValidationError):
        lane.model_validate(
            fx.report_lane("E02_FIRST_APPLICANT", criteria, version_source="RUN_SEED")
        )
    unscored = [fx.lane_criterion("E02_FIRST_APPLICANT", "e02-a", weight=50.0)]
    with pytest.raises(ValidationError, match="score"):
        lane.model_validate(fx.report_lane("E02_FIRST_APPLICANT", unscored))


def test_emission_receipt_contract_and_statuses() -> None:
    receipt = m("ModelEmissionReceipt")
    criterion_id = str(fx.sid("criterion", "x"))
    assert receipt.model_validate(fx.emission_receipt(criterion_id)).fixture_id == fx.FIXTURE_ID
    for status in ("EMITTED", "MODE_SOURCE_MISSING", "MARKER_INVALID"):
        receipt.model_validate(fx.emission_receipt(criterion_id, mode_status=status))
    with pytest.raises(ValidationError):
        receipt.model_validate(fx.emission_receipt(criterion_id, fixture_id="h03-report-v1"))
    with pytest.raises(ValidationError):
        receipt.model_validate(fx.emission_receipt(criterion_id, answer_text="원문"))


def test_citation_case_outcomes_and_item_scoped_invalid_id_flag() -> None:
    case = m("CitationCase")
    for mode in fx.INVALID_MODES:
        assert case.model_validate(fx.citation_case(mode)).outcome.value == "EMPTIED"
    assert case.model_validate(fx.citation_case("VALID")).outcome.value == "STORED_VALID"
    stored_invalid = fx.citation_case(
        "NONEXISTENT", outcome="STORED_INVALID", invalid_id_present=True
    )
    assert case.model_validate(stored_invalid).invalid_id_present is True


def test_report_record_snapshot_keeps_only_text_digests() -> None:
    record = m("ReportRecordSnapshot")
    value = record.model_validate(fx.e02_report_record("v1"))
    assert value.overall_score == 72
    assert value.summary_length == 32
    with pytest.raises(ValidationError):
        record.model_validate(fx.e02_report_record("v1", summary="원문 요약"))
    with pytest.raises(ValidationError):
        record.model_validate(fx.e02_report_record("v1", phase="SOMETIME"))


def test_report_read_snapshot_records_unknown_field_names_only() -> None:
    read = m("ReportReadSnapshot")
    value = read.model_validate(fx.report_read("POST_REMOVAL", unknown_fields=["playable"]))
    assert value.unknown_fields == ("playable",)


@pytest.mark.parametrize(
    "kind", ["EVIDENCE_SEGMENT_REMOVAL", "STORAGE_PROBE_WRITE", "CRITERIA_VERSION_PUBLISH"]
)
def test_change_injection_lifecycle_requires_matching_restore_digest(kind: str) -> None:
    injection = m("ChangeInjection")
    assert injection.model_validate(fx.change_injection(kind)).state.value == "RESTORED"
    with pytest.raises(ValidationError):
        injection.model_validate(fx.change_injection(kind, post_restore_digest="9" * 64))
    with pytest.raises(ValidationError):
        injection.model_validate(
            fx.change_injection(kind, state="RESTORE_FAILED", failure_code=None)
        )
    failed = injection.model_validate(fx.change_injection(kind, state="RESTORE_FAILED"))
    assert failed.failure_code == "RESTORE_DIGEST_MISMATCH"


def test_criteria_version_snapshot_enforces_status_and_weight_rules() -> None:
    snapshot = m("CriteriaVersionSnapshot")
    assert snapshot.model_validate(fx.criteria_version("v2")).status.value == "published"
    with pytest.raises(ValidationError):
        snapshot.model_validate(fx.criteria_version("v1", status="closed"))
    with pytest.raises(ValidationError):
        snapshot.model_validate(fx.criteria_version("v1", published_at=None))
    with pytest.raises(ValidationError):
        snapshot.model_validate(fx.criteria_version("v1", axis_weights={"depth": 100.0}))


def test_frozen_input_set_reports_missing_fields() -> None:
    frozen = m("FrozenInputSet")
    assert frozen.model_validate(fx.frozen_inputs("v1")).missing_fields == ()
    with pytest.raises(ValidationError):
        frozen.model_validate(
            fx.frozen_inputs("v1", scoring_inputs_present=False, missing_fields=[])
        )


def test_recompute_record_pins_the_rule_copy_and_tolerance() -> None:
    record = m("RecomputeRecord")
    payload = {
        "report_id": str(fx.sid("report", "E02_FIRST_APPLICANT")),
        "rule_copy_id": "controlproof.whyyou-scoring-copy.v1",
        "rule_source": [
            {
                "path": "backend/src/interview_evidence/reporting/domain/scoring.py",
                "blob_sha": "61d1e615f90ff63a353f7d2062707700b94744a1",
            },
            {
                "path": "backend/src/interview_evidence/reporting/domain/report.py",
                "blob_sha": "814289681114479aeac7ea778fae78da4d35ac48",
            },
        ],
        "target_source_blob_shas": [
            "61d1e615f90ff63a353f7d2062707700b94744a1",
            "814289681114479aeac7ea778fae78da4d35ac48",
        ],
        "inputs": {},
        "computed": {"score": 72, "numerator": 72.5, "denominator": 1.0},
        "comparisons": [
            {
                "target": "STORED_OVERALL_SCORE",
                "field_path": "reports.overall_score",
                "expected": 72,
                "observed": 72,
                "equal": True,
            }
        ],
        "tolerance": 1e-9,
    }
    assert record.model_validate(payload).tolerance == 1e-9
    with pytest.raises(ValidationError):
        record.model_validate(payload | {"tolerance": 1e-6})
    with pytest.raises(ValidationError):
        record.model_validate(payload | {"rule_copy_id": "other"})
