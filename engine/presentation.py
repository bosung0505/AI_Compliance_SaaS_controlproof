"""Review-safe projections for sealed Evidence Bundles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from engine.models import (
    SPEC004_PROFILES,
    AssertionStatus,
    ExecutionProfile,
    Judgement,
    Run,
    ScenarioProfile,
    sha256_bytes,
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
SPEC004_LIMITATIONS = ["FIXTURE_INTERVIEW_INPUT", "EXTERNAL_AI_BLOCKED", "FIXED_MODEL_SUBSTITUTE"]
SPEC004_SCOPE_NOTICE = (
    "이 결과는 로컬 환경에서 fixture 면접 입력과 고정 모델 대체물로 실행한 {scenario} 경로와 확보한 "
    "증적에 한정되며, 실제 AI 모델 품질, 실제 AWS 또는 법적 준수 전체를 인증하거나 보증하지 않습니다."
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
        "evidence_index": evidence_index(directory, manifest, judgement),
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
    if profile in SPEC004_PROFILES:
        review = _spec004_review(directory, profile, run, assertions)
        summary.update(review)
        summary["legal_scope_notice"] = SPEC004_SCOPE_NOTICE.format(scenario=run.scenario_id)
        summary["unverified_scope"] = list(run.unverified_scope)
        summary["limitations"] = list(SPEC004_LIMITATIONS)
        summary["environment_restore_status"] = review["change_injection_restore_status"]
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
    if "citation_modes" in summary:
        modes = ", ".join(f"{mode}={value}" for mode, value in summary["citation_modes"].items())
        lines.append(f"인용 모드: {modes or '증적 없음'}")
        removal = summary["evidence_removal"]
        lines.append(
            "근거 제거: "
            f"적용 {removal.get('applied')}, 복원 {removal.get('restored')}, "
            f"근거 부족 노출 {removal.get('exposed_as_insufficient')}"
        )
        exposure = summary["diagnostics"].get("E01-D1") or {}
        lines.append(
            "E01-D1(진단, 판정 무관): "
            + (", ".join(f"{mode}={value}" for mode, value in exposure.items()) or "기록 없음")
        )
    if "versions" in summary:
        versions = summary["versions"]
        lines.append(
            "기준 버전: "
            + ", ".join(
                f"{key} #{value.get('version_number')} {value.get('status')}"
                for key, value in versions.items()
                if value
            )
        )
        lines.append(f"첫 보고서 불변: {summary['first_report_unchanged']}")
        lines.append(f"두 번째 보고서 묶임: {summary['second_report_bound_to'] or '확인하지 못함'}")
        equal = sum(all(targets.values()) for targets in summary["recompute"].values())
        lines.append(f"재계산 일치 보고서: {equal}/{len(summary['recompute'])}")
    if "limitations" in summary:
        lines.append(f"변경 주입 복구: {summary['change_injection_restore_status']}")
        lines.append("격리 한계: " + ", ".join(summary["limitations"]))
        lines.append("미검증 범위: " + ", ".join(summary.get("unverified_scope", [])))
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


def _spec004_review(
    directory: Path, profile: ExecutionProfile, run: Run, assertions: list[dict[str, Any]]
) -> dict[str, Any]:
    """Spec 004 projections from sealed files only (no raw text exists in them)."""
    by_id = {item["assertion_id"]: item for item in assertions}
    injections = _read_jsonl(directory / "change-injections.jsonl")
    states = {row.get("state") for row in injections}
    if run.state.value == "RESTORE_FAILED" or "RESTORE_FAILED" in states:
        restore_status = "FAILED"
    elif injections and states == {"RESTORED"}:
        restore_status = "SUCCEEDED"
    else:
        restore_status = "NOT_APPLIED"
    review: dict[str, Any] = {"change_injection_restore_status": restore_status}
    if profile is ExecutionProfile.E01_CITATION_EVIDENCE_V1:
        cases = _read_jsonl(directory / "citation-cases.jsonl")
        removal = next(
            (row for row in injections if row.get("kind") == "EVIDENCE_SEGMENT_REMOVAL"), None
        )
        a3 = by_id.get("E01-A3") or {}
        actual = a3.get("actual") if isinstance(a3.get("actual"), dict) else {}
        exposed = (
            bool(actual.get("indicators")) and not actual.get("unexposed")
            if "indicators" in actual
            else None
        )
        probe = _read_json(directory / "storage-probe.json")
        review |= {
            "citation_modes": {case["mode"]: case["outcome"] for case in cases},
            "evidence_removal": {
                "applied": removal is not None and removal.get("applied_at") is not None,
                "restored": removal is not None and removal.get("state") == "RESTORED",
                "exposed_as_insufficient": exposed,
            },
            "diagnostics": {
                "E01-D1": {row["mode"]: row["exposure"] for row in probe.get("exposure", [])}
            },
        }
    else:
        versions = _read_json(directory / "criteria-versions.json")
        recompute = _read_json(directory / "recompute.json")
        a2 = by_id.get("E02-A2") or {}
        actual = a2.get("actual") if isinstance(a2.get("actual"), dict) else {}
        unchanged = (
            bool(actual.get("record_equal")) and bool(actual.get("read_equal"))
            if "record_equal" in actual
            else None
        )
        review |= {
            "versions": {
                key: _select(versions[key], "competency_model_version_id", "version_number", "status")
                if versions.get(key)
                else None
                for key in ("v1", "v2")
            },
            "first_report_unchanged": unchanged,
            "second_report_bound_to": versions.get("published_v2_id")
            if actual.get("second_bound_to_v2")
            else None,
            "recompute": {
                record["report_id"]: {
                    target: all(
                        item["equal"] for item in record["comparisons"] if item["target"] == target
                    )
                    for target in sorted({item["target"] for item in record["comparisons"]})
                }
                for record in recompute.get("records", [])
                if record is not None
            },
        }
    return review


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


def evidence_index(directory: Path, manifest: dict[str, Any], judgement: Judgement) -> dict[str, Any]:
    """Resolve every evidence reference to a `<run_root>/…` file with SHA-256, size and MIME (R-011).

    Reference forms: Spec 001 bare artifact IDs, `artifact:`, `file:`, `intrinsic:sealed-manifest` and cross-run
    objects (resolved through the sibling origin bundle's manifest). `by_assertion` is the assertion's own
    `artifact_ids` together with the references of its `required_evidence_ids` in the sealed scenario snapshot.
    """
    run_id = directory.name
    files: list[dict[str, Any]] = []
    by_ref: dict[str, dict[str, Any]] = {}
    by_path: dict[str, str] = {}

    def add(ref: str, record: dict[str, Any], bundle_id: str) -> dict[str, Any]:
        if ref not in by_ref:
            by_ref[ref] = {
                "ref": ref,
                "relative_path": f"<run_root>/{bundle_id}/{record.get('path')}",
                "sha256": record.get("sha256"),
                "size_bytes": record.get("size_bytes"),
                "mime_type": record.get("mime_type"),
                "evidence_requirement_ids": [],
            }
            files.append(by_ref[ref])
        return by_ref[ref]

    for record in manifest.get("files", []):
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            continue
        ref = f"artifact:{record['artifact_id']}" if record.get("artifact_id") else f"file:{record['path']}"
        add(ref, record, run_id)
        by_path[record["path"]] = ref

    def resolve(reference: Any) -> tuple[str, dict[str, Any] | None]:
        if isinstance(reference, dict):
            origin = str(reference.get("origin_run_id"))
            ref = f"run:{origin}/artifact:{reference.get('artifact_id')}"
            if ref in by_ref:
                return ref, by_ref[ref]
            try:
                origin_manifest = _read_json(directory.parent / origin / "manifest.json")
            except (OSError, ValueError):
                return ref, None
            for record in origin_manifest.get("files", []):
                if (
                    isinstance(record, dict)
                    and record.get("artifact_id") == reference.get("artifact_id")
                    and record.get("sha256") == reference.get("artifact_digest")
                ):
                    return ref, add(ref, record, origin)
            return ref, None
        if not isinstance(reference, str):
            return str(reference), None
        if reference == "intrinsic:sealed-manifest":
            if reference not in by_ref:
                payload = (directory / "manifest.json").read_bytes()
                record = {
                    "path": "manifest.json",
                    "sha256": sha256_bytes(payload),
                    "size_bytes": len(payload),
                    "mime_type": "application/json",
                }
                add(reference, record, run_id)
            return reference, by_ref[reference]
        if reference.startswith("file:"):
            ref = by_path.get(reference.removeprefix("file:"), reference)
            return ref, by_ref.get(ref)
        if reference.startswith("intrinsic:"):
            return reference, None
        ref = f"artifact:{reference.removeprefix('artifact:')}"
        return ref, by_ref.get(ref)

    by_requirement: dict[str, list[str]] = {}
    incomplete: set[str] = set()
    unresolved: list[dict[str, Any]] = []
    for evidence_id, references in manifest.get("required_evidence", {}).items():
        linked: list[str] = []
        for reference in references if isinstance(references, list) else ():
            ref, entry = resolve(reference)
            if entry is None:
                unresolved.append({"requirement_id": evidence_id, "ref": ref})
                incomplete.add(evidence_id)
                continue
            if ref not in linked:
                linked.append(ref)
            if evidence_id not in entry["evidence_requirement_ids"]:
                entry["evidence_requirement_ids"].append(evidence_id)
        by_requirement[evidence_id] = linked

    requirements = _snapshot_requirements(directory)
    by_assertion: dict[str, dict[str, Any]] = {}
    for result in judgement.assertion_results:
        refs = {f"artifact:{item}" for item in result.artifact_ids if f"artifact:{item}" in by_ref}
        missing = []
        for evidence_id in requirements.get(result.assertion_id, []):
            refs.update(by_requirement.get(evidence_id, []))
            if not by_requirement.get(evidence_id) or evidence_id in incomplete:
                missing.append(evidence_id)
        by_assertion[result.assertion_id] = {"refs": sorted(refs), "missing_requirement_ids": missing}
    return {
        "files": files,
        "by_requirement": by_requirement,
        "by_assertion": by_assertion,
        "unresolved_refs": unresolved,
    }


def _snapshot_requirements(directory: Path) -> dict[str, list[str]]:
    try:
        snapshot = yaml.safe_load((directory / "scenario.snapshot.yaml").read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    definition = snapshot.get("definition", snapshot) if isinstance(snapshot, dict) else {}
    assertions = definition.get("assertions", []) if isinstance(definition, dict) else []
    return {
        str(item.get("assertion_id")): [str(value) for value in item.get("required_evidence_ids", [])]
        for item in assertions
        if isinstance(item, dict)
    }


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
