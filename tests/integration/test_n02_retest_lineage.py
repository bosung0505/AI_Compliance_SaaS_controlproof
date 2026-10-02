"""N-02 child Run keeps the parent sealed and compares actual new lane facts."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256
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


def _confirmed_cleanup(tmp_path, parent):
    evidence = tmp_path / "cleanup-evidence.json"
    lanes = json.loads((tmp_path / str(parent.run_id) / "subjects.json").read_text(encoding="utf-8"))
    fault = next(row for row in lanes if row["lane_id"] == "CONSENT_FAULT_RECOVERY")
    evidence.write_text(
        json.dumps({
            "schema_version": "controlproof.n02-cleanup-evidence.v1",
            "parent_run_id": str(parent.run_id),
            "target_id": parent.target_id,
            "subject_ref": "n02-consent-order",
            "lane_subject_ref": fault["subject_ref"],
            "invitation_id": fault["invitation_id"],
            "applicant_id": fault["applicant_id"],
            "safe_state_read_only": True,
            "captured_at": datetime.now(UTC).isoformat(),
            "findings": {
                "invitation": [["identity_verified", 1]],
                **{key: 0 for key in (
                    "consent_records", "active_consents", "consented_transitions",
                    "consent_completed_events", "all_invitation_events", "upload_intents",
                    "submissions", "analyses", "interview_strategies",
                )},
            },
            "fault_files_exist": {"marker": False, "consumed_token": False, "fault_receipt": False},
        }),
        encoding="utf-8",
    )
    blocks = RestoreBlockStore(tmp_path)
    blocks.block_run_id(parent.target_id, "n02-consent-order", parent.run_id)
    blocks.confirm_cleanup(
        parent.target_id,
        "n02-consent-order",
        evidence_sha256=sha256(evidence.read_bytes()).hexdigest(),
        target_safe=True,
    )
    return evidence


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
    with pytest.raises(RetestError, match="cleanup"):
        _prepare(parent_bundle, _runner(tmp_path), uuid4())


def test_n02_retest_accepts_confirmed_cleanup_without_changing_parent(tmp_path):
    parent_runner = _runner(tmp_path, n02=FakeN02Adapters(restore_succeeded=False))
    parent, _, parent_bundle = parent_runner.execute(parent_runner.preflight("whyyou-local"))
    original = (parent_bundle / "manifest.json").read_bytes()
    evidence = _confirmed_cleanup(tmp_path, parent)
    child_runner = _runner(tmp_path)

    inherited, digest, records = prepare_retest(
        parent_bundle,
        child_run_id=uuid4(),
        child_target=child_runner.preflight("whyyou-local").target_snapshot,
        child_scenario_version=child_runner.scenario.version,
        child_scenario_digest=child_runner.scenario.snapshot().digest,
        child_profile=child_runner.scenario.execution_profile,
        child_fault_variant=child_runner.scenario.fault_variant,
        child_environment=_environment(child_runner),
        cleanup_evidence=evidence,
    )

    assert inherited.run_id == parent.run_id
    assert inherited.manual_cleanup_required is True
    assert records["link"]["cleanup_confirmation"]["evidence_sha256"] == sha256(evidence.read_bytes()).hexdigest()
    assert (parent_bundle / "manifest.json").read_bytes() == original
    assert_parent_unchanged(parent_bundle, digest)


@pytest.mark.parametrize("invalid", [
    "missing_evidence", "missing_record", "wrong_digest", "wrong_run", "wrong_target",
    "wrong_subject", "bad_timestamp", "unsafe_evidence", "new_block",
])
def test_n02_retest_rejects_unverified_or_reblocked_cleanup(tmp_path, invalid):
    parent_runner = _runner(tmp_path, n02=FakeN02Adapters(restore_succeeded=False))
    parent, _, parent_bundle = parent_runner.execute(parent_runner.preflight("whyyou-local"))
    evidence = _confirmed_cleanup(tmp_path, parent)
    record_path = tmp_path / "blocks" / "maintenance" / f"{parent.run_id}.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    if invalid == "wrong_digest":
        record["evidence_sha256"] = "0" * 64
    elif invalid == "missing_record":
        record_path.unlink()
    elif invalid == "wrong_run":
        record["blocked_run_id"] = str(uuid4())
    elif invalid == "wrong_target":
        record["target_id"] = "another-target"
    elif invalid == "wrong_subject":
        record["subject_ref"] = "another-subject"
    elif invalid == "bad_timestamp":
        record["confirmed_at"] = parent.ended_at.isoformat()
    elif invalid == "unsafe_evidence":
        payload = json.loads(evidence.read_text(encoding="utf-8"))
        payload["findings"]["consent_records"] = 1
        evidence.write_text(json.dumps(payload), encoding="utf-8")
        record["evidence_sha256"] = sha256(evidence.read_bytes()).hexdigest()
    elif invalid == "new_block":
        RestoreBlockStore(tmp_path).block_run_id(parent.target_id, "n02-consent-order", uuid4())
    if invalid in {"wrong_digest", "wrong_run", "wrong_target", "wrong_subject", "bad_timestamp", "unsafe_evidence"}:
        record_path.write_text(json.dumps(record), encoding="utf-8")
    child_runner = _runner(tmp_path)

    with pytest.raises(RetestError, match="cleanup"):
        prepare_retest(
            parent_bundle,
            child_run_id=uuid4(),
            child_target=child_runner.preflight("whyyou-local").target_snapshot,
            child_scenario_version=child_runner.scenario.version,
            child_scenario_digest=child_runner.scenario.snapshot().digest,
            child_profile=child_runner.scenario.execution_profile,
            child_fault_variant=child_runner.scenario.fault_variant,
            child_environment=_environment(child_runner),
            cleanup_evidence=None if invalid == "missing_evidence" else evidence,
        )
