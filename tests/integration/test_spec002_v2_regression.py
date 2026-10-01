from engine.evidence import verify_bundle
from engine.models import Verdict
from engine.runner import build_profile_runner
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters


def test_spec002_e03_before_still_executes_and_verifies(tmp_path) -> None:
    adapters, _ = make_adapters()
    runner = build_profile_runner(
        load("scenarios/E-03-BEFORE.yaml"), adapters, tmp_path, clock=FakeClock()
    )
    run, judgement, bundle = runner.execute(runner.preflight("whyyou-local"))
    assert run.execution_profile.value == "E03_BEFORE_V2"
    assert judgement.verdict in {Verdict.PASS, Verdict.FAIL, Verdict.INCONCLUSIVE}
    assert verify_bundle(bundle)["bundle_status"] == "VERIFIED"
