from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, UUID, uuid5

from engine.adapters.base import AdapterResult, AdapterSet, CapabilityProbeResult
from engine.adapters.whyyou.capability import CAPABILITY_VERSIONS
from engine.models import (
    DecisionPathCapability,
    DecisionPathId,
    FaultVariant,
    Phase,
    Presence,
    ReadinessStatus,
    TargetSnapshot,
    TargetSourceKind,
)
from tests.fixtures.spec002 import (
    EVENT_ID,
    RUN_ID,
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
                "company_id": "00000000-0000-7000-8000-000000000010",
                "company_user_id": "00000000-0000-7000-8000-000000000011",
                "position_id": "00000000-0000-7000-8000-000000000012",
                "invitation_id": "00000000-0000-0000-0000-000000000001",
                "interview_session_id": "00000000-0000-0000-0000-000000000002",
                "target_stage_id": "00000000-0000-7000-8000-000000000201",
                "final_accept_stage_id": "00000000-0000-7000-8000-000000000201",
                "final_reject_stage_id": "00000000-0000-7000-8000-000000000202",
                "pipeline_row_version": 1,
            },
        )

    def trigger(self, *, run_id, subject):
        return AdapterResult(
            True,
            "REPORTING_TRIGGERED",
            {"outbox_event_id": str(EVENT_ID)},
        )

    def teardown(self, *, run_id, subject):
        return AdapterResult(True, "TEARDOWN_COMPLETE")


class FakeState:
    def __init__(
        self,
        *,
        reason_present=True,
        decision_accepted=False,
        mutate=False,
        report_api_status="queued",
    ):
        self.reason_present = reason_present
        self.decision_accepted = decision_accepted
        self.mutate = mutate
        self.report_api_status = report_api_status
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
            {
                "presence": "ABSENT",
                "status": self.report_api_status,
                "exchange": {"status": 202},
            },
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
        events=None,
    ):
        self.effect = effect if before_effect is None else before_effect
        self.after_effect = after_effect
        self.duplicate_ack = duplicate_ack
        self.restore_ok = restore
        self.processing = processing
        self.events = events if events is not None else []

    def apply(self, *, run_id, subject, expires_at):
        self.events.append("fault.apply")
        return AdapterResult(True, "FAULT_MARKER_APPLIED", {"run_id": run_id})

    def apply_after(self, *, run_id, subject, expires_at):
        self.events.append("fault.apply_after")
        return AdapterResult(True, "AFTER_FAULT_MARKER_APPLIED", {"run_id": run_id})

    def probe_effect(self, *, run_id, subject, trigger):
        return AdapterResult(
            self.effect,
            "FAULT_EFFECT_CONFIRMED" if self.effect else "TRIGGER_RECEIPT_MISSING",
            {"run_id": run_id, "outbox_event_id": trigger["outbox_event_id"]},
        )

    def restore(self, *, run_id, subject):
        self.events.append("fault.restore")
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
        receipt = {
            "outbox_event_id": str(EVENT_ID),
            "delivery_attempt": 2,
            "consumer_name": "reporting-worker",
            "handler_skipped": True,
            "acknowledged": True,
        }
        return AdapterResult(
            self.duplicate_ack,
            "DUPLICATE_ACK_READ" if self.duplicate_ack else "DUPLICATE_ACK_MISSING",
            {"receipt": receipt} if self.duplicate_ack else {},
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
        dlq_presence=None,
        events=None,
    ):
        self.attempts_ok = attempts_ok
        self.dlq_ok = dlq_ok
        self.redrive_send = redrive_send
        self.redrive_delete = redrive_delete
        self.dlq_presence = dlq_presence
        self.events = events if events is not None else []

    def capture_topology(self):
        return queue_topology()

    def read_attempts(self, *, source_event_id, run_id=None):
        records = [delivery_attempt(delivery_attempt=index) for index in range(1, 4)]
        return AdapterResult(
            self.attempts_ok,
            "ATTEMPTS_READ" if self.attempts_ok else "ATTEMPTS_UNAVAILABLE",
            {
                "source_event_id": source_event_id,
                "records": records if self.attempts_ok else [],
            },
        )

    def read_dlq(self, *, source_event_id, subject_ref=None, session_id=None):
        presence = self.dlq_presence
        if presence is None:
            presence = Presence.PRESENT if self.dlq_ok else Presence.UNAVAILABLE
        else:
            presence = Presence(presence)
        return AdapterResult(
            presence is not Presence.UNAVAILABLE,
            "DLQ_MATCH_READ" if presence is not Presence.UNAVAILABLE else "DLQ_UNAVAILABLE",
            {
                "source_event_id": source_event_id,
                "presence": presence,
                "terminal_failure": terminal_failure() if presence is Presence.PRESENT else None,
            },
        )

    def redrive(self, *, source_event_id):
        self.events.append("queue.redrive")
        return redrive_receipt(
            source_event_id=source_event_id,
            send_succeeded=self.redrive_send,
            delete_succeeded=self.redrive_delete if self.redrive_send else False,
            republished_message_id="source-message-02" if self.redrive_send else None,
        )


class FakeDecision:
    def __init__(self, *, accepted=False, accepted_paths=None, partial_write=False):
        self.accepted = accepted
        self.accepted_paths = set(accepted_paths or ())
        self.partial_write = partial_write
        self.reset_calls = []

    def capabilities(self, *, subject=None):
        del subject
        accept = UUID("00000000-0000-7000-8000-000000000201")
        reject = UUID("00000000-0000-7000-8000-000000000202")
        commit = "b" * 40
        return (
            DecisionPathCapability(
                path_id=DecisionPathId.FINAL_DECISION,
                operation_id="recordHumanFinalDecision",
                target_stage_id=accept,
                target_stage_name="최종합격",
                source_commit=commit,
            ),
            DecisionPathCapability(
                path_id=DecisionPathId.BATCH_MOVE_FINAL_ACCEPT,
                operation_id="moveApplicantsToRecruitingStage",
                target_stage_id=accept,
                target_stage_name="최종합격",
                source_commit=commit,
            ),
            DecisionPathCapability(
                path_id=DecisionPathId.BATCH_MOVE_FINAL_REJECT,
                operation_id="moveApplicantsToRecruitingStage",
                target_stage_id=reject,
                target_stage_name="불합격",
                source_commit=commit,
            ),
        )

    def attempt(self, *, path_id, subject, idempotency_key=None):
        active_path = DecisionPathId(path_id)
        accepted = self.accepted or active_path in self.accepted_paths
        capability = next(
            item for item in self.capabilities(subject=subject) if item.path_id is active_path
        )
        key_digest = hashlib.sha256(str(idempotency_key).encode()).hexdigest()
        body_digest = hashlib.sha256(
            f"{subject['invitation_id']}:{capability.target_stage_id}:1".encode()
        ).hexdigest()
        return AdapterResult(
            True,
            "DECISION_ATTEMPTED",
            {
                "path_id": active_path,
                "subject_ref": subject.get("subject_ref", "candidate-01"),
                "accepted": accepted,
                "reason_present": not accepted,
                "reason_code": None if accepted else "REPORT_NOT_AVAILABLE",
                "partial_write": self.partial_write,
                "target_stage_id": capability.target_stage_id,
                "logical_decision_id": uuid5(
                    NAMESPACE_URL,
                    f"{key_digest}:{body_digest}:{capability.target_stage_id}",
                ),
                "idempotency_key_digest": key_digest,
                "request_body_digest": body_digest,
                "response_digest": "e" * 64,
                "target_idempotency_confirmed": False,
            },
        )

    def capture_reset_token(self, *, subject):
        return AdapterResult(
            True,
            "DECISION_RESET_SNAPSHOT_CAPTURED",
            {
                "invitation_status": "completed",
                "recruiting_stage_id": subject["target_stage_id"],
                "pipeline_row_version": subject["pipeline_row_version"],
                "human_review_ids": (),
                "audit_event_ids": (),
            },
        )

    def reset(self, *, subject, token):
        self.reset_calls.append((subject["subject_ref"], token["pipeline_row_version"]))
        return AdapterResult(True, "DECISION_STATE_RESET")


class FakeEffects:
    def __init__(
        self,
        *,
        reporting_available=True,
        decision_available=True,
        injected_reporting_present=False,
    ):
        self.reporting_available = reporting_available
        self.decision_available = decision_available
        self.injected_reporting_present = injected_reporting_present

    def read_reporting_effects(
        self,
        *,
        subject,
        phase,
        run_id=RUN_ID,
        logical_operation_id=None,
        source_event_id=EVENT_ID,
        step_id="state.effects.read",
        attempt=1,
    ):
        if not self.reporting_available:
            return (
                reporting_effect(
                    run_id=run_id,
                    phase=Phase(phase),
                    subject_ref=subject.get("subject_ref", "candidate-01"),
                    logical_operation_id=logical_operation_id or UUID(int=1),
                    source_event_id=source_event_id,
                    step_id=step_id,
                    attempt=attempt,
                    effects={},
                    source_status="UNAVAILABLE",
                    source_error_code="REPORTING_EFFECTS_UNAVAILABLE",
                ),
            )
        if Phase(phase) is Phase.INJECTED and not self.injected_reporting_present:
            return (
                reporting_effect(
                    run_id=run_id,
                    phase=Phase.INJECTED,
                    subject_ref=subject.get("subject_ref", "candidate-01"),
                    logical_operation_id=logical_operation_id or UUID(int=1),
                    source_event_id=source_event_id,
                    step_id=step_id,
                    attempt=attempt,
                    effects={
                        "logical_report_ids": [],
                        "projection_document_ids": [],
                        "projection_report_ids": [],
                        "processed_keys": [],
                        "source_outbox_event_ids": [str(source_event_id)],
                    },
                ),
            )
        return (
            reporting_effect(
                run_id=run_id,
                phase=Phase(phase),
                subject_ref=subject.get("subject_ref", "candidate-01"),
                logical_operation_id=logical_operation_id or UUID(int=1),
                source_event_id=source_event_id,
                step_id=step_id,
                attempt=attempt,
            ),
        )

    def read_decision_effects(
        self,
        *,
        subject,
        phase,
        run_id=RUN_ID,
        logical_operation_id=None,
        source_event_id=EVENT_ID,
        step_id="state.effects.read",
        attempt=1,
    ):
        if not self.decision_available:
            return (
                decision_effect(
                    run_id=run_id,
                    phase=Phase(phase),
                    subject_ref=subject.get("subject_ref", "candidate-01"),
                    logical_operation_id=logical_operation_id or UUID(int=1),
                    source_event_id=source_event_id,
                    step_id=step_id,
                    attempt=attempt,
                    effects={},
                    source_status="UNAVAILABLE",
                    source_error_code="DECISION_EFFECTS_UNAVAILABLE",
                ),
            )
        return (
            decision_effect(
                run_id=run_id,
                phase=Phase(phase),
                subject_ref=subject.get("subject_ref", "candidate-01"),
                logical_operation_id=logical_operation_id or UUID(int=1),
                source_event_id=source_event_id,
                step_id=step_id,
                attempt=attempt,
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
                    "terminal_status_class": (
                        "final_failed" if self.status_class == "failed" else self.status_class
                    ),
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
    report_api_status="queued",
    effect=True,
    before_effect=None,
    after_effect=True,
    duplicate_ack=True,
    restore=True,
    processing="READY",
    attempts_ok=True,
    dlq_ok=True,
    dlq_presence=None,
    redrive_send=True,
    redrive_delete=True,
    decision_path_accepted=False,
    accepted_decision_paths=None,
    decision_partial_write=False,
    reporting_effects_available=True,
    injected_reporting_present=False,
    decision_effects_available=True,
    target_exists=True,
    readiness_overrides=None,
):
    lifecycle_events = []
    target = FakeTarget(target_exists=target_exists, overrides=readiness_overrides)
    browser = FakeBrowser(status_class=status_class)
    fault = FakeFault(
        effect=effect,
        before_effect=before_effect,
        after_effect=after_effect,
        duplicate_ack=duplicate_ack,
        restore=restore,
        processing=processing,
        events=lifecycle_events,
    )
    queue = FakeQueue(
        attempts_ok=attempts_ok,
        dlq_ok=dlq_ok,
        dlq_presence=dlq_presence,
        redrive_send=redrive_send,
        redrive_delete=redrive_delete,
        events=lifecycle_events,
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
                report_api_status=report_api_status,
            ),
            fault=fault,
            browser=browser,
            environment=FakeEnvironment(),
            queue=queue,
            decision=FakeDecision(
                accepted=decision_path_accepted,
                accepted_paths=accepted_decision_paths,
                partial_write=decision_partial_write,
            ),
            effects=FakeEffects(
                reporting_available=reporting_effects_available,
                decision_available=decision_effects_available,
                injected_reporting_present=injected_reporting_present,
            ),
            boundary_receipts=fault,
            duplicate_acks=fault,
            safe_redrive=queue,
        ),
        browser,
    )
