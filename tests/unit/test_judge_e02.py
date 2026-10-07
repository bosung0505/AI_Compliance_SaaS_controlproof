"""T053 — E02-A1~A3 (contracts/scenario-profile-v4.md).

RED until T058 creates `engine/judges/e02.py`. Records come from the deterministic fake so the scoring inputs have
WhyYou's stored shape.
"""

from __future__ import annotations

import copy
from importlib import import_module
from uuid import uuid4

import pytest

from engine.judges.e02_scoring import PINNED_SOURCES
from engine.models import AssertionStatus, E02LaneId, RecomputeTarget
from seeds.spec004_subjects import e02_lane, e02_position_id, e02_version_body
from tests.fixtures.fake_spec004 import FakeSpec004Adapters

SHAS = {item["path"]: item["blob_sha"] for item in PINNED_SOURCES}


def e02():
    return import_module("engine.judges.e02")


def _publish(fake, position, key):
    created = fake.create_version(position_id=position, body=e02_version_body(key), idempotency_key=key * 8)
    fake.publish_version(
        version_id=created.data["version_id"], row_version=1, idempotency_key=key * 8
    )
    phase = "V1_PUBLISHED" if key == "v1" else "V2_PUBLISHED"
    return fake.latest_published(position_id=position, snapshot_phase=phase), created.data["version_id"]


def _report(fake, lane, phase):
    record = fake.read_records(lane=lane, phase=phase)
    read = fake.read_api(lane=lane, phase=phase)
    return record, read


def _journey(**options):
    fake = FakeSpec004Adapters(**options)
    run_id = uuid4()
    position = str(e02_position_id(run_id))
    fake.seed_position(run_id=str(run_id), position_id=position)
    v1, _ = _publish(fake, position, "v1")
    first = e02_lane(run_id, E02LaneId.E02_FIRST_APPLICANT, v1)
    fake.seed_lanes(run_id=str(run_id), lanes=(first,))
    fake.committed.add(first.subject_ref)
    fake.request_report(lane=first)
    pre_record, pre_read = _report(fake, first, "PRE_CHANGE")
    v2, v2_id = _publish(fake, position, "v2")
    second = e02_lane(run_id, E02LaneId.E02_SECOND_APPLICANT, v2)
    fake.seed_lanes(run_id=str(run_id), lanes=(second,))
    fake.committed.add(second.subject_ref)
    fake.request_report(lane=second)
    second_record, second_read = _report(fake, second, "POST_CHANGE")
    post_record, post_read = _report(fake, first, "POST_CHANGE")
    return {
        "v1": v1, "v2": v2, "v2_id": v2_id,
        "pre_record": pre_record, "pre_read": pre_read,
        "post_record": post_record, "post_read": post_read,
        "second_record": second_record, "second_read": second_read,
    }


def _a2(j):
    return e02().judge_e02_unchanged(
        v2=j["v2"], published_v2_id=j["v2_id"], second=j["second_record"],
        pre_record=j["pre_record"], post_record=j["post_record"],
        pre_read=j["pre_read"], post_read=j["post_read"],
    )


def _recompute(record, read):
    return e02().recompute(record=record, read=read, target_blob_shas=SHAS)


def _a3(j, first=None, second=None):
    return e02().judge_e02_recompute(
        records=(
            first or _recompute(j["post_record"], j["post_read"]),
            second or _recompute(j["second_record"], j["second_read"]),
        )
    )


def test_a1_passes_when_the_first_report_freezes_v1() -> None:
    j = _journey()
    result = e02().judge_e02_frozen(first=j["pre_record"], v1=j["v1"])
    assert result.status is AssertionStatus.PASS, result.detail


def test_a1_missing_field_or_weight_mismatch_fails() -> None:
    j = _journey()
    missing = j["pre_record"].model_copy(update={"model_version": None, "scoring_inputs": {}})
    result = e02().judge_e02_frozen(first=missing, v1=j["v1"])
    assert result.status is AssertionStatus.FAIL
    assert set(result.actual["missing_fields"]) >= {"model_version", "scoring_inputs"}
    mismatch = e02().judge_e02_frozen(first=j["pre_record"], v1=j["v2"])
    assert mismatch.status is AssertionStatus.FAIL


def test_a2_unchanged_passes_changed_fails_and_wrong_binding_is_inconclusive() -> None:
    assert _a2(_journey()).status is AssertionStatus.PASS
    assert _a2(_journey(report_mutates_after_change=True)).status is AssertionStatus.FAIL
    wrong = _a2(_journey(second_version_binding_wrong=True))
    assert wrong.status is AssertionStatus.INCONCLUSIVE
    assert wrong.detail.startswith("PRECONDITION_NOT_MET")


def test_a3_passes_when_every_target_matches() -> None:
    j = _journey()
    record = _recompute(j["post_record"], j["post_read"])
    assert {item.target for item in record.comparisons} == set(RecomputeTarget)
    assert all(item.equal for item in record.comparisons)
    assert record.tolerance == 1e-9
    assert _a3(j).status is AssertionStatus.PASS


@pytest.mark.parametrize(
    "option,target",
    [
        ({"stored_overall_offset": 1}, RecomputeTarget.STORED_OVERALL_SCORE),
        ({"api_overall_offset": 1}, RecomputeTarget.API_OVERALL_SCORE),
    ],
)
def test_a3_overall_mismatch_fails(option, target) -> None:
    j = _journey(**option)
    record = _recompute(j["post_record"], j["post_read"])
    assert not all(item.equal for item in record.comparisons if item.target is target)
    assert _a3(j).status is AssertionStatus.FAIL


def _tamper_inputs(record, path, value):
    inputs = copy.deepcopy(record.scoring_inputs)
    inputs[path] = value
    return record.model_copy(update={"scoring_inputs": inputs})


def _tamper_read(read, mutate):
    body = copy.deepcopy(read.report)
    mutate(body)
    return read.model_copy(update={"report": body})


def test_a3_scoring_inputs_breakdown_and_item_average_mismatch_fail() -> None:
    j = _journey()
    numerator = j["post_record"].scoring_inputs["numerator"]
    inputs = _tamper_inputs(j["post_record"], "numerator", numerator + 1)
    assert _a3(j, first=_recompute(inputs, j["post_read"])).status is AssertionStatus.FAIL

    def breakdown(body):
        body["scoring_breakdown"]["denominator"] += 1

    def average(body):
        body["items"][0]["average_score"] = (body["items"][0]["average_score"] or 0) + 1

    for mutate, target in (
        (breakdown, RecomputeTarget.API_SCORING_BREAKDOWN),
        (average, RecomputeTarget.API_ITEM_AVERAGE_SCORE),
    ):
        record = _recompute(j["post_record"], _tamper_read(j["post_read"], mutate))
        assert not all(item.equal for item in record.comparisons if item.target is target)
        assert _a3(j, first=record).status is AssertionStatus.FAIL


def test_a3_float_tolerance_and_integer_exactness() -> None:
    j = _journey()
    numerator = j["post_record"].scoring_inputs["numerator"]
    within = _tamper_inputs(j["post_record"], "numerator", numerator + 1e-12)
    assert _a3(j, first=_recompute(within, j["post_read"])).status is AssertionStatus.PASS
    shifted = j["post_record"].model_copy(update={"overall_score": j["post_record"].overall_score + 1})
    assert _a3(j, first=_recompute(shifted, j["post_read"])).status is AssertionStatus.FAIL


def test_a3_absent_report_is_inconclusive() -> None:
    j = _journey(refuse_lanes=frozenset({"E02_SECOND_APPLICANT"}))
    record = _recompute(j["second_record"], j["second_read"])
    assert record is None
    assert _a3(j, second=None).status is not AssertionStatus.PASS
