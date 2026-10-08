"""Web read model (`controlproof.web.v1`, contracts/web-read-model.md; R-003, R-005, R-006).

Every value is copied from the catalog, sealed bundles (through `verify_bundle`) or stored readiness records. Counts are
tallies of catalog statuses; nothing here compares expected and observed values or decides a verdict. One reader reads
one root, so ACTUAL and DEMO records never meet in a view.
"""

from __future__ import annotations

import json
import threading
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from engine.evidence import verify_bundle
from engine.web import badges
from engine.web.preflight import ReadinessStore

SCHEMA_VERSION = "controlproof.web.v1"
CATALOG_PATH = Path(__file__).resolve().parents[2] / "catalog" / "mvp-scenarios.yaml"
REASON_CODES = ("INSUFFICIENT_EVIDENCE", "NO_TEST_TARGET", "ACCESS_LIMITED", "EVIDENCE_CONFLICT")
NO_RECORD_NOTE = "이 화면에 기록 없음"


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
    ) -> None:
        if origin not in {"ACTUAL", "DEMO"}:
            raise ValueError("origin must be ACTUAL or DEMO")
        self.catalog = catalog
        self.run_root = Path(run_root)
        self.readiness = readiness
        self.origin = origin
        self.cache = cache or VerifyCache()

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
            "target": {"name": "WhyYou", "target_version": self._target_version()},
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
        }

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
        found: dict[str, list[str]] = {}
        if not self.run_root.is_dir():
            return found
        for directory in sorted(self.run_root.iterdir()):
            if not (directory / "manifest.json").is_file():
                continue
            try:
                run = json.loads((directory / "run.json").read_text(encoding="utf-8"))
                found.setdefault(str(run["scenario_id"]), []).append(directory.name)
            except (OSError, ValueError, KeyError, TypeError):
                continue
        return found

    def _target_version(self) -> str | None:
        versions = []
        for entry in self.catalog["scenarios"]:
            for profile in entry["profiles"]:
                record = self.readiness.latest(entry["id"], profile["execution_profile"]) or {}
                payload = record.get("stored_payload") or {}
                if payload.get("target_version"):
                    versions.append((record.get("checked_at") or "", payload["target_version"]))
        return max(versions)[1] if versions else None

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
