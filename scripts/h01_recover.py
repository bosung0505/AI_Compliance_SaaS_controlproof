"""Seal an interrupted H-01 collector from its untouched durable ownership/fact journal.

Never replays requests or edits a sealed Run. Missing preparation details remain explicit.
Only a factual FAIL may be recovered this way; PASS requires a fresh full execution.
"""

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from engine.adapters.whyyou.client import WhyYouClient
from engine.adapters.whyyou.h01_live import H01Live
from engine.config import Settings
from engine.evidence import EvidenceBundleWriter, verify_bundle
from engine.executors.h01 import LINKS, assertions_for
from engine.h01_actual import aggregate, cleanup_verified, validate_records
from engine.models import Judgement, Run, TargetEnvironmentSnapshot, sha256_bytes, utcnow
from engine.retest import prepare_retest
from engine.scenario import load
from seeds.spec004_subjects import lane_rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", required=True, type=Path)
    parser.add_argument("--parent", required=True, type=Path)
    parser.add_argument("--scenario", required=True, type=Path)
    args = parser.parse_args()
    raw = args.journal.read_bytes()
    journal = json.loads(raw)
    run_id = UUID(journal["run_id"])
    if journal["phase"] != "CLEANUP_FINISHED":
        raise ValueError("Recovery requires completed observations and cleanup checkpoint")
    validate_records(run_id, journal["rows"])
    settings = Settings.from_env()
    bundle = settings.run_root / str(run_id)
    if bundle.exists() and any(bundle.iterdir()):
        raise ValueError("Refuse existing/sealed bundle overwrite")
    environment = TargetEnvironmentSnapshot.model_validate(journal["source_environment"])
    target = WhyYouClient(settings).capture_target_snapshot()
    if target.git_commit_sha != environment.whyyou_commit.commit_sha:
        raise ValueError(
            "Target changed before recovery; use original independently verified target snapshot"
        )
    scenario = load(args.scenario)
    live = H01Live(settings, None, run_id)
    for _, subject, lane in live.cases:
        for seed in lane_rows(lane, company_id=subject.company_id, reviewer_id=subject.reviewer_id):
            live.resources.update(
                v
                for v in seed.values.values()
                if isinstance(v, UUID) and v not in {subject.company_id, subject.reviewer_id}
            )
    start = time.monotonic()
    recovery = live.cleanup()
    seconds = time.monotonic() - start
    recovery["restore_timing"] = {
        "environment_restore_seconds": seconds,
        "environment_restore_deadline_seconds": 120,
        "environment_restore_within_deadline": seconds <= 120,
    }
    if not cleanup_verified(recovery) or seconds > 120:
        raise ValueError("Independent recovery cleanup not confirmed")
    rows = journal["rows"]
    assertions = assertions_for(rows, recovery)
    if aggregate([a.status.value for a in assertions]) != "FAIL":
        raise ValueError(
            "Collector recovery can preserve factual FAIL only; fresh Run required for PASS"
        )
    snapshot = scenario.snapshot()
    parent_id = UUID(json.loads((args.parent / "run.json").read_text())["run_id"])
    _, _, retest = prepare_retest(
        args.parent,
        child_run_id=run_id,
        child_target=target,
        child_scenario_version=scenario.version,
        child_scenario_digest=snapshot.digest,
        child_profile=scenario.execution_profile,
        child_environment=environment,
    )
    scope = (
        "AWS_NOT_RUN",
        "H02_TOOL_SURFACE_NOT_RUN",
        "EXTERNAL_MODEL_QUALITY_NOT_TESTED",
        "COLLECTOR_RECOVERY_PREPARATION_DETAILS_MISSING",
    )
    run = Run(
        run_id=run_id,
        scenario_id="H-01",
        scenario_version=scenario.version,
        scenario_digest=snapshot.digest,
        target_id=settings.target_id,
        target_version=target.target_version,
        model_fixture_id=settings.model_fixture_id,
        model_fixture_digest=settings.model_fixture_digest,
        state="COMPLETED",
        started_at=environment.captured_at,
        ended_at=datetime.fromtimestamp(args.journal.stat().st_mtime, UTC),
        execution_profile=scenario.execution_profile,
        environment_kind="LOCAL_EMULATED",
        aws_deployment_status="NOT_RUN",
        environment_snapshot_digest=environment.snapshot_digest,
        parent_run_id=parent_id,
        seed_kind="h01-owned-report-lanes-v1",
        fault_kind="h01-adversarial-decision-requests-v1",
        label="h01-first-factual-failure-collector-recovered",
        unverified_scope=scope,
    )
    judgement = Judgement(
        run_id=run_id,
        scenario_id="H-01",
        verdict="FAIL",
        assertion_results=assertions,
        summary="SYSTEM의 합격·불합격 일괄 이동이 허용됐습니다. AI 생성 경로는 미입증이며 최초 실패를 보존했습니다.",
        unverified_scope=scope,
        decided_at=utcnow(),
    )
    emissions = [m for r in rows for m in r["model_receipts"]]
    documents = {
        "run.json": run.model_dump(mode="json"),
        "scenario.snapshot.yaml": snapshot.model_dump(mode="json"),
        "target.snapshot.json": target.model_dump(mode="json"),
        "environment.snapshot.json": environment.model_dump(mode="json"),
        "subjects.json": [r["subject"] for r in rows],
        "h01-subjects.json": [{"path": r["path"], "subject": r["subject"]} for r in rows],
        "h01-cases.json": rows,
        "h01-preparation.json": {
            "status": "DETAILS_UNAVAILABLE_IN_OLD_JOURNAL",
            "basis": "Original recorded prepared flags and independent ready before-state retained; not a complete preparation receipt set.",
        },
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
        "h01-model-emissions.json": emissions,
        "recovery.json": recovery,
        "h01-source.json": {
            "source_commits": {
                "controlproof": environment.controlproof_commit.model_dump(mode="json"),
                "whyyou": environment.whyyou_commit.model_dump(mode="json"),
            },
            "collector_recovery": {
                "journal_sha256": sha256_bytes(raw),
                "recovery_script_sha256": sha256_bytes(Path(__file__).read_bytes()),
                "reason": "Post-observation serialization duplicate case/request keys; no target request replayed.",
                "time_bounds": "Start is pre-write environment capture; end is durable cleanup checkpoint mtime.",
                "preparation_details": "Unavailable; whole PASS prohibited.",
            },
        },
        "assertions.json": [a.model_dump(mode="json") for a in assertions],
        "judgement.json": judgement.model_dump(mode="json"),
        "h01-journal.json": journal,
        "retest-link.json": retest["link"],
        "retest-diff.json": retest["diff"],
    }
    writer = EvidenceBundleWriter(settings.run_root, run)
    for name, value in documents.items():
        writer.write_json(name, value, redact_first=False)
    writer.write_bytes("observations.jsonl", b"", "application/x-ndjson")
    for evidence, files in LINKS.items():
        for name in sorted(files):
            writer.link_file_evidence(evidence, name)
    writer.link_file_evidence("EV6-06", "h01-journal.json")
    writer.seal()
    verified = verify_bundle(bundle)
    print(json.dumps({"run_id": str(run_id), "verdict": "FAIL", **verified}))


if __name__ == "__main__":
    main()
