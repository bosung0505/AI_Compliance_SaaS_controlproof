"""Explicit N-02 causal graph builder; timestamps never create edges by themselves."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID, uuid5

from engine.adapters.base import AdapterResult
from engine.models import (
    CausalEdge,
    CausalEdgeStatus,
    CausalEvent,
    CausalEventKind,
    CausalRelation,
    ConsentPolicySnapshot,
    ConsentStateSnapshot,
    N02LaneId,
    ProcessingAttemptReceipt,
    ProtectedEffectSnapshot,
    ProtectedPathId,
    utcnow,
)

_EVENT_NAMESPACE = UUID("e8e17d6b-df7b-5308-8525-f5f3a54f0665")


class WhyYouCausalityAdapter:
    """Normalize explicit request, transaction, receipt and result identities."""

    def __init__(self) -> None:
        self._graphs: dict[
            tuple[str, str], tuple[tuple[CausalEvent, ...], tuple[CausalEdge, ...]]
        ] = {}

    def capture_normal_order(
        self,
        *,
        subject: Mapping[str, Any],
        policy: ConsentPolicySnapshot,
        consent_state: ConsentStateSnapshot,
        attempts: Sequence[ProcessingAttemptReceipt],
        effects: Sequence[ProtectedEffectSnapshot],
        receipts: Sequence[Mapping[str, Any]] = (),
    ) -> AdapterResult:
        run_id = UUID(str(subject["run_id"]))
        lane = N02LaneId(str(subject["lane_id"]))
        subject_ref = str(subject["subject_ref"])
        events: list[CausalEvent] = []
        edges: list[CausalEdge] = []

        policy_event = _event(
            run_id,
            lane,
            subject_ref,
            CausalEventKind.POLICY_RECEIVED,
            None,
            {"policy_version": policy.policy_version, "content_digest": policy.content_digest},
            policy.received_at,
            "HTTP",
            policy.source_ref,
        )
        events.append(policy_event)
        if not consent_state.consent_record_ids:
            return AdapterResult(False, "CAUSAL_CONSENT_COMMIT_MISSING")
        consent_event = _event(
            run_id,
            lane,
            subject_ref,
            CausalEventKind.CONSENT_COMMITTED,
            None,
            {
                "consent_record_id": str(consent_state.consent_record_ids[0]),
                "state_change_id": str(consent_state.consented_state_change_ids[0]),
                "outbox_event_id": str(consent_state.consent_completed_event_ids[0]),
            },
            None,
            "DATABASE_TRANSACTION",
            "whyyou:consent-transaction:v1",
        )
        events.append(consent_event)
        edges.append(
            _edge(
                consent_state,
                policy_event,
                consent_event,
                CausalRelation.PROGRAM_ORDER,
                ("consent:policy-identity-match",),
            )
        )

        effect_by_path = {item.path_id: item for item in effects}
        receipts_by_path: dict[ProtectedPathId, list[Mapping[str, Any]]] = {
            path: [] for path in ProtectedPathId
        }
        for receipt in receipts:
            try:
                receipts_by_path[ProtectedPathId(str(receipt["path_id"]))].append(receipt)
            except (KeyError, ValueError):
                continue

        for attempt in attempts:
            request = _event(
                run_id,
                lane,
                subject_ref,
                CausalEventKind.PROCESSING_REQUESTED,
                attempt.path_id,
                {"request_or_event_id": attempt.request_id},
                attempt.sent_at,
                attempt.entry_kind.value,
                attempt.source_ref,
            )
            events.append(request)
            edges.append(
                _edge(
                    consent_state,
                    consent_event,
                    request,
                    CausalRelation.PROGRAM_ORDER,
                    ("executor:durable-consent-gate",),
                )
            )
            path_receipts = receipts_by_path[attempt.path_id]
            effect = effect_by_path.get(attempt.path_id)
            starts = [
                item
                for item in path_receipts
                if str(item.get("boundary", ""))
                in {
                    "ANALYSIS_HANDLER_ENTERED",
                    "INTERVIEW_SESSION_CREATED",
                    "INTERVIEW_SESSION_STARTED",
                    "REPORT_HANDLER_ENTERED",
                }
            ]
            start_ids = list(effect.start_receipt_ids if effect else ())
            if starts:
                start_ids.extend(str(item["receipt_id"]) for item in starts)
            if not start_ids:
                continue
            start = _event(
                run_id,
                lane,
                subject_ref,
                CausalEventKind.PROCESSING_STARTED,
                attempt.path_id,
                {"receipt_id": min(start_ids)},
                None,
                "BOUNDARY_RECEIPT",
                f"whyyou:observer:{attempt.path_id.value.casefold()}",
            )
            events.append(start)
            edges.append(
                _edge(
                    consent_state,
                    request,
                    start,
                    CausalRelation.HANDLED,
                    (f"receipt:{start.domain_identity['receipt_id']}",),
                )
            )
            result_ids = list(effect.result_ids if effect else ())
            if attempt.path_id is ProtectedPathId.RECORDING:
                result_ids.extend(
                    str(item["receipt_id"])
                    for item in path_receipts
                    if item.get("boundary") == "RECORDING_CONFIRMED"
                )
            if not result_ids:
                continue
            result = _event(
                run_id,
                lane,
                subject_ref,
                CausalEventKind.RESULT_CREATED,
                attempt.path_id,
                {"result_id": min(result_ids)},
                None,
                "DURABLE_EFFECT",
                f"whyyou:effects:{attempt.path_id.value.casefold()}",
            )
            events.append(result)
            edges.append(
                _edge(
                    consent_state,
                    start,
                    result,
                    CausalRelation.PRODUCED,
                    (f"effect:{result.domain_identity['result_id']}",),
                )
            )
        self._graphs[(str(run_id), subject_ref)] = (tuple(events), tuple(edges))
        return AdapterResult(True, "CAUSAL_GRAPH_CAPTURED", {"event_count": len(events)})

    def read_graph(
        self, *, subject: Mapping[str, Any]
    ) -> tuple[tuple[CausalEvent, ...], tuple[CausalEdge, ...]] | AdapterResult:
        key = (str(UUID(str(subject["run_id"]))), str(subject["subject_ref"]))
        return self._graphs.get(key) or AdapterResult(False, "CAUSAL_SOURCE_UNAVAILABLE")


def _event(
    run_id: UUID,
    lane: N02LaneId,
    subject_ref: str,
    kind: CausalEventKind,
    path: ProtectedPathId | None,
    identity: dict[str, str],
    occurred_at,
    source_type: str,
    source_ref: str,
) -> CausalEvent:
    identity_text = ":".join(f"{key}={identity[key]}" for key in sorted(identity))
    event_id = uuid5(
        _EVENT_NAMESPACE,
        f"{run_id}:{lane.value}:{subject_ref}:{kind.value}:{path}:{identity_text}",
    )
    return CausalEvent(
        causal_event_id=event_id,
        kind=kind,
        run_id=run_id,
        lane_id=lane,
        subject_ref=subject_ref,
        path_id=path,
        domain_identity=identity,
        occurred_at=occurred_at,
        observed_at=utcnow(),
        source_type=source_type,
        source_ref=source_ref,
    )


def _edge(
    state: ConsentStateSnapshot,
    source: CausalEvent,
    target: CausalEvent,
    relation: CausalRelation,
    proof_refs: tuple[str, ...],
) -> CausalEdge:
    return CausalEdge(
        run_id=state.run_id,
        lane_id=state.lane_id,
        subject_ref=state.subject_ref,
        from_event_id=source.causal_event_id,
        to_event_id=target.causal_event_id,
        relation=relation,
        proof_refs=proof_refs,
        status=CausalEdgeStatus.PROVEN,
    )
