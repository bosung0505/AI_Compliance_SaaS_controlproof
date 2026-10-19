"""T009a — N-03 executor over fakes: flow, sealed evidence, restore block, retest child, redaction."""

from __future__ import annotations

import hashlib
import json
from uuid import uuid4

import pytest

from engine.evidence import verify_bundle
from engine.executors.n03 import LINKS, UNVERIFIED_SCOPE, N03Executor
from engine.n03_evidence import REQUIRED_FILES
from engine.retest import prepare_retest
from engine.scenario import load
from tests.fixtures.fake_spec009 import (
    make_spec009_adapters,
    ready,
    spec009_environment,
    spec009_target,
)
from tests.fixtures.n02_review_bundle import reseal_file

SCENARIO = load("scenarios/N-03.yaml")


@pytest.fixture
def target(target_snapshot):
    return spec009_target(target_snapshot)


def _execute(tmp_path, target, **options):
    adapters, backend, store = make_spec009_adapters(tmp_path, target, **options)
    executor = N03Executor(SCENARIO, adapters, tmp_path / "runs")
    run, judgement, directory = executor.execute(ready(SCENARIO, target))
    return run, judgement, directory, SimpleState(adapters, backend, store, executor)


class SimpleState:
    def __init__(self, adapters, backend, store, executor) -> None:
        self.adapters, self.backend, self.store, self.executor = adapters, backend, store, executor


def _read(directory, name):
    return json.loads((directory / name).read_text(encoding="utf-8"))


def _statuses(judgement):
    return {item.assertion_id: item.status.value for item in judgement.assertion_results}


def test_pass_flow_seals_a_verified_bundle(tmp_path, target) -> None:
    run, judgement, directory, state = _execute(tmp_path, target)
    assert run.state.value == "COMPLETED" and not run.manual_cleanup_required
    assert judgement.verdict.value == "PASS", judgement.assertion_results
    assert _statuses(judgement) == {"N03-A1": "PASS", "N03-A2": "PASS", "N03-A3": "PASS"}
    names = {path.name for path in directory.iterdir()}
    assert REQUIRED_FILES <= names and "manifest.json" in names
    result = verify_bundle(directory)
    assert result["bundle_status"] == "VERIFIED", result["mismatched_files"]
    assert result["mismatched_files"] == [] and state.executor.verification["bundle_status"] == "VERIFIED"
    manifest = _read(directory, "manifest.json")
    assert manifest["profile_contract"] == "controlproof.bundle-profile.spec009.v1"
    assert set(manifest["required_evidence"]) == set(LINKS)
    attempt = _read(directory, "n03-stale-attempt.json")
    assert attempt["submitted"] != attempt["current"]
    assert attempt["response_status"] == 422 and attempt["adapter_code"] == "CONSENT_POLICY_MISMATCH"
    latest = _read(directory, "n03-latest-commit.json")
    assert latest["stored"] == {"policy_version": latest["reread"]["version"], "evidence_digest": latest["reread"]["digest"]}
    assert (tmp_path / "runs" / "progress" / f"{run.run_id}.json").is_file()
    assert run.seed_kind == "n03-session-lanes-v1" and run.fault_kind == "n03-stale-policy-submission-v1"
    assert run.model_fixture_id == "n02-analysis-v1"


def test_judgement_scope_and_scope_file_are_fixed(tmp_path, target) -> None:
    run, judgement, directory, _ = _execute(tmp_path, target)
    expected = ("AWS_NOT_RUN", "N03_U1_POLICY_SWAP_INJECTION", "N03_U2_NEAR_SWAP_SUBMISSION", "N03_U3_ANALYSIS_POLICY_ATTRIBUTION")
    assert UNVERIFIED_SCOPE == expected
    assert judgement.unverified_scope == expected and run.unverified_scope == expected
    scope = _read(directory, "n03-scope.json")
    assert scope["unverified_scope_items"] == [item.model_dump(mode="json") for item in SCENARIO.unverified_scope_items]
    assert scope["limitations"] == [item.model_dump(mode="json") for item in SCENARIO.limitations]
    assert [item["id"] for item in scope["common_limitations"]] == ["LOCAL_EMULATED", "SYNTHETIC_DATA", "EXTERNAL_AI_BLOCKED"]
    assert scope["target_access"] == ["API"]


def test_stale_submission_stored_is_a_sealed_fail(tmp_path, target) -> None:
    run, judgement, directory, _ = _execute(tmp_path, target, modes={"stale_accepted"})
    assert run.state.value == "COMPLETED"
    assert judgement.verdict.value == "FAIL"
    assert _statuses(judgement)["N03-A1"] == "FAIL"
    assert _read(directory, "n03-stale-attempt.json")["response_class"] == "2xx"
    assert verify_bundle(directory)["bundle_status"] == "VERIFIED"


@pytest.mark.parametrize(
    ("mode", "assertion"),
    [("policy_unavailable", "N03-A1"), ("stale_transport", "N03-A1"), ("state_unavailable", "N03-A3")],
)
def test_adapter_failures_are_sealed_as_inconclusive(tmp_path, target, mode, assertion) -> None:
    run, judgement, directory, _ = _execute(tmp_path, target, modes={mode})
    assert run.state.value == "COMPLETED"
    assert judgement.verdict.value == "INCONCLUSIVE" and judgement.reason_code.value == "INSUFFICIENT_EVIDENCE"
    result = next(item for item in judgement.assertion_results if item.assertion_id == assertion)
    assert result.status.value == "INCONCLUSIVE" and result.reason_code.value == "INSUFFICIENT_EVIDENCE"
    assert verify_bundle(directory)["bundle_status"] == "VERIFIED"
    if mode == "stale_transport":
        assert _read(directory, "n03-stale-attempt.json")["durable_state"] == "UNKNOWN"


@pytest.mark.parametrize("teardown", ["RESIDUE", "ERROR"])
def test_failed_teardown_blocks_the_target(tmp_path, target, teardown) -> None:
    run, judgement, directory, state = _execute(tmp_path, target, teardown=teardown)
    assert run.state.value == "RESTORE_FAILED" and run.manual_cleanup_required
    assert judgement.verdict.value == "INCONCLUSIVE"
    assert verify_bundle(directory)["bundle_status"] == "VERIFIED"
    assert (tmp_path / "runs" / "blocks" / "whyyou-local--n03-stale-consent.json").is_file()
    with pytest.raises(RuntimeError, match="N03_RESTORE_BLOCKED"):
        state.executor.execute(ready(SCENARIO, target))


def test_seed_failure_aborts_before_writes(tmp_path, target) -> None:
    adapters, _backend, _store = make_spec009_adapters(tmp_path, target, modes={"seed_fails"})
    with pytest.raises(RuntimeError, match="N03_SEED_FAILED:SPEC009_SEED_WRITE_FAILED"):
        N03Executor(SCENARIO, adapters, tmp_path / "runs").execute(ready(SCENARIO, target))
    assert adapters.spec009_seed.teardowns == []


def test_not_ready_readiness_is_refused(tmp_path, target) -> None:
    adapters, _backend, _store = make_spec009_adapters(tmp_path, target)
    blocked = ready(SCENARIO, target).model_copy(update={"status": "RUNNER_NOT_READY"})
    with pytest.raises(RuntimeError, match="N03_NOT_READY"):
        N03Executor(SCENARIO, adapters, tmp_path / "runs").execute(blocked)


def test_raw_cookies_never_reach_bundle_or_journal(tmp_path, target) -> None:
    run, _judgement, directory, state = _execute(tmp_path, target)
    assert len(state.store.seen) == 2
    files = [path for path in directory.rglob("*") if path.is_file()]
    files.append(tmp_path / "runs" / "progress" / f"{run.run_id}.json")
    for path in files:
        payload = path.read_bytes()
        assert all(secret.encode() not in payload for secret in state.store.seen), path.name
    assert state.store._values == {}


@pytest.mark.parametrize("mutation", ["assertions", "attempt", "recovery", "scope"])
def test_resealed_fabricated_facts_fail_semantic_verification(tmp_path, target, mutation) -> None:
    _run, _judgement, directory, _ = _execute(tmp_path, target)
    if mutation == "assertions":
        data = _read(directory, "assertions.json")
        data[0]["status"] = "FAIL"
        reseal_file(directory, "assertions.json", data)
    elif mutation == "attempt":
        data = _read(directory, "n03-stale-attempt.json")
        data["submitted"] = dict(data["current"])
        reseal_file(directory, "n03-stale-attempt.json", data)
    elif mutation == "recovery":
        data = _read(directory, "recovery.json")
        data["owned_residue_counts"]["outbox_events"] = 1
        reseal_file(directory, "recovery.json", data)
    else:
        data = _read(directory, "n03-scope.json")
        data["unverified_scope_items"] = []
        reseal_file(directory, "n03-scope.json", data)
    result = verify_bundle(directory)
    assert result["bundle_status"] == "INVALID"
    assert any(item.endswith(":semantic-evidence") for item in result["mismatched_files"])


def _hashes(directory):
    return {
        path.relative_to(directory).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in directory.rglob("*")
        if path.is_file()
    }


def test_retest_child_keeps_parent_bytes(tmp_path, target) -> None:
    parent, _judgement, parent_dir, state = _execute(tmp_path, target)
    before = _hashes(parent_dir)
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
    child, child_judgement, child_dir = state.executor.execute(
        ready(SCENARIO, target), parent_run_id=parent.run_id, retest_records=records, run_id=child_id
    )
    assert _hashes(parent_dir) == before
    assert child.parent_run_id == parent.run_id and child.run_id == child_id
    assert child_judgement.verdict.value == "PASS"
    assert (child_dir / "retest-link.json").is_file() and verify_bundle(child_dir)["bundle_status"] == "VERIFIED"


def test_restore_failed_parent_cannot_be_retested(tmp_path, target) -> None:
    _run, _judgement, parent_dir, _ = _execute(tmp_path, target, teardown="RESIDUE")
    from engine.retest import RetestError

    with pytest.raises(RetestError):
        prepare_retest(
            parent_dir,
            child_run_id=uuid4(),
            child_target=target,
            child_scenario_version=SCENARIO.version,
            child_scenario_digest=SCENARIO.snapshot().digest,
            child_profile=SCENARIO.execution_profile,
            child_environment=spec009_environment(target),
        )


def test_dirty_child_environment_is_refused(tmp_path, target) -> None:
    _run, _judgement, parent_dir, _ = _execute(tmp_path, target)
    from engine.retest import RetestError

    dirty = spec009_environment(target).model_dump(mode="json", exclude={"snapshot_digest"})
    dirty["controlproof_commit"] = {"commit_sha": "a" * 40, "dirty": True, "diff_digest": "e" * 64}
    from engine.models import TargetEnvironmentSnapshot

    with pytest.raises((RetestError, ValueError)):
        prepare_retest(
            parent_dir,
            child_run_id=uuid4(),
            child_target=target,
            child_scenario_version=SCENARIO.version,
            child_scenario_digest=SCENARIO.snapshot().digest,
            child_profile=SCENARIO.execution_profile,
            child_environment=TargetEnvironmentSnapshot.model_validate(dirty),
        )
