"""Service-neutral adapter boundaries used by the scenario runner."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from engine.models import (
    BusinessEffectSnapshot,
    DecisionPathCapability,
    FaultBoundaryReceipt,
    QueueTopologySnapshot,
    ReadinessStatus,
    RedriveReceipt,
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

    def read_attempts(self, *, source_event_id: str) -> AdapterResult: ...

    def read_dlq(self, *, source_event_id: str) -> AdapterResult: ...

    def redrive(self, *, source_event_id: str) -> RedriveReceipt: ...


class BoundaryReceiptAdapter(Protocol):
    def read_boundary_receipt(
        self,
        *,
        run_id: str,
        source_event_id: str,
        fault_variant: str,
    ) -> FaultBoundaryReceipt | AdapterResult: ...


class DuplicateAckAdapter(Protocol):
    def read_duplicate_ack(
        self, *, run_id: str, source_event_id: str
    ) -> AdapterResult: ...


class SafeRedriveAdapter(Protocol):
    def redrive(self, *, source_event_id: str) -> RedriveReceipt: ...


class DecisionAdapter(Protocol):
    def capabilities(self) -> tuple[DecisionPathCapability, ...]: ...

    def attempt(
        self,
        *,
        path_id: str,
        subject: Mapping[str, Any],
        idempotency_key: str | None = None,
    ) -> AdapterResult: ...


class EffectAdapter(Protocol):
    def read_reporting_effects(
        self, *, subject: Mapping[str, Any], phase: str
    ) -> tuple[BusinessEffectSnapshot, ...]: ...

    def read_decision_effects(
        self, *, subject: Mapping[str, Any], phase: str
    ) -> tuple[BusinessEffectSnapshot, ...]: ...


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
