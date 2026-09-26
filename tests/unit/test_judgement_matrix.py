from __future__ import annotations

import json

import pytest

from engine.judge import judge_h03
from engine.models import EvidenceArtifact, Observation, Run, Verdict
from engine.runner import RunOrchestrator
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters


@pytest.mark.parametrize(
    "options,verdict",
    [
        ({}, Verdict.PASS),
        ({"status_class": "queued_only"}, Verdict.FAIL),
        ({"effect": False}, Verdict.INCONCLUSIVE),
        ({"restore": False}, Verdict.INCONCLUSIVE),
    ],
)
def test_primary_judgement_matrix(tmp_path, options, verdict):
    adapters, _ = make_adapters(**options)
    runner = RunOrchestrator(load("scenarios/H-03.yaml"), adapters, tmp_path, clock=FakeClock())
    _, judgement, _ = runner.execute(runner.preflight("whyyou-local"))
    assert judgement.verdict is verdict


def test_direct_fail_outranks_unrelated_missing_evidence(tmp_path):
    run, observations, artifacts = _loaded_case(tmp_path, status_class="queued_only")
    without_ev09 = [
        artifact for artifact in artifacts if "EV-09" not in artifact.evidence_requirement_ids
    ]
    judgement = judge_h03(run, observations, without_ev09)
    assert judgement.verdict is Verdict.FAIL
    assert "EV-09" in judgement.missing_evidence


def test_same_dimension_conflict_forces_inconclusive(tmp_path):
    run, observations, artifacts = _loaded_case(tmp_path)
    original = next(row for row in observations if row.key == "report.ui.status_class")
    conflicting = original.model_copy(update={"value": "ready"})
    judgement = judge_h03(run, [*observations, conflicting], artifacts)
    assert judgement.verdict is Verdict.INCONCLUSIVE
    assert judgement.reason_code.value == "EVIDENCE_CONFLICT"


def _loaded_case(tmp_path, **options):
    adapters, _ = make_adapters(**options)
    runner = RunOrchestrator(load("scenarios/H-03.yaml"), adapters, tmp_path, clock=FakeClock())
    _, _, bundle = runner.execute(runner.preflight("whyyou-local"))
    run = Run.model_validate(json.loads((bundle / "run.json").read_text(encoding="utf-8")))
    observations = [
        Observation.model_validate(json.loads(line))
        for line in (bundle / "observations.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    records = {item.get("artifact_id"): item for item in manifest["files"]}
    artifacts = []
    for path in (bundle / "artifacts").glob("*.json"):
        envelope = json.loads(path.read_text(encoding="utf-8"))
        record = records[envelope["artifact_id"]]
        artifacts.append(
            EvidenceArtifact(
                artifact_id=envelope["artifact_id"],
                run_id=envelope["run_id"],
                subject_ref=envelope["subject_ref"],
                phase=envelope["phase"],
                step_id=envelope["step_id"],
                attempt=envelope["attempt"],
                evidence_requirement_ids=tuple(envelope["evidence_requirement_ids"]),
                artifact_type=envelope["artifact_type"],
                relative_path=record["path"],
                source_locator=envelope["source_locator"],
                captured_at=envelope["captured_at"],
                mime_type=record["mime_type"],
                size_bytes=record["size_bytes"],
                sha256=record["sha256"],
            )
        )
    return run, observations, artifacts
