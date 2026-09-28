"""LocalStack reporting queue observations and single-message safe redrive."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import NAMESPACE_URL, UUID, uuid5

import boto3  # type: ignore[import-untyped]
from botocore.config import Config  # type: ignore[import-untyped]

from engine.adapters.base import AdapterResult
from engine.config import Settings
from engine.models import (
    DeliveryAttemptOutcome,
    DeliveryAttemptRecord,
    FaultVariant,
    Presence,
    QueueTopologySnapshot,
    RedriveReceipt,
    TerminalFailureRecord,
    TerminalFailureRoute,
    canonical_json_bytes,
    sha256_bytes,
)


class SqsClient(Protocol):
    def get_queue_url(self, **kwargs: object) -> Mapping[str, object]: ...

    def get_queue_attributes(self, **kwargs: object) -> Mapping[str, object]: ...

    def receive_message(self, **kwargs: object) -> Mapping[str, object]: ...

    def send_message(self, **kwargs: object) -> Mapping[str, object]: ...

    def delete_message(self, **kwargs: object) -> Mapping[str, object]: ...


class QueueAdapterError(RuntimeError):
    """Sanitized queue boundary failure."""


class QueueAccessError(QueueAdapterError):
    pass


class QueueContractError(QueueAdapterError):
    pass


@dataclass(frozen=True, slots=True)
class _SelectedMessage:
    source_event_id: UUID
    message_id: str
    receipt_handle: str
    body: str
    message_attributes: dict[str, Any]


class WhyYouQueueAdapter:
    def __init__(self, settings: Settings, *, sqs_client: SqsClient | None = None) -> None:
        self.settings = settings
        self._client = sqs_client or _localstack_client(settings)
        self._source_url: str | None = None
        self._dlq_url: str | None = None
        self._selected: dict[UUID, _SelectedMessage] = {}

    def capture_topology(self) -> QueueTopologySnapshot:
        try:
            source_url, dlq_url = self._queue_urls()
            source = self._attributes(
                source_url,
                (
                    "QueueArn",
                    "VisibilityTimeout",
                    "MessageRetentionPeriod",
                    "RedrivePolicy",
                    "ApproximateNumberOfMessages",
                    "ApproximateNumberOfMessagesNotVisible",
                ),
            )
            dlq = self._attributes(
                dlq_url,
                (
                    "QueueArn",
                    "MessageRetentionPeriod",
                    "ApproximateNumberOfMessages",
                    "ApproximateNumberOfMessagesNotVisible",
                ),
            )
        except QueueAdapterError:
            raise
        except Exception as exc:
            raise QueueAccessError("LocalStack reporting queue attributes are unavailable") from exc
        try:
            policy = json.loads(source["RedrivePolicy"])
            max_receive = int(policy["maxReceiveCount"])
            visibility = int(source["VisibilityTimeout"])
            source_retention = int(source["MessageRetentionPeriod"])
            dlq_retention = int(dlq["MessageRetentionPeriod"])
            source_arn = source["QueueArn"]
            dlq_arn = dlq["QueueArn"]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise QueueContractError("reporting queue attributes are malformed") from exc
        if policy.get("deadLetterTargetArn") != dlq_arn:
            raise QueueContractError("reporting redrive target does not match the configured DLQ")
        if max_receive != self.settings.reporting_max_receive_count:
            raise QueueContractError("reporting max receive count does not match the profile")
        if visibility != self.settings.reporting_visibility_timeout_seconds:
            raise QueueContractError("reporting visibility timeout does not match the profile")
        if not source_arn.endswith(f":{self.settings.reporting_queue_name}"):
            raise QueueContractError("reporting source queue ARN does not match the profile")
        if not dlq_arn.endswith(f":{self.settings.reporting_dlq_name}"):
            raise QueueContractError("reporting DLQ ARN does not match the profile")
        try:
            return QueueTopologySnapshot(
                source_queue_name=self.settings.reporting_queue_name,
                source_queue_url_digest=sha256_bytes(source_url.encode("utf-8")),
                dead_letter_queue_name=self.settings.reporting_dlq_name,
                dead_letter_queue_arn=dlq_arn,
                max_receive_count=max_receive,
                visibility_timeout_seconds=visibility,
                source_retention_seconds=source_retention,
                dlq_retention_seconds=dlq_retention,
                redrive_policy_digest=sha256_bytes(canonical_json_bytes(policy)),
                captured_at=datetime.now(UTC),
            )
        except ValueError as exc:
            raise QueueContractError("reporting queue topology violates the profile") from exc

    def read_attempts(self, *, source_event_id: str, run_id: str) -> AdapterResult:
        try:
            event_id = UUID(source_event_id)
            active_run_id = UUID(run_id)
        except ValueError:
            return AdapterResult(False, "INVALID_ATTEMPT_IDENTITY")
        path = self.settings.fault_root / "receipts" / f"{active_run_id}.jsonl"
        if not path.exists():
            return AdapterResult(
                True,
                "DELIVERY_ATTEMPTS_READ",
                {"presence": Presence.ABSENT, "records": ()},
            )
        records: list[DeliveryAttemptRecord] = []
        malformed = 0
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return AdapterResult(
                False,
                "DELIVERY_ATTEMPTS_UNAVAILABLE",
                {"presence": Presence.UNAVAILABLE, "records": ()},
            )
        for line_number, line in enumerate(lines, start=1):
            try:
                receipt = json.loads(line)
                if (
                    receipt.get("schema_version")
                    != "controlproof.whyyou-fault-receipt.v2"
                    or UUID(str(receipt["run_id"])) != active_run_id
                    or UUID(str(receipt["outbox_event_id"])) != event_id
                    or receipt.get("fault_variant") != FaultVariant.BEFORE_RESULT_DURABLE.value
                    or receipt.get("boundary") != "BEFORE_REPORT_SIDE_EFFECT"
                ):
                    continue
                receipt_digest = sha256_bytes(canonical_json_bytes(receipt))
                records.append(
                    DeliveryAttemptRecord(
                        run_id=active_run_id,
                        subject_ref=str(receipt["session_id"]),
                        source_event_id=event_id,
                        consumer_name="reporting-worker",
                        delivery_attempt=int(receipt["delivery_attempt"]),
                        fault_variant=FaultVariant.BEFORE_RESULT_DURABLE,
                        outcome=DeliveryAttemptOutcome.FAULT_TRIGGERED,
                        observed_at=datetime.fromisoformat(str(receipt["triggered_at"])),
                        receipt_artifact_id=uuid5(
                            NAMESPACE_URL,
                            f"{active_run_id}:{line_number}:{receipt_digest}",
                        ),
                    )
                )
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                malformed += 1
        records.sort(key=lambda item: (item.delivery_attempt, item.observed_at))
        return AdapterResult(
            True,
            "DELIVERY_ATTEMPTS_READ",
            {
                "presence": Presence.PRESENT if records else Presence.ABSENT,
                "records": tuple(records),
                "malformed_records": malformed,
            },
        )

    def read_dlq(
        self,
        *,
        source_event_id: str,
        subject_ref: str,
        session_id: str | None = None,
    ) -> AdapterResult:
        try:
            event_id = UUID(source_event_id)
            expected_session_id = UUID(session_id or subject_ref)
        except ValueError:
            return AdapterResult(False, "INVALID_DLQ_IDENTITY")
        try:
            _, dlq_url = self._queue_urls()
            response = self._client.receive_message(
                QueueUrl=dlq_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=0,
                VisibilityTimeout=0,
                AttributeNames=["ApproximateReceiveCount"],
                MessageAttributeNames=["All"],
            )
        except Exception:  # noqa: BLE001 - SQS clients expose provider-specific errors
            return AdapterResult(
                False,
                "DLQ_READ_UNAVAILABLE",
                {"presence": Presence.UNAVAILABLE, "terminal_failure": None},
            )
        messages = response.get("Messages", ())
        if not isinstance(messages, list):
            messages = []
        for raw in messages:
            selected = self._match_message(raw, event_id, expected_session_id)
            if selected is None:
                continue
            self._selected[event_id] = selected
            receive_count = _receive_count(raw)
            terminal = TerminalFailureRecord(
                route_type=TerminalFailureRoute.INFRASTRUCTURE_DLQ,
                route_locator="localstack:sqs:iep-reporting-dlq",
                source_event_id=event_id,
                subject_ref=subject_ref,
                last_delivery_attempt=receive_count,
                last_failure_code="CONTROLPROOF_INJECTED_BEFORE_DURABLE",
                message_body_digest=sha256_bytes(selected.body.encode("utf-8")),
                observed_at=datetime.now(UTC),
            )
            return AdapterResult(
                True,
                "DLQ_MATCH_READ",
                {"presence": Presence.PRESENT, "terminal_failure": terminal},
            )
        return AdapterResult(
            True,
            "DLQ_MATCH_READ",
            {"presence": Presence.ABSENT, "terminal_failure": None},
        )

    def redrive(self, *, source_event_id: str) -> RedriveReceipt:
        event_id = UUID(source_event_id)
        selected = self._selected.get(event_id)
        if selected is None:
            raise QueueContractError("safe redrive requires a previously matched DLQ message")
        source_url, dlq_url = self._queue_urls()
        digest = sha256_bytes(selected.body.encode("utf-8"))
        send_kwargs: dict[str, Any] = {
            "QueueUrl": source_url,
            "MessageBody": selected.body,
        }
        if selected.message_attributes:
            send_kwargs["MessageAttributes"] = selected.message_attributes
        try:
            response = self._client.send_message(**send_kwargs)
            message_id = response.get("MessageId")
            if not isinstance(message_id, str) or not message_id:
                raise ValueError("missing republished message ID")
        except Exception:  # noqa: BLE001 - preserve a sanitized mutation receipt
            return RedriveReceipt(
                source_event_id=event_id,
                dlq_message_id=selected.message_id,
                republished_message_id=None,
                body_digest=digest,
                send_succeeded=False,
                delete_succeeded=False,
                redriven_at=datetime.now(UTC),
            )
        try:
            self._client.delete_message(
                QueueUrl=dlq_url,
                ReceiptHandle=selected.receipt_handle,
            )
            deleted = True
        except Exception:  # noqa: BLE001 - deletion uncertainty is evidence, not a secret
            deleted = False
        return RedriveReceipt(
            source_event_id=event_id,
            dlq_message_id=selected.message_id,
            republished_message_id=message_id,
            body_digest=digest,
            send_succeeded=True,
            delete_succeeded=deleted,
            redriven_at=datetime.now(UTC),
        )

    def _queue_urls(self) -> tuple[str, str]:
        if self._source_url is None:
            self._source_url = self._queue_url(self.settings.reporting_queue_name)
        if self._dlq_url is None:
            self._dlq_url = self._queue_url(self.settings.reporting_dlq_name)
        return self._source_url, self._dlq_url

    def _queue_url(self, name: str) -> str:
        try:
            response = self._client.get_queue_url(QueueName=name)
            value = response.get("QueueUrl")
        except Exception as exc:
            raise QueueAccessError("LocalStack queue URL is unavailable") from exc
        if not isinstance(value, str) or not value:
            raise QueueAccessError("LocalStack queue URL is unavailable")
        return value

    def _attributes(self, url: str, names: tuple[str, ...]) -> dict[str, str]:
        try:
            response = self._client.get_queue_attributes(
                QueueUrl=url, AttributeNames=list(names)
            )
        except Exception as exc:
            raise QueueAccessError("LocalStack queue attributes are unavailable") from exc
        attributes = response.get("Attributes")
        if not isinstance(attributes, Mapping):
            raise QueueContractError("reporting queue attributes are malformed")
        return {str(key): str(value) for key, value in attributes.items()}

    @staticmethod
    def _match_message(
        raw: object,
        event_id: UUID,
        session_id: UUID,
    ) -> _SelectedMessage | None:
        if not isinstance(raw, Mapping):
            return None
        body = raw.get("Body")
        message_id = raw.get("MessageId")
        receipt = raw.get("ReceiptHandle")
        if not all(isinstance(value, str) and value for value in (body, message_id, receipt)):
            return None
        try:
            envelope = json.loads(str(body))
            event = envelope["payload"]
            payload = event["payload"]
            matched = (
                envelope["event_type"] == "report.generation_requested"
                and UUID(str(event["event_id"])) == event_id
                and UUID(str(payload["interview_session_id"])) == session_id
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None
        if not matched:
            return None
        raw_attributes = raw.get("MessageAttributes", {})
        attributes = dict(raw_attributes) if isinstance(raw_attributes, Mapping) else {}
        return _SelectedMessage(event_id, str(message_id), str(receipt), str(body), attributes)


def _receive_count(raw: Mapping[str, Any]) -> int:
    attributes = raw.get("Attributes", {})
    if not isinstance(attributes, Mapping):
        return 1
    try:
        return max(1, int(str(attributes.get("ApproximateReceiveCount", 1))))
    except ValueError:
        return 1


def _localstack_client(settings: Settings) -> SqsClient:
    return boto3.client(
        "sqs",
        region_name=settings.whyyou_aws_region,
        endpoint_url=settings.whyyou_aws_endpoint_url,
        aws_access_key_id="local-controlproof",
        aws_secret_access_key="local-controlproof",
        config=Config(connect_timeout=3, read_timeout=3, retries={"max_attempts": 1}),
    )
