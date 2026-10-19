"""Deterministic, synthetic and Run-scoped subjects for the Spec 009 N-01 and N-03 profiles.

N-01 lanes start as ``invited`` with an unconsumed invitation token, so the product itself exchanges
the token, verifies the display name and creates the session and profile. N-03 lanes start
``identity_verified`` with a session, the same shape as N-02. Raw credentials live only on the
definition (``repr=False``) and are handed to the in-memory credential store by the adapter.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid5

from engine.models import (
    SPEC009_PROFILES,
    ExecutionProfile,
    N01LaneId,
    N03LaneId,
    Spec009SubjectLane,
    canonical_json_bytes,
    sha256_bytes,
)
from seeds.n02_subjects import SeedRow, _submission_requirements

_NAMESPACE = UUID("6b0c2f4e-1d9a-5c3e-8f27-0a9d4e5b7c11")
_FIXED_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_LOCAL_PEPPER = b"local-development-pepper"
_LANES: dict[ExecutionProfile, tuple[N01LaneId, ...] | tuple[N03LaneId, ...]] = {
    ExecutionProfile.N01_NOTICE_V1: tuple(N01LaneId),
    ExecutionProfile.N03_STALE_CONSENT_V1: tuple(N03LaneId),
}


def _id(run_id: UUID, lane: str, name: str) -> UUID:
    return uuid5(_NAMESPACE, f"{run_id}:{lane}:{name}")


def _local_hash(raw: str) -> str:
    """WhyYou ``hash_token``: HMAC-SHA256 with the local development pepper."""
    return hmac.new(_LOCAL_PEPPER, raw.encode("utf-8"), hashlib.sha256).hexdigest()


@dataclass(frozen=True, slots=True)
class Spec009SubjectDefinition:
    lane: Spec009SubjectLane
    display_name: str
    session_id: UUID | None
    raw_invitation_token: str | None = field(default=None, repr=False)
    raw_session_cookie: str | None = field(default=None, repr=False)

    @property
    def lane_id(self) -> N01LaneId | N03LaneId:
        return self.lane.lane_id

    @property
    def subject_ref(self) -> str:
        return self.lane.subject_ref

    @property
    def invitation_id(self) -> UUID:
        return self.lane.invitation_id

    @property
    def applicant_id(self) -> UUID:
        return self.lane.applicant_id

    @property
    def token_hash(self) -> str | None:
        return _local_hash(self.raw_invitation_token) if self.raw_invitation_token else None

    @property
    def session_hash(self) -> str | None:
        return _local_hash(self.raw_session_cookie) if self.raw_session_cookie else None

    def subject_payload(self) -> dict[str, Any]:
        return self.lane.model_dump(mode="json")


@dataclass(frozen=True, slots=True)
class Spec009SeedPlan:
    run_id: UUID
    profile: ExecutionProfile
    company_id: UUID
    reviewer_id: UUID
    position_id: UUID
    competency_model_version_id: UUID
    criterion_id: UUID
    stage_id: UUID
    subjects: tuple[Spec009SubjectDefinition, ...]
    rows: tuple[SeedRow, ...] = field(repr=False)
    digest: str

    @property
    def lanes(self) -> tuple[Spec009SubjectLane, ...]:
        return tuple(subject.lane for subject in self.subjects)

    def by_lane(self, lane_id: N01LaneId | N03LaneId) -> Spec009SubjectDefinition:
        return next(subject for subject in self.subjects if subject.lane_id == lane_id)

    def subject_payload(self, lane_id: N01LaneId | N03LaneId) -> dict[str, Any]:
        return self.by_lane(lane_id).subject_payload()

    def row_for(self, table: str, invitation_id: UUID) -> SeedRow:
        return next(
            row
            for row in self.rows
            if row.table == table and row.values.get("invitation_id") == invitation_id
        )

    def owned_ids(self) -> frozenset[UUID]:
        """Root IDs the cleanup scans from; never the company or reviewer."""
        lanes = self.lanes
        return frozenset(
            {lane.invitation_id for lane in lanes}
            | {lane.applicant_id for lane in lanes}
            | {
                self.position_id,
                self.competency_model_version_id,
                self.criterion_id,
                self.stage_id,
            }
        )

    def manifest(self) -> dict[str, Any]:
        """JSON-safe plan identity for evidence: IDs, lanes and digest, never a credential."""
        return {
            "run_id": str(self.run_id),
            "profile": self.profile.value,
            "lanes": [lane.model_dump(mode="json") for lane in self.lanes],
            "tables": [row.table for row in self.rows],
            "seed_digest": self.digest,
        }


def build_spec009_seed_plan(
    run_id: UUID,
    *,
    profile: ExecutionProfile,
    company_id: UUID,
    reviewer_id: UUID,
) -> Spec009SeedPlan:
    if profile not in SPEC009_PROFILES:
        raise ValueError(f"{profile} is not a Spec 009 profile")
    position_id = _id(run_id, "common", "position")
    model_id = _id(run_id, "common", "competency-model")
    criterion_id = _id(run_id, "common", "criterion")
    stage_id = _id(run_id, "common", "stage")
    invited = profile is ExecutionProfile.N01_NOTICE_V1
    prefix = "n01" if invited else "n03"
    subjects = []
    for lane_id in _LANES[profile]:
        slug = lane_id.value
        lane = Spec009SubjectLane(
            run_id=run_id,
            lane_id=lane_id,
            subject_ref=f"{prefix}-{str(run_id)[:8]}-{slug}",
            invitation_id=_id(run_id, slug, "invitation"),
            applicant_id=_id(run_id, slug, "applicant"),
            seed_kind="invited-token" if invited else "identity-verified-session",
            trace_namespace=f"controlproof:{run_id}:{slug}",
            seed_correlation_id=f"{prefix}-seed-{str(run_id)[:8]}-{slug}",
        )
        subjects.append(
            Spec009SubjectDefinition(
                lane=lane,
                display_name=f"CP-{prefix.upper()}-{slug}-{str(run_id)[:8]}",
                session_id=None if invited else _id(run_id, slug, "applicant-session"),
                raw_invitation_token=secrets.token_urlsafe(48) if invited else None,
                raw_session_cookie=None if invited else secrets.token_urlsafe(48),
            )
        )
    rows = _seed_rows(
        run_id,
        company_id=company_id,
        reviewer_id=reviewer_id,
        position_id=position_id,
        model_id=model_id,
        criterion_id=criterion_id,
        stage_id=stage_id,
        subjects=tuple(subjects),
    )
    identity = {
        "run_id": str(run_id),
        "profile": profile.value,
        "company_id": str(company_id),
        "reviewer_id": str(reviewer_id),
        "lanes": [subject.lane.model_dump(mode="json") for subject in subjects],
        "row_ids": [
            {key: str(value) for key, value in row.values.items() if key.endswith("_id")}
            for row in rows
        ],
    }
    return Spec009SeedPlan(
        run_id=run_id,
        profile=profile,
        company_id=company_id,
        reviewer_id=reviewer_id,
        position_id=position_id,
        competency_model_version_id=model_id,
        criterion_id=criterion_id,
        stage_id=stage_id,
        subjects=tuple(subjects),
        rows=rows,
        digest=sha256_bytes(canonical_json_bytes(identity)),
    )


def _seed_rows(
    run_id: UUID,
    *,
    company_id: UUID,
    reviewer_id: UUID,
    position_id: UUID,
    model_id: UUID,
    criterion_id: UUID,
    stage_id: UUID,
    subjects: tuple[Spec009SubjectDefinition, ...],
) -> tuple[SeedRow, ...]:
    expires_at = _FIXED_TIME + timedelta(days=3650)
    rows = [
        SeedRow(
            "positions",
            {
                "company_id": company_id,
                "position_id": position_id,
                "title": f"ControlProof N01/N03 {run_id}",
                "description": "Synthetic local/test-only Spec 009 position",
                "submission_requirements": _submission_requirements(),
                "created_by": reviewer_id,
                "status": "active",
                "row_version": 1,
                "created_at": _FIXED_TIME,
            },
        ),
        SeedRow(
            "competency_model_versions",
            {
                "company_id": company_id,
                "competency_model_version_id": model_id,
                "position_id": position_id,
                "version_number": 1,
                "prohibited_topics": [],
                "interview_duration_minutes": 30,
                "interview_level": "junior",
                "axis_weights": {},
                "persona_definition": {},
                "status": "published",
                "row_version": 1,
                "published_at": _FIXED_TIME,
            },
        ),
        SeedRow(
            "evaluation_criteria",
            {
                "company_id": company_id,
                "competency_model_version_id": model_id,
                "criterion_id": criterion_id,
                "code": "S009",
                "name": "Spec 009 synthetic criterion",
                "description": "Synthetic criterion",
                "weight": 1.0,
                # WhyYou validates this on every criterion read (ID-003-15).
                "verification_guide": {
                    "observable_dimensions": ["Synthetic situation", "Synthetic action"],
                    "strong_answer_signals": ["Synthetic specific action"],
                    "weak_answer_signals": ["Synthetic team-only answer"],
                    "follow_up_directions": ["Synthetic own action"],
                    "max_follow_ups": 1,
                    "time_budget_seconds": 300,
                },
                "abstain_guidance": "Abstain without evidence",
                "common_questions": [],
                "required": True,
            },
        ),
        SeedRow(
            "recruiting_stages",
            {
                "company_id": company_id,
                "recruiting_stage_id": stage_id,
                "position_id": position_id,
                "name": f"S009-{str(run_id)[:8]}",
                "sort_order": 1,
                "row_version": 1,
            },
        ),
    ]
    for subject in subjects:
        lane = subject.lane
        invited = lane.seed_kind == "invited-token"
        invitation = SeedRow(
            "invitations",
            {
                "company_id": company_id,
                "invitation_id": lane.invitation_id,
                "position_id": position_id,
                "competency_model_version_id": model_id,
                "applicant_id": lane.applicant_id,
                "applicant_email_normalized": f"{lane.subject_ref}@example.invalid",
                "applicant_display_name": subject.display_name,
                "submission_requirements": _submission_requirements(),
                # N-03 has no token row, so its token hash can never be exchanged.
                "token_hash": subject.token_hash
                or sha256_bytes(f"n03-token:{run_id}:{lane.lane_id.value}".encode()),
                "expires_at": expires_at,
                "status": "invited" if invited else "identity_verified",
                "identity_verified_at": None if invited else _FIXED_TIME,
                "last_state_actor_type": "system",
                "row_version": 1,
                "recruiting_stage_id": stage_id,
                "pipeline_row_version": 1,
            },
        )
        rows.append(invitation)
        if invited:
            rows.append(
                SeedRow(
                    "applicant_access_tokens",
                    {
                        "token_hash": subject.token_hash,
                        "company_id": company_id,
                        "invitation_id": lane.invitation_id,
                        "applicant_id": lane.applicant_id,
                        "expires_at": expires_at,
                        "consumed_at": None,
                    },
                )
            )
            continue
        rows.extend(
            [
                SeedRow(
                    "applicant_profiles",
                    {
                        "company_id": company_id,
                        "applicant_id": lane.applicant_id,
                        "invitation_id": lane.invitation_id,
                        "display_name": subject.display_name,
                        "verification_method": "controlproof-local",
                        "technology_tags": [],
                    },
                ),
                SeedRow(
                    "applicant_access_sessions",
                    {
                        "session_hash": subject.session_hash,
                        "company_id": company_id,
                        "invitation_id": lane.invitation_id,
                        "applicant_id": lane.applicant_id,
                        "session_id": subject.session_id,
                        "expires_at": expires_at,
                    },
                ),
            ]
        )
    return tuple(rows)
