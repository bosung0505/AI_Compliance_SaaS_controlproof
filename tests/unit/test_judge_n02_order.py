from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

from engine.judges.n02 import N02NormalOrderCase, judge_n02_normal_order
from engine.models import (
    AssertionStatus,
    CausalEdge,
    CausalEdgeStatus,
    CausalEventKind,
    CausalRelation,
    InconclusiveReason,
    N02LaneId,
    Phase,
    Presence,
    ProtectedPathId,
)
from tests.fixtures.fake_adapters import FakeN02Adapters


def _case(*, fake: FakeN02Adapters | None = None) -> N02NormalOrderCase:
    fake = fake or FakeN02Adapters()
    run_id = uuid4()
    lanes = fake.seed_lanes(run_id=str(run_id))
    lane = next(item for item in lanes if item.lane_id is N02LaneId.NORMAL_ORDER)
    subject = lane.model_dump(mode="json")
    policy = fake.read_policy(subject=subject)
    fake.commit(subject=subject, policy=policy, request_id="request", trace_id="trace")
    state = fake.read_state(subject=subject, phase=Phase.INJECTED.value, step_id="state")
    attempts = tuple(fake.attempt(path_id=path.value, subject=subject) for path in ProtectedPathId)
    effects = tuple(
        fake.read_effects(
            path_id=path.value,
            subject=subject,
            phase=Phase.INJECTED.value,
            step_id=f"effects-{path.value}",
        )
        for path in ProtectedPathId
    )
    fake.capture_normal_order(
        subject=subject,
        policy=policy,
        consent_state=state,
        attempts=attempts,
        effects=effects,
    )
    events, edges = fake.read_graph(subject=subject)
    return N02NormalOrderCase(policy, state, attempts, effects, events, edges)


def test_a5_passes_policy_identity_and_all_three_explicit_chains() -> None:
    result = judge_n02_normal_order(_case())
    assert result.status is AssertionStatus.PASS
    assert result.actual["causal_order"] == "PROVEN"


def test_equal_event_times_are_accepted_when_edges_are_proven() -> None:
    case = _case()
    same = case.policy.received_at
    events = tuple(item.model_copy(update={"occurred_at": same}) for item in case.events)
    assert judge_n02_normal_order(replace(case, events=events)).status is AssertionStatus.PASS


def test_notification_delivery_is_not_a_required_event() -> None:
    case = _case()
    assert all("NOTIFICATION" not in item.kind.value for item in case.events)
    assert judge_n02_normal_order(case).status is AssertionStatus.PASS


def test_unavailable_state_after_timeout_is_inconclusive() -> None:
    case = _case()
    state = case.consent_state.model_copy(
        update={
            "source_status": Presence.UNAVAILABLE,
            "source_error_code": "DB_TIMEOUT",
            "consent_record_ids": (),
            "active_consent_count": 0,
            "consented_state_change_ids": (),
            "consent_completed_event_ids": (),
        }
    )
    result = judge_n02_normal_order(replace(case, consent_state=state))
    assert result.status is AssertionStatus.INCONCLUSIVE
    assert result.reason_code is InconclusiveReason.INSUFFICIENT_EVIDENCE


def test_policy_digest_mismatch_is_direct_fail() -> None:
    case = _case()
    state = case.consent_state.model_copy(
        update={"consent_content_digests": ("9" * 64,)}
    )
    assert judge_n02_normal_order(replace(case, consent_state=state)).status is AssertionStatus.FAIL


def test_direct_processing_before_consent_edge_is_fail() -> None:
    case = _case()
    consent = next(item for item in case.events if item.kind is CausalEventKind.CONSENT_COMMITTED)
    request = next(item for item in case.events if item.kind is CausalEventKind.PROCESSING_REQUESTED)
    reverse = CausalEdge(
        run_id=case.consent_state.run_id,
        lane_id=case.consent_state.lane_id,
        subject_ref=case.consent_state.subject_ref,
        from_event_id=request.causal_event_id,
        to_event_id=consent.causal_event_id,
        relation=CausalRelation.PROGRAM_ORDER,
        proof_refs=("fixture:direct-violation",),
        status=CausalEdgeStatus.PROVEN,
    )
    result = judge_n02_normal_order(replace(case, edges=(*case.edges, reverse)))
    assert result.status is AssertionStatus.FAIL


def test_missing_edge_and_same_fact_conflict_are_distinct_inconclusive_reasons() -> None:
    case = _case()
    missing = judge_n02_normal_order(replace(case, edges=case.edges[:-1]))
    conflicted = judge_n02_normal_order(
        replace(
            case,
            edges=(
                case.edges[0].model_copy(update={"status": CausalEdgeStatus.CONFLICTING}),
                *case.edges[1:],
            ),
        )
    )
    assert missing.reason_code is InconclusiveReason.INSUFFICIENT_EVIDENCE
    assert conflicted.reason_code is InconclusiveReason.EVIDENCE_CONFLICT
