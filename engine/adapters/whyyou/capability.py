"""WhyYou H-03 capability classifier; runner gaps never masquerade as target absence."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, text

from engine.adapters.base import CapabilityProbeResult
from engine.adapters.whyyou.client import TargetSnapshotCaptureError, WhyYouClient
from engine.adapters.whyyou.decisions import WhyYouDecisionAdapter
from engine.adapters.whyyou.effects import WhyYouEffectAdapter
from engine.adapters.whyyou.environment import WhyYouEnvironmentAdapter
from engine.adapters.whyyou.queue import (
    QueueAccessError,
    QueueContractError,
    WhyYouQueueAdapter,
)
from engine.config import Settings
from engine.models import ReadinessStatus

CAPABILITY_VERSIONS = {
    "target.version.read": "v1",
    "reporting.status.read": "v1",
    "reporting.ui.observe": "v1",
    "hiring.final_decision.attempt": "v1",
    "hiring.state.read": "v1",
    "hiring.decision_history.read": "v1",
    "h03.subject.seed": "v1",
    "reporting.trigger": "v1",
    "reporting.fault.inject": "v1",
    "reporting.fault.probe": "v1",
    "reporting.fault.restore": "v1",
    "reporting.model.deterministic": "v1",
    "target.environment.read": "v1",
    "messaging.reporting.topology.read": "v1",
    "messaging.reporting.attempts.read": "v1",
    "messaging.reporting.dlq.read": "v1",
    "messaging.reporting.dlq.redrive": "v1",
    "reporting.fault.before.inject": "v1",
    "reporting.fault.after.inject": "v1",
    "reporting.fault.boundary.read": "v1",
    "reporting.duplicate_ack.read": "v1",
    "hiring.decision_paths.read": "v1",
    "hiring.decision_path.attempt": "v1",
    "hiring.final_decision.replay": "v1",
    "reporting.effects.read": "v1",
    "hiring.decision_effects.read": "v1",
}


class WhyYouCapabilityProbe:
    def __init__(
        self,
        settings: Settings,
        client: WhyYouClient,
        *,
        queue: WhyYouQueueAdapter | None = None,
        environment: WhyYouEnvironmentAdapter | None = None,
        decision: WhyYouDecisionAdapter | None = None,
        effects: WhyYouEffectAdapter | None = None,
    ) -> None:
        self.settings = settings
        self.client = client
        self.queue = queue
        self.environment = environment
        self.decision = decision
        self.effects = effects
        self._openapi_paths: set[str] | None = None

    @property
    def registrations(self) -> dict[str, str]:
        return dict(CAPABILITY_VERSIONS)

    def target_feature_exists(self) -> bool:
        try:
            paths = self._paths()
        except Exception:  # noqa: BLE001 - inability to inspect is not target absence
            # An inaccessible target is not evidence that the product feature is absent.
            # Individual probes preserve ACCESS_BLOCKED vs RUNNER_NOT_READY.
            return True
        return (
            "/v1/interview-sessions/{session_id}/report" in paths
            and "/v1/invitations/{invitation_id}/final-decisions" in paths
        )

    def probe(self, capability: str) -> CapabilityProbeResult:
        try:
            if capability == "target.version.read":
                self.client.capture_target_snapshot()
                return _ready(capability, "canonical target snapshot is available")
            if capability == "target.environment.read":
                if self.environment is None:
                    return _not_ready(
                        capability,
                        "environment adapter is not composed",
                        "compose the Spec 002 environment adapter",
                    )
                self.environment.capture_environment()
                return _ready(capability, "canonical local environment snapshot is available")
            if capability in {
                "messaging.reporting.topology.read",
                "messaging.reporting.attempts.read",
                "messaging.reporting.dlq.read",
                "messaging.reporting.dlq.redrive",
            }:
                if self.queue is None:
                    return _not_ready(
                        capability,
                        "queue adapter is not composed",
                        "compose the Spec 002 LocalStack queue adapter",
                    )
                self.queue.capture_topology()
                return _ready(capability, "LocalStack reporting queue contract matches")
            if capability in {
                "hiring.decision_paths.read",
                "hiring.decision_path.attempt",
                "hiring.final_decision.replay",
            }:
                if self.decision is None:
                    return _not_ready(
                        capability,
                        "decision path adapter is not composed",
                        "compose the Spec 002 decision-path adapter",
                    )
                operations = self.decision.probe_operations()
                if not operations.ok:
                    status = (
                        ReadinessStatus.ACCESS_BLOCKED
                        if operations.code == "DECISION_OPERATIONS_ACCESS_BLOCKED"
                        else ReadinessStatus.RUNNER_NOT_READY
                    )
                    return CapabilityProbeResult(
                        capability,
                        status,
                        "canonical decision operations are unavailable",
                        "repair the pinned WhyYou OpenAPI decision operations",
                    )
                return _ready(
                    capability,
                    "two pinned operations are ready for three isolated decision cases",
                )
            if capability == "reporting.status.read":
                return self._route(capability, "/v1/interview-sessions/{session_id}/report")
            if capability == "hiring.final_decision.attempt":
                return self._route(capability, "/v1/invitations/{invitation_id}/final-decisions")
            if capability in {
                "hiring.state.read",
                "hiring.decision_history.read",
                "h03.subject.seed",
                "reporting.trigger",
            }:
                return self._database(capability)
            if capability in {
                "reporting.effects.read",
                "hiring.decision_effects.read",
            }:
                if self.effects is None:
                    return _not_ready(
                        capability,
                        "effect adapter is not composed",
                        "compose the scoped WhyYou effect adapter",
                    )
                return self._database(capability)
            if capability == "reporting.ui.observe":
                return self._browser(capability)
            if capability in {
                "reporting.fault.inject",
                "reporting.fault.probe",
                "reporting.fault.restore",
                "reporting.fault.before.inject",
                "reporting.fault.after.inject",
                "reporting.fault.boundary.read",
                "reporting.duplicate_ack.read",
            }:
                return self._fault(capability)
            if capability == "reporting.model.deterministic":
                return self._model(capability)
            return _not_ready(capability, "unknown capability", "install the registered probe")
        except TargetSnapshotCaptureError as exc:
            return _not_ready(capability, str(exc), "use a clean target and repair snapshot inputs")
        except QueueContractError as exc:
            return _not_ready(capability, str(exc), "repair the LocalStack reporting topology")
        except QueueAccessError:
            return CapabilityProbeResult(
                capability,
                ReadinessStatus.ACCESS_BLOCKED,
                "LocalStack reporting queue access is unavailable",
                "start LocalStack and provide local/test queue access",
            )
        except PermissionError:
            return CapabilityProbeResult(
                capability,
                ReadinessStatus.ACCESS_BLOCKED,
                "company credential was rejected by the isolated target",
                "provide a valid local/test company credential",
            )
        except Exception as exc:  # noqa: BLE001 - capability probes never leak provider errors
            return _not_ready(
                capability,
                f"probe failed: {type(exc).__name__}",
                "inspect the isolated WhyYou local stack",
            )

    def _paths(self) -> set[str]:
        if self._openapi_paths is None:
            response = self.client.http.get("/openapi.json")
            if response.status_code in {401, 403}:
                raise PermissionError("company credential cannot read OpenAPI")
            response.raise_for_status()
            self._openapi_paths = set(response.json().get("paths", {}))
        return self._openapi_paths

    def _route(self, capability: str, route: str) -> CapabilityProbeResult:
        if route not in self._paths():
            return CapabilityProbeResult(
                capability,
                ReadinessStatus.NO_TEST_TARGET,
                f"target route is absent: {route}",
                "use a WhyYou version that implements the H-03 target",
            )
        return _ready(capability, f"target route exists: {route}")

    def _database(self, capability: str) -> CapabilityProbeResult:
        try:
            engine = create_engine(self.settings.whyyou_database_url)
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception as exc:  # noqa: BLE001 - normalize driver-specific access errors
            return CapabilityProbeResult(
                capability,
                ReadinessStatus.ACCESS_BLOCKED,
                f"isolated database is not accessible: {type(exc).__name__}",
                "provide a local/test database credential with minimal required access",
            )
        return _ready(capability, "isolated database and schema mapping are accessible")

    def _browser(self, capability: str) -> CapabilityProbeResult:
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as playwright:
                executable = Path(playwright.chromium.executable_path)
                if not executable.exists():
                    raise FileNotFoundError
        except Exception:  # noqa: BLE001 - browser runtime failures become readiness detail
            return _not_ready(
                capability,
                "Playwright Chromium is not installed",
                "run python -m playwright install chromium",
            )
        return _ready(capability, "Playwright Chromium is available")

    def _fault(self, capability: str) -> CapabilityProbeResult:
        root = self.settings.fault_root
        receipts = root / "receipts"
        from engine.lifecycle import RestoreBlockStore

        if RestoreBlockStore(self.settings.run_root).blocked(
            self.settings.target_id,
            "candidate-01",
        ):
            return _not_ready(
                capability,
                "target is blocked after an uncertain restore",
                "verify target safety and run cleanup-confirm with evidence",
            )
        try:
            receipts.mkdir(parents=True, exist_ok=True)
            probe = root / f".controlproof-probe-{os.getpid()}"
            probe.write_text("probe", encoding="utf-8")
            probe.unlink()
            response = self.client.http.get("/internal/controlproof/health")
            body = response.json() if response.status_code == 200 else {}
        except Exception:  # noqa: BLE001 - normalize filesystem/HTTP probe failures
            return _not_ready(
                capability,
                "shared fault/receipt root or target hook health is unavailable",
                "mount CONTROLPROOF_FAULT_ROOT into the local/test worker and enable the hook",
            )
        if not body.get("fault_hooks_enabled"):
            return _not_ready(
                capability,
                "test-only reporting fault hook is not enabled",
                "enable the hook only in the isolated WhyYou test profile",
            )
        return _ready(capability, "shared marker/receipt root and target hook are ready")

    def _model(self, capability: str) -> CapabilityProbeResult:
        if not self.settings.model_substitute_enabled:
            return _not_ready(
                capability,
                "deterministic model substitute is disabled",
                "enable it only in the isolated local/test profile",
            )
        try:
            response = self.client.http.get("/internal/controlproof/health")
            body = response.json() if response.status_code == 200 else {}
        except Exception:  # noqa: BLE001 - an unavailable health endpoint is a mismatch
            body = {}
        matches = (
            body.get("model_substitute_enabled") is True
            and body.get("fixture_id") == self.settings.model_fixture_id
            and body.get("fixture_digest") == self.settings.model_fixture_digest
        )
        if not matches:
            return _not_ready(
                capability,
                "target model fixture ID/digest does not match the scenario",
                "activate the allowed fixed fixture without external-model fallback",
            )
        return _ready(capability, "deterministic model fixture ID and digest match")


def _ready(capability: str, detail: str) -> CapabilityProbeResult:
    return CapabilityProbeResult(capability, ReadinessStatus.READY, detail)


def _not_ready(capability: str, detail: str, action: str) -> CapabilityProbeResult:
    return CapabilityProbeResult(
        capability,
        ReadinessStatus.RUNNER_NOT_READY,
        detail,
        action,
    )
