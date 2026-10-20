"""Spec 009 executor base (N-01·N-03): preflight probes, journal, mandatory cleanup and sealed evidence.

Same shape as ``engine/executors/h01.py``: checkpoints before and after writes, cleanup in ``finally``, assertions
rebuilt from sealed rows by pure judges, and ``verify_bundle`` before the Run is returned. Adapter failures are
recorded as facts (None/UNAVAILABLE) so the judge decides INCONCLUSIVE; they never abort the Run.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy import create_engine, text

from engine.adapters.base import AdapterResult, CapabilityProbeResult
from engine.evidence import EvidenceBundleWriter, verify_bundle
from engine.lifecycle import RestoreBlockStore, TargetSubjectLock, atomic_write
from engine.models import (
    ConsentPolicySnapshot,
    ConsentStateSnapshot,
    ExecutionProfile,
    Judgement,
    ReadinessStatus,
    Run,
    canonical_json_bytes,
    utcnow,
)
from engine.readiness import evaluate_readiness
from engine.scenario import SPEC009_FIXTURES

FIXTURE_ID, FIXTURE_DIGEST = next(iter(SPEC009_FIXTURES.items()))
RESTORE_DEADLINE_SECONDS = 120
CONSENT_PATH = "/v1/applicant/consents"
SUBJECT_FIELDS = ("run_id", "lane_id", "subject_ref", "invitation_id", "applicant_id")
#: Common limitations of every Spec 009 Run (contracts/scenario-profile-v9.md, spec FR-056).
COMMON_LIMITATIONS = (
    {"id": "LOCAL_EMULATED", "text": "로컬 에뮬레이션 환경에서만 실행했습니다.", "follow_up": None},
    {"id": "SYNTHETIC_DATA", "text": "Run 소유 합성 지원자만 사용했습니다.", "follow_up": None},
    {"id": "EXTERNAL_AI_BLOCKED", "text": "외부 AI 호출을 차단했습니다.", "follow_up": None},
)
COMMON_FILES = frozenset(
    {
        "run.json",
        "scenario.snapshot.yaml",
        "target.snapshot.json",
        "environment.snapshot.json",
        "subjects.json",
        "observations.jsonl",
        "assertions.json",
        "judgement.json",
        "recovery.json",
    }
)
_RANK = {ReadinessStatus.READY: 0, ReadinessStatus.RUNNER_NOT_READY: 1, ReadinessStatus.ACCESS_BLOCKED: 2}
_ACTIONS = {
    ReadinessStatus.ACCESS_BLOCKED: "대상 API·지원자 앱이 응답하고 권한이 있는지 확인한 뒤 preflight를 다시 실행하세요.",
    ReadinessStatus.RUNNER_NOT_READY: "깨끗한 두 소스·격리 스택·fixture·Chromium을 준비하고 check 코드를 확인하세요.",
}
_CP_ROOT = Path(__file__).resolve().parents[2]


def scope_document(scenario, unverified_scope: tuple[str, ...]) -> dict[str, Any]:
    """EV9-01 scope record: YAML items and limitations verbatim plus the common Spec 009 limitations."""
    return {
        "scenario_id": scenario.scenario_id,
        "target_access": [kind.value for kind in scenario.target_access],
        "unverified_scope": list(unverified_scope),
        "unverified_scope_items": [item.model_dump(mode="json") for item in scenario.unverified_scope_items],
        "limitations": [item.model_dump(mode="json") for item in scenario.limitations],
        "common_limitations": [dict(item) for item in COMMON_LIMITATIONS],
        "excluded_scope": list(scenario.excluded_scope),
    }


def subject_identity(subject) -> dict[str, Any]:
    return {name: str(subject[name]) for name in SUBJECT_FIELDS}


def policy_identifier(policy) -> dict[str, str] | None:
    if isinstance(policy, ConsentPolicySnapshot):
        return {"version": policy.policy_version, "digest": policy.content_digest}
    return None


def state_row(value) -> dict[str, Any] | None:
    return value.model_dump(mode="json") if isinstance(value, ConsentStateSnapshot) else None


def adapter_code(value) -> str:
    return value.code if isinstance(value, AdapterResult) else "OK"


class LocalProbes:
    """Real preflight probes; SQL identifiers are module constants, never request data."""

    def __init__(self, settings, adapters) -> None:
        self.settings, self.adapters = settings, adapters

    def git(self, repo):
        branch = subprocess.check_output(["git", "-C", str(repo), "branch", "--show-current"], text=True).strip()
        dirty = bool(subprocess.check_output(["git", "-C", str(repo), "status", "--porcelain"]))
        return branch, dirty

    def whyyou_python_ready(self) -> bool:
        executable = os.environ.get("CONTROLPROOF_WHYYOU_PYTHON")
        return bool(executable) and Path(executable).is_file()

    def capture_target(self):
        return self.adapters.target.capture_target_snapshot()

    def api_get(self, path):
        response = self.adapters.target.client.http.get(path)
        return response.status_code, response.json() if response.status_code == 200 else {}

    def db_probe(self, table, columns) -> None:
        engine = create_engine(self.settings.whyyou_database_url)
        try:
            with engine.connect() as connection:
                connection.execute(text(f"SELECT {columns} FROM {table} LIMIT 0"))
        finally:
            engine.dispose()

    def applicant_app_status(self, url) -> int:
        with httpx.Client(timeout=5, trust_env=False) as client:
            return client.get(f"{url}/").status_code

    def chromium_ready(self) -> bool:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            executable = playwright.chromium.executable_path
        return bool(executable) and Path(executable).is_file()


def _blocked_or_not_ready(exc: Exception) -> ReadinessStatus:
    if isinstance(exc, (httpx.ConnectError, ConnectionError)) or any(code in str(exc) for code in ("401", "403")):
        return ReadinessStatus.ACCESS_BLOCKED
    return ReadinessStatus.RUNNER_NOT_READY


class Spec009Executor:
    """Subclasses set the profile constants and implement the scenario steps and documents."""

    profile: ExecutionProfile
    tag: str
    block_subject: str
    seed_kind: str
    fault_kind: str
    unverified_scope: tuple[str, ...]
    links: dict[str, set[str]]
    scope_file: str
    api_capabilities: tuple[str, ...]
    db_checks: tuple[tuple[str, str, tuple[str, ...]], ...]
    judge: Any

    def __init__(self, scenario, adapters, run_root, *, clock=None):
        self.scenario, self.adapters, self.run_root = scenario, adapters, Path(run_root)
        self.verification: dict[str, Any] | None = None

    @property
    def settings(self):
        return self.adapters.spec009_seed.settings

    @property
    def probes(self):
        return getattr(self.adapters, "spec009_probes", None) or LocalProbes(self.settings, self.adapters)

    # ---- preflight -------------------------------------------------------------------------------------------

    def preflight(self, target_id):
        statuses = {name: (ReadinessStatus.READY, f"{name}:READY") for name in self.scenario.required_capabilities}

        def mark(capabilities, status, detail):
            for name in capabilities:
                if _RANK[status] > _RANK[statuses[name][0]]:
                    statuses[name] = (status, detail)

        environment, version = ("target.environment.read",), ("target.version.read",)
        probes, settings, target = self.probes, self.settings, None
        if (
            target_id != "whyyou-local"
            or settings.external_ai_allowed
            or not settings.model_substitute_enabled
            or settings.model_fixture_id != FIXTURE_ID
            or settings.model_fixture_digest != FIXTURE_DIGEST
            or settings.environment_kind != "LOCAL_EMULATED"
            or settings.aws_deployment_status != "NOT_RUN"
        ):
            mark(environment, ReadinessStatus.RUNNER_NOT_READY, "SPEC009_ISOLATED_FIXTURE_REQUIRED")
        try:
            for repo in (_CP_ROOT, settings.whyyou_repo_path):
                branch, dirty = probes.git(repo)
                if dirty or branch in {"main", "master", ""}:
                    raise ValueError("source")
        except Exception:  # noqa: BLE001 - any git failure means the sources are not proven clean
            mark(version, ReadinessStatus.RUNNER_NOT_READY, "SPEC009_CLEAN_FEATURE_SOURCES_REQUIRED")
        try:
            python_ready = probes.whyyou_python_ready()
        except Exception:  # noqa: BLE001
            python_ready = False
        if not python_ready:
            mark(environment, ReadinessStatus.RUNNER_NOT_READY, "SPEC009_WHYYOU_PYTHON_REQUIRED")
        try:
            target = probes.capture_target()
        except Exception as exc:  # noqa: BLE001 - normalized readiness, never a target verdict
            mark(version, _blocked_or_not_ready(exc), "SPEC009_TARGET_SNAPSHOT_UNAVAILABLE")
        health = self._api(probes, "/internal/controlproof/health", environment, mark)
        if health is not None:
            fixture = health.get("controlproof", health)
            if (
                fixture.get("fixture_id") != FIXTURE_ID
                or fixture.get("fixture_digest") != FIXTURE_DIGEST
                or fixture.get("external_ai_isolated") is not True
            ):
                mark(environment, ReadinessStatus.RUNNER_NOT_READY, "SPEC009_LIVE_FIXTURE_UNPROVEN")
        openapi = self._api(probes, "/openapi.json", self.api_capabilities, mark)
        if openapi is not None and CONSENT_PATH not in openapi.get("paths", {}):
            mark(self.api_capabilities, ReadinessStatus.RUNNER_NOT_READY, "SPEC009_TARGET_PATH_MISSING")
        for table, columns, capabilities in self.db_checks:
            try:
                probes.db_probe(table, columns)
            except Exception:  # noqa: BLE001 - table or column missing in the target schema
                mark(capabilities, ReadinessStatus.RUNNER_NOT_READY, f"SPEC009_DB_TABLE_UNAVAILABLE:{table}")
        self._extra_checks(probes, mark)
        results = [
            CapabilityProbeResult(
                capability=name,
                status=status,
                detail=detail,
                operator_action=None if status is ReadinessStatus.READY else _ACTIONS[status],
            )
            for name, (status, detail) in statuses.items()
        ]
        return evaluate_readiness(
            self.scenario,
            target_id=target_id,
            registrations=dict(self.scenario.required_capabilities),
            probe_results=results,
            target_feature_exists=True,
            target_snapshot=target,
        )

    @staticmethod
    def _api(probes, path, capabilities, mark):
        try:
            status, body = probes.api_get(path)
        except Exception as exc:  # noqa: BLE001
            mark(capabilities, _blocked_or_not_ready(exc), "SPEC009_API_UNREACHABLE")
            return None
        if status in {401, 403}:
            mark(capabilities, ReadinessStatus.ACCESS_BLOCKED, f"SPEC009_API_ACCESS_DENIED:{status}")
            return None
        if status != 200 or not isinstance(body, dict):
            mark(capabilities, ReadinessStatus.RUNNER_NOT_READY, f"SPEC009_API_UNAVAILABLE:{status}")
            return None
        return body

    def _extra_checks(self, probes, mark) -> None:
        return None

    # ---- execute ---------------------------------------------------------------------------------------------

    def execute(
        self,
        readiness,
        *,
        operator_id="local-operator",
        parent_run_id=None,
        label=None,
        retest_records=None,
        run_id=None,
    ):
        if readiness.status != "READY":
            raise RuntimeError(f"{self.tag}_NOT_READY")
        run_id, started = run_id or uuid4(), utcnow()
        blocks = RestoreBlockStore(self.run_root)
        if blocks.blocked(readiness.target_id, self.block_subject):
            raise RuntimeError(f"{self.tag}_RESTORE_BLOCKED")
        environment = self.adapters.environment.capture_environment()
        seed = self.adapters.spec009_seed
        self._captures: dict[str, bytes] = {}
        log: list[dict[str, Any]] = []
        record: dict[str, Any] = {}
        lanes: tuple = ()
        recovery = None
        errors: list[dict[str, str]] = []
        journal = self.run_root / "progress" / f"{run_id}.json"

        def checkpoint(phase):
            atomic_write(
                journal,
                canonical_json_bytes(
                    {
                        "run_id": str(run_id),
                        "phase": phase,
                        "execution_profile": self.profile.value,
                        "lanes": [lane.model_dump(mode="json") for lane in lanes],
                        "record": record,
                        "steps": log,
                        "errors": errors,
                        "source_environment": environment.model_dump(mode="json"),
                        "started_at": started.isoformat(),
                        "target_snapshot": readiness.target_snapshot.model_dump(mode="json"),
                        "scenario_snapshot": self.scenario.snapshot().model_dump(mode="json"),
                        "recovery": recovery,
                        "parent_run_id": str(parent_run_id) if parent_run_id else None,
                    }
                ),
            )

        def step(step_id, phase, lane, action, result):
            log.append(
                {
                    "step_id": step_id,
                    "phase": phase,
                    "lane": lane,
                    "action": action,
                    "ok": not isinstance(result, AdapterResult) or result.ok,
                    "adapter_code": adapter_code(result),
                }
            )

        checkpoint("REGISTERED_BEFORE_WRITES")
        with TargetSubjectLock(self.run_root, readiness.target_id, self.block_subject):
            seeded = seed.seed_lanes(run_id=str(run_id), profile=self.profile)
            if isinstance(seeded, AdapterResult):
                step(self._seed_step, "BASELINE", None, "seed_lanes", seeded)
                checkpoint("SEED_FAILED")
                # The seed transaction rolled back, so nothing was written to clean up.
                raise RuntimeError(f"{self.tag}_SEED_FAILED:{seeded.code}")  # noqa: TRY004 - adapter outcome, not a type error
            lanes = tuple(seeded)
            step(self._seed_step, "BASELINE", None, "seed_lanes", AdapterResult(True, "SPEC009_LANES_SEEDED"))
            record.update(self._initial_record(run_id, lanes))
            checkpoint("SEEDED")
            try:
                self._observe(run_id, lanes, record, step, checkpoint)
            except Exception as exc:  # noqa: BLE001 - keep the first facts and always clean up
                errors.append({"code": type(exc).__name__})
                step("executor-error", "INJECTED", None, "observe", AdapterResult(False, type(exc).__name__))
            finally:
                cleanup_started = time.monotonic()
                try:
                    result = seed.teardown_lanes(run_id=str(run_id), lanes=lanes)
                    data = dict(result.data)
                    # Only an ok teardown that itself reports SUCCEEDED counts as verified cleanup.
                    recovery = {
                        "status": data.get("status", "FAILED") if result.ok else "FAILED",
                        "owned_residue_counts": data.get("owned_residue_counts", {"unknown": 1}),
                        "product_rows_removed": data.get("product_rows_removed"),
                        "seed_digest": data.get("seed_digest"),
                        "adapter_code": result.code,
                    }
                except Exception as exc:  # noqa: BLE001 - preserve unresolved cleanup
                    recovery = {
                        "status": "FAILED",
                        "error_code": type(exc).__name__,
                        "owned_residue_counts": {"unknown": 1},
                    }
                elapsed = time.monotonic() - cleanup_started
                recovery["restore_timing"] = {
                    "environment_restore_seconds": elapsed,
                    "environment_restore_deadline_seconds": RESTORE_DEADLINE_SECONDS,
                    "environment_restore_within_deadline": elapsed <= RESTORE_DEADLINE_SECONDS,
                }
                if elapsed > RESTORE_DEADLINE_SECONDS:
                    recovery["status"] = "FAILED"
                code = recovery.get("adapter_code") or recovery.get("error_code", "FAILED")
                step(
                    "cleanup-owned-subjects",
                    "RECOVERED",
                    None,
                    "teardown_lanes",
                    AdapterResult(recovery["status"] == "SUCCEEDED", code),
                )
                checkpoint("CLEANUP_FINISHED")
        assertions = self._assertions(record, recovery)
        clean = self.judge.cleanup_verified(recovery)
        verdict = self.judge.verdict_for(assertions, recovery)
        judgement = Judgement(
            run_id=run_id,
            scenario_id=self.scenario.scenario_id,
            verdict=verdict,
            reason_code="INSUFFICIENT_EVIDENCE" if verdict == "INCONCLUSIVE" else None,
            assertion_results=assertions,
            unverified_scope=self.unverified_scope,
            summary=self._summary(verdict),
            decided_at=utcnow(),
        )
        snapshot = self.scenario.snapshot()
        run = Run(
            run_id=run_id,
            scenario_id=self.scenario.scenario_id,
            scenario_version=self.scenario.version,
            scenario_digest=snapshot.digest,
            target_id=readiness.target_id,
            target_version=readiness.target_snapshot.target_version,
            model_fixture_id=self.settings.model_fixture_id,
            model_fixture_digest=self.settings.model_fixture_digest,
            state="COMPLETED" if clean else "RESTORE_FAILED",
            manual_cleanup_required=not clean,
            started_at=started,
            ended_at=utcnow(),
            execution_profile=self.profile,
            seed_kind=self.seed_kind,
            fault_kind=self.fault_kind,
            environment_kind="LOCAL_EMULATED",
            aws_deployment_status="NOT_RUN",
            environment_snapshot_digest=environment.snapshot_digest,
            parent_run_id=parent_run_id,
            operator_id=operator_id,
            label=label,
            unverified_scope=self.unverified_scope,
        )
        if not clean:
            blocks.block(readiness.target_id, self.block_subject, run)
        writer = EvidenceBundleWriter(self.run_root, run)
        documents = {
            "run.json": run.model_dump(mode="json"),
            "scenario.snapshot.yaml": snapshot.model_dump(mode="json"),
            "target.snapshot.json": readiness.target_snapshot.model_dump(mode="json"),
            "environment.snapshot.json": environment.model_dump(mode="json"),
            "subjects.json": [lane.model_dump(mode="json") for lane in lanes],
            "recovery.json": recovery,
            "assertions.json": [item.model_dump(mode="json") for item in assertions],
            "judgement.json": judgement.model_dump(mode="json"),
            self.scope_file: scope_document(self.scenario, self.unverified_scope),
            **self._documents(record, lanes, errors),
        }
        if retest_records is not None:
            documents.update(
                {"retest-link.json": retest_records["link"], "retest-diff.json": retest_records["diff"]}
            )
        for name, value in documents.items():
            writer.write_json(name, value, redact_first=False)
        writer.write_bytes(
            "observations.jsonl",
            b"".join(canonical_json_bytes(row) + b"\n" for row in log),
            "application/x-ndjson",
        )
        for name, payload in sorted(self._captures.items()):
            writer.write_bytes(name, payload, "image/png")
        for evidence, files in self._links().items():
            for name in sorted(files):
                writer.link_file_evidence(evidence, name)
        writer.link_intrinsic_evidence("EV9-07", "sealed-manifest")
        writer.seal()
        self.verification = verify_bundle(writer.directory)
        if self.verification["bundle_status"] != "VERIFIED":
            raise RuntimeError(f"{self.tag}_BUNDLE_INVALID:" + ",".join(self.verification["mismatched_files"]))
        return run, judgement, writer.directory

    # ---- subclass hooks --------------------------------------------------------------------------------------

    _seed_step = "seed-lanes"

    def _initial_record(self, run_id, lanes) -> dict[str, Any]:
        raise NotImplementedError

    def _observe(self, run_id, lanes, record, step, checkpoint) -> None:
        raise NotImplementedError

    def _assertions(self, record, recovery):
        raise NotImplementedError

    def _documents(self, record, lanes, errors) -> dict[str, Any]:
        raise NotImplementedError

    def _links(self) -> dict[str, set[str]]:
        return {key: set(value) for key, value in self.links.items()}

    def _summary(self, verdict: str) -> str:
        raise NotImplementedError
