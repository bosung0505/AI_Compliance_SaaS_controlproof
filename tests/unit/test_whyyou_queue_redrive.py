from __future__ import annotations

import json
from types import SimpleNamespace

from engine.adapters.base import AdapterResult
from engine.adapters.whyyou.queue import WhyYouQueueAdapter
from engine.execution import coordinate_reporting_recovery
from engine.models import Phase
from tests.fixtures.spec002 import (
    EVENT_ID,
    OPERATION_ID,
    RUN_ID,
    SESSION_ID,
    reporting_effect,
)

SOURCE_URL = "http://localhost:4566/000000000000/iep-reporting"
DLQ_URL = "http://localhost:4566/000000000000/iep-reporting-dlq"


def _settings(tmp_path):
    return SimpleNamespace(
        whyyou_aws_endpoint_url="http://localhost:4566",
        whyyou_aws_region="ap-northeast-2",
        reporting_queue_name="iep-reporting",
        reporting_dlq_name="iep-reporting-dlq",
        reporting_max_receive_count=3,
        reporting_visibility_timeout_seconds=5,
        fault_root=tmp_path / "faults",
    )


def _body(event_id=EVENT_ID, session_id=SESSION_ID):
    return json.dumps(
        {
            "event_type": "report.generation_requested",
            "payload": {
                "event_id": str(event_id),
                "payload": {"interview_session_id": str(session_id)},
            },
        },
        sort_keys=True,
        separators=(",", ":"),
    )


class Sqs:
    def __init__(self, *, fail_send=False, fail_delete=False):
        self.fail_send = fail_send
        self.fail_delete = fail_delete
        self.operations = []
        self.messages = [
            {
                "MessageId": "foreign",
                "ReceiptHandle": "foreign-receipt",
                "Body": _body(event_id="00000000-0000-7000-8000-000000000699"),
                "Attributes": {"ApproximateReceiveCount": "3"},
            },
            {
                "MessageId": "selected",
                "ReceiptHandle": "selected-receipt",
                "Body": _body(),
                "Attributes": {"ApproximateReceiveCount": "3"},
                "MessageAttributes": {
                    "trace": {"DataType": "String", "StringValue": "safe-value"}
                },
            },
        ]

    def get_queue_url(self, *, QueueName):
        return {"QueueUrl": SOURCE_URL if QueueName == "iep-reporting" else DLQ_URL}

    def receive_message(self, **_kwargs):
        return {"Messages": self.messages}

    def send_message(self, **kwargs):
        self.operations.append(("send", kwargs))
        if self.fail_send:
            raise RuntimeError("send failed")
        return {"MessageId": "republished"}

    def delete_message(self, **kwargs):
        self.operations.append(("delete", kwargs))
        if self.fail_delete:
            raise RuntimeError("delete failed")
        return {}


class Fault:
    def restore(self, **_kwargs):
        return AdapterResult(
            True,
            "ENVIRONMENT_RESTORED",
            {"marker_inactive": True, "worker_healthy": True},
        )


class Effects:
    def __init__(self):
        self.reads = 0

    def read_reporting_effects(self, **kwargs):
        self.reads += 1
        if self.reads == 1:
            return (
                reporting_effect(
                    run_id=kwargs["run_id"],
                    phase=Phase.RECOVERED,
                    logical_operation_id=kwargs["logical_operation_id"],
                    source_event_id=kwargs["source_event_id"],
                    effects={
                        "logical_report_ids": [],
                        "projection_document_ids": [],
                        "projection_report_ids": [],
                        "processed_keys": [],
                        "source_outbox_event_ids": [str(EVENT_ID)],
                    },
                ),
            )
        return (
            reporting_effect(
                run_id=kwargs["run_id"],
                phase=Phase.RECOVERED,
                logical_operation_id=kwargs["logical_operation_id"],
                source_event_id=kwargs["source_event_id"],
            ),
        )


class Clock:
    def __init__(self):
        self.sleeps = []

    def sleep(self, seconds):
        self.sleeps.append(seconds)


def _select(adapter):
    result = adapter.read_dlq(
        source_event_id=str(EVENT_ID),
        subject_ref="candidate-01",
        session_id=str(SESSION_ID),
    )
    assert result.ok


def test_safe_redrive_preserves_exact_body_and_attributes_and_foreign_message(tmp_path):
    sqs = Sqs()
    adapter = WhyYouQueueAdapter(_settings(tmp_path), sqs_client=sqs)
    _select(adapter)

    receipt = adapter.redrive(source_event_id=str(EVENT_ID))

    assert receipt.send_succeeded and receipt.delete_succeeded
    assert [name for name, _ in sqs.operations] == ["send", "delete"]
    assert sqs.operations[0][1]["MessageBody"] == _body()
    assert sqs.operations[0][1]["MessageAttributes"]["trace"]["StringValue"] == "safe-value"
    assert sqs.operations[1][1]["ReceiptHandle"] == "selected-receipt"


def test_send_failure_preserves_dlq_and_delete_uncertainty_is_not_safe(tmp_path):
    failed_send = Sqs(fail_send=True)
    adapter = WhyYouQueueAdapter(_settings(tmp_path), sqs_client=failed_send)
    _select(adapter)
    receipt = adapter.redrive(source_event_id=str(EVENT_ID))
    assert not receipt.send_succeeded and not receipt.delete_succeeded
    assert [name for name, _ in failed_send.operations] == ["send"]

    failed_delete = Sqs(fail_delete=True)
    adapter = WhyYouQueueAdapter(_settings(tmp_path), sqs_client=failed_delete)
    _select(adapter)
    outcome = coordinate_reporting_recovery(
        fault=Fault(),
        redrive=adapter,
        effects=Effects(),
        run_id=RUN_ID,
        source_event_id=EVENT_ID,
        logical_operation_id=OPERATION_ID,
        subject={"subject_ref": "candidate-01"},
        clock=Clock(),
        poll_seconds=1,
        deadline_seconds=2,
    )
    assert outcome.redrive is not None and outcome.redrive.send_succeeded
    assert not outcome.redrive.delete_succeeded
    assert outcome.restore_safe is False


def test_common_recovery_persists_receipt_and_polls_until_reporting_effects_exist(tmp_path):
    sqs = Sqs()
    adapter = WhyYouQueueAdapter(_settings(tmp_path), sqs_client=sqs)
    _select(adapter)
    effects = Effects()
    clock = Clock()
    rows = []

    outcome = coordinate_reporting_recovery(
        fault=Fault(),
        redrive=adapter,
        effects=effects,
        run_id=RUN_ID,
        source_event_id=EVENT_ID,
        logical_operation_id=OPERATION_ID,
        subject={"subject_ref": "candidate-01"},
        clock=clock,
        poll_seconds=1,
        deadline_seconds=3,
        append_receipt=lambda path, value: rows.append((path, value)),
    )

    assert outcome.restore_safe is True
    assert effects.reads == 2 and clock.sleeps == [1]
    assert outcome.recovered_effects[0].effects["logical_report_ids"] == ["report-01"]
    assert rows[0][0] == "redrive-receipts.jsonl"
    assert rows[0][1]["source_event_id"] == str(EVENT_ID)
