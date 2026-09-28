from __future__ import annotations

from dataclasses import replace

from engine.adapters.base import AdapterResult
from engine.executors.e03_before import E03BeforeExecutor
from engine.models import AssertionStatus, ExecutionProfile, Phase
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters
from tests.fixtures.spec002 import EVENT_ID, RUN_ID


def test_e03_before_scenario_is_canonical_but_subset_executor_does_not_claim_a7():
    scenario = load("scenarios/E-03-BEFORE.yaml")
    assert scenario.execution_profile is ExecutionProfile.E03_BEFORE_V2
    assert scenario.applicable_assertion_ids == (
        "E03-A1",
        "E03-A2",
        "E03-A3",
        "E03-A4",
        "E03-A7",
        "E03-A8",
    )


def test_before_journey_proves_zero_injected_effects_then_exact_recovery(tmp_path):
    scenario = load("scenarios/E-03-BEFORE.yaml")
    adapters, _browser = make_adapters()
    result = E03BeforeExecutor(
        scenario, adapters, tmp_path, clock=FakeClock()
    ).collect_us3(run_id=RUN_ID)

    assert result.source_event_id == EVENT_ID
    assert result.injected_effects[0].phase is Phase.INJECTED
    assert result.injected_effects[0].effects["logical_report_ids"] == []
    assert result.recovered_effects[0].phase is Phase.RECOVERED
    assert result.recovered_effects[0].effects["logical_report_ids"] == ["report-01"]
    assert result.redrive is not None
    assert result.redrive.send_succeeded and result.redrive.delete_succeeded
    assert tuple(item.assertion_id for item in result.assertions) == (
        "E03-A1",
        "E03-A2",
        "E03-A3",
        "E03-A4",
        "E03-A8",
    )
    assert all(item.status is AssertionStatus.PASS for item in result.assertions)
    assert result.pending_assertion_ids == ("E03-A7",)
    assert adapters.fault.events.index("fault.restore") < adapters.queue.events.index(
        "queue.redrive"
    )


def test_before_journey_polls_for_the_async_boundary_receipt(tmp_path):
    class DelayedBoundary:
        def __init__(self, delegate):
            self.delegate = delegate
            self.calls = 0

        def read_boundary_receipt(self, **kwargs):
            self.calls += 1
            if self.calls < 3:
                return AdapterResult(False, "BOUNDARY_RECEIPT_MISSING")
            return self.delegate.read_boundary_receipt(**kwargs)

    scenario = load("scenarios/E-03-BEFORE.yaml")
    adapters, _browser = make_adapters()
    boundary = DelayedBoundary(adapters.boundary_receipts)
    adapters = replace(adapters, boundary_receipts=boundary)
    clock = FakeClock()
    started = clock.now()

    result = E03BeforeExecutor(
        scenario, adapters, tmp_path, clock=clock
    ).collect_us3(run_id=RUN_ID)

    assert result.boundary.outbox_event_id == EVENT_ID
    assert boundary.calls == 3
    assert (clock.now() - started).total_seconds() == 4
