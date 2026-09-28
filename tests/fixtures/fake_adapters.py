from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from engine.adapters.base import AdapterResult, AdapterSet, CapabilityProbeResult
from engine.adapters.whyyou.capability import CAPABILITY_VERSIONS
from engine.models import (
    DecisionPathCapability,
    DecisionPathId,
    FaultVariant,
    Phase,
    ReadinessStatus,
    TargetSnapshot,
    TargetSourceKind,
)
from tests.fixtures.spec002 import (
    boundary_receipt,
    decision_effect,
    delivery_attempt,
    environment_snapshot,
    queue_topology,
    redrive_receipt,
    reporting_effect,
    terminal_failure,
)


class FakeClock:
    def __init__(self) -> None:
        self.current = datetime(2026, 9, 24, tzinfo=UTC)

    def now(self):
        return self.current

    def sleep(self, seconds: float) -> None:
        self.current += timedelta(seconds=seconds)


class FakeTarget:
    def __init__(self, *, target_exists=True, overrides=None):
        self.target_exists = target_exists
        self.overrides = overrides or {}
        self.snapshot = TargetSnapshot(
            target_id="whyyou-local",
            source_kind=TargetSourceKind.GIT_WORKTREE,
            git_commit_sha="a" * 40,
            git_dirty=False,
            openapi_digest="b" * 64,
            schema_migration_head="head-v1",
            schema_signature_digest="c" * 64,
            model_fixture_id="h03-report-v1",
            model_fixture_digest="ce09b95403b34e1390502c90f5c5edc518ddf65d38c8ce881617a37cac6d16b1",
        )

    @property
    def registrations(self):
        return CAPABILITY_VERSIONS

    def capture_target_snapshot(self):
        return self.snapshot

    def target_feature_exists(self):
        return self.target_exists

    def probe(self, capability):
        status = self.overrides.get(capability, ReadinessStatus.READY)
        return CapabilityProbeResult(
            capability,
            status,
            "fixture probe",
            None if status is ReadinessStatus.READY else "repair fixture capability",
        )


class FakeSeed:
    def seed(self, *, run_id, subject_ref):
        return AdapterResult(
            True,
            "SUBJECT_SEEDED",
            {
                "subject_ref": subject_ref,
                "synthetic": True,
                "seed_correlation_id": f"cp-{run_id}",
                "invitation_id": "00000000-0000-0000-0000-000000000001",
                "interview_session_id": "00000000-0000-0000-0000-000000000002",
                "target_stage_id": "00000000-0000-0000-0000-000000000003",
                "pipeline_row_version": 1,
            },
        )

    def trigger(self, *, run_id, subject):
        return AdapterResult(
            True,
            "REPORTING_TRIGGERED",
            {"outbox_event_id": "00000000-0000-0000-0000-000000000004"},
        )

    def teardown(self, *, run_id, subject):
        return AdapterResult(True, "TEARDOWN_COMPLETE")


class FakeState:
    def __init__(self, *, reason_present=True, decision_accepted=False, mutate=False):
        self.reason_present = reason_present
        self.decision_accepted = decision_accepted
        self.mutate = mutate
        self.calls = 0

    def _state(self):
        self.calls += 1
        return {
            "invitation_status": "reviewed" if self.mutate and self.calls > 1 else "completed",
            "recruiting_stage_id": "stage-2" if self.mutate and self.calls > 1 else "stage-1",
            "pipeline_row_version": 2 if self.mutate and self.calls > 1 else 1,
            "final_decision_count": 1 if self.mutate and self.calls > 1 else 0,
            "latest_final_decision_actor_type": "SYSTEM"
            if self.mutate and self.calls > 1
            else None,
            "report_presence": "ABSENT",
            "report_status": None,
        }

    def snapshot(self, *, subject, phase):
        return AdapterResult(True, "STATE_CAPTURED", {"state": self._state(), "phase": phase})

    def report_status(self, *, subject):
        return AdapterResult(
            True,
            "REPORT_STATUS",
            {"presence": "ABSENT", "status": "queued", "exchange": {"status": 202}},
        )

    def attempt_final_decision(self, *, subject):
        return AdapterResult(
            True,
            "DECISION_ATTEMPTED",
            {
                "accepted": self.decision_accepted,
                "reason_present": self.reason_present,
                "reason_code": "REPORT_NOT_AVAILABLE" if self.reason_present else None,
                "exchange": {"status": 409 if self.reason_present else 404},
            },
        )


class FakeFault:
    def __init__(
        self,
        *,
        effect=True,
        before_effect=None,
        after_effect=True,
        duplicate_ack=True,
        restore=True,
        processing="READY",
    ):
        self.effect = effect if before_effect is None else before_effect
        self.after_effect = after_effect
        self.duplicate_ack = duplicate_ack
        self.restore_ok = restore
        self.processing = processing

    def apply(self, *, run_id, subject, expires_at):
        return AdapterResult(True, "FAULT_MARKER_APPLIED", {"run_id": run_id})

    def probe_effect(self, *, run_id, subject, trigger):
        return AdapterResult(
            self.effect,
            "FAULT_EFFECT_CONFIRMED" if self.effect else "TRIGGER_RECEIPT_MISSING",
            {"run_id": run_id, "outbox_event_id": trigger["outbox_event_id"]},
        )

    def restore(self, *, run_id, subject):
        return AdapterResult(
            self.restore_ok,
            "ENVIRONMENT_RESTORED" if self.restore_ok else "ENVIRONMENT_RESTORE_FAILED",
            {
                "environment_restore": "SUCCEEDED" if self.restore_ok else "FAILED",
                "report_processing_recovery": self.processing,
                "marker_inactive": self.restore_ok,
                "worker_healthy": self.restore_ok,
            },
        )

    def target_safe(self, *, subject_ref):
        return self.restore_ok

    def read_boundary_receipt(self, *, fault_variant, **_kwargs):
        variant = FaultVariant(fault_variant)
        observed = (
            self.effect
            if variant is FaultVariant.BEFORE_RESULT_DURABLE
            else self.after_effect
        )
        if not observed:
            return AdapterResult(False, "BOUNDARY_RECEIPT_MISSING")
        if variant is FaultVariant.AFTER_RESULT_DURABLE_BEFORE_COMPLETION:
            receipt = boundary_receipt(
                fault_variant=variant,
                boundary="AFTER_DB_COMMIT_BEFORE_SQS_ACK",
                one_shot_consumed=True,
            )
        else:
            receipt = boundary_receipt()
        return AdapterResult(True, "BOUNDARY_RECEIPT_READ", {"receipt": receipt})

    def read_duplicate_ack(self, **_kwargs):
        return AdapterResult(
            self.duplicate_ack,
            "DUPLICATE_ACK_READ" if self.duplicate_ack else "DUPLICATE_ACK_MISSING",
        )


class FakeEnvironment:
    def capture_environment(self):
        return environment_snapshot()


class FakeQueue:
    def __init__(
        self,
        *,
        attempts_ok=True,
        dlq_ok=True,
        redrive_send=True,
        redrive_delete=True,
    ):
        self.attempts_ok = attempts_ok
        self.dlq_ok = dlq_ok
        self.redrive_send = redrive_send
        self.redrive_delete = redrive_delete

    def capture_topology(self):
        return queue_topology()

    def read_attempts(self, *, source_event_id):
        records = [delivery_attempt(delivery_attempt=index) for index in range(1, 4)]
        return AdapterResult(
            self.attempts_ok,
            "ATTEMPTS_READ" if self.attempts_ok else "ATTEMPTS_UNAVAILABLE",
            {
                "source_event_id": source_event_id,
                "records": records if self.attempts_ok else [],
            },
        )

    def read_dlq(self, *, source_event_id):
        return AdapterResult(
            self.dlq_ok,
            "DLQ_MATCH_READ" if self.dlq_ok else "DLQ_UNAVAILABLE",
            {
                "source_event_id": source_event_id,
                "terminal_failure": terminal_failure() if self.dlq_ok else None,
            },
        )

    def redrive(self, *, source_event_id):
        return redrive_receipt(
            source_event_id=source_event_id,
            send_succeeded=self.redrive_send,
            delete_succeeded=self.redrive_delete if self.redrive_send else False,
            republished_message_id="source-message-02" if self.redrive_send else None,
        )


class FakeDecision:
    def __init__(self, *, accepted=False, partial_write=False):
        self.accepted = accepted
        self.partial_write = partial_write

    def capabilities(self):
        stage = UUID("00000000-0000-7000-8000-000000000201")
        commit = "b" * 40
        return (
            DecisionPathCapability(
                path_id=DecisionPathId.FINAL_DECISION,
                operation_id="createFinalDecision",
                target_stage_id=stage,
                target_stage_name="최종합격",
                source_commit=commit,
            ),
            DecisionPathCapability(
                path_id=DecisionPathId.BATCH_MOVE_FINAL_ACCEPT,
                operation_id="batchMoveInvitations",
                target_stage_id=stage,
                target_stage_name="최종합격",
                source_commit=commit,
            ),
            DecisionPathCapability(
                path_id=DecisionPathId.BATCH_MOVE_FINAL_REJECT,
                operation_id="batchMoveInvitations",
                target_stage_id=stage,
                target_stage_name="불합격",
                source_commit=commit,
            ),
        )

    def attempt(self, *, path_id, subject, idempotency_key=None):
        return AdapterResult(
            True,
            "DECISION_ATTEMPTED",
            {
                "path_id": path_id,
                "subject_ref": subject.get("subject_ref", "candidate-01"),
                "accepted": self.accepted,
                "partial_write": self.partial_write,
                "idempotency_key_digest": "f" * 64 if idempotency_key else None,
            },
        )


class FakeEffects:
    def __init__(self, *, reporting_available=True, decision_available=True):
        self.reporting_available = reporting_available
        self.decision_available = decision_available

    def read_reporting_effects(self, *, subject, phase):
        if not self.reporting_available:
            return (
                reporting_effect(
                    phase=Phase(phase),
                    subject_ref=subject.get("subject_ref", "candidate-01"),
                    effects={},
                    source_status="UNAVAILABLE",
                    source_error_code="REPORTING_EFFECTS_UNAVAILABLE",
                ),
            )
        return (
            reporting_effect(
                phase=Phase(phase),
                subject_ref=subject.get("subject_ref", "candidate-01"),
            ),
        )

    def read_decision_effects(self, *, subject, phase):
        if not self.decision_available:
            return (
                decision_effect(
                    phase=Phase(phase),
                    subject_ref=subject.get("subject_ref", "candidate-01"),
                    effects={},
                    source_status="UNAVAILABLE",
                    source_error_code="DECISION_EFFECTS_UNAVAILABLE",
                ),
            )
        return (
            decision_effect(
                phase=Phase(phase),
                subject_ref=subject.get("subject_ref", "candidate-01"),
            ),
        )


class FakeBrowser:
    def __init__(self, status_class="failed"):
        self.status_class = status_class
        self.closed = False

    def capture_review(self, *, subject):
        return AdapterResult(
            True,
            "BROWSER_CAPTURED",
            {
                "projection": {
                    "route": "/review/{session_id}",
                    "visible_text": "리포트 생성 실패",
                    "ready_content_visible": False,
                    "decision_control_visible": True,
                    "status_class": self.status_class,
                    "viewport": {"width": 1440, "height": 900},
                },
                "screenshot_bytes": b"synthetic-png",
            },
        )

    def close(self):
        self.closed = True


def make_adapters(
    *,
    status_class="failed",
    reason_present=True,
    decision_accepted=False,
    mutate=False,
    effect=True,
    before_effect=None,
    after_effect=True,
    duplicate_ack=True,
    restore=True,
    processing="READY",
    attempts_ok=True,
    dlq_ok=True,
    redrive_send=True,
    redrive_delete=True,
    decision_path_accepted=False,
    decision_partial_write=False,
    reporting_effects_available=True,
    decision_effects_available=True,
    target_exists=True,
    readiness_overrides=None,
):
    target = FakeTarget(target_exists=target_exists, overrides=readiness_overrides)
    browser = FakeBrowser(status_class=status_class)
    fault = FakeFault(
        effect=effect,
        before_effect=before_effect,
        after_effect=after_effect,
        duplicate_ack=duplicate_ack,
        restore=restore,
        processing=processing,
    )
    queue = FakeQueue(
        attempts_ok=attempts_ok,
        dlq_ok=dlq_ok,
        redrive_send=redrive_send,
        redrive_delete=redrive_delete,
    )
    return (
        AdapterSet(
            target=target,
            capability=target,
            seed=FakeSeed(),
            state=FakeState(
                reason_present=reason_present,
                decision_accepted=decision_accepted,
                mutate=mutate,
            ),
            fault=fault,
            browser=browser,
            environment=FakeEnvironment(),
            queue=queue,
            decision=FakeDecision(
                accepted=decision_path_accepted,
                partial_write=decision_partial_write,
            ),
            effects=FakeEffects(
                reporting_available=reporting_effects_available,
                decision_available=decision_effects_available,
            ),
            boundary_receipts=fault,
            duplicate_acks=fault,
            safe_redrive=queue,
        ),
        browser,
    )
