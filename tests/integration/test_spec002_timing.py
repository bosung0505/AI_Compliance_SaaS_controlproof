from __future__ import annotations

import pytest

from engine.adapters.base import AdapterResult
from engine.execution import coordinate_reporting_recovery
from engine.executors.e03_after import E03AfterExecutor
from engine.executors.h03_dlq import H03DlqExecutor
from engine.executors.sealed import RunDeadlineExceeded
from engine.models import Presence
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters
from tests.fixtures.spec002 import EVENT_ID, RUN_ID


def _with_timing(scenario, **updates):
    return scenario.model_copy(
        update={
            "timing_policy": scenario.timing_policy.model_copy(update=updates),
        }
    )


def test_canonical_deadlines_are_frozen_into_each_scenario_snapshot():
    for path in (
        "scenarios/H-03-DLQ.yaml",
        "scenarios/E-03-BEFORE.yaml",
        "scenarios/E-03-AFTER.yaml",
    ):
        scenario = load(path)
        timing = scenario.snapshot().definition["timing_policy"]
        assert timing["dlq_deadline_seconds"] in {60, 360}
        assert timing["duplicate_ack_deadline_seconds"] == 60
        assert timing["environment_restore_deadline_seconds"] == 180
        assert timing["run_deadline_seconds"] == 600


def test_dlq_poll_budget_comes_from_the_active_scenario_snapshot(tmp_path):
    class MissingDlq:
        def __init__(self):
            self.calls = 0

        def read_attempts(self, **_kwargs):
            return AdapterResult(True, "ATTEMPTS_READ", {"records": (), "presence": Presence.ABSENT})

        def read_dlq(self, **_kwargs):
            self.calls += 1
            return AdapterResult(
                True,
                "DLQ_MATCH_READ",
                {"presence": Presence.ABSENT, "terminal_failure": None},
            )

    scenario = _with_timing(load("scenarios/H-03-DLQ.yaml"), dlq_deadline_seconds=6)
    adapters, _browser = make_adapters()
    clock = FakeClock()
    queue = MissingDlq()
    executor = H03DlqExecutor(scenario, adapters, tmp_path, clock=clock)
    started = clock.now()

    executor._poll_terminal_lineage(
        queue=queue,
        run_id=RUN_ID,
        source_event_id=EVENT_ID,
        subject={"subject_ref": "candidate-01", "interview_session_id": str(EVENT_ID)},
    )

    assert queue.calls == 3
    assert (clock.now() - started).total_seconds() == 4


def test_duplicate_ack_poll_budget_comes_from_the_active_scenario_snapshot(tmp_path):
    class MissingDuplicateAck:
        def __init__(self):
            self.calls = 0

        def read_duplicate_ack(self, **_kwargs):
            self.calls += 1
            return AdapterResult(False, "DUPLICATE_ACK_MISSING")

    scenario = _with_timing(
        load("scenarios/E-03-AFTER.yaml"), duplicate_ack_deadline_seconds=6
    )
    adapters, _browser = make_adapters()
    clock = FakeClock()
    reader = MissingDuplicateAck()
    executor = E03AfterExecutor(scenario, adapters, tmp_path, clock=clock)
    started = clock.now()

    executor._poll_duplicate_ack(reader, run_id=RUN_ID, source_event_id=EVENT_ID)

    assert reader.calls == 3
    assert (clock.now() - started).total_seconds() == 4


def test_recovery_poll_budget_comes_from_the_active_scenario_snapshot():
    class MissingEffects:
        def __init__(self):
            self.calls = 0

        def read_reporting_effects(self, **_kwargs):
            self.calls += 1
            return ()

    scenario = _with_timing(
        load("scenarios/E-03-BEFORE.yaml"), environment_restore_deadline_seconds=6
    )
    adapters, _browser = make_adapters()
    clock = FakeClock()
    effects = MissingEffects()
    started = clock.now()

    outcome = coordinate_reporting_recovery(
        fault=adapters.fault,
        redrive=adapters.safe_redrive,
        effects=effects,
        run_id=RUN_ID,
        source_event_id=EVENT_ID,
        logical_operation_id=RUN_ID,
        subject={"subject_ref": "candidate-01"},
        clock=clock,
        poll_seconds=scenario.timing_policy.poll_seconds,
        deadline_seconds=scenario.timing_policy.environment_restore_deadline_seconds,
    )

    assert outcome.restore_safe is True
    assert effects.calls == 3
    assert (clock.now() - started).total_seconds() == 4


def test_whole_run_deadline_comes_from_the_active_scenario_snapshot(tmp_path):
    scenario = _with_timing(load("scenarios/E-03-AFTER.yaml"), run_deadline_seconds=7)
    adapters, _browser = make_adapters(
        injected_reporting_present=True,
        dlq_presence=Presence.ABSENT,
    )
    clock = FakeClock()
    executor = E03AfterExecutor(scenario, adapters, tmp_path, clock=clock)
    readiness = executor.preflight("whyyou-local")
    original = executor.collect_us4

    def slow_collector(**kwargs):
        result = original(**kwargs)
        clock.sleep(8)
        return result

    with pytest.raises(RunDeadlineExceeded, match="7"):
        from engine.executors.sealed import execute_profile

        execute_profile(executor, readiness, collector=slow_collector, run_id=RUN_ID)

    assert adapters.fault.events[-1] == "fault.restore"
    assert not (tmp_path / str(RUN_ID)).exists()
