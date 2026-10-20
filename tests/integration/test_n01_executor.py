"""T009b — N-01 executor over fakes: screens, captures, identifiers, sealed evidence, block, retest, redaction."""

from __future__ import annotations

import hashlib
import json
from uuid import uuid4

import pytest

from engine.evidence import verify_bundle
from engine.executors.n01 import LINKS, UNVERIFIED_SCOPE, N01Executor
from engine.n01_evidence import REQUIRED_FILES
from engine.retest import prepare_retest
from engine.scenario import load
from tests.fixtures.fake_spec009 import (
    CURRENT,
    make_spec009_adapters,
    ready,
    spec009_environment,
    spec009_target,
)
from tests.fixtures.n02_review_bundle import reseal_file

SCENARIO = load("scenarios/N-01.yaml")


@pytest.fixture
def target(target_snapshot):
    return spec009_target(target_snapshot)


class State:
    def __init__(self, adapters, backend, store, executor) -> None:
        self.adapters, self.backend, self.store, self.executor = adapters, backend, store, executor


def _execute(tmp_path, target, **options):
    adapters, backend, store = make_spec009_adapters(tmp_path, target, **options)
    executor = N01Executor(SCENARIO, adapters, tmp_path / "runs")
    run, judgement, directory = executor.execute(ready(SCENARIO, target))
    return run, judgement, directory, State(adapters, backend, store, executor)


def _read(directory, name):
    return json.loads((directory / name).read_text(encoding="utf-8"))


def _statuses(judgement):
    return {item.assertion_id: item.status.value for item in judgement.assertion_results}


def test_pass_flow_seals_captures_and_identifiers(tmp_path, target) -> None:
    run, judgement, directory, state = _execute(tmp_path, target)
    assert run.state.value == "COMPLETED"
    assert judgement.verdict.value == "PASS", judgement.assertion_results
    assert _statuses(judgement) == {"N01-A1": "PASS", "N01-A2": "PASS", "N01-A3": "PASS"}
    names = {path.name for path in directory.iterdir()}
    assert REQUIRED_FILES <= names
    assert {"n01-pc-capture.png", "n01-mobile-capture.png"} <= names
    result = verify_bundle(directory)
    assert result["bundle_status"] == "VERIFIED", result["mismatched_files"]
    assert state.executor.verification["bundle_status"] == "VERIFIED"
    manifest = _read(directory, "manifest.json")
    assert manifest["profile_contract"] == "controlproof.bundle-profile.spec009.v1"
    assert set(manifest["required_evidence"]) == set(LINKS)
    assert "file:n01-mobile-capture.png" in manifest["required_evidence"]["EV9-03"]
    measurements = _read(directory, "n01-measurements.json")
    for record in measurements:
        capture = record["capture"]
        payload = (directory / capture["file"]).read_bytes()
        assert capture["file"] == f"n01-{record['lane']}-capture.png"
        assert hashlib.sha256(payload).hexdigest() == capture["sha256"] and len(payload) == capture["bytes"]
    identifiers = _read(directory, "n01-policy-identifiers.json")
    assert [row["lane"] for row in identifiers] == ["pc", "mobile"]
    for row in identifiers:
        assert row["screen"] == row["server"] == CURRENT
        assert row["stored"] == {"policy_version": CURRENT["version"], "evidence_digest": CURRENT["digest"]}
        assert row["consented_at"] and row["commit_status"] == 201
    lanes = _read(directory, "n01-lanes.json")
    assert [(row["lane"], row["viewport"]["width"]) for row in lanes] == [("pc", 1440), ("mobile", 390)]
    assert run.seed_kind == "n01-invited-token-lanes-v1" and run.fault_kind == "n01-consent-screen-observation-v1"


def test_fragments_come_from_the_observed_policy(tmp_path, target) -> None:
    _run, _judgement, directory, _ = _execute(tmp_path, target)
    record = _read(directory, "n01-measurements.json")[0]
    fragments = {item["item_id"]: [f["fragment_id"] for f in item["fragments"]] for item in record["items"]}
    assert fragments["retention"] == ["retention.label", "retention.days"]
    assert sum(len(value) for value in fragments.values()) == 11


def test_mobile_overflow_is_a_sealed_fail(tmp_path, target) -> None:
    run, judgement, directory, _ = _execute(tmp_path, target, modes={"overflow_mobile"})
    assert run.state.value == "COMPLETED"
    assert judgement.verdict.value == "FAIL"
    assert _statuses(judgement) == {"N01-A1": "PASS", "N01-A2": "FAIL", "N01-A3": "PASS"}
    assert verify_bundle(directory)["bundle_status"] == "VERIFIED"


def test_identity_failure_is_inconclusive_without_captures(tmp_path, target) -> None:
    run, judgement, directory, _ = _execute(tmp_path, target, modes={"identity_failure"})
    assert run.state.value == "COMPLETED"
    assert judgement.verdict.value == "INCONCLUSIVE" and judgement.reason_code.value == "INSUFFICIENT_EVIDENCE"
    assert set(_statuses(judgement).values()) == {"INCONCLUSIVE"}
    assert not list(directory.glob("*.png"))
    records = _read(directory, "n01-measurements.json")
    assert {record["measurement_error"] for record in records} == {"BROWSER_IDENTITY_FAILED"}
    assert verify_bundle(directory)["bundle_status"] == "VERIFIED"


def test_commit_failure_judges_screens_and_leaves_identifiers_inconclusive(tmp_path, target) -> None:
    _run, judgement, directory, _ = _execute(tmp_path, target, modes={"commit_failure"})
    assert _statuses(judgement) == {"N01-A1": "PASS", "N01-A2": "PASS", "N01-A3": "INCONCLUSIVE"}
    assert verify_bundle(directory)["bundle_status"] == "VERIFIED"


def test_unreachable_app_records_pre_capture_failure(tmp_path, target) -> None:
    _run, judgement, directory, _ = _execute(tmp_path, target, modes={"app_unreachable"})
    assert judgement.verdict.value == "INCONCLUSIVE"
    records = _read(directory, "n01-measurements.json")
    assert {record["measurement_error"] for record in records} == {"BROWSER_CAPTURE_FAILED"}
    assert {record["step_reached"] for record in records} == {"error"}
    assert verify_bundle(directory)["bundle_status"] == "VERIFIED"


def test_judgement_scope_and_scope_file_are_fixed(tmp_path, target) -> None:
    run, judgement, directory, _ = _execute(tmp_path, target)
    expected = ("AWS_NOT_RUN", "EXTERNAL_MODEL_QUALITY_NOT_TESTED", "N02_PRE_CONSENT_BLOCK_NOT_RETESTED")
    assert UNVERIFIED_SCOPE == expected
    assert judgement.unverified_scope == expected and run.unverified_scope == expected
    scope = _read(directory, "n01-scope.json")
    assert scope["unverified_scope_items"] == [] and scope["limitations"] == []
    assert scope["target_access"] == ["SCREEN", "API"]


def test_failed_teardown_blocks_the_target(tmp_path, target) -> None:
    run, judgement, directory, state = _execute(tmp_path, target, teardown="RESIDUE")
    assert run.state.value == "RESTORE_FAILED" and run.manual_cleanup_required
    assert judgement.verdict.value == "INCONCLUSIVE"
    assert verify_bundle(directory)["bundle_status"] == "VERIFIED"
    with pytest.raises(RuntimeError, match="N01_RESTORE_BLOCKED"):
        state.executor.execute(ready(SCENARIO, target))


def test_raw_tokens_and_cookies_never_reach_bundle_or_journal(tmp_path, target) -> None:
    run, _judgement, directory, state = _execute(tmp_path, target)
    assert len(state.store.seen) == 4  # two invitation tokens, two browser session cookies
    files = [path for path in directory.rglob("*") if path.is_file()]
    files.append(tmp_path / "runs" / "progress" / f"{run.run_id}.json")
    for path in files:
        payload = path.read_bytes()
        assert all(secret.encode() not in payload for secret in state.store.seen), path.name
    assert state.store._values == {}


@pytest.mark.parametrize("mutation", ["capture_bytes", "capture_record", "identifiers", "lanes"])
def test_resealed_fabricated_facts_fail_semantic_verification(tmp_path, target, mutation) -> None:
    _run, _judgement, directory, _ = _execute(tmp_path, target)
    if mutation == "capture_bytes":
        from engine.models import canonical_json_bytes, sha256_bytes

        payload = b"\x89PNG\r\n\x1a\nother"
        (directory / "n01-pc-capture.png").write_bytes(payload)
        manifest = _read(directory, "manifest.json")
        record = next(row for row in manifest["files"] if row["path"] == "n01-pc-capture.png")
        record.update(sha256=sha256_bytes(payload), size_bytes=len(payload))
        manifest["bundle_digest"] = sha256_bytes(
            canonical_json_bytes({k: v for k, v in manifest.items() if k != "bundle_digest"})
        )
        (directory / "manifest.json").write_bytes(canonical_json_bytes(manifest))
    elif mutation == "capture_record":
        data = _read(directory, "n01-measurements.json")
        data[1]["capture"]["sha256"] = "0" * 64
        reseal_file(directory, "n01-measurements.json", data)
    elif mutation == "identifiers":
        data = _read(directory, "n01-policy-identifiers.json")
        data[0]["stored"]["evidence_digest"] = "c" * 64
        reseal_file(directory, "n01-policy-identifiers.json", data)
    else:
        data = _read(directory, "n01-lanes.json")
        data[0]["step_reached"] = "error"
        reseal_file(directory, "n01-lanes.json", data)
    result = verify_bundle(directory)
    assert result["bundle_status"] == "INVALID"
    assert any(item.endswith(":semantic-evidence") for item in result["mismatched_files"])


def test_retest_child_keeps_parent_bytes(tmp_path, target) -> None:
    parent, _judgement, parent_dir, state = _execute(tmp_path, target)
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in parent_dir.iterdir()}
    child_id = uuid4()
    _parent_run, _digest, records = prepare_retest(
        parent_dir,
        child_run_id=child_id,
        child_target=target,
        child_scenario_version=SCENARIO.version,
        child_scenario_digest=SCENARIO.snapshot().digest,
        child_profile=SCENARIO.execution_profile,
        child_environment=spec009_environment(target),
        child_scenario_snapshot=SCENARIO.snapshot(),
    )
    child, _child_judgement, child_dir = state.executor.execute(
        ready(SCENARIO, target), parent_run_id=parent.run_id, retest_records=records, run_id=child_id
    )
    assert {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in parent_dir.iterdir()} == before
    assert child.parent_run_id == parent.run_id
    assert verify_bundle(child_dir)["bundle_status"] == "VERIFIED"


def test_v1_measurement_bundle_still_verifies_with_the_v2_code(tmp_path, target) -> None:
    """The first actual Run (48a70f5e) was sealed with v1 records; v2 code must re-judge them unchanged."""
    _run, judgement, directory, _ = _execute(tmp_path, target)
    records = _read(directory, "n01-measurements.json")
    assert all("measurement_version" not in record or record["measurement_version"] is None for record in records)
    # New code serializes the v2-only fields as null in a v1 record; the real first-Run bundle has no such keys.
    assert all(f.get("style_visible") is None for r in records for i in r["items"] for f in i["fragments"])
    assert _read(directory, "assertions.json")[0]["expected"]["flags"] == [
        "text_present", "in_viewport", "not_occluded", "no_horizontal_overflow"
    ]
    result = verify_bundle(directory)
    assert result["bundle_status"] == "VERIFIED" and result["mismatched_files"] == []
    assert judgement.verdict.value == "PASS"


def test_v2_measurement_flow_seals_and_verifies(tmp_path, target) -> None:
    _run, judgement, directory, _ = _execute(tmp_path, target, modes={"measurement_v2"})
    assert judgement.verdict.value == "PASS"
    assert {record["measurement_version"] for record in _read(directory, "n01-measurements.json")} == {2}
    assert _read(directory, "assertions.json")[0]["expected"]["flags"][-2:] == ["style_visible", "not_clipped"]
    assert verify_bundle(directory)["bundle_status"] == "VERIFIED"


def test_v2_hidden_notice_fails_the_mobile_lane(tmp_path, target) -> None:
    _run, judgement, directory, _ = _execute(tmp_path, target, modes={"measurement_v2", "hidden_notice_mobile"})
    assert _statuses(judgement) == {"N01-A1": "PASS", "N01-A2": "FAIL", "N01-A3": "PASS"}
    assert "style_visible" in judgement.assertion_results[1].detail
    assert verify_bundle(directory)["bundle_status"] == "VERIFIED"
