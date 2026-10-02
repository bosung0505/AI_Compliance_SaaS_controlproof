"""Small sealed N-02 bundles for US4 review and integrity contracts."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from engine.models import (
    AssertionResult,
    AssertionStatus,
    InconclusiveReason,
    Judgement,
    RunState,
    canonical_json_bytes,
    sha256_bytes,
)
from tests.contract.test_bundle_profile_spec003 import _write_bundle


def reseal_file(bundle: Path, relative_path: str, value, *, jsonl: bool = False) -> None:
    payload = (
        b"".join(canonical_json_bytes(row) + b"\n" for row in value)
        if jsonl
        else canonical_json_bytes(value)
    )
    (bundle / relative_path).write_bytes(payload)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    record = next(row for row in manifest["files"] if row["path"] == relative_path)
    record["sha256"] = sha256_bytes(payload)
    record["size_bytes"] = len(payload)
    manifest["bundle_digest"] = sha256_bytes(
        canonical_json_bytes({key: value for key, value in manifest.items() if key != "bundle_digest"})
    )
    manifest_path.write_bytes(canonical_json_bytes(manifest))


def reseal_snapshot_link(bundle: Path, relative_path: str, value, digest_field: str) -> None:
    reseal_file(bundle, relative_path, value)
    digest = sha256_bytes((bundle / relative_path).read_bytes())
    run = json.loads((bundle / "run.json").read_text(encoding="utf-8"))
    run[digest_field] = digest
    reseal_file(bundle, "run.json", run)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[digest_field] = digest
    manifest["bundle_digest"] = sha256_bytes(
        canonical_json_bytes({key: item for key, item in manifest.items() if key != "bundle_digest"})
    )
    manifest_path.write_bytes(canonical_json_bytes(manifest))


def make_review_bundle(tmp_path, run_factory, target_snapshot) -> Path:
    writer, _manifest = _write_bundle(tmp_path, run_factory, target_snapshot)
    run = writer.run.model_copy(update={
        "state": RunState.COMPLETED,
        "started_at": datetime(2026, 10, 2, 1, tzinfo=UTC),
        "ended_at": datetime(2026, 10, 2, 1, 1, tzinfo=UTC),
    })
    reseal_file(writer.directory, "run.json", run.model_dump(mode="json"))
    assertions = tuple(
        AssertionResult(
            assertion_id=f"N02-A{index}",
            subject_ref=f"synthetic-lane-{index}",
            status=AssertionStatus.INCONCLUSIVE,
            expected={"protected": True},
            actual={"source_status": "UNAVAILABLE"},
            reason_code=InconclusiveReason.INSUFFICIENT_EVIDENCE,
            detail="필수 관찰 사실을 읽지 못했습니다.",
            source_requirements=(f"EV3-{index:02d}",),
        )
        for index in range(1, 8)
    )
    judgement = Judgement(
        run_id=run.run_id,
        scenario_id="N-02",
        verdict="INCONCLUSIVE",
        reason_code="INSUFFICIENT_EVIDENCE",
        assertion_results=assertions,
        summary="필수 관찰 사실을 읽지 못했습니다.",
        unverified_scope=("AWS", "N-01", "N-03"),
    )
    reseal_file(writer.directory, "judgement.json", judgement.model_dump(mode="json"))
    reseal_file(writer.directory, "assertions.json", [
        item.model_dump(mode="json") for item in assertions
    ])
    return writer.directory
