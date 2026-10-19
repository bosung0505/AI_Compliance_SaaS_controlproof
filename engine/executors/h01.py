"""H-01 official actual execution and sealed, independently verifiable evidence."""

import json
import os
import subprocess
import time
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, text

from engine.adapters.whyyou.h01_live import FIXTURE_DIGEST, FIXTURE_ID, H01Live
from engine.evidence import EvidenceBundleWriter, verify_bundle
from engine.h01 import H01Case
from engine.h01_actual import aggregate, assess_record, cleanup_verified, validate_records
from engine.lifecycle import RestoreBlockStore, TargetSubjectLock, atomic_write
from engine.models import (
    AssertionResult,
    ExecutionProfile,
    Judgement,
    ReadinessCheck,
    Run,
    ScenarioReadiness,
    canonical_json_bytes,
    utcnow,
)

PROFILE = ExecutionProfile.H01_HUMAN_DECISION_V1
LINKS = {
    "EV6-01": {
        "environment.snapshot.json",
        "target.snapshot.json",
        "scenario.snapshot.yaml",
        "h01-subjects.json",
    },
    "EV6-02": {"h01-preparation.json", "h01-cases.json"},
    "EV6-03": {"h01-requests.json", "h01-cases.json"},
    "EV6-04": {"h01-model-emissions.json", "h01-cases.json"},
    "EV6-05": {"h01-cases.json", "assertions.json", "judgement.json"},
    "EV6-06": {"recovery.json", "h01-source.json"},
}


def assertions_for(rows, recovery):
    results = []
    for index, case in enumerate(H01Case, 1):
        selected = [r for r in rows if r["subject"]["case"] == case]
        assessed = [assess_record(row) for row in selected]
        status = aggregate([a[0] for a in assessed])
        results.append(
            AssertionResult(
                assertion_id=f"H01-A{index}",
                subject_ref=case.value,
                status=status,
                expected={"authorized": case == H01Case.COMPANY_CONTROL},
                actual={
                    "paths": [
                        {
                            "path": r["path"],
                            "status": a[0],
                            "observation": a[1],
                            "response": r.get("attempt", {}).get("response"),
                            "http_status": r.get("attempt", {}).get("http_status"),
                            "before": r.get("before"),
                            "after": r.get("after"),
                        }
                        for r, a in zip(selected, assessed, strict=True)
                    ]
                },
                reason_code="INSUFFICIENT_EVIDENCE" if status == "INCONCLUSIVE" else None,
                detail=" ".join(dict.fromkeys(a[1] for a in assessed)),
                source_requirements=("V4-H01",),
            )
        )
    clean = cleanup_verified(recovery)
    results.append(
        AssertionResult(
            assertion_id="H01-A6",
            subject_ref="cleanup",
            status="PASS" if clean else "INCONCLUSIVE",
            expected={"owned_residues": 0},
            actual=recovery,
            reason_code=None if clean else "INSUFFICIENT_EVIDENCE",
            detail="이 실행 소유 DB 데이터의 잔여행이 0건입니다."
            if clean
            else "테스트 데이터 정리를 확인하지 못했습니다.",
            source_requirements=("V4-H01",),
        )
    )
    return tuple(results)


class H01Executor:
    fixture_id = FIXTURE_ID
    fixture_digest = FIXTURE_DIGEST
    capability = "h01.actual.lifecycle"
    def __init__(self, scenario, adapters, run_root, *, clock=None):
        self.scenario, self.adapters, self.run_root = scenario, adapters, Path(run_root)
        self.settings = adapters.spec004_seed.settings

    def preflight(self, target_id):
        target, error = None, None
        try:
            settings = self.settings
            if (
                target_id != "whyyou-local"
                or settings.external_ai_allowed
                or not settings.model_substitute_enabled
                or settings.model_fixture_id != self.fixture_id
                or settings.model_fixture_digest != self.fixture_digest
                or settings.environment_kind != "LOCAL_EMULATED"
                or settings.aws_deployment_status != "NOT_RUN"
            ):
                raise ValueError("H01_ISOLATED_FIXTURE_REQUIRED")
            cp = Path(__file__).resolve().parents[2]
            for repo in (cp, settings.whyyou_repo_path):
                branch = subprocess.check_output(
                    ["git", "-C", str(repo), "branch", "--show-current"], text=True
                ).strip()
                dirty = subprocess.check_output(["git", "-C", str(repo), "status", "--porcelain"])
                if dirty or branch in {"main", "master", ""}:
                    raise ValueError("H01_CLEAN_FEATURE_SOURCES_REQUIRED")
            executable = os.environ.get("CONTROLPROOF_WHYYOU_PYTHON")
            if not executable or not Path(executable).is_file():
                raise ValueError("H01_WHYYOU_PYTHON_REQUIRED")
            target = self.adapters.target.capture_target_snapshot()
            health = self.adapters.target.client.http.get("/internal/controlproof/health").json()
            fixture = health.get("controlproof", health)
            if (
                fixture.get("fixture_id") != self.fixture_id
                or fixture.get("fixture_digest") != self.fixture_digest
                or fixture.get("external_ai_isolated") is not True
            ):
                raise ValueError("H01_LIVE_FIXTURE_UNPROVEN")
            paths = self.adapters.target.client.http.get("/openapi.json").json()["paths"]
            if not all(
                p in paths
                for p in (
                    "/v1/invitations/{invitation_id}/final-decisions",
                    "/v1/positions/{position_id}/invitations/recruiting-stage",
                    "/v1/assistant/answers",
                )
            ):
                raise ValueError("H01_TARGET_PATH_MISSING")
            with create_engine(settings.whyyou_database_url).connect() as connection:
                connection.execute(
                    text("SELECT human_review_id,company_user_id FROM human_reviews LIMIT 0")
                )
                connection.execute(
                    text("SELECT audit_event_id,actor_type,request_id FROM audit_events LIMIT 0")
                )
        except Exception as exc:  # noqa: BLE001 - normalized readiness, never a target verdict
            error = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        ready = error is None
        return ScenarioReadiness(
            scenario_id=self.scenario.scenario_id,
            scenario_version=self.scenario.version,
            target_id=target_id,
            implementation_status="IMPLEMENTED",
            status="READY" if ready else "RUNNER_NOT_READY",
            checks=(
                ReadinessCheck(
                    capability=self.capability,
                    status="READY" if ready else "RUNNER_NOT_READY",
                    detail="H01_PATHS_AND_ISOLATION_READY" if ready else error,
                ),
            ),
            target_snapshot=target,
            target_version=target.target_version if target else None,
            model_fixture_id=self.settings.model_fixture_id,
            model_fixture_digest=self.settings.model_fixture_digest,
            operator_action=None
            if ready
            else "Prepare clean H-01 sources and isolated stack; inspect safe check code.",
        )

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
            raise RuntimeError("H01_NOT_READY")
        run_id, started = run_id or uuid4(), utcnow()
        live = H01Live(self.settings, self.adapters, run_id)
        blocks = RestoreBlockStore(self.run_root)
        if blocks.blocked(readiness.target_id, "h01-human-decision"):
            raise RuntimeError("H01_RESTORE_BLOCKED")
        rows, errors = [], []
        # Capture source before writes, retaining clean source identities.
        environment = self.adapters.environment.capture_environment()
        recovery = None
        journal = self.run_root / "progress" / f"{run_id}.json"

        def checkpoint(phase):
            atomic_write(
                journal,
                canonical_json_bytes(
                    {
                        "run_id": str(run_id),
                        "phase": phase,
                        "planned_cases": [
                            {"path": p, "subject": s.model_dump(mode="json")}
                            for p, s, _ in live.cases
                        ],
                        "rows": rows,
                        "source_environment": environment.model_dump(mode="json"),
                        "started_at": started.isoformat(),
                        "target_snapshot": readiness.target_snapshot.model_dump(mode="json"),
                        "scenario_snapshot": self.scenario.snapshot().model_dump(mode="json"),
                        "preparations": live.preparations,
                        "model_receipts": live.model_receipts,
                        "recovery": recovery,
                        "parent_run_id": str(parent_run_id) if parent_run_id else None,
                    }
                ),
            )

        checkpoint("REGISTERED_BEFORE_WRITES")
        deadline = time.monotonic() + 540
        with TargetSubjectLock(self.run_root, readiness.target_id, "h01-human-decision"):
            try:
                for path, subject, lane in live.cases:
                    row = {
                        "path": path,
                        "subject": subject.model_dump(mode="json"),
                        "prepared": False,
                        "identity_proven": False,
                        "before": None,
                        "after": None,
                        "attempt": {},
                        "model_receipts": [],
                    }
                    rows.append(row)
                    checkpoint("CASE_STARTED")
                    try:
                        if time.monotonic() >= deadline:
                            raise TimeoutError("H01 run deadline")
                        before = live.prepare(path, subject, lane)
                        row.update(
                            prepared=True,
                            before=before.model_dump(mode="json"),
                            identity_proven=live.identity(subject, lane),
                        )
                        row["attempt"] = live.attempt(path, subject, lane, before)
                        row["model_receipts"] = [
                            r
                            for r in live.model_receipts
                            if r["request_id"] == str(subject.request_id)
                        ]
                    except Exception as exc:  # noqa: BLE001 - retain failed step and always clean up
                        row["error_code"] = type(exc).__name__
                        errors.append(
                            {"path": path, "case": subject.case.value, "code": type(exc).__name__}
                        )
                    finally:
                        try:
                            row["after"] = live.observe(subject).model_dump(mode="json")
                        except Exception as exc:  # noqa: BLE001 - missing observation remains inconclusive
                            row["observation_error"] = type(exc).__name__
                        checkpoint("CASE_OBSERVED")
            finally:
                cleanup_started = time.monotonic()
                try:
                    recovery = live.cleanup()
                except Exception as exc:  # noqa: BLE001 - preserve unresolved cleanup
                    recovery = {
                        "status": "FAILED",
                        "error_code": type(exc).__name__,
                        "owned_residue_counts": {"unknown": 1},
                    }
                elapsed = time.monotonic() - cleanup_started
                recovery["restore_timing"] = {
                    "environment_restore_seconds": elapsed,
                    "environment_restore_deadline_seconds": 120,
                    "environment_restore_within_deadline": elapsed <= 120,
                }
                if elapsed > 120:
                    recovery["status"] = "FAILED"
                checkpoint("CLEANUP_FINISHED")
        validate_records(run_id, rows)
        assertions = assertions_for(rows, recovery)
        clean = cleanup_verified(recovery)
        verdict = aggregate([a.status.value for a in assertions]) if clean else "INCONCLUSIVE"
        scope = ("AWS_NOT_RUN", "H02_TOOL_SURFACE_NOT_RUN", "EXTERNAL_MODEL_QUALITY_NOT_TESTED")
        judgement = Judgement(
            run_id=run_id,
            scenario_id="H-01",
            verdict=verdict,
            reason_code="INSUFFICIENT_EVIDENCE" if verdict == "INCONCLUSIVE" else None,
            assertion_results=assertions,
            unverified_scope=scope,
            summary=f"세 결정 경로에서 다섯 주체를 테스트했습니다. 전체 {verdict}.",
            decided_at=utcnow(),
        )
        snapshot = self.scenario.snapshot()
        run = Run(
            run_id=run_id,
            scenario_id="H-01",
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
            execution_profile=PROFILE,
            seed_kind="h01-owned-report-lanes-v1",
            fault_kind="h01-adversarial-decision-requests-v1",
            environment_kind="LOCAL_EMULATED",
            aws_deployment_status="NOT_RUN",
            environment_snapshot_digest=environment.snapshot_digest,
            parent_run_id=parent_run_id,
            operator_id=operator_id,
            label=label,
            unverified_scope=scope,
        )
        if not clean:
            blocks.block(readiness.target_id, "h01-human-decision", run)
        writer = EvidenceBundleWriter(self.run_root, run)
        documents = {
            "run.json": run.model_dump(mode="json"),
            "scenario.snapshot.yaml": snapshot.model_dump(mode="json"),
            "target.snapshot.json": readiness.target_snapshot.model_dump(mode="json"),
            "environment.snapshot.json": environment.model_dump(mode="json"),
            "subjects.json": [r["subject"] for r in rows],
            "h01-subjects.json": [{"path": r["path"], "subject": r["subject"]} for r in rows],
            "h01-cases.json": rows,
            "h01-preparation.json": live.preparations,
            "h01-requests.json": [
                {
                    **r["attempt"],
                    "path": r["path"],
                    "case": r["subject"]["case"],
                    "request_id": r["subject"]["request_id"],
                    "identity_proven": r["identity_proven"],
                }
                for r in rows
            ],
            "h01-model-emissions.json": live.model_receipts,
            "recovery.json": recovery,
            "h01-source.json": {
                "errors": errors,
                "source_commits": {
                    "controlproof": environment.controlproof_commit.model_dump(mode="json"),
                    "whyyou": environment.whyyou_commit.model_dump(mode="json"),
                },
                "parent_run_id": str(parent_run_id) if parent_run_id else None,
            },
            "assertions.json": [a.model_dump(mode="json") for a in assertions],
            "judgement.json": judgement.model_dump(mode="json"),
        }
        if retest_records is not None:
            documents.update(
                {
                    "retest-link.json": retest_records["link"],
                    "retest-diff.json": retest_records["diff"],
                }
            )
        for name, value in documents.items():
            writer.write_json(name, value, redact_first=False)
        writer.write_bytes("observations.jsonl", b"", "application/x-ndjson")
        for evidence, files in LINKS.items():
            for name in sorted(files):
                writer.link_file_evidence(evidence, name)
        writer.seal()
        verified = verify_bundle(writer.directory)
        if verified["bundle_status"] != "VERIFIED":
            raise RuntimeError("H01_BUNDLE_INVALID:" + json.dumps(verified["mismatched_files"]))
        return run, judgement, writer.directory
