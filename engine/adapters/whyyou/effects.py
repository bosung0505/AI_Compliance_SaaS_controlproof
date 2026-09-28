"""Allowlisted WhyYou business-effect projections for Spec 002."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any
from uuid import UUID

from sqlalchemy import create_engine, text

from engine.config import Settings
from engine.models import (
    BusinessEffectSnapshot,
    EffectGroup,
    Phase,
    Presence,
    canonical_json_bytes,
    sha256_bytes,
    utcnow,
)


class WhyYouEffectAdapter:
    def __init__(
        self,
        settings: Settings,
        *,
        loader: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    ) -> None:
        self.settings = settings
        self._loader = loader or self._load_decision_effects

    def read_reporting_effects(self, **_kwargs: Any) -> tuple[BusinessEffectSnapshot, ...]:
        raise NotImplementedError("reporting effect projection is owned by Spec 002 US3")

    def read_decision_effects(
        self,
        *,
        subject: Mapping[str, Any],
        phase: str | Phase,
        run_id: UUID,
        logical_operation_id: UUID,
        source_event_id: UUID,
        step_id: str,
        attempt: int = 1,
    ) -> tuple[BusinessEffectSnapshot, ...]:
        active_phase = Phase(phase)
        try:
            source = self._loader(subject)
        except Exception:  # noqa: BLE001 - projection must not leak DB diagnostics
            return (
                BusinessEffectSnapshot(
                    run_id=run_id,
                    subject_ref=str(subject.get("subject_ref", "candidate-01")),
                    phase=active_phase,
                    step_id=step_id,
                    attempt=attempt,
                    logical_operation_id=logical_operation_id,
                    source_event_id=source_event_id,
                    effect_group=EffectGroup.DECISION,
                    effects={},
                    state_digest=sha256_bytes(canonical_json_bytes({})),
                    captured_at=utcnow(),
                    source_status=Presence.UNAVAILABLE,
                    source_error_code="DECISION_EFFECT_ACCESS_FAILED",
                ),
            )
        if source is None:
            presence = Presence.ABSENT
            effects: dict[str, Any] = {}
        else:
            presence = Presence.PRESENT
            reviews = tuple(source.get("human_reviews", ()))
            audits = tuple(source.get("audit_events", ()))
            stage_id = source.get("stage_id")
            invitation_id = str(source["invitation_id"])
            version = int(source["pipeline_row_version"])
            effects = {
                "stage_assignment_ids": (
                    [f"{invitation_id}:{stage_id}:{version}"] if stage_id else []
                ),
                "stage_id": str(stage_id) if stage_id else None,
                "pipeline_row_version": version,
                "invitation_status": str(source["invitation_status"]),
                "human_review_ids": [str(item["human_review_id"]) for item in reviews],
                "human_review_actor_types": [
                    str(item.get("actor_type", "COMPANY_USER")) for item in reviews
                ],
                "decision_actor_types": [
                    str(item["actor_type"])
                    for item in audits
                    if item.get("actor_type") is not None
                ],
                "final_decision_audit_ids": [
                    str(item["audit_event_id"])
                    for item in audits
                    if item.get("action") == "final_decision.create"
                ],
                "pipeline_move_audit_ids": [
                    str(item["audit_event_id"])
                    for item in audits
                    if item.get("action") == "applicant_pipeline.moved"
                ],
                "final_decision_request_ids": [
                    str(item["request_id"])
                    for item in audits
                    if item.get("action") == "final_decision.create"
                ],
            }
        return (
            BusinessEffectSnapshot(
                run_id=run_id,
                subject_ref=str(subject.get("subject_ref", "candidate-01")),
                phase=active_phase,
                step_id=step_id,
                attempt=attempt,
                logical_operation_id=logical_operation_id,
                source_event_id=source_event_id,
                effect_group=EffectGroup.DECISION,
                effects=effects,
                state_digest=sha256_bytes(canonical_json_bytes(effects)),
                captured_at=utcnow(),
                source_status=presence,
            ),
        )

    def _load_decision_effects(
        self, subject: Mapping[str, Any]
    ) -> Mapping[str, Any] | None:
        engine = create_engine(self.settings.whyyou_database_url)
        scope = {
            "company_id": UUID(str(subject["company_id"])),
            "position_id": UUID(str(subject["position_id"])),
            "invitation_id": UUID(str(subject["invitation_id"])),
        }
        with engine.connect() as connection:
            invitation = connection.execute(
                text(
                    "SELECT invitation_id, recruiting_stage_id AS stage_id, "
                    "pipeline_row_version, status AS invitation_status "
                    "FROM invitations WHERE company_id=:company_id "
                    "AND invitation_id=:invitation_id"
                ),
                scope,
            ).mappings().one_or_none()
            if invitation is None:
                return None
            reviews = tuple(
                dict(row)
                for row in connection.execute(
                    text(
                        "SELECT human_review_id, company_user_id, value "
                        "FROM human_reviews WHERE company_id=:company_id "
                        "AND target_id=:invitation_id AND review_type='final_decision' "
                        "ORDER BY human_review_id"
                    ),
                    scope,
                ).mappings()
            )
            review_ids = {row["human_review_id"] for row in reviews}
            audit_rows = connection.execute(
                text(
                    "SELECT audit_event_id, action, resource_id, request_id, actor_type "
                    "FROM audit_events WHERE company_id=:company_id "
                    "AND action IN ('final_decision.create','applicant_pipeline.moved') "
                    "ORDER BY audit_event_id"
                ),
                scope,
            ).mappings()
            audits = tuple(
                dict(row)
                for row in audit_rows
                if (
                    row["action"] == "final_decision.create"
                    and row["resource_id"] in review_ids
                )
                or (
                    row["action"] == "applicant_pipeline.moved"
                    and row["resource_id"] == scope["position_id"]
                )
            )
        return {
            **dict(invitation),
            "human_reviews": [
                {
                    "human_review_id": row["human_review_id"],
                    "actor_type": "COMPANY_USER",
                }
                for row in reviews
            ],
            "audit_events": audits,
        }
