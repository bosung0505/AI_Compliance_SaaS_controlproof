from uuid import uuid4

from engine.retest import prepare_retest
from engine.runner import RunOrchestrator
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters


def test_parent_pass_retest_never_requires_artificial_defect_variant(tmp_path):
    adapters, _ = make_adapters()
    scenario = load("scenarios/H-03.yaml")
    runner = RunOrchestrator(scenario, adapters, tmp_path, clock=FakeClock())
    parent, judgement, bundle = runner.execute(runner.preflight("whyyou-local"))
    child_id = uuid4()
    readiness = runner.preflight("whyyou-local")
    _, _, records = prepare_retest(
        bundle,
        child_run_id=child_id,
        child_target=readiness.target_snapshot,
        child_scenario_version=scenario.version,
        child_scenario_digest=scenario.snapshot().digest,
    )
    assert judgement.verdict.value == "PASS"
    assert records["diff"]["target"]["changed_fields"] == []
    assert "defect" not in str(records).casefold()
    assert records["link"]["parent_run_id"] == str(parent.run_id)
