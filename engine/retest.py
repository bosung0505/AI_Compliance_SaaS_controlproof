"""Immutable parent verification and child Run comparison records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from engine.evidence import verify_bundle
from engine.models import (
    TERMINAL_RUN_STATES,
    ExecutionProfile,
    FaultVariant,
    QueueTopologySnapshot,
    RetestLink,
    Run,
    RunState,
    TargetEnvironmentSnapshot,
    TargetSnapshot,
    TestSubject,
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
) -> tuple[Run, str, dict[str, Any]]:
    directory = parent_bundle.resolve()
    verification = verify_bundle(directory)
    if verification["bundle_status"] != "VERIFIED":
        raise RetestError("parent Evidence Bundle failed integrity verification")
    parent_run = Run.model_validate(_read(directory / "run.json"))
    if parent_run.state not in TERMINAL_RUN_STATES:
        raise RetestError("retest parent must be terminal")
    if parent_run.state is RunState.RESTORE_FAILED or parent_run.manual_cleanup_required:
        raise RetestError("retest parent does not prove safe cleanup")
    if parent_run.run_id == child_run_id:
        raise RetestError("retest child must use a new Run ID")
    parent_target = TargetSnapshot.model_validate(_read(directory / "target.snapshot.json"))
    parent_subjects = _read(directory / "subjects.json")
    if not isinstance(parent_subjects, list) or len(parent_subjects) != 1:
        raise RetestError("retest parent must contain exactly one canonical subject")
    try:
        parent_subject = TestSubject.model_validate(parent_subjects[0])
    except (TypeError, ValueError) as exc:
        raise RetestError("retest parent subject contract is invalid") from exc
    parent_digest = _read(directory / "manifest.json")["bundle_digest"]
    parent_manifest = _read(directory / "manifest.json")
    parent_profile = parent_run.execution_profile or ExecutionProfile.H03_MINIMAL_V1
    active_child_profile = child_profile or ExecutionProfile.H03_MINIMAL_V1
    if active_child_profile is not parent_profile:
        raise RetestError("retest child must inherit the parent execution profile")
    if child_fault_variant is not parent_run.fault_variant:
        raise RetestError("retest child must inherit the parent fault variant")
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
