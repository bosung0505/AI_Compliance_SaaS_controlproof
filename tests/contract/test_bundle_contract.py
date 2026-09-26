from pathlib import Path

import pytest

from engine.evidence import EvidenceBundleWriter, verify_bundle
from engine.models import Phase
from engine.scenario import load


def complete_bundle(tmp_path: Path, run, target_snapshot):
    scenario = load("scenarios/H-03.yaml").snapshot()
    writer = EvidenceBundleWriter(tmp_path, run)
    writer.write_json("run.json", run.model_dump(mode="json"), redact_first=False)
    writer.write_json(
        "scenario.snapshot.yaml", scenario.model_dump(mode="json"), redact_first=False
    )
    writer.write_json(
        "target.snapshot.json", target_snapshot.model_dump(mode="json"), redact_first=False
    )
    writer.write_json("subjects.json", [])
    writer.write_bytes("faults.jsonl", b"", "application/x-ndjson")
    writer.write_bytes("observations.jsonl", b"", "application/x-ndjson")
    writer.write_json("assertions.json", [])
    writer.write_json("judgement.json", {"verdict": "INCONCLUSIVE"})
    requirements = {
        "EV-01": ("STATE_SNAPSHOT",),
        "EV-02": ("FAULT_RECEIPT",),
        "EV-03": ("FAULT_RECEIPT", "HTTP_EXCHANGE"),
        "EV-04": ("SCREENSHOT", "BROWSER_PROJECTION"),
        "EV-05": ("HTTP_EXCHANGE",),
        "EV-06": ("STATE_SNAPSHOT",),
        "EV-07": ("STATE_SNAPSHOT",),
        "EV-08": ("FAULT_RECEIPT", "STATE_SNAPSHOT"),
        "EV-09": ("VERSION_SNAPSHOT",),
    }
    for evidence_id, artifact_types in requirements.items():
        for artifact_type in artifact_types:
            writer.collect_json_artifact(
                subject_ref="candidate-01",
                phase=Phase.BASELINE,
                step_id="fixture",
                attempt=1,
                evidence_requirement_ids=(evidence_id,),
                artifact_type=artifact_type,
                source_locator={"fixture": True},
                content={"evidence_id": evidence_id, "artifact_type": artifact_type},
            )
    writer.seal()
    return writer


def test_paths_redaction_hash_and_seal(tmp_path, run_factory, target_snapshot):
    scenario = load("scenarios/H-03.yaml").snapshot()
    run = run_factory(
        scenario_digest=scenario.digest,
        target_version=target_snapshot.target_version,
    )
    writer = complete_bundle(tmp_path, run, target_snapshot)
    result = verify_bundle(writer.directory)
    assert result["bundle_status"] == "VERIFIED"
    with pytest.raises(PermissionError):
        writer.write_json("after-seal.json", {})


def test_root_escape_is_rejected(tmp_path, run_factory):
    writer = EvidenceBundleWriter(tmp_path, run_factory())
    with pytest.raises(ValueError, match="escapes"):
        writer.write_json("../outside.json", {})


def test_redaction_happens_before_persist(tmp_path, run_factory):
    writer = EvidenceBundleWriter(tmp_path, run_factory())
    path = writer.write_json(
        "safe.json",
        {
            "Authorization": "Bearer secret-value",
            "email": "real.person@example.com",
            "phone": "010-1234-5678",
        },
    )
    text = path.read_text(encoding="utf-8")
    assert "secret-value" not in text
    assert "real.person@example.com" not in text
    assert "010-1234-5678" not in text


def test_modified_artifact_is_detected(tmp_path, run_factory, target_snapshot):
    scenario = load("scenarios/H-03.yaml").snapshot()
    run = run_factory(
        scenario_digest=scenario.digest, target_version=target_snapshot.target_version
    )
    writer = complete_bundle(tmp_path, run, target_snapshot)
    artifact = next((writer.directory / "artifacts").glob("*.json"))
    artifact.write_text("changed", encoding="utf-8")
    result = verify_bundle(writer.directory)
    assert result["bundle_status"] == "INVALID"
    assert artifact.relative_to(writer.directory).as_posix() in result["mismatched_files"]
