"""Review-safe projections for sealed Evidence Bundles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from engine.models import AssertionStatus, Judgement, Run


def load_bundle_summary(bundle: Path) -> dict[str, Any]:
    """Return the fixed first-screen review order without exposing raw artifact bodies."""
    directory = bundle.resolve()
    run = Run.model_validate(_read_json(directory / "run.json"))
    judgement = Judgement.model_validate(_read_json(directory / "judgement.json"))
    manifest = _read_json(directory / "manifest.json")
    observations = _read_jsonl(directory / "observations.jsonl")
    by_artifact = {
        record.get("artifact_id"): {
            "artifact_id": record.get("artifact_id"),
            "path": record.get("path"),
            "sha256": record.get("sha256"),
            "mime_type": record.get("mime_type"),
        }
        for record in manifest.get("files", [])
        if record.get("artifact_id")
    }
    assertions = []
    for result in judgement.assertion_results:
        assertions.append(
            {
                "assertion_id": result.assertion_id,
                "status": result.status.value,
                "expected": result.expected,
                "actual": result.actual,
                "detail": result.detail,
                "reason_code": result.reason_code.value if result.reason_code else None,
                "source_requirements": list(result.source_requirements),
                "evidence": [
                    by_artifact[str(artifact_id)]
                    for artifact_id in result.artifact_ids
                    if str(artifact_id) in by_artifact
                ],
            }
        )
    environment_restore = _latest_value(observations, "fault.environment_restore")
    report_recovery = _latest_value(observations, "report.processing_recovery")
    failed = [
        item["assertion_id"] for item in assertions if item["status"] == AssertionStatus.FAIL.value
    ]
    inconclusive = [
        item["assertion_id"]
        for item in assertions
        if item["status"] == AssertionStatus.INCONCLUSIVE.value
    ]
    return {
        "schema_version": "controlproof.review.v1",
        "run_id": str(run.run_id),
        "verdict": judgement.verdict.value,
        "reason_code": judgement.reason_code.value if judgement.reason_code else None,
        "summary": judgement.summary,
        "failed_assertions": failed,
        "inconclusive_assertions": inconclusive,
        "assertions": assertions,
        "evidence_links": {
            evidence_id: [
                by_artifact[artifact_id]
                for artifact_id in artifact_ids
                if artifact_id in by_artifact
            ]
            for evidence_id, artifact_ids in manifest.get("required_evidence", {}).items()
        },
        "environment_restore_status": environment_restore,
        "report_processing_recovery": report_recovery,
        "implementation_status": run.implementation_status.value,
        "run_state": run.state.value,
        "scenario_id": run.scenario_id,
        "scenario_version": run.scenario_version,
        "target_id": run.target_id,
        "target_version": run.target_version,
        "model_fixture_id": run.model_fixture_id,
        "model_fixture_digest": run.model_fixture_digest,
        "missing_evidence": list(judgement.missing_evidence),
        "findings": [finding.model_dump(mode="json") for finding in judgement.findings],
        "unverified_scope": list(judgement.unverified_scope),
        "parent_run_id": str(run.parent_run_id) if run.parent_run_id else None,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "ended_at": run.ended_at.isoformat() if run.ended_at else None,
    }


def render_human(summary: dict[str, Any]) -> str:
    """Concise Korean terminal view in the contractually fixed order."""
    failed = ", ".join(summary["failed_assertions"]) or "없음"
    inconclusive = ", ".join(summary["inconclusive_assertions"]) or "없음"
    return "\n".join(
        (
            f"판정: {summary['verdict']}",
            f"핵심 이유: {summary['summary']}",
            f"실패 assertion: {failed}",
            f"판정 불가 assertion: {inconclusive}",
            f"환경 복구: {summary['environment_restore_status'] or '조회하지 못함'}",
            f"리포트 처리 복구: {summary['report_processing_recovery'] or '조회하지 못함'}",
            f"증적 경로: {sum(len(value) for value in summary['evidence_links'].values())}개",
        )
    )


def _latest_value(observations: list[dict[str, Any]], key: str) -> Any:
    rows = [row for row in observations if row.get("key") == key]
    if not rows:
        return None
    row = rows[-1]
    if row.get("presence") == "ABSENT":
        return "조회 결과 없음"
    if row.get("presence") == "UNAVAILABLE":
        return "조회하지 못함"
    return row.get("value")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
