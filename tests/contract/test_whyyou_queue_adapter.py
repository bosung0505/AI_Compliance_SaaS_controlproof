from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import UUID

import pytest

from engine.adapters.whyyou.queue import (
    QueueAccessError,
    QueueContractError,
    WhyYouQueueAdapter,
)
from engine.models import Presence

EVENT_ID = UUID("00000000-0000-7000-8000-000000000301")
SESSION_ID = UUID("00000000-0000-7000-8000-000000000302")
SOURCE_URL = "http://localhost:4566/000000000000/iep-reporting"
DLQ_URL = "http://localhost:4566/000000000000/iep-reporting-dlq"
SOURCE_ARN = "arn:aws:sqs:ap-northeast-2:000000000000:iep-reporting"
DLQ_ARN = "arn:aws:sqs:ap-northeast-2:000000000000:iep-reporting-dlq"


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
            "company_id": "00000000-0000-7000-8000-000000000303",
            "event_type": "report.generation_requested",
            "trace_id": "fixture",
            "payload": {
                "event_id": str(event_id),
                "event_version": 1,
                "aggregate_type": "interview_session",
                "aggregate_id": str(session_id),
                "aggregate_version": 1,
                "idempotency_key": "fixture",
                "occurred_at": "2026-09-28T00:00:00+00:00",
                "payload": {"interview_session_id": str(session_id)},
            },
        },
        sort_keys=True,
        separators=(",", ":"),
    )


class RecordingSqs:
    def __init__(self):
        self.messages = []
        self.operations = []
        self.fail_receive = False
        self.fail_send = False
        self.fail_delete = False
        self.source_attributes = {
            "QueueArn": SOURCE_ARN,
            "VisibilityTimeout": "5",
            "MessageRetentionPeriod": "3600",
            "RedrivePolicy": json.dumps(
                {"deadLetterTargetArn": DLQ_ARN, "maxReceiveCount": 3}
            ),
            "ApproximateNumberOfMessages": "0",
            "ApproximateNumberOfMessagesNotVisible": "0",
        }
        self.dlq_attributes = {
            "QueueArn": DLQ_ARN,
            "MessageRetentionPeriod": "7200",
            "ApproximateNumberOfMessages": "1",
            "ApproximateNumberOfMessagesNotVisible": "0",
        }

    def get_queue_url(self, *, QueueName):
        return {"QueueUrl": SOURCE_URL if QueueName == "iep-reporting" else DLQ_URL}

    def get_queue_attributes(self, *, QueueUrl, AttributeNames):
        del AttributeNames
        return {
            "Attributes": self.source_attributes if QueueUrl == SOURCE_URL else self.dlq_attributes
        }

    def receive_message(self, **_kwargs):
        if self.fail_receive:
            raise RuntimeError("secret=do-not-leak")
        return {"Messages": list(self.messages)}

    def send_message(self, **kwargs):
        self.operations.append(("send", kwargs))
        if self.fail_send:
            raise RuntimeError("credential=do-not-leak")
        return {"MessageId": "republished-01"}

    def delete_message(self, **kwargs):
        self.operations.append(("delete", kwargs))
        if self.fail_delete:
            raise RuntimeError("receipt=do-not-leak")
        return {}


def _message(*, event_id=EVENT_ID, session_id=SESSION_ID, receive_count="3"):
    return {
        "MessageId": f"message-{event_id}",
        "ReceiptHandle": f"receipt-{event_id}",
        "Body": _body(event_id, session_id),
        "Attributes": {"ApproximateReceiveCount": receive_count},
        "MessageAttributes": {"fixture": {"DataType": "String", "StringValue": "safe"}},
    }


def test_queue_topology_requires_exact_localstack_redrive_contract(tmp_path):
    sqs = RecordingSqs()
    adapter = WhyYouQueueAdapter(_settings(tmp_path), sqs_client=sqs)

    topology = adapter.capture_topology()

    assert topology.max_receive_count == 3
    assert topology.visibility_timeout_seconds == 5
    assert topology.dead_letter_queue_arn == DLQ_ARN

    sqs.source_attributes["VisibilityTimeout"] = "30"
    with pytest.raises(QueueContractError, match="visibility"):
        adapter.capture_topology()


def test_dlq_read_selects_only_matching_event_and_session_without_mutation(tmp_path):
    sqs = RecordingSqs()
    sqs.messages = [_message(event_id=UUID(int=999)), _message()]
    adapter = WhyYouQueueAdapter(_settings(tmp_path), sqs_client=sqs)

    result = adapter.read_dlq(source_event_id=str(EVENT_ID), subject_ref=str(SESSION_ID))

    assert result.ok
    assert result.data["presence"] is Presence.PRESENT
    assert result.data["terminal_failure"].source_event_id == EVENT_ID
    assert sqs.operations == []


def test_dlq_empty_and_unavailable_are_not_conflated_or_leaky(tmp_path):
    sqs = RecordingSqs()
    adapter = WhyYouQueueAdapter(_settings(tmp_path), sqs_client=sqs)
    empty = adapter.read_dlq(source_event_id=str(EVENT_ID), subject_ref=str(SESSION_ID))
    assert empty.ok and empty.data["presence"] is Presence.ABSENT

    sqs.fail_receive = True
    unavailable = adapter.read_dlq(
        source_event_id=str(EVENT_ID), subject_ref=str(SESSION_ID)
    )
    assert not unavailable.ok
    assert unavailable.data["presence"] is Presence.UNAVAILABLE
    assert "do-not-leak" not in f"{unavailable.code}{unavailable.detail}{unavailable.data}"


def test_safe_redrive_sends_before_delete_and_never_deletes_after_send_failure(tmp_path):
    sqs = RecordingSqs()
    sqs.messages = [_message()]
    adapter = WhyYouQueueAdapter(_settings(tmp_path), sqs_client=sqs)
    assert adapter.read_dlq(
        source_event_id=str(EVENT_ID), subject_ref=str(SESSION_ID)
    ).ok

    receipt = adapter.redrive(source_event_id=str(EVENT_ID))

    assert receipt.send_succeeded and receipt.delete_succeeded
    assert [operation for operation, _ in sqs.operations] == ["send", "delete"]
    assert sqs.operations[0][1]["MessageBody"] == _body()

    failed = RecordingSqs()
    failed.messages = [_message()]
    failed.fail_send = True
    adapter = WhyYouQueueAdapter(_settings(tmp_path), sqs_client=failed)
    adapter.read_dlq(source_event_id=str(EVENT_ID), subject_ref=str(SESSION_ID))
    receipt = adapter.redrive(source_event_id=str(EVENT_ID))
    assert not receipt.send_succeeded and not receipt.delete_succeeded
    assert [operation for operation, _ in failed.operations] == ["send"]


def test_queue_access_exception_is_sanitized(tmp_path):
    class Denied(RecordingSqs):
        def get_queue_url(self, *, QueueName):
            raise RuntimeError(f"token=top-secret:{QueueName}")

    with pytest.raises(QueueAccessError) as captured:
        WhyYouQueueAdapter(_settings(tmp_path), sqs_client=Denied()).capture_topology()
    assert "top-secret" not in str(captured.value)
