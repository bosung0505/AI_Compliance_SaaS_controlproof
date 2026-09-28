"""Independently verifiable E-03 AFTER action pipeline."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from engine.adapters.base import AdapterResult, AdapterSet, Clock
from engine.judges.e03 import judge_e03_after
from engine.models import (
    AssertionResult,
    BusinessEffectSnapshot,
    ExecutionProfile,
    FaultBoundaryReceipt,
    FaultVariant,
    Presence,
    QueueTopologySnapshot,
    ReadinessCheck,
    ReadinessStatus,
    ScenarioReadiness,
    TargetEnvironmentSnapshot,
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
class E03AfterSliceResult:
    environment: TargetEnvironmentSnapshot
    topology: QueueTopologySnapshot
    subject: dict[str, Any]
    source_event_id: UUID
    boundary: FaultBoundaryReceipt | None
    duplicate_ack: AdapterResult
    committed_effects: tuple[BusinessEffectSnapshot, ...]
    final_effects: tuple[BusinessEffectSnapshot, ...]
    dlq_presence: Presence
    restore: AdapterResult
    assertions: tuple[
        AssertionResult,
        AssertionResult,
        AssertionResult,
        AssertionResult,
    ]


class E03AfterExecutor:
    """Owns US4 while the later shared bundle orchestration remains fail-closed."""

    profile = ExecutionProfile.E03_AFTER_V2

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
                        capability="profile.e03_after_v2.sealed_execution",
                        status=ReadinessStatus.RUNNER_NOT_READY,
                        detail="US4 action slice passes; sealed bundle composition is Phase 8 work",
                        operator_action=action,
                    ),
                ),
                "operator_action": action,
            }
        )

    def execute(self, *_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError(
            "E03_AFTER_V2 sealed execution remains blocked until shared bundle orchestration"
        )

    def collect_us4(
        self,
        *,
        run_id: UUID,
        subject_ref: str = "candidate-01",
    ) -> E03AfterSliceResult:
        environment = _required(self.adapters.environment, "environment").capture_environment()
        queue = _required(self.adapters.queue, "queue")
        effects = _required(self.adapters.effects, "reporting effects")
        duplicate_reader = _required(self.adapters.duplicate_acks, "duplicate ack")
        boundary_reader = _required(self.adapters.boundary_receipts, "boundary receipt")
        topology = queue.capture_topology()
        seeded = self.adapters.seed.seed(run_id=str(run_id), subject_ref=subject_ref)
        _require_ok(seeded, "seed")
        subject = dict(seeded.data)
        logical_operation_id = uuid5(
            NAMESPACE_URL,
            f"controlproof:{run_id}:e03-after:reporting",
        )

        applied: AdapterResult | None = None
        completed = False
        try:
            applied = self.adapters.fault.apply_after(
                run_id=str(run_id),
                subject=subject,
                expires_at=self.clock.now() + timedelta(minutes=5),
            )
            _require_ok(applied, "AFTER fault apply")
            trigger = self.adapters.seed.trigger(run_id=str(run_id), subject=subject)
            _require_ok(trigger, "reporting trigger")
            source_event_id = UUID(str(trigger.data["outbox_event_id"]))

            boundary = self._poll_boundary(
                boundary_reader,
                run_id=run_id,
                source_event_id=source_event_id,
                session_id=str(subject["interview_session_id"]),
            )
            committed = effects.read_reporting_effects(
                subject=subject,
                phase="INJECTED",
                run_id=run_id,
                logical_operation_id=logical_operation_id,
                source_event_id=source_event_id,
                step_id="after-commit-effects",
            )
            duplicate_ack = self._poll_duplicate_ack(
                duplicate_reader,
                run_id=run_id,
                source_event_id=source_event_id,
            )
            final = effects.read_reporting_effects(
                subject=subject,
                phase="RECOVERED",
                run_id=run_id,
                logical_operation_id=logical_operation_id,
                source_event_id=source_event_id,
                step_id="after-duplicate-ack-effects",
            )
            dlq = queue.read_dlq(
                source_event_id=str(source_event_id),
                subject_ref=subject_ref,
                session_id=str(subject["interview_session_id"]),
            )
            dlq_presence = dlq.data.get(
                "presence",
                Presence.ABSENT if dlq.ok else Presence.UNAVAILABLE,
            )
            restore = self.adapters.fault.restore(run_id=str(run_id), subject=subject)
            assertions = judge_e03_after(
                source_event_id=source_event_id,
                boundary=boundary,
                duplicate_ack=duplicate_ack,
                committed_effects=committed,
                final_effects=final,
                dlq_presence=dlq_presence,
                restore=restore,
            )
            completed = True
        finally:
            if applied is not None and applied.ok and not completed:
                self.adapters.fault.restore(run_id=str(run_id), subject=subject)

        teardown = self.adapters.seed.teardown(run_id=str(run_id), subject=subject)
        _require_ok(teardown, "synthetic fixture teardown")
        return E03AfterSliceResult(
            environment=environment,
            topology=topology,
            subject=subject,
            source_event_id=source_event_id,
            boundary=boundary,
            duplicate_ack=duplicate_ack,
            committed_effects=committed,
            final_effects=final,
            dlq_presence=dlq_presence,
            restore=restore,
            assertions=assertions,
        )

    def _poll_boundary(
        self,
        reader: Any,
        *,
        run_id: UUID,
        source_event_id: UUID,
        session_id: str,
    ) -> FaultBoundaryReceipt | None:
        iterations = self._duplicate_iterations()
        for index in range(iterations):
            result = reader.read_boundary_receipt(
                run_id=str(run_id),
                source_event_id=str(source_event_id),
                fault_variant=FaultVariant.AFTER_RESULT_DURABLE_BEFORE_COMPLETION.value,
                session_id=session_id,
            )
            if isinstance(result, FaultBoundaryReceipt):
                return result
            if isinstance(result, AdapterResult) and result.ok:
                receipt = result.data.get("receipt")
                if isinstance(receipt, FaultBoundaryReceipt):
                    return receipt
            if index + 1 < iterations:
                self.clock.sleep(self.scenario.timing_policy.poll_seconds)
        return None

    def _poll_duplicate_ack(
        self,
        reader: Any,
        *,
        run_id: UUID,
        source_event_id: UUID,
    ) -> AdapterResult:
        last = AdapterResult(False, "DUPLICATE_ACK_MISSING")
        for index in range(self._duplicate_iterations()):
            last = reader.read_duplicate_ack(
                run_id=str(run_id),
                source_event_id=str(source_event_id),
            )
            if last.ok:
                break
            if index + 1 < self._duplicate_iterations():
                self.clock.sleep(self.scenario.timing_policy.poll_seconds)
        return last

    def _duplicate_iterations(self) -> int:
        policy = self.scenario.timing_policy
        return max(1, int(policy.duplicate_ack_deadline_seconds / policy.poll_seconds))


def _required(adapter: Any, name: str) -> Any:
    if adapter is None:
        raise RuntimeError(f"E03 AFTER {name} adapter is not composed")
    return adapter


def _require_ok(result: AdapterResult, label: str) -> None:
    if not result.ok:
        raise RuntimeError(f"E03 AFTER {label} failed: {result.code}")
