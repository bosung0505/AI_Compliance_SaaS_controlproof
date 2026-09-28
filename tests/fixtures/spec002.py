"""Deterministic reusable builders for Spec 002 tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from engine.models import (
    AwsDeploymentStatus,
    BusinessEffectSnapshot,
    DeliveryAttemptOutcome,
    DeliveryAttemptRecord,
    EffectGroup,
    EnvironmentKind,
    FaultBoundary,
    FaultBoundaryReceipt,
    FaultVariant,
    GitIdentity,
    Phase,
    Presence,
    QueueTopologySnapshot,
    RedriveReceipt,
    TargetEnvironmentSnapshot,
    TerminalFailureRecord,
    TerminalFailureRoute,
)

FIXED_AT = datetime(2026, 9, 28, tzinfo=UTC)
RUN_ID = UUID("00000000-0000-7000-8000-000000000101")
SESSION_ID = UUID("00000000-0000-7000-8000-000000000102")
EVENT_ID = UUID("00000000-0000-7000-8000-000000000103")
OPERATION_ID = UUID("00000000-0000-7000-8000-000000000104")
ARTIFACT_ID = UUID("00000000-0000-7000-8000-000000000105")
MODEL_FIXTURE_DIGEST = "a" * 64

def _build[ModelT: BaseModel](
    model: type[ModelT], base: dict[str, Any], updates: dict[str, Any]
) -> ModelT:
    return model.model_validate({**base, **updates})


def environment_snapshot(**updates: Any) -> TargetEnvironmentSnapshot:
    return _build(
        TargetEnvironmentSnapshot,
        {
            "target_id": "whyyou-local",
            "environment_kind": EnvironmentKind.LOCAL_EMULATED,
            "host_os": "windows-11",
            "controlproof_commit": GitIdentity(commit_sha="a" * 40, dirty=False),
            "whyyou_commit": GitIdentity(commit_sha="b" * 40, dirty=False),
            "components": {"postgresql": "16", "localstack": "3.8"},
            "endpoints": {
                "api": "http://localhost:8080",
                "sqs": "http://localhost:4566",
            },
            "model_fixture_id": "h03-report-v1",
            "model_fixture_digest": MODEL_FIXTURE_DIGEST,
            "external_ai_allowed": False,
            "aws_deployment_status": AwsDeploymentStatus.NOT_RUN,
            "unverified_scope": (
                "AWS_SQS",
                "AWS_ECS",
                "AWS_IAM",
                "AWS_CLOUDWATCH",
                "AWS_NETWORK",
            ),
            "captured_at": FIXED_AT,
        },
        updates,
    )


def queue_topology(**updates: Any) -> QueueTopologySnapshot:
    return _build(
        QueueTopologySnapshot,
        {
            "source_queue_name": "iep-reporting",
            "source_queue_url_digest": "b" * 64,
            "dead_letter_queue_name": "iep-reporting-dlq",
            "dead_letter_queue_arn": (
                "arn:aws:sqs:ap-northeast-2:000000000000:iep-reporting-dlq"
            ),
            "max_receive_count": 3,
            "visibility_timeout_seconds": 5,
            "source_retention_seconds": 3600,
            "dlq_retention_seconds": 7200,
            "redrive_policy_digest": "c" * 64,
            "captured_at": FIXED_AT,
        },
        updates,
    )


def delivery_attempt(**updates: Any) -> DeliveryAttemptRecord:
    return _build(
        DeliveryAttemptRecord,
        {
            "run_id": RUN_ID,
            "subject_ref": "candidate-01",
            "source_event_id": EVENT_ID,
            "consumer_name": "reporting-worker",
            "delivery_attempt": 1,
            "fault_variant": FaultVariant.BEFORE_RESULT_DURABLE,
            "outcome": DeliveryAttemptOutcome.FAULT_TRIGGERED,
            "observed_at": FIXED_AT,
            "receipt_artifact_id": ARTIFACT_ID,
        },
        updates,
    )


def boundary_receipt(**updates: Any) -> FaultBoundaryReceipt:
    return _build(
        FaultBoundaryReceipt,
        {
            "run_id": RUN_ID,
            "session_id": SESSION_ID,
            "outbox_event_id": EVENT_ID,
            "delivery_attempt": 1,
            "fault_variant": FaultVariant.BEFORE_RESULT_DURABLE,
            "boundary": FaultBoundary.BEFORE_REPORT_SIDE_EFFECT,
            "triggered_at": FIXED_AT,
            "one_shot_consumed": False,
        },
        updates,
    )


def terminal_failure(**updates: Any) -> TerminalFailureRecord:
    return _build(
        TerminalFailureRecord,
        {
            "route_type": TerminalFailureRoute.INFRASTRUCTURE_DLQ,
            "route_locator": "localstack:sqs:iep-reporting-dlq",
            "source_event_id": EVENT_ID,
            "subject_ref": "candidate-01",
            "last_delivery_attempt": 3,
            "last_failure_code": "CONTROLPROOF_INJECTED_BEFORE_DURABLE",
            "message_body_digest": "d" * 64,
            "observed_at": FIXED_AT,
        },
        updates,
    )


def reporting_effect(**updates: Any) -> BusinessEffectSnapshot:
    return _effect(
        EffectGroup.REPORTING,
        {
            "logical_report_ids": ["report-01"],
            "projection_document_ids": ["projection-01"],
            "projection_report_ids": ["report-01"],
            "processed_keys": [
                {
                    "consumer_name": "reporting-worker",
                    "event_id": str(EVENT_ID),
                    "event_version": 1,
                }
            ],
            "source_outbox_event_ids": [str(EVENT_ID)],
        },
        updates,
    )


def decision_effect(**updates: Any) -> BusinessEffectSnapshot:
    return _effect(
        EffectGroup.DECISION,
        {
            "stage_assignment_ids": ["assignment-01"],
            "invitation_status": "reviewed",
            "human_review_ids": ["review-01"],
            "human_review_actor_types": ["COMPANY_USER"],
            "final_decision_audit_ids": ["audit-01"],
        },
        updates,
    )


def _effect(
    group: EffectGroup, effects: dict[str, Any], updates: dict[str, Any]
) -> BusinessEffectSnapshot:
    return _build(
        BusinessEffectSnapshot,
        {
            "run_id": RUN_ID,
            "subject_ref": "candidate-01",
            "phase": Phase.RECOVERED,
            "step_id": "state.effects.read",
            "attempt": 1,
            "logical_operation_id": OPERATION_ID,
            "source_event_id": EVENT_ID,
            "effect_group": group,
            "effects": effects,
            "state_digest": "e" * 64,
            "captured_at": FIXED_AT,
            "source_status": Presence.PRESENT,
        },
        updates,
    )


def redrive_receipt(**updates: Any) -> RedriveReceipt:
    return _build(
        RedriveReceipt,
        {
            "source_event_id": EVENT_ID,
            "dlq_message_id": "dlq-message-01",
            "republished_message_id": "source-message-02",
            "body_digest": "d" * 64,
            "send_succeeded": True,
            "delete_succeeded": True,
            "redriven_at": FIXED_AT,
        },
        updates,
    )
