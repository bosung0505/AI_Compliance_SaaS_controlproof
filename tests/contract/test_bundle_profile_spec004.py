"""T007 — Spec 004 bundle profile (contracts/evidence-bundle-v4.md).

RED until T012 (profile enum and Run policy) and T018 (bundle profile registry and verifiers). A Spec 004 Run
reuses the Spec 003 digest fields: `lane_manifest_digest` covers `spec004-lanes.json`, `path_capability_digest`
covers `spec004-capabilities.json`; E-02 adds `scoring_rule_source_digest` (data-model §1).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from importlib import import_module

import pytest

from engine.evidence import EvidenceBundleWriter, verify_bundle
from engine.models import (
    AwsDeploymentStatus,
    EnvironmentKind,
    ExecutionProfile,
    GitIdentity,
    TargetEnvironmentSnapshot,
    canonical_json_bytes,
    sha256_bytes,
)

E01_FILES = {
    "spec004-capabilities.json",
    "spec004-lanes.json",
    "citation-cases.jsonl",
    "model-emissions.jsonl",
    "report-records.jsonl",
    "report-reads.jsonl",
    "storage-probe.json",
    "change-injections.jsonl",
    "recovery.json",
}
E02_FILES = {
    "spec004-capabilities.json",
    "spec004-lanes.json",
    "report-records.jsonl",
    "report-reads.jsonl",
    "criteria-versions.json",
    "frozen-inputs.json",
    "recompute.json",
    "change-injections.jsonl",
    "recovery.json",
}
SNAPSHOTS = ("environment.snapshot.json", "scenario.snapshot.yaml", "target.snapshot.json")
E01_LINKS = {
    "EV4-01": ("spec004-capabilities.json", *SNAPSHOTS),
    "EV4-02": ("spec004-lanes.json",),
    "EV4-03": ("citation-cases.jsonl", "model-emissions.jsonl"),
    "EV4-04": ("report-records.jsonl", "storage-probe.json"),
    "EV4-05": ("report-reads.jsonl",),
    "EV4-09": ("change-injections.jsonl", "recovery.json"),
    "EV4-10": ("assertions.json", "judgement.json"),
}
E02_LINKS = {
    "EV4-01": ("spec004-capabilities.json", "recompute.json", *SNAPSHOTS),
    "EV4-02": ("spec004-lanes.json",),
    "EV4-04": ("report-records.jsonl",),
    "EV4-06": ("criteria-versions.json",),
    "EV4-07": ("frozen-inputs.json", "report-reads.jsonl"),
    "EV4-08": ("recompute.json",),
    "EV4-09": ("change-injections.jsonl", "recovery.json"),
    "EV4-10": ("assertions.json", "judgement.json"),
}
PROFILES = {
    "E01_CITATION_EVIDENCE_V1": ("E-01", E01_FILES, E01_LINKS),
    "E02_SCORING_FREEZE_V1": ("E-02", E02_FILES, E02_LINKS),
}


def _environment(target_snapshot) -> TargetEnvironmentSnapshot:
    return TargetEnvironmentSnapshot(
        target_id="whyyou-local",
        environment_kind=EnvironmentKind.LOCAL_EMULATED,
        host_os="windows-11",
        controlproof_commit=GitIdentity(commit_sha="a" * 40, dirty=False),
        whyyou_commit=GitIdentity(commit_sha="b" * 40, dirty=False),
        components={"postgres": "fixture"},
        endpoints={"api": "http://localhost:8080"},
        model_fixture_id=target_snapshot.model_fixture_id,
        model_fixture_digest=target_snapshot.model_fixture_digest,
        external_ai_allowed=False,
        aws_deployment_status=AwsDeploymentStatus.NOT_RUN,
        unverified_scope=("AWS", "N-01", "N-03"),
        captured_at=datetime(2026, 10, 7, tzinfo=UTC),
    )


def _write_bundle(
    tmp_path, run_factory, target_snapshot, profile_name: str, *, skip: str | None = None
):
    scenario_id, files, links = PROFILES[profile_name]
    profile = getattr(ExecutionProfile, profile_name)
    environment = _environment(target_snapshot)
    contents = {
        "spec004-capabilities.json": {"capabilities": []},
        "spec004-lanes.json": {"lanes": []},
    }
    extra = {}
    if profile_name == "E02_SCORING_FREEZE_V1":
        extra["scoring_rule_source_digest"] = "d" * 64
    run = run_factory(
        scenario_id=scenario_id,
        scenario_version="1.0.0",
        execution_profile=profile,
        environment_kind=EnvironmentKind.LOCAL_EMULATED,
        aws_deployment_status=AwsDeploymentStatus.NOT_RUN,
        scenario_digest=sha256_bytes(canonical_json_bytes({"execution_profile": profile_name})),
        environment_snapshot_digest=environment.snapshot_digest,
        lane_manifest_digest=sha256_bytes(canonical_json_bytes(contents["spec004-lanes.json"])),
        path_capability_digest=sha256_bytes(
            canonical_json_bytes(contents["spec004-capabilities.json"])
        ),
        unverified_scope=("AWS", "N-01", "N-03"),
        seed_kind="spec004-report-lanes-v1",
        fault_kind="spec004-change-injection-v1",
        **extra,
    )
    writer = EvidenceBundleWriter(tmp_path, run)
    documents = {
        "run.json": run.model_dump(mode="json"),
        "scenario.snapshot.yaml": {
            "digest": run.scenario_digest,
            "definition": {"execution_profile": profile_name},
        },
        "target.snapshot.json": target_snapshot.model_dump(mode="json"),
        "environment.snapshot.json": environment.model_dump(mode="json"),
        "subjects.json": [],
        "assertions.json": [],
        "judgement.json": {"verdict": "INCONCLUSIVE"},
        **contents,
        "storage-probe.json": {"exposure": []},
        "criteria-versions.json": {"versions": []},
        "frozen-inputs.json": {"reports": []},
        "recompute.json": {"records": []},
        "recovery.json": {"restore_status": "SUCCEEDED"},
    }
    for path, value in documents.items():
        if (
            path
            in files
            | {"run.json", "subjects.json", "assertions.json", "judgement.json", *SNAPSHOTS}
            and path != skip
        ):
            writer.write_json(path, value, redact_first=False)
    for path in sorted(files):
        if path.endswith(".jsonl") and path != skip:
            writer.write_bytes(path, b"", "application/x-ndjson")
    writer.write_bytes("observations.jsonl", b"", "application/x-ndjson")
    for evidence_id, paths in links.items():
        for path in paths:
            if path != skip:
                writer.link_file_evidence(evidence_id, path)
    writer.link_intrinsic_evidence("EV4-10", "sealed-manifest")
    return writer, writer.seal()


def test_module_exports_the_spec004_profile_contract() -> None:
    evidence = import_module("engine.evidence")
    assert evidence.SPEC004_PROFILE_CONTRACT == "controlproof.bundle-profile.spec004.v1"
    assert evidence.spec004_required_files(ExecutionProfile.E01_CITATION_EVIDENCE_V1) == E01_FILES
    assert evidence.spec004_required_files(ExecutionProfile.E02_SCORING_FREEZE_V1) == E02_FILES


@pytest.mark.parametrize("profile_name", sorted(PROFILES))
def test_spec004_bundle_is_sealed_with_the_profile_evidence_subset(
    tmp_path, run_factory, target_snapshot, profile_name
) -> None:
    writer, manifest = _write_bundle(tmp_path, run_factory, target_snapshot, profile_name)
    _, files, links = PROFILES[profile_name]
    assert manifest["profile_contract"] == "controlproof.bundle-profile.spec004.v1"
    assert files <= {record["path"] for record in manifest["files"]}
    result = verify_bundle(writer.directory)
    assert result["bundle_status"] == "VERIFIED"
    assert result["checked_evidence_requirements"] == sorted(links)


@pytest.mark.parametrize(
    "profile_name,missing",
    [
        ("E01_CITATION_EVIDENCE_V1", "storage-probe.json"),
        ("E01_CITATION_EVIDENCE_V1", "model-emissions.jsonl"),
        ("E02_SCORING_FREEZE_V1", "recompute.json"),
        ("E02_SCORING_FREEZE_V1", "criteria-versions.json"),
    ],
)
def test_missing_profile_file_is_invalid(
    tmp_path, run_factory, target_snapshot, profile_name, missing
) -> None:
    """A sealed bundle that later loses a profile file is INVALID (ID-004-04: the writer refuses to
    seal without it, so the loss can only happen after sealing)."""
    writer, _ = _write_bundle(tmp_path, run_factory, target_snapshot, profile_name)
    (writer.directory / missing).unlink()
    result = verify_bundle(writer.directory)
    assert result["bundle_status"] == "INVALID"
    assert missing in result["missing_files"]


@pytest.mark.parametrize(
    "profile_name,missing",
    [
        ("E01_CITATION_EVIDENCE_V1", "storage-probe.json"),
        ("E02_SCORING_FREEZE_V1", "recompute.json"),
    ],
)
def test_writer_refuses_to_seal_without_a_profile_file(
    tmp_path, run_factory, target_snapshot, profile_name, missing
) -> None:
    with pytest.raises(ValueError, match="canonical files missing"):
        _write_bundle(tmp_path, run_factory, target_snapshot, profile_name, skip=missing)


def test_e02_bundle_does_not_require_model_emissions(
    tmp_path, run_factory, target_snapshot
) -> None:
    writer, manifest = _write_bundle(
        tmp_path, run_factory, target_snapshot, "E02_SCORING_FREEZE_V1"
    )
    assert "model-emissions.jsonl" not in {record["path"] for record in manifest["files"]}
    assert verify_bundle(writer.directory)["bundle_status"] == "VERIFIED"


def test_tampered_spec004_file_is_invalid_and_manifest_is_unchanged(
    tmp_path, run_factory, target_snapshot
) -> None:
    writer, _ = _write_bundle(tmp_path, run_factory, target_snapshot, "E01_CITATION_EVIDENCE_V1")
    original = (writer.directory / "manifest.json").read_bytes()
    (writer.directory / "report-reads.jsonl").write_text(
        json.dumps({"tampered": True}) + "\n", encoding="utf-8"
    )
    assert verify_bundle(writer.directory)["bundle_status"] == "INVALID"
    assert (writer.directory / "manifest.json").read_bytes() == original
