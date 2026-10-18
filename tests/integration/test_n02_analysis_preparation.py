"""Stage-1 synthetic validation only; these are not actual WhyYou Run results."""

import json
from uuid import uuid4

import pytest

from engine.adapters.base import CapabilityProbeResult
from engine.evidence import verify_bundle
from engine.models import (
    SPEC003_UNVERIFIED_SCOPE,
    ReadinessStatus,
    RunState,
    TargetEnvironmentSnapshot,
    Verdict,
)
from engine.readiness import evaluate_readiness
from engine.retest import RetestError, assert_parent_unchanged, prepare_retest
from engine.runner import build_profile_runner
from engine.scenario import load, load_all
from tests.fixtures.fake_adapters import FakeClock, make_adapters
from tests.fixtures.n02_review_bundle import reseal_file

PATH = "scenarios/_N-02-analysis.yaml"
FIXTURE = "n02-analysis-v1"
DIGEST = "092de5950a39ba3a7255c8696ffb073cddc65cda4615237044e3d910e32f9828"


def test_analysis_scenario_keeps_all_original_rules_and_is_explicit_only():
    legacy, analysis = load("scenarios/N-02.yaml"), load(PATH)
    assert analysis.version == "1.1.0"
    assert analysis.allowed_model_fixtures == {FIXTURE: DIGEST}
    for field in ("assertions", "steps", "required_capabilities", "required_evidence", "lanes"):
        assert getattr(analysis, field) == getattr(legacy, field)
    assert all(item.version != "1.1.0" for item in load_all() if item.scenario_id == "N-02")


@pytest.mark.parametrize(
    "fixture,digest,ready",
    [
        (FIXTURE, DIGEST, True),
        (FIXTURE, "f" * 64, False),
        (
            "h03-report-v1",
            "ce09b95403b34e1390502c90f5c5edc518ddf65d38c8ce881617a37cac6d16b1",
            False,
        ),
    ],
)
def test_analysis_readiness_rejects_wrong_fixture_or_digest(
    target_snapshot, fixture, digest, ready
):
    scenario = load(PATH)
    target = type(target_snapshot).model_validate(
        target_snapshot.model_dump(exclude={"target_version"})
        | {"model_fixture_id": fixture, "model_fixture_digest": digest}
    )
    result = evaluate_readiness(
        scenario,
        target_id="whyyou-local",
        registrations=scenario.required_capabilities,
        probe_results=[
            CapabilityProbeResult(key, ReadinessStatus.READY, "synthetic")
            for key in scenario.required_capabilities
        ],
        target_feature_exists=True,
        target_snapshot=target,
    )
    assert (result.status is ReadinessStatus.READY) is ready


def test_new_fixture_synthetic_executor_seals_and_verifies_recovered_evidence(tmp_path):
    adapters, _ = make_adapters()
    adapters.target.snapshot = type(adapters.target.snapshot).model_validate(
        adapters.target.snapshot.model_dump(exclude={"target_version"})
        | {"model_fixture_id": FIXTURE, "model_fixture_digest": DIGEST}
    )
    runner = build_profile_runner(load(PATH), adapters, tmp_path, clock=FakeClock())
    run, judgement, bundle = runner.execute(runner.preflight("whyyou-local"))
    assert run.state is RunState.COMPLETED
    assert judgement.verdict is Verdict.PASS
    assert run.model_fixture_id == FIXTURE
    assert verify_bundle(bundle)["bundle_status"] == "VERIFIED"
    assert (bundle / "causal-events.jsonl").read_text(encoding="utf-8")


@pytest.mark.parametrize("changed_rule", [False, True])
def test_fixture_only_revision_can_link_to_legacy_parent_but_rule_changes_cannot(
    tmp_path, changed_rule
):
    adapters, _ = make_adapters()
    parent_runner = build_profile_runner(
        load("scenarios/N-02.yaml"), adapters, tmp_path, clock=FakeClock()
    )
    parent, _, parent_bundle = parent_runner.execute(parent_runner.preflight("whyyou-local"))
    scenario = load(PATH)
    if changed_rule:
        scenario = scenario.model_copy(update={"title": "different definition"})
    adapters, _ = make_adapters()
    adapters.target.snapshot = type(adapters.target.snapshot).model_validate(
        adapters.target.snapshot.model_dump(exclude={"target_version"})
        | {"model_fixture_id": FIXTURE, "model_fixture_digest": DIGEST}
    )
    child_runner = build_profile_runner(scenario, adapters, tmp_path, clock=FakeClock())
    child_id = uuid4()
    environment = adapters.environment.capture_environment()
    environment = TargetEnvironmentSnapshot.model_validate(
        environment.model_dump(exclude={"snapshot_digest"})
        | {"unverified_scope": sorted(SPEC003_UNVERIFIED_SCOPE)}
    )
    kwargs = {
        "child_run_id": child_id,
        "child_target": adapters.target.snapshot,
        "child_scenario_version": scenario.version,
        "child_scenario_digest": scenario.snapshot().digest,
        "child_profile": scenario.execution_profile,
        "child_environment": environment,
        "child_scenario_snapshot": scenario.snapshot(),
    }
    if changed_rule:
        with pytest.raises(RetestError, match="fixture-only"):
            prepare_retest(parent_bundle, **kwargs)
        return
    inherited, digest, records = prepare_retest(parent_bundle, **kwargs)
    child, _, bundle = child_runner.execute(
        child_runner.preflight("whyyou-local"),
        parent_run_id=inherited.run_id,
        retest_records=records,
        run_id=child_id,
    )
    assert child.parent_run_id == parent.run_id
    assert child.scenario_digest != parent.scenario_digest
    assert verify_bundle(bundle)["bundle_status"] == "VERIFIED"
    assert_parent_unchanged(parent_bundle, digest)
    comparison = json.loads((bundle / "retest-diff.json").read_text(encoding="utf-8"))
    comparison["scenario"]["changed"] = False
    reseal_file(bundle, "retest-diff.json", comparison)
    verification = verify_bundle(bundle)
    assert verification["bundle_status"] == "INVALID"
    assert "n02-retest:fixture-only-revision" in verification["mismatched_files"]
