import pytest

from engine.evidence import verify_bundle
from engine.models import ExecutionProfile, Verdict
from engine.runner import (
    ExecutionProfileRegistry,
    UnregisteredExecutionProfile,
    build_profile_runner,
)
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters


def test_v1_profile_still_executes_after_v2_foundation_is_loaded(tmp_path):
    scenario = load("scenarios/H-03.yaml")
    adapters, _browser = make_adapters()
    runner = build_profile_runner(scenario, adapters, tmp_path, clock=FakeClock())
    readiness = runner.preflight("whyyou-local")
    _run, judgement, bundle = runner.execute(readiness)
    assert judgement.verdict is Verdict.PASS
    assert verify_bundle(bundle)["bundle_status"] == "VERIFIED"


def test_unregistered_v2_profile_is_refused_before_run_creation(tmp_path):
    scenario = load("scenarios/H-03.yaml").model_copy(
        update={"execution_profile": ExecutionProfile.E03_BEFORE_V2}
    )
    adapters, _browser = make_adapters()
    registry = ExecutionProfileRegistry()
    existing = set(tmp_path.iterdir())
    with pytest.raises(UnregisteredExecutionProfile, match="E03_BEFORE_V2"):
        registry.build(scenario, adapters, tmp_path, clock=FakeClock())
    assert set(tmp_path.iterdir()) == existing
