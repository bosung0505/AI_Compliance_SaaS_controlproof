"""H-03 DLQ evidence collection slice shared by the eventual full profile executor."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from engine.adapters.base import AdapterResult, AdapterSet, Clock
from engine.execution import coordinate_reporting_recovery
from engine.judges.h03_dlq import judge_h03_decisions, judge_h03_dlq
from engine.models import (
    AssertionResult,
    BusinessEffectSnapshot,
    DecisionPathCapability,
    DecisionPathId,
    DeliveryAttemptRecord,
    ExecutionProfile,
    FaultBoundaryReceipt,
    FaultVariant,
    Phase,
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
    decision_capabilities: tuple[DecisionPathCapability, ...] = ()
    decision_cases: tuple[DecisionPathCaseResult, ...] = ()
    decision_assertion: AssertionResult | None = None


@dataclass(frozen=True, slots=True)
class DecisionPathCaseResult:
    path_id: DecisionPathId
    logical_operation_id: UUID
    attempt: AdapterResult
    pre_effects: tuple[BusinessEffectSnapshot, ...]
    post_effects: tuple[BusinessEffectSnapshot, ...]
    reset: AdapterResult

    def judge_input(self) -> dict[str, Any]:
        return {
            "path_id": self.path_id,
            "attempt": self.attempt,
            "pre_effects": self.pre_effects,
            "post_effects": self.post_effects,
            "reset": self.reset,
        }


class H03DlqExecutor:
    """Owns the independently verifiable US1 and US2 H-03 action slices.

    The canonical sealed profile remains fail-closed until later shared recovery/evidence
    orchestration is composed. These slice methods never manufacture a partial profile verdict.
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

        # The independently testable US1/US2 slices are intentionally not a sealed Run.
        # Keep CLI preflight honest until the shared recovery/evidence composition is complete.
        action = (
            "complete shared recovery/evidence orchestration before running the canonical "
            "H03_DLQ_V2 profile"
        )
        return readiness.model_copy(
            update={
                "status": ReadinessStatus.RUNNER_NOT_READY,
                "checks": readiness.checks
                + (
                    ReadinessCheck(
                        capability="profile.h03_dlq_v2.sealed_execution",
                        status=ReadinessStatus.RUNNER_NOT_READY,
                        detail="US1 and US2 slices pass, but canonical bundle orchestration is incomplete",
                        operator_action=action,
                    ),
                ),
                "operator_action": action,
            }
        )

    def execute(self, *_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError(
            "H03_DLQ_V2 sealed execution remains blocked until shared recovery/evidence "
            "orchestration is composed"
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

        return self._collect(run_id=run_id, subject_ref=subject_ref, include_decisions=False)

    def collect_us2(
        self,
        *,
        run_id: UUID,
        subject_ref: str = "candidate-01",
    ) -> H03DlqSliceResult:
        """Exercise US1 plus the three isolated company decision paths from US2."""

        return self._collect(run_id=run_id, subject_ref=subject_ref, include_decisions=True)

    def _collect(
        self,
        *,
        run_id: UUID,
        subject_ref: str,
        include_decisions: bool,
    ) -> H03DlqSliceResult:
        environment = _required_adapter(
            self.adapters.environment, "environment"
        ).capture_environment()
        queue = _required_adapter(self.adapters.queue, "queue")
        topology = queue.capture_topology()
        seeded = self.adapters.seed.seed(run_id=str(run_id), subject_ref=subject_ref)
        _require_ok(seeded, "seed")
        subject = dict(seeded.data)
        baseline = self.adapters.state.snapshot(subject=subject, phase="BASELINE")
        _require_ok(baseline, "baseline")

        applied: AdapterResult | None = None
        restore: AdapterResult | None = None
        decision_capabilities: tuple[DecisionPathCapability, ...] = ()
        decision_cases: tuple[DecisionPathCaseResult, ...] = ()
        decision_assertion = None
        collection_completed = False
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
                session_id=str(subject["interview_session_id"]),
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
            if include_decisions:
                decision = _required_adapter(self.adapters.decision, "decision")
                decision_capabilities = decision.capabilities(subject=subject)
                decision_cases = self._execute_decision_cases(
                    run_id=run_id,
                    source_event_id=source_event_id,
                    subject=subject,
                    capabilities=decision_capabilities,
                )
                decision_assertion = judge_h03_decisions(
                    capabilities=decision_capabilities,
                    cases=tuple(case.judge_input() for case in decision_cases),
                )
            collection_completed = True
        finally:
            if applied is not None and applied.ok and not collection_completed:
                restore = self.adapters.fault.restore(run_id=str(run_id), subject=subject)

        if terminal is not None:
            recovery = coordinate_reporting_recovery(
                fault=self.adapters.fault,
                redrive=queue,
                effects=None,
                run_id=run_id,
                source_event_id=source_event_id,
                logical_operation_id=uuid5(
                    NAMESPACE_URL, f"controlproof:{run_id}:h03:reporting-recovery"
                ),
                subject=subject,
                clock=self.clock,
                poll_seconds=self.scenario.timing_policy.poll_seconds,
                deadline_seconds=(
                    self.scenario.timing_policy.environment_restore_deadline_seconds
                ),
            )
            restore = recovery.restore
            redrive = recovery.redrive
        else:
            restore = self.adapters.fault.restore(run_id=str(run_id), subject=subject)
            redrive = None
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
            decision_capabilities=decision_capabilities,
            decision_cases=decision_cases,
            decision_assertion=decision_assertion,
        )

    def _execute_decision_cases(
        self,
        *,
        run_id: UUID,
        source_event_id: UUID,
        subject: dict[str, Any],
        capabilities: tuple[DecisionPathCapability, ...],
    ) -> tuple[DecisionPathCaseResult, ...]:
        decision = _required_adapter(self.adapters.decision, "decision")
        effects = _required_adapter(self.adapters.effects, "decision effects")
        cases: list[DecisionPathCaseResult] = []
        for capability in capabilities:
            logical_operation_id = uuid5(
                NAMESPACE_URL,
                f"controlproof:{run_id}:h03:{capability.path_id.value}",
            )
            token = decision.capture_reset_token(subject=subject)
            _require_ok(token, f"{capability.path_id.value} reset snapshot")
            pre = effects.read_decision_effects(
                subject=subject,
                phase=Phase.INJECTED,
                run_id=run_id,
                logical_operation_id=logical_operation_id,
                source_event_id=source_event_id,
                step_id=f"{capability.path_id.value}.pre",
            )
            attempt: AdapterResult | None = None
            post: tuple[BusinessEffectSnapshot, ...] = ()
            reset: AdapterResult | None = None
            try:
                attempt = decision.attempt(
                    path_id=capability.path_id,
                    subject=subject,
                    idempotency_key=(
                        f"controlproof:{run_id}:{capability.path_id.value}"
                    ),
                )
                post = effects.read_decision_effects(
                    subject=subject,
                    phase=Phase.INJECTED,
                    run_id=run_id,
                    logical_operation_id=logical_operation_id,
                    source_event_id=source_event_id,
                    step_id=f"{capability.path_id.value}.post",
                )
            finally:
                reset = decision.reset(subject=subject, token=token.data)
            _require_ok(reset, f"{capability.path_id.value} state reset")
            if attempt is None:
                raise RuntimeError(f"{capability.path_id.value} decision attempt did not run")
            cases.append(
                DecisionPathCaseResult(
                    path_id=capability.path_id,
                    logical_operation_id=logical_operation_id,
                    attempt=attempt,
                    pre_effects=pre,
                    post_effects=post,
                    reset=reset,
                )
            )
        return tuple(cases)

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
    session_id: str,
) -> FaultBoundaryReceipt:
    reader = _required_adapter(adapter, "boundary receipt")
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
    raise RuntimeError(f"H03 DLQ boundary receipt failed: {code}")
