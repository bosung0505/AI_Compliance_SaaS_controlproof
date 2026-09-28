from __future__ import annotations

from engine.executors.e03_before import E03BeforeExecutor
from engine.models import AssertionStatus, DecisionPathId, Presence
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters
from tests.fixtures.spec002 import RUN_ID


def test_recovered_before_journey_replays_one_human_decision_without_changing_lineage(
    tmp_path,
):
    scenario = load("scenarios/E-03-BEFORE.yaml")
    adapters, _browser = make_adapters(decision_path_accepted=True)

    result = E03BeforeExecutor(
        scenario,
        adapters,
        tmp_path,
        clock=FakeClock(),
    ).collect_us5(run_id=RUN_ID)

    judged = {item.assertion_id: item for item in result.assertions}
    assert tuple(judged) == (
        "E03-A1",
        "E03-A2",
        "E03-A3",
        "E03-A4",
        "E03-A7",
        "E03-A8",
    )
    assert all(item.status is AssertionStatus.PASS for item in judged.values())
    assert result.pending_assertion_ids == ()
    assert result.decision_path is DecisionPathId.FINAL_DECISION
    assert result.first_decision.data["logical_decision_id"] == result.replay_decision.data[
        "logical_decision_id"
    ]
    assert result.replay_comparison.data["request_equivalent"] is True
    assert result.first_decision_effects[0].state_digest == result.replay_decision_effects[
        0
    ].state_digest
    assert result.dlq_presence is Presence.PRESENT
    assert result.recovered_effects[0].effects["logical_report_ids"] == ["report-01"]
