from __future__ import annotations

from engine.adapters.base import AdapterResult
from engine.judges.h03_dlq import judge_h03_decisions
from engine.models import (
    AssertionStatus,
    DecisionPathCapability,
    DecisionPathId,
    InconclusiveReason,
    Presence,
)
from tests.fixtures.spec002 import decision_effect


def _capabilities():
    commit = "b" * 40
    accept = "00000000-0000-7000-8000-000000000201"
    reject = "00000000-0000-7000-8000-000000000202"
    return (
        DecisionPathCapability(
            path_id=DecisionPathId.FINAL_DECISION,
            operation_id="recordHumanFinalDecision",
            target_stage_id=accept,
            target_stage_name="최종합격",
            source_commit=commit,
        ),
        DecisionPathCapability(
            path_id=DecisionPathId.BATCH_MOVE_FINAL_ACCEPT,
            operation_id="moveApplicantsToRecruitingStage",
            target_stage_id=accept,
            target_stage_name="최종합격",
            source_commit=commit,
        ),
        DecisionPathCapability(
            path_id=DecisionPathId.BATCH_MOVE_FINAL_REJECT,
            operation_id="moveApplicantsToRecruitingStage",
            target_stage_id=reject,
            target_stage_name="불합격",
            source_commit=commit,
        ),
    )


def _case(path_id, *, accepted=False, reason_present=True, pre=None, post=None, ok=True):
    return {
        "path_id": path_id,
        "attempt": AdapterResult(
            ok,
            "DECISION_ATTEMPTED" if ok else "DECISION_ACCESS_FAILED",
            {
                "accepted": accepted,
                "reason_present": reason_present,
                "reason_code": "REPORT_NOT_AVAILABLE" if reason_present else None,
            },
        ),
        "pre_effects": (pre or decision_effect(),),
        "post_effects": (post or decision_effect(),),
    }


def test_h03_a7_passes_only_when_all_three_paths_explicitly_refuse_without_effects():
    capabilities = _capabilities()
    result = judge_h03_decisions(
        capabilities=capabilities,
        cases=tuple(_case(capability.path_id) for capability in capabilities),
    )
    assert result.assertion_id == "H03-A7"
    assert result.status is AssertionStatus.PASS


def test_missing_path_registration_blocks_pass_as_inconclusive():
    capabilities = _capabilities()[:2]
    result = judge_h03_decisions(
        capabilities=capabilities,
        cases=tuple(_case(capability.path_id) for capability in capabilities),
    )
    assert result.status is AssertionStatus.INCONCLUSIVE
    assert result.reason_code is InconclusiveReason.INSUFFICIENT_EVIDENCE


def test_accepted_batch_bypass_or_any_partial_state_write_is_a_direct_fail():
    capabilities = _capabilities()
    accepted = tuple(
        _case(capability.path_id, accepted=capability.path_id is DecisionPathId.BATCH_MOVE_FINAL_ACCEPT)
        for capability in capabilities
    )
    assert judge_h03_decisions(capabilities=capabilities, cases=accepted).status is AssertionStatus.FAIL

    changed = decision_effect(
        state_digest="f" * 64,
        effects={
            "stage_assignment_ids": ["assignment-02"],
            "stage_id": "00000000-0000-7000-8000-000000000202",
            "pipeline_row_version": 2,
            "invitation_status": "reviewed",
            "human_review_ids": ["review-02"],
            "human_review_actor_types": ["COMPANY_USER"],
            "final_decision_audit_ids": ["audit-02"],
        },
    )
    cases = tuple(
        _case(
            capability.path_id,
            post=changed if capability.path_id is DecisionPathId.FINAL_DECISION else None,
        )
        for capability in capabilities
    )
    assert judge_h03_decisions(capabilities=capabilities, cases=cases).status is AssertionStatus.FAIL


def test_automatic_system_decision_is_fail_even_when_another_path_is_unavailable():
    capabilities = _capabilities()
    system_effect = decision_effect(
        state_digest="a" * 64,
        effects={
            "stage_assignment_ids": ["assignment-system"],
            "stage_id": "00000000-0000-7000-8000-000000000201",
            "pipeline_row_version": 2,
            "invitation_status": "reviewed",
            "human_review_ids": ["review-system"],
            "human_review_actor_types": [],
            "decision_actor_types": ["SYSTEM"],
            "final_decision_audit_ids": ["audit-system"],
        },
    )
    cases = (
        _case(DecisionPathId.FINAL_DECISION, post=system_effect),
        _case(DecisionPathId.BATCH_MOVE_FINAL_ACCEPT, ok=False),
        _case(DecisionPathId.BATCH_MOVE_FINAL_REJECT),
    )
    result = judge_h03_decisions(capabilities=capabilities, cases=cases)
    assert result.status is AssertionStatus.FAIL


def test_access_loss_without_a_direct_risk_is_inconclusive():
    capabilities = _capabilities()
    unavailable = decision_effect(
        effects={},
        source_status=Presence.UNAVAILABLE,
        source_error_code="DECISION_EFFECT_ACCESS_FAILED",
    )
    cases = (
        _case(DecisionPathId.FINAL_DECISION, pre=unavailable, post=unavailable),
        _case(DecisionPathId.BATCH_MOVE_FINAL_ACCEPT),
        _case(DecisionPathId.BATCH_MOVE_FINAL_REJECT),
    )
    result = judge_h03_decisions(capabilities=capabilities, cases=cases)
    assert result.status is AssertionStatus.INCONCLUSIVE
    assert result.reason_code is InconclusiveReason.ACCESS_LIMITED


def test_non_explicit_rejection_is_insufficient_not_a_product_fail():
    capabilities = _capabilities()
    cases = tuple(
        _case(
            capability.path_id,
            reason_present=capability.path_id is not DecisionPathId.FINAL_DECISION,
        )
        for capability in capabilities
    )
    result = judge_h03_decisions(capabilities=capabilities, cases=cases)
    assert result.status is AssertionStatus.INCONCLUSIVE
    assert result.reason_code is InconclusiveReason.INSUFFICIENT_EVIDENCE
