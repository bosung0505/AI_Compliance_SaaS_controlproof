"""T064 — Spec 004 cross-reference rules (contracts/evidence-bundle-v4.md "Cross-reference rules", "Redaction").

RED until T067. Each case edits one sealed file and re-seals the manifest digests, so only the cross-reference
check (not the hash check) can catch it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.evidence import verify_bundle
from engine.models import canonical_json_bytes, sha256_bytes
from engine.runner import build_profile_runner
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters
from tests.fixtures.fake_spec004 import FakeSpec004Adapters, use_spec004_fixture


def _bundle(tmp_path: Path, scenario: str, **options) -> Path:
    adapters, _ = make_adapters(spec004=FakeSpec004Adapters(**options))
    use_spec004_fixture(adapters)
    runner = build_profile_runner(
        load(f"scenarios/{scenario}.yaml"), adapters, tmp_path, clock=FakeClock()
    )
    _, _, bundle = runner.execute(runner.preflight("whyyou-local"))
    return bundle


def _rows(bundle: Path, name: str) -> list[dict]:
    return [
        json.loads(line)
        for line in (bundle / name).read_text(encoding="utf-8").splitlines()
        if line
    ]


def _write_rows(bundle: Path, name: str, rows: list[dict]) -> None:
    payload = b"".join(canonical_json_bytes(row) + b"\n" for row in rows)
    _reseal(bundle, name, payload)


def _write_json(bundle: Path, name: str, value) -> None:
    _reseal(bundle, name, canonical_json_bytes(value))


def _reseal(bundle: Path, name: str, payload: bytes) -> None:
    (bundle / name).write_bytes(payload)
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    for record in manifest["files"]:
        if record["path"] == name:
            record["sha256"] = sha256_bytes(payload)
            record["size_bytes"] = len(payload)
    manifest.pop("bundle_digest", None)
    manifest["bundle_digest"] = sha256_bytes(canonical_json_bytes(manifest))
    (bundle / "manifest.json").write_bytes(canonical_json_bytes(manifest))


def _invalid(bundle: Path, needle: str) -> None:
    result = verify_bundle(bundle)
    assert result["bundle_status"] == "INVALID", result
    problems = result["mismatched_files"] + result.get("cross_reference_errors", [])
    assert any(needle in item for item in problems), problems


def test_untouched_bundles_verify_with_cross_reference_results(tmp_path) -> None:
    for scenario, options in (("E-01", {"removal_indicator": "score_null"}), ("E-02", {})):
        result = verify_bundle(_bundle(tmp_path / scenario, scenario, **options))
        assert result["bundle_status"] == "VERIFIED", result
        assert result["cross_reference_errors"] == []
        assert result["redaction_violations"] == []
    e02 = verify_bundle(_bundle(tmp_path / "again", "E-02"))
    assert e02["recompute_reexecution"] == "MATCH"


def test_citation_case_must_reference_an_existing_receipt(tmp_path) -> None:
    bundle = _bundle(tmp_path, "E-01", removal_indicator="score_null")
    rows = _rows(bundle, "citation-cases.jsonl")
    rows[0]["emission_receipt_id"] = "00000000-0000-0000-0000-0000000000aa"
    _write_rows(bundle, "citation-cases.jsonl", rows)
    _invalid(bundle, "citation-cases.jsonl:receipt")


def test_lane_references_must_exist(tmp_path) -> None:
    bundle = _bundle(tmp_path, "E-01", removal_indicator="score_null")
    rows = _rows(bundle, "report-records.jsonl")
    rows[0]["subject_ref"] = "not-a-run-lane"
    _write_rows(bundle, "report-records.jsonl", rows)
    _invalid(bundle, "report-records.jsonl:lane")


def test_restored_injection_requires_the_pre_change_digest(tmp_path) -> None:
    bundle = _bundle(tmp_path, "E-01", removal_indicator="score_null")
    rows = _rows(bundle, "change-injections.jsonl")
    rows[0]["post_restore_digest"] = "f" * 64
    _write_rows(bundle, "change-injections.jsonl", rows)
    _invalid(bundle, "change-injections.jsonl:restore")


def test_removal_reads_must_follow_phase_order(tmp_path) -> None:
    bundle = _bundle(tmp_path, "E-01", removal_indicator="score_null")
    rows = _rows(bundle, "report-reads.jsonl")
    phases = [row["phase"] for row in rows]
    pre, post = phases.index("PRE_REMOVAL"), phases.index("POST_REMOVAL")
    rows[pre], rows[post] = rows[post], rows[pre]
    _write_rows(bundle, "report-reads.jsonl", rows)
    _invalid(bundle, "report-reads.jsonl:order")


@pytest.mark.parametrize("field", ["computed", "rule_copy_id"])
def test_recompute_is_re_executed(tmp_path, field) -> None:
    bundle = _bundle(tmp_path, "E-02")
    document = json.loads((bundle / "recompute.json").read_text(encoding="utf-8"))
    if field == "computed":
        document["records"][0]["computed"]["score"] += 1
    else:
        document["records"][0]["rule_copy_id"] = "other-copy"
    _write_json(bundle, "recompute.json", document)
    _invalid(bundle, "recompute.json")


def _permuted_comparisons(document, *, policy, equal):
    for record in document["records"]:
        if policy is None:
            record.pop("comparison_policy", None)
        else:
            record["comparison_policy"] = policy
        for comparison in record["comparisons"]:
            if comparison["field_path"] in {
                "scoring_inputs.criteria",
                "report.scoring_breakdown.contributions",
            }:
                comparison["observed"].reverse()
                comparison["equal"] = equal


def test_verify_keyed_comparison_policy_preserves_permutation_equivalence(tmp_path) -> None:
    bundle = _bundle(tmp_path, "E-02")
    document = json.loads((bundle / "recompute.json").read_text(encoding="utf-8"))
    _permuted_comparisons(document, policy="CRITERION_ID_V2", equal=True)
    _write_json(bundle, "recompute.json", document)
    assert verify_bundle(bundle)["bundle_status"] == "VERIFIED"


def test_verify_absent_policy_preserves_legacy_positional_fail(tmp_path) -> None:
    bundle = _bundle(tmp_path, "E-02", stored_overall_offset=1)
    document = json.loads((bundle / "recompute.json").read_text(encoding="utf-8"))
    _permuted_comparisons(document, policy=None, equal=False)
    _write_json(bundle, "recompute.json", document)
    assert verify_bundle(bundle)["bundle_status"] == "VERIFIED"


@pytest.mark.parametrize("mutation", ["value", "duplicate", "unknown_policy"])
def test_verify_keyed_comparisons_still_reject_tampering(tmp_path, mutation) -> None:
    bundle = _bundle(tmp_path, "E-02")
    document = json.loads((bundle / "recompute.json").read_text(encoding="utf-8"))
    _permuted_comparisons(document, policy="CRITERION_ID_V2", equal=True)
    record = document["records"][0]
    if mutation == "unknown_policy":
        record["comparison_policy"] = "unreviewed-policy"
    else:
        comparison = next(
            item
            for item in record["comparisons"]
            if item["field_path"] == "scoring_inputs.criteria"
        )
        if mutation == "value":
            comparison["observed"][0]["contribution"] += 1
        else:
            comparison["observed"][1] = comparison["observed"][0].copy()
    _write_json(bundle, "recompute.json", document)
    _invalid(bundle, "recompute.json")


def test_raw_text_in_a_record_is_a_redaction_violation(tmp_path) -> None:
    bundle = _bundle(tmp_path, "E-01", removal_indicator="score_null")
    rows = _rows(bundle, "report-records.jsonl")
    rows[0]["transcript_text"] = "the applicant said something"
    _write_rows(bundle, "report-records.jsonl", rows)
    result = verify_bundle(bundle)
    assert result["bundle_status"] == "INVALID"
    assert any("report-records.jsonl" in item for item in result["redaction_violations"])
