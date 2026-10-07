from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from engine.adapters.base import AdapterResult, AdapterSet, CapabilityProbeResult
from engine.adapters.whyyou.capability import CAPABILITY_VERSIONS
from engine.adapters.whyyou.causality import WhyYouCausalityAdapter
from engine.models import (
    BaselineKind,
    CausalEdge,
    CausalEdgeStatus,
    CausalEvent,
    CausalEventKind,
    CausalRelation,
    ConsentFaultBoundary,
    ConsentFaultReceipt,
    ConsentFaultVariant,
    ConsentPolicySnapshot,
    ConsentPurpose,
    ConsentStateSnapshot,
    DecisionPathCapability,
    DecisionPathId,
    FaultVariant,
    N02EffectGroup,
    N02LaneId,
    Phase,
    Presence,
    ProcessingAttemptReceipt,
    ProcessingEntryKind,
    ProcessingResponseClass,
    ProtectedEffectSnapshot,
    ProtectedPathId,
    ProtectedProcessingPath,
    ReadinessStatus,
    RunSubjectLane,
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


class FakeN02Adapters:
    """Deterministic N-02 capability set with independently selectable outcomes."""

    def __init__(
        self,
        *,
        responses: dict[ProtectedPathId, ProcessingResponseClass] | None = None,
        new_effects: dict[ProtectedPathId, tuple[str, ...]] | None = None,
        unavailable_paths: frozenset[ProtectedPathId] = frozenset(),
        causal_available: bool = True,
        fault_triggered: bool = True,
        restore_succeeded: bool = True,
        consent_timeout: bool = False,
        timeout_state_known: bool = True,
        state_unavailable: bool = False,
        policy_mismatch: bool = False,
        blocked_paths: frozenset[ProtectedPathId] = frozenset(),
        causal_missing_path: ProtectedPathId | None = None,
        causal_conflict: bool = False,
    ) -> None:
        self.prerequisite_calls: list[tuple[str, str, str | None]] = []
        self.responses = responses or {
            path: ProcessingResponseClass.DENIED for path in ProtectedPathId
        }
        self.new_effects = new_effects or {path: () for path in ProtectedPathId}
        self.unavailable_paths = unavailable_paths
        self.causal_available = causal_available
        self.fault_triggered = fault_triggered
        self.restore_succeeded = restore_succeeded
        self.consent_timeout = consent_timeout
        self.timeout_state_known = timeout_state_known
        self.state_unavailable = state_unavailable
        self.policy_mismatch = policy_mismatch
        self.blocked_paths = blocked_paths
        self.causal_missing_path = causal_missing_path
        self.causal_conflict = causal_conflict
        self.now = datetime(2026, 10, 1, tzinfo=UTC)
        self._committed_subjects: set[str] = set()
        self._causality = WhyYouCausalityAdapter()
        self.attempted_paths: list[ProtectedPathId] = []
        self._fault_active = False
        self._fault_was_triggered = False
        self._fault_request_id: str | None = None
        self._overlay_paths: set[ProtectedPathId] = set()

    def seed_lanes(self, *, run_id: str):
        active_run = UUID(run_id)
        lanes = []
        for lane in N02LaneId:
            fixture = lane in {
                N02LaneId.RECORDING_BOUNDARY_PROBE,
                N02LaneId.ASSESSMENT_BOUNDARY_PROBE,
            }
            path = {
                N02LaneId.RECORDING_BOUNDARY_PROBE: N02EffectGroup.RECORDING,
                N02LaneId.ASSESSMENT_BOUNDARY_PROBE: N02EffectGroup.AI_ASSESSMENT,
                N02LaneId.DOCUMENT_BYPASS: N02EffectGroup.DOCUMENT_ANALYSIS,
            }.get(lane, N02EffectGroup.DOCUMENT_ANALYSIS)
            lanes.append(
                RunSubjectLane(
                    run_id=active_run,
                    lane_id=lane,
                    subject_ref=f"synthetic-{lane.value.casefold()}",
                    invitation_id=uuid5(active_run, f"invitation:{lane.value}"),
                    applicant_id=uuid5(active_run, f"applicant:{lane.value}"),
                    baseline_kind=(
                        BaselineKind.PREREQUISITE_FIXTURE if fixture else BaselineKind.PRISTINE
                    ),
                    fixture_kind=f"{lane.value.casefold()}-v1" if fixture else None,
                    fixture_digest="a" * 64 if fixture else None,
                    allowed_preexisting_effects={"fixture": 1} if fixture else {},
                    target_effect_groups=(path,),
                    trace_namespace=f"controlproof:{active_run}:{lane.value}",
                    seed_correlation_id=f"seed-{lane.value.casefold()}",
                )
            )
        return tuple(lanes)

    def teardown_lanes(self, *, run_id: str, lanes):
        return AdapterResult(True, "N02_LANES_REMOVED", {"count": len(lanes)})

    def target_session_for(self, *, subject):
        return AdapterResult(True, "N02_TARGET_SESSION_READ", {"interview_session_id": None})

    def apply_processing_prerequisites(self, *, subject, path_id: str, interview_session_id=None):
        self.prerequisite_calls.append((str(subject["lane_id"]), path_id, interview_session_id))
        return AdapterResult(True, "N02_PREREQUISITES_APPLIED", {"fixture_effect_ids": ()})

    def apply_probe_overlay(self, *, subject, path_id: str):
        path = ProtectedPathId(path_id)
        self._overlay_paths.add(path)
        return AdapterResult(True, "N02_OVERLAY_APPLIED", {"path_id": path_id})

    def remove_probe_overlay(self, *, subject, path_id: str):
        path = ProtectedPathId(path_id)
        self._overlay_paths.discard(path)
        return AdapterResult(
            True,
            "N02_OVERLAY_REMOVED",
            {"path_id": path_id, "remaining_overlay_count": len(self._overlay_paths)},
        )

    def paths(self):
        values = []
        for path in ProtectedPathId:
            deep = path is not ProtectedPathId.DOCUMENT_ANALYSIS
            values.append(
                ProtectedProcessingPath(
                    path_id=path,
                    entry_boundary={
                        ProtectedPathId.DOCUMENT_ANALYSIS: "createSubmissionUploadIntent",
                        ProtectedPathId.RECORDING: "createInterviewSession",
                        ProtectedPathId.AI_ASSESSMENT: "report.generation_requested",
                    }[path],
                    entry_kind=(
                        ProcessingEntryKind.DOMAIN_EVENT
                        if path is ProtectedPathId.AI_ASSESSMENT
                        else ProcessingEntryKind.HTTP
                    ),
                    independent_direct_route=not deep,
                    earliest_real_boundary="worker-or-session-boundary" if deep else None,
                    required_fixture_kind=f"{path.value.casefold()}-fixture-v1" if deep else None,
                    request_effect_keys=("request_id",),
                    start_effect_keys=("receipt_id",),
                    result_effect_keys=("result_id",),
                    consent_purpose=ConsentPurpose(path.value.casefold()),
                    source_locator={"path": "backend/src/interview_evidence", "symbol": path.value},
                )
            )
        return tuple(values)

    def attempt(self, *, path_id: str, subject, drive: bool = False):
        path = ProtectedPathId(path_id)
        self.attempted_paths.append(path)
        normal = (
            N02LaneId(subject["lane_id"]) is N02LaneId.NORMAL_ORDER
            or str(subject["subject_ref"]) in self._committed_subjects
        )
        response = (
            ProcessingResponseClass.DENIED
            if normal and path in self.blocked_paths
            else ProcessingResponseClass.ACCEPTED
            if normal
            else self.responses[path]
        )
        entry = (
            ProcessingEntryKind.DOMAIN_EVENT
            if path is ProtectedPathId.AI_ASSESSMENT
            else ProcessingEntryKind.HTTP
        )
        return ProcessingAttemptReceipt(
            run_id=UUID(str(subject["run_id"])),
            lane_id=N02LaneId(subject["lane_id"]),
            subject_ref=str(subject["subject_ref"]),
            path_id=path,
            entry_kind=entry,
            operation_id=path.value,
            request_id=str(uuid4()),
            trace_id_digest="b" * 64,
            sent_at=self.now,
            response_at=None if response is ProcessingResponseClass.NO_RESPONSE else self.now,
            response_class=response,
            status_code=(
                403
                if entry is ProcessingEntryKind.HTTP
                and response is ProcessingResponseClass.DENIED
                else None
            ),
            sanitized_reason_code="CONSENT_REQUIRED" if response is ProcessingResponseClass.DENIED else None,
            source_ref=f"fixture:{path.value}",
        )

    def read_effects(self, *, path_id: str, subject, phase: str, step_id: str):
        path = ProtectedPathId(path_id)
        unavailable = path in self.unavailable_paths
        is_pristine = N02LaneId(subject["lane_id"]) is N02LaneId.PRISTINE_BASELINE
        is_normal = (
            N02LaneId(subject["lane_id"]) is N02LaneId.NORMAL_ORDER
            or str(subject["subject_ref"]) in self._committed_subjects
        )
        effects = (
            (f"request:{path.value}", f"start:{path.value}", f"result:{path.value}")
            if is_normal and not unavailable and path not in self.blocked_paths
            else self.new_effects[path]
            if not unavailable and not is_pristine
            else ()
        )
        fixtures = tuple(
            sorted(
                {str(value) for value in subject.get("allowed_fixture_effect_ids", ())}
                & set(effects)
            )
        )
        new_effects = tuple(sorted(set(effects) - set(fixtures)))
        return ProtectedEffectSnapshot(
            run_id=UUID(str(subject["run_id"])),
            lane_id=N02LaneId(subject["lane_id"]),
            subject_ref=str(subject["subject_ref"]),
            path_id=path,
            phase=Phase(phase),
            step_id=step_id,
            attempt=1,
            effect_group=N02EffectGroup(path.value),
            request_ids=(f"request:{path.value}",) if is_normal and effects else (),
            start_receipt_ids=(f"start:{path.value}",) if is_normal and effects else (),
            result_ids=(f"result:{path.value}",) if is_normal and effects else (),
            fixture_effect_ids=fixtures,
            current_effect_ids=effects,
            new_effect_ids=new_effects,
            source_status=Presence.UNAVAILABLE if unavailable else (
                Presence.PRESENT if effects else Presence.ABSENT
            ),
            source_error_code="FIXTURE_SOURCE_UNAVAILABLE" if unavailable else None,
            state_digest="c" * 64,
            captured_at=self.now,
        )

    def read_policy(self, *, subject):
        return ConsentPolicySnapshot(
            policy_version="fixture-v1",
            content_digest="d" * 64,
            required_purposes=tuple(ConsentPurpose),
            retention_days=365,
            received_at=self.now,
            request_id=uuid4(),
            source_ref="fixture:policy",
        )

    def commit(self, *, subject, policy, request_id: str, trace_id: str):
        subject_ref = str(subject["subject_ref"])
        if (
            N02LaneId(subject["lane_id"]) is N02LaneId.CONSENT_FAULT_RECOVERY
            and self._fault_active
        ):
            self._fault_was_triggered = self.fault_triggered
            self._fault_request_id = request_id
            return AdapterResult(
                False,
                "CONSENT_COMMIT_REJECTED",
                {
                    "status_code": 500,
                    "durable_state": "NOT_COMMITTED",
                    "request_id": request_id,
                },
            )
        if self.policy_mismatch:
            return AdapterResult(False, "CONSENT_POLICY_MISMATCH")
        if not self.consent_timeout or self.timeout_state_known:
            self._committed_subjects.add(subject_ref)
        if self.consent_timeout:
            return AdapterResult(
                False,
                "CONSENT_COMMIT_RESPONSE_UNKNOWN",
                {"durable_state": "UNKNOWN", "request_id": request_id},
            )
        return AdapterResult(True, "CONSENT_COMMITTED", {"request_id": request_id})

    def read_state(self, *, subject, phase: str, step_id: str):
        if self.state_unavailable or (self.consent_timeout and not self.timeout_state_known):
            return ConsentStateSnapshot(
                run_id=UUID(str(subject["run_id"])),
                lane_id=N02LaneId(subject["lane_id"]),
                subject_ref=str(subject["subject_ref"]),
                phase=Phase(phase),
                step_id=step_id,
                attempt=1,
                invitation_status="unknown",
                invitation_row_version=0,
                captured_at=self.now,
                source_status=Presence.UNAVAILABLE,
                source_error_code="DB_TIMEOUT",
                state_digest="e" * 64,
            )
        committed = str(subject["subject_ref"]) in self._committed_subjects
        consent_id = uuid5(UUID(str(subject["run_id"])), "normal-consent")
        transition_id = uuid5(UUID(str(subject["run_id"])), "normal-transition")
        event_id = uuid5(UUID(str(subject["run_id"])), "normal-event")
        return ConsentStateSnapshot(
            run_id=UUID(str(subject["run_id"])),
            lane_id=N02LaneId(subject["lane_id"]),
            subject_ref=str(subject["subject_ref"]),
            phase=Phase(phase),
            step_id=step_id,
            attempt=1,
            invitation_status="consented" if committed else "identity_verified",
            invitation_row_version=2 if committed else 1,
            consent_record_ids=(consent_id,) if committed else (),
            active_consent_count=1 if committed else 0,
            consent_policy_versions=("fixture-v1",) if committed else (),
            consent_content_digests=("d" * 64,) if committed else (),
            accepted_purpose_sets=(tuple(ConsentPurpose),) if committed else (),
            consented_state_change_ids=(transition_id,) if committed else (),
            consent_completed_event_ids=(event_id,) if committed else (),
            trace_ids=("f" * 64,) if committed else (),
            captured_at=self.now,
            source_status=Presence.PRESENT if committed else Presence.ABSENT,
            state_digest="e" * 64,
        )

    def capture_normal_order(
        self, *, subject, policy, consent_state, attempts, effects, receipts=()
    ):
        result = self._causality.capture_normal_order(
            subject=subject,
            policy=policy,
            consent_state=consent_state,
            attempts=attempts,
            effects=effects,
            receipts=receipts,
        )
        if result.ok:
            graph = self._causality.read_graph(subject=subject)
            if not isinstance(graph, AdapterResult):
                events, edges = graph
                if self.causal_missing_path is not None:
                    path_event_ids = {
                        event.causal_event_id
                        for event in events
                        if event.path_id is self.causal_missing_path
                    }
                    edges = tuple(
                        edge
                        for edge in edges
                        if edge.from_event_id not in path_event_ids
                        and edge.to_event_id not in path_event_ids
                    )
                if self.causal_conflict and edges:
                    edges = (
                        edges[0].model_copy(update={"status": CausalEdgeStatus.CONFLICTING}),
                        *edges[1:],
                    )
                self._normal_graph = (events, edges)
        return result

    def read_graph(self, *, subject):
        if not self.causal_available:
            return AdapterResult(False, "CAUSAL_SOURCE_UNAVAILABLE")
        if hasattr(self, "_normal_graph"):
            return self._normal_graph
        run_id = UUID(str(subject["run_id"]))
        lane = N02LaneId(subject["lane_id"])
        first = CausalEvent(
            kind=CausalEventKind.CONSENT_COMMITTED,
            run_id=run_id,
            lane_id=lane,
            subject_ref=str(subject["subject_ref"]),
            domain_identity={"consent_id": str(uuid4())},
            occurred_at=self.now,
            observed_at=self.now,
            source_type="DB",
            source_ref="fixture:consent",
        )
        second = CausalEvent(
            kind=CausalEventKind.PROCESSING_REQUESTED,
            run_id=run_id,
            lane_id=lane,
            subject_ref=str(subject["subject_ref"]),
            path_id=ProtectedPathId.DOCUMENT_ANALYSIS,
            domain_identity={"request_id": str(uuid4())},
            occurred_at=self.now,
            observed_at=self.now,
            source_type="HTTP",
            source_ref="fixture:request",
        )
        edge = CausalEdge(
            run_id=run_id,
            lane_id=lane,
            subject_ref=str(subject["subject_ref"]),
            from_event_id=first.causal_event_id,
            to_event_id=second.causal_event_id,
            relation=CausalRelation.PROGRAM_ORDER,
            proof_refs=("fixture:program-order",),
            status=CausalEdgeStatus.PROVEN,
        )
        return (first, second), (edge,)

    def apply_consent_fault(self, *, run_id: str, subject, expires_at):
        self._fault_active = True
        return AdapterResult(True, "FAULT_MARKER_APPLIED", {"expires_at": expires_at.isoformat()})

    def read_consent_fault_receipt(self, *, run_id: str, subject):
        if not self._fault_was_triggered:
            return AdapterResult(False, "FAULT_NOT_TRIGGERED")
        return ConsentFaultReceipt(
            run_id=UUID(run_id),
            lane_id=N02LaneId.CONSENT_FAULT_RECOVERY,
            subject_ref=str(subject["subject_ref"]),
            invitation_id=UUID(str(subject["invitation_id"])),
            applicant_id=UUID(str(subject["applicant_id"])),
            fault_variant=ConsentFaultVariant.AFTER_CONSENT_RECORD_BEFORE_STATE,
            boundary=ConsentFaultBoundary.AFTER_CONSENT_RECORD_BEFORE_INVITATION_STATE,
            request_id=str(self._fault_request_id),
            triggered_at=self.now,
            one_shot_consumed=True,
        )

    def restore_consent_fault(self, *, run_id: str, subject):
        succeeded = self.restore_succeeded
        if succeeded:
            self._fault_active = False
            self._overlay_paths.clear()
        return AdapterResult(
            succeeded,
            "CONSENT_FAULT_RESTORED" if succeeded else "CONSENT_FAULT_RESTORE_FAILED",
            {
                "marker_removed": succeeded,
                "consumed_token_removed": succeeded,
                "hook_inactive": succeeded,
                "failed_request_effects_zero": succeeded,
                "manual_cleanup_required": not succeeded,
            },
        )

    def read_processing_receipts(self, *, run_id: str, lane_id: str, subject_ref: str):
        return AdapterResult(True, "RECEIPTS_READ", {"receipts": []})


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
    n02 = FakeN02Adapters()
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
            n02_consent=n02,
            n02_seed=n02,
            n02_processing=n02,
            n02_causality=n02,
            n02_fault=n02,
            n02_observer=n02,
        ),
        browser,
    )
