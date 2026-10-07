"""Versioned scenario definition loader and cross-reference validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from engine.models import (
    SPEC004_FIXTURE_ID,
    SPEC004_PROFILES,
    SPEC004_TIMING_POLICY,
    ComparatorPolicy,
    E01LaneId,
    E02LaneId,
    ExecutionProfile,
    FaultVariant,
    N02LaneId,
    Phase,
    ScenarioProfile,
    ScenarioSnapshot,
    canonical_json_bytes,
    sha256_bytes,
)
from engine.observations import H03_EXACT_COMPARATORS

H03_ASSERTIONS = tuple(f"H03-A{index}" for index in range(1, 7))
H03_EVIDENCE = tuple(f"EV-{index:02d}" for index in range(1, 10))
N02_CANONICAL_STEPS = (
    "capture-environment",
    "capture-path-capabilities",
    "seed-subject-lanes",
    "capture-pristine-baseline",
    "attempt-document-bypass",
    "capture-document-effects",
    "attempt-recording-boundary",
    "capture-recording-effects",
    "attempt-assessment-boundary",
    "capture-assessment-effects",
    "read-policy",
    "commit-normal-consent",
    "capture-normal-consent",
    "run-normal-processing",
    "capture-normal-causality",
    "apply-consent-fault",
    "attempt-faulted-consent",
    "read-fault-trigger",
    "capture-failed-consent-effects",
    "restore-consent-fault",
    "verify-safe-state",
    "attempt-faulted-document-path",
    "apply-fault-recording-overlay",
    "attempt-faulted-recording-path",
    "remove-fault-recording-overlay",
    "apply-fault-assessment-overlay",
    "attempt-faulted-assessment-path",
    "remove-fault-assessment-overlay",
    "verify-pristine-before-retry",
    "retry-normal-consent",
    "run-recovered-processing",
    "capture-recovered-effects",
    "teardown-subject-lanes",
)
N02_ALWAYS_RUN_STEPS = frozenset(
    {
        "restore-consent-fault",
        "verify-safe-state",
        "remove-fault-recording-overlay",
        "remove-fault-assessment-overlay",
        "verify-pristine-before-retry",
        "teardown-subject-lanes",
    }
)
N02_REQUIRED_CAPABILITIES = {
    "target.version.read": "v1",
    "target.environment.read": "v1",
    "consent.policy.read": "v1",
    "consent.commit.write": "v1",
    "consent.state.read": "v1",
    "n02.subjects.seed": "v1",
    "n02.subjects.teardown": "v1",
    "processing.paths.read": "v1",
    "processing.document.attempt": "v1",
    "processing.recording.attempt": "v1",
    "processing.assessment.attempt": "v1",
    "processing.effects.read": "v1",
    "processing.boundary.receipts.read": "v1",
    "consent.fault.inject": "v1",
    "consent.fault.receipt.read": "v1",
    "consent.fault.restore": "v1",
}


SPEC004_FIXTURE_DIGEST = "e15ec3790b64b2fba10e0caa9372f08c917edbbaa99ce308076952b838668b3f"
SPEC004_BUNDLE_PROFILE = "controlproof.bundle-profile.spec004.v1"
SPEC004_COMMON_CAPABILITIES = {
    "target.version.read": "v1",
    "target.environment.read": "v1",
    "model.fixture.read": "v1",
    "spec004.lanes.seed": "v1",
    "spec004.lanes.teardown": "v1",
    "consent.policy.read": "v1",
    "consent.commit.write": "v1",
    "consent.state.read": "v1",
    "report.generation.request": "v1",
    "report.processing.receipts.read": "v1",
    "report.records.read": "v1",
    "report.api.read": "v1",
}
E01_REQUIRED_CAPABILITIES = SPEC004_COMMON_CAPABILITIES | {
    "model.emission.read": "v1",
    "timeline.api.read": "v1",
    "evidence.segment.remove": "v1",
    "evidence.segment.restore": "v1",
    "report.axes.probe_write": "v1",
    "report.axes.probe_restore": "v1",
}
E02_REQUIRED_CAPABILITIES = SPEC004_COMMON_CAPABILITIES | {
    "criteria.version.create": "v1",
    "criteria.version.publish": "v1",
    "criteria.version.read": "v1",
    "scoring.rule.source.read": "v1",
}
E01_CANONICAL_STEPS = (
    "capture-environment",
    "capture-capabilities",
    "seed-report-lanes",
    "commit-lane-consents",
    "request-lane-reports",
    "capture-reference-report",
    "seed-citation-matrix",
    "commit-matrix-consent",
    "request-matrix-report",
    "capture-citation-cases",
    "capture-removal-baseline",
    "apply-evidence-removal",
    "capture-post-removal",
    "restore-evidence-removal",
    "verify-removal-restored",
    "capture-post-restore",
    "capture-probe-baseline",
    "apply-storage-probe",
    "capture-storage-probe-reads",
    "restore-storage-probe",
    "verify-storage-probe-restored",
    "recapture-reference-report",
    "teardown-report-lanes",
)
E01_ALWAYS_RUN_STEPS = frozenset(
    {
        "restore-evidence-removal",
        "verify-removal-restored",
        "restore-storage-probe",
        "verify-storage-probe-restored",
        "teardown-report-lanes",
    }
)
E02_CANONICAL_STEPS = (
    "capture-environment",
    "capture-capabilities",
    "capture-scoring-rule-source",
    "seed-e02-position",
    "create-publish-v1",
    "seed-first-applicant",
    "commit-first-consent",
    "request-first-report",
    "capture-pre-change",
    "recompute-first-report",
    "create-publish-v2",
    "capture-version-change",
    "seed-second-applicant",
    "commit-second-consent",
    "request-second-report",
    "capture-second-report",
    "capture-post-change",
    "recompute-second-report",
    "compare-first-report",
    "teardown-e02-position",
    "verify-other-positions-unchanged",
)
E02_ALWAYS_RUN_STEPS = frozenset({"teardown-e02-position", "verify-other-positions-unchanged"})
#: Steps a Spec 004 scenario may never contain (contracts/scenario-profile-v4.md validation rules).
SPEC004_FORBIDDEN_STEP_TERMS = (
    "n-01",
    "n-03",
    "viewport",
    "policy invalidation",
    "deletion request",
    "deletion-request",
    "published version direct",
)
SPEC004_PROFILE_RULES = {
    ExecutionProfile.E01_CITATION_EVIDENCE_V1: {
        "lanes": tuple(E01LaneId),
        "capabilities": E01_REQUIRED_CAPABILITIES,
        "steps": E01_CANONICAL_STEPS,
        "always": E01_ALWAYS_RUN_STEPS,
        "diagnostics": ("E01-D1",),
        "preconditions": frozenset({"source-clean", "fixture-spec004"}),
    },
    ExecutionProfile.E02_SCORING_FREEZE_V1: {
        "lanes": tuple(E02LaneId),
        "capabilities": E02_REQUIRED_CAPABILITIES,
        "steps": E02_CANONICAL_STEPS,
        "always": E02_ALWAYS_RUN_STEPS,
        "diagnostics": (),
        "preconditions": frozenset({"source-clean", "fixture-spec004", "scoring-source-pinned"}),
    },
}


class ScenarioError(ValueError):
    pass


class ScenarioModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Precondition(ScenarioModel):
    precondition_id: str
    kind: str
    description: str
    required: bool = True


class ScenarioStep(ScenarioModel):
    step_id: str
    phase: Phase
    action: str
    attempt_policy: dict[str, Any] = Field(default_factory=lambda: {"max_attempts": 1})
    outputs: tuple[str, ...] = ()
    evidence_requirements: tuple[str, ...] = ()
    always_run: bool = False


class AssertionDefinition(ScenarioModel):
    assertion_id: str
    description: str
    expectation: dict[str, Any]
    fail_condition: dict[str, Any] | None = None
    required_observation_keys: tuple[str, ...]
    required_evidence_ids: tuple[str, ...]
    source_requirements: tuple[str, ...]


class EvidenceRequirement(ScenarioModel):
    evidence_id: str
    description: str
    artifact_types: tuple[str, ...]


class TimingPolicy(ScenarioModel):
    poll_seconds: float = Field(gt=0)
    injected_deadline_seconds: float | None = Field(default=None, gt=0)
    automatic_decision_window_seconds: float | None = Field(default=None, gt=0)
    dlq_deadline_seconds: float | None = Field(default=None, gt=0)
    duplicate_ack_deadline_seconds: float | None = Field(default=None, gt=0)
    environment_restore_deadline_seconds: float = Field(gt=0)
    run_deadline_seconds: float | None = Field(default=None, gt=0)
    fault_ttl_seconds: float | None = Field(default=None, gt=0, le=600)
    bundle_verify_deadline_seconds: float | None = Field(default=None, gt=0)
    stability_consecutive: int = Field(ge=1)
    stability_seconds: float = Field(ge=0)
    expected_queue: dict[str, int] = Field(default_factory=dict)


class RestorePolicy(ScenarioModel):
    mandatory: bool
    action: str
    report_processing_result_field: str


class ScenarioDefinition(ScenarioModel):
    schema_version: str | None = None
    scenario_id: str
    version: str
    execution_profile: ExecutionProfile | None = None
    fault_variant: FaultVariant | None = None
    bundle_profile_contract: str | None = None
    applicable_assertion_ids: tuple[str, ...] = ()
    diagnostic_ids: tuple[str, ...] = ()
    lanes: tuple[N02LaneId | E01LaneId | E02LaneId, ...] = ()
    title: str
    control_intent: str
    required_capabilities: dict[str, str]
    preconditions: tuple[Precondition, ...]
    steps: tuple[ScenarioStep, ...]
    assertions: tuple[AssertionDefinition, ...]
    required_evidence: tuple[EvidenceRequirement, ...]
    timing_policy: TimingPolicy
    restore_policy: RestorePolicy
    observation_comparators: dict[str, ComparatorPolicy]
    source_requirements: tuple[str, ...]
    allowed_model_fixtures: dict[str, str]
    excluded_scope: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_definition(self) -> ScenarioDefinition:
        if len({step.step_id for step in self.steps}) != len(self.steps):
            raise ValueError("scenario step_id values must be unique")
        if any(version != "v1" for version in self.required_capabilities.values()):
            raise ValueError("capability contract versions must all be v1")
        assertion_ids = tuple(item.assertion_id for item in self.assertions)
        evidence_ids = tuple(item.evidence_id for item in self.required_evidence)
        if self.diagnostic_ids and self.execution_profile not in SPEC004_PROFILES:
            raise ValueError("diagnostic_ids are a Spec 004 scenario field")
        if self.execution_profile is None:
            if self.schema_version not in {None, "controlproof.scenario.v1"}:
                raise ValueError("v1 scenario has an unsupported schema_version")
            if (
                self.fault_variant is not None
                or self.applicable_assertion_ids
                or self.bundle_profile_contract is not None
                or self.lanes
                or self.diagnostic_ids
            ):
                raise ValueError("v1 scenario cannot declare partial v2 profile fields")
        elif self.execution_profile in SPEC004_PROFILES:
            self._validate_spec004(assertion_ids, evidence_ids)
        elif self.execution_profile is ExecutionProfile.N02_CONSENT_ORDER_V1:
            if self.schema_version != "controlproof.scenario.v3":
                raise ValueError("N-02 profile requires controlproof.scenario.v3")
            canonical = ScenarioProfile.canonical(self.execution_profile)
            if self.scenario_id != canonical.scenario_id or self.fault_variant is not None:
                raise ValueError("scenario_id or fault variant does not match N-02 profile")
            if self.bundle_profile_contract != "controlproof.bundle-profile.spec003.v1":
                raise ValueError("N-02 requires the Spec 003 bundle profile")
            if tuple(self.applicable_assertion_ids) != canonical.applicable_assertion_ids:
                raise ValueError("applicable assertions do not match canonical N-02 profile")
            if assertion_ids != canonical.applicable_assertion_ids:
                raise ValueError("YAML assertions do not match canonical N-02 profile")
            if evidence_ids != canonical.required_evidence:
                raise ValueError("required evidence does not match canonical N-02 profile")
            if self.lanes != tuple(N02LaneId):
                raise ValueError("N-02 lanes must match the canonical ordered six lanes")
            if self.required_capabilities != N02_REQUIRED_CAPABILITIES:
                raise ValueError("N-02 required capabilities must match the canonical registry")
            if tuple(step.step_id for step in self.steps) != N02_CANONICAL_STEPS:
                raise ValueError("N-02 ordered steps do not match the canonical contract")
            actual_always = frozenset(step.step_id for step in self.steps if step.always_run)
            if actual_always != N02_ALWAYS_RUN_STEPS:
                raise ValueError("N-02 restore and teardown always-run steps are not canonical")
            timing = self.timing_policy
            if (
                timing.poll_seconds,
                timing.stability_consecutive,
                timing.stability_seconds,
                timing.fault_ttl_seconds,
                timing.environment_restore_deadline_seconds,
                timing.run_deadline_seconds,
                timing.bundle_verify_deadline_seconds,
                timing.expected_queue,
            ) != (2, 3, 4, 600, 120, 540, 60, {}):
                raise ValueError("N-02 timing policy must match the fixed 600-second contract")
            forbidden = ("n-01", "n-03", "viewport", "policy invalidation")
            for step in self.steps:
                searchable = f"{step.step_id} {step.action}".casefold()
                if any(term in searchable for term in forbidden):
                    raise ValueError("N-01/N-03 steps are forbidden in the N-02 profile")
        else:
            if self.schema_version != "controlproof.scenario.v2":
                raise ValueError("v2 profile requires controlproof.scenario.v2")
            canonical = ScenarioProfile.canonical(self.execution_profile)
            if self.scenario_id != canonical.scenario_id:
                raise ValueError("scenario_id does not match execution profile")
            if self.fault_variant is not canonical.fault_variant:
                raise ValueError("fault_variant does not match execution profile")
            if tuple(self.applicable_assertion_ids) != canonical.applicable_assertion_ids:
                raise ValueError("applicable assertions do not match canonical profile")
            if assertion_ids != canonical.applicable_assertion_ids:
                raise ValueError("YAML assertions do not match canonical profile")
            if set(evidence_ids) != set(canonical.required_evidence):
                raise ValueError("required evidence does not match canonical profile")
            if self.timing_policy.run_deadline_seconds is None:
                raise ValueError("v2 profile requires a whole-Run deadline")
            expected_queue = self.timing_policy.expected_queue
            if expected_queue != {"max_receive_count": 3, "visibility_timeout_seconds": 5}:
                raise ValueError("v2 profile requires the canonical queue timing snapshot")
        if self.scenario_id == "H-03" and self.execution_profile is None:
            if set(assertion_ids) != set(H03_ASSERTIONS) or len(assertion_ids) != 6:
                raise ValueError("H-03 requires exactly H03-A1 through H03-A6")
            if set(evidence_ids) != set(H03_EVIDENCE) or len(evidence_ids) != 9:
                raise ValueError("H-03 requires exactly EV-01 through EV-09")
            required_keys = {
                key for assertion in self.assertions for key in assertion.required_observation_keys
            }
            missing = required_keys - set(self.observation_comparators)
            if missing:
                raise ValueError(f"H-03 comparator registry is incomplete: {sorted(missing)}")
            for key in required_keys:
                if self.observation_comparators[key].kind.value != "EXACT":
                    raise ValueError("H-03 assertion inputs must use EXACT")
            if set(self.observation_comparators) != set(H03_EXACT_COMPARATORS):
                raise ValueError("H-03 comparator registry must match the canonical key set")
        known_evidence = set(evidence_ids)
        for step in self.steps:
            unknown = set(step.evidence_requirements) - known_evidence
            if unknown:
                raise ValueError(
                    f"step {step.step_id} references unknown evidence {sorted(unknown)}"
                )
            if step.always_run and step.phase is not Phase.RECOVERED:
                raise ValueError("only RECOVERED steps may be always_run")
        for assertion in self.assertions:
            unknown = set(assertion.required_evidence_ids) - known_evidence
            if unknown:
                raise ValueError(
                    f"assertion {assertion.assertion_id} references unknown evidence {sorted(unknown)}"
                )
        if not self.restore_policy.mandatory:
            raise ValueError("fault scenario requires mandatory restore")
        if not self.allowed_model_fixtures:
            raise ValueError("fault scenario requires at least one deterministic model fixture")
        if any(len(digest) != 64 for digest in self.allowed_model_fixtures.values()):
            raise ValueError("model fixture digest must be SHA-256 lowercase hex")
        return self

    def _validate_spec004(self, assertion_ids: tuple[str, ...], evidence_ids: tuple[str, ...]) -> None:
        """Canonical E-01/E-02 contract (contracts/scenario-profile-v4.md)."""
        assert self.execution_profile is not None
        if self.schema_version != "controlproof.scenario.v4":
            raise ValueError("Spec 004 profiles require controlproof.scenario.v4")
        canonical = ScenarioProfile.canonical(self.execution_profile)
        rules = SPEC004_PROFILE_RULES[self.execution_profile]
        if self.scenario_id != canonical.scenario_id or self.fault_variant is not None:
            raise ValueError("scenario_id or fault variant does not match the Spec 004 profile")
        if self.bundle_profile_contract != SPEC004_BUNDLE_PROFILE:
            raise ValueError("Spec 004 requires the Spec 004 bundle profile")
        if tuple(self.applicable_assertion_ids) != canonical.applicable_assertion_ids:
            raise ValueError("applicable assertions do not match the canonical Spec 004 profile")
        if assertion_ids != canonical.applicable_assertion_ids:
            raise ValueError("YAML assertions do not match the canonical Spec 004 profile")
        if self.diagnostic_ids not in {(), rules["diagnostics"]}:
            raise ValueError("diagnostic_ids do not match the canonical Spec 004 profile")
        if evidence_ids != canonical.required_evidence:
            raise ValueError("required evidence does not match the profile's EV4 subset")
        if self.lanes != rules["lanes"]:
            raise ValueError("lanes must match the profile's canonical ordered lanes")
        if self.required_capabilities != rules["capabilities"]:
            raise ValueError("required capabilities must match the profile's canonical registry")
        if tuple(step.step_id for step in self.steps) != rules["steps"]:
            raise ValueError("ordered steps do not match the canonical Spec 004 contract")
        if frozenset(step.step_id for step in self.steps if step.always_run) != rules["always"]:
            raise ValueError("restore and teardown always-run steps are not canonical")
        timing = self.timing_policy
        actual = {name: getattr(timing, name) for name in SPEC004_TIMING_POLICY}
        if actual != SPEC004_TIMING_POLICY or timing.fault_ttl_seconds is not None or timing.expected_queue:
            raise ValueError("Spec 004 timing policy must match the fixed 600-second contract")
        if self.allowed_model_fixtures != {SPEC004_FIXTURE_ID: SPEC004_FIXTURE_DIGEST}:
            raise ValueError("Spec 004 allows exactly the spec004-report-v1 model fixture")
        missing = rules["preconditions"] - {item.precondition_id for item in self.preconditions}
        if missing:
            raise ValueError(f"Spec 004 preconditions missing: {', '.join(sorted(missing))}")
        for step in self.steps:
            searchable = f"{step.step_id} {step.action}".casefold()
            if any(term in searchable for term in SPEC004_FORBIDDEN_STEP_TERMS):
                raise ValueError("N-01/N-03, product deletion and direct version edits are forbidden")

    def snapshot(self) -> ScenarioSnapshot:
        spec004 = self.execution_profile in SPEC004_PROFILES
        # `diagnostic_ids` arrived with Spec 004; excluding it elsewhere keeps every earlier
        # profile's snapshot digest byte-identical.
        exclude = set() if spec004 else {"diagnostic_ids"}
        if self.execution_profile is None:
            exclude |= {
                "schema_version",
                "execution_profile",
                "fault_variant",
                "bundle_profile_contract",
                "applicable_assertion_ids",
                "lanes",
            }
        elif self.execution_profile is not ExecutionProfile.N02_CONSENT_ORDER_V1 and not spec004:
            exclude |= {"bundle_profile_contract", "lanes"}
        definition = self.model_dump(mode="json", exclude=exclude)
        if spec004:
            definition["timing_policy"].pop("fault_ttl_seconds", None)
        elif self.execution_profile is not ExecutionProfile.N02_CONSENT_ORDER_V1:
            timing = definition["timing_policy"]
            for field in ("fault_ttl_seconds", "bundle_verify_deadline_seconds"):
                timing.pop(field, None)
        if self.execution_profile is None:
            timing = definition["timing_policy"]
            for field in (
                "dlq_deadline_seconds",
                "duplicate_ack_deadline_seconds",
                "run_deadline_seconds",
                "expected_queue",
            ):
                timing.pop(field, None)
        digest = sha256_bytes(canonical_json_bytes(definition))
        return ScenarioSnapshot(
            scenario_id=self.scenario_id,
            version=self.version,
            digest=digest,
            definition=definition,
        )


def load(path: str | Path) -> ScenarioDefinition:
    source = Path(path)
    try:
        raw = yaml.safe_load(source.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ScenarioError(f"{source}: top level must be a mapping")
        return ScenarioDefinition.model_validate(raw)
    except (OSError, yaml.YAMLError, ValueError) as exc:
        if isinstance(exc, ScenarioError):
            raise
        raise ScenarioError(f"{source}: {exc}") from exc


def load_all(directory: str | Path = "scenarios") -> list[ScenarioDefinition]:
    paths = sorted(path for path in Path(directory).glob("*.yaml") if not path.name.startswith("_"))
    definitions = [load(path) for path in paths]
    identities = [
        (
            item.scenario_id,
            item.version,
            (item.execution_profile or ExecutionProfile.H03_MINIMAL_V1).value,
        )
        for item in definitions
    ]
    if len(identities) != len(set(identities)):
        raise ScenarioError("scenario_id, version, execution_profile must be unique")
    return definitions
