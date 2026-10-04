"""Deterministic, synthetic and Run-scoped subjects for the N-02 profile."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid5

from engine.models import (
    BaselineKind,
    N02EffectGroup,
    N02LaneId,
    RunSubjectLane,
    canonical_json_bytes,
    sha256_bytes,
)

_NAMESPACE = UUID("3af15ed7-92ef-5e7f-a912-972d9ca32331")
_FIXED_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_LOCAL_PEPPER = b"local-development-pepper"


def _id(run_id: UUID, name: str) -> UUID:
    return uuid5(_NAMESPACE, f"{run_id}:{name}")


# WhyYou loads positions and invitations through ``SubmissionRequirementSet``, which rejects a
# set with no required+enabled material. An empty list made every applicant route that loads
# the invitation (including ``POST /v1/applicant/consents``) fail with 422 before the consent
# transaction ran -- see Spec 003 ID-003-09. Mirrors WhyYou ``DEFAULT_SUBMISSION_REQUIREMENTS``.
_DEFAULT_SUBMISSION_REQUIREMENTS: tuple[tuple[str, bool], ...] = (
    ("resume", True),
    ("cover_letter", True),
    ("career_description", False),
    ("projects", False),
    ("portfolio", False),
)


def _submission_requirements() -> list[dict[str, Any]]:
    return [
        {"material_type": material, "required": required, "enabled": True, "instructions": None}
        for material, required in _DEFAULT_SUBMISSION_REQUIREMENTS
    ]


@dataclass(frozen=True, slots=True)
class SeedRow:
    table: str
    values: dict[str, Any]


@dataclass(frozen=True, slots=True)
class N02SubjectDefinition:
    lane: RunSubjectLane
    session_id: UUID
    equipment_check_id: UUID
    strategy_id: UUID
    interview_session_id: UUID
    final_turn_id: UUID
    recording_asset_id: UUID
    transcript_segment_id: UUID
    synthetic_email: str = field(repr=False)
    raw_session_cookie: str = field(repr=False)

    @property
    def lane_id(self) -> N02LaneId:
        return self.lane.lane_id

    @property
    def invitation_id(self) -> UUID:
        return self.lane.invitation_id

    @property
    def applicant_id(self) -> UUID:
        return self.lane.applicant_id

    @property
    def subject_ref(self) -> str:
        return self.lane.subject_ref

    @property
    def baseline_kind(self) -> BaselineKind:
        return self.lane.baseline_kind

    @property
    def allowed_preexisting_effects(self) -> dict[str, int]:
        return self.lane.allowed_preexisting_effects

    @property
    def session_hash(self) -> str:
        return hmac.new(
            _LOCAL_PEPPER,
            self.raw_session_cookie.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def fixture_effect_ids(self) -> tuple[str, ...]:
        if self.lane_id is N02LaneId.RECORDING_BOUNDARY_PROBE:
            return (str(self.equipment_check_id), str(self.strategy_id))
        if self.lane_id is N02LaneId.ASSESSMENT_BOUNDARY_PROBE:
            return (
                str(self.interview_session_id),
                str(self.final_turn_id),
                str(self.recording_asset_id),
            )
        return ()


@dataclass(frozen=True, slots=True)
class N02SeedPlan:
    run_id: UUID
    company_id: UUID
    reviewer_id: UUID
    position_id: UUID
    competency_model_version_id: UUID
    criterion_id: UUID
    stage_id: UUID
    subjects: tuple[N02SubjectDefinition, ...]
    rows: tuple[SeedRow, ...]
    digest: str

    @property
    def lanes(self) -> tuple[RunSubjectLane, ...]:
        return tuple(subject.lane for subject in self.subjects)

    def by_lane(self, lane_id: N02LaneId) -> N02SubjectDefinition:
        return next(subject for subject in self.subjects if subject.lane_id is lane_id)

    def subject_payload(self, lane_id: N02LaneId) -> dict[str, Any]:
        subject = self.by_lane(lane_id)
        return subject.lane.model_dump(mode="json") | {
            "equipment_check_id": str(subject.equipment_check_id),
            "strategy_id": str(subject.strategy_id),
            "interview_session_id": str(subject.interview_session_id),
            "allowed_fixture_effect_ids": list(subject.fixture_effect_ids()),
        }

    def pristine_effect_counts(self) -> dict[str, int]:
        return {"consent": 0, "document": 0, "recording": 0, "assessment": 0}


def build_n02_seed_plan(
    run_id: UUID,
    *,
    company_id: UUID,
    reviewer_id: UUID,
) -> N02SeedPlan:
    """Build six isolated subjects without reusing product/demo identities."""

    position_id = _id(run_id, "position")
    model_id = _id(run_id, "competency-model")
    criterion_id = _id(run_id, "criterion")
    stage_id = _id(run_id, "stage")
    subjects: list[N02SubjectDefinition] = []
    for lane_id in N02LaneId:
        prerequisite = lane_id in {
            N02LaneId.RECORDING_BOUNDARY_PROBE,
            N02LaneId.ASSESSMENT_BOUNDARY_PROBE,
        }
        fixture_effects = (
            {"equipment": 1, "strategy": 1}
            if lane_id is N02LaneId.RECORDING_BOUNDARY_PROBE
            else (
                {"completed_session": 1, "final_turn": 1, "final_video": 1}
                if lane_id is N02LaneId.ASSESSMENT_BOUNDARY_PROBE
                else {}
            )
        )
        target_group = {
            N02LaneId.RECORDING_BOUNDARY_PROBE: N02EffectGroup.RECORDING,
            N02LaneId.ASSESSMENT_BOUNDARY_PROBE: N02EffectGroup.AI_ASSESSMENT,
        }.get(lane_id, N02EffectGroup.DOCUMENT_ANALYSIS)
        slug = lane_id.value.casefold().replace("_", "-")
        fixture_kind = f"n02-{slug}-fixture-v1" if prerequisite else None
        fixture_digest = (
            sha256_bytes(fixture_kind.encode("utf-8")) if fixture_kind else None
        )
        lane = RunSubjectLane(
            run_id=run_id,
            lane_id=lane_id,
            subject_ref=f"n02-{str(run_id)[:8]}-{slug}",
            invitation_id=_id(run_id, f"{lane_id}:invitation"),
            applicant_id=_id(run_id, f"{lane_id}:applicant"),
            baseline_kind=(
                BaselineKind.PREREQUISITE_FIXTURE
                if prerequisite
                else BaselineKind.PRISTINE
            ),
            fixture_kind=fixture_kind,
            fixture_digest=fixture_digest,
            allowed_preexisting_effects=fixture_effects,
            target_effect_groups=(target_group,),
            trace_namespace=f"controlproof:{run_id}:{lane_id.value}",
            seed_correlation_id=f"n02-seed-{str(run_id)[:8]}-{slug}",
        )
        subjects.append(
            N02SubjectDefinition(
                lane=lane,
                session_id=_id(run_id, f"{lane_id}:applicant-session"),
                equipment_check_id=_id(run_id, f"{lane_id}:equipment"),
                strategy_id=_id(run_id, f"{lane_id}:strategy"),
                interview_session_id=_id(run_id, f"{lane_id}:interview-session"),
                final_turn_id=_id(run_id, f"{lane_id}:final-turn"),
                recording_asset_id=_id(run_id, f"{lane_id}:recording-asset"),
                transcript_segment_id=_id(run_id, f"{lane_id}:transcript"),
                synthetic_email=f"n02-{run_id.hex}-{slug}@example.invalid",
                raw_session_cookie=f"n02-local-{run_id.hex}-{slug}",
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
        "company_id": str(company_id),
        "reviewer_id": str(reviewer_id),
        "lanes": [subject.lane.model_dump(mode="json") for subject in subjects],
        "row_ids": [
            {key: str(value) for key, value in row.values.items() if key.endswith("_id")}
            for row in rows
        ],
    }
    return N02SeedPlan(
        run_id=run_id,
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
    subjects: tuple[N02SubjectDefinition, ...],
) -> tuple[SeedRow, ...]:
    expires_at = _FIXED_TIME + timedelta(days=3650)
    rows = [
        SeedRow(
            "positions",
            {
                "company_id": company_id,
                "position_id": position_id,
                "title": f"ControlProof N02 {run_id}",
                "description": "Synthetic local/test-only N-02 position",
                "submission_requirements": _submission_requirements(),
                "created_by": reviewer_id,
                "status": "open",
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
                "interview_level": "standard",
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
                "code": "N02",
                "name": "N-02 synthetic criterion",
                "description": "Synthetic criterion",
                "weight": 1.0,
                "verification_guide": {},
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
                "name": f"N02-{str(run_id)[:8]}",
                "sort_order": 1,
                "row_version": 1,
            },
        ),
    ]
    for subject in subjects:
        lane = subject.lane
        rows.extend(
            [
                SeedRow(
                    "invitations",
                    {
                        "company_id": company_id,
                        "invitation_id": lane.invitation_id,
                        "position_id": position_id,
                        "competency_model_version_id": model_id,
                        "applicant_id": lane.applicant_id,
                        "applicant_email_normalized": subject.synthetic_email,
                        "applicant_display_name": lane.subject_ref,
                        "submission_requirements": _submission_requirements(),
                        "token_hash": sha256_bytes(
                            f"n02-token:{run_id}:{lane.lane_id.value}".encode()
                        ),
                        "expires_at": expires_at,
                        "status": "identity_verified",
                        "identity_verified_at": _FIXED_TIME,
                        "last_state_actor_type": "system",
                        "row_version": 1,
                        "recruiting_stage_id": stage_id,
                        "pipeline_row_version": 1,
                    },
                ),
                SeedRow(
                    "applicant_profiles",
                    {
                        "company_id": company_id,
                        "applicant_id": lane.applicant_id,
                        "invitation_id": lane.invitation_id,
                        "display_name": lane.subject_ref,
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
        if lane.lane_id in {
            N02LaneId.RECORDING_BOUNDARY_PROBE,
            N02LaneId.ASSESSMENT_BOUNDARY_PROBE,
        }:
            rows.extend(
                build_probe_overlay_rows(
                    subject,
                    company_id,
                    model_id,
                    criterion_id,
                    include_assessment=(
                        lane.lane_id is N02LaneId.ASSESSMENT_BOUNDARY_PROBE
                    ),
                )
            )
    return tuple(rows)


def build_probe_overlay_rows(
    subject: N02SubjectDefinition,
    company_id: UUID,
    model_id: UUID,
    criterion_id: UUID,
    *,
    include_assessment: bool,
) -> list[SeedRow]:
    rows = [
        SeedRow(
            "equipment_checks",
            {
                "company_id": company_id,
                "equipment_check_id": subject.equipment_check_id,
                "invitation_id": subject.invitation_id,
                "applicant_id": subject.applicant_id,
                "camera_status": "ready",
                "microphone_status": "ready",
                "network_status": "ready",
                "overall_status": "ready",
                "checked_at": _FIXED_TIME,
            },
        ),
        SeedRow(
            "interview_strategies",
            {
                "company_id": company_id,
                "interview_strategy_id": subject.strategy_id,
                "invitation_id": subject.invitation_id,
                "applicant_id": subject.applicant_id,
                "competency_model_version_id": model_id,
                "strategy_version": 1,
                "common_topics": [],
                "verification_points": [],
                "follow_up_directions": {},
                "time_budget": {},
                "required_evidence_plan": {},
                "source_reference_candidates": [],
                "model_config_version": "controlproof-fixed-v1",
                "status": "ready",
            },
        ),
    ]
    if not include_assessment:
        return rows
    rows.extend(
        [
            SeedRow(
                "interview_sessions",
                {
                    "company_id": company_id,
                    "interview_session_id": subject.interview_session_id,
                    "invitation_id": subject.invitation_id,
                    "applicant_id": subject.applicant_id,
                    "interview_strategy_id": subject.strategy_id,
                    "competency_model_version_id": model_id,
                    "state": "completed",
                    "session_sequence": 1,
                    "row_version": 1,
                    "degraded_modes": [],
                    "created_at": _FIXED_TIME,
                    "started_at": _FIXED_TIME,
                    "completed_at": _FIXED_TIME + timedelta(minutes=1),
                },
            ),
            SeedRow(
                "interview_turns",
                {
                    "company_id": company_id,
                    "turn_id": subject.final_turn_id,
                    "interview_session_id": subject.interview_session_id,
                    "sequence": 1,
                    "speaker": "applicant",
                    "status": "final",
                    "text": "Synthetic answer",
                    "target_criterion_id": criterion_id,
                    "idempotency_key": f"n02-{subject.final_turn_id}",
                    "model_config_version": "controlproof-fixed-v1",
                    "finalized_at": _FIXED_TIME,
                },
            ),
            SeedRow(
                "recording_assets",
                {
                    "company_id": company_id,
                    "recording_asset_id": subject.recording_asset_id,
                    "interview_session_id": subject.interview_session_id,
                    "asset_type": "final_video",
                    "object_key": f"controlproof/{subject.recording_asset_id}",
                    "content_hash": "0" * 64,
                    "duration_ms": 1000,
                    "status": "ready",
                    "missing_ranges": [],
                    "created_at": _FIXED_TIME,
                },
            ),
            SeedRow(
                "transcript_segments",
                {
                    "company_id": company_id,
                    "transcript_segment_id": subject.transcript_segment_id,
                    "interview_session_id": subject.interview_session_id,
                    "turn_id": subject.final_turn_id,
                    "speaker": "applicant",
                    "text": "Synthetic transcript",
                    "confidence": 1.0,
                    "session_start_ms": 0,
                    "session_end_ms": 1000,
                    "source_audio_key": f"controlproof/{subject.recording_asset_id}",
                    "version": 1,
                    "created_at": _FIXED_TIME,
                },
            ),
        ]
    )
    return rows
