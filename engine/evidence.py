"""Redacted, atomic, hash-addressed, immutable Evidence Bundles."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from engine.lifecycle import atomic_write
from engine.models import (
    SPEC004_PROFILES,
    EvidenceArtifact,
    ExecutionProfile,
    IntegrityStatus,
    Phase,
    Run,
    ScenarioProfile,
    canonical_json_bytes,
    sha256_bytes,
    utcnow,
)

REDACTED = "[REDACTED]"
HASHED = "[HASHED]"
FORBIDDEN_KEYS = {
    "authorization",
    "cookie",
    "password",
    "access_token",
    "refresh_token",
    "token_hash",
    "signed_url",
    "database_url",
    "idempotency_key",
    "idempotency-key",
    "queue_url",
    "source_queue_url",
    "dead_letter_queue_url",
    "receipt_handle",
    "message_body",
    "raw_message_body",
    "db_projection",
    "raw_db_projection",
    "database_projection",
    "database_dump",
    "policy_text",
    "answer_text",
    "document_text",
    "report_text",
    "model_prompt",
    "credential",
    # Spec 004 raw text fields: projections carry *_sha256/*_length instead (FR-042, T018).
    # Generic keys such as summary/rationale stay allowed for ControlProof's own wording.
    "report_summary",
    "item_observation",
    "axis_rationale",
    "item_uncertainty",
    "follow_up_question",
    "question_text",
    "transcript_text",
    "criterion_description",
    "playback_url",
}
PII_KEYS = {
    "name",
    "full_name",
    "display_name",
    "applicant_name",
    "applicant_display_name",
    "email",
    "phone",
    "phone_number",
}
EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
PHONE_RE = re.compile(
    r"(?<![0-9A-Za-z])(?:01[016789]|\+82[- ]?1[016789])[- ]?\d{3,4}[- ]?\d{4}"
    r"(?![0-9A-Za-z])"
)
BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
SIGNED_QUERY_RE = re.compile(r"(?i)(X-Amz-Signature|signature|sig|token)=([^&\s]+)")
USER_PATH_RE = re.compile(
    r"(?i)(?:[A-Z]:[/\\]Users[/\\][^/\\\s]+|/Users/[^/\s]+|/home/[^/\s]+)"
)

CANONICAL_FILES = {
    "run.json",
    "scenario.snapshot.yaml",
    "target.snapshot.json",
    "subjects.json",
    "faults.jsonl",
    "observations.jsonl",
    "assertions.json",
    "judgement.json",
}

SPEC002_PROFILE_CONTRACT = "controlproof.bundle-profile.spec002.v1"
SPEC003_PROFILE_CONTRACT = "controlproof.bundle-profile.spec003.v1"
SPEC002_COMMON_CANONICAL_FILES = CANONICAL_FILES | {
    "environment.snapshot.json",
    "queue-topology.snapshot.json",
    "delivery-attempts.jsonl",
    "effects.jsonl",
}
SPEC002_DLQ_CANONICAL_FILES = SPEC002_COMMON_CANONICAL_FILES | {
    "terminal-failure.json",
    "redrive-receipts.jsonl",
}
SPEC003_CANONICAL_FILES = CANONICAL_FILES | {
    "environment.snapshot.json",
    "n02-capabilities.json",
    "n02-lanes.json",
    "policy-and-consent.json",
    "baseline-effects.jsonl",
    "bypass-attempts.jsonl",
    "protected-effects.jsonl",
    "causal-events.jsonl",
    "causal-edges.jsonl",
    "fault-receipts.jsonl",
    "recovery.json",
}
SPEC003_REQUIRED_FILE_LINKS = {
    "EV3-01": {
        "n02-capabilities.json",
        "n02-lanes.json",
        "environment.snapshot.json",
        "scenario.snapshot.yaml",
        "target.snapshot.json",
    },
    "EV3-02": {"policy-and-consent.json"},
    "EV3-03": {"baseline-effects.jsonl", "n02-lanes.json"},
    "EV3-04": {"bypass-attempts.jsonl"},
    "EV3-05": {"protected-effects.jsonl"},
    "EV3-06": {"causal-events.jsonl", "causal-edges.jsonl"},
    "EV3-07": {"fault-receipts.jsonl"},
    "EV3-08": {"policy-and-consent.json", "protected-effects.jsonl"},
    "EV3-09": {"recovery.json", "protected-effects.jsonl"},
    "EV3-10": {"assertions.json", "judgement.json"},
}

SPEC004_PROFILE_CONTRACT = "controlproof.bundle-profile.spec004.v1"
#: Spec 004 has no fault marker, so `faults.jsonl` is not canonical (ID-004-05).
SPEC004_BASE_FILES = (CANONICAL_FILES - {"faults.jsonl"}) | {"environment.snapshot.json"}
SPEC004_SNAPSHOT_FILES = frozenset(
    {"environment.snapshot.json", "scenario.snapshot.yaml", "target.snapshot.json"}
)
SPEC004_PROFILE_FILES = {
    ExecutionProfile.E01_CITATION_EVIDENCE_V1: frozenset(
        {
            "spec004-capabilities.json",
            "spec004-lanes.json",
            "citation-cases.jsonl",
            "model-emissions.jsonl",
            "report-records.jsonl",
            "report-reads.jsonl",
            "storage-probe.json",
            "change-injections.jsonl",
            "recovery.json",
        }
    ),
    ExecutionProfile.E02_SCORING_FREEZE_V1: frozenset(
        {
            "spec004-capabilities.json",
            "spec004-lanes.json",
            "report-records.jsonl",
            "report-reads.jsonl",
            "criteria-versions.json",
            "frozen-inputs.json",
            "recompute.json",
            "change-injections.jsonl",
            "recovery.json",
        }
    ),
}
#: contracts/evidence-bundle-v4.md "Evidence mapping".
SPEC004_REQUIRED_FILE_LINKS = {
    ExecutionProfile.E01_CITATION_EVIDENCE_V1: {
        "EV4-01": {"spec004-capabilities.json", *SPEC004_SNAPSHOT_FILES},
        "EV4-02": {"spec004-lanes.json"},
        "EV4-03": {"citation-cases.jsonl", "model-emissions.jsonl"},
        "EV4-04": {"report-records.jsonl", "storage-probe.json"},
        "EV4-05": {"report-reads.jsonl"},
        "EV4-09": {"change-injections.jsonl", "recovery.json"},
        "EV4-10": {"assertions.json", "judgement.json"},
    },
    ExecutionProfile.E02_SCORING_FREEZE_V1: {
        "EV4-01": {"spec004-capabilities.json", "recompute.json", *SPEC004_SNAPSHOT_FILES},
        "EV4-02": {"spec004-lanes.json"},
        "EV4-04": {"report-records.jsonl"},
        "EV4-06": {"criteria-versions.json"},
        "EV4-07": {"frozen-inputs.json", "report-reads.jsonl"},
        "EV4-08": {"recompute.json"},
        "EV4-09": {"change-injections.jsonl", "recovery.json"},
        "EV4-10": {"assertions.json", "judgement.json"},
    },
}


def spec004_required_files(profile: ExecutionProfile) -> set[str]:
    """The profile-specific files a Spec 004 bundle must carry (on top of the base files)."""
    return set(SPEC004_PROFILE_FILES[profile])


REQUIRED_EVIDENCE_ARTIFACT_TYPES: dict[str, frozenset[str]] = {
    "EV-01": frozenset({"STATE_SNAPSHOT"}),
    "EV-02": frozenset({"FAULT_RECEIPT"}),
    "EV-03": frozenset({"FAULT_RECEIPT", "HTTP_EXCHANGE"}),
    "EV-04": frozenset({"SCREENSHOT", "BROWSER_PROJECTION"}),
    "EV-05": frozenset({"HTTP_EXCHANGE"}),
    "EV-06": frozenset({"STATE_SNAPSHOT"}),
    "EV-07": frozenset({"STATE_SNAPSHOT"}),
    "EV-08": frozenset({"FAULT_RECEIPT", "STATE_SNAPSHOT"}),
    "EV-09": frozenset({"VERSION_SNAPSHOT"}),
}


def _is_spec002_profile(profile: ExecutionProfile | None) -> bool:
    return profile in {
        ExecutionProfile.H03_DLQ_V2,
        ExecutionProfile.E03_BEFORE_V2,
        ExecutionProfile.E03_AFTER_V2,
    }


def _is_spec003_profile(profile: ExecutionProfile | None) -> bool:
    return profile is ExecutionProfile.N02_CONSENT_ORDER_V1


def _is_spec004_profile(profile: ExecutionProfile | None) -> bool:
    return profile in SPEC004_PROFILES


def _is_versioned_profile(profile: ExecutionProfile | None) -> bool:
    return (
        _is_spec002_profile(profile)
        or _is_spec003_profile(profile)
        or _is_spec004_profile(profile)
    )


def _canonical_files(profile: ExecutionProfile | None) -> set[str]:
    if profile in {ExecutionProfile.H03_DLQ_V2, ExecutionProfile.E03_BEFORE_V2}:
        return set(SPEC002_DLQ_CANONICAL_FILES)
    if profile is ExecutionProfile.E03_AFTER_V2:
        return set(SPEC002_COMMON_CANONICAL_FILES)
    if _is_spec003_profile(profile):
        return set(SPEC003_CANONICAL_FILES)
    if _is_spec004_profile(profile):
        return set(SPEC004_BASE_FILES) | spec004_required_files(profile)
    return set(CANONICAL_FILES)


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            lowered = key.casefold()
            if _is_sensitive_key(lowered):
                result[key] = HASHED if lowered.endswith("token_hash") else REDACTED
            else:
                result[key] = redact(item)
        return result
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    if isinstance(value, str):
        text = BEARER_RE.sub("Bearer [REDACTED]", value)
        text = EMAIL_RE.sub("[SUBJECT_REF]", text)
        text = PHONE_RE.sub(REDACTED, text)
        text = SIGNED_QUERY_RE.sub(lambda match: f"{match.group(1)}={REDACTED}", text)
        text = USER_PATH_RE.sub("[USER_ROOT]", text)
        return text
    return value


def assert_redacted(payload: bytes) -> None:
    text = payload.decode("utf-8", errors="ignore")
    if (
        BEARER_RE.search(text)
        or EMAIL_RE.search(text)
        or PHONE_RE.search(text)
        or USER_PATH_RE.search(text)
    ):
        raise ValueError("redaction scanner found prohibited secret or PII pattern")
    for document in _json_documents(text):
        if _contains_unredacted_sensitive_field(document):
            raise ValueError("redaction scanner found prohibited secret or PII field")


def _is_sensitive_key(lowered: str) -> bool:
    return (
        lowered in FORBIDDEN_KEYS
        or lowered in PII_KEYS
        or lowered.endswith(
            (
                "_token",
                "_token_hash",
                "_receipt_handle",
                "_queue_url",
                "_message_body",
                "_db_projection",
                "_database_projection",
                "_database_dump",
            )
        )
    )


def _json_documents(text: str) -> tuple[Any, ...]:
    stripped = text.strip()
    if not stripped:
        return ()
    try:
        return (json.loads(stripped),)
    except json.JSONDecodeError:
        documents: list[Any] = []
        for line in stripped.splitlines():
            try:
                documents.append(json.loads(line))
            except json.JSONDecodeError:
                return ()
        return tuple(documents)


def _contains_unredacted_sensitive_field(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if _is_sensitive_key(str(key).casefold()) and item not in {
                None,
                REDACTED,
                HASHED,
            }:
                return True
            if _contains_unredacted_sensitive_field(item):
                return True
        return False
    if isinstance(value, (list, tuple)):
        return any(_contains_unredacted_sensitive_field(item) for item in value)
    return False


def _relative(root: Path, relative_path: str) -> Path:
    candidate_text = relative_path.replace("\\", "/")
    if candidate_text.startswith("/") or ".." in Path(candidate_text).parts:
        raise ValueError("bundle path escapes the Run root")
    candidate = (root / candidate_text).resolve()
    if not candidate.is_relative_to(root.resolve()):
        raise ValueError("bundle path escapes the Run root")
    if candidate.exists() and candidate.is_symlink():
        raise ValueError("bundle files cannot be symlinks")
    return candidate


class EvidenceBundleWriter:
    def __init__(self, run_root: Path, run: Run) -> None:
        self.run = run
        self.profile = run.execution_profile
        self.directory = (run_root.resolve() / str(run.run_id)).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self._files: dict[str, dict[str, Any]] = {}
        if _is_versioned_profile(self.profile):
            required = ScenarioProfile.canonical(self.profile).required_evidence
        else:
            required = tuple(f"EV-{index:02d}" for index in range(1, 10))
        self._required: dict[str, list[Any]] = {evidence_id: [] for evidence_id in required}

    @property
    def sealed(self) -> bool:
        return (self.directory / "manifest.json").exists()

    def _ensure_mutable(self) -> None:
        if self.sealed:
            raise PermissionError("sealed Evidence Bundle is immutable")

    def write_json(self, relative_path: str, value: Any, *, redact_first: bool = True) -> Path:
        self._ensure_mutable()
        projected = redact(value) if redact_first else value
        payload = canonical_json_bytes(projected)
        assert_redacted(payload)
        path = _relative(self.directory, relative_path)
        atomic_write(path, payload)
        self._register(relative_path, payload, "application/json")
        return path

    def write_bytes(self, relative_path: str, payload: bytes, mime_type: str) -> Path:
        self._ensure_mutable()
        if mime_type.startswith("text/") or mime_type in {
            "application/json",
            "application/yaml",
            "application/x-ndjson",
        }:
            assert_redacted(payload)
        path = _relative(self.directory, relative_path)
        atomic_write(path, payload)
        self._register(relative_path, payload, mime_type)
        return path

    def append_jsonl(self, relative_path: str, value: Any) -> None:
        self._ensure_mutable()
        projected = redact(value)
        payload = canonical_json_bytes(projected)
        assert_redacted(payload)
        path = _relative(self.directory, relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("ab") as stream:
            stream.write(payload + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        complete = path.read_bytes()
        self._register(relative_path, complete, "application/x-ndjson")

    def link_file_evidence(self, evidence_id: str, relative_path: str) -> None:
        """Link a registered bundle file to a profile-scoped evidence requirement."""

        self._ensure_mutable()
        if evidence_id not in self._required:
            raise ValueError(f"unknown evidence requirement: {evidence_id}")
        normalized = relative_path.replace("\\", "/")
        if normalized not in self._files:
            raise ValueError(f"evidence file is not registered: {normalized}")
        reference = f"file:{normalized}"
        if reference not in self._required[evidence_id]:
            self._required[evidence_id].append(reference)

    def link_intrinsic_evidence(self, evidence_id: str, name: str) -> None:
        """Link an intrinsic verifier fact such as the final sealed manifest."""

        self._ensure_mutable()
        if evidence_id not in self._required:
            raise ValueError(f"unknown evidence requirement: {evidence_id}")
        if name != "sealed-manifest":
            raise ValueError(f"unknown intrinsic evidence: {name}")
        reference = f"intrinsic:{name}"
        if reference not in self._required[evidence_id]:
            self._required[evidence_id].append(reference)

    def link_origin_artifact(
        self,
        evidence_id: str,
        *,
        origin_run_id: UUID,
        artifact_id: UUID,
        artifact_digest: str,
        bundle_digest: str,
    ) -> None:
        """Link an artifact from another already sealed Run by immutable digests."""

        self._ensure_mutable()
        if evidence_id not in self._required:
            raise ValueError(f"unknown evidence requirement: {evidence_id}")
        if not re.fullmatch(r"[0-9a-f]{64}", artifact_digest) or not re.fullmatch(
            r"[0-9a-f]{64}", bundle_digest
        ):
            raise ValueError("cross-Run evidence requires canonical SHA-256 digests")
        self._required[evidence_id].append(
            {
                "origin_run_id": str(origin_run_id),
                "artifact_id": str(artifact_id),
                "artifact_digest": artifact_digest,
                "bundle_digest": bundle_digest,
            }
        )

    def collect_json_artifact(
        self,
        *,
        subject_ref: str,
        phase: Phase,
        step_id: str,
        attempt: int,
        evidence_requirement_ids: tuple[str, ...],
        artifact_type: str,
        source_locator: dict[str, Any],
        content: Any,
        artifact_id: UUID | None = None,
    ) -> EvidenceArtifact:
        self._ensure_mutable()
        active_id = artifact_id or uuid4()
        relative_path = f"artifacts/{active_id}.json"
        captured_at = utcnow()
        envelope = redact(
            {
                "schema_version": "controlproof.artifact.v1",
                "artifact_id": str(active_id),
                "run_id": str(self.run.run_id),
                "subject_ref": subject_ref,
                "phase": phase.value,
                "step_id": step_id,
                "attempt": attempt,
                "evidence_requirement_ids": evidence_requirement_ids,
                "artifact_type": artifact_type,
                "captured_at": captured_at.isoformat(),
                "source_locator": source_locator,
                "content": content,
            }
        )
        payload = canonical_json_bytes(envelope)
        assert_redacted(payload)
        path = _relative(self.directory, relative_path)
        atomic_write(path, payload)
        self._register(
            relative_path,
            payload,
            "application/json",
            artifact_id=str(active_id),
            redaction_profile="controlproof-redaction-v1",
            subject_ref=subject_ref,
            phase=phase.value,
            step_id=step_id,
            attempt=attempt,
            evidence_requirement_ids=evidence_requirement_ids,
            artifact_type=artifact_type,
        )
        for evidence_id in evidence_requirement_ids:
            if evidence_id not in self._required:
                raise ValueError(f"unknown evidence requirement: {evidence_id}")
            reference = (
                f"artifact:{active_id}" if _is_versioned_profile(self.profile) else str(active_id)
            )
            self._required[evidence_id].append(reference)
        return EvidenceArtifact(
            artifact_id=active_id,
            run_id=self.run.run_id,
            subject_ref=subject_ref,
            phase=phase,
            step_id=step_id,
            attempt=attempt,
            evidence_requirement_ids=evidence_requirement_ids,
            artifact_type=artifact_type,
            relative_path=relative_path,
            source_locator=redact(source_locator),
            captured_at=captured_at,
            mime_type="application/json",
            size_bytes=len(payload),
            sha256=sha256_bytes(payload),
            integrity_status=IntegrityStatus.VERIFIED,
        )

    def collect_binary_artifact(
        self,
        *,
        subject_ref: str,
        phase: Phase,
        step_id: str,
        attempt: int,
        evidence_requirement_ids: tuple[str, ...],
        artifact_type: str,
        source_locator: dict[str, Any],
        payload: bytes,
        mime_type: str,
        suffix: str,
        artifact_id: UUID | None = None,
    ) -> EvidenceArtifact:
        self._ensure_mutable()
        active_id = artifact_id or uuid4()
        relative_path = f"artifacts/{active_id}.{suffix.lstrip('.')}"
        path = _relative(self.directory, relative_path)
        atomic_write(path, payload)
        self._register(
            relative_path,
            payload,
            mime_type,
            artifact_id=str(active_id),
            redaction_profile="controlproof-redaction-v1",
            subject_ref=subject_ref,
            phase=phase.value,
            step_id=step_id,
            attempt=attempt,
            evidence_requirement_ids=evidence_requirement_ids,
            artifact_type=artifact_type,
        )
        for evidence_id in evidence_requirement_ids:
            if evidence_id not in self._required:
                raise ValueError(f"unknown evidence requirement: {evidence_id}")
            reference = (
                f"artifact:{active_id}" if _is_versioned_profile(self.profile) else str(active_id)
            )
            self._required[evidence_id].append(reference)
        return EvidenceArtifact(
            artifact_id=active_id,
            run_id=self.run.run_id,
            subject_ref=subject_ref,
            phase=phase,
            step_id=step_id,
            attempt=attempt,
            evidence_requirement_ids=evidence_requirement_ids,
            artifact_type=artifact_type,
            relative_path=relative_path,
            source_locator=redact(source_locator),
            captured_at=utcnow(),
            mime_type=mime_type,
            size_bytes=len(payload),
            sha256=sha256_bytes(payload),
            integrity_status=IntegrityStatus.VERIFIED,
        )

    def _register(
        self,
        relative_path: str,
        payload: bytes,
        mime_type: str,
        *,
        artifact_id: str | None = None,
        redaction_profile: str | None = None,
        subject_ref: str | None = None,
        phase: str | None = None,
        step_id: str | None = None,
        attempt: int | None = None,
        evidence_requirement_ids: tuple[str, ...] | None = None,
        artifact_type: str | None = None,
    ) -> None:
        record: dict[str, Any] = {
            "path": relative_path.replace("\\", "/"),
            "mime_type": mime_type,
            "size_bytes": len(payload),
            "sha256": sha256_bytes(payload),
        }
        if artifact_id:
            record["artifact_id"] = artifact_id
        if redaction_profile:
            record["redaction_profile"] = redaction_profile
        if artifact_id:
            record.update(
                {
                    "subject_ref": subject_ref,
                    "phase": phase,
                    "step_id": step_id,
                    "attempt": attempt,
                    "evidence_requirement_ids": list(evidence_requirement_ids or ()),
                    "artifact_type": artifact_type,
                }
            )
        self._files[record["path"]] = record

    def seal(self) -> dict[str, Any]:
        self._ensure_mutable()
        missing_canonical = sorted(_canonical_files(self.profile) - set(self._files))
        if missing_canonical:
            raise ValueError(f"cannot seal bundle; canonical files missing: {missing_canonical}")
        manifest = {
            "schema_version": "controlproof.bundle.v1",
            "run_id": str(self.run.run_id),
            "created_at": self.run.started_at.isoformat()
            if self.run.started_at
            else utcnow().isoformat(),
            "sealed_at": utcnow().isoformat(),
            "files": [self._files[key] for key in sorted(self._files)],
            "required_evidence": self._required,
        }
        if _is_spec002_profile(self.profile):
            manifest.update(
                {
                    "profile_contract": SPEC002_PROFILE_CONTRACT,
                    "execution_profile": self.profile.value,
                    "environment_snapshot_digest": self.run.environment_snapshot_digest,
                    "queue_topology_digest": self.run.queue_topology_digest,
                }
            )
        elif _is_spec003_profile(self.profile):
            manifest.update(
                {
                    "profile_contract": SPEC003_PROFILE_CONTRACT,
                    "execution_profile": self.profile.value,
                    "environment_snapshot_digest": self.run.environment_snapshot_digest,
                    "lane_manifest_digest": self.run.lane_manifest_digest,
                    "path_capability_digest": self.run.path_capability_digest,
                    "policy_snapshot_digest": self.run.policy_snapshot_digest,
                }
            )
        elif _is_spec004_profile(self.profile):
            manifest.update(
                {
                    "profile_contract": SPEC004_PROFILE_CONTRACT,
                    "execution_profile": self.profile.value,
                    "environment_snapshot_digest": self.run.environment_snapshot_digest,
                    "lane_manifest_digest": self.run.lane_manifest_digest,
                    "path_capability_digest": self.run.path_capability_digest,
                    "scoring_rule_source_digest": self.run.scoring_rule_source_digest,
                }
            )
        manifest["bundle_digest"] = sha256_bytes(canonical_json_bytes(manifest))
        atomic_write(self.directory / "manifest.json", canonical_json_bytes(manifest))
        return manifest


def verify_bundle(path: Path, *, require_all_evidence: bool = True) -> dict[str, Any]:
    directory = path.resolve()
    manifest_path = directory / "manifest.json"
    result: dict[str, Any] = {
        "bundle_status": "VERIFIED",
        "checked_files": 0,
        "missing_files": [],
        "mismatched_files": [],
        "unregistered_files": [],
        "verified_at": utcnow().isoformat(),
    }
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        result["bundle_status"] = "INVALID"
        result["mismatched_files"].append(f"manifest.json:{type(exc).__name__}")
        return result
    if not isinstance(manifest, dict):
        result["bundle_status"] = "INVALID"
        result["mismatched_files"].append("manifest.json:object")
        return result
    if manifest.get("schema_version") != "controlproof.bundle.v1":
        result["mismatched_files"].append("manifest.json:schema_version")
    profile = _resolve_bundle_profile(directory, manifest, result)
    digest_payload = {key: value for key, value in manifest.items() if key != "bundle_digest"}
    if manifest.get("bundle_digest") != sha256_bytes(canonical_json_bytes(digest_payload)):
        result["mismatched_files"].append("manifest.json:bundle_digest")
    records = manifest.get("files")
    if not isinstance(records, list):
        result["mismatched_files"].append("manifest.json:files")
        records = []
    registered = set()
    artifact_records: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            result["mismatched_files"].append("manifest.json:file_record")
            continue
        relative_path = record.get("path", "")
        if not isinstance(relative_path, str) or not relative_path:
            result["mismatched_files"].append("manifest.json:file_path")
            continue
        if relative_path in registered:
            result["mismatched_files"].append(f"{relative_path}:duplicate")
        registered.add(relative_path)
        try:
            file_path = _relative(directory, relative_path)
        except ValueError:
            result["mismatched_files"].append(f"{relative_path}:path")
            continue
        if not file_path.exists():
            result["missing_files"].append(relative_path)
            continue
        payload = file_path.read_bytes()
        result["checked_files"] += 1
        if len(payload) != record.get("size_bytes") or sha256_bytes(payload) != record.get(
            "sha256"
        ):
            result["mismatched_files"].append(relative_path)
        artifact_id = record.get("artifact_id")
        if artifact_id:
            if artifact_id in artifact_records:
                result["mismatched_files"].append(f"artifact:{artifact_id}:duplicate")
            artifact_records[artifact_id] = record
            _verify_artifact_envelope(directory, record, result)
    for canonical in sorted(_canonical_files(profile)):
        if canonical not in registered or not (directory / canonical).is_file():
            result["missing_files"].append(canonical)
    actual = {
        item.relative_to(directory).as_posix()
        for item in directory.rglob("*")
        if item.is_file() and item.name != "manifest.json"
    }
    result["unregistered_files"] = sorted(actual - registered)
    if result["unregistered_files"]:
        result["mismatched_files"].extend(
            f"{relative_path}:unregistered" for relative_path in result["unregistered_files"]
        )
    if require_all_evidence:
        required_evidence = manifest.get("required_evidence")
        if not isinstance(required_evidence, dict):
            result["mismatched_files"].append("manifest.json:required_evidence")
            required_evidence = {}
        if _is_spec002_profile(profile):
            _verify_spec002_evidence(
                directory,
                required_evidence,
                ScenarioProfile.canonical(profile).required_evidence,
                registered,
                artifact_records,
                result,
            )
        elif _is_spec003_profile(profile):
            expected = ScenarioProfile.canonical(profile).required_evidence
            _verify_spec002_evidence(
                directory,
                required_evidence,
                expected,
                registered,
                artifact_records,
                result,
            )
            for evidence_id, paths in SPEC003_REQUIRED_FILE_LINKS.items():
                references = required_evidence.get(evidence_id, [])
                if not isinstance(references, list) or not {
                    f"file:{name}" for name in paths
                }.issubset(references):
                    result["mismatched_files"].append(
                        f"evidence:{evidence_id}:canonical-files"
                    )
            result["checked_evidence_requirements"] = list(expected)
        elif _is_spec004_profile(profile):
            expected = ScenarioProfile.canonical(profile).required_evidence
            _verify_spec002_evidence(
                directory,
                required_evidence,
                expected,
                registered,
                artifact_records,
                result,
            )
            for evidence_id, paths in SPEC004_REQUIRED_FILE_LINKS[profile].items():
                references = required_evidence.get(evidence_id, [])
                if not isinstance(references, list) or not {
                    f"file:{name}" for name in paths
                }.issubset(references):
                    result["mismatched_files"].append(
                        f"evidence:{evidence_id}:canonical-files"
                    )
            result["checked_evidence_requirements"] = list(expected)
        else:
            _verify_v1_evidence(required_evidence, artifact_records, result)
    _verify_manifest_run_link(directory, manifest, result)
    _verify_snapshot_links(directory, result)
    if _is_spec002_profile(profile):
        _verify_spec002_snapshot_links(directory, manifest, result)
    elif _is_spec003_profile(profile):
        _verify_spec003_snapshot_links(directory, manifest, result)
        _verify_spec003_facts(directory, result)
    elif _is_spec004_profile(profile):
        _verify_spec004_snapshot_links(directory, manifest, profile, result)
        _verify_spec004_facts(directory, profile, result)
    if result["missing_files"] or result["mismatched_files"]:
        result["bundle_status"] = "INVALID"
    result["missing_files"].sort()
    result["mismatched_files"].sort()
    return result


def _verify_v1_evidence(
    required_evidence: dict[str, Any],
    artifact_records: dict[str, dict[str, Any]],
    result: dict[str, Any],
) -> None:
    for evidence_id in (f"EV-{index:02d}" for index in range(1, 10)):
        linked = required_evidence.get(evidence_id)
        if not isinstance(linked, list) or not linked:
            result["missing_files"].append(f"evidence:{evidence_id}")
            continue
        for artifact_id in linked:
            if artifact_id not in artifact_records:
                result["mismatched_files"].append(
                    f"evidence:{evidence_id}:unknown-artifact:{artifact_id}"
                )
                continue
            record = artifact_records[artifact_id]
            declared = record.get("evidence_requirement_ids")
            if not isinstance(declared, list) or evidence_id not in declared:
                result["mismatched_files"].append(
                    f"evidence:{evidence_id}:cross-link:{artifact_id}"
                )
        linked_types = {
            artifact_records[artifact_id].get("artifact_type")
            for artifact_id in linked
            if artifact_id in artifact_records
            and isinstance(artifact_records[artifact_id].get("evidence_requirement_ids"), list)
            and evidence_id in artifact_records[artifact_id]["evidence_requirement_ids"]
        }
        for artifact_type in sorted(REQUIRED_EVIDENCE_ARTIFACT_TYPES[evidence_id] - linked_types):
            result["mismatched_files"].append(
                f"evidence:{evidence_id}:artifact-type:{artifact_type}"
            )


def _resolve_bundle_profile(
    directory: Path,
    manifest: dict[str, Any],
    result: dict[str, Any],
) -> ExecutionProfile | None:
    try:
        run = json.loads((directory / "run.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    raw_profile = run.get("execution_profile") if isinstance(run, dict) else None
    try:
        profile = ExecutionProfile(raw_profile) if raw_profile else None
    except ValueError:
        result["mismatched_files"].append("run.json:execution_profile")
        return None
    contract = manifest.get("profile_contract")
    if contract is None:
        if _is_versioned_profile(profile):
            result["mismatched_files"].append("manifest.json:profile_contract")
        return profile
    if _is_spec003_profile(profile):
        expected_contract = SPEC003_PROFILE_CONTRACT
    elif _is_spec004_profile(profile):
        expected_contract = SPEC004_PROFILE_CONTRACT
    else:
        expected_contract = SPEC002_PROFILE_CONTRACT
    if contract != expected_contract:
        result["mismatched_files"].append("manifest.json:profile_contract")
        return profile
    if not _is_versioned_profile(profile):
        result["mismatched_files"].append("manifest.json:execution_profile")
        return profile
    if manifest.get("execution_profile") != profile.value:
        result["mismatched_files"].append("manifest.json:execution_profile")
    return profile


def _verify_spec002_evidence(
    directory: Path,
    required_evidence: dict[str, Any],
    expected_ids: tuple[str, ...],
    registered_files: set[str],
    artifact_records: dict[str, dict[str, Any]],
    result: dict[str, Any],
) -> None:
    if set(required_evidence) != set(expected_ids):
        result["mismatched_files"].append("manifest.json:required_evidence_profile")
    for evidence_id in expected_ids:
        linked = required_evidence.get(evidence_id)
        if not isinstance(linked, list) or not linked:
            result["missing_files"].append(f"evidence:{evidence_id}")
            continue
        for reference in linked:
            if isinstance(reference, dict):
                _verify_cross_run_reference(
                    evidence_id, reference, result, bundle_directory=directory
                )
                continue
            if not isinstance(reference, str):
                result["mismatched_files"].append(
                    f"evidence:{evidence_id}:reference-type"
                )
                continue
            if reference.startswith("file:"):
                relative_path = reference.removeprefix("file:")
                if relative_path not in registered_files:
                    result["mismatched_files"].append(
                        f"evidence:{evidence_id}:unknown-file:{relative_path}"
                    )
            elif reference.startswith("artifact:"):
                artifact_id = reference.removeprefix("artifact:")
                record = artifact_records.get(artifact_id)
                if record is None:
                    result["mismatched_files"].append(
                        f"evidence:{evidence_id}:unknown-artifact:{artifact_id}"
                    )
                elif evidence_id not in record.get("evidence_requirement_ids", []):
                    result["mismatched_files"].append(
                        f"evidence:{evidence_id}:cross-link:{artifact_id}"
                    )
            elif reference != "intrinsic:sealed-manifest":
                result["mismatched_files"].append(
                    f"evidence:{evidence_id}:unknown-reference:{reference}"
                )


def _verify_cross_run_reference(
    evidence_id: str,
    reference: dict[str, Any],
    result: dict[str, Any],
    *,
    bundle_directory: Path,
) -> None:
    required = {"origin_run_id", "artifact_id", "artifact_digest", "bundle_digest"}
    if set(reference) != required:
        result["mismatched_files"].append(f"evidence:{evidence_id}:cross-run-fields")
        return
    for field in ("artifact_digest", "bundle_digest"):
        value = reference.get(field)
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            result["mismatched_files"].append(
                f"evidence:{evidence_id}:cross-run-{field}"
            )
            return
    try:
        origin_run_id = str(UUID(str(reference["origin_run_id"])))
        artifact_id = str(UUID(str(reference["artifact_id"])))
    except (ValueError, TypeError):
        result["mismatched_files"].append(f"evidence:{evidence_id}:cross-run-identity")
        return
    origin_directory = bundle_directory.parent / origin_run_id
    origin_verification = verify_bundle(origin_directory, require_all_evidence=False)
    if origin_verification["bundle_status"] != "VERIFIED":
        result["mismatched_files"].append(f"evidence:{evidence_id}:origin-bundle-invalid")
        return
    try:
        origin_manifest = json.loads(
            (origin_directory / "manifest.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        result["mismatched_files"].append(f"evidence:{evidence_id}:origin-manifest")
        return
    if origin_manifest.get("bundle_digest") != reference["bundle_digest"]:
        result["mismatched_files"].append(f"evidence:{evidence_id}:origin-bundle-digest")
    matching = [
        record
        for record in origin_manifest.get("files", [])
        if isinstance(record, dict) and record.get("artifact_id") == artifact_id
    ]
    if len(matching) != 1 or matching[0].get("sha256") != reference["artifact_digest"]:
        result["mismatched_files"].append(f"evidence:{evidence_id}:origin-artifact")


def _verify_artifact_envelope(
    directory: Path,
    record: dict[str, Any],
    result: dict[str, Any],
) -> None:
    if record.get("mime_type") != "application/json":
        return
    relative_path = record["path"]
    try:
        payload = json.loads(_relative(directory, relative_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        result["mismatched_files"].append(f"{relative_path}:envelope")
        return
    required = {
        "schema_version",
        "artifact_id",
        "run_id",
        "subject_ref",
        "phase",
        "step_id",
        "attempt",
        "evidence_requirement_ids",
        "artifact_type",
        "captured_at",
        "source_locator",
        "content",
    }
    if not isinstance(payload, dict) or not required.issubset(payload):
        result["mismatched_files"].append(f"{relative_path}:envelope")
        return
    if payload.get("schema_version") != "controlproof.artifact.v1":
        result["mismatched_files"].append(f"{relative_path}:schema_version")
    if payload.get("artifact_id") != record.get("artifact_id"):
        result["mismatched_files"].append(f"{relative_path}:artifact_id")
    dimensions = (
        "subject_ref",
        "phase",
        "step_id",
        "attempt",
        "evidence_requirement_ids",
        "artifact_type",
    )
    for key in dimensions:
        if key not in record:
            result["mismatched_files"].append(f"{relative_path}:manifest_metadata")
            break
        if payload.get(key) != record.get(key):
            result["mismatched_files"].append(f"{relative_path}:{key}")
    try:
        run = json.loads((directory / "run.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if payload.get("run_id") != run.get("run_id"):
        result["mismatched_files"].append(f"{relative_path}:run_id")


def _verify_manifest_run_link(
    directory: Path,
    manifest: dict[str, Any],
    result: dict[str, Any],
) -> None:
    try:
        run = json.loads((directory / "run.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(run, dict) or manifest.get("run_id") != run.get("run_id"):
        result["mismatched_files"].append("manifest.json:run_id")


def _verify_snapshot_links(directory: Path, result: dict[str, Any]) -> None:
    try:
        run = json.loads((directory / "run.json").read_text(encoding="utf-8"))
        target = json.loads((directory / "target.snapshot.json").read_text(encoding="utf-8"))
        scenario_payload = (directory / "scenario.snapshot.yaml").read_bytes()
    except (OSError, json.JSONDecodeError):
        return
    target_identity = {
        key: value for key, value in target.items() if key not in {"captured_at", "target_version"}
    }
    target_version = f"target-snapshot:sha256:{sha256_bytes(canonical_json_bytes(target_identity))}"
    if (
        run.get("target_version") != target_version
        or target.get("target_version") != target_version
    ):
        result["mismatched_files"].append("target.snapshot.json:link")
    if target.get("git_dirty") is not False or target.get("git_diff_digest") is not None:
        result["mismatched_files"].append("target.snapshot.json:dirty-run")
    try:
        scenario = json.loads(scenario_payload)
    except json.JSONDecodeError:
        scenario = None
    if isinstance(scenario, dict):
        definition = scenario.get("definition")
        expected = sha256_bytes(canonical_json_bytes(definition)) if definition else None
        if run.get("scenario_digest") != expected or scenario.get("digest") != expected:
            result["mismatched_files"].append("scenario.snapshot.yaml:link")


def _verify_spec002_snapshot_links(
    directory: Path,
    manifest: dict[str, Any],
    result: dict[str, Any],
) -> None:
    try:
        run = json.loads((directory / "run.json").read_text(encoding="utf-8"))
        environment = json.loads(
            (directory / "environment.snapshot.json").read_text(encoding="utf-8")
        )
        queue = json.loads(
            (directory / "queue-topology.snapshot.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return
    if not all(isinstance(item, dict) for item in (run, environment, queue)):
        result["mismatched_files"].append("spec002:snapshot-object")
        return
    environment_identity = {
        key: value
        for key, value in environment.items()
        if key not in {"captured_at", "snapshot_digest"}
    }
    queue_identity = {
        key: value
        for key, value in queue.items()
        if key not in {"captured_at", "snapshot_digest"}
    }
    environment_digest = sha256_bytes(canonical_json_bytes(environment_identity))
    queue_digest = sha256_bytes(canonical_json_bytes(queue_identity))
    links = (
        (
            "environment.snapshot.json:link",
            environment_digest,
            environment.get("snapshot_digest"),
            run.get("environment_snapshot_digest"),
            manifest.get("environment_snapshot_digest"),
        ),
        (
            "queue-topology.snapshot.json:link",
            queue_digest,
            queue.get("snapshot_digest"),
            run.get("queue_topology_digest"),
            manifest.get("queue_topology_digest"),
        ),
    )
    for error, expected, embedded, run_digest, manifest_digest in links:
        if not expected == embedded == run_digest == manifest_digest:
            result["mismatched_files"].append(error)
    expected_scope = {"AWS_SQS", "AWS_ECS", "AWS_IAM", "AWS_CLOUDWATCH", "AWS_NETWORK"}
    if (
        run.get("environment_kind") != "LOCAL_EMULATED"
        or run.get("aws_deployment_status") != "NOT_RUN"
        or set(run.get("unverified_scope", [])) != expected_scope
    ):
        result["mismatched_files"].append("run.json:local-environment-claim")
    if (
        environment.get("target_id") != "whyyou-local"
        or environment.get("environment_kind") != "LOCAL_EMULATED"
        or environment.get("aws_deployment_status") != "NOT_RUN"
        or environment.get("external_ai_allowed") is not False
        or set(environment.get("unverified_scope", [])) != expected_scope
    ):
        result["mismatched_files"].append("environment.snapshot.json:local-claim")
    if (
        queue.get("source_queue_name") != "iep-reporting"
        or queue.get("dead_letter_queue_name") != "iep-reporting-dlq"
        or queue.get("max_receive_count") != 3
        or queue.get("visibility_timeout_seconds") != 5
    ):
        result["mismatched_files"].append("queue-topology.snapshot.json:contract")


def _verify_spec004_snapshot_links(
    directory: Path,
    manifest: dict[str, Any],
    profile: ExecutionProfile,
    result: dict[str, Any],
) -> None:
    """Spec 004 Run ↔ manifest ↔ file digest links and the local-only claim."""
    try:
        run = json.loads((directory / "run.json").read_text(encoding="utf-8"))
        environment = json.loads(
            (directory / "environment.snapshot.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(run, dict) or not isinstance(environment, dict):
        result["mismatched_files"].append("spec004:snapshot-object")
        return
    environment_identity = {
        key: value
        for key, value in environment.items()
        if key not in {"captured_at", "snapshot_digest"}
    }
    environment_digest = sha256_bytes(canonical_json_bytes(environment_identity))
    if not (
        environment_digest
        == environment.get("snapshot_digest")
        == run.get("environment_snapshot_digest")
        == manifest.get("environment_snapshot_digest")
    ):
        result["mismatched_files"].append("environment.snapshot.json:link")
    for relative_path, field in (
        ("spec004-lanes.json", "lane_manifest_digest"),
        ("spec004-capabilities.json", "path_capability_digest"),
    ):
        try:
            digest = sha256_bytes((directory / relative_path).read_bytes())
        except OSError:
            continue
        if not digest == run.get(field) == manifest.get(field):
            result["mismatched_files"].append(f"{relative_path}:link")
    if run.get("scoring_rule_source_digest") != manifest.get("scoring_rule_source_digest"):
        result["mismatched_files"].append("manifest.json:scoring_rule_source_digest")
    e02 = profile is ExecutionProfile.E02_SCORING_FREEZE_V1
    if e02 != bool(manifest.get("scoring_rule_source_digest")):
        result["mismatched_files"].append("manifest.json:scoring_rule_source_digest")
    expected_scope = {"AWS", "N-01", "N-03"}
    if (
        run.get("environment_kind") != "LOCAL_EMULATED"
        or run.get("aws_deployment_status") != "NOT_RUN"
        or set(run.get("unverified_scope", [])) != expected_scope
        or environment.get("external_ai_allowed") is not False
    ):
        result["mismatched_files"].append("run.json:spec004-local-claim")


def _verify_spec003_snapshot_links(
    directory: Path,
    manifest: dict[str, Any],
    result: dict[str, Any],
) -> None:
    try:
        run = json.loads((directory / "run.json").read_text(encoding="utf-8"))
        environment = json.loads(
            (directory / "environment.snapshot.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(run, dict) or not isinstance(environment, dict):
        result["mismatched_files"].append("spec003:snapshot-object")
        return
    environment_identity = {
        key: value
        for key, value in environment.items()
        if key not in {"captured_at", "snapshot_digest"}
    }
    environment_digest = sha256_bytes(canonical_json_bytes(environment_identity))
    if not (
        environment_digest
        == environment.get("snapshot_digest")
        == run.get("environment_snapshot_digest")
        == manifest.get("environment_snapshot_digest")
    ):
        result["mismatched_files"].append("environment.snapshot.json:link")
    file_links = (
        ("n02-lanes.json", "lane_manifest_digest"),
        ("n02-capabilities.json", "path_capability_digest"),
        ("policy-and-consent.json", "policy_snapshot_digest"),
    )
    for relative_path, field in file_links:
        try:
            digest = sha256_bytes((directory / relative_path).read_bytes())
        except OSError:
            continue
        if not digest == run.get(field) == manifest.get(field):
            result["mismatched_files"].append(f"{relative_path}:link")
    expected_scope = {"AWS", "N-01", "N-03"}
    if (
        run.get("environment_kind") != "LOCAL_EMULATED"
        or run.get("aws_deployment_status") != "NOT_RUN"
        or set(run.get("unverified_scope", [])) != expected_scope
        or environment.get("external_ai_allowed") is not False
        or set(environment.get("unverified_scope", [])) != expected_scope
    ):
        result["mismatched_files"].append("run.json:n02-local-claim")


def _submitted_and_refused(
    attempts: list[dict[str, Any]], effects: list[dict[str, Any]], lane: str
) -> bool:
    """A runner-submitted assessment input the target refused, with no start or new effect."""
    submitted = any(
        row.get("lane_id") == lane
        and row.get("recovery_stage") != "AFTER_RETRY"
        and row.get("path_id") == "AI_ASSESSMENT"
        and row.get("response_class") == "SUBMITTED"
        for row in attempts
    )
    refused = [
        row
        for row in effects
        if row.get("lane_id") == lane
        and row.get("recovery_stage") != "AFTER_RETRY"
        and row.get("effect_group") == "AI_ASSESSMENT"
    ]
    return (
        submitted
        and bool(refused)
        and all(
            row.get("refusal_receipt_ids")
            and not row.get("start_receipt_ids")
            and row.get("new_effect_ids") == []
            for row in refused
        )
    )


def _verify_spec003_facts(directory: Path, result: dict[str, Any]) -> None:
    """Validate N-02 identities and readable PASS facts after the byte-level seal."""
    documents: dict[str, Any] = {}
    for relative_path in sorted(SPEC003_CANONICAL_FILES):
        path = directory / relative_path
        if not path.is_file():
            continue
        try:
            payload = path.read_bytes()
            assert_redacted(payload)
            if relative_path.endswith(".jsonl"):
                value = [
                    json.loads(line)
                    for line in payload.decode("utf-8").splitlines()
                    if line.strip()
                ]
                if not all(isinstance(item, dict) for item in value):
                    raise ValueError("JSONL rows must be objects")
            else:
                value = json.loads(payload.decode("utf-8"))
            documents[relative_path] = value
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
            result["mismatched_files"].append(
                f"{relative_path}:unreadable-or-unredacted:{type(exc).__name__}"
            )
    run = documents.get("run.json")
    lane_document = documents.get("n02-lanes.json")
    if not isinstance(run, dict) or not isinstance(lane_document, dict):
        return
    run_id = run.get("run_id")
    if run.get("parent_run_id") is not None:
        _verify_spec003_retest_link(directory, run, result)
    lane_rows = lane_document.get("lanes")
    if not isinstance(lane_rows, list):
        result["mismatched_files"].append("n02-lanes.json:lanes")
        return
    lanes: dict[str, str] = {}
    for lane in lane_rows:
        if not isinstance(lane, dict):
            result["mismatched_files"].append("n02-lanes.json:lane-object")
            continue
        lane_id = lane.get("lane_id")
        subject_ref = lane.get("subject_ref")
        if not isinstance(lane_id, str) or not isinstance(subject_ref, str):
            result["mismatched_files"].append("n02-lanes.json:lane-identity")
            continue
        if lane_id in lanes or subject_ref in lanes.values():
            result["mismatched_files"].append("n02-lanes.json:duplicate-lane-or-subject")
        lanes[lane_id] = subject_ref
        if lane.get("run_id", run_id) != run_id:
            result["mismatched_files"].append(f"n02-lanes.json:{lane_id}:run")

    def check_identity(row: dict[str, Any], source: str) -> None:
        lane_id = row.get("lane_id")
        if (
            row.get("run_id") != run_id
            or not isinstance(lane_id, str)
            or lanes.get(lane_id) != row.get("subject_ref")
        ):
            result["mismatched_files"].append(f"{source}:lane-subject-run")

    row_files = (
        "observations.jsonl",
        "baseline-effects.jsonl",
        "bypass-attempts.jsonl",
        "protected-effects.jsonl",
        "causal-events.jsonl",
        "fault-receipts.jsonl",
    )
    for name in row_files:
        rows = documents.get(name, ())
        if not isinstance(rows, list):
            result["mismatched_files"].append(f"{name}:rows")
            continue
        for row in rows:
            check_identity(row, name)
    for name in ("policy-and-consent.json", "recovery.json"):
        value = documents.get(name)
        if isinstance(value, dict) and "lane_id" in value:
            check_identity(value, name)

    attempts = documents.get("bypass-attempts.jsonl", [])
    effects = documents.get("protected-effects.jsonl", [])
    if not isinstance(attempts, list) or not isinstance(effects, list):
        return
    attempts_by_id = {
        item["attempt_id"]: item
        for item in attempts if isinstance(item.get("attempt_id"), str)
    }
    attempts_by_request = {
        item["request_id"]: item
        for item in attempts if isinstance(item.get("request_id"), str)
    }
    observer_receipts = {
        item.get("receipt_id"): item
        for item in documents.get("observations.jsonl", [])
        if isinstance(item, dict)
        and item.get("schema_version") == "controlproof.whyyou-processing-receipt.v1"
        and isinstance(item.get("receipt_id"), str)
    }
    for effect in effects:
        linked = []
        attempt_id = effect.get("attempt_id")
        if attempt_id is not None:
            if attempt_id not in attempts_by_id:
                result["mismatched_files"].append("protected-effects.jsonl:unknown-attempt")
            else:
                linked.append(attempts_by_id[attempt_id])
        request_ids = effect.get("request_ids", [])
        if not isinstance(request_ids, list):
            result["mismatched_files"].append("protected-effects.jsonl:request-ids")
            continue
        for request_id in request_ids:
            attempt = attempts_by_request.get(request_id)
            if attempt is not None:
                linked.append(attempt)
        probe_inputs = effect.get("probe_input_effect_ids", [])
        if probe_inputs:
            matching_attempts = [
                attempt for attempt in attempts
                if attempt.get("lane_id") == effect.get("lane_id")
                and attempt.get("subject_ref") == effect.get("subject_ref")
                and attempt.get("path_id") == effect.get("path_id")
                and attempt.get("probe_input_effect_id") in probe_inputs
            ]
            if len(matching_attempts) != len(probe_inputs) or any(
                item in effect.get("new_effect_ids", []) for item in probe_inputs
            ):
                result["mismatched_files"].append("protected-effects.jsonl:probe-input-link")
        for receipt_id in (
            effect.get("start_receipt_ids", [])
            if effect.get("path_id") == "AI_ASSESSMENT" and probe_inputs
            else []
        ):
            receipt = observer_receipts.get(receipt_id)
            expected_event_ids = {
                item.removeprefix("event:") for item in probe_inputs
                if isinstance(item, str)
            }
            if (
                receipt is None
                or receipt.get("lane_id") != effect.get("lane_id")
                or receipt.get("subject_ref") != effect.get("subject_ref")
                or receipt.get("path_id") != effect.get("path_id")
                or receipt.get("boundary") != "REPORT_ASSESSMENT_STARTED"
                or receipt.get("request_or_event_id") not in expected_event_ids
            ):
                result["mismatched_files"].append("protected-effects.jsonl:start-receipt-link")
        for receipt_id in effect.get("refusal_receipt_ids", []):
            receipt = observer_receipts.get(receipt_id)
            if (
                not probe_inputs
                or receipt is None
                or receipt.get("lane_id") != effect.get("lane_id")
                or receipt.get("subject_ref") != effect.get("subject_ref")
                or receipt.get("path_id") != effect.get("path_id")
                or receipt.get("boundary") != "REPORT_ASSESSMENT_REFUSED"
                or receipt.get("request_or_event_id")
                not in {item.removeprefix("event:") for item in probe_inputs if isinstance(item, str)}
            ):
                result["mismatched_files"].append("protected-effects.jsonl:refusal-receipt-link")
        if any(
            attempt.get("lane_id") != effect.get("lane_id")
            or attempt.get("subject_ref") != effect.get("subject_ref")
            or attempt.get("path_id") != effect.get("effect_group")
            for attempt in linked
        ):
            result["mismatched_files"].append("protected-effects.jsonl:attempt-effect-link")

    events = documents.get("causal-events.jsonl", [])
    if not isinstance(events, list):
        return
    event_by_id = {
        item["causal_event_id"]: item
        for item in events if isinstance(item.get("causal_event_id"), str)
    }
    edges = documents.get("causal-edges.jsonl", [])
    if not isinstance(edges, list):
        return
    for edge in edges:
        before = event_by_id.get(edge.get("from_event_id"))
        after = event_by_id.get(edge.get("to_event_id"))
        if (
            before is None
            or after is None
            or any(
                before.get(key) != after.get(key) for key in ("run_id", "lane_id", "subject_ref")
            )
        ):
            result["mismatched_files"].append("causal-edges.jsonl:event-link")

    policy = documents.get("policy-and-consent.json")
    failed_request_id = policy.get("failed_request_id") if isinstance(policy, dict) else None
    receipts = documents.get("fault-receipts.jsonl", [])
    if not isinstance(receipts, list):
        return
    for receipt in receipts:
        if receipt.get("lane_id") != "CONSENT_FAULT_RECOVERY":
            result["mismatched_files"].append("fault-receipts.jsonl:fault-lane")
        if failed_request_id and receipt.get("request_id") != failed_request_id:
            result["mismatched_files"].append("fault-receipts.jsonl:failed-request")

    judgement = documents.get("judgement.json")
    assertions = documents.get("assertions.json")
    if not isinstance(judgement, dict) or not isinstance(assertions, list):
        return
    judged = judgement.get("assertion_results", [])
    valid_assertion_rows = isinstance(judged, list) and all(
        isinstance(item, dict) for item in judged + assertions
    )
    if ("run_id" in judgement or "assertion_results" in judgement or judgement.get("verdict") == "PASS") and (
        judgement.get("run_id") != run_id
        or not valid_assertion_rows
        or [(item.get("assertion_id"), item.get("status")) for item in judged]
        != [(item.get("assertion_id"), item.get("status")) for item in assertions]
    ):
        result["mismatched_files"].append("assertions.json:judgement-link")
    if judgement.get("verdict") == "PASS":
        if not valid_assertion_rows:
            result["mismatched_files"].append("judgement.json:pass-assertions-unreadable")
            return
        if {
            item.get("assertion_id") for item in judged if item.get("status") == "PASS"
        } != {f"N02-A{index}" for index in range(1, 8)}:
            result["mismatched_files"].append("judgement.json:pass-assertions")
        required_rows = (
            "n02-lanes.json",
            "policy-and-consent.json",
            "baseline-effects.jsonl",
            "bypass-attempts.jsonl",
            "protected-effects.jsonl",
            "causal-events.jsonl",
            "causal-edges.jsonl",
            "fault-receipts.jsonl",
            "recovery.json",
        )
        for name in required_rows:
            value = documents.get(name)
            if name == "n02-lanes.json":
                readable = len(lanes) == 6
            elif name.endswith(".jsonl"):
                readable = isinstance(value, list) and bool(value)
            else:
                readable = isinstance(value, dict) and len(value) > 1
            if not readable:
                result["mismatched_files"].append(f"{name}:pass-facts-unreadable")
    _verify_spec003_pass_assertions(documents, result)


def _verify_spec003_retest_link(
    directory: Path,
    run: dict[str, Any],
    result: dict[str, Any],
    *,
    evidence_id: str = "EV3-10",
    label: str = "n02-retest",
) -> None:
    """A child is valid only while its sealed parent and comparison files remain intact."""
    try:
        parent_id = str(UUID(str(run["parent_run_id"])))
        child_id = str(UUID(str(run["run_id"])))
        link = json.loads((directory / "retest-link.json").read_text(encoding="utf-8"))
        diff = json.loads((directory / "retest-diff.json").read_text(encoding="utf-8"))
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        parent_dir = directory.parent / parent_id
        parent_manifest = json.loads((parent_dir / "manifest.json").read_text(encoding="utf-8"))
        parent_run = json.loads((parent_dir / "run.json").read_text(encoding="utf-8"))
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        result["mismatched_files"].append(f"{label}:unreadable-link")
        return
    required = manifest.get("required_evidence", {}).get(evidence_id, [])
    if (
        parent_id == child_id
        or parent_run.get("parent_run_id") == child_id
        or link.get("parent_run_id") != parent_id
        or link.get("child_run_id") != child_id
        or diff.get("parent_run_id") != parent_id
        or diff.get("child_run_id") != child_id
        or "file:retest-link.json" not in required
        or "file:retest-diff.json" not in required
        or link.get("parent_bundle_digest") != parent_manifest.get("bundle_digest")
        or link.get("parent_judgement_sha256")
        != next(
            (row.get("sha256") for row in parent_manifest.get("files", [])
             if row.get("path") == "judgement.json"),
            None,
        )
    ):
        result["mismatched_files"].append(f"{label}:parent-link")
        return
    if verify_bundle(parent_dir, require_all_evidence=False)["bundle_status"] != "VERIFIED":
        result["mismatched_files"].append(f"{label}:parent-invalid")


def _verify_spec003_pass_assertions(
    documents: dict[str, Any], result: dict[str, Any]
) -> None:
    judgement = documents.get("judgement.json")
    if not isinstance(judgement, dict):
        return
    judged = judgement.get("assertion_results", [])
    if not isinstance(judged, list):
        return
    passed = {
        item.get("assertion_id")
        for item in judged
        if isinstance(item, dict) and item.get("status") == "PASS"
    }
    if not passed:
        return
    baselines = documents.get("baseline-effects.jsonl", [])
    attempts = documents.get("bypass-attempts.jsonl", [])
    effects = documents.get("protected-effects.jsonl", [])
    events = documents.get("causal-events.jsonl", [])
    edges = documents.get("causal-edges.jsonl", [])
    receipts = documents.get("fault-receipts.jsonl", [])
    policy = documents.get("policy-and-consent.json", {})
    recovery = documents.get("recovery.json", {})
    if not all(isinstance(value, list) for value in (baselines, attempts, effects, events, edges, receipts)):
        result["mismatched_files"].append("spec003:pass-fact-types")
        return
    if "N02-A1" in passed and not any(
        row.get("lane_id") == "PRISTINE_BASELINE"
        and row.get("source_status") != "UNAVAILABLE"
        and not row.get("new_effect_ids")
        for row in baselines
    ):
        result["mismatched_files"].append("N02-A1:baseline-unreadable")
    paths = {
        "N02-A2": ("DOCUMENT_ANALYSIS", "DOCUMENT_BYPASS"),
        "N02-A3": ("RECORDING", "RECORDING_BOUNDARY_PROBE"),
        "N02-A4": ("AI_ASSESSMENT", "ASSESSMENT_BOUNDARY_PROBE"),
    }
    for assertion_id, (path, lane) in paths.items():
        if assertion_id not in passed:
            continue
        denied = any(
            row.get("lane_id") == lane
            and row.get("path_id") == path
            and row.get("response_class") == "DENIED"
            for row in attempts
        )
        zero_delta = any(
            row.get("lane_id") == lane
            and row.get("effect_group") == path
            and row.get("source_status") in {"ABSENT", "PRESENT"}
            and row.get("new_effect_ids") == []
            for row in effects
        )
        # ID-003-17: for the runner-submitted assessment input, a linked target refusal with
        # no start and no new effect stands in for an HTTP denial.
        refused = path == "AI_ASSESSMENT" and _submitted_and_refused(attempts, effects, lane)
        if not (denied or refused) or not zero_delta:
            result["mismatched_files"].append(f"{assertion_id}:denied-zero-delta-unreadable")
    if "N02-A5" in passed:
        policy_value = policy.get("policy", policy) if isinstance(policy, dict) else {}
        consent = policy.get("consent") if isinstance(policy, dict) else None
        committed = [
            row for row in events
            if row.get("kind") == "CONSENT_COMMITTED" and row.get("lane_id") == "NORMAL_ORDER"
        ]
        adjacency: dict[str, set[str]] = {}
        for edge in edges:
            if edge.get("status") == "PROVEN":
                adjacency.setdefault(str(edge.get("from_event_id")), set()).add(
                    str(edge.get("to_event_id"))
                )

        def reachable(start: str, goal: str) -> bool:
            pending = [start]
            visited: set[str] = set()
            while pending:
                current = pending.pop()
                if current == goal:
                    return True
                if current in visited:
                    continue
                visited.add(current)
                pending.extend(adjacency.get(current, set()) - visited)
            return False

        path_order_proven = all(
            any(
                reachable(
                    str(commit.get("causal_event_id")),
                    str(event.get("causal_event_id")),
                )
                for commit in committed
                for event in events
                if event.get("path_id") == path
                and event.get("kind") == kind
                and event.get("lane_id") == "NORMAL_ORDER"
            )
            for path in ("DOCUMENT_ANALYSIS", "RECORDING", "AI_ASSESSMENT")
            for kind in ("PROCESSING_REQUESTED", "PROCESSING_STARTED", "RESULT_CREATED")
        )
        if (
            not isinstance(policy_value, dict)
            or not policy_value.get("policy_version")
            or not policy_value.get("content_digest")
            or not isinstance(consent, dict)
            or not consent.get("consent_record_ids")
            or not committed
            or not path_order_proven
        ):
            result["mismatched_files"].append("N02-A5:policy-causal-facts-unreadable")
    if "N02-A6" in passed:
        failed_state = policy.get("failed_state") if isinstance(policy, dict) else None
        fault_attempt_paths = {
            row.get("path_id")
            for row in attempts
            if row.get("lane_id") == "CONSENT_FAULT_RECOVERY"
            and row.get("recovery_stage") != "AFTER_RETRY"
            and row.get("response_class") == "DENIED"
        } | (
            {"AI_ASSESSMENT"}
            if _submitted_and_refused(attempts, effects, "CONSENT_FAULT_RECOVERY")
            else set()
        )
        zero_effect_paths = {
            row.get("effect_group")
            for row in effects
            if row.get("lane_id") == "CONSENT_FAULT_RECOVERY"
            and row.get("recovery_stage") != "AFTER_RETRY"
            and row.get("source_status") in {"ABSENT", "PRESENT"}
            and row.get("new_effect_ids") == []
        }
        if (
            not receipts
            or not isinstance(policy, dict)
            or not policy.get("failed_request_id")
            or any(row.get("request_id") != policy.get("failed_request_id") for row in receipts)
            or not isinstance(failed_state, dict)
            or failed_state.get("source_status") == "UNAVAILABLE"
            or failed_state.get("active_consent_count") != 0
            or failed_state.get("consent_record_ids") != []
            or failed_state.get("consent_completed_event_ids") != []
            or fault_attempt_paths != {"DOCUMENT_ANALYSIS", "RECORDING", "AI_ASSESSMENT"}
            or zero_effect_paths != {"DOCUMENT_ANALYSIS", "RECORDING", "AI_ASSESSMENT"}
            or not isinstance(recovery, dict)
            or recovery.get("failed_request_effects_zero") is not True
            or recovery.get("marker_removed") is not True
            or recovery.get("consumed_token_removed") is not True
            or recovery.get("hook_inactive") is not True
        ):
            result["mismatched_files"].append("N02-A6:fault-rollback-facts-unreadable")
    if "N02-A7" in passed and (
        not isinstance(recovery, dict)
        or recovery.get("restore_status") != "SUCCEEDED"
        or recovery.get("logical_consent_count") != 1
        or recovery.get("consent_completed_event_count") != 1
        or recovery.get("processing_order_proven") is not True
        or recovery.get("normal_retry_succeeded") is not True
        or recovery.get("manual_cleanup_required") is not False
    ):
        result["mismatched_files"].append("N02-A7:recovery-facts-unreadable")
    if "N02-A7" in passed and not _recovered_n02_proof_readable(
        policy, recovery, attempts, effects, events, edges
    ):
        result["mismatched_files"].append("N02-A7:recovered-proof-unreadable")


def _recovered_n02_proof_readable(policy, recovery, attempts, effects, events, edges) -> bool:
    """Recompute recovered order from sealed facts, rather than summary booleans."""
    from engine.judges.n02 import N02NormalOrderCase, judge_n02_normal_order
    from engine.models import (
        CausalEdge,
        CausalEvent,
        ConsentPolicySnapshot,
        ConsentStateSnapshot,
        ProcessingAttemptReceipt,
        ProtectedEffectSnapshot,
    )

    lane = "CONSENT_FAULT_RECOVERY"
    try:
        state = ConsentStateSnapshot.model_validate(policy["recovered_state"])
        safe = ConsentStateSnapshot.model_validate(policy["safe_state"])
        recovered_policy = ConsentPolicySnapshot.model_validate(policy["recovered_policy"])
        commit = policy["recovered_commit"]
        if (
            commit.get("ok") is not True
            or not commit.get("request_id")
            or safe.source_status.value != "ABSENT"
            or safe.invitation_status != "identity_verified"
            or safe.active_consent_count != 0
            or safe.consent_record_ids
            or safe.consented_state_change_ids
            or safe.consent_completed_event_ids
            or len(state.consent_record_ids) != 1
        ):
            return False
        retry_attempts = tuple(
            ProcessingAttemptReceipt.model_validate(row)
            for row in attempts
            if row.get("lane_id") == lane and row.get("recovery_stage") == "AFTER_RETRY"
        )
        retry_effects = tuple(
            ProtectedEffectSnapshot.model_validate(row)
            for row in effects
            if row.get("lane_id") == lane and row.get("recovery_stage") == "AFTER_RETRY"
        )
        retry_events = tuple(
            CausalEvent.model_validate(row) for row in events if row.get("lane_id") == lane
        )
        retry_edges = tuple(
            CausalEdge.model_validate(row) for row in edges if row.get("lane_id") == lane
        )
        paths = {"DOCUMENT_ANALYSIS", "RECORDING", "AI_ASSESSMENT"}
        if (
            len(retry_attempts) != 3
            or len(retry_effects) != 3
            or {row.path_id.value for row in retry_attempts} != paths
            or {row.path_id.value for row in retry_effects} != paths
            or any(not row.new_effect_ids or not row.start_receipt_ids for row in retry_effects)
        ):
            return False
        for row in (state, safe, *retry_attempts, *retry_effects, *retry_events, *retry_edges):
            if (
                str(row.run_id) != recovery.get("run_id")
                or row.lane_id.value != lane
                or row.subject_ref != recovery.get("subject_ref")
            ):
                return False
        return (
            judge_n02_normal_order(
                N02NormalOrderCase(
                    recovered_policy,
                    state,
                    retry_attempts,
                    retry_effects,
                    retry_events,
                    retry_edges,
                )
            ).status.value
            == "PASS"
        )
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


# --- Spec 004 cross-reference, redaction and recompute re-execution (T067) -------------------------

_E01_INVALID_MODES = ("EMPTY", "NONEXISTENT", "OTHER_APPLICANT", "OTHER_CRITERION")
_REMOVAL_PHASES = ("PRE_REMOVAL", "POST_REMOVAL", "POST_RESTORE")


def _spec004_rows(directory: Path, name: str) -> list[dict[str, Any]]:
    path = directory / name
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _spec004_assertions(directory: Path) -> dict[str, dict[str, Any]]:
    rows = json.loads((directory / "assertions.json").read_text(encoding="utf-8"))
    return {item["assertion_id"]: item for item in rows}


def _spec004_redaction(directory: Path, profile: ExecutionProfile, result: dict[str, Any]) -> None:
    for name in sorted(spec004_required_files(profile) | SPEC004_BASE_FILES):
        path = directory / name
        if not path.exists() or not name.endswith((".json", ".jsonl")):
            continue
        try:
            assert_redacted(path.read_bytes())
        except ValueError:
            result["redaction_violations"].append(name)


def _spec004_lane_refs(directory: Path, errors: list[str]) -> dict[str, dict[str, Any]]:
    document = json.loads((directory / "spec004-lanes.json").read_text(encoding="utf-8"))
    lanes = {lane["lane_id"]: lane for lane in document.get("lanes", [])}
    pairs = {(lane_id, lane["subject_ref"]) for lane_id, lane in lanes.items()}
    for name in ("report-records.jsonl", "change-injections.jsonl"):
        for row in _spec004_rows(directory, name):
            if (row.get("lane_id"), row.get("subject_ref")) not in pairs:
                errors.append(f"{name}:lane")
                break
    for row in _spec004_rows(directory, "report-reads.jsonl"):
        if row.get("lane_id") not in lanes:
            errors.append("report-reads.jsonl:lane")
            break
    return lanes


def _spec004_e01_refs(
    directory: Path, lanes: dict[str, dict[str, Any]], errors: list[str]
) -> None:
    receipts = {
        row.get("receipt_id"): row for row in _spec004_rows(directory, "model-emissions.jsonl")
    }
    criteria = {
        f"{lane_id}:{criterion['code']}": criterion["criterion_id"]
        for lane_id, lane in lanes.items()
        for criterion in lane.get("criteria", [])
    }
    cases = _spec004_rows(directory, "citation-cases.jsonl")
    for case in cases:
        receipt_id = case.get("emission_receipt_id")
        if receipt_id is None:
            continue
        receipt = receipts.get(receipt_id)
        if receipt is None or receipt.get("criterion_id") != criteria.get(case.get("case_id")):
            errors.append("citation-cases.jsonl:receipt")
            break
    removal = [
        row["phase"]
        for row in _spec004_rows(directory, "report-reads.jsonl")
        if row.get("lane_id") == "E01_EVIDENCE_REMOVAL" and row.get("phase") in _REMOVAL_PHASES
    ]
    if removal != sorted(removal, key=_REMOVAL_PHASES.index):
        errors.append("report-reads.jsonl:order")
    # A PASS is re-derived from the files, never restored from a stored boolean.
    if _spec004_assertions(directory).get("E01-A1", {}).get("status") == "PASS":
        by_mode = {case.get("mode"): case for case in cases}
        if any(
            by_mode.get(mode, {}).get("outcome") != "EMPTIED"
            or by_mode.get(mode, {}).get("emission_receipt_id") not in receipts
            for mode in _E01_INVALID_MODES
        ):
            errors.append("assertions.json:E01-A1")


def _spec004_recompute(directory: Path, errors: list[str]) -> tuple[bool, dict[str, Any]]:
    from engine.judges.e02 import _equal
    from engine.judges.e02_scoring import RULE_COPY_ID, report_aggregate

    document = json.loads((directory / "recompute.json").read_text(encoding="utf-8"))
    mismatch = False
    for record in document.get("records", []):
        if record is None:
            continue
        if record.get("rule_copy_id") != RULE_COPY_ID:
            errors.append("recompute.json:rule_copy_id")
            mismatch = True
            continue
        inputs = record.get("inputs", {})
        items = [
            item | {"axes": [tuple(axis) for axis in item.get("axes", [])]}
            for item in inputs.get("items", [])
        ]
        again = report_aggregate(items, inputs.get("config_version", ""))
        computed = {
            "score": again.score,
            "numerator": again.numerator,
            "denominator": again.denominator,
        }
        if not _equal(computed, record.get("computed")):
            errors.append("recompute.json:computed")
            mismatch = True
        if any(
            bool(item.get("equal")) != _equal(item.get("expected"), item.get("observed"))
            for item in record.get("comparisons", [])
        ):
            errors.append("recompute.json:comparison")
            mismatch = True
    return mismatch, document


def _spec004_e02_refs(directory: Path, errors: list[str], result: dict[str, Any]) -> None:
    mismatch, document = _spec004_recompute(directory, errors)
    result["recompute_reexecution"] = "MISMATCH" if mismatch else "MATCH"
    assertions = _spec004_assertions(directory)
    if assertions.get("E02-A2", {}).get("status") == "PASS":
        steps = {
            row.get("step"): row.get("state_digest")
            for row in _spec004_rows(directory, "report-records.jsonl")
        }
        before, after = steps.get("capture-pre-change"), steps.get("capture-post-change")
        if before is None or before != after:
            errors.append("assertions.json:E02-A2")
    records = document.get("records") or []
    complete = bool(records) and all(
        record is not None and all(item.get("equal") for item in record.get("comparisons", []))
        for record in records
    )
    if assertions.get("E02-A3", {}).get("status") == "PASS" and (mismatch or not complete):
        errors.append("assertions.json:E02-A3")


def _verify_spec004_facts(
    directory: Path, profile: ExecutionProfile, result: dict[str, Any]
) -> None:
    errors: list[str] = []
    result["cross_reference_errors"] = errors
    result["redaction_violations"] = []
    result["recompute_reexecution"] = "NOT_APPLICABLE"
    _spec004_redaction(directory, profile, result)
    try:
        run = json.loads((directory / "run.json").read_text(encoding="utf-8"))
        if run.get("parent_run_id"):
            _verify_spec003_retest_link(
                directory, run, result, evidence_id="EV4-10", label="spec004-retest"
            )
        lanes = _spec004_lane_refs(directory, errors)
        for row in _spec004_rows(directory, "change-injections.jsonl"):
            if row.get("state") == "RESTORED" and (
                row.get("post_restore_digest") != row.get("pre_projection_digest")
            ):
                errors.append("change-injections.jsonl:restore")
        if profile is ExecutionProfile.E01_CITATION_EVIDENCE_V1:
            _spec004_e01_refs(directory, lanes, errors)
        else:
            _spec004_e02_refs(directory, errors, result)
    except (OSError, KeyError, TypeError, ValueError, AttributeError):
        errors.append("spec004:facts-unreadable")
    if errors or result["redaction_violations"]:
        result["bundle_status"] = "INVALID"
