from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

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
    Presence,
    QueueTopologySnapshot,
    TargetEnvironmentSnapshot,
)


def test_environment_snapshot_is_local_deterministic_and_self_digesting():
    snapshot = TargetEnvironmentSnapshot(
        target_id="whyyou-local",
        environment_kind=EnvironmentKind.LOCAL_EMULATED,
        host_os="windows-11",
        controlproof_commit=GitIdentity(commit_sha="a" * 40, dirty=False),
        whyyou_commit=GitIdentity(commit_sha="b" * 40, dirty=False),
        components={"postgresql": "16", "localstack": "3.8"},
        endpoints={"api": "http://localhost:8080", "sqs": "http://localhost:4566"},
        model_fixture_id="h03-report-v1",
        model_fixture_digest="c" * 64,
        external_ai_allowed=False,
        aws_deployment_status=AwsDeploymentStatus.NOT_RUN,
        unverified_scope=("AWS_SQS", "AWS_ECS", "AWS_IAM", "AWS_CLOUDWATCH", "AWS_NETWORK"),
        captured_at=datetime(2026, 9, 28, tzinfo=UTC),
    )
    assert len(snapshot.snapshot_digest) == 64
    assert snapshot.environment_kind is EnvironmentKind.LOCAL_EMULATED


def test_environment_snapshot_rejects_external_ai_and_non_loopback_endpoint():
    common = {
        "target_id": "whyyou-local",
        "environment_kind": "LOCAL_EMULATED",
        "host_os": "windows-11",
        "controlproof_commit": {"commit_sha": "a" * 40, "dirty": False},
        "whyyou_commit": {"commit_sha": "b" * 40, "dirty": False},
        "components": {"localstack": "3.8"},
        "model_fixture_id": "fixture",
        "model_fixture_digest": "c" * 64,
        "aws_deployment_status": "NOT_RUN",
        "unverified_scope": ["AWS_SQS", "AWS_ECS", "AWS_IAM", "AWS_CLOUDWATCH", "AWS_NETWORK"],
    }
    with pytest.raises(ValidationError):
        TargetEnvironmentSnapshot(**common, endpoints={"api": "https://example.com"}, external_ai_allowed=False)
    with pytest.raises(ValidationError):
        TargetEnvironmentSnapshot(**common, endpoints={"api": "http://localhost:8080"}, external_ai_allowed=True)


def test_queue_topology_enforces_demo_contract_and_digest():
    snapshot = QueueTopologySnapshot(
        source_queue_name="iep-reporting",
        source_queue_url_digest="a" * 64,
        dead_letter_queue_name="iep-reporting-dlq",
        dead_letter_queue_arn="arn:aws:sqs:ap-northeast-2:000000000000:iep-reporting-dlq",
        max_receive_count=3,
        visibility_timeout_seconds=5,
        source_retention_seconds=3600,
        dlq_retention_seconds=7200,
        redrive_policy_digest="b" * 64,
        captured_at=datetime(2026, 9, 28, tzinfo=UTC),
    )
    assert len(snapshot.snapshot_digest) == 64
    with pytest.raises(ValidationError):
        snapshot.model_copy(update={"max_receive_count": 4}).__class__.model_validate(
            {**snapshot.model_dump(), "max_receive_count": 4, "snapshot_digest": None}
        )


def test_attempt_boundary_and_effect_records_require_canonical_identity():
    run_id = uuid4()
    event_id = uuid4()
    attempt = DeliveryAttemptRecord(
        run_id=run_id,
        subject_ref="candidate-01",
        source_event_id=event_id,
        consumer_name="reporting-worker",
        delivery_attempt=1,
        fault_variant=FaultVariant.BEFORE_RESULT_DURABLE,
        outcome=DeliveryAttemptOutcome.FAULT_TRIGGERED,
        observed_at=datetime(2026, 9, 28, tzinfo=UTC),
        receipt_artifact_id=uuid4(),
    )
    receipt = FaultBoundaryReceipt(
        run_id=run_id,
        session_id=uuid4(),
        outbox_event_id=event_id,
        delivery_attempt=1,
        fault_variant=FaultVariant.BEFORE_RESULT_DURABLE,
        boundary=FaultBoundary.BEFORE_REPORT_SIDE_EFFECT,
        triggered_at=datetime(2026, 9, 28, tzinfo=UTC),
        one_shot_consumed=False,
    )
    effect = BusinessEffectSnapshot(
        run_id=run_id,
        subject_ref="candidate-01",
        phase="INJECTED",
        step_id="state.effects.read",
        attempt=1,
        logical_operation_id=uuid4(),
        source_event_id=event_id,
        effect_group=EffectGroup.REPORTING,
        effects={"report_ids": []},
        state_digest="d" * 64,
        source_status=Presence.ABSENT,
        captured_at=datetime(2026, 9, 28, tzinfo=UTC),
    )
    assert attempt.fault_variant is FaultVariant.BEFORE_RESULT_DURABLE
    assert receipt.boundary is FaultBoundary.BEFORE_REPORT_SIDE_EFFECT
    assert effect.source_error_code is None
