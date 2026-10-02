"""N-02 child Run keeps the parent sealed and compares actual new lane facts."""

from __future__ import annotations

import json
from dataclasses import replace
from uuid import uuid4

import pytest

from engine.lifecycle import RestoreBlockStore
from engine.models import (
    SPEC003_UNVERIFIED_SCOPE,
    ExecutionProfile,
    ProtectedPathId,
    TargetEnvironmentSnapshot,
    TargetSnapshot,
)
from engine.retest import RetestError, assert_parent_unchanged, prepare_retest
from engine.runner import build_profile_runner
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, FakeN02Adapters, make_adapters


def _runner(root, *, n02=None, target_commit=None):
    adapters, _ = make_adapters()
    fake = n02 or FakeN02Adapters()
    if target_commit:
        original = adapters.target.snapshot
        adapters.target.snapshot = TargetSnapshot.model_validate(
            original.model_dump(mode="json", exclude={"target_version"})
            | {"git_commit_sha": target_commit}
        )
    adapters = replace(
        adapters,
        n02_seed=fake,
        n02_consent=fake,
        n02_processing=fake,
        n02_causality=fake,
        n02_fault=fake,
        n02_observer=fake,
    )
    return build_profile_runner(load("scenarios/N-02.yaml"), adapters, root, clock=FakeClock())


def _environment(runner):
    raw = runner.adapters.environment.capture_environment()
    return TargetEnvironmentSnapshot.model_validate(
        raw.model_dump(mode="json", exclude={"snapshot_digest"})
        | {"unverified_scope": sorted(SPEC003_UNVERIFIED_SCOPE)}
    )


def _prepare(parent_bundle, child_runner, child_id):
    return prepare_retest(
        parent_bundle,
        child_run_id=child_id,
        child_target=child_runner.preflight("whyyou-local").target_snapshot,
        child_scenario_version=child_runner.scenario.version,
        child_scenario_digest=child_runner.scenario.snapshot().digest,
        child_profile=child_runner.scenario.execution_profile,
        child_fault_variant=child_runner.scenario.fault_variant,
        child_environment=_environment(child_runner),
    )


def test_n02_retest_inherits_profile_and_creates_fresh_six_subjects(tmp_path):
    parent_runner = _runner(tmp_path)
    parent, _, parent_bundle = parent_runner.execute(parent_runner.preflight("whyyou-local"))
    child_runner = _runner(tmp_path, target_commit="b" * 40)
    child_id = uuid4()
    inherited, parent_digest, records = _prepare(parent_bundle, child_runner, child_id)

    child, _, child_bundle = child_runner.execute(
        child_runner.preflight("whyyou-local"),
        parent_run_id=inherited.run_id,
        retest_records=records,
        run_id=child_id,
    )
    parent_lanes = json.loads((parent_bundle / "n02-lanes.json").read_text(encoding="utf-8"))["lanes"]
    child_lanes = json.loads((child_bundle / "n02-lanes.json").read_text(encoding="utf-8"))["lanes"]
    diff = json.loads((child_bundle / "retest-diff.json").read_text(encoding="utf-8"))

    assert child.run_id != parent.run_id
    assert child.parent_run_id == parent.run_id
    assert child.execution_profile is parent.execution_profile is ExecutionProfile.N02_CONSENT_ORDER_V1
    assert child.scenario_digest == parent.scenario_digest
    assert len(parent_lanes) == len(child_lanes) == 6
    assert {row["invitation_id"] for row in parent_lanes}.isdisjoint(
        {row["invitation_id"] for row in child_lanes}
    )
    assert {row["applicant_id"] for row in parent_lanes}.isdisjoint(
        {row["applicant_id"] for row in child_lanes}
    )
    assert {item["path"] for item in diff["target"]["changed_fields"]} == {"git_commit_sha"}
    assert diff["execution_profile"]["changed"] is False
    assert set(diff["n02"]) == {"path_capability", "policy", "lane_fixtures"}
    assert len(diff["n02"]["lane_fixtures"]["lanes"]) == 6
    assert_parent_unchanged(parent_bundle, parent_digest)


def test_n02_retest_refuses_unresolved_cleanup_before_child_seed(tmp_path):
    parent_runner = _runner(tmp_path)
    parent, _, parent_bundle = parent_runner.execute(parent_runner.preflight("whyyou-local"))
    RestoreBlockStore(tmp_path).block_run_id("whyyou-local", "n02-consent-order", parent.run_id)
    child_runner = _runner(tmp_path)

    with pytest.raises(RetestError, match="cleanup"):
        _prepare(parent_bundle, child_runner, uuid4())
    assert len(list(tmp_path.glob("*/manifest.json"))) == 1


def test_n02_retest_records_actual_policy_path_and_fixture_changes(tmp_path):
    class ChangedN02(FakeN02Adapters):
        def paths(self):
            return tuple(
                item.model_copy(update={"entry_boundary": "createInterviewSessionV2"})
                if item.path_id is ProtectedPathId.RECORDING else item
                for item in super().paths()
            )

        def read_policy(self, *, subject):
            return super().read_policy(subject=subject).model_copy(update={
                "policy_version": "fixture-v2",
                "content_digest": "e" * 64,
            })

        def seed_lanes(self, *, run_id):
            return tuple(
                lane.model_copy(update={"fixture_digest": "b" * 64})
                if lane.fixture_digest else lane
                for lane in super().seed_lanes(run_id=run_id)
            )

    parent_runner = _runner(tmp_path)
    parent, _, parent_bundle = parent_runner.execute(parent_runner.preflight("whyyou-local"))
    child_runner = _runner(tmp_path, n02=ChangedN02())
    child_id = uuid4()
    inherited, _, records = _prepare(parent_bundle, child_runner, child_id)
    _, _, child_bundle = child_runner.execute(
        child_runner.preflight("whyyou-local"),
        parent_run_id=inherited.run_id,
        retest_records=records,
        run_id=child_id,
    )
    diff = json.loads((child_bundle / "retest-diff.json").read_text(encoding="utf-8"))["n02"]

    assert diff["path_capability"]["changed"] is True
    assert diff["policy"]["changed"] is True
    assert diff["policy"]["before"]["content_digest"] != diff["policy"]["after"]["content_digest"]
    assert diff["lane_fixtures"]["changed"] is True
    assert {row["lane_id"] for row in diff["lane_fixtures"]["lanes"] if row["changed"]} == {
        "RECORDING_BOUNDARY_PROBE", "ASSESSMENT_BOUNDARY_PROBE"
    }
    assert parent.parent_run_id is None


def test_n02_retest_rejects_restore_failed_parent(tmp_path):
    parent_runner = _runner(tmp_path, n02=FakeN02Adapters(restore_succeeded=False))
    parent, _, parent_bundle = parent_runner.execute(parent_runner.preflight("whyyou-local"))
    assert parent.manual_cleanup_required is True
    with pytest.raises(RetestError, match="safe cleanup"):
        _prepare(parent_bundle, _runner(tmp_path), uuid4())
