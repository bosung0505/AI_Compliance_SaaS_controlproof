"""T089: snapshot timing and restore-only accounting for E-01/E-02 (SC-002/003).

Counterfactual timing copies are test-only: published v4 scenarios retain their fixed policy.
FakeClock advances without real sleeps; complete runs still seal and genuinely verify their bundles.
"""

from __future__ import annotations

import json
from datetime import timedelta
from uuid import uuid4

import pytest

from engine.adapters.base import AdapterResult
from engine.lifecycle import RestoreBlockStore
from engine.models import E02LaneId
from engine.runner import build_profile_runner
from engine.scenario import load
from seeds.spec004_subjects import e01_lanes, e02_lane, e02_version_body
from tests.fixtures.fake_adapters import FakeClock, make_adapters
from tests.fixtures.fake_spec004 import FakeSpec004Adapters, use_spec004_fixture

SCENARIOS = ("E-01", "E-02")


class RecordingClock(FakeClock):
    def __init__(self):
        super().__init__()
        self.sleeps: list[float] = []

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        super().sleep(seconds)


def _runner(tmp_path, scenario_id, clock, fake=None, **timing_updates):
    fake = fake or FakeSpec004Adapters(removal_indicator="score_null")
    scenario = load(f"scenarios/{scenario_id}.yaml")
    if timing_updates:
        scenario = scenario.model_copy(
            update={"timing_policy": scenario.timing_policy.model_copy(update=timing_updates)}
        )
    adapters, _ = make_adapters(spec004=fake)
    use_spec004_fixture(adapters)
    return build_profile_runner(scenario, adapters, tmp_path, clock=clock), fake


def _lane(fake, scenario_id):
    run_id = uuid4()
    if scenario_id == "E-01":
        lane = e01_lanes(run_id)[0]
    else:
        position_id = str(uuid4())
        created = fake.create_version(
            position_id=position_id, body=e02_version_body("v1"), idempotency_key="timing-v1"
        )
        fake.publish_version(
            version_id=created.data["version_id"], row_version=1, idempotency_key="timing-publish"
        )
        version = fake.latest_published(position_id=position_id, snapshot_phase="V1_PUBLISHED")
        lane = e02_lane(run_id, E02LaneId.E02_FIRST_APPLICANT, version)
    fake.seed_lanes(run_id=str(run_id), lanes=(lane,))
    return lane


def _execute(runner):
    readiness = runner.preflight("whyyou-local")
    assert readiness.status.value == "READY"
    return runner.execute(readiness)


@pytest.mark.parametrize("scenario_id", SCENARIOS)
def test_canonical_snapshot_freezes_all_timing_budgets(scenario_id):
    timing = load(f"scenarios/{scenario_id}.yaml").snapshot().definition["timing_policy"]
    assert {
        key: timing[key]
        for key in (
            "poll_seconds",
            "stability_consecutive",
            "stability_seconds",
            "environment_restore_deadline_seconds",
            "run_deadline_seconds",
            "bundle_verify_deadline_seconds",
        )
    } == {
        "poll_seconds": 2,
        "stability_consecutive": 3,
        "stability_seconds": 4,
        "environment_restore_deadline_seconds": 120,
        "run_deadline_seconds": 540,
        "bundle_verify_deadline_seconds": 60,
    }
    assert timing["run_deadline_seconds"] + timing["bundle_verify_deadline_seconds"] == 600


@pytest.mark.parametrize("scenario_id", SCENARIOS)
@pytest.mark.parametrize(
    "updates,digests,expected_sleeps",
    [
        ({}, "aaa", [2, 2]),
        (
            {"poll_seconds": 1, "stability_consecutive": 4, "stability_seconds": 3},
            "abbbb",
            [1, 1, 1, 1],
        ),
        (
            {"poll_seconds": 1, "stability_consecutive": 2, "stability_seconds": 5},
            "aaaaaa",
            [1, 1, 1, 1, 1],
        ),
        (
            {"poll_seconds": 1, "stability_consecutive": 5, "stability_seconds": 1},
            "aaaaa",
            [1, 1, 1, 1],
        ),
        (
            {"poll_seconds": 1, "stability_consecutive": 3, "stability_seconds": 2},
            "aabbb",
            [1, 1, 1, 1],
        ),
    ],
    ids=["canonical", "changed-poll", "window-required", "streak-required", "reset-on-change"],
)
def test_stable_read_requires_snapshot_poll_streak_and_window(
    tmp_path, scenario_id, updates, digests, expected_sleeps
):
    clock = RecordingClock()
    runner, fake = _runner(tmp_path, scenario_id, clock, **updates)
    lane = _lane(fake, scenario_id)
    fake.committed.add(lane.subject_ref)
    fake.request_report(lane=lane)
    template = fake.read_records(lane=lane, phase="GENERATED")
    values = iter(template.model_copy(update={"state_digest": value * 64}) for value in digests)
    reads = []

    def read_records(**kwargs):
        reads.append(kwargs)
        return next(values)

    fake.read_records = read_records
    runner._deadline = clock.now() + timedelta(seconds=30)
    result = runner.stable_records(lane, "GENERATED")

    assert result.state_digest == digests[-1] * 64
    assert len(reads) == len(digests)
    assert clock.sleeps == expected_sleeps


@pytest.mark.parametrize("scenario_id", SCENARIOS)
@pytest.mark.parametrize("budget", [5, 9])
def test_missing_report_stops_at_snapshot_run_deadline_and_still_tears_down(
    tmp_path, scenario_id, budget
):
    clock = RecordingClock()
    runner, fake = _runner(tmp_path, scenario_id, clock, run_deadline_seconds=budget)
    fake.request_report = lambda **kwargs: AdapterResult(True, "REPORT_REQUESTED")
    fake.read_processing = lambda **kwargs: AdapterResult(True, "PROCESSING_READ", {"receipts": []})
    started = clock.now()
    run, judgement, _bundle = _execute(runner)

    assert runner._deadline == started + timedelta(seconds=budget)
    assert 0 <= (run.ended_at - runner._deadline).total_seconds() < 2
    assert all(value == 2 for value in clock.sleeps)
    assert run.state.value == "COMPLETED" and fake.torn_down
    assert judgement.verdict.value == "INCONCLUSIVE"
    assert runner.timing_report()["environment_restore_seconds"] == 0


@pytest.mark.parametrize("scenario_id", SCENARIOS)
@pytest.mark.parametrize(
    "budget,elapsed,state",
    [(5, 5, "COMPLETED"), (5, 5.01, "RESTORE_FAILED"), (8, 5.01, "COMPLETED")],
    ids=["exact-limit", "over-limit", "changed-budget"],
)
def test_restore_snapshot_limit_controls_state_block_and_sealed_recovery(
    tmp_path, scenario_id, budget, elapsed, state
):
    clock = FakeClock()
    runner, fake = _runner(
        tmp_path, scenario_id, clock, environment_restore_deadline_seconds=budget
    )
    teardown = fake.teardown

    def slow_teardown(**kwargs):
        clock.sleep(elapsed)
        return teardown(**kwargs)

    fake.teardown = slow_teardown
    run, judgement, bundle = _execute(runner)
    timing = runner.timing_report()
    safe = state == "COMPLETED"

    assert run.state.value == state
    assert run.manual_cleanup_required is (not safe)
    assert RestoreBlockStore(tmp_path).blocked("whyyou-local", runner.block_subject) is (not safe)
    assert timing["environment_restore_deadline_seconds"] == budget
    assert timing["environment_restore_seconds"] == pytest.approx(elapsed)
    assert timing["environment_restore_within_deadline"] is safe
    recovery = json.loads((bundle / "recovery.json").read_text(encoding="utf-8"))
    assert recovery["restore_timing"] == {
        key: timing[key]
        for key in (
            "environment_restore_deadline_seconds",
            "environment_restore_seconds",
            "environment_restore_within_deadline",
        )
    }
    assert judgement.verdict.value == ("PASS" if safe else "INCONCLUSIVE")


@pytest.mark.parametrize("scenario_id,expected_restore", [("E-01", 15), ("E-02", 7)])
def test_report_work_is_excluded_but_all_restore_operations_are_accumulated(
    tmp_path, scenario_id, expected_restore
):
    clock = FakeClock()
    runner, fake = _runner(tmp_path, scenario_id, clock, environment_restore_deadline_seconds=20)

    def delayed(method, seconds):
        def call(**kwargs):
            clock.sleep(seconds)
            return method(**kwargs)

        return call

    fake.request_report = delayed(fake.request_report, 80)
    fake.restore_segment = delayed(fake.restore_segment, 3)
    fake.restore_probe_axes = delayed(fake.restore_probe_axes, 5)
    fake.teardown = delayed(fake.teardown, 7)
    run, judgement, _bundle = _execute(runner)

    assert (run.ended_at - run.started_at).total_seconds() > 120
    assert run.state.value == "COMPLETED" and judgement.verdict.value == "PASS"
    assert runner.timing_report()["environment_restore_seconds"] == expected_restore
    assert runner.timing_report()["environment_restore_within_deadline"] is True
    assert fake.torn_down


@pytest.mark.parametrize("scenario_id", SCENARIOS)
def test_failed_restore_operation_counts_its_time_but_not_earlier_work(tmp_path, scenario_id):
    clock = FakeClock()
    runner, _fake = _runner(tmp_path, scenario_id, clock)
    clock.sleep(150)

    def failed_restore():
        clock.sleep(3)
        raise RuntimeError("synthetic restore failure")

    with pytest.raises(RuntimeError, match="synthetic restore failure"):
        runner.restore_operation(failed_restore)
    assert runner._restore_seconds == 3


@pytest.mark.parametrize("scenario_id", SCENARIOS)
@pytest.mark.parametrize(
    "budget,elapsed,within",
    [(5, 5, True), (5, 6, False), (9, 6, True)],
    ids=["exact-limit", "over-limit", "changed-budget"],
)
def test_real_bundle_verification_is_measured_against_snapshot_budget(
    tmp_path, monkeypatch, scenario_id, budget, elapsed, within
):
    import engine.executors.report_lanes as executor_module

    clock = FakeClock()
    real_verify = executor_module.verify_bundle

    def slow_verify(directory):
        clock.sleep(elapsed)
        return real_verify(directory)

    monkeypatch.setattr(executor_module, "verify_bundle", slow_verify)
    runner, _fake = _runner(tmp_path, scenario_id, clock, bundle_verify_deadline_seconds=budget)
    _run, _judgement, bundle = _execute(runner)
    timing = runner.timing_report()

    assert real_verify(bundle)["bundle_status"] == "VERIFIED"
    assert timing["bundle_verify_seconds"] == elapsed
    assert timing["bundle_verify_deadline_seconds"] == budget
    assert timing["bundle_verify_within_budget"] is within
    snapshot = json.loads((bundle / "scenario.snapshot.yaml").read_text(encoding="utf-8"))
    assert snapshot["definition"]["timing_policy"]["bundle_verify_deadline_seconds"] == budget
