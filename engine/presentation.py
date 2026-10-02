"""Review-safe projections for sealed Evidence Bundles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from engine.models import (
    AssertionStatus,
    ExecutionProfile,
    Judgement,
    Run,
    ScenarioProfile,
)

CLAIM_SCOPE = "EXECUTED_SCENARIO_AND_EVIDENCE_ONLY"
NO_CERTIFICATION_NOTICE = (
    "이 결과는 실행된 시나리오와 확보한 증적에 한정되며 "
    "법적 준수 전체를 인증하거나 보증하지 않습니다."
)
N02_SCOPE_NOTICE = (
    "이 결과는 LOCAL_EMULATED에서 실행한 N-02 경로에 한정됩니다. "
    "N-01·N-03과 실제 AWS는 NOT_RUN이며 법적 준수 전체를 인증하거나 보증하지 않습니다."
)
N02_PATH_ASSERTIONS = {
    "DOCUMENT_ANALYSIS": "N02-A2",
    "RECORDING": "N02-A3",
    "AI_ASSESSMENT": "N02-A4",
}


def load_bundle_summary(bundle: Path) -> dict[str, Any]:
    """Return the fixed first-screen review order without exposing raw artifact bodies."""
    directory = bundle.resolve()
    run = Run.model_validate(_read_json(directory / "run.json"))
    judgement = Judgement.model_validate(_read_json(directory / "judgement.json"))
    manifest = _read_json(directory / "manifest.json")
    observations = _read_jsonl(directory / "observations.jsonl")
    effects = _read_jsonl(directory / "effects.jsonl")
    attempts = _read_jsonl(directory / "delivery-attempts.jsonl")
    terminal_failure = (
        _read_json(directory / "terminal-failure.json")
        if (directory / "terminal-failure.json").exists()
        else None
    )
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
    profile = run.execution_profile or ExecutionProfile.H03_MINIMAL_V1
    evaluated = (
        list(ScenarioProfile.canonical(profile).applicable_assertion_ids)
        if profile is not ExecutionProfile.H03_MINIMAL_V1
        else [item.assertion_id for item in judgement.assertion_results]
    )
    remaining = _remaining_variant_coverage(profile)
    decision_a7 = next(
        (item for item in assertions if item["assertion_id"] == "H03-A7"), None
    )
    decision_cases = (
        decision_a7.get("actual", {}).get("cases", {})
        if isinstance(decision_a7, dict) and isinstance(decision_a7.get("actual"), dict)
        else {}
    )
    n02_review = (
        _n02_review(directory, assertions)
        if profile is ExecutionProfile.N02_CONSENT_ORDER_V1
        else None
    )
    summary = {
        "schema_version": "controlproof.review.v1",
        "run_id": str(run.run_id),
        "verdict": judgement.verdict.value,
        "reason_code": judgement.reason_code.value if judgement.reason_code else None,
        "summary": judgement.summary,
        "failed_assertions": failed,
        "inconclusive_assertions": inconclusive,
        "assertions": assertions,
        "evidence_links": _evidence_links(manifest, by_artifact),
        "environment_restore_status": environment_restore,
        "report_processing_recovery": report_recovery,
        "implementation_status": run.implementation_status.value,
        "execution_profile": profile.value,
        "fault_variant": run.fault_variant.value if run.fault_variant else None,
        "claim_scope": CLAIM_SCOPE,
        "legal_scope_notice": (
            N02_SCOPE_NOTICE if n02_review is not None else NO_CERTIFICATION_NOTICE
        ),
        "scenario_result": {
            "scenario_id": run.scenario_id,
            "execution_profile": profile.value,
            "verdict": judgement.verdict.value,
        },
        "evaluated_assertions": evaluated,
        "remaining_variant_coverage": remaining,
        "failure_route": terminal_failure,
        "decision_path_coverage": sorted(decision_cases),
        "delivery_lineage": {
            "source_event_id": str(run.source_event_id) if run.source_event_id else None,
            "attempts": [item.get("delivery_attempt") for item in attempts],
        },
        "effect_differences": _effect_differences(effects),
        "environment_kind": run.environment_kind.value if run.environment_kind else None,
        "aws_deployment_status": (
            run.aws_deployment_status.value if run.aws_deployment_status else None
        ),
        "cloud_verification": {
            "aws_deployment_status": (
                run.aws_deployment_status.value if run.aws_deployment_status else None
            ),
            "unverified_scope": list(run.unverified_scope),
        },
        "run_state": run.state.value,
        "scenario_id": run.scenario_id,
        "scenario_version": run.scenario_version,
        "target_id": run.target_id,
        "target_version": run.target_version,
        "model_fixture_id": run.model_fixture_id,
        "model_fixture_digest": run.model_fixture_digest,
        "missing_evidence": list(judgement.missing_evidence),
        "findings": [finding.model_dump(mode="json") for finding in judgement.findings],
        "unverified_scope": (
            list(run.unverified_scope)
            if n02_review is not None else list(judgement.unverified_scope)
        ),
        "parent_run_id": str(run.parent_run_id) if run.parent_run_id else None,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "ended_at": run.ended_at.isoformat() if run.ended_at else None,
    }
    if n02_review is not None:
        summary["n02_review"] = n02_review
        summary["path_capability_digest"] = run.path_capability_digest
        summary["policy_snapshot_digest"] = run.policy_snapshot_digest
        summary["lane_manifest_digest"] = run.lane_manifest_digest
        summary["consent_fault_triggered"] = (
            n02_review["fault_recovery"]["trigger_receipt_count"] > 0
        )
        summary["environment_restore_status"] = n02_review["fault_recovery"].get(
            "restore_status"
        )
        summary["path_results"] = {
            path: next(
                (item["status"] for item in assertions if item["assertion_id"] == assertion_id),
                "INCONCLUSIVE",
            )
            for path, assertion_id in N02_PATH_ASSERTIONS.items()
        }
    return summary


def render_human(summary: dict[str, Any]) -> str:
    """Concise Korean terminal view in the contractually fixed order."""
    failed = ", ".join(summary["failed_assertions"]) or "없음"
    inconclusive = ", ".join(summary["inconclusive_assertions"]) or "없음"
    lines = [
            f"판정: {summary['verdict']}",
            f"핵심 이유: {summary['summary']}",
            f"실패 assertion: {failed}",
            f"판정 불가 assertion: {inconclusive}",
            f"환경 복구: {summary['environment_restore_status'] or '조회하지 못함'}",
            f"리포트 처리 복구: {summary['report_processing_recovery'] or '조회하지 못함'}",
            f"증적 경로: {sum(len(value) for value in summary['evidence_links'].values())}개",
            f"주장 범위: {summary.get('claim_scope', CLAIM_SCOPE)}",
            summary.get("legal_scope_notice", NO_CERTIFICATION_NOTICE),
    ]
    review = summary.get("n02_review")
    if isinstance(review, dict):
        for path, facts in review["paths"].items():
            request = facts.get("request") or {}
            effect = facts.get("effect") or {}
            source = effect.get("source_status")
            source_label = "조회하지 못함" if source == "UNAVAILABLE" else source or "증적 없음"
            lines.append(
                f"{path}: 요청 {request.get('response_class') or '증적 없음'}, "
                f"신규 효과 {len(effect.get('new_effect_ids') or [])}건, {source_label}"
            )
        policy = review["policy_order"]
        lines.append(f"정책 버전: {policy.get('policy_version') or '조회하지 못함'}")
        lines.append(f"인과 edge: {policy.get('causal_edge_count', 0)}건")
        recovery = review["fault_recovery"]
        lines.append(f"동의 장애 복구: {recovery.get('restore_status') or '조회하지 못함'}")
        if recovery.get("manual_cleanup_required"):
            lines.append("수동 정리 확인 필요")
        lines.append("미검증 범위: " + ", ".join(summary.get("unverified_scope", [])))
    return "\n".join(lines)


def _n02_review(directory: Path, assertions: list[dict[str, Any]]) -> dict[str, Any]:
    lanes_payload = _read_json(directory / "n02-lanes.json")
    lanes = lanes_payload.get("lanes", []) if isinstance(lanes_payload, dict) else []
    capabilities = _read_json(directory / "n02-capabilities.json")
    cap_paths = capabilities.get("paths", []) if isinstance(capabilities, dict) else []
    attempts = _read_jsonl(directory / "bypass-attempts.jsonl")
    effects = _read_jsonl(directory / "protected-effects.jsonl")
    causal_edges = _read_jsonl(directory / "causal-edges.jsonl")
    fault_receipts = _read_jsonl(directory / "fault-receipts.jsonl")
    policy = _read_json(directory / "policy-and-consent.json")
    recovery = _read_json(directory / "recovery.json")
    paths: dict[str, Any] = {}
    unavailable: list[str] = []
    for path, assertion_id in N02_PATH_ASSERTIONS.items():
        capability = next(
            (item for item in cap_paths if isinstance(item, dict) and item.get("path_id") == path),
            {},
        )
        attempt = next(
            (item for item in attempts if isinstance(item, dict) and item.get("path_id") == path),
            {},
        )
        effect = next(
            (item for item in effects if isinstance(item, dict) and item.get("effect_group") == path),
            {},
        )
        if effect.get("source_status") == "UNAVAILABLE":
            unavailable.append(path)
        paths[path] = {
            "entry_boundary": capability.get("entry_boundary"),
            "entry_kind": attempt.get("entry_kind") or capability.get("entry_kind"),
            "independent_direct_route": capability.get("independent_direct_route"),
            "operation_id": attempt.get("operation_id"),
            "request": _select(attempt, "attempt_id", "request_id", "response_class", "source_status"),
            "effect": _select(effect, "new_effect_ids", "fixture_effect_ids", "source_status", "source_error_code"),
            "assertion_id": assertion_id,
        }
    policy_payload = policy.get("policy", policy) if isinstance(policy, dict) else {}
    recovery_payload = recovery if isinstance(recovery, dict) else {}
    return {
        "lanes": [
            _select(lane, "lane_id", "subject_ref", "baseline_kind", "fixture_kind", "fixture_digest")
            for lane in lanes if isinstance(lane, dict)
        ],
        "paths": paths,
        "policy_order": {
            **_select(policy_payload, "policy_version", "content_digest", "required_purposes"),
            "causal_edge_count": len(causal_edges),
            "a5_status": next((item["status"] for item in assertions if item["assertion_id"] == "N02-A5"), None),
        },
        "fault_recovery": {
            **_select(recovery_payload, "restore_status", "manual_cleanup_required", "logical_consent_count", "consent_completed_event_count"),
            "trigger_receipt_count": len(fault_receipts),
        },
        "unavailable_paths": unavailable,
    }


def _select(value: dict[str, Any], *keys: str) -> dict[str, Any]:
    return {key: value.get(key) for key in keys}


def _remaining_variant_coverage(profile: ExecutionProfile) -> list[str]:
    if profile is ExecutionProfile.E03_BEFORE_V2:
        return ["E03-A5", "E03-A6"]
    if profile is ExecutionProfile.E03_AFTER_V2:
        return ["E03-A2", "E03-A3", "E03-A4", "E03-A7"]
    return []


def _evidence_links(
    manifest: dict[str, Any], by_artifact: dict[str, dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for evidence_id, references in manifest.get("required_evidence", {}).items():
        linked: list[dict[str, Any]] = []
        for reference in references if isinstance(references, list) else ():
            if not isinstance(reference, str):
                continue
            artifact_id = reference.removeprefix("artifact:")
            if artifact_id in by_artifact:
                linked.append(by_artifact[artifact_id])
        result[evidence_id] = linked
    return result


def _effect_differences(effects: list[dict[str, Any]]) -> dict[str, Any]:
    if not effects:
        return {"changed": None, "comparisons": []}
    by_operation: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in effects:
        key = (str(item.get("effect_group")), str(item.get("logical_operation_id")))
        by_operation.setdefault(key, []).append(item)
    comparisons = []
    for (group, operation), rows in sorted(by_operation.items()):
        comparisons.append(
            {
                "effect_group": group,
                "logical_operation_id": operation,
                "before_digest": rows[0].get("state_digest"),
                "after_digest": rows[-1].get("state_digest"),
                "changed": rows[0].get("state_digest") != rows[-1].get("state_digest"),
            }
        )
    return {
        "changed": any(item["changed"] for item in comparisons),
        "comparisons": comparisons,
    }


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
