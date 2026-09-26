"""Deterministic H-03 fixture: completed interview, final media, no report/event/decision."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from seeds.state_seed import ApplicantSpec, Fixture, apply, build_fixture, sid, teardown


@dataclass(frozen=True, slots=True)
class PendingReportSeed:
    fixture: Fixture
    subject_ref: str

    @property
    def correlation(self) -> dict[str, str]:
        return self.fixture.correlation


def build_pending_report_fixture(
    label: str, *, subject_ref: str = "candidate-01"
) -> PendingReportSeed:
    fixture = deepcopy(
        build_fixture(
            label,
            [ApplicantSpec(ref=subject_ref, scored_axes=(), evidence_count=0)],
        )
    )
    fixture.rows["report"] = []
    fixture.rows["report_item"] = []
    fixture.rows["evidence"] = []
    fixture.correlation.pop(f"report_id:{subject_ref}", None)
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
        "aggregate_type": "interview_session",
        "aggregate_id": session_id,
        "event_type": "report.generation_requested",
        "event_version": 1,
        "payload": {"interview_session_id": session_id, "report_version": "report-v1"},
        "idempotency_key": f"controlproof-report-generation-{session_id}",
        "correlation_id": f"cp-{run_id}",
    }


def trigger_sql(event: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    sql = (
        "INSERT INTO outbox_events "
        "(outbox_event_id, aggregate_type, aggregate_id, event_type, event_version, payload, "
        "idempotency_key, trace_id) VALUES (:outbox_event_id, :aggregate_type, :aggregate_id, "
        ":event_type, :event_version, :payload, :idempotency_key, :correlation_id) "
        "ON CONFLICT (idempotency_key) DO NOTHING"
    )
    return sql, event


def teardown_pending(connection, seed: PendingReportSeed) -> None:
    teardown(connection, seed.fixture)
