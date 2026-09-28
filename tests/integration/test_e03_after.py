from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from engine.adapters.base import AdapterResult
from engine.executors.e03_after import E03AfterExecutor
from engine.models import AssertionStatus, ExecutionProfile, Phase, Presence
from engine.runner import build_profile_runner
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters
from tests.fixtures.spec002 import EVENT_ID, RUN_ID, reporting_effect


def _results(**adapter_options):
    scenario = load("scenarios/E-03-AFTER.yaml")
    adapters, _browser = make_adapters(
        injected_reporting_present=True,
        dlq_presence=Presence.ABSENT,
        **adapter_options,
    )
    result = E03AfterExecutor(
        scenario,
        adapters,
        Path("runs"),
        clock=FakeClock(),
    ).collect_us4(run_id=RUN_ID)
    return scenario, adapters, result


def test_after_profile_is_registered_and_complete_for_its_four_assertions(tmp_path):
    scenario = load("scenarios/E-03-AFTER.yaml")
    adapters, _browser = make_adapters(
        injected_reporting_present=True,
        dlq_presence=Presence.ABSENT,
    )

    runner = build_profile_runner(scenario, adapters, tmp_path, clock=FakeClock())
    result = runner.collect_us4(run_id=RUN_ID)

    assert scenario.execution_profile is ExecutionProfile.E03_AFTER_V2
    assert isinstance(runner, E03AfterExecutor)
    assert tuple(item.assertion_id for item in result.assertions) == (
        "E03-A1",
        "E03-A5",
        "E03-A6",
        "E03-A8",
    )
    assert all(item.status is AssertionStatus.PASS for item in result.assertions)
    assert result.committed_effects[0].phase is Phase.INJECTED
    assert result.final_effects[0].phase is Phase.RECOVERED
    assert result.committed_effects[0].state_digest == result.final_effects[0].state_digest


def test_after_missing_duplicate_ack_represents_handler_short_circuit_failure():
    scenario = load("scenarios/E-03-AFTER.yaml")
    adapters, _browser = make_adapters(
        injected_reporting_present=True,
        dlq_presence=Presence.ABSENT,
    )

    class HandlerRerunReceipt:
        def read_duplicate_ack(self, **_kwargs):
            return AdapterResult(
                True,
                "DUPLICATE_ACK_READ",
                {
                    "receipt": {
                        "outbox_event_id": str(EVENT_ID),
                        "delivery_attempt": 2,
                        "consumer_name": "reporting-worker",
                        "handler_skipped": False,
                        "acknowledged": True,
                    }
                },
            )

    result = E03AfterExecutor(
        scenario,
        replace(adapters, duplicate_acks=HandlerRerunReceipt()),
        Path("runs"),
        clock=FakeClock(),
    ).collect_us4(run_id=RUN_ID)
    judged = {item.assertion_id: item for item in result.assertions}
    assert judged["E03-A6"].status is AssertionStatus.FAIL


def test_after_duplicate_business_effect_fails_exact_effect_comparison():
    scenario = load("scenarios/E-03-AFTER.yaml")
    adapters, _browser = make_adapters(
        injected_reporting_present=True,
        dlq_presence=Presence.ABSENT,
    )
    base_effects = adapters.effects

    class DuplicateEffects:
        def read_reporting_effects(self, **kwargs):
            observed = base_effects.read_reporting_effects(**kwargs)
            if kwargs["phase"] == "INJECTED":
                return observed
            return (
                reporting_effect(
                    run_id=kwargs["run_id"],
                    phase=Phase.RECOVERED,
                    logical_operation_id=kwargs["logical_operation_id"],
                    source_event_id=EVENT_ID,
                    step_id=kwargs["step_id"],
                    effects={
                        "logical_report_ids": ["report-01", "report-02"],
                        "projection_document_ids": ["projection-01", "projection-02"],
                        "projection_report_ids": ["report-01", "report-02"],
                        "processed_keys": [
                            {
                                "consumer_name": "reporting-worker",
                                "event_id": str(EVENT_ID),
                                "event_version": 1,
                            }
                        ],
                        "source_outbox_event_ids": [str(EVENT_ID)],
                    },
                    state_digest="f" * 64,
                ),
            )

        def read_decision_effects(self, **kwargs):
            return base_effects.read_decision_effects(**kwargs)

    result = E03AfterExecutor(
        scenario,
        replace(adapters, effects=DuplicateEffects()),
        Path("runs"),
        clock=FakeClock(),
    ).collect_us4(run_id=RUN_ID)
    judged = {item.assertion_id: item for item in result.assertions}
    assert judged["E03-A5"].status is AssertionStatus.FAIL


def test_after_boundary_not_reached_is_inconclusive_not_target_pass_or_fail():
    _scenario, _adapters, result = _results(after_effect=False)
    judged = {item.assertion_id: item for item in result.assertions}
    assert judged["E03-A1"].status is AssertionStatus.INCONCLUSIVE
    assert judged["E03-A5"].status is AssertionStatus.INCONCLUSIVE
    assert judged["E03-A6"].status is AssertionStatus.INCONCLUSIVE


def test_after_unexpected_dlq_is_a_direct_failure():
    scenario = load("scenarios/E-03-AFTER.yaml")
    adapters, _browser = make_adapters(
        injected_reporting_present=True,
        dlq_presence=Presence.PRESENT,
    )
    result = E03AfterExecutor(
        scenario,
        adapters,
        Path("runs"),
        clock=FakeClock(),
    ).collect_us4(run_id=RUN_ID)
    judged = {item.assertion_id: item for item in result.assertions}
    assert judged["E03-A1"].status is AssertionStatus.FAIL
    assert judged["E03-A8"].status is AssertionStatus.FAIL
