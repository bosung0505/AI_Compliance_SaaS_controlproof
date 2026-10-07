"""T054 — E-02 journey on the deterministic fake (US3, FR-031, FR-032, FR-041, SC-002).

RED until T056 (scenario), T057 (executor) and T059 (scoring-source preflight).
"""

from __future__ import annotations

import json

import pytest

from engine.models import AssertionStatus, RunState, Verdict
from engine.runner import build_profile_runner
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters
from tests.fixtures.fake_spec004 import FakeSpec004Adapters, use_spec004_fixture


def _runner(tmp_path, fake):
    adapters, _ = make_adapters(spec004=fake)
    use_spec004_fixture(adapters)
    return build_profile_runner(load("scenarios/E-02.yaml"), adapters, tmp_path, clock=FakeClock())


def _run(tmp_path, fake):
    runner = _runner(tmp_path, fake)
    readiness = runner.preflight("whyyou-local")
    assert readiness.status.value == "READY", readiness
    run, judgement, bundle = runner.execute(readiness)
    return runner, run, judgement, bundle


def _results(judgement):
    return {item.assertion_id: item for item in judgement.assertion_results}


def test_freeze_journey_passes_and_binds_the_second_applicant_to_v2(tmp_path) -> None:
    fake = FakeSpec004Adapters()
    _, run, judgement, bundle = _run(tmp_path, fake)
    results = _results(judgement)
    for assertion_id in ("E02-A1", "E02-A2", "E02-A3"):
        assert results[assertion_id].status is AssertionStatus.PASS, results[assertion_id].detail
    assert judgement.verdict is Verdict.PASS and run.state is RunState.COMPLETED
    assert run.scoring_rule_source_digest
    calls = fake.calls
    assert calls.index("request:E02_FIRST_APPLICANT") < calls.index("seed:E02_SECOND_APPLICANT")
    versions = json.loads((bundle / "criteria-versions.json").read_text(encoding="utf-8"))
    first, second = fake.lanes["E02_FIRST_APPLICANT"], fake.lanes["E02_SECOND_APPLICANT"]
    assert str(first.competency_model_version_id) == versions["v1"]["competency_model_version_id"]
    assert str(second.competency_model_version_id) == versions["v2"]["competency_model_version_id"]
    recompute = json.loads((bundle / "recompute.json").read_text(encoding="utf-8"))
    assert len(recompute["records"]) == 2
    assert fake.torn_down


@pytest.mark.parametrize(
    "option,assertion_id,status",
    [
        ({"report_mutates_after_change": True}, "E02-A2", AssertionStatus.FAIL),
        ({"stored_overall_offset": 1}, "E02-A3", AssertionStatus.FAIL),
        ({"api_overall_offset": 1}, "E02-A3", AssertionStatus.FAIL),
        ({"second_version_binding_wrong": True}, "E02-A2", AssertionStatus.INCONCLUSIVE),
    ],
)
def test_single_wrong_fact_maps_to_its_assertion(tmp_path, option, assertion_id, status) -> None:
    _, _, judgement, _ = _run(tmp_path, FakeSpec004Adapters(**option))
    assert _results(judgement)[assertion_id].status is status


@pytest.mark.parametrize("option", ["other_positions_changed", "teardown_fails"])
def test_unsafe_teardown_is_restore_failed_and_blocks(tmp_path, option) -> None:
    fake = FakeSpec004Adapters(**{option: True})
    runner, run, judgement, _ = _run(tmp_path, fake)
    assert run.state is RunState.RESTORE_FAILED
    assert judgement.verdict is Verdict.INCONCLUSIVE
    with pytest.raises(RuntimeError, match="blocked"):
        runner.execute(runner.preflight("whyyou-local"))


def test_scoring_source_drift_is_not_ready_before_any_write(tmp_path) -> None:
    fake = FakeSpec004Adapters(scoring_source_drift=True)
    readiness = _runner(tmp_path, fake).preflight("whyyou-local")
    assert readiness.status.value == "RUNNER_NOT_READY"
    assert "SCORING_RULE_SOURCE_DRIFT" in readiness.operator_action
    assert fake.calls == []
