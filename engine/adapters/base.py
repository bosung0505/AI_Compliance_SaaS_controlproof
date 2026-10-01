"""Service-neutral adapter boundaries used by the scenario runner."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from engine.models import (
    BusinessEffectSnapshot,
    CausalEdge,
    CausalEvent,
    ConsentFaultReceipt,
    ConsentPolicySnapshot,
    ConsentStateSnapshot,
    DecisionPathCapability,
    FaultBoundaryReceipt,
    ProcessingAttemptReceipt,
    ProtectedEffectSnapshot,
    ProtectedProcessingPath,
    QueueTopologySnapshot,
    ReadinessStatus,
    RecoveryRecord,
    RedriveReceipt,
    RunSubjectLane,
    TargetEnvironmentSnapshot,
    TargetSnapshot,
)


@dataclass(frozen=True, slots=True)
class CapabilityProbeResult:
    capability: str
    status: ReadinessStatus
    detail: str
    operator_action: str | None = None


@dataclass(frozen=True, slots=True)
class AdapterResult:
    ok: bool
    code: str
    data: Mapping[str, Any] = field(default_factory=dict)
    detail: str = ""


class CapabilityProbe(Protocol):
    @property
    def registrations(self) -> Mapping[str, str]: ...

    def probe(self, capability: str) -> CapabilityProbeResult: ...


class TargetAdapter(Protocol):
    @property
    def registrations(self) -> Mapping[str, str]: ...

    def capture_target_snapshot(self) -> TargetSnapshot: ...

    def target_feature_exists(self) -> bool: ...


class SeedAdapter(Protocol):
    def seed(self, *, run_id: str, subject_ref: str) -> AdapterResult: ...

    def trigger(self, *, run_id: str, subject: Mapping[str, Any]) -> AdapterResult: ...

    def teardown(self, *, run_id: str, subject: Mapping[str, Any]) -> AdapterResult: ...


class StateAdapter(Protocol):
    def snapshot(self, *, subject: Mapping[str, Any], phase: str) -> AdapterResult: ...

    def report_status(self, *, subject: Mapping[str, Any]) -> AdapterResult: ...

    def attempt_final_decision(self, *, subject: Mapping[str, Any]) -> AdapterResult: ...


class FaultAdapter(Protocol):
    def apply(
        self, *, run_id: str, subject: Mapping[str, Any], expires_at: datetime
    ) -> AdapterResult: ...

    def apply_after(
        self, *, run_id: str, subject: Mapping[str, Any], expires_at: datetime
    ) -> AdapterResult: ...

    def probe_effect(
        self,
        *,
        run_id: str,
        subject: Mapping[str, Any],
        trigger: Mapping[str, Any],
    ) -> AdapterResult: ...

    def restore(self, *, run_id: str, subject: Mapping[str, Any]) -> AdapterResult: ...

    def target_safe(self, *, subject_ref: str) -> bool: ...


class BrowserAdapter(Protocol):
    def capture_review(self, *, subject: Mapping[str, Any]) -> AdapterResult: ...

    def close(self) -> None: ...


class Clock(Protocol):
    def now(self) -> datetime: ...

    def sleep(self, seconds: float) -> None: ...


class EnvironmentAdapter(Protocol):
    def capture_environment(self) -> TargetEnvironmentSnapshot: ...


class QueueAdapter(Protocol):
    def capture_topology(self) -> QueueTopologySnapshot: ...

    def read_attempts(
        self, *, source_event_id: str, run_id: str | None = None
    ) -> AdapterResult: ...

    def read_dlq(
        self,
        *,
        source_event_id: str,
        subject_ref: str | None = None,
        session_id: str | None = None,
    ) -> AdapterResult: ...

    def redrive(self, *, source_event_id: str) -> RedriveReceipt: ...


class BoundaryReceiptAdapter(Protocol):
    def read_boundary_receipt(
        self,
        *,
        run_id: str,
        source_event_id: str,
        fault_variant: str,
        session_id: str | None = None,
        expected_attempt: int | None = None,
    ) -> FaultBoundaryReceipt | AdapterResult: ...


class DuplicateAckAdapter(Protocol):
    def read_duplicate_ack(
        self, *, run_id: str, source_event_id: str
    ) -> AdapterResult: ...


class SafeRedriveAdapter(Protocol):
    def redrive(self, *, source_event_id: str) -> RedriveReceipt: ...


class DecisionAdapter(Protocol):
    def capabilities(
        self, *, subject: Mapping[str, Any] | None = None
    ) -> tuple[DecisionPathCapability, ...]: ...

    def attempt(
        self,
        *,
        path_id: str,
        subject: Mapping[str, Any],
        idempotency_key: str | None = None,
    ) -> AdapterResult: ...

    def capture_reset_token(self, *, subject: Mapping[str, Any]) -> AdapterResult: ...

    def reset(
        self, *, subject: Mapping[str, Any], token: Mapping[str, Any]
    ) -> AdapterResult: ...


class EffectAdapter(Protocol):
    def read_reporting_effects(
        self,
        *,
        subject: Mapping[str, Any],
        phase: str,
        run_id: Any,
        logical_operation_id: Any,
        source_event_id: Any,
        step_id: str,
        attempt: int = 1,
    ) -> tuple[BusinessEffectSnapshot, ...]: ...

    def read_decision_effects(
        self,
        *,
        subject: Mapping[str, Any],
        phase: str,
        run_id: Any,
        logical_operation_id: Any,
        source_event_id: Any,
        step_id: str,
        attempt: int = 1,
    ) -> tuple[BusinessEffectSnapshot, ...]: ...


class ConsentAdapter(Protocol):
    def read_policy(self, *, subject: Mapping[str, Any]) -> ConsentPolicySnapshot | AdapterResult: ...

    def commit(
        self,
        *,
        subject: Mapping[str, Any],
        policy: ConsentPolicySnapshot,
        request_id: str,
        trace_id: str,
    ) -> AdapterResult: ...

    def read_state(
        self, *, subject: Mapping[str, Any], phase: str, step_id: str
    ) -> ConsentStateSnapshot | AdapterResult: ...


class N02SeedAdapter(Protocol):
    def seed_lanes(self, *, run_id: str) -> tuple[RunSubjectLane, ...] | AdapterResult: ...

    def apply_probe_overlay(
        self, *, subject: Mapping[str, Any], path_id: str
    ) -> AdapterResult: ...

    def remove_probe_overlay(
        self, *, subject: Mapping[str, Any], path_id: str
    ) -> AdapterResult: ...

    def teardown_lanes(self, *, run_id: str, lanes: tuple[RunSubjectLane, ...]) -> AdapterResult: ...


class ProtectedProcessingAdapter(Protocol):
    def paths(self) -> tuple[ProtectedProcessingPath, ...]: ...

    def attempt(
        self, *, path_id: str, subject: Mapping[str, Any]
    ) -> ProcessingAttemptReceipt | AdapterResult: ...

    def read_effects(
        self, *, path_id: str, subject: Mapping[str, Any], phase: str, step_id: str
    ) -> ProtectedEffectSnapshot | AdapterResult: ...


class CausalityAdapter(Protocol):
    def read_graph(
        self, *, subject: Mapping[str, Any]
    ) -> tuple[tuple[CausalEvent, ...], tuple[CausalEdge, ...]] | AdapterResult: ...


class ConsentFaultAdapter(Protocol):
    def apply_consent_fault(
        self, *, run_id: str, subject: Mapping[str, Any], expires_at: datetime
    ) -> AdapterResult: ...

    def read_consent_fault_receipt(
        self, *, run_id: str, subject: Mapping[str, Any]
    ) -> ConsentFaultReceipt | AdapterResult: ...

    def restore_consent_fault(
        self, *, run_id: str, subject: Mapping[str, Any]
    ) -> RecoveryRecord | AdapterResult: ...


class ProcessingObserverAdapter(Protocol):
    def read_processing_receipts(
        self, *, run_id: str, lane_id: str, subject_ref: str
    ) -> AdapterResult: ...


@dataclass(frozen=True, slots=True)
class AdapterSet:
    target: TargetAdapter
    capability: CapabilityProbe
    seed: SeedAdapter
    state: StateAdapter
    fault: FaultAdapter
    browser: BrowserAdapter
    environment: EnvironmentAdapter | None = None
    queue: QueueAdapter | None = None
    decision: DecisionAdapter | None = None
    effects: EffectAdapter | None = None
    boundary_receipts: BoundaryReceiptAdapter | None = None
    duplicate_acks: DuplicateAckAdapter | None = None
    safe_redrive: SafeRedriveAdapter | None = None
    n02_consent: ConsentAdapter | None = None
    n02_seed: N02SeedAdapter | None = None
    n02_processing: ProtectedProcessingAdapter | None = None
    n02_causality: CausalityAdapter | None = None
    n02_fault: ConsentFaultAdapter | None = None
    n02_observer: ProcessingObserverAdapter | None = None
