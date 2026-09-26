from __future__ import annotations

from dataclasses import replace

from engine.adapters.base import AdapterResult
from engine.models import AssertionStatus, RunState, Verdict
from engine.runner import RunOrchestrator
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, FakeFault, FakeState, make_adapters


class DelayedFault(FakeFault):
    def __init__(self, *, effect_after: int = 1, restore_after: int = 1) -> None:
        super().__init__()
        self.effect_after = effect_after
        self.restore_after = restore_after
        self.effect_calls = 0
        self.restore_calls = 0

    def probe_effect(self, *, run_id, subject, trigger):
        self.effect_calls += 1
        if self.effect_calls < self.effect_after:
            return AdapterResult(False, "TRIGGER_RECEIPT_MISSING")
        return super().probe_effect(run_id=run_id, subject=subject, trigger=trigger)

    def restore(self, *, run_id, subject):
        self.restore_calls += 1
        if self.restore_calls < self.restore_after:
            return AdapterResult(
                False,
                "ENVIRONMENT_RESTORE_PENDING",
                {
                    "environment_restore": "FAILED",
                    "report_processing_recovery": "UNAVAILABLE",
                    "marker_inactive": True,
                    "worker_healthy": False,
                },
            )
        return super().restore(run_id=run_id, subject=subject)


class SequencedReportState(FakeState):
    def __init__(self, sequence):
        super().__init__()
        self.sequence = list(sequence)
        self.report_calls = 0

    def report_status(self, *, subject):
        value = self.sequence[min(self.report_calls, len(self.sequence) - 1)]
        self.report_calls += 1
        return AdapterResult(
            True,
            "REPORT_STATUS",
            {"presence": value[0], "status": value[1], "exchange": {"status": 202}},
        )


def _runner(tmp_path, *, fault=None, state=None):
    adapters, _ = make_adapters()
    adapters = replace(
        adapters,
        fault=fault or adapters.fault,
        state=state or adapters.state,
    )
    return RunOrchestrator(load("scenarios/H-03.yaml"), adapters, tmp_path, clock=FakeClock())


def test_delayed_worker_receipt_is_polled_until_it_matches(tmp_path):
    fault = DelayedFault(effect_after=3)
    runner = _runner(tmp_path, fault=fault)

    _, judgement, _ = runner.execute(runner.preflight("whyyou-local"))

    assert fault.effect_calls == 3
    assert judgement.verdict is Verdict.PASS


def test_last_transient_report_sample_does_not_replace_last_stable_state(tmp_path):
    sequence = [("ABSENT", "queued")] * 14 + [("PRESENT", "ready")]
    runner = _runner(tmp_path, state=SequencedReportState(sequence))

    _, judgement, _ = runner.execute(runner.preflight("whyyou-local"))

    a2 = next(item for item in judgement.assertion_results if item.assertion_id == "H03-A2")
    assert a2.status is AssertionStatus.PASS
    assert a2.actual["report.api.presence"] == "ABSENT"


def test_no_stable_report_state_is_inconclusive(tmp_path):
    sequence = [
        ("ABSENT", "queued") if index % 2 == 0 else ("PRESENT", "ready") for index in range(15)
    ]
    runner = _runner(tmp_path, state=SequencedReportState(sequence))

    _, judgement, _ = runner.execute(runner.preflight("whyyou-local"))

    a2 = next(item for item in judgement.assertion_results if item.assertion_id == "H03-A2")
    assert a2.status is AssertionStatus.INCONCLUSIVE
    assert judgement.verdict is Verdict.INCONCLUSIVE


def test_restore_is_reprobed_within_deadline_before_declaring_failure(tmp_path):
    fault = DelayedFault(restore_after=3)
    runner = _runner(tmp_path, fault=fault)

    run, judgement, _ = runner.execute(runner.preflight("whyyou-local"))

    assert fault.restore_calls == 3
    assert run.state is RunState.COMPLETED
    assert judgement.verdict is Verdict.PASS
