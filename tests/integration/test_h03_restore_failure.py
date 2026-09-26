import pytest

from engine.models import RunState, Verdict
from engine.runner import RunOrchestrator
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters


def test_restore_failure_is_inconclusive_and_blocks_followup(tmp_path):
    adapters, _ = make_adapters(restore=False)
    runner = RunOrchestrator(load("scenarios/H-03.yaml"), adapters, tmp_path, clock=FakeClock())
    readiness = runner.preflight("whyyou-local")
    run, judgement, _ = runner.execute(readiness)
    assert run.state is RunState.RESTORE_FAILED
    assert judgement.verdict is Verdict.INCONCLUSIVE
    assert runner.blocks.blocked("whyyou-local", "candidate-01")
    with pytest.raises(RuntimeError, match="blocked"):
        runner.execute(readiness)
