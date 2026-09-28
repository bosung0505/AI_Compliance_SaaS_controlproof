"""H-03 DLQ evidence collection slice shared by the eventual full profile executor."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

from engine.adapters.base import AdapterResult, AdapterSet, Clock
from engine.judges.h03_dlq import judge_h03_dlq
from engine.models import (
    AssertionResult,
    DeliveryAttemptRecord,
    ExecutionProfile,
    FaultBoundaryReceipt,
    FaultVariant,
    Presence,
    QueueTopologySnapshot,
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
class H03DlqSliceResult:
    environment: TargetEnvironmentSnapshot
    topology: QueueTopologySnapshot
    subject: dict[str, Any]
    baseline: AdapterResult
    fault_application: AdapterResult
    trigger: AdapterResult
    boundary: FaultBoundaryReceipt
    source_event_id: UUID
    attempts: tuple[DeliveryAttemptRecord, ...]
    attempts_presence: Presence
    dlq_presence: Presence
    terminal_failure: TerminalFailureRecord | None
    report_status: str | None
    browser_projection: dict[str, Any]
    restore: AdapterResult
    redrive: RedriveReceipt | None
    assertions: tuple[AssertionResult, AssertionResult]


class H03DlqExecutor:
    """Owns the US1 pipeline while US2 later adds full decision-path execution.

    The profile is registered now, but preflight stays fail-closed until every capability in
    H-03-DLQ.yaml—including the US2 decision paths—is composed. No partial profile verdict or
    partially sealed Run is created by this class.
    """

    profile = ExecutionProfile.H03_DLQ_V2

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
        except Exception as exc:  # noqa: BLE001 - preserve sanitized readiness projection
            target_snapshot = getattr(exc, "diagnostic", None)
        probes = [
            self.adapters.capability.probe(capability)
            for capability in self.scenario.required_capabilities
        ]
        return evaluate_readiness(
            self.scenario,
            target_id=target_id,
            registrations=self.adapters.capability.registrations,
            probe_results=probes,
            target_feature_exists=self.adapters.target.target_feature_exists(),
            target_snapshot=target_snapshot,
        )

    def execute(self, *_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError(
            "H03_DLQ_V2 full profile execution remains blocked until US2 decision paths are composed"
        )

    def collect_us1(
        self,
        *,
        run_id: UUID,
        subject_ref: str = "candidate-01",
    ) -> H03DlqSliceResult:
        """Exercise the US1 action flow without claiming a full H03 profile verdict.

        This intentionally stops short of the decision-path assertions owned by US2. It still
        owns the real seed → fault → retry/DLQ → visibility → restore/redrive ordering, so US1
        can be verified independently without creating a misleading partial evidence bundle.
        """

        environment = _required_adapter(self.adapters.environment, "environment").capture_environment()
        queue = _required_adapter(self.adapters.queue, "queue")
        topology = queue.capture_topology()
        seeded = self.adapters.seed.seed(run_id=str(run_id), subject_ref=subject_ref)
        _require_ok(seeded, "seed")
        subject = dict(seeded.data)
        baseline = self.adapters.state.snapshot(subject=subject, phase="BASELINE")
        _require_ok(baseline, "baseline")

        applied: AdapterResult | None = None
        restore: AdapterResult | None = None
        try:
            now = self.clock.now()
            applied = self.adapters.fault.apply(
                run_id=str(run_id),
                subject=subject,
                expires_at=now + timedelta(minutes=5),
            )
            _require_ok(applied, "fault apply")
            triggered = self.adapters.seed.trigger(run_id=str(run_id), subject=subject)
            _require_ok(triggered, "reporting trigger")
            source_event_id = UUID(str(triggered.data["outbox_event_id"]))
            boundary = _read_required_boundary(
                self.adapters.boundary_receipts,
                run_id=run_id,
                source_event_id=source_event_id,
            )
            attempts, attempts_presence, presence, terminal = self._poll_terminal_lineage(
                queue=queue,
                run_id=run_id,
                source_event_id=source_event_id,
                subject=subject,
            )
            report = self.adapters.state.report_status(subject=subject)
            report_status = _report_status_class(report)
            browser = self.adapters.browser.capture_review(subject=subject)
            projection = dict(browser.data.get("projection", {})) if browser.ok else {}
        finally:
            if applied is not None and applied.ok:
                restore = self.adapters.fault.restore(run_id=str(run_id), subject=subject)

        if restore is None:
            raise RuntimeError("H03 DLQ restore did not execute")
        redrive = None
        if (
            terminal is not None
            and restore.ok
            and restore.data.get("marker_inactive") is True
            and restore.data.get("worker_healthy") is True
        ):
            redrive = queue.redrive(source_event_id=str(source_event_id))
        assertions = judge_h03_dlq(
            attempts=attempts,
            attempts_presence=attempts_presence,
            terminal=terminal,
            dlq_presence=presence,
            ui_status=projection.get("terminal_status_class"),
            api_status=report_status,
            operator_locator=terminal.route_locator if terminal else None,
            expected_receive_count=topology.max_receive_count,
        )
        teardown = self.adapters.seed.teardown(run_id=str(run_id), subject=subject)
        _require_ok(teardown, "synthetic fixture teardown")
        self.adapters.browser.close()
        return H03DlqSliceResult(
            environment=environment,
            topology=topology,
            subject=subject,
            baseline=baseline,
            fault_application=applied,
            trigger=triggered,
            boundary=boundary,
            source_event_id=source_event_id,
            attempts=attempts,
            attempts_presence=attempts_presence,
            dlq_presence=presence,
            terminal_failure=terminal,
            report_status=report_status,
            browser_projection=projection,
            restore=restore,
            redrive=redrive,
            assertions=assertions,
        )

    def _poll_terminal_lineage(
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
        presence = Presence.ABSENT
        terminal = None
        for index in range(iterations):
            attempts_result = queue.read_attempts(
                source_event_id=str(source_event_id), run_id=str(run_id)
            )
            attempts = tuple(attempts_result.data.get("records", ()))
            attempts_presence = attempts_result.data.get(
                "presence",
                Presence.ABSENT if attempts_result.ok else Presence.UNAVAILABLE,
            )
            dlq_result = queue.read_dlq(
                source_event_id=str(source_event_id),
                subject_ref=str(subject.get("subject_ref", "candidate-01")),
                session_id=str(subject["interview_session_id"]),
            )
            presence = dlq_result.data.get("presence", Presence.UNAVAILABLE)
            terminal = dlq_result.data.get("terminal_failure")
            if presence in {Presence.PRESENT, Presence.UNAVAILABLE}:
                break
            if index + 1 < iterations:
                self.clock.sleep(policy.poll_seconds)
        return attempts, attempts_presence, presence, terminal


def _required_adapter(adapter: Any, name: str) -> Any:
    if adapter is None:
        raise RuntimeError(f"H03 DLQ {name} adapter is not composed")
    return adapter


def _require_ok(result: AdapterResult, label: str) -> None:
    if not result.ok:
        raise RuntimeError(f"H03 DLQ {label} failed: {result.code}")


def _report_status_class(result: AdapterResult) -> str | None:
    if not result.ok:
        return None
    value = result.data.get("status") or result.data.get("presence")
    if isinstance(value, Presence):
        return value.value.casefold()
    return str(value).casefold() if value is not None else "absent"


def _read_required_boundary(
    adapter: Any,
    *,
    run_id: UUID,
    source_event_id: UUID,
) -> FaultBoundaryReceipt:
    reader = _required_adapter(adapter, "boundary receipt")
    result = reader.read_boundary_receipt(
        run_id=str(run_id),
        source_event_id=str(source_event_id),
        fault_variant=FaultVariant.BEFORE_RESULT_DURABLE.value,
    )
    if isinstance(result, FaultBoundaryReceipt):
        return result
    if isinstance(result, AdapterResult) and result.ok:
        receipt = result.data.get("receipt")
        if isinstance(receipt, FaultBoundaryReceipt):
            return receipt
    code = result.code if isinstance(result, AdapterResult) else "INVALID_BOUNDARY_RECEIPT"
    raise RuntimeError(f"H03 DLQ boundary receipt failed: {code}")
