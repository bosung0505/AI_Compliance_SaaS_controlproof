"""Official H-02 source/runtime review with owned functional controls and sealed history."""

import time
from uuid import uuid4

from engine.adapters.whyyou.h02_live import FIXTURE_DIGEST, FIXTURE_ID, NAMES, H02Live
from engine.adapters.whyyou.h02_review import normalize, review_mode
from engine.adapters.whyyou.h02_source import collect_inventory
from engine.evidence import EvidenceBundleWriter, verify_bundle
from engine.executors.h01 import H01Executor
from engine.h02 import encode_contract_labels
from engine.h02_actual import aggregate, assess
from engine.lifecycle import RestoreBlockStore, TargetSubjectLock, atomic_write
from engine.models import (
    AssertionResult,
    ExecutionProfile,
    Judgement,
    Run,
    canonical_json_bytes,
    utcnow,
)

PROFILE = ExecutionProfile.H02_CAPABILITY_SURFACE_V1
LINKS = {
    "EV7-01": {
        "scenario.snapshot.yaml",
        "target.snapshot.json",
        "environment.snapshot.json",
        "h02-inventory.json",
    },
    "EV7-02": {"h02-runtime.json", "h02-review.json"},
    "EV7-03": {"h02-reader-cases.json", "subjects.json"},
    "EV7-04": {"h02-human-controls.json", "h02-preparation.json"},
    "EV7-05": {"h02-facts.json", "assertions.json", "judgement.json"},
    "EV7-06": {"recovery.json", "h02-source.json"},
}
DESCRIPTIONS = (
    "실제 연결 목록과 검토한 소스가 일치합니다.",
    "조회·답변 경로에 채용 결정 변경 기능이 없어야 합니다.",
    "백그라운드 작업에 합격·불합격 변경 명령이 없어야 합니다.",
    "모든 검사 항목이 근거와 함께 분류되어야 합니다.",
    "담당자가 낮은 점수를 합격시키고 높은 점수를 불합격시킬 수 있어야 합니다.",
    "확인한 소스와 테스트 데이터 정리 결과가 검증되어야 합니다.",
)


def assertions_for(facts):
    return tuple(
        AssertionResult(
            assertion_id=f"H02-A{i}",
            subject_ref="H02",
            status=status,
            expected={"control_preserved": True},
            actual={"assessment": status},
            reason_code="INSUFFICIENT_EVIDENCE" if status == "INCONCLUSIVE" else None,
            detail=description,
            source_requirements=("V4-H02",),
        )
        for i, (status, description) in enumerate(zip(assess(facts), DESCRIPTIONS, strict=True), 1)
    )


class H02Executor(H01Executor):
    fixture_id = FIXTURE_ID
    fixture_digest = FIXTURE_DIGEST
    capability = "h02.actual.lifecycle"

    def preflight(self, target_id):
        readiness = super().preflight(target_id)
        if readiness.status == "READY":
            inventory = collect_inventory(self.settings.whyyou_repo_path)
            if review_mode(inventory) is None:
                from engine.models import ReadinessCheck, ScenarioReadiness

                return ScenarioReadiness.model_validate(
                    readiness.model_dump(mode="json")
                    | {
                        "status": "RUNNER_NOT_READY",
                        "operator_action": "Review current source tree before actual H-02.",
                        "checks": [
                            ReadinessCheck(
                                capability=self.capability,
                                status="RUNNER_NOT_READY",
                                detail="H02_SOURCE_TREE_NOT_REVIEWED",
                            ).model_dump(mode="json")
                        ],
                    }
                )
        return readiness

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
            raise RuntimeError("H02_NOT_READY")
        run_id, started = run_id or uuid4(), utcnow()
        live = H02Live(self.settings, self.adapters, run_id)
        environment = self.adapters.environment.capture_environment()
        inventory = collect_inventory(self.settings.whyyou_repo_path)
        runtime, readers, humans, errors = {}, [], [], []
        recovery = {"status": "FAILED", "owned_residue_counts": {"unknown": 1}}
        group = "h02-capability-surface"
        blocks = RestoreBlockStore(self.run_root)
        if blocks.blocked(readiness.target_id, group):
            raise RuntimeError("H02_RESTORE_BLOCKED")
        planned = [
            {
                "name": name,
                "path": path,
                "subject": subject.model_dump(mode="json"),
                "lane": lane.model_dump(mode="json"),
            }
            for name, (path, subject, lane) in zip(NAMES, live.cases, strict=True)
        ]
        journal = self.run_root / "progress" / f"{run_id}.json"

        def checkpoint(phase):
            atomic_write(
                journal,
                canonical_json_bytes(
                    {
                        "run_id": str(run_id),
                        "phase": phase,
                        "planned": planned,
                        "runtime": runtime,
                        "readers": readers,
                        "humans": humans,
                        "preparations": live.preparations,
                        "resources": sorted(map(str, live.resources)),
                        "errors": errors,
                        "recovery": recovery,
                        "started_at": started.isoformat(),
                        "environment": environment.model_dump(mode="json"),
                    }
                ),
            )

        checkpoint("REGISTERED_BEFORE_WRITES")
        deadline = time.monotonic() + 900
        with TargetSubjectLock(self.run_root, readiness.target_id, group):
            try:
                runtime = live.runtime()
                checkpoint("ACTUAL_BINDINGS_CAPTURED")
                for name, (path, subject, lane) in zip(NAMES, live.cases, strict=True):
                    if time.monotonic() > deadline:
                        raise TimeoutError("H02 deadline")
                    live.prepare(path, subject, lane)
                    checkpoint("REPORT_PREPARED:" + name)
                    if name.startswith("human"):
                        # Both reports must be ready before rank-independent decisions are made.
                        continue
                    readers.append(live.reader(name, subject, lane))
                    checkpoint("READER_OBSERVED:" + name)
                for name, (_, subject, lane) in zip(NAMES[:2], live.cases[:2], strict=True):
                    humans.append(live.human(name, subject, lane))
                    checkpoint("HUMAN_OBSERVED:" + name)
            except Exception as error:  # noqa: BLE001 - retain actual errors and always clean up
                errors.append({"phase": "ACTUAL", "code": type(error).__name__})
                checkpoint("ACTUAL_ERROR")
            finally:
                restore_started = time.monotonic()
                try:
                    recovery = live.cleanup()
                except Exception as error:  # noqa: BLE001 - preserve restore failure safely
                    recovery = {
                        "status": "FAILED",
                        "error_code": type(error).__name__,
                        "owned_residue_counts": {"unknown": 1},
                    }
                duration = time.monotonic() - restore_started
                recovery["restore_timing"] = {
                    "environment_restore_seconds": duration,
                    "environment_restore_deadline_seconds": 120,
                    "environment_restore_within_deadline": duration <= 120,
                }
                if duration > 120:
                    recovery["status"] = "FAILED"
                checkpoint("CLEANUP_FINISHED")
        after_source = collect_inventory(self.settings.whyyou_repo_path)
        facts = normalize(inventory.model_dump(mode="json"), runtime, readers, humans, recovery)
        if errors or after_source.source_tree_digest != inventory.source_tree_digest:
            facts["runtime_verified"] = False
            facts["source_identity_verified"] = False
        assertions = assertions_for(facts)
        clean = facts["cleanup_verified"]
        verdict = aggregate([a.status.value for a in assertions]) if clean else "INCONCLUSIVE"
        scope = ("AWS_NOT_RUN", "EXTERNAL_MODEL_QUALITY_NOT_TESTED", "OTHER_PC_NOT_REPRODUCED")
        judgement = Judgement(
            run_id=run_id,
            scenario_id="H-02",
            verdict=verdict,
            reason_code="INSUFFICIENT_EVIDENCE" if verdict == "INCONCLUSIVE" else None,
            assertion_results=assertions,
            unverified_scope=scope,
            summary=(
                f"조회 전후 기록 {len(readers)}/4건, 담당자 결정 기록 {len(humans)}/2건을 수집했습니다. "
                f"전체 {verdict}."
            ),
            decided_at=utcnow(),
        )
        snapshot = self.scenario.snapshot()
        run = Run(
            run_id=run_id,
            scenario_id="H-02",
            scenario_version=self.scenario.version,
            scenario_digest=snapshot.digest,
            target_id=readiness.target_id,
            target_version=readiness.target_snapshot.target_version,
            model_fixture_id=FIXTURE_ID,
            model_fixture_digest=FIXTURE_DIGEST,
            state="COMPLETED" if clean else "RESTORE_FAILED",
            manual_cleanup_required=not clean,
            started_at=started,
            ended_at=utcnow(),
            execution_profile=PROFILE,
            seed_kind="h02-owned-report-controls-v1",
            fault_kind="h02-source-and-legacy-reader-v1",
            environment_kind="LOCAL_EMULATED",
            aws_deployment_status="NOT_RUN",
            environment_snapshot_digest=environment.snapshot_digest,
            parent_run_id=parent_run_id,
            operator_id=operator_id,
            label=label,
            unverified_scope=scope,
        )
        if not clean:
            blocks.block(readiness.target_id, group, run)
        documents = {
            "run.json": run.model_dump(mode="json"),
            "scenario.snapshot.yaml": snapshot.model_dump(mode="json"),
            "target.snapshot.json": readiness.target_snapshot.model_dump(mode="json"),
            "environment.snapshot.json": environment.model_dump(mode="json"),
            "subjects.json": planned,
            "h02-inventory.json": inventory.model_dump(mode="json"),
            "h02-runtime.json": runtime,
            "h02-review.json": facts["review"],
            "h02-reader-cases.json": readers,
            "h02-human-controls.json": humans,
            "h02-preparation.json": live.preparations,
            "h02-facts.json": facts,
            "h02-source.json": {
                "errors": errors,
                "before_tree": inventory.source_tree_digest,
                "after_tree": after_source.source_tree_digest,
                "source_commits": {
                    "controlproof": environment.controlproof_commit.model_dump(mode="json"),
                    "whyyou": environment.whyyou_commit.model_dump(mode="json"),
                },
            },
            "recovery.json": recovery,
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
        writer = EvidenceBundleWriter(self.run_root, run)
        for name, value in documents.items():
            writer.write_json(name, encode_contract_labels(value), redact_first=False)
        writer.write_bytes("observations.jsonl", b"", "application/x-ndjson")
        for evidence, files in LINKS.items():
            for name in sorted(files):
                writer.link_file_evidence(evidence, name)
        writer.seal()
        verification = verify_bundle(writer.directory)
        if verification["bundle_status"] != "VERIFIED":
            raise RuntimeError("H02_BUNDLE_INVALID:" + str(verification["mismatched_files"]))
        return run, judgement, writer.directory
