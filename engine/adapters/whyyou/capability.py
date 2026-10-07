"""WhyYou H-03 capability classifier; runner gaps never masquerade as target absence."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import create_engine, text

from engine.adapters.base import CapabilityProbeResult
from engine.adapters.whyyou.client import TargetSnapshotCaptureError, WhyYouClient
from engine.adapters.whyyou.consent import WhyYouConsentAdapter
from engine.adapters.whyyou.consent_fault import WhyYouConsentFaultAdapter
from engine.adapters.whyyou.decisions import WhyYouDecisionAdapter
from engine.adapters.whyyou.effects import WhyYouEffectAdapter
from engine.adapters.whyyou.environment import WhyYouEnvironmentAdapter
from engine.adapters.whyyou.protected_processing import WhyYouProtectedProcessingAdapter
from engine.adapters.whyyou.queue import (
    QueueAccessError,
    QueueContractError,
    WhyYouQueueAdapter,
)
from engine.config import Settings, fixture_digest
from engine.models import SPEC004_FIXTURE_ID, ReadinessStatus

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
    "n02.subjects.seed": "v1",
    "n02.subjects.teardown": "v1",
    "processing.paths.read": "v1",
    "processing.document.attempt": "v1",
    "processing.recording.attempt": "v1",
    "processing.assessment.attempt": "v1",
    "processing.effects.read": "v1",
    "processing.boundary.receipts.read": "v1",
    "consent.policy.read": "v1",
    "consent.commit.write": "v1",
    "consent.state.read": "v1",
    "consent.fault.inject": "v1",
    "consent.fault.receipt.read": "v1",
    "consent.fault.restore": "v1",
    # Spec 004 (T042, T047). Criteria-version and scoring-source probes stay RUNNER_NOT_READY
    # until their adapters are composed (T055).
    "model.fixture.read": "v1",
    "spec004.lanes.seed": "v1",
    "spec004.lanes.teardown": "v1",
    "report.generation.request": "v1",
    "report.processing.receipts.read": "v1",
    "report.records.read": "v1",
    "report.api.read": "v1",
    "timeline.api.read": "v1",
    "model.emission.read": "v1",
    "evidence.segment.remove": "v1",
    "evidence.segment.restore": "v1",
    "report.axes.probe_write": "v1",
    "report.axes.probe_restore": "v1",
    "criteria.version.create": "v1",
    "criteria.version.publish": "v1",
    "criteria.version.read": "v1",
    "scoring.rule.source.read": "v1",
}

_SPEC004_COMPOSED = {
    "spec004.lanes.seed": ("spec004_seed", "database"),
    "spec004.lanes.teardown": ("spec004_seed", "database"),
    "report.generation.request": ("spec004_reports", "database"),
    "report.processing.receipts.read": ("spec004_reports", "database"),
    "report.records.read": ("spec004_reports", "database"),
    "report.api.read": ("spec004_reports", "/v1/interview-sessions/{session_id}/report"),
    "timeline.api.read": (
        "spec004_reports",
        "/v1/interview-sessions/{session_id}/timeline",
    ),
    "model.emission.read": ("spec004_emissions", "observer"),
    "evidence.segment.remove": ("spec004_mutation", "database"),
    "evidence.segment.restore": ("spec004_mutation", "database"),
    "report.axes.probe_write": ("spec004_mutation", "database"),
    "report.axes.probe_restore": ("spec004_mutation", "database"),
    "criteria.version.create": ("spec004_versions", "/v1/positions/{position_id}/competency-model-versions"),
    "criteria.version.publish": ("spec004_versions", "database"),
    "criteria.version.read": ("spec004_versions", "database"),
    "scoring.rule.source.read": ("spec004_scoring_source", "observer"),
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
        n02_processing: WhyYouProtectedProcessingAdapter | None = None,
        n02_consent: WhyYouConsentAdapter | None = None,
        n02_fault: WhyYouConsentFaultAdapter | None = None,
        spec004: Mapping[str, Any] | None = None,
    ) -> None:
        self.settings = settings
        self.client = client
        self.queue = queue
        self.environment = environment
        self.decision = decision
        self.effects = effects
        self.n02_processing = n02_processing
        self.n02_consent = n02_consent
        self.n02_fault = n02_fault
        self.spec004 = dict(spec004 or {})
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
            if capability == "model.fixture.read":
                snapshot = self.client.capture_target_snapshot()
                if (
                    snapshot.model_fixture_id != SPEC004_FIXTURE_ID
                    or snapshot.model_fixture_digest != fixture_digest(SPEC004_FIXTURE_ID)
                ):
                    return _not_ready(
                        capability,
                        "the target does not run the spec004-report-v1 fixture",
                        "start the local/test stack with CONTROLPROOF_MODEL_FIXTURE_ID=spec004-report-v1",
                    )
                return _ready(capability, "spec004-report-v1 fixture identity matches")
            if capability in _SPEC004_COMPOSED:
                return self._spec004(capability)
            if capability in {"n02.subjects.seed", "n02.subjects.teardown"}:
                return self._database(capability)
            if capability in {"consent.policy.read", "consent.commit.write"}:
                if self.n02_consent is None:
                    return _not_ready(
                        capability,
                        "N-02 consent adapter is not composed",
                        "compose the N-02 consent adapter",
                    )
                return self._route(capability, "/v1/applicant/consents")
            if capability == "consent.state.read":
                if self.n02_consent is None:
                    return _not_ready(
                        capability,
                        "N-02 consent state adapter is not composed",
                        "compose the N-02 consent adapter",
                    )
                return self._database(capability)
            if capability in {
                "consent.fault.inject",
                "consent.fault.receipt.read",
                "consent.fault.restore",
            }:
                if self.n02_fault is None:
                    return _not_ready(
                        capability,
                        "N-02 consent fault adapter is not composed",
                        "compose the N-02 consent fault adapter",
                    )
                if not self.settings.test_hooks_enabled:
                    return _not_ready(
                        capability,
                        "local/test consent fault hook is disabled",
                        "enable CONTROLPROOF_TEST_HOOKS_ENABLED only in local/test",
                    )
                try:
                    self.settings.fault_root.mkdir(parents=True, exist_ok=True)
                    probe = self.settings.fault_root / f".n02-consent-probe-{os.getpid()}"
                    probe.write_text("probe", encoding="utf-8")
                    probe.unlink()
                except OSError:
                    return CapabilityProbeResult(
                        capability,
                        ReadinessStatus.ACCESS_BLOCKED,
                        "consent fault root is not writable",
                        "grant local/test write access to CONTROLPROOF_FAULT_ROOT",
                    )
                return _ready(capability, "bounded local/test consent fault root is writable")
            if capability == "processing.paths.read":
                if self.n02_processing is None:
                    return _not_ready(
                        capability,
                        "N-02 protected-processing adapter is not composed",
                        "compose the N-02 protected-processing adapter",
                    )
                if len(self.n02_processing.paths()) != 3:
                    return _not_ready(
                        capability,
                        "the exact three protected paths are not mapped",
                        "map document, recording and assessment boundaries",
                    )
                return self._n02_worker_isolation(capability)
            if capability == "processing.document.attempt":
                if self.n02_processing is None:
                    return _not_ready(
                        capability,
                        "document attempt adapter is not composed",
                        "compose the N-02 protected-processing adapter",
                    )
                return self._route(
                    capability, "/v1/applicant/submissions/upload-intents"
                )
            if capability == "processing.recording.attempt":
                if self.n02_processing is None:
                    return _not_ready(
                        capability,
                        "recording attempt adapter is not composed",
                        "compose the N-02 protected-processing adapter",
                    )
                return self._route(capability, "/v1/applicant/interview-sessions")
            if capability in {
                "processing.assessment.attempt",
                "processing.effects.read",
            }:
                if self.n02_processing is None:
                    return _not_ready(
                        capability,
                        "N-02 database adapter is not composed",
                        "compose the N-02 protected-processing adapter",
                    )
                return self._database(capability)
            if capability == "processing.boundary.receipts.read":
                if self.n02_processing is None:
                    return _not_ready(
                        capability,
                        "processing receipt reader is not composed",
                        "compose the N-02 processing receipt reader",
                    )
                if not self.settings.observer_enabled:
                    return _not_ready(
                        capability,
                        "local processing observer is disabled",
                        "enable CONTROLPROOF_OBSERVER_ENABLED only in local/test",
                    )
                try:
                    self.settings.observer_root.mkdir(parents=True, exist_ok=True)
                    probe = self.settings.observer_root / f".controlproof-probe-{os.getpid()}"
                    probe.write_text("probe", encoding="utf-8")
                    probe.unlink()
                except OSError:
                    return CapabilityProbeResult(
                        capability,
                        ReadinessStatus.ACCESS_BLOCKED,
                        "processing observer root is not writable",
                        "grant local/test write access to CONTROLPROOF_OBSERVER_ROOT",
                    )
                return _ready(capability, "local processing receipts are readable")
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

    def _spec004(self, capability: str) -> CapabilityProbeResult:
        component, check = _SPEC004_COMPOSED[capability]
        if self.spec004.get(component) is None:
            return _not_ready(
                capability,
                f"Spec 004 {component} adapter is not composed",
                f"compose the Spec 004 {component} adapter",
            )
        if check == "database":
            return self._database(capability)
        if check == "observer":
            if not self.settings.observer_root.is_dir():
                return _not_ready(
                    capability,
                    "observer root is not readable",
                    "create CONTROLPROOF_OBSERVER_ROOT shared with the local WhyYou stack",
                )
            return _ready(capability, "observer root is readable")
        return self._route(capability, check)

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
        expected_root_digest = hashlib.sha256(
            root.resolve().as_posix().casefold().encode("utf-8")
        ).hexdigest()
        if body.get("fault_root_digest") != expected_root_digest:
            return _not_ready(
                capability,
                "configured target fault root does not match runner fault root",
                "point WhyYou and ControlProof at the same isolated fault root",
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

    def _n02_worker_isolation(self, capability: str) -> CapabilityProbeResult:
        action = "restart the isolated local worker pool with matching loopback AI endpoints"
        if not self.settings.model_substitute_enabled or self.settings.external_ai_allowed:
            return _not_ready(capability, "N-02 external AI isolation is disabled", action)
        try:
            response = self.client.http.get("/internal/controlproof/health")
            health = response.json() if response.status_code == 200 else {}
            digest = health.get("ai_isolation_digest")
            if (
                health.get("external_ai_isolated") is not True
                or health.get("model_substitute_enabled") is not True
                or health.get("fixture_id") != self.settings.model_fixture_id
                or health.get("fixture_digest") != self.settings.model_fixture_digest
                or not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
            ):
                return _not_ready(capability, "API AI isolation proof is missing or mismatched", action)
            root = self.settings.observer_root.resolve()
            session = json.loads((root / "worker-session.json").read_text(encoding="utf-8"))
            session_id = str(UUID(str(session["session_id"])))
            launcher_pid = session["launcher_pid"]
            worker_pids = session["worker_pids"]
            if (
                session.get("schema_version") != "controlproof.n02-worker-session.v1"
                or session.get("ai_isolation_digest") != digest
                or type(launcher_pid) is not int
                or launcher_pid < 1
                or not isinstance(worker_pids, list)
                or not 1 <= len(worker_pids) <= 16
                or session.get("expected_worker_count") != len(worker_pids)
                or any(type(pid) is not int or pid < 1 for pid in worker_pids)
                or len(set(worker_pids)) != len(worker_pids)
                or not _fresh_heartbeat(session.get("heartbeat_at"), max_age_seconds=5)
            ):
                return _not_ready(capability, "worker pool proof is missing or stale", action)
            directory = root / "worker-attestations"
            for pid in worker_pids:
                proof = json.loads(
                    (directory / f"{session_id}-{pid}.json").read_text(encoding="utf-8")
                )
                if (
                    proof.get("schema_version") != "controlproof.n02-worker-attestation.v1"
                    or proof.get("session_id") != session_id
                    or proof.get("launcher_pid") != launcher_pid
                    or proof.get("worker_pid") != pid
                    or proof.get("ai_isolation_digest") != digest
                    or not _fresh_heartbeat(proof.get("heartbeat_at"), max_age_seconds=30)
                ):
                    return _not_ready(capability, "worker AI isolation proof is mismatched or stale", action)
            for path in directory.glob("*.json"):
                if path.name in {f"{session_id}-{pid}.json" for pid in worker_pids}:
                    continue
                other = json.loads(path.read_text(encoding="utf-8"))
                if _fresh_heartbeat(other.get("heartbeat_at"), max_age_seconds=30):
                    return _not_ready(capability, "an unmanaged worker attestation is active", action)
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return _not_ready(capability, "worker AI isolation proof is unavailable", action)
        return _ready(capability, "API and all managed workers attest the same local AI isolation")


def _fresh_heartbeat(value: object, *, max_age_seconds: int) -> bool:
    if not isinstance(value, str):
        return False
    try:
        moment = datetime.fromisoformat(value)
        if moment.tzinfo is None:
            return False
        age = (datetime.now(UTC) - moment).total_seconds()
    except ValueError:
        return False
    return -2 <= age <= max_age_seconds


def _ready(capability: str, detail: str) -> CapabilityProbeResult:
    return CapabilityProbeResult(capability, ReadinessStatus.READY, detail)


def _not_ready(capability: str, detail: str, action: str) -> CapabilityProbeResult:
    return CapabilityProbeResult(
        capability,
        ReadinessStatus.RUNNER_NOT_READY,
        detail,
        action,
    )
