"""T070 — Spec 004 retest lineage (FR-050, FR-052, SC-005).

RED until T071. A child inherits the parent's scenario and profile, creates its own lanes/position/versions under a
new Run ID, records target/fixture/scoring-source differences, never edits the parent, and is refused while a
restore block is unresolved.
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest

from engine.evidence import verify_bundle
from engine.models import SPEC004_UNVERIFIED_SCOPE, TargetEnvironmentSnapshot, TargetSnapshot
from engine.retest import RetestError, assert_parent_unchanged, prepare_retest
from engine.runner import build_profile_runner
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters
from tests.fixtures.fake_spec004 import FakeSpec004Adapters, use_spec004_fixture

PARENT_FAULT = {"E-01": {}, "E-02": {"report_mutates_after_change": True}}
CHILD_FIX = {"E-01": {"removal_indicator": "score_null"}, "E-02": {}}


def _runner(root, scenario, options, *, commit=None):
    adapters, _ = make_adapters(spec004=FakeSpec004Adapters(**options))
    use_spec004_fixture(adapters)
    if commit:
        original = adapters.target.snapshot
        adapters.target.snapshot = TargetSnapshot.model_validate(
            original.model_dump(mode="json", exclude={"target_version"}) | {"git_commit_sha": commit}
        )
    return build_profile_runner(load(f"scenarios/{scenario}.yaml"), adapters, root, clock=FakeClock())


def _environment(runner):
    raw = runner.adapters.environment.capture_environment()
    return TargetEnvironmentSnapshot.model_validate(
        raw.model_dump(mode="json", exclude={"snapshot_digest"})
        | {"unverified_scope": sorted(SPEC004_UNVERIFIED_SCOPE)}
    )


def _retest(root, parent_bundle, scenario, *, commit="b" * 40):
    child = _runner(root, scenario, CHILD_FIX[scenario], commit=commit)
    readiness = child.preflight("whyyou-local")
    child_id = uuid4()
    parent_run, parent_digest, records = prepare_retest(
        parent_bundle,
        child_run_id=child_id,
        child_target=readiness.target_snapshot,
        child_scenario_version=child.scenario.version,
        child_scenario_digest=child.scenario.snapshot().digest,
        child_profile=child.scenario.execution_profile,
        child_environment=_environment(child),
    )
    run, judgement, bundle = child.execute(
        readiness, parent_run_id=parent_run.run_id, retest_records=records, run_id=child_id
    )
    assert_parent_unchanged(parent_bundle, parent_digest)
    return parent_run, run, judgement, bundle


@pytest.mark.parametrize("scenario", ["E-01", "E-02"])
def test_child_is_independent_and_records_differences(tmp_path, scenario) -> None:
    parent = _runner(tmp_path, scenario, PARENT_FAULT[scenario])
    parent_run, parent_judgement, parent_bundle = parent.execute(parent.preflight("whyyou-local"))
    assert parent_judgement.verdict.value == "FAIL"
    before = (parent_bundle / "manifest.json").read_bytes()
    _, child_run, child_judgement, child_bundle = _retest(tmp_path, parent_bundle, scenario)
    assert child_judgement.verdict.value == "PASS"
    assert child_run.parent_run_id == parent_run.run_id and child_run.run_id != parent_run.run_id
    assert (parent_bundle / "manifest.json").read_bytes() == before
    parent_lanes = json.loads((parent_bundle / "spec004-lanes.json").read_text(encoding="utf-8"))["lanes"]
    child_lanes = json.loads((child_bundle / "spec004-lanes.json").read_text(encoding="utf-8"))["lanes"]
    assert not {lane["invitation_id"] for lane in parent_lanes} & {lane["invitation_id"] for lane in child_lanes}
    assert not {lane["position_id"] for lane in parent_lanes} & {lane["position_id"] for lane in child_lanes}
    diff = json.loads((child_bundle / "retest-diff.json").read_text(encoding="utf-8"))
    assert diff["execution_profile"]["changed"] is False
    assert any(item["path"].endswith("git_commit_sha") for item in diff["target"]["changed_fields"])
    assert diff["spec004"]["model_fixture"]["changed"] is False
    assert diff["spec004"]["scoring_rule_source"]["changed"] is False
    assert diff["spec004"]["lanes"]["reused_identities"] == []
    link = json.loads((child_bundle / "retest-link.json").read_text(encoding="utf-8"))
    assert link["parent_bundle_digest"] == json.loads(before)["bundle_digest"]
    assert verify_bundle(child_bundle)["bundle_status"] == "VERIFIED"


def test_unresolved_block_refuses_the_retest(tmp_path) -> None:
    parent = _runner(tmp_path, "E-01", {"removal_indicator": "score_null", "restore_mismatch": True})
    run, _, parent_bundle = parent.execute(parent.preflight("whyyou-local"))
    assert run.state.value == "RESTORE_FAILED"
    with pytest.raises(RetestError, match="block"):
        _retest(tmp_path, parent_bundle, "E-01")


def test_child_must_inherit_the_parent_profile(tmp_path) -> None:
    parent = _runner(tmp_path, "E-01", {})
    _, _, parent_bundle = parent.execute(parent.preflight("whyyou-local"))
    other = _runner(tmp_path, "E-02", {})
    readiness = other.preflight("whyyou-local")
    with pytest.raises(RetestError, match="profile"):
        prepare_retest(
            parent_bundle,
            child_run_id=uuid4(),
            child_target=readiness.target_snapshot,
            child_scenario_version=other.scenario.version,
            child_scenario_digest=other.scenario.snapshot().digest,
            child_profile=other.scenario.execution_profile,
            child_environment=_environment(other),
        )
