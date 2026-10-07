"""Immutable parent verification and child Run comparison records."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID

from engine.evidence import verify_bundle
from engine.lifecycle import RestoreBlockStore
from engine.models import (
    SPEC003_UNVERIFIED_SCOPE,
    SPEC004_PROFILES,
    SPEC004_UNVERIFIED_SCOPE,
    TERMINAL_RUN_STATES,
    ExecutionProfile,
    FaultVariant,
    N02LaneId,
    QueueTopologySnapshot,
    RetestLink,
    Run,
    RunState,
    RunSubjectLane,
    TargetEnvironmentSnapshot,
    TargetSnapshot,
    TestSubject,
    canonical_json_bytes,
    sha256_bytes,
    utcnow,
)


class RetestError(RuntimeError):
    pass


def prepare_retest(
    parent_bundle: Path,
    *,
    child_run_id: UUID,
    child_target: TargetSnapshot,
    child_scenario_version: str,
    child_scenario_digest: str,
    child_profile: ExecutionProfile | None = None,
    child_fault_variant: FaultVariant | None = None,
    child_environment: TargetEnvironmentSnapshot | None = None,
    child_queue: QueueTopologySnapshot | None = None,
    cleanup_evidence: Path | None = None,
) -> tuple[Run, str, dict[str, Any]]:
    directory = parent_bundle.resolve()
    verification = verify_bundle(directory)
    if verification["bundle_status"] != "VERIFIED":
        raise RetestError("parent Evidence Bundle failed integrity verification")
    parent_run = Run.model_validate(_read(directory / "run.json"))
    if parent_run.state not in TERMINAL_RUN_STATES:
        raise RetestError("retest parent must be terminal")
    parent_profile = parent_run.execution_profile or ExecutionProfile.H03_MINIMAL_V1
    cleanup_confirmation = None
    if parent_profile is ExecutionProfile.N02_CONSENT_ORDER_V1:
        if parent_run.state is RunState.RESTORE_FAILED or parent_run.manual_cleanup_required:
            cleanup_confirmation = _verified_n02_cleanup(directory, parent_run, cleanup_evidence)
    elif parent_profile in SPEC004_PROFILES:
        _spec004_cleanup_resolved(directory, parent_run)
    elif parent_run.state is RunState.RESTORE_FAILED or parent_run.manual_cleanup_required:
        raise RetestError("retest parent does not prove safe cleanup")
    if parent_run.run_id == child_run_id:
        raise RetestError("retest child must use a new Run ID")
    parent_target = TargetSnapshot.model_validate(_read(directory / "target.snapshot.json"))
    parent_digest = _read(directory / "manifest.json")["bundle_digest"]
    parent_manifest = _read(directory / "manifest.json")
    active_child_profile = child_profile or ExecutionProfile.H03_MINIMAL_V1
    if active_child_profile is not parent_profile:
        raise RetestError("retest child must inherit the parent execution profile")
    if child_fault_variant is not parent_run.fault_variant:
        raise RetestError("retest child must inherit the parent fault variant")
    if parent_profile is ExecutionProfile.N02_CONSENT_ORDER_V1:
        return _prepare_n02_retest(
            directory=directory,
            parent_run=parent_run,
            parent_manifest=parent_manifest,
            parent_digest=parent_digest,
            parent_target=parent_target,
            child_run_id=child_run_id,
            child_target=child_target,
            child_scenario_version=child_scenario_version,
            child_scenario_digest=child_scenario_digest,
            child_environment=child_environment,
            child_queue=child_queue,
            cleanup_confirmation=cleanup_confirmation,
        )
    if parent_profile in SPEC004_PROFILES:
        return _prepare_spec004_retest(
            directory=directory,
            parent_run=parent_run,
            parent_manifest=parent_manifest,
            parent_digest=parent_digest,
            parent_target=parent_target,
            child_run_id=child_run_id,
            child_target=child_target,
            child_scenario_version=child_scenario_version,
            child_scenario_digest=child_scenario_digest,
            child_environment=child_environment,
            child_queue=child_queue,
        )
    parent_subjects = _read(directory / "subjects.json")
    if not isinstance(parent_subjects, list) or len(parent_subjects) != 1:
        raise RetestError("retest parent must contain exactly one canonical subject")
    try:
        parent_subject = TestSubject.model_validate(parent_subjects[0])
    except (TypeError, ValueError) as exc:
        raise RetestError("retest parent subject contract is invalid") from exc
    changed_target = _diff(parent_target.identity(), child_target.identity())
    environment_diff: dict[str, Any] | None = None
    queue_diff: dict[str, Any] | None = None
    if parent_profile is not ExecutionProfile.H03_MINIMAL_V1:
        if child_environment is None or child_queue is None:
            raise RetestError("Spec 002 retest requires environment and queue snapshots")
        try:
            parent_environment = TargetEnvironmentSnapshot.model_validate(
                _read(directory / "environment.snapshot.json")
            )
            parent_queue = QueueTopologySnapshot.model_validate(
                _read(directory / "queue-topology.snapshot.json")
            )
        except (OSError, TypeError, ValueError) as exc:
            raise RetestError("Spec 002 parent snapshots are invalid") from exc
        environment_diff = {
            "before_digest": parent_environment.snapshot_digest,
            "after_digest": child_environment.snapshot_digest,
            "changed": parent_environment.snapshot_digest
            != child_environment.snapshot_digest,
            "changed_fields": _diff(
                parent_environment.model_dump(
                    mode="json", exclude={"captured_at", "snapshot_digest"}
                ),
                child_environment.model_dump(
                    mode="json", exclude={"captured_at", "snapshot_digest"}
                ),
            ),
        }
        queue_diff = {
            "before_digest": parent_queue.snapshot_digest,
            "after_digest": child_queue.snapshot_digest,
            "changed": parent_queue.snapshot_digest != child_queue.snapshot_digest,
            "changed_fields": _diff(
                parent_queue.model_dump(
                    mode="json", exclude={"captured_at", "snapshot_digest"}
                ),
                child_queue.model_dump(
                    mode="json", exclude={"captured_at", "snapshot_digest"}
                ),
            ),
        }
    diff = {
        "schema_version": "controlproof.retest-diff.v1",
        "parent_run_id": str(parent_run.run_id),
        "child_run_id": str(child_run_id),
        "scenario": {
            "before": {
                "version": parent_run.scenario_version,
                "digest": parent_run.scenario_digest,
            },
            "after": {
                "version": child_scenario_version,
                "digest": child_scenario_digest,
            },
            "changed": (
                parent_run.scenario_version != child_scenario_version
                or parent_run.scenario_digest != child_scenario_digest
            ),
        },
        "target": {
            "before_digest": parent_target.target_version,
            "after_digest": child_target.target_version,
            "changed_fields": changed_target,
        },
        "execution_profile": {
            "before": parent_profile.value,
            "after": active_child_profile.value,
            "changed": parent_profile is not active_child_profile,
        },
        "environment": environment_diff,
        "queue_topology": queue_diff,
        "subject": {
            "subject_ref": parent_subject.subject_ref,
            "role": {
                "before": parent_subject.subject_type,
                "after": None,
                "changed": None,
            },
            "initial_state_digest": {
                "before": parent_subject.initial_state_digest,
                "after": None,
                "changed": None,
            },
        },
        "config": {
            "model_fixture_id": {
                "before": parent_run.model_fixture_id,
                "after": child_target.model_fixture_id,
            },
            "model_fixture_digest": {
                "before": parent_run.model_fixture_digest,
                "after": child_target.model_fixture_digest,
            },
        },
        "fault_condition": {
            "before": parent_run.fault_kind,
            "after": (
                child_fault_variant.value
                if child_fault_variant is not None
                else parent_run.fault_kind
            ),
            "changed": parent_run.fault_kind
            != (
                child_fault_variant.value
                if child_fault_variant is not None
                else parent_run.fault_kind
            ),
        },
        "created_at": utcnow().isoformat(),
    }
    link = RetestLink(
        parent_run_id=parent_run.run_id,
        child_run_id=child_run_id,
        changed_dimensions={
            "scenario": diff["scenario"]["changed"],
            "target_paths": [item["path"] for item in changed_target],
            "environment": environment_diff["changed"] if environment_diff else None,
            "queue_topology": queue_diff["changed"] if queue_diff else None,
        },
        reason="WhyYou 수정 후 독립 Run 재시험",
    )
    records = {
        "link": link.model_dump(mode="json"),
        "diff": diff,
        "_parent_subject": parent_subject.model_dump(mode="json"),
    }
    if parent_profile is not ExecutionProfile.H03_MINIMAL_V1:
        origin = next(
            (
                record
                for record in parent_manifest.get("files", [])
                if isinstance(record, dict)
                and record.get("artifact_id")
                and record.get("sha256")
            ),
            None,
        )
        if origin is None:
            raise RetestError("Spec 002 parent has no reusable origin artifact")
        records["_origin_reference"] = {
            "origin_run_id": str(parent_run.run_id),
            "artifact_id": origin["artifact_id"],
            "artifact_digest": origin["sha256"],
            "bundle_digest": parent_digest,
        }
    return (
        parent_run,
        parent_digest,
        records,
    )


def _prepare_n02_retest(
    *,
    directory: Path,
    parent_run: Run,
    parent_manifest: dict[str, Any],
    parent_digest: str,
    parent_target: TargetSnapshot,
    child_run_id: UUID,
    child_target: TargetSnapshot,
    child_scenario_version: str,
    child_scenario_digest: str,
    child_environment: TargetEnvironmentSnapshot | None,
    child_queue: QueueTopologySnapshot | None,
    cleanup_confirmation: dict[str, Any] | None,
) -> tuple[Run, str, dict[str, Any]]:
    if RestoreBlockStore(directory.parent).blocked(parent_run.target_id, "n02-consent-order"):
        raise RetestError("N-02 retest refused: unresolved manual cleanup block")
    if child_target.target_id != parent_run.target_id:
        raise RetestError("N-02 retest must use the same target")
    if (
        child_scenario_version != parent_run.scenario_version
        or child_scenario_digest != parent_run.scenario_digest
    ):
        raise RetestError("N-02 retest must inherit the parent scenario snapshot")
    if child_queue is not None:
        raise RetestError("N-02 retest has no Spec 002 queue topology")
    if child_environment is None:
        raise RetestError("N-02 retest requires a local environment snapshot")
    if (
        child_environment.target_id != child_target.target_id
        or set(child_environment.unverified_scope) != SPEC003_UNVERIFIED_SCOPE
    ):
        raise RetestError("N-02 retest environment snapshot has the wrong target or scope")
    try:
        parent_environment = TargetEnvironmentSnapshot.model_validate(
            _read(directory / "environment.snapshot.json")
        )
        parent_lanes = tuple(
            RunSubjectLane.model_validate(row)
            for row in _read(directory / "n02-lanes.json")["lanes"]
        )
        parent_paths = _read(directory / "n02-capabilities.json")
        parent_policy = _read(directory / "policy-and-consent.json")["policy"]
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise RetestError("N-02 parent comparison facts are unreadable") from exc
    if len(parent_lanes) != len(N02LaneId) or {lane.lane_id for lane in parent_lanes} != set(N02LaneId):
        raise RetestError("N-02 parent must contain six canonical lanes")
    target_changes = _diff(parent_target.identity(), child_target.identity())
    environment_changes = _diff(
        parent_environment.model_dump(mode="json", exclude={"captured_at", "snapshot_digest"}),
        child_environment.model_dump(mode="json", exclude={"captured_at", "snapshot_digest"}),
    )
    diff = {
        "schema_version": "controlproof.retest-diff.v1",
        "parent_run_id": str(parent_run.run_id),
        "child_run_id": str(child_run_id),
        "scenario": {
            "before": {"version": parent_run.scenario_version, "digest": parent_run.scenario_digest},
            "after": {"version": child_scenario_version, "digest": child_scenario_digest},
            "changed": False,
        },
        "target": {
            "before_digest": parent_target.target_version,
            "after_digest": child_target.target_version,
            "changed_fields": target_changes,
        },
        "execution_profile": {
            "before": ExecutionProfile.N02_CONSENT_ORDER_V1.value,
            "after": ExecutionProfile.N02_CONSENT_ORDER_V1.value,
            "changed": False,
        },
        "environment": {
            "before_digest": parent_environment.snapshot_digest,
            "after_digest": child_environment.snapshot_digest,
            "changed": bool(environment_changes),
            "changed_fields": environment_changes,
        },
        "queue_topology": None,
        "n02": {
            "path_capability": {"before_digest": parent_run.path_capability_digest, "after_digest": None, "changed": None, "changed_fields": []},
            "policy": {"before": _policy_identity(parent_policy), "after": None, "changed": None, "changed_fields": []},
            "lane_fixtures": {"lanes": [], "changed": None},
        },
        "created_at": utcnow().isoformat(),
    }
    link = RetestLink(
        parent_run_id=parent_run.run_id,
        child_run_id=child_run_id,
        changed_dimensions={
            "scenario": False,
            "target_paths": [item["path"] for item in target_changes],
            "environment": bool(environment_changes),
            "path_capability": None,
            "policy": None,
            "lane_fixtures": None,
        },
        reason="WhyYou 수정 후 N-02 독립 Run 재시험",
    )
    origin = next(
        (row for row in parent_manifest.get("files", []) if row.get("path") == "judgement.json"),
        None,
    )
    if not isinstance(origin, dict) or not origin.get("sha256"):
        raise RetestError("N-02 parent judgement origin file is missing")
    link_payload = link.model_dump(mode="json") | {
        "parent_bundle_digest": parent_digest,
        "parent_judgement_sha256": origin["sha256"],
    }
    if cleanup_confirmation is not None:
        link_payload["cleanup_confirmation"] = cleanup_confirmation
    records = {
        "link": link_payload,
        "diff": diff,
        "_n02_parent": {
            "lanes": [item.model_dump(mode="json") for item in parent_lanes],
            "paths": parent_paths,
        },
    }
    return parent_run, parent_digest, records


def _verified_n02_cleanup(
    directory: Path, parent_run: Run, cleanup_evidence: Path | None
) -> dict[str, Any]:
    blocks = RestoreBlockStore(directory.parent)
    if blocks.blocked(parent_run.target_id, "n02-consent-order"):
        raise RetestError("N-02 retest refused: unresolved manual cleanup block")
    if cleanup_evidence is None:
        raise RetestError("N-02 retest requires cleanup evidence")
    try:
        record = _read(blocks.root / "maintenance" / f"{parent_run.run_id}.json")
        evidence_bytes = cleanup_evidence.read_bytes()
        evidence = json.loads(evidence_bytes)
        confirmed_at = datetime.fromisoformat(record["confirmed_at"])
        captured_at = datetime.fromisoformat(evidence["captured_at"])
        parent_subjects = _read(directory / "subjects.json")
        fault_subjects = [
            row for row in parent_subjects
            if row.get("lane_id") == N02LaneId.CONSENT_FAULT_RECOVERY.value
            and row.get("run_id") == str(parent_run.run_id)
        ]
        if len(fault_subjects) != 1:
            raise ValueError("N-02 parent fault subject is not unique")
        fault_subject = fault_subjects[0]
        expected_record = {
            "schema_version": "controlproof.cleanup-confirmation.v1",
            "target_id": parent_run.target_id,
            "subject_ref": "n02-consent-order",
            "blocked_run_id": str(parent_run.run_id),
            "evidence_sha256": sha256(evidence_bytes).hexdigest(),
        }
        if any(record.get(key) != value for key, value in expected_record.items()):
            raise ValueError("N-02 cleanup confirmation does not match parent or evidence")
        expected_evidence = {
            "schema_version": "controlproof.n02-cleanup-evidence.v1",
            "parent_run_id": str(parent_run.run_id),
            "target_id": parent_run.target_id,
            "subject_ref": "n02-consent-order",
            "lane_subject_ref": fault_subject["subject_ref"],
            "invitation_id": fault_subject["invitation_id"],
            "applicant_id": fault_subject["applicant_id"],
            "safe_state_read_only": True,
        }
        if any(evidence.get(key) != value for key, value in expected_evidence.items()):
            raise ValueError("N-02 cleanup evidence does not match parent")
        if (
            confirmed_at.tzinfo is None
            or captured_at.tzinfo is None
            or parent_run.ended_at is None
            or not parent_run.ended_at <= captured_at <= confirmed_at
            or confirmed_at > datetime.now(UTC) + timedelta(seconds=2)
            or confirmed_at - captured_at > timedelta(seconds=300)
        ):
            raise ValueError("N-02 cleanup confirmation time is invalid")
        findings = evidence["findings"]
        if findings.get("invitation") != [["identity_verified", 1]] or any(
            type(findings.get(key)) is not int or findings[key] != 0
            for key in (
                "consent_records", "active_consents", "consented_transitions",
                "consent_completed_events", "all_invitation_events", "upload_intents",
                "submissions", "analyses", "interview_strategies",
            )
        ):
            raise ValueError("N-02 cleanup evidence contains effects")
        files = evidence["fault_files_exist"]
        if any(files.get(key) is not False for key in ("marker", "consumed_token", "fault_receipt")):
            raise ValueError("N-02 cleanup evidence contains active fault files")
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise RetestError("N-02 retest cleanup confirmation is invalid") from exc
    return record


def finalize_n02_retest_records(
    records: dict[str, Any],
    *,
    child_run_id: UUID,
    child_lanes: tuple[RunSubjectLane, ...],
    child_paths: dict[str, Any],
    child_policy: dict[str, Any],
) -> None:
    """Fill policy, capability and fixture comparisons from the actual child Run."""
    try:
        parent = records["_n02_parent"]
        parent_lanes = tuple(RunSubjectLane.model_validate(row) for row in parent["lanes"])
        parent_paths = parent["paths"]
        diff = records["diff"]["n02"]
        changed = records["link"]["changed_dimensions"]
    except (KeyError, TypeError, ValueError) as exc:
        raise RetestError("N-02 retest comparison context is invalid") from exc
    if (
        len(child_lanes) != len(N02LaneId)
        or {lane.lane_id for lane in child_lanes} != set(N02LaneId)
        or any(lane.run_id != child_run_id for lane in child_lanes)
    ):
        raise RetestError("N-02 child must create six lanes for its own Run")
    if (
        {lane.invitation_id for lane in parent_lanes} & {lane.invitation_id for lane in child_lanes}
        or {lane.applicant_id for lane in parent_lanes} & {lane.applicant_id for lane in child_lanes}
    ):
        raise RetestError("N-02 child reused parent subject identities")
    path_changes = _diff(parent_paths, child_paths)
    diff["path_capability"].update({
        "after_digest": sha256_bytes(canonical_json_bytes(child_paths)),
        "changed": bool(path_changes),
        "changed_fields": path_changes,
    })
    before_policy = diff["policy"]["before"]
    after_policy = _policy_identity(child_policy)
    policy_changes = _diff(before_policy, after_policy)
    diff["policy"].update({
        "after": after_policy,
        "changed": bool(policy_changes),
        "changed_fields": policy_changes,
    })
    by_lane = {lane.lane_id: lane for lane in parent_lanes}
    fixture_rows = []
    for lane in child_lanes:
        previous = by_lane[lane.lane_id]
        before = _fixture_identity(previous)
        after = _fixture_identity(lane)
        fixture_rows.append({
            "lane_id": lane.lane_id.value,
            "before": before,
            "after": after,
            "changed": before != after,
        })
    diff["lane_fixtures"].update({
        "lanes": fixture_rows,
        "changed": any(row["changed"] for row in fixture_rows),
    })
    changed.update({
        "path_capability": bool(path_changes),
        "policy": bool(policy_changes),
        "lane_fixtures": diff["lane_fixtures"]["changed"],
    })


def _policy_identity(value: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value.get(key)
        for key in ("policy_version", "content_digest", "required_purposes", "retention_days")
    }


def _fixture_identity(lane: RunSubjectLane) -> dict[str, Any]:
    return {
        "baseline_kind": lane.baseline_kind.value,
        "fixture_kind": lane.fixture_kind,
        "fixture_digest": lane.fixture_digest,
        "allowed_preexisting_effects": lane.allowed_preexisting_effects,
    }


def finalize_retest_records(records: dict[str, Any], child_subject: TestSubject) -> None:
    """Complete subject comparison from the actual child baseline before bundle sealing."""
    try:
        parent_subject = TestSubject.model_validate(records["_parent_subject"])
        subject_diff = records["diff"]["subject"]
        link = records["link"]
    except (KeyError, TypeError, ValueError) as exc:
        raise RetestError("retest subject comparison context is invalid") from exc
    if parent_subject.subject_ref != child_subject.subject_ref:
        raise RetestError("retest subject_ref must remain comparable")
    comparisons = {
        "role": (parent_subject.subject_type, child_subject.subject_type),
        "initial_state_digest": (
            parent_subject.initial_state_digest,
            child_subject.initial_state_digest,
        ),
    }
    for key, (before, after) in comparisons.items():
        subject_diff[key] = {
            "before": before,
            "after": after,
            "changed": before != after,
        }
    link.setdefault("changed_dimensions", {})["subject_role"] = subject_diff["role"]["changed"]
    link["changed_dimensions"]["subject_initial_state"] = subject_diff["initial_state_digest"][
        "changed"
    ]


def assert_parent_unchanged(parent_bundle: Path, expected_bundle_digest: str) -> None:
    result = verify_bundle(parent_bundle.resolve())
    if result["bundle_status"] != "VERIFIED":
        raise RetestError("parent Evidence Bundle changed during retest")
    current = _read(parent_bundle.resolve() / "manifest.json").get("bundle_digest")
    if current != expected_bundle_digest:
        raise RetestError("parent bundle digest changed during retest")


def _diff(before: Any, after: Any, path: str = "") -> list[dict[str, Any]]:
    if isinstance(before, dict) and isinstance(after, dict):
        changes: list[dict[str, Any]] = []
        for key in sorted(set(before) | set(after)):
            child = f"{path}.{key}" if path else key
            changes.extend(_diff(before.get(key), after.get(key), child))
        return changes
    if before == after and type(before) is type(after):
        return []
    return [{"path": path, "before": before, "after": after}]


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


# --- Spec 004 (E-01/E-02) retest lineage (T071) ----------------------------------------------------

SPEC004_BLOCK_SUBJECTS = {
    ExecutionProfile.E01_CITATION_EVIDENCE_V1: "e01-citation-evidence",
    ExecutionProfile.E02_SCORING_FREEZE_V1: "e02-scoring-freeze",
}
_SPEC004_IDENTITIES = ("invitation_id", "applicant_id", "position_id", "interview_session_id")


def _spec004_cleanup_resolved(directory: Path, parent_run: Run) -> None:
    profile = parent_run.execution_profile
    blocks = RestoreBlockStore(directory.parent)
    if blocks.blocked(parent_run.target_id, SPEC004_BLOCK_SUBJECTS[profile]):
        raise RetestError("Spec 004 retest refused: unresolved restore block")
    if parent_run.state is RunState.RESTORE_FAILED or parent_run.manual_cleanup_required:
        confirmation = directory.parent / "maintenance" / f"{parent_run.run_id}.json"
        if not confirmation.is_file():
            raise RetestError("Spec 004 retest refused: restore block was never confirmed")


def _prepare_spec004_retest(
    *,
    directory: Path,
    parent_run: Run,
    parent_manifest: dict[str, Any],
    parent_digest: str,
    parent_target: TargetSnapshot,
    child_run_id: UUID,
    child_target: TargetSnapshot,
    child_scenario_version: str,
    child_scenario_digest: str,
    child_environment: TargetEnvironmentSnapshot | None,
    child_queue: QueueTopologySnapshot | None,
) -> tuple[Run, str, dict[str, Any]]:
    if child_target.target_id != parent_run.target_id:
        raise RetestError("Spec 004 retest must use the same target")
    if (
        child_scenario_version != parent_run.scenario_version
        or child_scenario_digest != parent_run.scenario_digest
    ):
        raise RetestError("Spec 004 retest must inherit the parent scenario snapshot")
    if child_queue is not None:
        raise RetestError("Spec 004 retest has no Spec 002 queue topology")
    if child_environment is None or (
        child_environment.target_id != child_target.target_id
        or set(child_environment.unverified_scope) != SPEC004_UNVERIFIED_SCOPE
    ):
        raise RetestError("Spec 004 retest requires a local environment snapshot of the target")
    try:
        parent_environment = TargetEnvironmentSnapshot.model_validate(
            _read(directory / "environment.snapshot.json")
        )
        parent_lanes = _read(directory / "spec004-lanes.json")["lanes"]
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise RetestError("Spec 004 parent comparison facts are unreadable") from exc
    target_changes = _diff(parent_target.identity(), child_target.identity())
    environment_changes = _diff(
        parent_environment.model_dump(mode="json", exclude={"captured_at", "snapshot_digest"}),
        child_environment.model_dump(mode="json", exclude={"captured_at", "snapshot_digest"}),
    )
    fixture_before = {
        "id": parent_run.model_fixture_id,
        "digest": parent_run.model_fixture_digest,
    }
    fixture_after = {
        "id": child_target.model_fixture_id,
        "digest": child_target.model_fixture_digest,
    }
    profile = parent_run.execution_profile
    diff = {
        "schema_version": "controlproof.retest-diff.v1",
        "parent_run_id": str(parent_run.run_id),
        "child_run_id": str(child_run_id),
        "scenario": {
            "before": {"version": parent_run.scenario_version, "digest": parent_run.scenario_digest},
            "after": {"version": child_scenario_version, "digest": child_scenario_digest},
            "changed": False,
        },
        "target": {
            "before_digest": parent_target.target_version,
            "after_digest": child_target.target_version,
            "changed_fields": target_changes,
        },
        "execution_profile": {"before": profile.value, "after": profile.value, "changed": False},
        "environment": {
            "before_digest": parent_environment.snapshot_digest,
            "after_digest": child_environment.snapshot_digest,
            "changed": bool(environment_changes),
            "changed_fields": environment_changes,
        },
        "queue_topology": None,
        "spec004": {
            "model_fixture": {
                "before": fixture_before,
                "after": fixture_after,
                "changed": fixture_before != fixture_after,
            },
            "scoring_rule_source": {
                "before_digest": parent_run.scoring_rule_source_digest,
                "after_digest": None,
                "changed": None,
            },
            "lanes": {
                "before_lane_manifest_digest": parent_run.lane_manifest_digest,
                "after_lane_manifest_digest": None,
                "reused_identities": None,
            },
        },
        "created_at": utcnow().isoformat(),
    }
    link = RetestLink(
        parent_run_id=parent_run.run_id,
        child_run_id=child_run_id,
        changed_dimensions={
            "scenario": False,
            "target_paths": [item["path"] for item in target_changes],
            "environment": bool(environment_changes),
            "model_fixture": fixture_before != fixture_after,
            "scoring_rule_source": None,
        },
        reason=f"WhyYou 수정 후 {parent_run.scenario_id} 독립 Run 재시험",
    )
    origin = next(
        (row for row in parent_manifest.get("files", []) if row.get("path") == "judgement.json"),
        None,
    )
    if not isinstance(origin, dict) or not origin.get("sha256"):
        raise RetestError("Spec 004 parent judgement origin file is missing")
    records = {
        "link": link.model_dump(mode="json")
        | {"parent_bundle_digest": parent_digest, "parent_judgement_sha256": origin["sha256"]},
        "diff": diff,
        "_spec004_parent": {"lanes": parent_lanes},
    }
    return parent_run, parent_digest, records


def finalize_spec004_retest_records(
    records: dict[str, Any], *, child_run: Run, child_lanes: tuple[Any, ...]
) -> None:
    """Fill the lane and scoring-source comparisons from the actual child Run."""
    try:
        parent_lanes = records["_spec004_parent"]["lanes"]
        diff = records["diff"]["spec004"]
        changed = records["link"]["changed_dimensions"]
    except (KeyError, TypeError) as exc:
        raise RetestError("Spec 004 retest comparison context is invalid") from exc
    if any(lane.run_id != child_run.run_id for lane in child_lanes):
        raise RetestError("Spec 004 child lanes must belong to the child Run")
    reused = sorted(
        {
            f"{name}:{lane[name]}"
            for lane in parent_lanes
            for name in _SPEC004_IDENTITIES
        }
        & {
            f"{name}:{getattr(lane, name)}"
            for lane in child_lanes
            for name in _SPEC004_IDENTITIES
        }
    )
    if reused:
        raise RetestError("Spec 004 child reused parent subject identities")
    before = diff["scoring_rule_source"]["before_digest"]
    diff["scoring_rule_source"].update(
        {
            "after_digest": child_run.scoring_rule_source_digest,
            "changed": before != child_run.scoring_rule_source_digest,
        }
    )
    diff["lanes"].update(
        {
            "after_lane_manifest_digest": child_run.lane_manifest_digest,
            "reused_identities": reused,
        }
    )
    changed["scoring_rule_source"] = diff["scoring_rule_source"]["changed"]
    records.pop("_spec004_parent", None)
