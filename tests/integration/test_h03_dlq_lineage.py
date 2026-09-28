from __future__ import annotations

import json
from dataclasses import replace

import pytest

from engine.adapters.base import AdapterResult
from engine.adapters.whyyou.queue import QueueContractError, WhyYouQueueAdapter
from engine.executors.h03_dlq import H03DlqExecutor
from engine.judges.h03_dlq import judge_h03_dlq
from engine.models import AssertionStatus, Presence
from engine.runner import build_profile_runner
from engine.scenario import load
from tests.contract.test_whyyou_queue_adapter import (
    DLQ_ARN,
    EVENT_ID,
    SESSION_ID,
    RecordingSqs,
    _message,
    _settings,
)
from tests.fixtures.fake_adapters import FakeClock, make_adapters
from tests.fixtures.spec002 import EVENT_ID as FIXTURE_EVENT_ID
from tests.fixtures.spec002 import RUN_ID


def _write_attempts(tmp_path, run_id):
    path = tmp_path / "faults" / "receipts" / f"{run_id}.jsonl"
    path.parent.mkdir(parents=True)
    lines = [
        {
            "schema_version": "controlproof.whyyou-fault-receipt.v2",
            "run_id": run_id,
            "session_id": str(SESSION_ID),
            "outbox_event_id": str(EVENT_ID),
            "event_version": 1,
            "delivery_attempt": attempt,
            "fault_variant": "BEFORE_RESULT_DURABLE",
            "boundary": "BEFORE_REPORT_SIDE_EFFECT",
            "triggered_at": f"2026-09-28T00:00:0{attempt}+00:00",
            "one_shot_consumed": False,
        }
        for attempt in range(1, 4)
    ]
    path.write_text("\n".join(json.dumps(line) for line in lines) + "\n", encoding="utf-8")


def test_attempts_to_matching_dlq_form_one_preserved_failure_lineage(tmp_path):
    run_id = "00000000-0000-7000-8000-000000000399"
    _write_attempts(tmp_path, run_id)
    sqs = RecordingSqs()
    sqs.messages = [_message()]
    adapter = WhyYouQueueAdapter(_settings(tmp_path), sqs_client=sqs)

    attempts = adapter.read_attempts(source_event_id=str(EVENT_ID), run_id=run_id)
    dlq = adapter.read_dlq(source_event_id=str(EVENT_ID), subject_ref=str(SESSION_ID))
    results = judge_h03_dlq(
        attempts=attempts.data["records"],
        terminal=dlq.data["terminal_failure"],
        dlq_presence=dlq.data["presence"],
        ui_status="final_failed",
        api_status="failed",
        operator_locator=dlq.data["terminal_failure"].route_locator,
    )
    assert [record.delivery_attempt for record in attempts.data["records"]] == [1, 2, 3]
    assert results[0].status is AssertionStatus.PASS


def test_wrong_queue_contract_refuses_before_any_run_is_created(tmp_path):
    sqs = RecordingSqs()
    sqs.source_attributes["RedrivePolicy"] = json.dumps(
        {"deadLetterTargetArn": DLQ_ARN, "maxReceiveCount": 4}
    )
    adapter = WhyYouQueueAdapter(_settings(tmp_path), sqs_client=sqs)
    run_root = tmp_path / "runs"
    run_root.mkdir(exist_ok=True)
    existing = set(run_root.iterdir())
    with pytest.raises(QueueContractError, match="receive"):
        adapter.capture_topology()
    assert set(run_root.iterdir()) == existing


def test_access_loss_remains_unavailable_in_integration_projection(tmp_path):
    sqs = RecordingSqs()
    sqs.fail_receive = True
    adapter = WhyYouQueueAdapter(_settings(tmp_path), sqs_client=sqs)
    dlq = adapter.read_dlq(source_event_id=str(EVENT_ID), subject_ref=str(SESSION_ID))
    assert dlq.data["presence"] is Presence.UNAVAILABLE


def test_h03_dlq_profile_dispatches_to_its_registered_executor(tmp_path):
    scenario = load("scenarios/H-03-DLQ.yaml")
    adapters, _browser = make_adapters()
    runner = build_profile_runner(scenario, adapters, tmp_path, clock=FakeClock())
    assert isinstance(runner, H03DlqExecutor)


def test_us1_slice_collects_dlq_visibility_then_restores_before_redrive(tmp_path):
    scenario = load("scenarios/H-03-DLQ.yaml")
    adapters, _browser = make_adapters(status_class="failed")
    runner = H03DlqExecutor(scenario, adapters, tmp_path, clock=FakeClock())
    result = runner.collect_us1(
        run_id=RUN_ID,
    )
    assert result.baseline.ok is True
    assert result.fault_application.ok is True
    assert result.trigger.ok is True
    assert result.source_event_id == FIXTURE_EVENT_ID
    assert result.boundary.outbox_event_id == FIXTURE_EVENT_ID
    assert [item.delivery_attempt for item in result.attempts] == [1, 2, 3]
    assert result.assertions[0].status is AssertionStatus.PASS
    # The fixture API remains queued, so a final-failure-looking screen alone cannot pass A9.
    assert result.assertions[1].status is AssertionStatus.FAIL
    assert result.restore.ok is True
    assert result.redrive is not None
    assert result.redrive.send_succeeded is True
    assert result.redrive.delete_succeeded is True
    assert adapters.fault.events.index("fault.restore") < adapters.queue.events.index(
        "queue.redrive"
    )


def test_us1_slice_restores_the_fault_even_when_boundary_evidence_is_missing(tmp_path):
    class MissingBoundary:
        def read_boundary_receipt(self, **_kwargs):
            return AdapterResult(False, "BOUNDARY_RECEIPT_MISSING")

    scenario = load("scenarios/H-03-DLQ.yaml")
    adapters, _browser = make_adapters()
    adapters = replace(adapters, boundary_receipts=MissingBoundary())
    runner = H03DlqExecutor(scenario, adapters, tmp_path, clock=FakeClock())

    with pytest.raises(RuntimeError, match="BOUNDARY_RECEIPT_MISSING"):
        runner.collect_us1(run_id=RUN_ID)

    assert adapters.fault.events == ["fault.apply", "fault.restore"]
    assert "queue.redrive" not in adapters.queue.events
