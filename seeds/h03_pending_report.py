"""Deterministic H-03 fixture: completed interview, final media, no report/event/decision."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from seeds.state_seed import ApplicantSpec, Fixture, apply, build_fixture, sid, teardown


@dataclass(frozen=True, slots=True)
class PendingReportSeed:
    fixture: Fixture
    subject_ref: str

    @property
    def correlation(self) -> dict[str, str]:
        return self.fixture.correlation


def build_pending_report_fixture(
    label: str,
    *,
    subject_ref: str = "candidate-01",
    company_id: UUID | None = None,
    reviewer_id: UUID | None = None,
) -> PendingReportSeed:
    fixture = deepcopy(
        build_fixture(
            label,
            [ApplicantSpec(ref=subject_ref, scored_axes=(), evidence_count=0)],
            company_id=company_id,
            reviewer_id=reviewer_id,
        )
    )
    fixture.rows["report"] = []
    fixture.rows["report_item"] = []
    fixture.rows["evidence"] = []
    fixture.correlation.pop(f"report_id:{subject_ref}", None)
    stages = fixture.rows["recruiting_stage"]
    position_id = fixture.rows["position"][0]["position_id"]
    company = fixture.rows["position"][0]["company_id"]
    final_accept_stage_id = sid(label, "stage/final-accept")
    final_reject_stage_id = sid(label, "stage/final-reject")
    stages.extend(
        (
            {
                "company_id": company,
                "recruiting_stage_id": final_accept_stage_id,
                "position_id": position_id,
                "name": "최종합격",
                "sort_order": 3,
                "row_version": 1,
            },
            {
                "company_id": company,
                "recruiting_stage_id": final_reject_stage_id,
                "position_id": position_id,
                "name": "불합격",
                "sort_order": 4,
                "row_version": 1,
            },
        )
    )
    fixture.correlation["final_accept_stage_id"] = str(final_accept_stage_id)
    fixture.correlation["final_reject_stage_id"] = str(final_reject_stage_id)
    session = fixture.rows["interview_session"][0]
    invitation = fixture.rows["invitation"][0]
    fixture.correlation[f"interview_session_id:{subject_ref}"] = str(
        session["interview_session_id"]
    )
    fixture.correlation[f"invitation_id:{subject_ref}"] = str(invitation["invitation_id"])
    fixture.correlation["seed_correlation_id"] = f"cp-{label}"
    for asset in fixture.rows["recording_asset"]:
        asset["asset_type"] = "final_video"
    return PendingReportSeed(fixture=fixture, subject_ref=subject_ref)


def check_pending_invariants(seed: PendingReportSeed) -> list[str]:
    fixture = seed.fixture
    problems: list[str] = []
    if fixture.of("report") or fixture.of("report_item") or fixture.of("evidence"):
        problems.append("pending-report seed must not contain report data")
    if len(fixture.of("interview_session")) != 1:
        problems.append("pending-report seed requires exactly one interview session")
    if any(row["status"] != "completed" for row in fixture.of("invitation")):
        problems.append("invitation must be completed")
    if not fixture.of("recording_asset") or any(
        row["asset_type"] != "final_video" or row["status"] != "ready"
        for row in fixture.of("recording_asset")
    ):
        problems.append("final ready video is required")
    if not fixture.of("interview_turn") or any(
        row["status"] != "final" for row in fixture.of("interview_turn")
    ):
        problems.append("all interview turns must be final")
    if "report_generation_event_id" in fixture.correlation:
        problems.append("report event must not exist before trigger")
    stage_names = {str(row["name"]) for row in fixture.of("recruiting_stage")}
    if not {"최종합격", "불합격"}.issubset(stage_names):
        problems.append("pending-report seed requires both canonical final stages")
    return problems


def apply_pending(connection, seed: PendingReportSeed) -> None:
    problems = check_pending_invariants(seed)
    if problems:
        raise ValueError(f"pending-report seed invariant violation: {problems}")
    apply(connection, seed.fixture)


def trigger_event(seed: PendingReportSeed, *, run_id: str) -> dict[str, Any]:
    session_id = seed.correlation[f"interview_session_id:{seed.subject_ref}"]
    event_id = str(sid(run_id, f"report-generation-event/{session_id}"))
    return {
        "outbox_event_id": event_id,
        "company_id": seed.correlation["company_id"],
        "aggregate_type": "interview_session",
        "aggregate_id": session_id,
        "aggregate_version": 1,
        "event_type": "report.generation_requested",
        "event_version": 1,
        "payload": {"interview_session_id": session_id, "report_version": "report-v1"},
        "idempotency_key": f"controlproof-report-generation-{session_id}",
        "correlation_id": f"cp-{run_id}",
    }


def trigger_sql(event: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    sql = (
        "INSERT INTO outbox_events "
        "(outbox_event_id, company_id, aggregate_type, aggregate_id, aggregate_version, "
        "event_type, event_version, payload, idempotency_key, trace_id, occurred_at, "
        "publish_status, publish_attempts) VALUES (:outbox_event_id, :company_id, "
        ":aggregate_type, :aggregate_id, :aggregate_version, :event_type, :event_version, "
        "CAST(:payload AS json), :idempotency_key, :correlation_id, CURRENT_TIMESTAMP, "
        "'pending', 0) "
        "ON CONFLICT (idempotency_key) DO NOTHING"
    )
    params = dict(event)
    params["payload"] = json.dumps(event["payload"], ensure_ascii=False)
    return sql, params


def teardown_pending(connection, seed: PendingReportSeed) -> None:
    teardown(connection, seed.fixture)
