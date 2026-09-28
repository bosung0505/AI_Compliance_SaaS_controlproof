from __future__ import annotations

from engine.executors.h03_dlq import H03DlqExecutor
from engine.models import AssertionStatus, DecisionPathId, ReadinessStatus
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters
from tests.fixtures.spec002 import RUN_ID


def test_two_operations_expand_to_three_isolated_decision_cases(tmp_path):
    scenario = load("scenarios/H-03-DLQ.yaml")
    adapters, _browser = make_adapters()
    result = H03DlqExecutor(scenario, adapters, tmp_path, clock=FakeClock()).collect_us2(
        run_id=RUN_ID
    )

    assert {item.operation_id for item in result.decision_capabilities} == {
        "recordHumanFinalDecision",
        "moveApplicantsToRecruitingStage",
    }
    assert [item.path_id for item in result.decision_cases] == list(DecisionPathId)
    assert len({item.logical_operation_id for item in result.decision_cases}) == 3
    for case in result.decision_cases:
        assert case.pre_effects[0].logical_operation_id == case.logical_operation_id
        assert case.post_effects[0].logical_operation_id == case.logical_operation_id
        assert case.reset.ok is True
    assert result.decision_assertion.status is AssertionStatus.PASS


def test_one_accepted_batch_path_fails_h03_a7_without_contaminating_the_next_case(tmp_path):
    scenario = load("scenarios/H-03-DLQ.yaml")
    adapters, _browser = make_adapters(
        accepted_decision_paths={DecisionPathId.BATCH_MOVE_FINAL_ACCEPT}
    )
    result = H03DlqExecutor(scenario, adapters, tmp_path, clock=FakeClock()).collect_us2(
        run_id=RUN_ID
    )

    by_path = {case.path_id: case for case in result.decision_cases}
    assert by_path[DecisionPathId.BATCH_MOVE_FINAL_ACCEPT].attempt.data["accepted"] is True
    assert by_path[DecisionPathId.BATCH_MOVE_FINAL_REJECT].attempt.data["accepted"] is False
    assert all(case.reset.ok for case in result.decision_cases)
    assert result.decision_assertion.status is AssertionStatus.FAIL


def test_preflight_is_ready_after_canonical_sealed_execution_is_composed(tmp_path):
    scenario = load("scenarios/H-03-DLQ.yaml")
    adapters, _browser = make_adapters()
    readiness = H03DlqExecutor(scenario, adapters, tmp_path, clock=FakeClock()).preflight(
        "whyyou-local"
    )

    assert readiness.status is ReadinessStatus.READY
    assert readiness.operator_action is None
