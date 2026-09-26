from engine.models import ComparatorKind
from engine.scenario import load


def test_h03_exact_shape_and_timing():
    scenario = load("scenarios/H-03.yaml")
    assert [item.assertion_id for item in scenario.assertions] == [f"H03-A{i}" for i in range(1, 7)]
    assert [item.evidence_id for item in scenario.required_evidence] == [
        f"EV-{i:02d}" for i in range(1, 10)
    ]
    assert scenario.timing_policy.poll_seconds == 2
    assert scenario.timing_policy.injected_deadline_seconds == 30
    assert scenario.timing_policy.automatic_decision_window_seconds == 10
    assert scenario.timing_policy.environment_restore_deadline_seconds == 120
    assert scenario.restore_policy.report_processing_result_field == "report.processing_recovery"
    assert all(
        policy.kind is ComparatorKind.EXACT for policy in scenario.observation_comparators.values()
    )
