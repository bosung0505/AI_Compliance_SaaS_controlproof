"""Immutable parent verification and child Run comparison records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from engine.evidence import verify_bundle
from engine.models import TERMINAL_RUN_STATES, RetestLink, Run, TargetSnapshot, utcnow


class RetestError(RuntimeError):
    pass


def prepare_retest(
    parent_bundle: Path,
    *,
    child_run_id: UUID,
    child_target: TargetSnapshot,
    child_scenario_version: str,
    child_scenario_digest: str,
) -> tuple[Run, str, dict[str, Any]]:
    directory = parent_bundle.resolve()
    verification = verify_bundle(directory)
    if verification["bundle_status"] != "VERIFIED":
        raise RetestError("parent Evidence Bundle failed integrity verification")
    parent_run = Run.model_validate(_read(directory / "run.json"))
    if parent_run.state not in TERMINAL_RUN_STATES:
        raise RetestError("retest parent must be terminal")
    if parent_run.run_id == child_run_id:
        raise RetestError("retest child must use a new Run ID")
    parent_target = TargetSnapshot.model_validate(_read(directory / "target.snapshot.json"))
    parent_digest = _read(directory / "manifest.json")["bundle_digest"]
    changed_target = _diff(parent_target.identity(), child_target.identity())
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
        "subject": {"role": "synthetic_applicant", "subject_ref": "candidate-01"},
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
            "after": "reporting_handler_timeout_v1",
        },
        "created_at": utcnow().isoformat(),
    }
    link = RetestLink(
        parent_run_id=parent_run.run_id,
        child_run_id=child_run_id,
        changed_dimensions={
            "scenario": diff["scenario"]["changed"],
            "target_paths": [item["path"] for item in changed_target],
        },
        reason="WhyYou 수정 후 독립 Run 재시험",
    )
    return (
        parent_run,
        parent_digest,
        {
            "link": link.model_dump(mode="json"),
            "diff": diff,
        },
    )


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
