from __future__ import annotations

import json
from datetime import UTC, datetime

from engine.evidence import EvidenceBundleWriter, verify_bundle
from engine.models import (
    SPEC003_UNVERIFIED_SCOPE,
    AwsDeploymentStatus,
    EnvironmentKind,
    ExecutionProfile,
    GitIdentity,
    TargetEnvironmentSnapshot,
    canonical_json_bytes,
    sha256_bytes,
)

N02_FILES = {
    "n02-capabilities.json",
    "n02-lanes.json",
    "policy-and-consent.json",
    "baseline-effects.jsonl",
    "bypass-attempts.jsonl",
    "protected-effects.jsonl",
    "causal-events.jsonl",
    "causal-edges.jsonl",
    "fault-receipts.jsonl",
    "recovery.json",
}


def _n02_run(run_factory, environment, contents):
    scenario_definition = {"execution_profile": "N02_CONSENT_ORDER_V1"}
    return run_factory(
        scenario_id="N-02",
        scenario_version="1.0.0",
        execution_profile=ExecutionProfile.N02_CONSENT_ORDER_V1,
        environment_kind=EnvironmentKind.LOCAL_EMULATED,
        aws_deployment_status=AwsDeploymentStatus.NOT_RUN,
        scenario_digest=sha256_bytes(canonical_json_bytes(scenario_definition)),
        environment_snapshot_digest=environment.snapshot_digest,
        lane_manifest_digest=sha256_bytes(canonical_json_bytes(contents["n02-lanes.json"])),
        path_capability_digest=sha256_bytes(
            canonical_json_bytes(contents["n02-capabilities.json"])
        ),
        policy_snapshot_digest=sha256_bytes(
            canonical_json_bytes(contents["policy-and-consent.json"])
        ),
        unverified_scope=tuple(sorted(SPEC003_UNVERIFIED_SCOPE)),
        seed_kind="n02-six-lanes-v1",
        fault_kind="consent_after_record_before_state_v1",
    )


def _write_bundle(tmp_path, run_factory, target_snapshot):
    contents = {
        "n02-capabilities.json": {"paths": []},
        "n02-lanes.json": {"lanes": []},
        "policy-and-consent.json": {"policy_version": "fixture-v1"},
    }
    environment = TargetEnvironmentSnapshot(
        target_id="whyyou-local",
        environment_kind=EnvironmentKind.LOCAL_EMULATED,
        host_os="windows-11",
        controlproof_commit=GitIdentity(commit_sha="a" * 40, dirty=False),
        whyyou_commit=GitIdentity(commit_sha="b" * 40, dirty=False),
        components={"postgres": "fixture", "localstack": "fixture"},
        endpoints={"api": "http://localhost:8000"},
        model_fixture_id=target_snapshot.model_fixture_id,
        model_fixture_digest=target_snapshot.model_fixture_digest,
        external_ai_allowed=False,
        aws_deployment_status=AwsDeploymentStatus.NOT_RUN,
        unverified_scope=tuple(sorted(SPEC003_UNVERIFIED_SCOPE)),
        captured_at=datetime(2026, 10, 1, tzinfo=UTC),
    )
    run = _n02_run(run_factory, environment, contents)
    writer = EvidenceBundleWriter(tmp_path, run)
    for path, value in {
        "run.json": run.model_dump(mode="json"),
        "scenario.snapshot.yaml": {
            "digest": run.scenario_digest,
            "definition": {"execution_profile": "N02_CONSENT_ORDER_V1"},
        },
        "target.snapshot.json": target_snapshot.model_dump(mode="json"),
        "environment.snapshot.json": environment.model_dump(mode="json"),
        "subjects.json": [],
        "assertions.json": [],
        "judgement.json": {"verdict": "INCONCLUSIVE"},
        **contents,
        "recovery.json": {"restore_status": "SUCCEEDED"},
    }.items():
        writer.write_json(path, value, redact_first=False)
    for path in (
        "faults.jsonl",
        "observations.jsonl",
        "baseline-effects.jsonl",
        "bypass-attempts.jsonl",
        "protected-effects.jsonl",
        "causal-events.jsonl",
        "causal-edges.jsonl",
        "fault-receipts.jsonl",
    ):
        writer.write_bytes(path, b"", "application/x-ndjson")
    mapping = {
        "EV3-01": (
            "n02-capabilities.json",
            "n02-lanes.json",
            "environment.snapshot.json",
            "scenario.snapshot.yaml",
            "target.snapshot.json",
        ),
        "EV3-02": ("policy-and-consent.json",),
        "EV3-03": ("baseline-effects.jsonl", "n02-lanes.json"),
        "EV3-04": ("bypass-attempts.jsonl",),
        "EV3-05": ("protected-effects.jsonl",),
        "EV3-06": ("causal-events.jsonl", "causal-edges.jsonl"),
        "EV3-07": ("fault-receipts.jsonl",),
        "EV3-08": ("policy-and-consent.json", "protected-effects.jsonl"),
        "EV3-09": ("recovery.json", "protected-effects.jsonl"),
        "EV3-10": ("assertions.json", "judgement.json"),
    }
    for evidence_id, paths in mapping.items():
        for path in paths:
            writer.link_file_evidence(evidence_id, path)
    writer.link_intrinsic_evidence("EV3-10", "sealed-manifest")
    manifest = writer.seal()
    return writer, manifest


def test_spec003_bundle_is_additive_sealed_and_tamper_evident(
    tmp_path, run_factory, target_snapshot
) -> None:
    writer, manifest = _write_bundle(tmp_path, run_factory, target_snapshot)
    assert manifest["profile_contract"] == "controlproof.bundle-profile.spec003.v1"
    assert N02_FILES <= {record["path"] for record in manifest["files"]}
    result = verify_bundle(writer.directory)
    assert result["bundle_status"] == "VERIFIED"
    assert result["checked_evidence_requirements"] == [
        f"EV3-{index:02d}" for index in range(1, 11)
    ]

    original_manifest = (writer.directory / "manifest.json").read_bytes()
    (writer.directory / "causal-edges.jsonl").write_text(
        json.dumps({"tampered": True}) + "\n", encoding="utf-8"
    )
    assert verify_bundle(writer.directory)["bundle_status"] == "INVALID"
    assert (writer.directory / "manifest.json").read_bytes() == original_manifest
