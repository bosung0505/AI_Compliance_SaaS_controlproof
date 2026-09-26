"""Canonical ControlProof execution, evidence, and judgement models."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
TARGET_VERSION_RE = re.compile(r"^target-snapshot:sha256:[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def utcnow() -> datetime:
    return datetime.now(UTC)


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=lambda item: item.isoformat() if isinstance(item, datetime) else str(item),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class ReadinessStatus(StrEnum):
    READY = "READY"
    RUNNER_NOT_READY = "RUNNER_NOT_READY"
    ACCESS_BLOCKED = "ACCESS_BLOCKED"
    NO_TEST_TARGET = "NO_TEST_TARGET"


class RunState(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    RESTORING = "RESTORING"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"
    RESTORE_FAILED = "RESTORE_FAILED"


TERMINAL_RUN_STATES = frozenset({RunState.COMPLETED, RunState.ABORTED, RunState.RESTORE_FAILED})


class Verdict(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"
    NOT_RUN = "NOT_RUN"


class InconclusiveReason(StrEnum):
    NO_TEST_TARGET = "NO_TEST_TARGET"
    ACCESS_LIMITED = "ACCESS_LIMITED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    EVIDENCE_CONFLICT = "EVIDENCE_CONFLICT"


class Phase(StrEnum):
    BASELINE = "BASELINE"
    INJECTED = "INJECTED"
    RECOVERED = "RECOVERED"


class Presence(StrEnum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    UNAVAILABLE = "UNAVAILABLE"


class AssertionStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"


class ImplementationStatus(StrEnum):
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    PARTIAL = "PARTIAL"
    IMPLEMENTED = "IMPLEMENTED"


class ComparatorKind(StrEnum):
    EXACT = "EXACT"
    ABSOLUTE_TOLERANCE = "ABSOLUTE_TOLERANCE"


class TargetSourceKind(StrEnum):
    GIT_WORKTREE = "GIT_WORKTREE"
    CONTAINER_IMAGE = "CONTAINER_IMAGE"
    GIT_AND_CONTAINER = "GIT_AND_CONTAINER"


class ReportProcessingRecovery(StrEnum):
    READY = "READY"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    UNAVAILABLE = "UNAVAILABLE"


class IntegrityStatus(StrEnum):
    VERIFIED = "VERIFIED"
    MISMATCH = "MISMATCH"
    MISSING = "MISSING"


class Source(StrEnum):
    HTTP = "HTTP"
    API = "HTTP"  # compatibility alias for the initial skeleton
    BROWSER = "BROWSER"
    DB = "DB"
    LOG = "LOG"
    FAULT = "FAULT"
    SYSTEM = "SYSTEM"
    SEED = "SEED"
    MAIL = "MAIL"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", use_enum_values=False)


class ComparatorPolicy(FrozenModel):
    kind: ComparatorKind = ComparatorKind.EXACT
    value_type: str
    tolerance: float | None = None

    @model_validator(mode="after")
    def validate_policy(self) -> ComparatorPolicy:
        if self.value_type not in {"string", "integer", "boolean", "decimal", "datetime"}:
            raise ValueError("unsupported comparator value_type")
        if self.kind is ComparatorKind.EXACT and self.tolerance is not None:
            raise ValueError("EXACT comparator cannot declare tolerance")
        if self.kind is ComparatorKind.ABSOLUTE_TOLERANCE:
            if self.value_type not in {"integer", "decimal", "datetime"}:
                raise ValueError("ABSOLUTE_TOLERANCE supports numeric or datetime values only")
            if self.tolerance is None or self.tolerance < 0:
                raise ValueError("ABSOLUTE_TOLERANCE requires non-negative tolerance")
        return self


class ScenarioSnapshot(FrozenModel):
    scenario_id: str
    version: str
    digest: str
    definition: dict[str, Any]

    @field_validator("digest")
    @classmethod
    def valid_digest(cls, value: str) -> str:
        if not SHA256_RE.fullmatch(value):
            raise ValueError("scenario digest must be 64 lowercase hex characters")
        return value


class TargetSnapshot(FrozenModel):
    schema_version: str = "controlproof.target-snapshot.v1"
    target_id: str
    source_kind: TargetSourceKind
    git_commit_sha: str | None = None
    git_dirty: bool | None = None
    git_diff_digest: str | None = None
    container_image_digests: dict[str, str] = Field(default_factory=dict)
    openapi_digest: str
    schema_migration_head: str
    schema_signature_digest: str
    model_fixture_id: str
    model_fixture_digest: str
    captured_at: datetime = Field(default_factory=utcnow)
    target_version: str | None = None

    @model_validator(mode="after")
    def validate_and_digest(self) -> TargetSnapshot:
        has_git = self.source_kind in {
            TargetSourceKind.GIT_WORKTREE,
            TargetSourceKind.GIT_AND_CONTAINER,
        }
        has_images = self.source_kind in {
            TargetSourceKind.CONTAINER_IMAGE,
            TargetSourceKind.GIT_AND_CONTAINER,
        }
        if has_git:
            if not self.git_commit_sha or not GIT_SHA_RE.fullmatch(self.git_commit_sha):
                raise ValueError("git source requires a 40-character lowercase commit SHA")
            if self.git_dirty is None:
                raise ValueError("git source requires git_dirty")
            if self.git_dirty and not _is_sha(self.git_diff_digest):
                raise ValueError("dirty git source requires git_diff_digest")
            if not self.git_dirty and self.git_diff_digest is not None:
                raise ValueError("clean git source requires git_diff_digest=null")
        elif any(
            value is not None
            for value in (self.git_commit_sha, self.git_dirty, self.git_diff_digest)
        ):
            raise ValueError("container-only source cannot contain git identity")
        if has_images:
            required = {"backend", "reporting-worker", "company-console"}
            if set(self.container_image_digests) != required:
                raise ValueError("container source requires exactly three canonical components")
            if any(not _is_prefixed_sha(value) for value in self.container_image_digests.values()):
                raise ValueError("container image digest must use sha256:<64 lowercase hex>")
        elif self.container_image_digests:
            raise ValueError("git-only source cannot contain container image digests")
        for name in ("openapi_digest", "schema_signature_digest", "model_fixture_digest"):
            if not _is_sha(getattr(self, name)):
                raise ValueError(f"{name} must be 64 lowercase hex characters")
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must be timezone-aware")
        expected = f"target-snapshot:sha256:{sha256_bytes(canonical_json_bytes(self.identity()))}"
        if self.target_version is not None and self.target_version != expected:
            raise ValueError("target_version does not match canonical identity digest")
        object.__setattr__(self, "target_version", expected)
        return self

    def identity(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"captured_at", "target_version"})


def _is_sha(value: str | None) -> bool:
    return bool(value and SHA256_RE.fullmatch(value))


def _is_prefixed_sha(value: str) -> bool:
    return value.startswith("sha256:") and _is_sha(value.removeprefix("sha256:"))


class Run(FrozenModel):
    run_id: UUID = Field(default_factory=uuid4)
    scenario_id: str
    scenario_version: str
    scenario_digest: str
    target_id: str
    target_version: str
    model_fixture_id: str
    model_fixture_digest: str
    state: RunState = RunState.PENDING
    started_at: datetime | None = None
    ended_at: datetime | None = None
    seed_kind: str = "h03_pending_report_v1"
    fault_kind: str = "reporting_handler_timeout_v1"
    parent_run_id: UUID | None = None
    operator_id: str = "local-operator"
    label: str | None = None
    fault_ever_applied: bool = False
    manual_cleanup_required: bool = False
    implementation_status: ImplementationStatus = ImplementationStatus.IMPLEMENTED

    @model_validator(mode="after")
    def validate_run(self) -> Run:
        if self.implementation_status is not ImplementationStatus.IMPLEMENTED:
            raise ValueError("created Run must snapshot IMPLEMENTED status")
        if not _is_sha(self.scenario_digest):
            raise ValueError("scenario_digest must be 64 lowercase hex characters")
        if not TARGET_VERSION_RE.fullmatch(self.target_version):
            raise ValueError("target_version must be a canonical TargetSnapshot digest")
        if not _is_sha(self.model_fixture_digest):
            raise ValueError("model_fixture_digest must be 64 lowercase hex characters")
        if self.parent_run_id == self.run_id:
            raise ValueError("Run cannot be its own parent")
        if self.label is not None and (not self.label.strip() or len(self.label) > 100):
            raise ValueError("Run label must contain 1-100 characters")
        if self.state is RunState.PENDING and self.started_at is not None:
            raise ValueError("PENDING Run cannot have started_at")
        if self.state is not RunState.PENDING and self.started_at is None:
            raise ValueError("non-PENDING Run requires started_at")
        if self.state in TERMINAL_RUN_STATES and self.ended_at is None:
            raise ValueError("terminal Run requires ended_at")
        if self.state not in TERMINAL_RUN_STATES and self.ended_at is not None:
            raise ValueError("non-terminal Run cannot have ended_at")
        if self.state is RunState.RESTORE_FAILED and not self.manual_cleanup_required:
            raise ValueError("RESTORE_FAILED requires manual_cleanup_required=true")
        return self


class TestSubject(FrozenModel):
    subject_ref: str
    subject_type: str = "synthetic_applicant"
    synthetic: bool = True
    locators: dict[str, str]
    initial_state_digest: str
    seed_correlation_id: str

    @model_validator(mode="after")
    def synthetic_only(self) -> TestSubject:
        if not self.synthetic or not _is_sha(self.initial_state_digest):
            raise ValueError("Spec 001 requires a synthetic subject and valid initial digest")
        return self


class FaultCondition(FrozenModel):
    fault_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    subject_ref: str
    fault_kind: str = "reporting_handler_timeout_v1"
    target_locator: dict[str, str]
    requested_at: datetime
    applied_at: datetime | None = None
    effect_observed_at: datetime | None = None
    effect_receipt_locator: str | None = None
    expires_at: datetime
    restored_at: datetime | None = None
    apply_success: bool | None = None
    effect_confirmed: bool | None = None
    environment_restore_success: bool | None = None
    report_processing_recovery: ReportProcessingRecovery | None = None
    actor_ref: str = "controlproof-runner"


class Observation(FrozenModel):
    schema_version: str = "controlproof.observation.v1"
    observation_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    subject_ref: str
    phase: Phase
    step_id: str
    attempt: int = Field(ge=1)
    key: str
    presence: Presence
    value: Any = None
    source_type: Source
    source_ref: str
    observed_at: datetime = Field(default_factory=utcnow)
    artifact_ids: tuple[UUID, ...] = ()
    error_code: str | None = None

    @model_validator(mode="after")
    def validate_presence(self) -> Observation:
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        if self.presence is Presence.PRESENT and self.value is None:
            raise ValueError("PRESENT observation requires value")
        if self.presence is not Presence.PRESENT and self.value is not None:
            raise ValueError("ABSENT/UNAVAILABLE observation value must be null")
        if self.presence is Presence.UNAVAILABLE and not self.error_code:
            raise ValueError("UNAVAILABLE observation requires error_code")
        if self.presence is not Presence.UNAVAILABLE and self.error_code is not None:
            raise ValueError("only UNAVAILABLE observation may have error_code")
        return self

    @property
    def dimension(self) -> tuple[UUID, str, Phase, str, int, str]:
        return (
            self.run_id,
            self.subject_ref,
            self.phase,
            self.step_id,
            self.attempt,
            self.key,
        )


class EvidenceArtifact(FrozenModel):
    schema_version: str = "controlproof.artifact.v1"
    artifact_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    subject_ref: str
    phase: Phase
    step_id: str
    attempt: int = Field(ge=1)
    evidence_requirement_ids: tuple[str, ...]
    artifact_type: str
    relative_path: str
    source_locator: dict[str, Any]
    captured_at: datetime = Field(default_factory=utcnow)
    mime_type: str
    size_bytes: int = Field(ge=0)
    sha256: str
    redaction_profile: str = "controlproof-redaction-v1"
    integrity_status: IntegrityStatus = IntegrityStatus.VERIFIED

    @model_validator(mode="after")
    def validate_artifact(self) -> EvidenceArtifact:
        path = PurePosixPath(self.relative_path.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("artifact relative_path must remain within the Run root")
        if not self.evidence_requirement_ids or not _is_sha(self.sha256):
            raise ValueError("artifact requires evidence IDs and a valid SHA-256")
        return self


class AssertionResult(FrozenModel):
    assertion_id: str
    subject_ref: str
    status: AssertionStatus
    expected: Any
    actual: Any
    observation_ids: tuple[UUID, ...] = ()
    artifact_ids: tuple[UUID, ...] = ()
    reason_code: InconclusiveReason | None = None
    detail: str
    source_requirements: tuple[str, ...] = ()

    @model_validator(mode="after")
    def require_reason_for_inconclusive(self) -> AssertionResult:
        if self.status is AssertionStatus.INCONCLUSIVE and self.reason_code is None:
            raise ValueError("INCONCLUSIVE assertion requires reason_code")
        if self.status is not AssertionStatus.INCONCLUSIVE and self.reason_code is not None:
            raise ValueError("only INCONCLUSIVE assertion may have reason_code")
        return self


class Finding(FrozenModel):
    code: str
    severity: str
    detail: str
    assertion_id: str | None = None
    artifact_ids: tuple[UUID, ...] = ()


class Judgement(FrozenModel):
    run_id: UUID
    scenario_id: str
    verdict: Verdict
    reason_code: InconclusiveReason | None = None
    assertion_results: tuple[AssertionResult, ...] = ()
    findings: tuple[Finding, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    unverified_scope: tuple[str, ...] = ()
    summary: str
    decided_at: datetime = Field(default_factory=utcnow)
    engine_version: str = "0.1.0"

    @model_validator(mode="after")
    def validate_judgement(self) -> Judgement:
        if self.verdict is Verdict.NOT_RUN:
            raise ValueError("NOT_RUN cannot be stored for a created Run")
        if self.verdict is Verdict.INCONCLUSIVE and self.reason_code is None:
            raise ValueError("INCONCLUSIVE judgement requires reason_code")
        if self.verdict is not Verdict.INCONCLUSIVE and self.reason_code is not None:
            raise ValueError("only INCONCLUSIVE judgement may have reason_code")
        return self


class RetestLink(FrozenModel):
    parent_run_id: UUID
    child_run_id: UUID
    changed_dimensions: dict[str, Any]
    reason: str
    created_at: datetime = Field(default_factory=utcnow)

    @model_validator(mode="after")
    def prevent_self_link(self) -> RetestLink:
        if self.parent_run_id == self.child_run_id:
            raise ValueError("retest child must differ from parent")
        return self


class ReadinessCheck(FrozenModel):
    capability: str
    status: ReadinessStatus
    detail: str
    operator_action: str | None = None


class ScenarioReadiness(FrozenModel):
    scenario_id: str
    scenario_version: str
    target_id: str
    implementation_status: ImplementationStatus
    status: ReadinessStatus
    checks: tuple[ReadinessCheck, ...]
    checked_at: datetime = Field(default_factory=utcnow)
    target_version: str | None = None
    target_snapshot: TargetSnapshot | None = None
    model_fixture_id: str | None = None
    model_fixture_digest: str | None = None
    operator_action: str | None = None

    @model_validator(mode="after")
    def validate_readiness(self) -> ScenarioReadiness:
        if self.status is ReadinessStatus.READY:
            if self.implementation_status is not ImplementationStatus.IMPLEMENTED:
                raise ValueError("READY requires IMPLEMENTED")
            if (
                self.target_snapshot is None
                or self.target_version != self.target_snapshot.target_version
            ):
                raise ValueError("READY requires linked canonical TargetSnapshot")
            if not self.model_fixture_id or not _is_sha(self.model_fixture_digest):
                raise ValueError("READY H-03 requires deterministic model fixture identity")
        elif not self.operator_action:
            raise ValueError("non-READY result requires operator_action")
        return self


class RuleResult(FrozenModel):
    """Compatibility result for the generic rule evaluator used by non-H03 spikes."""

    rule_type: str
    passed: bool | None
    detail: str
    used_keys: tuple[str, ...] = ()
    missing_keys: tuple[str, ...] = ()


class EvidenceBundle(FrozenModel):
    run: Run
    observations: tuple[Observation, ...]
    judgement: Judgement
    artifacts: tuple[EvidenceArtifact, ...] = ()
