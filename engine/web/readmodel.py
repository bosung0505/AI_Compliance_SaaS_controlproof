"""Web read model (`controlproof.web.v1`, contracts/web-read-model.md; R-003, R-005, R-006).

Every value is copied from the catalog, sealed bundles (through `verify_bundle`) or stored readiness records. Counts are
tallies of catalog statuses; nothing here compares expected and observed values or decides a verdict. One reader reads
one root, so ACTUAL and DEMO records never meet in a view.
"""

from __future__ import annotations

import json
import threading
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from engine.evidence import scan_bytes_strict, sha256_bytes, verify_bundle
from engine.presentation import load_bundle_summary
from engine.web import badges
from engine.web.memos import MemoStore
from engine.web.preflight import ReadinessStore

SCHEMA_VERSION = "controlproof.web.v1"
CATALOG_PATH = Path(__file__).resolve().parents[2] / "catalog" / "mvp-scenarios.yaml"
REASON_CODES = ("INSUFFICIENT_EVIDENCE", "NO_TEST_TARGET", "ACCESS_LIMITED", "EVIDENCE_CONFLICT")
NO_RECORD_NOTE = "이 화면에 기록 없음"
VIEW_LIMIT_BYTES = 256 * 1024
TEXT_MIME_TYPES = {"application/json", "application/x-ndjson", "application/yaml", "text/yaml"}
RESULT_LINK_LIMIT = 5
# Human names for sealed files (FR-015, FR-019); the file names themselves stay in developer details.
DISPLAY_NAMES = {
    "run.json": "실행 기록",
    "judgement.json": "판정 기록",
    "assertions.json": "규칙별 결과 기록",
    "manifest.json": "봉인 목록",
    "scenario.snapshot.yaml": "실행한 시나리오 정의",
    "target.snapshot.json": "대상 버전 기록",
    "environment.snapshot.json": "실행 환경 기록",
    "subjects.json": "합성 대상 목록",
    "faults.jsonl": "시험 조건 적용·해제 기록",
    "observations.jsonl": "관찰 기록",
    "checkpoints.jsonl": "단계 진행 기록",
    "recovery.json": "복구 기록",
    "effects.jsonl": "대상 서비스 상태 변화 기록",
    "delivery-attempts.jsonl": "처리 재시도 기록",
    "queue-topology.snapshot.json": "작업 대기열 구성 기록",
    "terminal-failure.json": "최종 실패 표시 기록",
    "retest-link.json": "재시험 부모 연결 기록",
    "retest-diff.json": "재시험 변경 차원 기록",
    "change-injections.jsonl": "변경 주입·복원 기록",
    "citation-cases.jsonl": "인용 시험 결과",
    "model-emissions.jsonl": "시험용 고정 모델 출력",
    "report-reads.jsonl": "회사 화면 리포트 조회",
    "report-records.jsonl": "리포트 저장 기록",
    "storage-probe.json": "저장소 직접 쓰기 진단",
    "spec004-capabilities.json": "준비 항목 기록",
    "spec004-lanes.json": "합성 대상 경로 기록",
    "policy-and-consent.json": "동의 정책과 동의 기록",
    "causal-events.jsonl": "사건 순서 기록",
    "causal-edges.jsonl": "사건 연결 기록",
    "baseline-effects.jsonl": "기준선 상태 기록",
    "bypass-attempts.jsonl": "우회 시도 기록",
    "protected-effects.jsonl": "보호 대상 처리 기록",
    "fault-receipts.jsonl": "장애 주입 수신 기록",
}
LIMITATION_LABELS = {
    "FIXTURE_INTERVIEW_INPUT": "합성 면접 입력 사용",
    "EXTERNAL_AI_BLOCKED": "외부 AI 호출 차단",
    "FIXED_MODEL_SUBSTITUTE": "실제 AI 대신 시험용 고정 모델 사용",
}
ARTIFACT_NAMES = {"image/png": "화면 캡처", "application/json": "수집한 원본 기록"}


class RunNotFound(LookupError):
    """No sealed bundle with that Run ID in this root."""


class EvidenceNotFound(LookupError):
    """The reference is not an evidence entry of this Run."""


class IntegrityBlocked(RuntimeError):
    """The Run failed integrity, so its evidence is not shown (HTTP 422)."""


def load_catalog(path: Path | None = None) -> dict[str, Any]:
    return yaml.safe_load(Path(path or CATALOG_PATH).read_text(encoding="utf-8"))


class VerifyCache:
    """`verify_bundle` results keyed by `bundle_digest` and every file's (relative path, size, mtime) (FR-017).

    Any change after sealing changes the key, so the bundle is verified again instead of served from the cache.
    """

    def __init__(self) -> None:
        self._entries: dict[str, tuple[tuple[Any, ...], dict[str, Any]]] = {}
        self._lock = threading.Lock()
        self.misses = 0

    def verify(self, bundle: Path) -> dict[str, Any]:
        key = _cache_key(bundle)
        with self._lock:
            cached = self._entries.get(str(bundle))
            if cached is not None and cached[0] == key:
                return cached[1]
        result = verify_bundle(bundle)
        with self._lock:
            self.misses += 1
            self._entries[str(bundle)] = (key, result)
        return result


def _cache_key(bundle: Path) -> tuple[Any, ...]:
    try:
        digest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8")).get("bundle_digest")
    except (OSError, ValueError, AttributeError):
        digest = None
    files = []
    for path in sorted(bundle.rglob("*")):
        if path.is_file():
            stat = path.stat()
            files.append((path.relative_to(bundle).as_posix(), stat.st_size, stat.st_mtime_ns))
    return (digest, tuple(files))


def integrity_of(result: dict[str, Any]) -> str:
    """`VERIFIED`, `INVALID`, or `UNREADABLE` when the manifest itself could not be read."""
    if result["bundle_status"] == "VERIFIED":
        return "VERIFIED"
    unreadable = any(
        item.startswith("manifest.json:") and item.split(":", 1)[1] in {"FileNotFoundError", "JSONDecodeError", "object"}
        for item in result.get("mismatched_files", [])
    )
    return "UNREADABLE" if unreadable else "INVALID"


class WorkbenchReader:
    def __init__(
        self,
        catalog: dict[str, Any],
        run_root: Path,
        *,
        readiness: ReadinessStore,
        origin: str = "ACTUAL",
        cache: VerifyCache | None = None,
        memos: MemoStore | None = None,
    ) -> None:
        if origin not in {"ACTUAL", "DEMO"}:
            raise ValueError("origin must be ACTUAL or DEMO")
        self.catalog = catalog
        self.run_root = Path(run_root)
        self.readiness = readiness
        self.origin = origin
        self.cache = cache or VerifyCache()
        self.memos = memos

    def header(self, view: str) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "view": view,
            "generated_at": datetime.now(UTC).isoformat(),
            "environment_kind": "LOCAL_EMULATED",
            "aws_deployment_status": "NOT_RUN",
            "claim_scope": "EXECUTED_SCENARIO_AND_EVIDENCE_ONLY",
            "data_origin": self.origin,
            "demo": self.origin == "DEMO",
        }

    def workbench(self) -> dict[str, Any]:
        bundles = self._bundles_by_scenario()
        rows = [self._row(entry, bundles.get(entry["id"], [])) for entry in self.catalog["scenarios"]]
        common = _common_checked_at(rows)
        for row in rows:
            checked = row["readiness"].get("checked_at")
            row["readiness"]["differs_from_common"] = bool(checked and common and _minute(checked) != _minute(common))
        groups = []
        for control in self.catalog["controls"]:
            members = [row for row in rows if row["control"] == control["control"]]
            groups.append(
                {"control": control["control"], "control_label": control["control_label"], "scenarios": members}
            )
        return {
            **self.header("workbench"),
            "target": {"service": "WhyYou", **self._target_identity()},
            "readiness_checked_at": common,
            "counts": _counts(rows),
            "count_members": _count_members(rows),
            "treatment_counts": dict(Counter(entry["mvp_treatment"] for entry in self.catalog["scenarios"])),
            "groups": groups,
            "retest_needed": [{"scenario_id": row["id"]} for row in rows if row["official"]["result"] == "FAIL"],
            "preserved_first_failures": self._preserved_first_failures(),
            "fixed_scope_sentence": " ".join(self.catalog["fixed_scope_sentence"].split()),
        }

    def _row(self, entry: dict[str, Any], local: list[str]) -> dict[str, Any]:
        status = entry["official_status"]
        official_ids = {record["run_id"] for record in status.get("records", [])}
        official = []
        mismatch = None
        for record in status.get("records", []):
            bundle = self.run_root / record["run_id"]
            if not bundle.is_dir():
                continue
            integrity = integrity_of(self.cache.verify(bundle))
            verdict = _bundle_verdict(bundle) if integrity == "VERIFIED" else None
            official.append(
                {"run_id": record["run_id"], "role": record["role"], "integrity": integrity, "verdict": verdict}
            )
            if mismatch is None and verdict is not None and verdict != record["result"]:
                mismatch = {"run_id": record["run_id"], "bundle_verdict": verdict, "catalog_result": record["result"]}
        present = bool(official)
        return {
            "id": entry["id"],
            "control": entry["control"],
            "question": entry["question"],
            "target_exists": entry["target_exists"],
            "mvp_treatment": entry["mvp_treatment"],
            "execution_mode": _execution_mode(entry),
            "readiness": self._readiness(entry),
            "official": {
                "result": status["result"],
                "reason_code": status.get("reason_code"),
                "badge": badges.result_badge(status["result"], status.get("reason_code")).key,
                "note": status.get("note"),
                "summary": status.get("summary"),
            },
            "records_on_this_pc": {
                "official_present": present,
                "official": official,
                "web_validation_runs": sum(1 for run_id in local if run_id not in official_ids),
                "validation_ref": status["validation_ref"],
                "note": None if present or entry["mvp_treatment"] != "EXECUTED" else NO_RECORD_NOTE,
            },
            "mismatch": mismatch,
            "result_links": self._result_links(official, local),
        }

    def _result_links(self, official: list[dict[str, Any]], local: list[str]) -> list[dict[str, Any]]:
        links = [{"run_id": item["run_id"], "role": "OFFICIAL"} for item in official]
        role = "DEMO" if self.origin == "DEMO" else "WEB_VALIDATION"
        links += [{"run_id": run_id, "role": role} for run_id in local if run_id not in {i["run_id"] for i in official}]
        return links[:RESULT_LINK_LIMIT]

    def _readiness(self, entry: dict[str, Any]) -> dict[str, Any]:
        if entry["mvp_treatment"] == "NOT_RUN":
            return {
                "value": "RUNNER_NOT_READY", "badge": "runner_not_ready", "checked_at": None, "source": "CATALOG",
                "note": "실행 프로필 없음(이번 범위에서 실행하지 않음)", "profiles": [],
            }
        if entry["mvp_treatment"] == "NO_TEST_TARGET":
            return {
                "value": "NO_TEST_TARGET", "badge": "readiness_no_test_target", "checked_at": None,
                "source": "CATALOG", "note": None, "profiles": [],
            }
        profiles = [
            _profile_readiness(profile["execution_profile"], self.readiness.latest(entry["id"], profile["execution_profile"]))
            for profile in entry["profiles"]
        ]
        recorded = [item for item in profiles if item["recorded"]]
        if not recorded:
            return {
                "value": None, "badge": None, "checked_at": None, "source": "NONE", "note": "확인 기록 없음",
                "profiles": profiles,
            }
        # Row value (ID-005-07): the shared value when every profile has the same record, otherwise the first profile in
        # catalog order that is not READY. Each profile's own value stays in `profiles`.
        if len(recorded) == len(profiles) and len({item["badge"] for item in profiles}) == 1:
            shown = profiles[0]
        else:
            shown = next(item for item in profiles if item["badge"] != "ready")
        return {
            "value": shown["value"],
            "badge": shown["badge"],
            "checked_at": min(item["checked_at"] for item in recorded if item["checked_at"]),
            "source": "PREFLIGHT",
            "note": shown.get("note") if shown["recorded"] else "확인 기록 없음",
            "profiles": profiles,
        }

    def _bundles_by_scenario(self) -> dict[str, list[str]]:
        """Run IDs per scenario in this root, newest first."""
        found: dict[str, list[tuple[str, str]]] = {}
        if not self.run_root.is_dir():
            return {}
        for directory in sorted(self.run_root.iterdir()):
            if not (directory / "manifest.json").is_file():
                continue
            try:
                run = json.loads((directory / "run.json").read_text(encoding="utf-8"))
                found.setdefault(str(run["scenario_id"]), []).append((str(run.get("started_at") or ""), directory.name))
            except (OSError, ValueError, KeyError, TypeError):
                continue
        return {key: [name for _, name in sorted(items, reverse=True)] for key, items in found.items()}

    def _target_version(self) -> str | None:
        return self._target_identity()["target_version"]

    def _target_identity(self) -> dict[str, str | None]:
        """Target version and short WhyYou commit from the latest readiness record (ID-005-09)."""
        versions = []
        for entry in self.catalog["scenarios"]:
            for profile in entry["profiles"]:
                record = self.readiness.latest(entry["id"], profile["execution_profile"]) or {}
                payload = record.get("stored_payload") or {}
                if payload.get("target_version"):
                    commit = ((payload.get("target_snapshot") or {}).get("git_commit_sha") or "")[:7] or None
                    versions.append((record.get("checked_at") or "", payload["target_version"], commit))
        if not versions:
            return {"target_version": None, "target_commit": None}
        _, version, commit = max(versions, key=lambda item: item[0])
        return {"target_version": version, "target_commit": commit}

    def _preserved_first_failures(self) -> list[dict[str, Any]]:
        lineages = []
        for entry in self.catalog["scenarios"]:
            records = entry["official_status"].get("records", [])
            for parent in records:
                if parent["role"] != "parent" or parent["result"] != "FAIL":
                    continue
                final = next(
                    (
                        record
                        for record in records
                        if record["role"] == "final" and record.get("execution_profile") == parent.get("execution_profile")
                    ),
                    None,
                )
                if final is not None:
                    lineages.append(
                        {
                            "scenario_id": entry["id"],
                            "execution_profile": parent.get("execution_profile"),
                            "parent_run_id": parent["run_id"],
                            "parent_result": parent["result"],
                            "parent_badge": badges.result_badge(parent["result"], None).key,
                            "child_run_id": final["run_id"],
                            "child_result": final["result"],
                            "child_badge": badges.result_badge(final["result"], None).key,
                        }
                    )
        return lineages


    # -- run view (US2) --------------------------------------------------------------------------------------------
    def run(self, run_id: str) -> dict[str, Any]:
        bundle = self._bundle(run_id)
        record = _read_json(bundle / "run.json") or {}
        state = record.get("state")
        integrity = self._integrity(bundle, state)
        verified = integrity["status"] == "VERIFIED"
        view: dict[str, Any] = {
            **self.header("run"),
            "run": self._run_block(bundle, record),
            "integrity": integrity,
            "integrity_display": _integrity_display(integrity, self.cache.verify(bundle)["bundle_status"]),
            "display_order": _display_order(integrity["status"], state),
            "safety_badges": ["restore_failed"] if state == "RESTORE_FAILED" else [],
            "verdict": None,
            "assertions": None,
            "evidence": None,
            "steps": [],
            "conditions": [],
            "restore": None,
            "limitations": [],
            "memos": self.memos.list(run_id) if self.memos else [],
            "memo_allowed": self.origin == "ACTUAL",
            "developer": {
                "files": _manifest_paths(bundle),
                "problems": integrity["problems"],
                "target_version": record.get("target_version"),
                "steps": [
                    {"phase": item.get("phase"), "step_id": item.get("step_id"), "always_run": bool(item.get("always_run"))}
                    for item in _snapshot_definition(bundle).get("steps", [])
                    if isinstance(item, dict)
                ],
            },
            "phase_summary": [],
        }
        if not verified:
            return view
        summary = load_bundle_summary(bundle)
        snapshot = _snapshot_definition(bundle)
        index = summary["evidence_index"]
        entry = self._catalog_entry(summary["scenario_id"])
        failed = list(summary["failed_assertions"])
        view["verdict"] = {
            "value": summary["verdict"],
            "reason_code": summary["reason_code"],
            "summary": summary["summary"],
            "badge": badges.result_badge(summary["verdict"], summary["reason_code"]).key,
            "target_verdict": state not in {"ABORTED", "RESTORE_FAILED"},
            "plain_meaning": _verdict_meaning(summary["verdict"], summary["reason_code"], failed, state),
            "impact": (
                ((entry or {}).get("explanation", {}).get("failure_impact") or {}).get("text")
                if summary["verdict"] != "PASS" else None
            ),
            "missing_evidence": list(summary.get("missing_evidence") or []),
        }
        requirements = {item.get("assertion_id"): item for item in snapshot.get("assertions", []) if isinstance(item, dict)}
        view["assertions"] = [
            {
                "assertion_id": item["assertion_id"],
                "description": requirements.get(item["assertion_id"], {}).get("description"),
                "status": item["status"],
                "reason_code": item["reason_code"],
                "badge": badges.result_badge(item["status"], item["reason_code"]).key,
                "expected": item["expected"],
                "actual": item["actual"],
                "detail": item["detail"],
                "source_requirements": item["source_requirements"],
                "required_evidence_ids": list(requirements.get(item["assertion_id"], {}).get("required_evidence_ids", [])),
                "evidence_refs": index["by_assertion"].get(item["assertion_id"], {}).get("refs", []),
                "evidence_groups": [],
                "missing_evidence_ids": index["by_assertion"].get(item["assertion_id"], {}).get("missing_requirement_ids", []),
                "plain_meaning": _assertion_meaning(item["status"], item["reason_code"]),
            }
            for item in summary["assertions"]
        ]
        linked_rules: dict[str, list[str]] = {}
        for assertion_id, item in index["by_assertion"].items():
            for ref in item["refs"]:
                linked_rules.setdefault(ref, []).append(assertion_id)
        phases = _manifest_phases(bundle)
        labels = self.catalog.get("evidence_labels", {})
        view["evidence"] = [
            {
                **item,
                "evidence_name": _evidence_name(item, phases.get(item["ref"]), labels),
                "evidence_kind": _display_name(item),
                "phase": phases.get(item["ref"]),
                "assertion_ids": sorted(linked_rules.get(item["ref"], [])),
                **_viewability(self._evidence_path(bundle, item), item.get("mime_type")),
            }
            for item in index["files"]
        ]
        for item in view["evidence"]:
            item.pop("text", None)
        _number_duplicate_names(view["evidence"])
        by_ref = {item["ref"]: item for item in view["evidence"]}
        for assertion in view["assertions"]:
            assertion["evidence_groups"] = _evidence_groups(assertion["evidence_refs"], by_ref)
        view["unresolved_refs"] = index["unresolved_refs"]
        view["steps"] = [
            {"phase": item.get("phase"), "step_id": item.get("step_id"), "always_run": bool(item.get("always_run"))}
            for item in snapshot.get("steps", [])
            if isinstance(item, dict)
        ]
        view["conditions"] = _conditions(bundle, record, self.catalog.get("condition_labels", {}))
        view["restore"] = _restore(bundle, record, summary, snapshot)
        view["phase_summary"] = _phase_summary(view["steps"], view["conditions"], view["restore"])
        codes = list(summary.get("limitations") or [])
        view["limitations"] = [LIMITATION_LABELS.get(code, code) for code in codes]
        view["developer"]["limitation_codes"] = codes
        raw_scope = list(summary.get("unverified_scope") or [])
        scope_labels = self.catalog.get("scope_labels", {})
        view["unverified_scope"] = [scope_labels.get(item, "기타 미검증 항목(개발자용 정보 참고)") for item in raw_scope]
        view["legal_scope_notice"] = summary.get("legal_scope_notice")
        view["developer"].update(
            {
                "model_fixture_id": summary.get("model_fixture_id"),
                "target_id": summary.get("target_id"),
                "raw_actual": {item["assertion_id"]: item["actual"] for item in summary["assertions"]},
                "missing_evidence_links": integrity["aborted_missing_evidence"],
                "unverified_scope_raw": raw_scope,
            }
        )
        return view

    def evidence(self, run_id: str, ref: str) -> dict[str, Any]:
        """One evidence entry; text only when it is text, at most 256 KB and passes the strict scan (R-009 e)."""
        bundle = self._bundle(run_id)
        record = _read_json(bundle / "run.json") or {}
        if self._integrity(bundle, record.get("state"))["status"] != "VERIFIED":
            raise IntegrityBlocked(run_id)
        index = load_bundle_summary(bundle)["evidence_index"]
        item = next((entry for entry in index["files"] if entry["ref"] == ref), None)
        if item is None:
            raise EvidenceNotFound(ref)
        return {
            **self.header("evidence"),
            "run_id": run_id,
            "ref": ref,
            "evidence_name": _display_name(item),
            "relative_path": item["relative_path"],
            "mime_type": item.get("mime_type"),
            "size_bytes": item.get("size_bytes"),
            "sha256": item.get("sha256"),
            "evidence_requirement_ids": item.get("evidence_requirement_ids", []),
            **_viewability(self._evidence_path(bundle, item), item.get("mime_type")),
        }

    def _bundle(self, run_id: str) -> Path:
        try:
            canonical = str(uuid.UUID(str(run_id)))
        except ValueError as exc:
            raise RunNotFound(run_id) from exc
        bundle = self.run_root / canonical
        if canonical != run_id or not bundle.is_dir():
            raise RunNotFound(run_id)
        return bundle

    def _evidence_path(self, bundle: Path, item: dict[str, Any]) -> Path | None:
        relative = str(item.get("relative_path") or "").removeprefix("<run_root>/")
        candidate = (self.run_root / relative).resolve()
        root = self.run_root.resolve()
        if root not in candidate.parents or not candidate.is_file():
            return None
        return candidate

    def _integrity(self, bundle: Path, state: str | None) -> dict[str, Any]:
        result = self.cache.verify(bundle)
        if result["bundle_status"] == "VERIFIED":
            return {"status": "VERIFIED", "problems": [], "aborted_missing_evidence": []}
        problems = sorted(set(result.get("missing_files", [])) | set(result.get("mismatched_files", [])))
        links_only = (
            not result.get("mismatched_files")
            and result.get("missing_files")
            and all(item.startswith("evidence:") for item in result["missing_files"])
        )
        # ID-005-01: an ABORTED Run whose only problem is missing required-evidence links keeps its sealed integrity;
        # the missing links are listed. The CLI verify result itself is unchanged.
        relaxed_ok = (
            state == "ABORTED"
            and links_only
            and verify_bundle(bundle, require_all_evidence=False)["bundle_status"] == "VERIFIED"
        )
        if relaxed_ok:
            missing = sorted(item.split(":", 1)[1] for item in result["missing_files"])
            return {"status": "VERIFIED", "problems": [], "aborted_missing_evidence": missing}
        return {"status": integrity_of(result), "problems": problems, "aborted_missing_evidence": []}

    def _run_block(self, bundle: Path, record: dict[str, Any]) -> dict[str, Any]:
        manifest = bundle / "manifest.json"
        official = {
            item["run_id"]
            for entry in self.catalog["scenarios"]
            for item in entry["official_status"].get("records", [])
        }
        if self.origin == "DEMO":
            role = "OTHER"
        else:
            role = "OFFICIAL" if bundle.name in official else "WEB_VALIDATION"
        return {
            "run_id": bundle.name,
            "scenario_id": record.get("scenario_id"),
            "scenario_version": record.get("scenario_version"),
            "execution_profile": record.get("execution_profile") or "H03_MINIMAL_V1",
            "target_version": record.get("target_version"),
            "target_commit": ((_read_json(bundle / "target.snapshot.json") or {}).get("git_commit_sha") or "")[:7] or None,
            "run_state": record.get("state"),
            "started_at": record.get("started_at"),
            "ended_at": record.get("ended_at"),
            "record_origin": self.origin,
            "record_role": role,
            "parent_run_id": record.get("parent_run_id"),
            "manifest_sha256": sha256_bytes(manifest.read_bytes()) if manifest.is_file() else None,
        }

    def _catalog_entry(self, scenario_id: str | None) -> dict[str, Any] | None:
        return next((entry for entry in self.catalog["scenarios"] if entry["id"] == scenario_id), None)

    # -- report view (US3) -----------------------------------------------------------------------------------------
    def report(self) -> dict[str, Any]:
        workbench = self.workbench()
        rows = [row for group in workbench["groups"] for row in group["scenarios"]]
        texts = self.catalog["report"]
        bundles = self._bundles_by_scenario()
        executed = [entry for entry in self.catalog["scenarios"] if entry["mvp_treatment"] == "EXECUTED"]
        impacts = {
            entry["id"]: (entry["explanation"].get("failure_impact") or {}).get("text") for entry in executed
        }
        lineages = workbench["preserved_first_failures"]
        report: dict[str, Any] = {
            **self.header("report"),
            "fixed_scope_sentence": " ".join(
                line.strip() for line in self.catalog["fixed_scope_sentence"].splitlines() if line.strip()
            ),
            "target_and_versions": texts["target_and_versions"],
            "target_version_now": workbench["target"]["target_version"],
            "target_commit_now": workbench["target"]["target_commit"],
            "purpose_and_scope": texts["purpose_and_scope"],
            "synthetic_data_notice": texts["synthetic_data_notice"],
            "catalog_status": [
                {
                    "id": row["id"],
                    "control": row["control"],
                    "question": row["question"],
                    "result": row["official"]["result"],
                    "reason_code": row["official"]["reason_code"],
                    "badge": row["official"]["badge"],
                    "note": row["official"]["note"],
                }
                for row in rows
            ],
            "groups": [
                {"control": group["control"], "control_label": group["control_label"]} for group in workbench["groups"]
            ],
            "counts": workbench["counts"],
            "count_members": workbench["count_members"],
            "scenario_expectations": [
                {
                    "scenario_id": entry["id"],
                    "result": entry["official_status"]["result"],
                    "reason_code": entry["official_status"].get("reason_code"),
                    "badge": badges.result_badge(
                        entry["official_status"]["result"], entry["official_status"].get("reason_code")
                    ).key,
                    "note": entry["official_status"].get("note"),
                    "summary": entry["official_status"]["summary"],
                    "validation_ref": entry["official_status"]["validation_ref"],
                }
                for entry in executed
            ],
            "major_failures": [{**item, "impact": impacts.get(item["scenario_id"])} for item in lineages],
            "evidence_summary": [
                {
                    "scenario_id": entry["id"],
                    "records_on_this_pc": len(bundles.get(entry["id"], [])),
                    "official_present": any(
                        (self.run_root / item["run_id"]).is_dir() for item in entry["official_status"].get("records", [])
                    ),
                    "validation_ref": entry["official_status"]["validation_ref"],
                    "missing": (
                        [f"{entry['official_status'].get('note') or ''} {entry['official_status']['summary']}".strip()]
                        if entry["official_status"].get("reason_code") == "INSUFFICIENT_EVIDENCE"
                        else []
                    ),
                }
                for entry in executed
            ],
            "versions": texts["versions"],
            "lineages": lineages,
            "test_only_additions": [{**item, "is_product_feature": False} for item in texts["test_only_additions"]],
            "unverified_scope": list(texts["unverified_scope"]),
            "other_pc_reproduction": texts["other_pc_reproduction"],
            "limitations": list(texts["limitations"]),
            "legal_notice": texts["legal_notice"],
            "ai_score_principle": texts["ai_score_principle"],
            "human_decision_location": texts["human_decision_location"],
            "no_test_target": [
                {"id": row["id"], "question": row["question"], "badge": row["official"]["badge"]}
                for row in rows
                if row["mvp_treatment"] == "NO_TEST_TARGET"
            ],
            "one_screen_notice": texts["one_screen_notice"],
            "developer": {"model_fixtures": list(texts["model_fixtures"])},
        }
        present = {
            "R1": report["target_and_versions"],
            "R2": report["purpose_and_scope"] and report["fixed_scope_sentence"],
            "R3": report["synthetic_data_notice"],
            "R4": len(report["catalog_status"]) == 12,
            "R5": report["counts"],
            "R6": report["scenario_expectations"],
            "R7": report["major_failures"],
            "R8": report["evidence_summary"],
            "R9": report["versions"],
            "R10": report["lineages"],
            "R11": report["test_only_additions"],
            "R12": report["unverified_scope"],
            "R13": report["legal_notice"],
            "C1": report["counts"],
            "C2": report["evidence_summary"],
            "C3": report["ai_score_principle"],
            "C4": report["human_decision_location"],
            "C5": report["lineages"],
            "C6": len(report["no_test_target"]) == 3,
            "C7": report["one_screen_notice"],
            "C8": report["unverified_scope"] and report["claim_scope"],
            "C9": report["legal_notice"],
        }
        report["items_present"] = {key: bool(value) for key, value in present.items()}
        return report


def _profile_readiness(profile: str, record: dict[str, Any] | None) -> dict[str, Any]:
    if record is None:
        return {"execution_profile": profile, "recorded": False, "value": None, "badge": None, "checked_at": None}
    if record.get("result_kind") == "READINESS" and record.get("readiness"):
        return {
            "execution_profile": profile, "recorded": True, "value": record["readiness"],
            "badge": badges.readiness_badge(record["readiness"]).key, "checked_at": record.get("checked_at"),
            "note": record.get("operator_action"), "capabilities": record.get("capabilities"),
        }
    # A tool error (usage error, timeout, unreadable output) is not a readiness value (R-010).
    return {
        "execution_profile": profile, "recorded": True, "value": None, "badge": "tool_error",
        "checked_at": record.get("checked_at"), "error_kind": record.get("error_kind"),
        "note": record.get("operator_action"),
    }


def _bundle_verdict(bundle: Path) -> str | None:
    try:
        return json.loads((bundle / "judgement.json").read_text(encoding="utf-8")).get("verdict")
    except (OSError, ValueError, AttributeError):
        return None


def _execution_mode(entry: dict[str, Any]) -> str:
    if entry["mvp_treatment"] != "EXECUTED":
        return entry["mvp_treatment"]
    count = len(entry["profiles"])
    return "실제 실행" if count == 1 else f"실제 실행 ({count}개 프로필)"


def _counts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    results = Counter(row["official"]["result"] for row in rows)
    reasons = Counter(row["official"]["reason_code"] for row in rows if row["official"]["result"] == "INCONCLUSIVE")
    by_reason = {code: reasons.get(code, 0) for code in REASON_CODES}
    return {
        "PASS": results.get("PASS", 0),
        "FAIL": results.get("FAIL", 0),
        "NOT_RUN": results.get("NOT_RUN", 0),
        "INCONCLUSIVE": {"total": sum(by_reason.values()), "by_reason": by_reason},
    }


def _count_members(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Scenario IDs behind each count card, in catalog order (display only)."""
    members: dict[str, Any] = {"PASS": [], "FAIL": [], "NOT_RUN": [], "INCONCLUSIVE": {code: [] for code in REASON_CODES}}
    for row in rows:
        result = row["official"]["result"]
        if result == "INCONCLUSIVE":
            members["INCONCLUSIVE"][row["official"]["reason_code"]].append(row["id"])
        else:
            members[result].append(row["id"])
    return members


def _common_checked_at(rows: list[dict[str, Any]]) -> str | None:
    times = [row["readiness"]["checked_at"] for row in rows if row["readiness"].get("checked_at")]
    return max(times) if times else None


def _minute(value: str) -> str:
    try:
        return datetime.fromisoformat(value).astimezone(UTC).strftime("%Y-%m-%dT%H:%M")
    except ValueError:
        return value[:16]


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _snapshot_definition(bundle: Path) -> dict[str, Any]:
    try:
        snapshot = yaml.safe_load((bundle / "scenario.snapshot.yaml").read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    if not isinstance(snapshot, dict):
        return {}
    definition = snapshot.get("definition", snapshot)
    return definition if isinstance(definition, dict) else {}


def _manifest_paths(bundle: Path) -> list[str]:
    manifest = _read_json(bundle / "manifest.json") or {}
    return [record.get("path") for record in manifest.get("files", []) if isinstance(record, dict)]


def _manifest_phases(bundle: Path) -> dict[str, str]:
    manifest = _read_json(bundle / "manifest.json") or {}
    phases = {}
    for record in manifest.get("files", []):
        if isinstance(record, dict) and record.get("artifact_id") and record.get("phase"):
            phases[f"artifact:{record['artifact_id']}"] = record["phase"]
    return phases


def _display_order(integrity: str, state: str | None) -> list[str]:
    if integrity != "VERIFIED":
        return ["integrity", "run_state"]
    if state == "ABORTED":
        return ["run_state", "integrity", "verdict"]
    if state == "RESTORE_FAILED":
        return ["safety", "integrity", "verdict"]
    return ["integrity", "verdict"]


def _verdict_meaning(verdict: str, reason_code: str | None, failed: list[str], state: str | None) -> str:
    if state == "ABORTED":
        return "실행이 중간에 중단돼 이 결과는 대상 서비스의 판정이 아닙니다. 봉인된 판정 값은 그대로 함께 보입니다."
    if state == "RESTORE_FAILED":
        return "복구가 끝나지 않은 실행 안전 문제입니다. 대상 서비스의 FAIL이 아니며 사람이 정리를 확인해야 합니다."
    if verdict == "PASS":
        return "기대 결과와 필수 증적이 모두 확인됐습니다."
    if verdict == "FAIL":
        return f"규칙 {', '.join(failed)}에서 실제 동작이 기대와 달랐습니다. 아래 규칙별 결과에서 기대와 관찰을 확인하세요."
    reason = badges.result_badge("INCONCLUSIVE", reason_code)
    return f"결론을 낼 수 없습니다. 사유: {reason.description}."


def _assertion_meaning(status: str, reason_code: str | None) -> str:
    if status == "PASS":
        return "기대대로 관찰됐습니다."
    if status == "FAIL":
        return "기대와 관찰이 다릅니다."
    return f"결론을 낼 수 없습니다: {badges.result_badge('INCONCLUSIVE', reason_code).description}."


def _display_name(item: dict[str, Any]) -> str:
    ref = item["ref"]
    if ref == "intrinsic:sealed-manifest":
        return "봉인 목록"
    name = str(item.get("relative_path", "")).rsplit("/", 1)[-1]
    if ref.startswith("file:"):
        return DISPLAY_NAMES.get(name, "수집한 기록")
    if ref.startswith("run:"):
        return "이전 실행의 원본 기록"
    return ARTIFACT_NAMES.get(str(item.get("mime_type")), "수집한 원본 기록")


def _viewability(path: Path | None, mime_type: str | None) -> dict[str, Any]:
    if path is None:
        return {"viewable": False, "reason": "원본 파일을 찾을 수 없습니다.", "text": None}
    if not (str(mime_type) in TEXT_MIME_TYPES or str(mime_type).startswith("text/")):
        return {"viewable": False, "reason": f"텍스트 형식이 아니라 원문을 보이지 않습니다(형식: {mime_type}).", "text": None}
    if path.stat().st_size > VIEW_LIMIT_BYTES:
        return {"viewable": False, "reason": "256 KB를 넘어 화면에 원문을 보이지 않습니다.", "text": None}
    payload = path.read_bytes()
    findings = scan_bytes_strict(payload)
    if findings:
        rules = ", ".join(sorted(findings))
        return {"viewable": False, "reason": f"경로·토큰·개인정보 검사에 걸려 원문을 보이지 않습니다(규칙: {rules}).", "text": None}
    return {"viewable": True, "reason": None, "text": payload.decode("utf-8", errors="replace")}


def _conditions(bundle: Path, record: dict[str, Any], labels: dict[str, str]) -> list[dict[str, Any]]:
    """Applied and released test conditions as the bundle recorded them (no inference); Korean labels (ID-005-09)."""
    conditions = []
    for line in _jsonl(bundle / "change-injections.jsonl"):
        kind = str(line.get("kind"))
        label = labels.get(kind, "시험용 데이터 변경")
        raw = f"{kind} ({line.get('lane_id')})"
        if line.get("applied_at"):
            conditions.append({"kind": "APPLIED", "label": label, "raw": raw, "at": line["applied_at"]})
        if line.get("restored_at"):
            conditions.append({"kind": "RELEASED", "label": label, "raw": raw, "at": line["restored_at"]})
    if record.get("fault_ever_applied"):
        conditions.append({"kind": "APPLIED", "label": "시험용 장애 주입", "raw": "fault_ever_applied", "at": None})
    attempts = [line for line in _jsonl(bundle / "faults.jsonl") if line.get("environment_restore")]
    if attempts:
        last = attempts[-1]["environment_restore"]
        conditions.append(
            {
                "kind": "RELEASED",
                "label": f"시험용 장애 해제와 환경 복구(시도 {len(attempts)}회, 마지막 결과 {last})",
                "raw": "faults.jsonl",
                "at": None,
            }
        )
    return conditions


PHASE_LABELS = {"BASELINE": "기준선", "INJECTED": "주입", "RECOVERED": "복구"}


def _phase_summary(
    steps: list[dict[str, Any]], conditions: list[dict[str, Any]], restore: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """Plain per-phase summary of the sealed definition and recorded conditions; step IDs stay in developer details."""
    summary = []
    applied = sorted({item["label"] for item in conditions if item["kind"] == "APPLIED"})
    released = sorted({item["label"] for item in conditions if item["kind"] == "RELEASED"})
    for phase, label in PHASE_LABELS.items():
        members = [step for step in steps if step.get("phase") == phase]
        always = sum(1 for step in members if step.get("always_run"))
        if phase == "BASELINE":
            sentences = [f"정의된 단계 {len(members)}개로 시험 전 상태와 합성 대상을 준비·기록합니다."]
        elif phase == "INJECTED":
            sentences = [f"정의된 단계 {len(members)}개로 시험 조건을 적용하고 대상의 반응을 관찰합니다."]
            sentences.append("적용한 시험 조건: " + (", ".join(applied) if applied else "기록 없음"))
        else:
            sentences = [f"정의된 단계 {len(members)}개(실패해도 항상 실행 {always}개)로 시험 조건을 되돌립니다."]
            sentences.append("해제한 시험 조건: " + (", ".join(released) if released else "기록 없음"))
            sentences.append("복구 결과: " + str((restore or {}).get("status") or "기록 없음"))
        summary.append({"phase": phase, "label": label, "step_count": len(members), "sentences": sentences})
    return summary


def _integrity_display(integrity: dict[str, Any], cli_status: str) -> dict[str, Any]:
    """Screen wording that never contradicts the CLI verify value (ID-005-09 T057a)."""
    if integrity["aborted_missing_evidence"]:
        missing = ", ".join(integrity["aborted_missing_evidence"])
        label = f"봉인 무결성 확인됨(봉인 파일·manifest 일치) · 명령줄 verify: {cli_status}(중단으로 빠진 필수 증적 {missing})"
    elif integrity["status"] == "VERIFIED":
        label = "봉인 무결성 확인됨 (VERIFIED)"
    elif integrity["status"] == "UNREADABLE":
        label = "기록을 읽을 수 없습니다 (UNREADABLE)"
    else:
        label = "봉인 뒤 기록이 바뀌었습니다 (INVALID)"
    return {"label": label, "cli_verify_status": cli_status}


def _evidence_name(item: dict[str, Any], phase: str | None, labels: dict[str, str]) -> str:
    """Requirement ID + short Korean label + collection phase (or record kind), e.g. "EV-02 장애 적용 요청 · 주입"."""
    requirements = item.get("evidence_requirement_ids") or []
    if not requirements:
        return _display_name(item)
    first = requirements[0]
    name = f"{first} {labels.get(first, '증적')}"
    if len(requirements) > 1:
        name += f" 외 {len(requirements) - 1}"
    if phase in PHASE_LABELS:
        detail = PHASE_LABELS[phase]
    elif str(item["ref"]).startswith("artifact:"):
        detail = "화면 캡처" if item.get("mime_type") == "image/png" else "관찰 기록"
    else:
        detail = _display_name(item)
    return f"{name} · {detail}"


def _number_duplicate_names(evidence: list[dict[str, Any]]) -> None:
    counts = Counter(item["evidence_name"] for item in evidence)
    seen: Counter[str] = Counter()
    for item in evidence:
        base = item["evidence_name"]
        item["evidence_group"] = base
        if counts[base] > 1:
            seen[base] += 1
            item["evidence_name"] = f"{base} #{seen[base]}"


def _evidence_groups(refs: list[str], by_ref: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[str]] = {}
    for ref in refs:
        item = by_ref.get(ref)
        groups.setdefault(item["evidence_group"] if item else ref, []).append(ref)
    return [{"label": label, "count": len(members), "refs": members} for label, members in groups.items()]


def _restore(bundle: Path, record: dict[str, Any], summary: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    timing = ((_read_json(bundle / "recovery.json") or {}).get("restore_timing")) or {}
    policy = snapshot.get("timing_policy") or {}
    return {
        "status": summary.get("environment_restore_status"),
        "seconds": timing.get("environment_restore_seconds"),
        "deadline_seconds": timing.get("environment_restore_deadline_seconds", policy.get("environment_restore_deadline_seconds")),
        "within_deadline": timing.get("environment_restore_within_deadline"),
        "manual_cleanup_required": bool(record.get("manual_cleanup_required")),
    }


def _jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows = []
    for line in lines:
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows
