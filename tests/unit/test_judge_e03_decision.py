from __future__ import annotations

from engine.adapters.base import AdapterResult
from engine.judges.e03 import judge_e03_decision_replay
from engine.models import AssertionStatus, InconclusiveReason, Presence
from tests.fixtures.spec002 import decision_effect

TARGET_STAGE_ID = "00000000-0000-7000-8000-000000000201"


def _comparison(ok=True):
    return AdapterResult(
        ok,
        "DECISION_REPLAY_MATCHED" if ok else "DECISION_REPLAY_NON_EQUIVALENT",
        {
            "request_equivalent": ok,
            "logical_decision_id": "00000000-0000-7000-8000-000000000301",
            "idempotency_key_digest": "f" * 64,
            "target_stage_id": TARGET_STAGE_ID,
            "target_idempotency_confirmed": False,
            "first_accepted": True,
            "replay_accepted": True,
        },
    )


def _effects(**updates):
    values = {
        "stage_assignment_ids": [f"invitation:{TARGET_STAGE_ID}:2"],
        "stage_id": TARGET_STAGE_ID,
        "pipeline_row_version": 2,
        "invitation_status": "reviewed",
        "human_review_ids": ["review-01"],
        "human_review_actor_types": ["COMPANY_USER"],
        "decision_actor_types": ["COMPANY_USER"],
        "final_decision_actor_types": ["COMPANY_USER"],
        "final_decision_audit_ids": ["audit-01"],
        "final_decision_request_ids": ["request-01"],
        "pipeline_move_audit_ids": [],
    }
    values.update(updates)
    return decision_effect(effects=values)


def _judge(first=None, replay=None, comparison=None):
    return judge_e03_decision_replay(
        replay_comparison=comparison or _comparison(),
        first_effects=(first or _effects(),),
        replay_effects=(replay or _effects(),),
        target_stage_id=TARGET_STAGE_ID,
    )


def test_one_complete_human_decision_effect_set_survives_same_key_replay():
    result = _judge()
    assert result.assertion_id == "E03-A7"
    assert result.status is AssertionStatus.PASS


def test_missing_or_duplicate_required_effect_is_a_direct_failure():
    variants = (
        _effects(stage_assignment_ids=[]),
        _effects(human_review_ids=[]),
        _effects(final_decision_audit_ids=[]),
        _effects(human_review_ids=["review-01", "review-02"]),
        _effects(final_decision_audit_ids=["audit-01", "audit-02"]),
    )
    for replay in variants:
        assert _judge(replay=replay).status is AssertionStatus.FAIL


def test_contradictory_invitation_stage_or_wrong_actor_fails():
    assert _judge(replay=_effects(invitation_status="completed")).status is AssertionStatus.FAIL
    assert _judge(replay=_effects(stage_id="00000000-0000-7000-8000-000000000999")).status is AssertionStatus.FAIL
    assert _judge(
        replay=_effects(human_review_actor_types=["SYSTEM"])
    ).status is AssertionStatus.FAIL
    assert _judge(
        replay=_effects(final_decision_actor_types=["AI"])
    ).status is AssertionStatus.FAIL


def test_changed_effect_digest_after_replay_fails_even_if_each_snapshot_looks_complete():
    replay = _effects(
        stage_assignment_ids=[f"invitation:{TARGET_STAGE_ID}:3"],
        pipeline_row_version=3,
        human_review_ids=["review-02"],
        final_decision_audit_ids=["audit-02"],
        final_decision_request_ids=["request-02"],
        state_digest="d" * 64,
    )
    assert _judge(replay=replay).status is AssertionStatus.FAIL


def test_inaccessible_effects_are_inconclusive_not_a_product_failure():
    unavailable = decision_effect(
        effects={},
        source_status=Presence.UNAVAILABLE,
        source_error_code="DECISION_EFFECT_ACCESS_FAILED",
    )
    result = _judge(replay=unavailable)
    assert result.status is AssertionStatus.INCONCLUSIVE
    assert result.reason_code is InconclusiveReason.ACCESS_LIMITED


def test_ai_score_is_not_an_input_to_human_decision_idempotency():
    first = _effects(ai_score=99)
    replay = _effects(ai_score=1)
    replay = replay.model_copy(update={"state_digest": first.state_digest})
    result = _judge(first=first, replay=replay)
    assert result.status is AssertionStatus.PASS
