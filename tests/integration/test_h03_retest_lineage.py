from uuid import uuid4

from engine.evidence import verify_bundle
from engine.retest import assert_parent_unchanged, prepare_retest
from engine.runner import RunOrchestrator
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters


def test_fail_to_pass_retest_keeps_independent_queryable_bundles(tmp_path):
    scenario = load("scenarios/H-03.yaml")
    failing_adapters, _ = make_adapters(status_class="queued_only")
    parent_runner = RunOrchestrator(scenario, failing_adapters, tmp_path, clock=FakeClock())
    parent, parent_judgement, parent_bundle = parent_runner.execute(
        parent_runner.preflight("whyyou-local")
    )
    child_id = uuid4()
    passing_adapters, _ = make_adapters()
    child_runner = RunOrchestrator(scenario, passing_adapters, tmp_path, clock=FakeClock())
    readiness = child_runner.preflight("whyyou-local")
    _, parent_digest, records = prepare_retest(
        parent_bundle,
        child_run_id=child_id,
        child_target=readiness.target_snapshot,
        child_scenario_version=scenario.version,
        child_scenario_digest=scenario.snapshot().digest,
    )
    child, child_judgement, child_bundle = child_runner.execute(
        readiness,
        parent_run_id=parent.run_id,
        retest_records=records,
        run_id=child_id,
    )
    assert parent_judgement.verdict.value == "FAIL"
    assert child_judgement.verdict.value == "PASS"
    assert child.parent_run_id == parent.run_id
    assert verify_bundle(parent_bundle)["bundle_status"] == "VERIFIED"
    assert verify_bundle(child_bundle)["bundle_status"] == "VERIFIED"
    assert_parent_unchanged(parent_bundle, parent_digest)
