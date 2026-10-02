"""EV3 integrity includes readable facts and cross-file identity, not hashes alone."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest

from engine.evidence import verify_bundle
from engine.models import canonical_json_bytes, sha256_bytes
from tests.fixtures.n02_review_bundle import (
    make_review_bundle,
    reseal_file,
    reseal_snapshot_link,
)
from tests.fixtures.spec003 import (
    causal_edge,
    causal_event,
    fault_receipt,
    processing_attempt,
    protected_effect,
    six_subject_lanes,
)


def _set_lanes(bundle) -> None:
    run_id = json.loads((bundle / "run.json").read_text(encoding="utf-8"))["run_id"]
    reseal_snapshot_link(
        bundle,
        "n02-lanes.json",
        {"lanes": [{**lane, "run_id": run_id} for lane in six_subject_lanes()]},
        "lane_manifest_digest",
    )


@pytest.mark.parametrize("evidence_id", [f"EV3-{index:02d}" for index in range(1, 11)])
def test_each_ev3_mapping_is_required_for_bundle_verification(
    tmp_path, run_factory, target_snapshot, evidence_id
) -> None:
    bundle = make_review_bundle(tmp_path, run_factory, target_snapshot)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["required_evidence"].pop(evidence_id)
    manifest["bundle_digest"] = sha256_bytes(
        canonical_json_bytes({key: value for key, value in manifest.items() if key != "bundle_digest"})
    )
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    result = verify_bundle(bundle)
    assert result["bundle_status"] == "INVALID"
    assert f"evidence:{evidence_id}" in result["missing_files"]


def test_ev3_mapping_cannot_point_to_unrelated_registered_file(
    tmp_path, run_factory, target_snapshot
) -> None:
    bundle = make_review_bundle(tmp_path, run_factory, target_snapshot)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["required_evidence"]["EV3-04"] = ["file:assertions.json"]
    manifest["bundle_digest"] = sha256_bytes(
        canonical_json_bytes({key: value for key, value in manifest.items() if key != "bundle_digest"})
    )
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    result = verify_bundle(bundle)
    assert result["bundle_status"] == "INVALID"
    assert "evidence:EV3-04:canonical-files" in result["mismatched_files"]


@pytest.mark.parametrize(
    ("relative_path", "rows"),
    [
        ("bypass-attempts.jsonl", [processing_attempt(lane_id="DOCUMENT_BYPASS", subject_ref="unregistered-subject")]),
        ("protected-effects.jsonl", [protected_effect(lane_id="DOCUMENT_BYPASS", subject_ref="unregistered-subject")]),
        ("causal-events.jsonl", [causal_event(subject_ref="unregistered-subject")]),
        ("fault-receipts.jsonl", [fault_receipt(subject_ref="unregistered-subject")]),
    ],
)
def test_registered_ev3_file_cannot_reference_another_subject(
    tmp_path, run_factory, target_snapshot, relative_path, rows
) -> None:
    bundle = make_review_bundle(tmp_path, run_factory, target_snapshot)
    _set_lanes(bundle)
    run_id = json.loads((bundle / "run.json").read_text(encoding="utf-8"))["run_id"]
    rows = [{**row, "run_id": run_id} for row in rows]
    reseal_file(bundle, relative_path, rows, jsonl=True)
    result = verify_bundle(bundle)
    assert result["bundle_status"] == "INVALID"
    assert result["mismatched_files"]


def test_attempt_effect_path_mismatch_invalidates_hash_consistent_bundle(
    tmp_path, run_factory, target_snapshot
) -> None:
    bundle = make_review_bundle(tmp_path, run_factory, target_snapshot)
    _set_lanes(bundle)
    run_id = json.loads((bundle / "run.json").read_text(encoding="utf-8"))["run_id"]
    attempt = processing_attempt("DOCUMENT_ANALYSIS", lane_id="DOCUMENT_BYPASS", run_id=run_id)
    effect = protected_effect(
        "RECORDING",
        lane_id="DOCUMENT_BYPASS",
        request_ids=[attempt["request_id"]],
        run_id=run_id,
    )
    reseal_file(bundle, "bypass-attempts.jsonl", [attempt], jsonl=True)
    reseal_file(bundle, "protected-effects.jsonl", [effect], jsonl=True)
    assert verify_bundle(bundle)["bundle_status"] == "INVALID"


def test_causal_edge_must_name_two_same_run_lane_subject_events(
    tmp_path, run_factory, target_snapshot
) -> None:
    bundle = make_review_bundle(tmp_path, run_factory, target_snapshot)
    _set_lanes(bundle)
    run_id = json.loads((bundle / "run.json").read_text(encoding="utf-8"))["run_id"]
    event = causal_event(run_id=run_id)
    reseal_file(bundle, "causal-events.jsonl", [event], jsonl=True)
    reseal_file(
        bundle,
        "causal-edges.jsonl",
        [causal_edge(event["causal_event_id"], str(uuid4()))],
        jsonl=True,
    )
    assert verify_bundle(bundle)["bundle_status"] == "INVALID"


def test_fault_receipt_must_match_current_run_and_failed_request(
    tmp_path, run_factory, target_snapshot
) -> None:
    bundle = make_review_bundle(tmp_path, run_factory, target_snapshot)
    _set_lanes(bundle)
    reseal_file(bundle, "fault-receipts.jsonl", [fault_receipt(run_id=str(uuid4()))], jsonl=True)
    assert verify_bundle(bundle)["bundle_status"] == "INVALID"


def test_unreadable_required_facts_cannot_reconstruct_pass(
    tmp_path, run_factory, target_snapshot
) -> None:
    bundle = make_review_bundle(tmp_path, run_factory, target_snapshot)
    judgement = json.loads((bundle / "judgement.json").read_text(encoding="utf-8"))
    judgement["verdict"] = "PASS"
    judgement["reason_code"] = None
    for assertion in judgement["assertion_results"]:
        assertion["status"] = "PASS"
        assertion["reason_code"] = None
    reseal_file(bundle, "judgement.json", judgement)
    reseal_file(bundle, "assertions.json", judgement["assertion_results"])
    result = verify_bundle(bundle)
    assert result["bundle_status"] == "INVALID"
    assert result["mismatched_files"] or result["missing_files"]


def test_unregistered_file_and_secret_are_rejected_without_rewriting_manifest(
    tmp_path, run_factory, target_snapshot
) -> None:
    bundle = make_review_bundle(tmp_path, run_factory, target_snapshot)
    original_manifest = (bundle / "manifest.json").read_bytes()
    (bundle / "extra.json").write_text("{}", encoding="utf-8")
    result = verify_bundle(bundle)
    assert result["bundle_status"] == "INVALID"
    assert result["unregistered_files"] == ["extra.json"]
    assert (bundle / "manifest.json").read_bytes() == original_manifest

    (bundle / "extra.json").unlink()
    reseal_file(bundle, "bypass-attempts.jsonl", [
        {"password": "synthetic-secret"}
    ], jsonl=True)
    assert verify_bundle(bundle)["bundle_status"] == "INVALID"
