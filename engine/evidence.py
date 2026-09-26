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
    EvidenceArtifact,
    IntegrityStatus,
    Phase,
    Run,
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
PHONE_RE = re.compile(r"(?<!\d)(?:01[016789]|\+82[- ]?1[016789])[- ]?\d{3,4}[- ]?\d{4}(?!\d)")
BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
SIGNED_QUERY_RE = re.compile(r"(?i)(X-Amz-Signature|signature|sig|token)=([^&\s]+)")

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


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            lowered = key.casefold()
            if (
                lowered in FORBIDDEN_KEYS
                or lowered in PII_KEYS
                or lowered.endswith(("_token", "_token_hash"))
            ):
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
        return text
    return value


def assert_redacted(payload: bytes) -> None:
    text = payload.decode("utf-8", errors="ignore")
    if BEARER_RE.search(text) or EMAIL_RE.search(text) or PHONE_RE.search(text):
        raise ValueError("redaction scanner found prohibited secret or PII pattern")


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
        self.directory = (run_root.resolve() / str(run.run_id)).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self._files: dict[str, dict[str, Any]] = {}
        self._required: dict[str, list[str]] = {f"EV-{index:02d}": [] for index in range(1, 10)}

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
        if mime_type.startswith("text/") or mime_type in {"application/json", "application/yaml"}:
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
            self._required[evidence_id].append(str(active_id))
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
            self._required[evidence_id].append(str(active_id))
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
        missing_canonical = sorted(CANONICAL_FILES - set(self._files))
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
    for canonical in sorted(CANONICAL_FILES):
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
            for artifact_type in sorted(
                REQUIRED_EVIDENCE_ARTIFACT_TYPES[evidence_id] - linked_types
            ):
                result["mismatched_files"].append(
                    f"evidence:{evidence_id}:artifact-type:{artifact_type}"
                )
    _verify_manifest_run_link(directory, manifest, result)
    _verify_snapshot_links(directory, result)
    if result["missing_files"] or result["mismatched_files"]:
        result["bundle_status"] = "INVALID"
    result["missing_files"].sort()
    result["mismatched_files"].sort()
    return result


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
