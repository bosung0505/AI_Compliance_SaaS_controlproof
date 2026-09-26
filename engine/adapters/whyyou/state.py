"""Allowlisted WhyYou state projection used for baseline and side-effect checks."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from sqlalchemy import create_engine, text

from engine.adapters.base import AdapterResult
from engine.adapters.whyyou.client import WhyYouClient
from engine.config import Settings

STATE_KEYS = (
    "invitation_status",
    "recruiting_stage_id",
    "pipeline_row_version",
    "final_decision_count",
    "latest_final_decision_actor_type",
    "report_presence",
    "report_status",
)


class WhyYouStateAdapter:
    def __init__(
        self,
        settings: Settings,
        client: WhyYouClient,
        loader: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    ) -> None:
        self.settings = settings
        self.client = client
        self._loader = loader or self._load_from_database

    def snapshot(self, *, subject: Mapping[str, Any], phase: str) -> AdapterResult:
        try:
            source = self._loader(subject)
            projection = {key: source.get(key) for key in STATE_KEYS}
            missing = [key for key in STATE_KEYS if key not in source]
            if missing:
                return AdapterResult(
                    False,
                    "STATE_PROJECTION_INCOMPLETE",
                    {"missing_keys": missing, "phase": phase},
                )
            return AdapterResult(True, "STATE_CAPTURED", {"state": projection, "phase": phase})
        except Exception as exc:  # noqa: BLE001 - adapter hides driver-specific details
            return AdapterResult(False, "STATE_ACCESS_FAILED", detail=type(exc).__name__)

    def report_status(self, *, subject: Mapping[str, Any]) -> AdapterResult:
        try:
            result = self.client.report_status(str(subject["interview_session_id"]))
        except Exception as exc:  # noqa: BLE001 - adapter hides transport-specific details
            return AdapterResult(False, "REPORT_ACCESS_FAILED", detail=type(exc).__name__)
        return AdapterResult(result.get("presence") != "UNAVAILABLE", "REPORT_STATUS", result)

    def attempt_final_decision(self, *, subject: Mapping[str, Any]) -> AdapterResult:
        try:
            result = self.client.attempt_final_decision(
                str(subject["invitation_id"]),
                recruiting_stage_id=str(subject["target_stage_id"]),
                expected_pipeline_version=int(subject["pipeline_row_version"]),
                idempotency_key=f"controlproof-h03-{subject['invitation_id']}",
            )
        except Exception as exc:  # noqa: BLE001 - adapter hides transport-specific details
            return AdapterResult(False, "DECISION_ACCESS_FAILED", detail=type(exc).__name__)
        return AdapterResult(True, "DECISION_ATTEMPTED", result)

    def _load_from_database(self, subject: Mapping[str, Any]) -> Mapping[str, Any]:
        engine = create_engine(self.settings.whyyou_database_url)
        query = text(
            "SELECT i.status AS invitation_status, i.recruiting_stage_id, "
            "i.pipeline_row_version, "
            "(SELECT COUNT(*) FROM human_reviews h WHERE h.invitation_id=i.invitation_id "
            "AND h.decision_kind='final_decision') AS final_decision_count, "
            "(SELECT h.actor_type FROM human_reviews h WHERE h.invitation_id=i.invitation_id "
            "AND h.decision_kind='final_decision' ORDER BY h.created_at DESC LIMIT 1) "
            "AS latest_final_decision_actor_type, "
            "CASE WHEN r.report_id IS NULL THEN 'ABSENT' ELSE 'PRESENT' END AS report_presence, "
            "r.status AS report_status FROM invitations i "
            "LEFT JOIN reports r ON r.invitation_id=i.invitation_id "
            "WHERE i.invitation_id=:invitation_id"
        )
        with engine.connect() as connection:
            row = (
                connection.execute(
                    query,
                    {"invitation_id": str(subject["invitation_id"])},
                )
                .mappings()
                .one()
            )
            return dict(row)
