"""H-01 semantic verification in addition to the common SHA/redaction/link scanner."""

import json

from engine.h01_actual import aggregate, cleanup_verified, validate_records
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
    "h01-subjects.json",
    "h01-cases.json",
    "h01-preparation.json",
    "h01-requests.json",
    "h01-model-emissions.json",
    "recovery.json",
    "h01-source.json",
}


def verify_links(directory, evidence, registered, artifacts, result):
    from engine.evidence import _verify_spec002_evidence
    from engine.executors.h01 import LINKS

    _verify_spec002_evidence(directory, evidence, tuple(LINKS), registered, artifacts, result)
    for key, files in LINKS.items():
        if not {f"file:{f}" for f in files}.issubset(evidence.get(key, [])):
            result["mismatched_files"].append(f"evidence:{key}:canonical-files")
    result["checked_evidence_requirements"] = list(LINKS)


def verify_facts(directory, manifest, result):
    from engine.adapters.whyyou.h01_live import FIXTURE_DIGEST, FIXTURE_ID
    from engine.executors.h01 import assertions_for

    try:

        def read(name):
            return json.loads((directory / name).read_text(encoding="utf-8"))

        run = Run.model_validate(read("run.json"))
        from engine.scenario import ScenarioDefinition

        scenario = ScenarioDefinition.model_validate(read("scenario.snapshot.yaml")["definition"])
        if (
            scenario.execution_profile != run.execution_profile
            or scenario.snapshot().digest != run.scenario_digest
        ):
            raise ValueError("scenario contract mismatch")
        rows, recovery = read("h01-cases.json"), read("recovery.json")
        validate_records(run.run_id, rows)
        expected = [a.model_dump(mode="json") for a in assertions_for(rows, recovery)]
        judgement = read("judgement.json")
        if judgement["run_id"] != str(run.run_id) or judgement["scenario_id"] != run.scenario_id:
            raise ValueError("judgement identity mismatch")
        if expected != read("assertions.json") or expected != judgement["assertion_results"]:
            raise ValueError("assessment mismatch")
        clean = cleanup_verified(recovery)
        verdict = aggregate([a["status"] for a in expected]) if clean else "INCONCLUSIVE"
        if judgement["verdict"] != verdict or run.state != (
            "COMPLETED" if clean else "RESTORE_FAILED"
        ):
            raise ValueError("verdict/restore mismatch")
        environment = TargetEnvironmentSnapshot.model_validate(read("environment.snapshot.json"))
        target = read("target.snapshot.json")
        if (
            environment.snapshot_digest != run.environment_snapshot_digest
            or manifest["environment_snapshot_digest"] != environment.snapshot_digest
            or environment.controlproof_commit.dirty
            or environment.whyyou_commit.dirty
            or environment.whyyou_commit.commit_sha != target["git_commit_sha"]
            or run.model_fixture_id != FIXTURE_ID
            or run.model_fixture_digest != FIXTURE_DIGEST
            or environment.model_fixture_id != FIXTURE_ID
            or environment.model_fixture_digest != FIXTURE_DIGEST
        ):
            raise ValueError("environment/source/fixture mismatch")
        if read("subjects.json") != [r["subject"] for r in rows]:
            raise ValueError("subject mismatch")
        if read("h01-subjects.json") != [
            {"path": r["path"], "subject": r["subject"]} for r in rows
        ]:
            raise ValueError("path subject mismatch")
        emissions = [m for r in rows for m in r["model_receipts"]]
        if emissions != read("h01-model-emissions.json"):
            raise ValueError("model receipt mismatch")
        for item in emissions:
            if item.get("fixture_id") != FIXTURE_ID or item.get("fixture_digest") != FIXTURE_DIGEST:
                raise ValueError("model fixture receipt mismatch")
        requests = [
            {
                **r["attempt"],
                "path": r["path"],
                "case": r["subject"]["case"],
                "request_id": r["subject"]["request_id"],
                "identity_proven": r["identity_proven"],
            }
            for r in rows
        ]
        if requests != read("h01-requests.json"):
            raise ValueError("request mismatch")
        if verdict == "PASS":
            preparations = read("h01-preparation.json")
            if not isinstance(preparations, list):
                raise ValueError("Full PASS requires real preparation receipts")
            for row in rows:
                selected = [
                    p
                    for p in preparations
                    if p.get("path") == row["path"] and p.get("case") == row["subject"]["case"]
                ]
                ready = [
                    p
                    for p in selected
                    if p.get("report_id") == row["before"]["report_id"]
                    and p.get("report_status") == "ready"
                    and p.get("consent_committed") is True
                    and p.get("report_requested") is True
                    and p.get("stable_observations", 0) >= 3
                ]
                fixture = [p["fixture_completion"] for p in selected if p.get("fixture_completion")]
                if (
                    len(ready) != 1
                    or len(fixture) != 1
                    or fixture[0].get("run_id") != row["subject"]["run_id"]
                    or fixture[0].get("invitation_id") != row["subject"]["invitation_id"]
                    or [t.get("to") for t in fixture[0].get("transitions", [])]
                    != ["materials_submitted", "analyzing", "ready", "interviewing", "completed"]
                ):
                    raise ValueError("Missing owned normal-report/fixture preparation evidence")
    except (OSError, ValueError, TypeError, KeyError):
        result["mismatched_files"].append("h01-cases.json:semantic-evidence")
