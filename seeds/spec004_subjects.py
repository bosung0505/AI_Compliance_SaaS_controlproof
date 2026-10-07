"""Deterministic, synthetic and Run-scoped report lanes for the Spec 004 E-01/E-02 profiles.

Every lane owns its invitation, applicant, completed interview session, strategy, one final video and, per
criterion, an interviewer question turn (``target_criterion_id``), the applicant's final answer turn and its
transcript segment. WhyYou groups an answer under a criterion only when a question turn precedes it
(``runtime/worker.py`` ``_criterion_answers_by_criterion``), so the pair is what makes a criterion scorable.

E-01 lanes also seed their own position and competency version (``RUN_SEED``) whose criterion descriptions start
with the ``spec004-report-v1`` marker. E-02 lanes are bound to a version the product API created and published
(``PRODUCT_API_LATEST_PUBLISHED``); only the shared Run-owned position is seeded for E-02.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid5

from engine.models import (
    CitationMode,
    CriteriaVersionSnapshot,
    E01LaneId,
    E02LaneId,
    LaneCriterion,
    ReportLane,
    VersionSource,
    canonical_json_bytes,
    sha256_bytes,
    spec004_marker,
)
from seeds.n02_subjects import SeedRow, _submission_requirements

_NAMESPACE = UUID("8d0f8a3e-3c4e-5a52-9a1b-2f5b0c7e4d04")
_FIXED_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_LOCAL_PEPPER = b"local-development-pepper"
_TURN_SPACING_MS = 10_000
_ANSWER_START_MS = 2_000
_ANSWER_END_MS = 8_000
CONSENT_PURPOSES = ("ai_assessment", "document_analysis", "recording")
AXIS_KEYS = ("correctness", "depth", "fundamentals", "ownership", "communication")

#: lane -> ((code, mode, weight), ...); codes sort in evaluation order (WhyYou order_by(code)).
E01_LANE_CRITERIA: dict[E01LaneId, tuple[tuple[str, CitationMode, float], ...]] = {
    E01LaneId.E01_REFERENCE: (("E01-REF-1-VALID", CitationMode.VALID, 100.0),),
    E01LaneId.E01_CITATION_MATRIX: (
        ("E01-1-VALID", CitationMode.VALID, 20.0),
        ("E01-2-EMPTY", CitationMode.EMPTY, 20.0),
        ("E01-3-NONEXISTENT", CitationMode.NONEXISTENT, 20.0),
        ("E01-4-OTHER-APPLICANT", CitationMode.OTHER_APPLICANT, 20.0),
        ("E01-5-OTHER-CRITERION", CitationMode.OTHER_CRITERION, 20.0),
    ),
    E01LaneId.E01_EVIDENCE_REMOVAL: (
        ("E01-REM-1-VALID", CitationMode.VALID, 50.0),
        ("E01-REM-2-VALID", CitationMode.VALID, 50.0),
    ),
    E01LaneId.E01_STORAGE_PROBE: (("E01-PROBE-1-VALID", CitationMode.VALID, 100.0),),
}
#: plan.md "E-02 점수 표식 값": (code, score, weight); v1 72.5 -> 72, v2 73.5 -> 74.
E02_VERSION_CRITERIA = {
    "v1": (("E02-A", 72, 50.0), ("E02-B", 73, 50.0)),
    "v2": (("E02-A", 72, 25.0), ("E02-B", 74, 75.0)),
}
E02_AXIS_WEIGHTS = {
    "v1": {axis: 20.0 for axis in AXIS_KEYS},
    "v2": {
        "correctness": 30.0,
        "depth": 25.0,
        "fundamentals": 20.0,
        "ownership": 15.0,
        "communication": 10.0,
    },
}
_VERIFICATION_GUIDE = {
    "observable_dimensions": ["Synthetic situation", "Synthetic action"],
    "strong_answer_signals": ["Synthetic specific action"],
    "weak_answer_signals": ["Synthetic team-only answer"],
    "follow_up_directions": ["Synthetic own action"],
    "max_follow_ups": 1,
    "time_budget_seconds": 300,
}


def _id(run_id: UUID, name: str) -> UUID:
    return uuid5(_NAMESPACE, f"{run_id}:{name}")


def _slug(lane_id: E01LaneId | E02LaneId) -> str:
    return lane_id.value.casefold().replace("_", "-")


def nonexistent_evidence_id(run_id: UUID) -> UUID:
    """A UUID no WhyYou table holds (seed preflight confirms absence)."""
    return _id(run_id, "e01-nonexistent")


def e02_position_id(run_id: UUID) -> UUID:
    return _id(run_id, "e02:position")


def lane_credential(lane: ReportLane) -> str:
    """The local/test applicant session value for this lane; never written to evidence."""
    return f"spec004-local-{lane.run_id.hex}-{_slug(lane.lane_id)}"


def _session_hash(raw: str) -> str:
    return hmac.new(_LOCAL_PEPPER, raw.encode("utf-8"), hashlib.sha256).hexdigest()


def _criterion(
    run_id: UUID,
    lane_id: E01LaneId | E02LaneId,
    *,
    code: str,
    criterion_id: UUID,
    weight: float,
    mode: CitationMode,
    argument: str | None = None,
    score: int | None = None,
) -> LaneCriterion:
    prefix = f"{lane_id.value}:{code}"
    return LaneCriterion(
        criterion_id=criterion_id,
        code=code,
        weight=weight,
        citation_mode=mode,
        mode_argument=argument,
        fixture_score=score,
        marker=spec004_marker(mode, argument, score),
        answer_turn_id=_id(run_id, f"{prefix}:answer"),
        question_turn_id=_id(run_id, f"{prefix}:question"),
        transcript_segment_id=_id(run_id, f"{prefix}:segment"),
    )


def _lane(
    run_id: UUID,
    lane_id: E01LaneId | E02LaneId,
    *,
    criteria: tuple[LaneCriterion, ...],
    position_id: UUID,
    version_id: UUID,
    source: VersionSource,
) -> ReportLane:
    slug = _slug(lane_id)
    identity = {
        "run_id": str(run_id),
        "lane_id": lane_id.value,
        "position_id": str(position_id),
        "version_id": str(version_id),
        "criteria": [item.model_dump(mode="json") for item in criteria],
    }
    return ReportLane(
        run_id=run_id,
        lane_id=lane_id,
        subject_ref=f"spec004-{str(run_id)[:8]}-{slug}",
        position_id=position_id,
        invitation_id=_id(run_id, f"{lane_id.value}:invitation"),
        applicant_id=_id(run_id, f"{lane_id.value}:applicant"),
        interview_session_id=_id(run_id, f"{lane_id.value}:session"),
        competency_model_version_id=version_id,
        version_source=source,
        criteria=criteria,
        fixture_rows={},
        fixture_digest=sha256_bytes(canonical_json_bytes(identity)),
        consent_required_purposes=CONSENT_PURPOSES,
        trace_namespace=f"controlproof:{run_id}:{lane_id.value}",
        seed_correlation_id=f"spec004-seed-{str(run_id)[:8]}-{slug}",
    )


def _e01_lane(run_id: UUID, lane_id: E01LaneId, arguments: dict[CitationMode, str]) -> ReportLane:
    criteria = []
    for code, mode, weight in E01_LANE_CRITERIA[lane_id]:
        criterion_id = _id(run_id, f"{lane_id.value}:{code}:criterion")
        argument = arguments.get(mode) if mode is not CitationMode.OTHER_CRITERION else None
        if mode is CitationMode.OTHER_CRITERION:
            argument = str(criteria[0].criterion_id)  # the lane's first, VALID criterion
        criteria.append(
            _criterion(
                run_id,
                lane_id,
                code=code,
                criterion_id=criterion_id,
                weight=weight,
                mode=mode,
                argument=argument,
            )
        )
    return _lane(
        run_id,
        lane_id,
        criteria=tuple(criteria),
        position_id=_id(run_id, f"{lane_id.value}:position"),
        version_id=_id(run_id, f"{lane_id.value}:version"),
        source=VersionSource.RUN_SEED,
    )


def e01_lanes(run_id: UUID) -> tuple[ReportLane, ...]:
    """The three E-01 lanes seeded first (the matrix needs the reference report's Evidence ID)."""
    return tuple(
        _e01_lane(run_id, lane_id, {})
        for lane_id in (
            E01LaneId.E01_REFERENCE,
            E01LaneId.E01_EVIDENCE_REMOVAL,
            E01LaneId.E01_STORAGE_PROBE,
        )
    )


def e01_matrix_lane(run_id: UUID, reference_evidence_id: UUID) -> ReportLane:
    return _e01_lane(
        run_id,
        E01LaneId.E01_CITATION_MATRIX,
        {
            CitationMode.NONEXISTENT: str(nonexistent_evidence_id(run_id)),
            CitationMode.OTHER_APPLICANT: str(reference_evidence_id),
        },
    )


def e02_version_body(version_key: str) -> dict[str, Any]:
    """Product API body for `POST /positions/{id}/competency-model-versions` (adapter contract)."""
    criteria = E02_VERSION_CRITERIA[version_key]
    return {
        "job_requirements": [
            {
                "requirement_type": "required",
                "statement": "Synthetic requirement for ControlProof E-02",
                "priority": 1,
                "criterion_code": criteria[0][0],
            }
        ],
        "criteria": [
            {
                "code": code,
                "name": f"E-02 synthetic criterion {code}",
                "description": f"{spec004_marker(CitationMode.VALID, None, score)} Synthetic E-02 criterion",
                "weight": weight,
                "verification_guide": dict(_VERIFICATION_GUIDE),
                "abstain_guidance": "Abstain without evidence",
                "common_questions": [],
                "required": True,
            }
            for code, score, weight in criteria
        ],
        "prohibited_topics": [],
        "interview_duration_minutes": 30,
        "interview_level": "junior",
        "axis_weights": dict(E02_AXIS_WEIGHTS[version_key]),
    }


def e02_lane(run_id: UUID, lane_id: E02LaneId, version: CriteriaVersionSnapshot) -> ReportLane:
    """Bind an E-02 lane to the latest published version read back from the product API."""
    scores = {}
    for key in ("v1", "v2"):
        weights = {code: weight for code, _, weight in E02_VERSION_CRITERIA[key]}
        if weights == {item.code: item.weight for item in version.criteria}:
            scores = {code: score for code, score, _ in E02_VERSION_CRITERIA[key]}
    if not scores:
        raise ValueError("published version does not match a Spec 004 E-02 version body")
    criteria = tuple(
        _criterion(
            run_id,
            lane_id,
            code=item.code,
            criterion_id=item.criterion_id,
            weight=item.weight,
            mode=CitationMode.VALID,
            score=scores[item.code],
        )
        for item in sorted(version.criteria, key=lambda value: value.code)
    )
    return _lane(
        run_id,
        lane_id,
        criteria=criteria,
        position_id=version.position_id,
        version_id=version.competency_model_version_id,
        source=VersionSource.PRODUCT_API_LATEST_PUBLISHED,
    )


def _position_rows(
    run_id: UUID, position_id: UUID, *, company_id: UUID, reviewer_id: UUID, name: str
) -> list[SeedRow]:
    return [
        SeedRow(
            "positions",
            {
                "company_id": company_id,
                "position_id": position_id,
                "title": f"ControlProof Spec004 {name} {run_id}",
                "description": "Synthetic local/test-only Spec 004 position",
                "submission_requirements": _submission_requirements(),
                "created_by": reviewer_id,
                "status": "active",
                "row_version": 1,
                "created_at": _FIXED_TIME,
            },
        ),
        SeedRow(
            "recruiting_stages",
            {
                "company_id": company_id,
                "recruiting_stage_id": _id(run_id, f"{position_id}:stage"),
                "position_id": position_id,
                "name": f"S4-{str(position_id)[:8]}",
                "sort_order": 1,
                "row_version": 1,
            },
        ),
    ]


def e02_position_rows(run_id: UUID, *, company_id: UUID, reviewer_id: UUID) -> tuple[SeedRow, ...]:
    return tuple(
        _position_rows(
            run_id,
            e02_position_id(run_id),
            company_id=company_id,
            reviewer_id=reviewer_id,
            name="E02",
        )
    )


def lane_rows(lane: ReportLane, *, company_id: UUID, reviewer_id: UUID) -> tuple[SeedRow, ...]:
    """Every row the seed adapter inserts for one lane (and removes, children first, at teardown)."""
    run_id = lane.run_id
    rows: list[SeedRow] = []
    if lane.version_source is VersionSource.RUN_SEED:
        rows.extend(
            _position_rows(
                run_id,
                lane.position_id,
                company_id=company_id,
                reviewer_id=reviewer_id,
                name=lane.lane_id.value,
            )
        )
        rows.append(
            SeedRow(
                "competency_model_versions",
                {
                    "company_id": company_id,
                    "competency_model_version_id": lane.competency_model_version_id,
                    "position_id": lane.position_id,
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
            )
        )
        rows.extend(
            SeedRow(
                "evaluation_criteria",
                {
                    "company_id": company_id,
                    "competency_model_version_id": lane.competency_model_version_id,
                    "criterion_id": criterion.criterion_id,
                    "code": criterion.code,
                    "name": f"E-01 synthetic criterion {criterion.code}",
                    "description": f"{criterion.marker} Synthetic E-01 criterion",
                    "weight": criterion.weight,
                    "verification_guide": dict(_VERIFICATION_GUIDE),
                    "abstain_guidance": "Abstain without evidence",
                    "common_questions": [],
                    "required": True,
                },
            )
            for criterion in lane.criteria
        )
    stage_id = _id(run_id, f"{lane.position_id}:stage")
    expires_at = _FIXED_TIME + timedelta(days=3650)
    raw = lane_credential(lane)
    slug = _slug(lane.lane_id)
    strategy_id = _id(run_id, f"{lane.lane_id.value}:strategy")
    asset_id = _id(run_id, f"{lane.lane_id.value}:final-video")
    rows.extend(
        [
            SeedRow(
                "invitations",
                {
                    "company_id": company_id,
                    "invitation_id": lane.invitation_id,
                    "position_id": lane.position_id,
                    "competency_model_version_id": lane.competency_model_version_id,
                    "applicant_id": lane.applicant_id,
                    "applicant_email_normalized": f"spec004-{run_id.hex}-{slug}@example.invalid",
                    "applicant_display_name": lane.subject_ref,
                    "submission_requirements": _submission_requirements(),
                    "token_hash": sha256_bytes(
                        f"spec004-token:{run_id}:{lane.lane_id.value}".encode()
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
                    "session_hash": _session_hash(raw),
                    "company_id": company_id,
                    "invitation_id": lane.invitation_id,
                    "applicant_id": lane.applicant_id,
                    "session_id": _id(run_id, f"{lane.lane_id.value}:applicant-session"),
                    "expires_at": expires_at,
                },
            ),
            SeedRow(
                "interview_strategies",
                {
                    "company_id": company_id,
                    "interview_strategy_id": strategy_id,
                    "invitation_id": lane.invitation_id,
                    "applicant_id": lane.applicant_id,
                    "competency_model_version_id": lane.competency_model_version_id,
                    "strategy_version": 1,
                    "common_topics": [],
                    "verification_points": [],
                    "follow_up_directions": {},
                    "time_budget": {"total_seconds": 600},
                    "required_evidence_plan": {},
                    "source_reference_candidates": [],
                    "model_config_version": "controlproof-fixed-v1",
                    "status": "ready",
                },
            ),
            SeedRow(
                "interview_sessions",
                {
                    "company_id": company_id,
                    "interview_session_id": lane.interview_session_id,
                    "invitation_id": lane.invitation_id,
                    "applicant_id": lane.applicant_id,
                    "interview_strategy_id": strategy_id,
                    "competency_model_version_id": lane.competency_model_version_id,
                    "state": "completed",
                    "session_sequence": 1,
                    "row_version": 1,
                    "degraded_modes": [],
                    "created_at": _FIXED_TIME,
                    "started_at": _FIXED_TIME,
                    "completed_at": _FIXED_TIME + timedelta(minutes=10),
                },
            ),
        ]
    )
    for index, criterion in enumerate(lane.criteria):
        offset = index * _TURN_SPACING_MS
        for sequence, (turn_id, speaker, text) in enumerate(
            (
                (
                    criterion.question_turn_id,
                    "interviewer",
                    f"Synthetic question for {criterion.code}",
                ),
                (criterion.answer_turn_id, "applicant", f"Synthetic answer for {criterion.code}"),
            ),
            start=1 + 2 * index,
        ):
            rows.append(
                SeedRow(
                    "interview_turns",
                    {
                        "company_id": company_id,
                        "turn_id": turn_id,
                        "interview_session_id": lane.interview_session_id,
                        "sequence": sequence,
                        "speaker": speaker,
                        "status": "final",
                        "text": text,
                        "target_criterion_id": criterion.criterion_id,
                        "idempotency_key": f"spec004-{turn_id}",
                        "model_config_version": "controlproof-fixed-v1",
                        "finalized_at": _FIXED_TIME + timedelta(milliseconds=offset),
                    },
                )
            )
        rows.append(
            SeedRow(
                "transcript_segments",
                {
                    "company_id": company_id,
                    "transcript_segment_id": criterion.transcript_segment_id,
                    "interview_session_id": lane.interview_session_id,
                    "turn_id": criterion.answer_turn_id,
                    "speaker": "applicant",
                    "text": f"Synthetic transcript for {criterion.code}",
                    "confidence": 1.0,
                    "session_start_ms": offset + _ANSWER_START_MS,
                    "session_end_ms": offset + _ANSWER_END_MS,
                    "source_audio_key": f"companies/{company_id}/controlproof/{asset_id}",
                    "version": 1,
                    "created_at": _FIXED_TIME,
                },
            )
        )
    rows.append(
        SeedRow(
            "recording_assets",
            {
                "company_id": company_id,
                "recording_asset_id": asset_id,
                "interview_session_id": lane.interview_session_id,
                "asset_type": "final_video",
                "object_key": f"companies/{company_id}/controlproof/{asset_id}",
                "content_hash": "0" * 64,
                "duration_ms": len(lane.criteria) * _TURN_SPACING_MS,
                "status": "ready",
                "missing_ranges": [],
                "created_at": _FIXED_TIME,
            },
        )
    )
    return tuple(rows)
