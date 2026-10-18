"""Explicit cleanup of N-02 product rows not connected to seed rows by foreign keys."""

from uuid import UUID

from sqlalchemy import text

from engine.adapters.whyyou.n02_seed import _delete_dependents
from engine.models import N02LaneId

# Cross-module IDs deliberately have no database FK. Never start from a company/reviewer row.
_SUBJECT_TABLES = (
    ("assistant_retrieval_documents", "applicant_id"),
    ("question_rationales", "applicant_id"),
    ("claim_conflicts", "applicant_id"),
    ("candidate_claims", "applicant_id"),
    ("retrieval_documents", "applicant_id"),
    ("verification_progress", "applicant_id"),
    ("verification_targets", "applicant_id"),
    ("candidate_verification_maps", "applicant_id"),
    ("reports", "invitation_id"),
    ("interview_sessions", "invitation_id"),
    ("submission_chunks", "applicant_id"),
    ("submissions", "invitation_id"),
    ("interview_strategies", "invitation_id"),
    ("equipment_checks", "invitation_id"),
    ("submission_upload_intents", "invitation_id"),
)
_SESSION_TABLES = ("report_generation_failures", "question_source_references")
_RESOURCE_KEYS = {
    "interview_session_id",
    "submission_id",
    "report_id",
    "analysis_id",
    "upload_id",
    "candidate_verification_map_id",
    "verification_target_id",
    "chunk_id",
    "turn_id",
}


def delete_product_rows(connection, *, company_id, lanes):
    if (
        len(lanes) != 6
        or {lane.lane_id for lane in lanes} != set(N02LaneId)
        or len({lane.run_id for lane in lanes}) != 1
        or len({lane.invitation_id for lane in lanes}) != 6
        or len({lane.applicant_id for lane in lanes}) != 6
    ):
        raise ValueError("cleanup requires six owned lanes from one Run")
    removed = 0
    resources = {lane.invitation_id for lane in lanes} | {lane.applicant_id for lane in lanes}

    def selected(table, column, subject_id):
        params = {"company_id": company_id, "subject_id": subject_id}
        where = f"company_id=:company_id AND {column}=:subject_id"
        rows = (
            connection.execute(text(f"SELECT * FROM {table} WHERE {where}"), params)
            .mappings()
            .all()
        )
        return rows, where, params

    def remove(table, column, subject_id):
        nonlocal removed
        rows, where, params = selected(table, column, subject_id)
        for row in rows:
            resources.update(
                UUID(str(row[key])) for key in _RESOURCE_KEYS if row.get(key) is not None
            )
            _delete_dependents(connection, table, dict(row))
        if rows:
            connection.execute(text(f"DELETE FROM {table} WHERE {where}"), params)
            if selected(table, column, subject_id)[0]:
                raise RuntimeError("owned product cleanup left rows")
        removed += len(rows)

    for lane in lanes:
        sessions, _, _ = selected("interview_sessions", "invitation_id", lane.invitation_id)
        for session in sessions:
            for table in _SESSION_TABLES:
                remove(table, "interview_session_id", session["interview_session_id"])
        for table, column in _SUBJECT_TABLES:
            remove(table, column, getattr(lane, column))
    for resource_id in resources:
        for table in ("command_idempotency", "audit_events"):
            connection.execute(
                text(
                    f"DELETE FROM {table} WHERE company_id=:company_id AND resource_id=:subject_id"
                ),
                {"company_id": company_id, "subject_id": resource_id},
            )
    events = (
        connection.execute(
            text(
                "SELECT outbox_event_id FROM outbox_events WHERE company_id=:company_id AND trace_id LIKE :trace"
            ),
            {"company_id": company_id, "trace": f"controlproof:{lanes[0].run_id}:%"},
        )
        .mappings()
        .all()
    )
    for row in events:
        connection.execute(
            text("DELETE FROM processed_messages WHERE event_id=:event_id"),
            {"event_id": row["outbox_event_id"]},
        )
        connection.execute(
            text(
                "DELETE FROM outbox_events WHERE company_id=:company_id AND outbox_event_id=:event_id"
            ),
            {"company_id": company_id, "event_id": row["outbox_event_id"]},
        )
    return removed
