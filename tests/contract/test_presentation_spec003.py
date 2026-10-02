"""N-02 review must expose facts and the boundary of its claim."""

from __future__ import annotations

from engine.presentation import load_bundle_summary, render_human
from tests.fixtures.n02_review_bundle import (
    make_review_bundle,
    reseal_file,
    reseal_snapshot_link,
)
from tests.fixtures.spec003 import (
    consent_state,
    processing_attempt,
    protected_effect,
    six_subject_lanes,
)


def test_n02_review_keeps_lane_path_request_and_effect_facts_separate(
    tmp_path, run_factory, target_snapshot
) -> None:
    bundle = make_review_bundle(tmp_path, run_factory, target_snapshot)
    reseal_snapshot_link(bundle, "n02-lanes.json", {"lanes": six_subject_lanes()}, "lane_manifest_digest")
    reseal_file(bundle, "bypass-attempts.jsonl", [processing_attempt()], jsonl=True)
    reseal_file(bundle, "protected-effects.jsonl", [protected_effect()], jsonl=True)
    summary = load_bundle_summary(bundle)

    review = summary["n02_review"]
    assert len(review["lanes"]) == 6
    document = review["paths"]["DOCUMENT_ANALYSIS"]
    assert document["entry_kind"] == "HTTP"
    assert document["operation_id"] == "createSubmissionUploadIntent"
    assert document["request"]["response_class"] == "DENIED"
    assert document["effect"]["new_effect_ids"] == []
    assert document["effect"]["source_status"] != "UNAVAILABLE"


def test_n02_review_explains_policy_order_fault_restore_and_unavailable_facts(
    tmp_path, run_factory, target_snapshot
) -> None:
    bundle = make_review_bundle(tmp_path, run_factory, target_snapshot)
    reseal_snapshot_link(
        bundle,
        "policy-and-consent.json",
        {"policy_version": "2026-08-v1", "consent": consent_state()},
        "policy_snapshot_digest",
    )
    reseal_file(bundle, "recovery.json", {"restore_status": "FAILED", "manual_cleanup_required": True})
    reseal_file(
        bundle,
        "protected-effects.jsonl",
        [protected_effect("RECORDING", lane_id="RECORDING_BOUNDARY_PROBE", source_status="UNAVAILABLE", source_error_code="OBSERVER_UNAVAILABLE")],
        jsonl=True,
    )
    summary = load_bundle_summary(bundle)
    human = render_human(summary)

    assert summary["n02_review"]["policy_order"]["policy_version"] == "2026-08-v1"
    assert summary["n02_review"]["fault_recovery"]["restore_status"] == "FAILED"
    assert summary["n02_review"]["paths"]["RECORDING"]["effect"]["source_status"] == "UNAVAILABLE"
    assert "조회하지 못함" in human
    assert "수동" in human


def test_n02_review_limits_local_claim_and_never_certifies_other_scenarios(
    tmp_path, run_factory, target_snapshot
) -> None:
    bundle = make_review_bundle(tmp_path, run_factory, target_snapshot)
    summary = load_bundle_summary(bundle)
    human = render_human(summary)

    assert summary["claim_scope"] == "EXECUTED_SCENARIO_AND_EVIDENCE_ONLY"
    assert summary["environment_kind"] == "LOCAL_EMULATED"
    assert summary["aws_deployment_status"] == "NOT_RUN"
    assert set(summary["unverified_scope"]) == {"AWS", "N-01", "N-03"}
    assert all(part in human for part in ("N-01", "N-03", "AWS", "법적 준수 전체"))
    assert "인증하거나 보증하지 않습니다" in human
