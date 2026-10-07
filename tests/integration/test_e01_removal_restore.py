"""T046 — E-01 removal/probe journey with always-run restores (US2, FR-022, FR-041, SC-002).

RED until T048 adds the removal and storage-probe steps to `engine/executors/e01.py`.
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest

from engine.models import AssertionStatus, E01LaneId, RunState, Verdict
from engine.runner import build_profile_runner
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters
from tests.fixtures.fake_spec004 import FakeSpec004Adapters, use_spec004_fixture


def _runner(tmp_path, fake, clock=None):
    adapters, _ = make_adapters(spec004=fake)
    use_spec004_fixture(adapters)
    return build_profile_runner(
        load("scenarios/E-01.yaml"), adapters, tmp_path, clock=clock or FakeClock()
    )


def _run(tmp_path, fake, clock=None):
    runner = _runner(tmp_path, fake, clock)
    readiness = runner.preflight("whyyou-local")
    assert readiness.status.value == "READY", readiness
    run, judgement, bundle = runner.execute(readiness)
    return runner, run, judgement, bundle


def _results(judgement):
    return {item.assertion_id: item for item in judgement.assertion_results}


def _segments_back(fake) -> bool:
    return set(fake.segments) == fake.present_segments


@pytest.mark.parametrize("reverse_item_order", [False, True])
def test_exposed_removal_and_restore_pass_and_d1_is_diagnostic(
    tmp_path, reverse_item_order
) -> None:
    fake = FakeSpec004Adapters(removal_indicator="score_null")
    original = fake.read_records
    snapshots = []

    reordered = False

    def captured(**kwargs):
        nonlocal reordered
        lane = kwargs["lane"]
        if reverse_item_order and not reordered and lane.lane_id is E01LaneId.E01_STORAGE_PROBE:
            fake.reports[lane.lane_id.value]["items"].reverse()
            reordered = True
        snapshot = original(**kwargs)
        snapshots.append(snapshot)
        return snapshot

    fake.read_records = captured
    _, run, judgement, bundle = _run(tmp_path, fake)
    results = _results(judgement)
    for assertion_id in ("E01-A1", "E01-A2", "E01-A3", "E01-A4"):
        assert results[assertion_id].status is AssertionStatus.PASS, results[assertion_id].detail
    assert judgement.verdict is Verdict.PASS
    assert run.state is RunState.COMPLETED
    probe = json.loads((bundle / "storage-probe.json").read_text(encoding="utf-8"))
    assert probe["diagnostic_id"] == "E01-D1"
    assert {row["mode"] for row in probe["exposure"]} == {
        "EMPTY",
        "NONEXISTENT",
        "OTHER_APPLICANT",
        "OTHER_CRITERION",
    }
    source = probe["other_criterion_source"]
    baseline = next(
        row
        for row in snapshots
        if row.lane_id is E01LaneId.E01_STORAGE_PROBE and row.phase == "PRE_PROBE"
    )
    target = next(
        item for item in baseline.items if str(item.report_item_id) == probe["report_item_id"]
    )
    donor = next(
        item for item in baseline.items if str(item.report_item_id) == source["report_item_id"]
    )
    evidence = next(
        item for item in baseline.evidence if str(item.evidence_id) == source["evidence_id"]
    )
    assert donor.criterion_id != target.criterion_id
    probe_lane = next(
        row["lane"]
        for row in fake.injections.values()
        if row["lane"].lane_id is E01LaneId.E01_STORAGE_PROBE
    )
    assert target.criterion_id == probe_lane.criteria[0].criterion_id
    assert donor.criterion_id == probe_lane.criteria[1].criterion_id
    assert evidence.report_item_id == donor.report_item_id
    assert evidence.criterion_id == donor.criterion_id
    assert evidence.competency_model_version_id == donor.competency_model_version_id
    written = next(row for row in probe["written_axes"] if row["mode"] == "OTHER_CRITERION")
    assert written["quoted_evidence_ids"] == [source["evidence_id"]]
    after = next(
        row
        for row in snapshots
        if row.lane_id is E01LaneId.E01_STORAGE_PROBE and row.phase == "POST_RESTORE"
    )
    assert baseline.items == after.items and baseline.evidence == after.evidence
    assert "E01-D1" not in results
    assert _segments_back(fake) and fake.torn_down


@pytest.mark.parametrize(
    "fault",
    ["missing", "wrong_item", "wrong_criterion", "wrong_version", "unquoted", "wrong_report"],
)
def test_probe_never_writes_partial_modes_when_donor_provenance_is_unverified(
    tmp_path, fault
) -> None:
    fake = FakeSpec004Adapters(removal_indicator="score_null")
    original = fake.read_records

    def altered(*, lane, phase):
        snapshot = original(lane=lane, phase=phase)
        if lane.lane_id is not E01LaneId.E01_STORAGE_PROBE or phase != "PRE_PROBE":
            return snapshot
        if fault == "wrong_report":
            return snapshot.model_copy(update={"report_id": uuid4()})
        donor_ids = {item.criterion_id for item in lane.criteria[1:]}
        evidence = []
        for row in snapshot.evidence:
            if row.criterion_id in donor_ids:
                if fault == "missing":
                    continue
                fields = {
                    "wrong_item": "report_item_id",
                    "wrong_criterion": "criterion_id",
                    "wrong_version": "competency_model_version_id",
                    "unquoted": "evidence_id",
                }
                row = row.model_copy(update={fields[fault]: uuid4()})
            evidence.append(row)
        return snapshot.model_copy(update={"evidence": tuple(evidence)})

    fake.read_records = altered
    _, run, judgement, bundle = _run(tmp_path, fake)
    probe = json.loads((bundle / "storage-probe.json").read_text(encoding="utf-8"))
    assert probe["status"] == "NOT_RUN"
    assert "PROBE_PREREQUISITE_UNVERIFIED" in probe["detail"]
    assert not any(
        row["lane"].lane_id is E01LaneId.E01_STORAGE_PROBE for row in fake.injections.values()
    )
    assert run.state is RunState.COMPLETED and judgement.verdict is Verdict.PASS
    assert _segments_back(fake) and fake.torn_down


def test_p1_shape_fails_a3(tmp_path) -> None:
    _, _, judgement, _ = _run(tmp_path, FakeSpec004Adapters())
    assert _results(judgement)["E01-A3"].status is AssertionStatus.FAIL
    assert judgement.verdict is Verdict.FAIL


@pytest.mark.parametrize("option", ["restore_mismatch", "probe_restore_fails"])
def test_unsafe_restore_is_restore_failed_and_blocks(tmp_path, option) -> None:
    fake = FakeSpec004Adapters(removal_indicator="score_null", **{option: True})
    runner, run, judgement, _ = _run(tmp_path, fake)
    assert run.state is RunState.RESTORE_FAILED
    assert judgement.verdict is Verdict.INCONCLUSIVE
    with pytest.raises(RuntimeError, match="blocked"):
        runner.execute(runner.preflight("whyyou-local"))


def test_exception_after_removal_still_restores(tmp_path) -> None:
    fake = FakeSpec004Adapters(removal_indicator="score_null")
    original = fake.read_api

    def broken(*, lane, phase, include_timeline=False):
        if phase == "POST_REMOVAL":
            raise ConnectionError("synthetic read failure")
        return original(lane=lane, phase=phase, include_timeline=include_timeline)

    fake.read_api = broken
    _, run, judgement, _ = _run(tmp_path, fake)
    assert _results(judgement)["E01-A3"].status is AssertionStatus.INCONCLUSIVE
    assert run.state is RunState.COMPLETED
    assert _segments_back(fake) and fake.torn_down


def test_cancellation_restores_then_propagates(tmp_path) -> None:
    fake = FakeSpec004Adapters(removal_indicator="score_null")
    original = fake.read_api

    def cancelled(*, lane, phase, include_timeline=False):
        if phase == "POST_REMOVAL":
            raise KeyboardInterrupt
        return original(lane=lane, phase=phase, include_timeline=include_timeline)

    fake.read_api = cancelled
    runner = _runner(tmp_path, fake)
    with pytest.raises(KeyboardInterrupt):
        runner.execute(runner.preflight("whyyou-local"))
    assert _segments_back(fake) and fake.torn_down


def test_deadline_skips_reads_but_not_restore_and_budget_counts_restore_only(tmp_path) -> None:
    fake = FakeSpec004Adapters(removal_indicator="score_null")
    clock = FakeClock()
    original = fake.remove_segment

    def slow(**kwargs):
        clock.sleep(1000)  # apply work, not restore work
        return original(**kwargs)

    fake.remove_segment = slow
    runner, run, judgement, _ = _run(tmp_path, fake, clock)
    assert _results(judgement)["E01-A3"].status is AssertionStatus.INCONCLUSIVE
    assert run.state is RunState.COMPLETED
    timing = runner.timing_report()
    assert timing["environment_restore_within_deadline"] is True
    assert timing["environment_restore_seconds"] < 120
    assert _segments_back(fake) and fake.torn_down
