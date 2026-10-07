"""Canonical ControlProof execution, evidence, and judgement models."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any, Literal
from urllib.parse import urlparse
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


class ExecutionProfile(StrEnum):
    H03_MINIMAL_V1 = "H03_MINIMAL_V1"
    H03_DLQ_V2 = "H03_DLQ_V2"
    E03_BEFORE_V2 = "E03_BEFORE_V2"
    E03_AFTER_V2 = "E03_AFTER_V2"
    N02_CONSENT_ORDER_V1 = "N02_CONSENT_ORDER_V1"


class FaultVariant(StrEnum):
    BEFORE_RESULT_DURABLE = "BEFORE_RESULT_DURABLE"
    AFTER_RESULT_DURABLE_BEFORE_COMPLETION = "AFTER_RESULT_DURABLE_BEFORE_COMPLETION"


class EnvironmentKind(StrEnum):
    LOCAL_EMULATED = "LOCAL_EMULATED"


class AwsDeploymentStatus(StrEnum):
    NOT_RUN = "NOT_RUN"


class DeliveryAttemptOutcome(StrEnum):
    FAULT_TRIGGERED = "FAULT_TRIGGERED"
    COMMITTED_ACK_DROPPED = "COMMITTED_ACK_DROPPED"
    DUPLICATE_ACK = "DUPLICATE_ACK"
    COMPLETED = "COMPLETED"


class TerminalFailureRoute(StrEnum):
    APPLICATION_DLQ = "APPLICATION_DLQ"
    INFRASTRUCTURE_DLQ = "INFRASTRUCTURE_DLQ"
    TRACEABLE_FAILED_STATE = "TRACEABLE_FAILED_STATE"


class FaultBoundary(StrEnum):
    BEFORE_REPORT_SIDE_EFFECT = "BEFORE_REPORT_SIDE_EFFECT"
    AFTER_DB_COMMIT_BEFORE_SQS_ACK = "AFTER_DB_COMMIT_BEFORE_SQS_ACK"


class DecisionPathId(StrEnum):
    FINAL_DECISION = "FINAL_DECISION"
    BATCH_MOVE_FINAL_ACCEPT = "BATCH_MOVE_FINAL_ACCEPT"
    BATCH_MOVE_FINAL_REJECT = "BATCH_MOVE_FINAL_REJECT"


class EffectGroup(StrEnum):
    REPORTING = "REPORTING"
    DECISION = "DECISION"


class N02LaneId(StrEnum):
    PRISTINE_BASELINE = "PRISTINE_BASELINE"
    DOCUMENT_BYPASS = "DOCUMENT_BYPASS"
    RECORDING_BOUNDARY_PROBE = "RECORDING_BOUNDARY_PROBE"
    ASSESSMENT_BOUNDARY_PROBE = "ASSESSMENT_BOUNDARY_PROBE"
    NORMAL_ORDER = "NORMAL_ORDER"
    CONSENT_FAULT_RECOVERY = "CONSENT_FAULT_RECOVERY"


class BaselineKind(StrEnum):
    PRISTINE = "PRISTINE"
    PREREQUISITE_FIXTURE = "PREREQUISITE_FIXTURE"


class ProtectedPathId(StrEnum):
    DOCUMENT_ANALYSIS = "DOCUMENT_ANALYSIS"
    RECORDING = "RECORDING"
    AI_ASSESSMENT = "AI_ASSESSMENT"


class N02EffectGroup(StrEnum):
    DOCUMENT_ANALYSIS = "DOCUMENT_ANALYSIS"
    RECORDING = "RECORDING"
    AI_ASSESSMENT = "AI_ASSESSMENT"


class ProcessingEntryKind(StrEnum):
    HTTP = "HTTP"
    WEBSOCKET = "WEBSOCKET"
    DOMAIN_EVENT = "DOMAIN_EVENT"


class ProcessingResponseClass(StrEnum):
    ACCEPTED = "ACCEPTED"
    SUBMITTED = "SUBMITTED"
    DENIED = "DENIED"
    ERROR = "ERROR"
    NO_RESPONSE = "NO_RESPONSE"


class ConsentPurpose(StrEnum):
    DOCUMENT_ANALYSIS = "document_analysis"
    RECORDING = "recording"
    AI_ASSESSMENT = "ai_assessment"


class CausalEventKind(StrEnum):
    POLICY_RECEIVED = "POLICY_RECEIVED"
    CONSENT_REQUESTED = "CONSENT_REQUESTED"
    CONSENT_COMMITTED = "CONSENT_COMMITTED"
    PROCESSING_REQUESTED = "PROCESSING_REQUESTED"
    PROCESSING_STARTED = "PROCESSING_STARTED"
    RESULT_CREATED = "RESULT_CREATED"


class CausalRelation(StrEnum):
    PROGRAM_ORDER = "PROGRAM_ORDER"
    SAME_TRANSACTION = "SAME_TRANSACTION"
    EMITTED = "EMITTED"
    HANDLED = "HANDLED"
    PRODUCED = "PRODUCED"


class CausalEdgeStatus(StrEnum):
    PROVEN = "PROVEN"
    UNAVAILABLE = "UNAVAILABLE"
    CONFLICTING = "CONFLICTING"


class ConsentFaultVariant(StrEnum):
    AFTER_CONSENT_RECORD_BEFORE_STATE = "AFTER_CONSENT_RECORD_BEFORE_STATE"


class ConsentFaultBoundary(StrEnum):
    AFTER_CONSENT_RECORD_BEFORE_INVITATION_STATE = (
        "AFTER_CONSENT_RECORD_BEFORE_INVITATION_STATE"
    )


class ConsentFaultLifecycle(StrEnum):
    REQUESTED = "REQUESTED"
    APPLIED = "APPLIED"
    TRIGGERED = "TRIGGERED"
    RESTORING = "RESTORING"
    RESTORED = "RESTORED"
    RESTORE_FAILED = "RESTORE_FAILED"


class RecoveryStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    UNVERIFIED = "UNVERIFIED"


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


SPEC002_UNVERIFIED_SCOPE = frozenset(
    {"AWS_SQS", "AWS_ECS", "AWS_IAM", "AWS_CLOUDWATCH", "AWS_NETWORK"}
)
SPEC003_UNVERIFIED_SCOPE = frozenset({"AWS", "N-01", "N-03"})


class ScenarioProfile(FrozenModel):
    execution_profile: ExecutionProfile
    scenario_id: str
    scenario_version: str
    fault_variant: FaultVariant | None
    applicable_assertion_ids: tuple[str, ...]
    required_capabilities: dict[str, str] = Field(default_factory=dict)
    required_evidence: tuple[str, ...]
    timing_policy: dict[str, Any] = Field(default_factory=dict)
    snapshot_digest: str | None = None

    @classmethod
    def canonical(cls, profile: ExecutionProfile) -> ScenarioProfile:
        timing = {
            "poll_seconds": 2,
            "dlq_deadline_seconds": 360,
            "duplicate_ack_deadline_seconds": 60,
            "environment_restore_deadline_seconds": 180,
            "run_deadline_seconds": 600,
            "stability_consecutive": 3,
            "stability_seconds": 4,
            "expected_queue": {"max_receive_count": 3, "visibility_timeout_seconds": 5},
        }
        if profile is ExecutionProfile.H03_MINIMAL_V1:
            return cls(
                execution_profile=profile,
                scenario_id="H-03",
                scenario_version="1.0.0",
                fault_variant=None,
                applicable_assertion_ids=tuple(f"H03-A{i}" for i in range(1, 7)),
                required_evidence=tuple(f"EV-{i:02d}" for i in range(1, 10)),
                timing_policy={},
            )
        if profile is ExecutionProfile.H03_DLQ_V2:
            evidence = tuple(f"EV-{i:02d}" for i in range(1, 10)) + (
                *(f"EV2-{i:02d}" for i in range(1, 10)),
                "EV2-12",
            )
            return cls(
                execution_profile=profile,
                scenario_id="H-03",
                scenario_version="2.0.0",
                fault_variant=FaultVariant.BEFORE_RESULT_DURABLE,
                applicable_assertion_ids=tuple(f"H03-A{i}" for i in range(1, 10)),
                required_evidence=evidence,
                timing_policy=timing,
            )
        if profile is ExecutionProfile.E03_BEFORE_V2:
            return cls(
                execution_profile=profile,
                scenario_id="E-03",
                scenario_version="2.0.0",
                fault_variant=FaultVariant.BEFORE_RESULT_DURABLE,
                applicable_assertion_ids=(
                    "E03-A1",
                    "E03-A2",
                    "E03-A3",
                    "E03-A4",
                    "E03-A7",
                    "E03-A8",
                ),
                required_evidence=(
                    *(f"EV2-{i:02d}" for i in range(1, 6)),
                    *(f"EV2-{i:02d}" for i in range(9, 13)),
                ),
                timing_policy=timing,
            )
        if profile is ExecutionProfile.N02_CONSENT_ORDER_V1:
            return cls(
                execution_profile=profile,
                scenario_id="N-02",
                scenario_version="1.0.0",
                fault_variant=None,
                applicable_assertion_ids=tuple(f"N02-A{i}" for i in range(1, 8)),
                required_evidence=tuple(f"EV3-{i:02d}" for i in range(1, 11)),
                timing_policy={
                    "poll_seconds": 2,
                    "stability_consecutive": 3,
                    "stability_seconds": 4,
                    "fault_ttl_seconds": 600,
                    "environment_restore_deadline_seconds": 120,
                    "run_deadline_seconds": 540,
                    "bundle_verify_deadline_seconds": 60,
                },
            )
        return cls(
            execution_profile=profile,
            scenario_id="E-03",
            scenario_version="2.0.0",
            fault_variant=FaultVariant.AFTER_RESULT_DURABLE_BEFORE_COMPLETION,
            applicable_assertion_ids=("E03-A1", "E03-A5", "E03-A6", "E03-A8"),
            required_evidence=(
                "EV2-01",
                "EV2-02",
                "EV2-03",
                "EV2-04",
                "EV2-09",
                "EV2-10",
                "EV2-12",
            ),
            timing_policy=timing,
        )

    @model_validator(mode="after")
    def validate_canonical_profile(self) -> ScenarioProfile:
        if not re.fullmatch(r"\d+\.\d+\.\d+", self.scenario_version):
            raise ValueError("scenario_version must be semantic versioning")
        canonical = {
            ExecutionProfile.H03_MINIMAL_V1: ("H-03", None, tuple(f"H03-A{i}" for i in range(1, 7))),
            ExecutionProfile.H03_DLQ_V2: (
                "H-03",
                FaultVariant.BEFORE_RESULT_DURABLE,
                tuple(f"H03-A{i}" for i in range(1, 10)),
            ),
            ExecutionProfile.E03_BEFORE_V2: (
                "E-03",
                FaultVariant.BEFORE_RESULT_DURABLE,
                ("E03-A1", "E03-A2", "E03-A3", "E03-A4", "E03-A7", "E03-A8"),
            ),
            ExecutionProfile.E03_AFTER_V2: (
                "E-03",
                FaultVariant.AFTER_RESULT_DURABLE_BEFORE_COMPLETION,
                ("E03-A1", "E03-A5", "E03-A6", "E03-A8"),
            ),
            ExecutionProfile.N02_CONSENT_ORDER_V1: (
                "N-02",
                None,
                tuple(f"N02-A{i}" for i in range(1, 8)),
            ),
        }[self.execution_profile]
        if (self.scenario_id, self.fault_variant, self.applicable_assertion_ids) != canonical:
            raise ValueError("profile scenario, fault variant, or assertion ownership is not canonical")
        if len(set(self.applicable_assertion_ids)) != len(self.applicable_assertion_ids):
            raise ValueError("applicable assertion IDs must be unique")
        if len(set(self.required_evidence)) != len(self.required_evidence):
            raise ValueError("required evidence IDs must be unique")
        identity = self.model_dump(mode="json", exclude={"snapshot_digest"})
        digest = sha256_bytes(canonical_json_bytes(identity))
        if self.snapshot_digest is not None and self.snapshot_digest != digest:
            raise ValueError("profile snapshot_digest does not match canonical identity")
        object.__setattr__(self, "snapshot_digest", digest)
        return self


class GitIdentity(FrozenModel):
    commit_sha: str
    dirty: bool
    diff_digest: str | None = None

    @model_validator(mode="after")
    def validate_git_identity(self) -> GitIdentity:
        if not GIT_SHA_RE.fullmatch(self.commit_sha):
            raise ValueError("commit_sha must be a 40-character lowercase git SHA")
        if self.dirty and not _is_sha(self.diff_digest):
            raise ValueError("dirty checkout requires diff_digest")
        if not self.dirty and self.diff_digest is not None:
            raise ValueError("clean checkout cannot have diff_digest")
        return self


class TargetEnvironmentSnapshot(FrozenModel):
    schema_version: str = "controlproof.environment-snapshot.v1"
    target_id: str
    environment_kind: EnvironmentKind
    host_os: str
    controlproof_commit: GitIdentity
    whyyou_commit: GitIdentity
    components: dict[str, str]
    endpoints: dict[str, str]
    model_fixture_id: str
    model_fixture_digest: str
    external_ai_allowed: bool
    aws_deployment_status: AwsDeploymentStatus
    unverified_scope: tuple[str, ...]
    captured_at: datetime = Field(default_factory=utcnow)
    snapshot_digest: str | None = None

    @model_validator(mode="after")
    def validate_environment(self) -> TargetEnvironmentSnapshot:
        if self.target_id != "whyyou-local" or self.environment_kind is not EnvironmentKind.LOCAL_EMULATED:
            raise ValueError("Spec 002 official environment must be whyyou-local/LOCAL_EMULATED")
        if self.external_ai_allowed:
            raise ValueError("external AI must be disabled")
        if self.aws_deployment_status is not AwsDeploymentStatus.NOT_RUN:
            raise ValueError("local environment requires AWS deployment status NOT_RUN")
        if set(self.unverified_scope) not in (
            SPEC002_UNVERIFIED_SCOPE,
            SPEC003_UNVERIFIED_SCOPE,
        ):
            raise ValueError("local environment must declare an exact profile-owned scope")
        if not _is_sha(self.model_fixture_digest):
            raise ValueError("model fixture digest must be lowercase SHA-256")
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must be timezone-aware")
        allowlisted = {"localhost", "127.0.0.1", "host.docker.internal", "postgres", "localstack", "mailpit"}
        for name, endpoint in self.endpoints.items():
            parsed = urlparse(endpoint.replace("postgresql+psycopg", "postgresql", 1))
            if parsed.hostname not in allowlisted or parsed.username or parsed.password or parsed.query:
                raise ValueError(f"endpoint {name} must be secret-free and local")
        identity = self.model_dump(mode="json", exclude={"captured_at", "snapshot_digest"})
        digest = sha256_bytes(canonical_json_bytes(identity))
        if self.snapshot_digest is not None and self.snapshot_digest != digest:
            raise ValueError("environment snapshot digest mismatch")
        object.__setattr__(self, "snapshot_digest", digest)
        return self


class QueueTopologySnapshot(FrozenModel):
    schema_version: str = "controlproof.queue-topology.v1"
    source_queue_name: str
    source_queue_url_digest: str
    dead_letter_queue_name: str
    dead_letter_queue_arn: str
    max_receive_count: int
    visibility_timeout_seconds: int
    source_retention_seconds: int
    dlq_retention_seconds: int
    redrive_policy_digest: str
    captured_at: datetime = Field(default_factory=utcnow)
    snapshot_digest: str | None = None

    @model_validator(mode="after")
    def validate_topology(self) -> QueueTopologySnapshot:
        if self.source_queue_name != "iep-reporting" or self.dead_letter_queue_name != "iep-reporting-dlq":
            raise ValueError("official reporting queue topology is required")
        if self.max_receive_count != 3:
            raise ValueError("max receive count must be 3")
        if self.visibility_timeout_seconds != 5:
            raise ValueError("visibility timeout must be 5 seconds")
        if self.dlq_retention_seconds <= self.source_retention_seconds:
            raise ValueError("DLQ retention must exceed source retention")
        if not _is_sha(self.source_queue_url_digest) or not _is_sha(self.redrive_policy_digest):
            raise ValueError("queue and redrive digests must be lowercase SHA-256")
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must be timezone-aware")
        identity = self.model_dump(mode="json", exclude={"captured_at", "snapshot_digest"})
        digest = sha256_bytes(canonical_json_bytes(identity))
        if self.snapshot_digest is not None and self.snapshot_digest != digest:
            raise ValueError("queue topology snapshot digest mismatch")
        object.__setattr__(self, "snapshot_digest", digest)
        return self


class DeliveryAttemptRecord(FrozenModel):
    schema_version: str = "controlproof.delivery-attempt.v1"
    run_id: UUID
    subject_ref: str
    source_event_id: UUID
    consumer_name: str
    delivery_attempt: int = Field(ge=1)
    fault_variant: FaultVariant
    outcome: DeliveryAttemptOutcome
    observed_at: datetime
    receipt_artifact_id: UUID

    @model_validator(mode="after")
    def validate_attempt(self) -> DeliveryAttemptRecord:
        if self.consumer_name != "reporting-worker":
            raise ValueError("Spec 002 delivery attempts belong to reporting-worker")
        if not self.subject_ref.strip():
            raise ValueError("delivery attempt requires subject_ref")
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        expected = {
            FaultVariant.BEFORE_RESULT_DURABLE: {DeliveryAttemptOutcome.FAULT_TRIGGERED},
            FaultVariant.AFTER_RESULT_DURABLE_BEFORE_COMPLETION: {
                DeliveryAttemptOutcome.COMMITTED_ACK_DROPPED,
                DeliveryAttemptOutcome.DUPLICATE_ACK,
                DeliveryAttemptOutcome.COMPLETED,
            },
        }[self.fault_variant]
        if self.outcome not in expected:
            raise ValueError("delivery outcome does not match the selected fault variant")
        return self


class TerminalFailureRecord(FrozenModel):
    schema_version: str = "controlproof.terminal-failure.v1"
    route_type: TerminalFailureRoute
    route_locator: str
    source_event_id: UUID
    subject_ref: str
    last_delivery_attempt: int = Field(ge=1)
    last_failure_code: str
    message_body_digest: str
    observed_at: datetime

    @field_validator("message_body_digest")
    @classmethod
    def validate_message_digest(cls, value: str) -> str:
        if not _is_sha(value):
            raise ValueError("message body digest must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_terminal_failure(self) -> TerminalFailureRecord:
        if self.route_type is not TerminalFailureRoute.INFRASTRUCTURE_DLQ:
            raise ValueError("official Spec 002 target uses the infrastructure DLQ")
        if self.route_locator != "localstack:sqs:iep-reporting-dlq":
            raise ValueError("terminal failure must identify the official LocalStack DLQ")
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        return self


class FaultBoundaryReceipt(FrozenModel):
    schema_version: str = "controlproof.whyyou-fault-receipt.v2"
    run_id: UUID
    session_id: UUID
    outbox_event_id: UUID
    delivery_attempt: int = Field(ge=1)
    fault_variant: FaultVariant
    boundary: FaultBoundary
    triggered_at: datetime
    one_shot_consumed: bool

    @model_validator(mode="after")
    def validate_boundary(self) -> FaultBoundaryReceipt:
        expected = (
            FaultBoundary.BEFORE_REPORT_SIDE_EFFECT
            if self.fault_variant is FaultVariant.BEFORE_RESULT_DURABLE
            else FaultBoundary.AFTER_DB_COMMIT_BEFORE_SQS_ACK
        )
        if self.boundary is not expected:
            raise ValueError("fault variant and boundary do not match")
        if self.fault_variant is FaultVariant.AFTER_RESULT_DURABLE_BEFORE_COMPLETION and not self.one_shot_consumed:
            raise ValueError("AFTER boundary must consume its one-shot marker")
        if self.triggered_at.tzinfo is None:
            raise ValueError("triggered_at must be timezone-aware")
        return self


class DecisionPathCapability(FrozenModel):
    path_id: DecisionPathId
    operation_id: str
    target_stage_id: UUID
    target_stage_name: str
    expected_effects: frozenset[str] = frozenset()
    source_commit: str

    @model_validator(mode="after")
    def validate_decision_path(self) -> DecisionPathCapability:
        if self.target_stage_name not in {"최종합격", "불합격"}:
            raise ValueError("decision path target must be a final stage")
        if not GIT_SHA_RE.fullmatch(self.source_commit):
            raise ValueError("source_commit must be a git SHA")
        return self


class BusinessEffectSnapshot(FrozenModel):
    schema_version: str = "controlproof.effect-snapshot.v1"
    run_id: UUID
    subject_ref: str
    phase: Phase
    step_id: str
    attempt: int = Field(ge=1)
    logical_operation_id: UUID
    source_event_id: UUID
    effect_group: EffectGroup
    effects: dict[str, Any]
    state_digest: str
    captured_at: datetime
    source_status: Presence
    source_error_code: str | None = None

    @model_validator(mode="after")
    def validate_effect(self) -> BusinessEffectSnapshot:
        if not _is_sha(self.state_digest):
            raise ValueError("effect state_digest must be lowercase SHA-256")
        if self.source_status is Presence.UNAVAILABLE and not self.source_error_code:
            raise ValueError("UNAVAILABLE effect source requires error code")
        if self.source_status is not Presence.UNAVAILABLE and self.source_error_code is not None:
            raise ValueError("only UNAVAILABLE effect source may have error code")
        if self.source_status is Presence.UNAVAILABLE and self.effects:
            raise ValueError("UNAVAILABLE effect snapshots cannot claim effects")
        if self.source_status is Presence.ABSENT and any(
            bool(value) for value in self.effects.values()
        ):
            raise ValueError("ABSENT effect snapshots cannot contain present identities")
        if self.source_status is Presence.PRESENT and not self.effects:
            raise ValueError("PRESENT effect snapshot requires a projected effect set")
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must be timezone-aware")
        return self


class RedriveReceipt(FrozenModel):
    schema_version: str = "controlproof.dlq-redrive-receipt.v1"
    source_event_id: UUID
    dlq_message_id: str
    republished_message_id: str | None = None
    body_digest: str
    send_succeeded: bool
    delete_succeeded: bool
    redriven_at: datetime

    @model_validator(mode="after")
    def validate_redrive(self) -> RedriveReceipt:
        if not _is_sha(self.body_digest):
            raise ValueError("redrive body_digest must be lowercase SHA-256")
        if self.send_succeeded and not self.republished_message_id:
            raise ValueError("successful redrive send requires republished message ID")
        if not self.send_succeeded and self.delete_succeeded:
            raise ValueError("DLQ message cannot be deleted after failed send")
        if self.redriven_at.tzinfo is None:
            raise ValueError("redriven_at must be timezone-aware")
        return self


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


class RunSubjectLane(FrozenModel):
    schema_version: str = "controlproof.n02-subject-lane.v1"
    run_id: UUID
    lane_id: N02LaneId
    subject_ref: str
    invitation_id: UUID
    applicant_id: UUID
    baseline_kind: BaselineKind
    fixture_kind: str | None = None
    fixture_digest: str | None = None
    allowed_preexisting_effects: dict[str, int] = Field(default_factory=dict)
    probe_overlays: tuple[str, ...] = ()
    target_effect_groups: tuple[N02EffectGroup, ...]
    trace_namespace: str
    seed_correlation_id: str

    @model_validator(mode="after")
    def validate_lane(self) -> RunSubjectLane:
        pristine = {
            N02LaneId.PRISTINE_BASELINE,
            N02LaneId.DOCUMENT_BYPASS,
            N02LaneId.NORMAL_ORDER,
            N02LaneId.CONSENT_FAULT_RECOVERY,
        }
        if self.lane_id in pristine:
            if self.baseline_kind is not BaselineKind.PRISTINE or any(
                value for value in (self.fixture_kind, self.fixture_digest)
            ) or self.allowed_preexisting_effects:
                raise ValueError("pristine lane cannot declare prerequisite fixture effects")
        else:
            if self.baseline_kind is not BaselineKind.PREREQUISITE_FIXTURE:
                raise ValueError("probe lane requires PREREQUISITE_FIXTURE baseline")
            if not self.fixture_kind or not _is_sha(self.fixture_digest):
                raise ValueError("probe lane requires fixture kind and digest")
            if not self.allowed_preexisting_effects:
                raise ValueError("probe lane requires allowlisted fixture effects")
        if self.probe_overlays and self.lane_id is not N02LaneId.CONSENT_FAULT_RECOVERY:
            raise ValueError("probe overlays belong only to the consent fault lane")
        expected_trace = f"controlproof:{self.run_id}:{self.lane_id.value}"
        if self.trace_namespace != expected_trace:
            raise ValueError("trace_namespace must bind the Run and lane")
        if not self.subject_ref.strip() or not self.seed_correlation_id.strip():
            raise ValueError("lane identity fields must be non-empty")
        if not self.target_effect_groups or len(set(self.target_effect_groups)) != len(
            self.target_effect_groups
        ):
            raise ValueError("target effect groups must be non-empty and unique")
        if any(value < 0 for value in self.allowed_preexisting_effects.values()):
            raise ValueError("fixture effect counts cannot be negative")
        return self


class ProtectedProcessingPath(FrozenModel):
    schema_version: str = "controlproof.n02-processing-path.v1"
    path_id: ProtectedPathId
    entry_boundary: str
    entry_kind: ProcessingEntryKind
    independent_direct_route: bool
    earliest_real_boundary: str | None = None
    required_fixture_kind: str | None = None
    request_effect_keys: tuple[str, ...]
    start_effect_keys: tuple[str, ...]
    result_effect_keys: tuple[str, ...]
    consent_purpose: ConsentPurpose
    contract_version: str = "v1"
    source_locator: dict[str, str]

    @model_validator(mode="after")
    def validate_path(self) -> ProtectedProcessingPath:
        expected_purpose = ConsentPurpose(self.path_id.value.casefold())
        if self.consent_purpose is not expected_purpose:
            raise ValueError("processing path must own its matching consent purpose")
        if not self.independent_direct_route and not self.earliest_real_boundary:
            raise ValueError("deep path requires earliest_real_boundary")
        if self.contract_version != "v1":
            raise ValueError("N-02 MVP processing path contract must be v1")
        for value in self.source_locator.values():
            path = PurePosixPath(value.replace("\\", "/"))
            if path.is_absolute() or re.match(r"^[A-Za-z]:/", value.replace("\\", "/")):
                raise ValueError("source locators must be repository-relative")
        return self


class ConsentPolicySnapshot(FrozenModel):
    schema_version: str = "controlproof.n02-policy.v1"
    policy_version: str
    content_digest: str
    required_purposes: tuple[ConsentPurpose, ...]
    retention_days: int = Field(ge=1)
    received_at: datetime
    request_id: UUID
    source_ref: str

    @model_validator(mode="after")
    def validate_policy(self) -> ConsentPolicySnapshot:
        if not self.policy_version.strip() or not _is_sha(self.content_digest):
            raise ValueError("policy version and content digest are required")
        if set(self.required_purposes) != set(ConsentPurpose) or len(
            self.required_purposes
        ) != len(ConsentPurpose):
            raise ValueError("policy must contain the exact three N-02 purposes")
        if self.received_at.tzinfo is None:
            raise ValueError("received_at must be timezone-aware")
        return self


class ConsentStateSnapshot(FrozenModel):
    schema_version: str = "controlproof.n02-consent-state.v1"
    run_id: UUID
    lane_id: N02LaneId
    subject_ref: str
    phase: Phase
    step_id: str
    attempt: int = Field(ge=1)
    invitation_status: str
    invitation_row_version: int = Field(ge=0)
    consent_record_ids: tuple[UUID, ...] = ()
    active_consent_count: int = Field(default=0, ge=0)
    consent_policy_versions: tuple[str, ...] = ()
    consent_content_digests: tuple[str, ...] = ()
    accepted_purpose_sets: tuple[tuple[ConsentPurpose, ...], ...] = ()
    consented_state_change_ids: tuple[UUID, ...] = ()
    consent_completed_event_ids: tuple[UUID, ...] = ()
    trace_ids: tuple[str, ...] = ()
    captured_at: datetime
    source_status: Presence
    source_error_code: str | None = None
    state_digest: str

    @model_validator(mode="after")
    def validate_consent_state(self) -> ConsentStateSnapshot:
        if self.captured_at.tzinfo is None or not _is_sha(self.state_digest):
            raise ValueError("consent state requires aware time and SHA-256 digest")
        if any(not _is_sha(item) for item in (*self.consent_content_digests, *self.trace_ids)):
            raise ValueError("consent and trace digests must be lowercase SHA-256")
        if self.source_status is Presence.UNAVAILABLE:
            if not self.source_error_code:
                raise ValueError("UNAVAILABLE consent state requires source_error_code")
            if any(
                (
                    self.consent_record_ids,
                    self.active_consent_count,
                    self.consented_state_change_ids,
                    self.consent_completed_event_ids,
                )
            ):
                raise ValueError("UNAVAILABLE consent state cannot claim projected facts")
        elif self.source_error_code is not None:
            raise ValueError("only UNAVAILABLE consent state may have source_error_code")
        if self.source_status is Presence.ABSENT and any(
            (
                self.consent_record_ids,
                self.active_consent_count,
                self.consented_state_change_ids,
                self.consent_completed_event_ids,
            )
        ):
            raise ValueError("ABSENT consent state cannot claim consent effects")
        if self.active_consent_count > len(self.consent_record_ids):
            raise ValueError("active consent count cannot exceed projected records")
        return self


class ProtectedEffectSnapshot(FrozenModel):
    recovery_stage: Literal["BEFORE_RETRY", "AFTER_RETRY"] | None = None
    schema_version: str = "controlproof.n02-protected-effect.v1"
    run_id: UUID
    lane_id: N02LaneId
    subject_ref: str
    path_id: ProtectedPathId
    phase: Phase
    step_id: str
    attempt: int = Field(ge=1)
    effect_group: N02EffectGroup
    request_ids: tuple[str, ...] = ()
    start_receipt_ids: tuple[str, ...] = ()
    # ID-003-17: the target's refusal of a runner input, kept apart from its start.
    refusal_receipt_ids: tuple[str, ...] = ()
    result_ids: tuple[str, ...] = ()
    status_projection: dict[str, Any] = Field(default_factory=dict)
    baseline_effect_ids: tuple[str, ...] = ()
    fixture_effect_ids: tuple[str, ...] = ()
    probe_input_effect_ids: tuple[str, ...] = ()
    # The consumer's processed row for a runner input: bookkeeping, not a protected effect.
    probe_bookkeeping_effect_ids: tuple[str, ...] = ()
    current_effect_ids: tuple[str, ...] = ()
    new_effect_ids: tuple[str, ...] = ()
    source_status: Presence
    source_error_code: str | None = None
    state_digest: str
    captured_at: datetime

    @model_validator(mode="after")
    def validate_effect(self) -> ProtectedEffectSnapshot:
        if self.effect_group.value != self.path_id.value:
            raise ValueError("effect group must match processing path")
        if not _is_sha(self.state_digest) or self.captured_at.tzinfo is None:
            raise ValueError("protected effect requires aware time and SHA-256 digest")
        if self.source_status is Presence.UNAVAILABLE:
            if not self.source_error_code:
                raise ValueError("UNAVAILABLE effect source requires error code")
            if any(
                (
                    self.request_ids,
                    self.start_receipt_ids,
                    self.refusal_receipt_ids,
                    self.result_ids,
                    self.new_effect_ids,
                )
            ):
                raise ValueError("UNAVAILABLE effect source cannot claim facts")
            return self
        if self.source_error_code is not None:
            raise ValueError("only UNAVAILABLE effect source may have error code")
        expected = (
            set(self.current_effect_ids)
            - set(self.baseline_effect_ids)
            - set(self.fixture_effect_ids)
            - set(self.probe_input_effect_ids)
            - set(self.probe_bookkeeping_effect_ids)
        )
        if set(self.new_effect_ids) != expected:
            raise ValueError("new effect IDs must equal the canonical delta")
        if not set(self.fixture_effect_ids) <= set(self.current_effect_ids):
            raise ValueError("fixture effects must remain present in current projection")
        if not set(self.probe_input_effect_ids) <= set(self.current_effect_ids):
            raise ValueError("probe inputs must remain present in current projection")
        inputs = {item.removeprefix("event:") for item in self.probe_input_effect_ids}
        if not set(self.probe_bookkeeping_effect_ids) <= set(self.current_effect_ids) or any(
            not item.startswith("processed:") or item.removeprefix("processed:") not in inputs
            for item in self.probe_bookkeeping_effect_ids
        ):
            raise ValueError("probe bookkeeping must be the consumer row of a present probe input")
        if self.refusal_receipt_ids and self.path_id is not ProtectedPathId.AI_ASSESSMENT:
            raise ValueError("refusal receipts belong to the assessment path")
        if self.source_status is Presence.ABSENT and any(
            (self.current_effect_ids, self.new_effect_ids)
        ):
            raise ValueError("ABSENT effect source cannot claim present effects")
        return self


class ProcessingAttemptReceipt(FrozenModel):
    recovery_stage: Literal["BEFORE_RETRY", "AFTER_RETRY"] | None = None
    schema_version: str = "controlproof.n02-processing-attempt.v1"
    attempt_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    lane_id: N02LaneId
    subject_ref: str
    path_id: ProtectedPathId
    entry_kind: ProcessingEntryKind
    operation_id: str
    request_id: str
    trace_id_digest: str
    sent_at: datetime
    response_at: datetime | None = None
    response_class: ProcessingResponseClass
    status_code: int | None = None
    sanitized_reason_code: str | None = None
    probe_input_effect_id: str | None = None
    # ID-003-18: when the runner drives a consented path to its result, the session it
    # created and the sanitized outcome of each step ("equipment-check:201", ...).
    created_session_id: str | None = None
    drive_steps: tuple[str, ...] = ()
    source_ref: str

    @model_validator(mode="after")
    def validate_attempt(self) -> ProcessingAttemptReceipt:
        if not _is_sha(self.trace_id_digest):
            raise ValueError("attempt trace_id_digest must be lowercase SHA-256")
        if self.sent_at.tzinfo is None or (
            self.response_at is not None and self.response_at.tzinfo is None
        ):
            raise ValueError("attempt timestamps must be timezone-aware")
        if self.response_class is ProcessingResponseClass.NO_RESPONSE:
            if self.response_at is not None or self.status_code is not None:
                raise ValueError("NO_RESPONSE cannot contain response fields")
        elif self.response_at is None:
            raise ValueError("completed attempt requires response_at")
        if self.entry_kind is not ProcessingEntryKind.HTTP and self.status_code is not None:
            raise ValueError("status_code belongs only to HTTP attempts")
        return self


class CausalEvent(FrozenModel):
    schema_version: str = "controlproof.n02-causal-event.v1"
    causal_event_id: UUID = Field(default_factory=uuid4)
    kind: CausalEventKind
    run_id: UUID
    lane_id: N02LaneId
    subject_ref: str
    path_id: ProtectedPathId | None = None
    domain_identity: dict[str, str]
    occurred_at: datetime | None = None
    observed_at: datetime
    source_type: str
    source_ref: str

    @model_validator(mode="after")
    def validate_event(self) -> CausalEvent:
        processing = {
            CausalEventKind.PROCESSING_REQUESTED,
            CausalEventKind.PROCESSING_STARTED,
            CausalEventKind.RESULT_CREATED,
        }
        if (self.kind in processing) != (self.path_id is not None):
            raise ValueError("processing causal events require exactly one path")
        if not self.domain_identity:
            raise ValueError("causal event requires allowlisted domain identity")
        if self.observed_at.tzinfo is None or (
            self.occurred_at is not None and self.occurred_at.tzinfo is None
        ):
            raise ValueError("causal event timestamps must be timezone-aware")
        return self


class CausalEdge(FrozenModel):
    schema_version: str = "controlproof.n02-causal-edge.v1"
    run_id: UUID
    lane_id: N02LaneId
    subject_ref: str
    from_event_id: UUID
    to_event_id: UUID
    relation: CausalRelation
    proof_refs: tuple[str, ...]
    status: CausalEdgeStatus

    @model_validator(mode="after")
    def validate_edge(self) -> CausalEdge:
        if self.from_event_id == self.to_event_id or not self.proof_refs:
            raise ValueError("causal edge requires distinct events and proof refs")
        return self


class ConsentFaultCondition(FrozenModel):
    schema_version: str = "controlproof.n02-consent-fault.v1"
    run_id: UUID
    lane_id: N02LaneId = N02LaneId.CONSENT_FAULT_RECOVERY
    subject_ref: str
    invitation_id: UUID
    applicant_id: UUID
    fault_kind: str = "consent_after_record_before_state_v1"
    fault_variant: ConsentFaultVariant = ConsentFaultVariant.AFTER_CONSENT_RECORD_BEFORE_STATE
    marker_digest: str
    one_shot: bool = True
    lifecycle: ConsentFaultLifecycle = ConsentFaultLifecycle.REQUESTED
    trigger_receipt_id: UUID | None = None
    requested_at: datetime
    expires_at: datetime
    restored_at: datetime | None = None
    environment_restore_success: bool | None = None

    @model_validator(mode="after")
    def validate_fault(self) -> ConsentFaultCondition:
        if self.lane_id is not N02LaneId.CONSENT_FAULT_RECOVERY:
            raise ValueError("consent fault belongs to the fault recovery lane")
        if not self.one_shot or not _is_sha(self.marker_digest):
            raise ValueError("consent fault requires one-shot marker digest")
        if any(item.tzinfo is None for item in (self.requested_at, self.expires_at)):
            raise ValueError("fault timestamps must be timezone-aware")
        if not self.requested_at < self.expires_at or (
            self.expires_at - self.requested_at
        ).total_seconds() > 600:
            raise ValueError("consent fault TTL must be in (0, 600] seconds")
        if self.lifecycle in {
            ConsentFaultLifecycle.TRIGGERED,
            ConsentFaultLifecycle.RESTORING,
            ConsentFaultLifecycle.RESTORED,
            ConsentFaultLifecycle.RESTORE_FAILED,
        } and self.trigger_receipt_id is None:
            raise ValueError("triggered fault lifecycle requires trigger receipt")
        if self.lifecycle in {
            ConsentFaultLifecycle.RESTORED,
            ConsentFaultLifecycle.RESTORE_FAILED,
        } and (self.restored_at is None or self.environment_restore_success is None):
            raise ValueError("terminal fault lifecycle requires restore result")
        return self


class ConsentFaultReceipt(FrozenModel):
    schema_version: str = "controlproof.whyyou-consent-fault-receipt.v1"
    receipt_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    lane_id: N02LaneId
    subject_ref: str
    invitation_id: UUID
    applicant_id: UUID
    fault_variant: ConsentFaultVariant
    boundary: ConsentFaultBoundary
    request_id: str
    triggered_at: datetime
    one_shot_consumed: bool

    @model_validator(mode="after")
    def validate_receipt(self) -> ConsentFaultReceipt:
        if self.lane_id is not N02LaneId.CONSENT_FAULT_RECOVERY:
            raise ValueError("fault receipt belongs to the fault recovery lane")
        if not self.one_shot_consumed:
            raise ValueError("fault receipt requires consumed one-shot token")
        if self.triggered_at.tzinfo is None:
            raise ValueError("triggered_at must be timezone-aware")
        return self


class RecoveryRecord(FrozenModel):
    schema_version: str = "controlproof.n02-recovery.v1"
    run_id: UUID
    lane_id: N02LaneId
    subject_ref: str
    marker_removed: bool
    consumed_token_removed: bool
    hook_inactive: bool
    condition_cleanup_succeeded: bool | None = None
    safe_state_confirmed: bool | None = None
    retry_commit_code: str | None = None
    retry_target_reason_code: str | None = None
    failed_request_effects_zero: bool | None
    normal_retry_succeeded: bool | None
    logical_consent_count: int | None = Field(default=None, ge=0)
    consent_completed_event_count: int | None = Field(default=None, ge=0)
    processing_order_proven: bool | None
    restore_status: RecoveryStatus
    manual_cleanup_required: bool

    @model_validator(mode="after")
    def validate_recovery(self) -> RecoveryRecord:
        if self.lane_id is not N02LaneId.CONSENT_FAULT_RECOVERY:
            raise ValueError("recovery belongs to the consent fault lane")
        # restore_status covers restore safety only (FR-032, ID-003-14); the retry outcome
        # (failed-request effects, retried consent, processing order) is judged by A6/A7.
        if self.restore_status is RecoveryStatus.SUCCEEDED:
            if self.manual_cleanup_required:
                raise ValueError("successful recovery cannot require manual cleanup")
            if not all(
                (
                    self.marker_removed,
                    self.consumed_token_removed,
                    self.hook_inactive,
                    self.condition_cleanup_succeeded is True,
                    self.safe_state_confirmed is True,
                )
            ):
                raise ValueError("successful recovery requires every safety proof")
        elif not self.manual_cleanup_required:
            raise ValueError("failed or unverified recovery requires manual cleanup")
        return self


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
    execution_profile: ExecutionProfile | None = None
    fault_variant: FaultVariant | None = None
    environment_kind: EnvironmentKind | None = None
    aws_deployment_status: AwsDeploymentStatus | None = None
    environment_snapshot_digest: str | None = None
    queue_topology_digest: str | None = None
    lane_manifest_digest: str | None = None
    path_capability_digest: str | None = None
    policy_snapshot_digest: str | None = None
    source_event_id: UUID | None = None
    unverified_scope: tuple[str, ...] = ()

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
        spec002_profiles = {
            ExecutionProfile.H03_DLQ_V2,
            ExecutionProfile.E03_BEFORE_V2,
            ExecutionProfile.E03_AFTER_V2,
        }
        if self.execution_profile in spec002_profiles:
            if self.fault_variant is None:
                raise ValueError("Spec 002 Run requires fault_variant")
            if self.environment_kind is not EnvironmentKind.LOCAL_EMULATED:
                raise ValueError("Spec 002 Run requires LOCAL_EMULATED environment")
            if self.aws_deployment_status is not AwsDeploymentStatus.NOT_RUN:
                raise ValueError("Spec 002 local Run requires AWS NOT_RUN")
            if not _is_sha(self.environment_snapshot_digest) or not _is_sha(
                self.queue_topology_digest
            ):
                raise ValueError("Spec 002 Run requires environment and queue snapshot digests")
            if set(self.unverified_scope) != SPEC002_UNVERIFIED_SCOPE:
                raise ValueError("Spec 002 Run requires the exact unverified AWS scope")
        if self.execution_profile is ExecutionProfile.N02_CONSENT_ORDER_V1:
            if self.scenario_id != "N-02" or self.fault_variant is not None:
                raise ValueError("N-02 Run requires canonical scenario and no Spec 002 fault variant")
            if self.environment_kind is not EnvironmentKind.LOCAL_EMULATED:
                raise ValueError("N-02 Run requires LOCAL_EMULATED environment")
            if self.aws_deployment_status is not AwsDeploymentStatus.NOT_RUN:
                raise ValueError("N-02 local Run requires AWS NOT_RUN")
            required_digests = (
                self.environment_snapshot_digest,
                self.lane_manifest_digest,
                self.path_capability_digest,
                self.policy_snapshot_digest,
            )
            if any(not _is_sha(value) for value in required_digests):
                raise ValueError("N-02 Run requires environment, lane, path and policy digests")
            if self.queue_topology_digest is not None and not _is_sha(
                self.queue_topology_digest
            ):
                raise ValueError("optional N-02 queue topology digest must be SHA-256")
            if set(self.unverified_scope) != SPEC003_UNVERIFIED_SCOPE:
                raise ValueError("N-02 Run requires exact AWS/N-01/N-03 unverified scope")
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
    fault_variant: FaultVariant | None = None
    boundary_receipt_id: UUID | None = None
    one_shot: bool = False


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
