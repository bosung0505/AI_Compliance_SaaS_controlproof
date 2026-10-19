"""Independent H-02 source/runtime/observation reconciliation and judgment recomputation."""

import json
from datetime import datetime
from types import SimpleNamespace
from uuid import UUID

from engine.adapters.whyyou.h02_live import FIXTURE_DIGEST, FIXTURE_ID, NAMES, h02_cases
from engine.adapters.whyyou.h02_review import normalize
from engine.h02 import Inventory, decode_contract_labels
from engine.h02_actual import aggregate
from engine.models import Run, TargetEnvironmentSnapshot

REQUIRED_FILES = {
    "run.json",
    "scenario.snapshot.yaml",
    "target.snapshot.json",
    "environment.snapshot.json",
    "subjects.json",
    "observations.jsonl",
    "assertions.json",
    "judgement.json",
    "recovery.json",
    "h02-inventory.json",
    "h02-runtime.json",
    "h02-review.json",
    "h02-reader-cases.json",
    "h02-human-controls.json",
    "h02-preparation.json",
    "h02-facts.json",
    "h02-source.json",
}


def verify_links(directory, evidence, registered, artifacts, result):
    from engine.evidence import _verify_spec002_evidence
    from engine.executors.h02 import LINKS

    _verify_spec002_evidence(directory, evidence, tuple(LINKS), registered, artifacts, result)
    for key, files in LINKS.items():
        if not {f"file:{name}" for name in files} <= set(evidence.get(key, [])):
            result["mismatched_files"].append(f"evidence:{key}:canonical-files")
    result["checked_evidence_requirements"] = list(LINKS)


def verify_facts(directory, manifest, result):
    from engine.executors.h02 import assertions_for
    from engine.scenario import ScenarioDefinition

    def read(name):
        return decode_contract_labels(json.loads((directory / name).read_text(encoding="utf-8")))

    try:
        run = Run.model_validate(read("run.json"))
        scenario = ScenarioDefinition.model_validate(read("scenario.snapshot.yaml")["definition"])
        environment = TargetEnvironmentSnapshot.model_validate(read("environment.snapshot.json"))
        target = read("target.snapshot.json")
        inventory = Inventory.model_validate(read("h02-inventory.json"))
        if (
            run.scenario_id != "H-02"
            or scenario.execution_profile != run.execution_profile
            or scenario.snapshot().digest != run.scenario_digest
            or run.environment_snapshot_digest != environment.snapshot_digest
            or manifest["environment_snapshot_digest"] != environment.snapshot_digest
            or environment.controlproof_commit.dirty
            or environment.whyyou_commit.dirty
            or inventory.source_dirty is not False
            or inventory.source_head != environment.whyyou_commit.commit_sha
            or inventory.source_head != target["git_commit_sha"]
            or run.model_fixture_id != FIXTURE_ID
            or run.model_fixture_digest != FIXTURE_DIGEST
            or environment.model_fixture_id != FIXTURE_ID
            or environment.model_fixture_digest != FIXTURE_DIGEST
        ):
            raise ValueError("source/environment/profile mismatch")
        readers, humans = read("h02-reader-cases.json"), read("h02-human-controls.json")
        subjects = read("subjects.json")
        if len(subjects) != 6 or [s["name"] for s in subjects] != list(NAMES):
            raise ValueError("canonical subject coverage mismatch")
        first = subjects[0]["subject"]
        settings = SimpleNamespace(
            whyyou_company_id=first["company_id"], whyyou_company_user_id=first["reviewer_id"]
        )
        for entry, (path, subject, lane) in zip(
            subjects, h02_cases(run.run_id, settings), strict=True
        ):
            if entry != {
                "name": entry["name"],
                "path": path,
                "subject": subject.model_dump(mode="json"),
                "lane": lane.model_dump(mode="json"),
            }:
                raise ValueError("foreign planned subject")
        by_name = {s["name"]: s for s in subjects}
        if len({r["name"] for r in readers + humans}) != len(readers + humans):
            raise ValueError("duplicate observations")
        for row in readers + humans:
            entry = by_name[row["name"]]
            if row["subject"] != entry["subject"]:
                raise ValueError("foreign observation")
            for state in (row["before"], row["after"]):
                if (
                    state["company_id"] != entry["subject"]["company_id"]
                    or state["invitation_id"] != entry["subject"]["invitation_id"]
                    or state["position_id"] != entry["lane"]["position_id"]
                    or state["competency_model_version_id"]
                    != entry["lane"]["competency_model_version_id"]
                    or type(state["pipeline_row_version"]) is not int
                    or state["pipeline_row_version"] < 1
                    or type(state["reviews"]) is not int
                    or state["reviews"] < 0
                    or state["report_status"] != "ready"
                ):
                    raise ValueError("invalid owned state")
                UUID(state["report_id"])
            if row["name"].startswith("human"):
                for receipt in row.get("model_receipts", []):
                    emitted = datetime.fromisoformat(receipt["emitted_at"])
                    if not run.started_at <= emitted <= run.ended_at:
                        raise ValueError("model receipt outside execution")
                    if receipt.get("criterion_id") not in {
                        c["criterion_id"] for c in entry["lane"]["criteria"]
                    }:
                        raise ValueError("foreign model criterion")
                if row["before"]["overall_score"] != (35 if row["name"] == "human_low" else 90):
                    raise ValueError("unexpected fixed score")
                if row["after"]["recruiting_stage_id"] != entry["subject"]["target_stage_id"]:
                    raise ValueError("foreign final stage")
            elif row["name"].endswith("legacy") and (
                row["before"]["recruiting_stage_id"] is not None
                or row.get("synthetic_legacy_precondition") is not True
            ):
                raise ValueError("legacy input mismatch")
        source, recovery = read("h02-source.json"), read("recovery.json")
        if source["before_tree"] != inventory.source_tree_digest:
            raise ValueError("source manifest mismatch")
        facts = normalize(
            read("h02-inventory.json"), read("h02-runtime.json"), readers, humans, recovery
        )
        if source["errors"] or source["after_tree"] != source["before_tree"]:
            facts["runtime_verified"] = False
            facts["source_identity_verified"] = False
        if facts != read("h02-facts.json") or facts["review"] != read("h02-review.json"):
            raise ValueError("review/raw fact mismatch")
        assertions = [a.model_dump(mode="json") for a in assertions_for(facts)]
        judgement = read("judgement.json")
        verdict = (
            aggregate([a["status"] for a in assertions])
            if facts["cleanup_verified"]
            else "INCONCLUSIVE"
        )
        if (
            assertions != read("assertions.json")
            or assertions != judgement["assertion_results"]
            or judgement["verdict"] != verdict
            or judgement["run_id"] != str(run.run_id)
            or judgement["scenario_id"] != "H-02"
            or run.state != ("COMPLETED" if facts["cleanup_verified"] else "RESTORE_FAILED")
        ):
            raise ValueError("assertion/verdict/restore mismatch")
        if verdict == "PASS":
            preparations = read("h02-preparation.json")
            if len(readers) != 4 or len(humans) != 2 or len(preparations) != 12:
                raise ValueError("missing actual preparation")
            for entry in subjects:
                subject, path = entry["subject"], entry["path"]
                selected = [
                    p
                    for p in preparations
                    if p.get("path") == path and p.get("case") == subject["case"]
                ]
                completions = [
                    p["fixture_completion"] for p in selected if "fixture_completion" in p
                ]
                ready = [p for p in selected if p.get("report_status") == "ready"]
                if len(completions) != 1 or len(ready) != 1:
                    raise ValueError("missing unique report prerequisite")
                completion = completions[0]
                if (
                    completion["run_id"] != subject["run_id"]
                    or completion["invitation_id"] != subject["invitation_id"]
                    or completion.get("synthetic_completed_interview") is not True
                    or [t["to"] for t in completion["transitions"]]
                    != ["materials_submitted", "analyzing", "ready", "interviewing", "completed"]
                    or ready[0].get("consent_committed") is not True
                    or ready[0].get("report_requested") is not True
                    or ready[0].get("stable_observations", 0) < 3
                ):
                    raise ValueError("unproven normal report preparation")
        result["checked_profile_facts"] = [
            "H02-source-runtime-coverage",
            "H02-review-and-observations",
            "H02-human-rank-control",
            "H02-restoration",
        ]
    except Exception:  # noqa: BLE001 - malformed evidence fails without echoing payloads
        result["mismatched_files"].append("h02:semantic-facts")
