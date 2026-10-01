from __future__ import annotations

from uuid import uuid4

from engine.adapters.whyyou.causality import WhyYouCausalityAdapter
from engine.models import CausalEventKind, CausalRelation, N02LaneId, Phase, ProtectedPathId
from tests.fixtures.fake_adapters import FakeN02Adapters


def _normal_facts():
    run_id = uuid4()
    fake = FakeN02Adapters()
    lanes = fake.seed_lanes(run_id=str(run_id))
    lane = next(item for item in lanes if item.lane_id is N02LaneId.NORMAL_ORDER)
    subject = lane.model_dump(mode="json")
    policy = fake.read_policy(subject=subject)
    fake.commit(subject=subject, policy=policy, request_id="request-1", trace_id="trace-1")
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
    return subject, policy, state, attempts, effects


def test_causal_graph_uses_explicit_transaction_request_receipt_and_result_edges() -> None:
    subject, policy, state, attempts, effects = _normal_facts()
    adapter = WhyYouCausalityAdapter()
    captured = adapter.capture_normal_order(
        subject=subject,
        policy=policy,
        consent_state=state,
        attempts=attempts,
        effects=effects,
    )
    events, edges = adapter.read_graph(subject=subject)
    assert captured.ok
    assert sum(item.kind is CausalEventKind.PROCESSING_REQUESTED for item in events) == 3
    assert sum(item.kind is CausalEventKind.PROCESSING_STARTED for item in events) == 3
    assert sum(item.kind is CausalEventKind.RESULT_CREATED for item in events) == 3
    assert {item.relation for item in edges} >= {
        CausalRelation.PROGRAM_ORDER,
        CausalRelation.HANDLED,
        CausalRelation.PRODUCED,
    }
    consent = next(item for item in events if item.kind is CausalEventKind.CONSENT_COMMITTED)
    assert set(consent.domain_identity) == {
        "consent_record_id",
        "state_change_id",
        "outbox_event_id",
    }


def test_equal_timestamps_do_not_replace_or_invalidate_explicit_edges() -> None:
    subject, policy, state, attempts, effects = _normal_facts()
    adapter = WhyYouCausalityAdapter()
    adapter.capture_normal_order(
        subject=subject,
        policy=policy,
        consent_state=state,
        attempts=attempts,
        effects=effects,
    )
    events, edges = adapter.read_graph(subject=subject)
    assert len({item.occurred_at for item in events if item.occurred_at is not None}) <= 2
    assert all(item.proof_refs for item in edges)


def test_missing_receipt_does_not_invent_start_or_result_from_time() -> None:
    subject, policy, state, attempts, effects = _normal_facts()
    missing = tuple(
        item.model_copy(update={"start_receipt_ids": (), "result_ids": ()})
        if item.path_id is ProtectedPathId.RECORDING
        else item
        for item in effects
    )
    adapter = WhyYouCausalityAdapter()
    adapter.capture_normal_order(
        subject=subject,
        policy=policy,
        consent_state=state,
        attempts=attempts,
        effects=missing,
    )
    events, _ = adapter.read_graph(subject=subject)
    assert not any(
        item.path_id is ProtectedPathId.RECORDING
        and item.kind in {CausalEventKind.PROCESSING_STARTED, CausalEventKind.RESULT_CREATED}
        for item in events
    )
