"""Independently verifiable E-03 BEFORE action pipeline (A7 intentionally pending)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from engine.adapters.base import AdapterResult, AdapterSet, Clock
from engine.adapters.whyyou.decisions import compare_decision_replay
from engine.execution import coordinate_reporting_recovery
from engine.judges.e03 import judge_e03_before, judge_e03_decision_replay
from engine.models import (
    AssertionResult,
    AssertionStatus,
    BusinessEffectSnapshot,
    DecisionPathId,
    DeliveryAttemptRecord,
    ExecutionProfile,
    FaultBoundaryReceipt,
    FaultVariant,
    Presence,
    QueueTopologySnapshot,
    ReadinessCheck,
    ReadinessStatus,
    RedriveReceipt,
    ScenarioReadiness,
    TargetEnvironmentSnapshot,
    TerminalFailureRecord,
    utcnow,
)
from engine.readiness import evaluate_readiness
from engine.scenario import ScenarioDefinition


class _SystemClock:
    def now(self):
        return utcnow()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


@dataclass(frozen=True, slots=True)
class E03BeforeSliceResult:
    environment: TargetEnvironmentSnapshot
    topology: QueueTopologySnapshot
    subject: dict[str, Any]
    source_event_id: UUID
    boundary: FaultBoundaryReceipt
    attempts: tuple[DeliveryAttemptRecord, ...]
    attempts_presence: Presence
    dlq_presence: Presence
    terminal_failure: TerminalFailureRecord | None
    injected_effects: tuple[BusinessEffectSnapshot, ...]
    recovered_effects: tuple[BusinessEffectSnapshot, ...]
    restore: AdapterResult
    redrive: RedriveReceipt | None
    assertions: tuple[AssertionResult, ...]
    pending_assertion_ids: tuple[str, ...]
    redrive_receipts: tuple[dict[str, Any], ...]
    decision_path: DecisionPathId | None
    first_decision: AdapterResult | None
    replay_decision: AdapterResult | None
    replay_comparison: AdapterResult | None
    first_decision_effects: tuple[BusinessEffectSnapshot, ...]
    replay_decision_effects: tuple[BusinessEffectSnapshot, ...]


class E03BeforeExecutor:
    """Runs BEFORE recovery and the post-recovery same-key human decision replay."""

    profile = ExecutionProfile.E03_BEFORE_V2

    def __init__(
        self,
        scenario: ScenarioDefinition,
        adapters: AdapterSet,
        run_root: Path,
        *,
        clock: Clock | None = None,
    ) -> None:
        self.scenario = scenario
        self.adapters = adapters
        self.run_root = run_root.resolve()
        self.clock = clock or _SystemClock()

    def preflight(self, target_id: str) -> ScenarioReadiness:
        target_snapshot = None
        try:
            target_snapshot = self.adapters.target.capture_target_snapshot()
        except Exception as exc:  # noqa: BLE001
            target_snapshot = getattr(exc, "diagnostic", None)
        probes = [
            self.adapters.capability.probe(capability)
            for capability in self.scenario.required_capabilities
        ]
        readiness = evaluate_readiness(
            self.scenario,
            target_id=target_id,
            registrations=self.adapters.capability.registrations,
            probe_results=probes,
            target_feature_exists=self.adapters.target.target_feature_exists(),
            target_snapshot=target_snapshot,
        )
        if readiness.status is not ReadinessStatus.READY:
            return readiness
        action = "complete shared Spec 002 bundle orchestration before canonical execution"
        return readiness.model_copy(
            update={
                "status": ReadinessStatus.RUNNER_NOT_READY,
                "checks": readiness.checks
                + (
                    ReadinessCheck(
                        capability="profile.e03_before_v2.sealed_execution",
                        status=ReadinessStatus.RUNNER_NOT_READY,
                        detail="US3/US5 action slice passes; sealed bundle composition is Phase 8 work",
                        operator_action=action,
                    ),
                ),
                "operator_action": action,
            }
        )

    def execute(self, *_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError(
            "E03_BEFORE_V2 sealed execution remains blocked until shared bundle orchestration"
        )

    def collect_us3(
        self,
        *,
        run_id: UUID,
        subject_ref: str = "candidate-01",
    ) -> E03BeforeSliceResult:
        return self._collect(
            run_id=run_id,
            subject_ref=subject_ref,
            include_decision_replay=False,
        )

    def collect_us5(
        self,
        *,
        run_id: UUID,
        subject_ref: str = "candidate-01",
    ) -> E03BeforeSliceResult:
        return self._collect(
            run_id=run_id,
            subject_ref=subject_ref,
            include_decision_replay=True,
        )

    def _collect(
        self,
        *,
        run_id: UUID,
        subject_ref: str,
        include_decision_replay: bool,
    ) -> E03BeforeSliceResult:
        environment = _required(self.adapters.environment, "environment").capture_environment()
        queue = _required(self.adapters.queue, "queue")
        effects = _required(self.adapters.effects, "reporting effects")
        topology = queue.capture_topology()
        seeded = self.adapters.seed.seed(run_id=str(run_id), subject_ref=subject_ref)
        _require_ok(seeded, "seed")
        subject = dict(seeded.data)
        logical_operation_id = uuid5(
            NAMESPACE_URL, f"controlproof:{run_id}:e03-before:reporting"
        )

        applied: AdapterResult | None = None
        completed = False
        try:
            applied = self.adapters.fault.apply(
                run_id=str(run_id),
                subject=subject,
                expires_at=self.clock.now() + timedelta(minutes=5),
            )
            _require_ok(applied, "fault apply")
            trigger = self.adapters.seed.trigger(run_id=str(run_id), subject=subject)
            _require_ok(trigger, "reporting trigger")
            source_event_id = UUID(str(trigger.data["outbox_event_id"]))
            boundary = _read_boundary(
                self.adapters.boundary_receipts,
                run_id=run_id,
                source_event_id=source_event_id,
                session_id=str(subject["interview_session_id"]),
            )
            attempts, attempts_presence, dlq_presence, terminal = self._poll_terminal(
                queue=queue,
                run_id=run_id,
                source_event_id=source_event_id,
                subject=subject,
            )
            injected = effects.read_reporting_effects(
                subject=subject,
                phase="INJECTED",
                run_id=run_id,
                logical_operation_id=logical_operation_id,
                source_event_id=source_event_id,
                step_id="injected-reporting-effects",
            )
            receipts: list[dict[str, Any]] = []
            recovery = coordinate_reporting_recovery(
                fault=self.adapters.fault,
                redrive=_required(self.adapters.safe_redrive, "safe redrive"),
                effects=effects,
                run_id=run_id,
                source_event_id=source_event_id,
                logical_operation_id=logical_operation_id,
                subject=subject,
                clock=self.clock,
                poll_seconds=self.scenario.timing_policy.poll_seconds,
                deadline_seconds=(
                    self.scenario.timing_policy.environment_restore_deadline_seconds
                ),
                append_receipt=lambda path, value: receipts.append(
                    {"path": path, **dict(value)}
                ),
            )
            assertions = judge_e03_before(
                source_event_id=source_event_id,
                boundary=boundary,
                attempts=attempts,
                attempts_presence=attempts_presence,
                terminal=terminal,
                dlq_presence=dlq_presence,
                injected_effects=injected,
                recovered_effects=recovery.recovered_effects,
                restore=recovery.restore,
                redrive=recovery.redrive,
                expected_receive_count=topology.max_receive_count,
            )
            decision_path = None
            first_decision = None
            replay_decision = None
            replay_comparison = None
            first_decision_effects: tuple[BusinessEffectSnapshot, ...] = ()
            replay_decision_effects: tuple[BusinessEffectSnapshot, ...] = ()
            pending_assertion_ids = ("E03-A7",)
            if include_decision_replay:
                if assertions[3].status is AssertionStatus.PASS:
                    (
                        decision_path,
                        first_decision,
                        replay_decision,
                        replay_comparison,
                        first_decision_effects,
                        replay_decision_effects,
                        decision_assertion,
                    ) = self._execute_decision_replay(
                        run_id=run_id,
                        source_event_id=source_event_id,
                        subject=subject,
                    )
                else:
                    replay_comparison = AdapterResult(
                        False,
                        "DECISION_REPLAY_NOT_RUN",
                        {"reason": "REPORTING_RECOVERY_NOT_CONFIRMED"},
                    )
                    decision_assertion = judge_e03_decision_replay(
                        replay_comparison=replay_comparison,
                        first_effects=(),
                        replay_effects=(),
                        target_stage_id=str(subject["final_accept_stage_id"]),
                    )
                assertions = (*assertions[:4], decision_assertion, assertions[4])
                pending_assertion_ids = ()
            completed = True
        finally:
            if applied is not None and applied.ok and not completed:
                self.adapters.fault.restore(run_id=str(run_id), subject=subject)

        teardown = self.adapters.seed.teardown(run_id=str(run_id), subject=subject)
        _require_ok(teardown, "synthetic fixture teardown")
        return E03BeforeSliceResult(
            environment=environment,
            topology=topology,
            subject=subject,
            source_event_id=source_event_id,
            boundary=boundary,
            attempts=attempts,
            attempts_presence=attempts_presence,
            dlq_presence=dlq_presence,
            terminal_failure=terminal,
            injected_effects=injected,
            recovered_effects=recovery.recovered_effects,
            restore=recovery.restore,
            redrive=recovery.redrive,
            assertions=assertions,
            pending_assertion_ids=pending_assertion_ids,
            redrive_receipts=tuple(receipts),
            decision_path=decision_path,
            first_decision=first_decision,
            replay_decision=replay_decision,
            replay_comparison=replay_comparison,
            first_decision_effects=first_decision_effects,
            replay_decision_effects=replay_decision_effects,
        )

    def _execute_decision_replay(
        self,
        *,
        run_id: UUID,
        source_event_id: UUID,
        subject: dict[str, Any],
    ) -> tuple[
        DecisionPathId,
        AdapterResult,
        AdapterResult,
        AdapterResult,
        tuple[BusinessEffectSnapshot, ...],
        tuple[BusinessEffectSnapshot, ...],
        AssertionResult,
    ]:
        decision = _required(self.adapters.decision, "decision replay")
        effects = _required(self.adapters.effects, "decision effects")
        capability = next(
            item
            for item in decision.capabilities(subject=subject)
            if item.path_id is DecisionPathId.FINAL_DECISION
        )
        logical_operation_id = uuid5(
            NAMESPACE_URL,
            f"controlproof:{run_id}:e03:human-decision-replay",
        )
        idempotency_key = f"controlproof:{run_id}:E03-A7"
        first = decision.attempt(
            path_id=DecisionPathId.FINAL_DECISION,
            subject=subject,
            idempotency_key=idempotency_key,
        )
        first_effects = effects.read_decision_effects(
            subject=subject,
            phase="RECOVERED",
            run_id=run_id,
            logical_operation_id=logical_operation_id,
            source_event_id=source_event_id,
            step_id="human-decision-first-effects",
            attempt=1,
        )
        replay = decision.attempt(
            path_id=DecisionPathId.FINAL_DECISION,
            subject=subject,
            idempotency_key=idempotency_key,
        )
        replay_effects = effects.read_decision_effects(
            subject=subject,
            phase="RECOVERED",
            run_id=run_id,
            logical_operation_id=logical_operation_id,
            source_event_id=source_event_id,
            step_id="human-decision-replay-effects",
            attempt=2,
        )
        comparison = compare_decision_replay(first, replay)
        assertion = judge_e03_decision_replay(
            replay_comparison=comparison,
            first_effects=first_effects,
            replay_effects=replay_effects,
            target_stage_id=str(capability.target_stage_id),
        )
        return (
            DecisionPathId.FINAL_DECISION,
            first,
            replay,
            comparison,
            first_effects,
            replay_effects,
            assertion,
        )

    def _poll_terminal(
        self,
        *,
        queue: Any,
        run_id: UUID,
        source_event_id: UUID,
        subject: dict[str, Any],
    ) -> tuple[
        tuple[DeliveryAttemptRecord, ...],
        Presence,
        Presence,
        TerminalFailureRecord | None,
    ]:
        policy = self.scenario.timing_policy
        iterations = max(1, int(policy.dlq_deadline_seconds / policy.poll_seconds))
        attempts: tuple[DeliveryAttemptRecord, ...] = ()
        attempts_presence = Presence.ABSENT
        dlq_presence = Presence.ABSENT
        terminal = None
        for index in range(iterations):
            attempt_result = queue.read_attempts(
                source_event_id=str(source_event_id), run_id=str(run_id)
            )
            attempts = tuple(attempt_result.data.get("records", ()))
            attempts_presence = attempt_result.data.get(
                "presence",
                Presence.ABSENT if attempt_result.ok else Presence.UNAVAILABLE,
            )
            dlq_result = queue.read_dlq(
                source_event_id=str(source_event_id),
                subject_ref=str(subject.get("subject_ref", "candidate-01")),
                session_id=str(subject["interview_session_id"]),
            )
            dlq_presence = dlq_result.data.get("presence", Presence.UNAVAILABLE)
            terminal = dlq_result.data.get("terminal_failure")
            if dlq_presence in {Presence.PRESENT, Presence.UNAVAILABLE}:
                break
            if index + 1 < iterations:
                self.clock.sleep(policy.poll_seconds)
        return attempts, attempts_presence, dlq_presence, terminal


def _read_boundary(
    adapter: Any,
    *,
    run_id: UUID,
    source_event_id: UUID,
    session_id: str,
) -> FaultBoundaryReceipt:
    reader = _required(adapter, "boundary receipt")
    result = reader.read_boundary_receipt(
        run_id=str(run_id),
        source_event_id=str(source_event_id),
        fault_variant=FaultVariant.BEFORE_RESULT_DURABLE.value,
        session_id=session_id,
    )
    if isinstance(result, FaultBoundaryReceipt):
        return result
    if isinstance(result, AdapterResult) and result.ok:
        receipt = result.data.get("receipt")
        if isinstance(receipt, FaultBoundaryReceipt):
            return receipt
    code = result.code if isinstance(result, AdapterResult) else "INVALID_BOUNDARY_RECEIPT"
    raise RuntimeError(f"E03 BEFORE boundary receipt failed: {code}")


def _required(adapter: Any, name: str) -> Any:
    if adapter is None:
        raise RuntimeError(f"E03 BEFORE {name} adapter is not composed")
    return adapter


def _require_ok(result: AdapterResult, label: str) -> None:
    if not result.ok:
        raise RuntimeError(f"E03 BEFORE {label} failed: {result.code}")
