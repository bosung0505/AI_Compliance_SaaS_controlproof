from __future__ import annotations

import json
from datetime import UTC, datetime

from engine.evidence import EvidenceBundleWriter, verify_bundle
from engine.models import (
    AwsDeploymentStatus,
    EnvironmentKind,
    ExecutionProfile,
    FaultVariant,
    GitIdentity,
    Phase,
    QueueTopologySnapshot,
    Run,
    TargetEnvironmentSnapshot,
    canonical_json_bytes,
    sha256_bytes,
)


def test_spec002_bundle_uses_additive_profile_contract(
    tmp_path, run_factory, target_snapshot
):
    origin_run, origin_manifest, origin_artifact, origin_writer = _write_origin_bundle(
        tmp_path, run_factory, target_snapshot
    )
    environment = TargetEnvironmentSnapshot(
        target_id="whyyou-local",
        environment_kind=EnvironmentKind.LOCAL_EMULATED,
        host_os="windows-11",
        controlproof_commit=GitIdentity(commit_sha="a" * 40, dirty=False),
        whyyou_commit=GitIdentity(commit_sha="b" * 40, dirty=False),
        components={"localstack": "3.8"},
        endpoints={"api": "http://localhost:8080", "sqs": "http://localhost:4566"},
        model_fixture_id="h03-report-v1",
        model_fixture_digest=target_snapshot.model_fixture_digest,
        external_ai_allowed=False,
        aws_deployment_status=AwsDeploymentStatus.NOT_RUN,
        unverified_scope=("AWS_SQS", "AWS_ECS", "AWS_IAM", "AWS_CLOUDWATCH", "AWS_NETWORK"),
        captured_at=datetime(2026, 9, 28, tzinfo=UTC),
    )
    queue = QueueTopologySnapshot(
        source_queue_name="iep-reporting",
        source_queue_url_digest="d" * 64,
        dead_letter_queue_name="iep-reporting-dlq",
        dead_letter_queue_arn="arn:aws:sqs:ap-northeast-2:000000000000:iep-reporting-dlq",
        max_receive_count=3,
        visibility_timeout_seconds=5,
        source_retention_seconds=3600,
        dlq_retention_seconds=7200,
        redrive_policy_digest="e" * 64,
        captured_at=datetime(2026, 9, 28, tzinfo=UTC),
    )
    scenario_definition = {"execution_profile": "E03_AFTER_V2"}
    base = run_factory().model_dump(mode="python")
    run = Run.model_validate(
        {
            **base,
            "scenario_id": "E-03",
            "scenario_version": "2.0.0",
            "scenario_digest": sha256_bytes(canonical_json_bytes(scenario_definition)),
            "execution_profile": ExecutionProfile.E03_AFTER_V2,
            "fault_variant": FaultVariant.AFTER_RESULT_DURABLE_BEFORE_COMPLETION,
            "environment_kind": EnvironmentKind.LOCAL_EMULATED,
            "aws_deployment_status": AwsDeploymentStatus.NOT_RUN,
            "environment_snapshot_digest": environment.snapshot_digest,
            "queue_topology_digest": queue.snapshot_digest,
            "unverified_scope": environment.unverified_scope,
        }
    )
    writer = EvidenceBundleWriter(tmp_path, run)
    for path, value in {
        "run.json": run.model_dump(mode="json"),
        "scenario.snapshot.yaml": {
            "digest": run.scenario_digest,
            "definition": scenario_definition,
        },
        "target.snapshot.json": target_snapshot.model_dump(mode="json"),
        "environment.snapshot.json": environment.model_dump(mode="json"),
        "queue-topology.snapshot.json": queue.model_dump(mode="json"),
        "subjects.json": [],
        "assertions.json": [],
        "judgement.json": {"verdict": "INCONCLUSIVE"},
    }.items():
        writer.write_json(path, value, redact_first=False)
    for path in ("faults.jsonl", "observations.jsonl", "delivery-attempts.jsonl", "effects.jsonl"):
        writer.write_bytes(path, b"", "application/x-ndjson")
    writer.link_file_evidence("EV2-01", "environment.snapshot.json")
    writer.link_file_evidence("EV2-01", "queue-topology.snapshot.json")
    writer.link_file_evidence("EV2-02", "effects.jsonl")
    writer.link_file_evidence("EV2-12", "scenario.snapshot.yaml")
    writer.link_file_evidence("EV2-12", "target.snapshot.json")
    writer.link_intrinsic_evidence("EV2-12", "sealed-manifest")
    artifact = writer.collect_json_artifact(
        subject_ref="candidate-01",
        phase=Phase.INJECTED,
        step_id="fault.boundary.read",
        attempt=1,
        evidence_requirement_ids=("EV2-03",),
        artifact_type="FAULT_RECEIPT",
        source_locator={"kind": "fixture"},
        content={"boundary": "AFTER_DB_COMMIT_BEFORE_SQS_ACK"},
    )
    writer.link_origin_artifact(
        "EV2-03",
        origin_run_id=origin_run.run_id,
        artifact_id=origin_artifact.artifact_id,
        artifact_digest=origin_artifact.sha256,
        bundle_digest=origin_manifest["bundle_digest"],
    )
    writer.link_file_evidence("EV2-04", "delivery-attempts.jsonl")
    writer.link_file_evidence("EV2-09", "effects.jsonl")
    writer.link_file_evidence("EV2-10", "effects.jsonl")
    manifest = writer.seal()
    assert manifest["profile_contract"] == "controlproof.bundle-profile.spec002.v1"
    assert manifest["required_evidence"]["EV2-01"] == [
        "file:environment.snapshot.json",
        "file:queue-topology.snapshot.json",
    ]
    assert manifest["required_evidence"]["EV2-03"][0] == f"artifact:{artifact.artifact_id}"
    assert manifest["required_evidence"]["EV2-03"][1]["origin_run_id"] == str(
        origin_run.run_id
    )
    assert "intrinsic:sealed-manifest" in manifest["required_evidence"]["EV2-12"]
    assert verify_bundle(writer.directory)["bundle_status"] == "VERIFIED"
    persisted = json.loads((writer.directory / "manifest.json").read_text(encoding="utf-8"))
    assert persisted["environment_snapshot_digest"] == environment.snapshot_digest
    (writer.directory / "effects.jsonl").write_bytes(b'{"tampered":true}\n')
    assert verify_bundle(writer.directory, require_all_evidence=False)["bundle_status"] == "INVALID"
    (writer.directory / "effects.jsonl").write_bytes(b"")
    (origin_writer.directory / origin_artifact.relative_path).write_bytes(b"{}")
    result = verify_bundle(writer.directory)
    assert result["bundle_status"] == "INVALID"
    assert "evidence:EV2-03:origin-bundle-invalid" in result["mismatched_files"]


def _write_origin_bundle(tmp_path, run_factory, target_snapshot):
    definition = {"fixture": "origin-run"}
    origin = run_factory(
        scenario_digest=sha256_bytes(canonical_json_bytes(definition))
    )
    writer = EvidenceBundleWriter(tmp_path, origin)
    for path, value in {
        "run.json": origin.model_dump(mode="json"),
        "scenario.snapshot.yaml": {
            "digest": origin.scenario_digest,
            "definition": definition,
        },
        "target.snapshot.json": target_snapshot.model_dump(mode="json"),
        "subjects.json": [],
        "assertions.json": [],
        "judgement.json": {"verdict": "INCONCLUSIVE"},
    }.items():
        writer.write_json(path, value, redact_first=False)
    writer.write_bytes("faults.jsonl", b"", "application/x-ndjson")
    writer.write_bytes("observations.jsonl", b"", "application/x-ndjson")
    artifact = writer.collect_json_artifact(
        subject_ref="candidate-01",
        phase=Phase.BASELINE,
        step_id="origin.snapshot",
        attempt=1,
        evidence_requirement_ids=("EV-01",),
        artifact_type="STATE_SNAPSHOT",
        source_locator={"kind": "fixture"},
        content={"state": "origin"},
    )
    manifest = writer.seal()
    assert verify_bundle(writer.directory, require_all_evidence=False)["bundle_status"] == "VERIFIED"
    return origin, manifest, artifact, writer
