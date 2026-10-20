"""Semantic checks shared by the N-01/N-03 bundle profiles (contracts/evidence-bundle-v9.md `verify_facts`)."""

from __future__ import annotations

import json
from typing import Any

from engine.models import Run, Spec009SubjectLane, TargetEnvironmentSnapshot


class SemanticMismatch(ValueError):
    """Names the sealed file whose facts do not agree; reported as `<file>:semantic-evidence`."""

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.name = name


def reader(directory):
    def read(name: str) -> Any:
        return json.loads((directory / name).read_text(encoding="utf-8"))

    return read


def verify_links(directory, evidence, registered, artifacts, result, links) -> None:
    from engine.evidence import _verify_spec002_evidence

    _verify_spec002_evidence(directory, evidence, tuple(links), registered, artifacts, result)
    for key, files in links.items():
        if not {f"file:{name}" for name in files}.issubset(evidence.get(key, [])):
            result["mismatched_files"].append(f"evidence:{key}:canonical-files")
    result["checked_evidence_requirements"] = list(links)


def verify_common(
    directory, manifest, *, profile, judge, unverified_scope, scope_file, lane_ids, rebuild
) -> dict[str, Any]:
    """Run/scenario/environment/fixture identity, subjects, scope and the re-judged verdict.

    ``rebuild(read, recovery)`` returns the assertions recomputed from the sealed observation files with
    ``judge`` (engine.n01 or engine.n03), whose ``cleanup_verified``/``verdict_for`` decide the verdict.
    """
    from engine.executors.spec009 import FIXTURE_DIGEST, FIXTURE_ID, scope_document
    from engine.scenario import ScenarioDefinition

    read = reader(directory)
    run = Run.model_validate(read("run.json"))
    scenario = ScenarioDefinition.model_validate(read("scenario.snapshot.yaml")["definition"])
    if (
        run.execution_profile is not profile
        or scenario.execution_profile is not profile
        or scenario.snapshot().digest != run.scenario_digest
    ):
        raise SemanticMismatch("scenario.snapshot.yaml")
    environment = TargetEnvironmentSnapshot.model_validate(read("environment.snapshot.json"))
    target = read("target.snapshot.json")
    if (
        environment.snapshot_digest != run.environment_snapshot_digest
        or manifest.get("environment_snapshot_digest") != environment.snapshot_digest
        or environment.controlproof_commit.dirty
        or environment.whyyou_commit.dirty
        or environment.whyyou_commit.commit_sha != target["git_commit_sha"]
        or (run.model_fixture_id, run.model_fixture_digest) != (FIXTURE_ID, FIXTURE_DIGEST)
        or (environment.model_fixture_id, environment.model_fixture_digest) != (FIXTURE_ID, FIXTURE_DIGEST)
    ):
        raise SemanticMismatch("environment.snapshot.json")
    subjects = [Spec009SubjectLane.model_validate(row) for row in read("subjects.json")]
    if [lane.lane_id.value for lane in subjects] != list(lane_ids) or any(
        lane.run_id != run.run_id for lane in subjects
    ):
        raise SemanticMismatch("subjects.json")
    if read(scope_file) != scope_document(scenario, unverified_scope):
        raise SemanticMismatch(scope_file)
    recovery = read("recovery.json")
    expected = rebuild(read, recovery)
    rows = [item.model_dump(mode="json") for item in expected]
    judgement = read("judgement.json")
    if rows != read("assertions.json") or rows != judgement["assertion_results"]:
        raise SemanticMismatch("assertions.json")
    clean = judge.cleanup_verified(recovery)
    if (
        judgement["run_id"] != str(run.run_id)
        or judgement["scenario_id"] != run.scenario_id
        or judgement["verdict"] != judge.verdict_for(expected, recovery)
        or run.state.value != ("COMPLETED" if clean else "RESTORE_FAILED")
        or run.manual_cleanup_required is clean
    ):
        raise SemanticMismatch("recovery.json")
    if tuple(judgement["unverified_scope"]) != unverified_scope or run.unverified_scope != unverified_scope:
        raise SemanticMismatch("judgement.json")
    return {"read": read, "run": run, "subjects": subjects}
