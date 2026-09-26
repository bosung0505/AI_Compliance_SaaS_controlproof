import pytest

from engine.models import RunState, Verdict
from engine.runner import RunOrchestrator
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters


def execute(tmp_path, **options):
    adapters, _ = make_adapters(**options)
    runner = RunOrchestrator(load("scenarios/H-03.yaml"), adapters, tmp_path, clock=FakeClock())
    readiness = runner.preflight("whyyou-local")
    return runner.execute(readiness)


def test_safe_fixture_passes(tmp_path):
    run, judgement, _ = execute(tmp_path)
    assert run.state is RunState.COMPLETED
    assert judgement.verdict is Verdict.PASS
    assert all(result.status.value == "PASS" for result in judgement.assertion_results)


@pytest.mark.parametrize(
    "options,assertion",
    [
        ({"status_class": "queued_only"}, "H03-A2"),
        ({"decision_accepted": True}, "H03-A3"),
        ({"reason_present": False}, "H03-A3"),
        ({"mutate": True}, "H03-A4"),
    ],
)
def test_direct_protection_failures_are_fail(tmp_path, options, assertion):
    _, judgement, _ = execute(tmp_path, **options)
    assert judgement.verdict is Verdict.FAIL
    failed = {
        item.assertion_id for item in judgement.assertion_results if item.status.value == "FAIL"
    }
    assert assertion in failed


def test_effect_not_confirmed_is_inconclusive(tmp_path):
    _, judgement, _ = execute(tmp_path, effect=False)
    assert judgement.verdict is Verdict.INCONCLUSIVE


def test_report_processing_failure_is_finding_not_restore_failure(tmp_path):
    run, judgement, _ = execute(tmp_path, processing="FAILED")
    assert run.state is RunState.COMPLETED
    assert judgement.verdict is Verdict.PASS
    assert any(item.code == "REPORT_PROCESSING_RECOVERY_INCOMPLETE" for item in judgement.findings)
