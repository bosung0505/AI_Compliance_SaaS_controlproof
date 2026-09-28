"""Independently verifiable E-03 BEFORE action pipeline (A7 intentionally pending)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from engine.adapters.base import AdapterResult, AdapterSet, Clock
from engine.execution import coordinate_reporting_recovery
from engine.judges.e03 import judge_e03_before
from engine.models import (
    AssertionResult,
    BusinessEffectSnapshot,
    DeliveryAttemptRecord,
    FaultBoundaryReceipt,
    FaultVariant,
    Presence,
    QueueTopologySnapshot,
    RedriveReceipt,
    TargetEnvironmentSnapshot,
    TerminalFailureRecord,
    utcnow,
)
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
    assertions: tuple[
        AssertionResult,
        AssertionResult,
        AssertionResult,
        AssertionResult,
        AssertionResult,
    ]
    pending_assertion_ids: tuple[str, ...]
    redrive_receipts: tuple[dict[str, Any], ...]


class E03BeforeExecutor:
    """Runs the US3 subset without creating a profile verdict or Evidence Bundle."""

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

    def execute(self, *_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError(
            "E03_BEFORE_V2 remains blocked until US5 composes E03-A7 decision replay"
        )

    def collect_us3(
        self,
        *,
        run_id: UUID,
        subject_ref: str = "candidate-01",
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
            pending_assertion_ids=("E03-A7",),
            redrive_receipts=tuple(receipts),
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
