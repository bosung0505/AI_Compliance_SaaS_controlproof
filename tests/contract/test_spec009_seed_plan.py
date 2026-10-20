"""T007·T008 — Spec 009 seed plan: Run-scoped synthetic invitations for N-01 and N-03 lanes."""

from __future__ import annotations

import hashlib
import hmac
import json
from collections import Counter
from uuid import UUID, uuid4

import pytest

from engine.models import ExecutionProfile, N01LaneId, N03LaneId, Spec009SubjectLane
from seeds.spec009_subjects import build_spec009_seed_plan

PEPPER = b"local-development-pepper"
COMPANY = UUID("11111111-1111-4111-8111-111111111111")
REVIEWER = UUID("22222222-2222-4222-8222-222222222222")
COMMON = ["positions", "competency_model_versions", "evaluation_criteria", "recruiting_stages"]


def _plan(profile: ExecutionProfile, run_id: UUID | None = None):
    return build_spec009_seed_plan(
        run_id or uuid4(), profile=profile, company_id=COMPANY, reviewer_id=REVIEWER
    )


def _hmac(raw: str) -> str:
    return hmac.new(PEPPER, raw.encode("utf-8"), hashlib.sha256).hexdigest()


def _ids(plan) -> list[str]:
    return sorted(
        str(value)
        for row in plan.rows
        for key, value in row.values.items()
        if key.endswith("_id") and key not in {"company_id", "created_by"}
    )


def test_n01_plan_seeds_two_invited_token_lanes() -> None:
    plan = _plan(ExecutionProfile.N01_NOTICE_V1)
    assert tuple(lane.lane_id for lane in plan.lanes) == tuple(N01LaneId)
    assert {lane.seed_kind for lane in plan.lanes} == {"invited-token"}
    tables = [row.table for row in plan.rows]
    assert tables[:4] == COMMON
    assert Counter(tables[4:]) == {"invitations": 2, "applicant_access_tokens": 2}
    for subject in plan.subjects:
        assert subject.raw_invitation_token and subject.raw_session_cookie is None
        invitation = plan.row_for("invitations", subject.invitation_id)
        token = plan.row_for("applicant_access_tokens", subject.invitation_id)
        assert invitation.values["status"] == "invited"
        assert invitation.values["identity_verified_at"] is None
        assert invitation.values["last_state_actor_type"] == "system"
        assert invitation.values["recruiting_stage_id"] == plan.stage_id
        assert invitation.values["pipeline_row_version"] == 1
        assert invitation.values["row_version"] == 1
        run_prefix = str(plan.run_id)[:8]
        assert subject.display_name == f"CP-N01-{subject.lane_id.value}-{run_prefix}"
        assert invitation.values["applicant_display_name"] == subject.display_name
        expected_hash = _hmac(subject.raw_invitation_token)
        assert invitation.values["token_hash"] == expected_hash == token.values["token_hash"]
        assert token.values["consumed_at"] is None
        assert token.values["applicant_id"] == subject.applicant_id
        assert token.values["expires_at"] == invitation.values["expires_at"]


def test_n03_plan_seeds_two_identity_verified_session_lanes() -> None:
    plan = _plan(ExecutionProfile.N03_STALE_CONSENT_V1)
    assert tuple(lane.lane_id for lane in plan.lanes) == tuple(N03LaneId)
    assert {lane.seed_kind for lane in plan.lanes} == {"identity-verified-session"}
    tables = [row.table for row in plan.rows]
    assert tables[:4] == COMMON
    assert Counter(tables[4:]) == {
        "invitations": 2,
        "applicant_profiles": 2,
        "applicant_access_sessions": 2,
    }
    for subject in plan.subjects:
        assert subject.raw_session_cookie and subject.raw_invitation_token is None
        invitation = plan.row_for("invitations", subject.invitation_id)
        session = plan.row_for("applicant_access_sessions", subject.invitation_id)
        assert invitation.values["status"] == "identity_verified"
        assert invitation.values["identity_verified_at"] is not None
        assert session.values["session_hash"] == _hmac(subject.raw_session_cookie)
        # No token row exists, so the invitation token hash can never be exchanged.
        assert invitation.values["token_hash"] != session.values["session_hash"]


def test_common_rows_match_the_n02_shape() -> None:
    plan = _plan(ExecutionProfile.N01_NOTICE_V1)
    position = plan.rows[0]
    assert position.values["title"] == f"ControlProof N01/N03 {plan.run_id}"
    assert position.values["status"] == "active"
    assert any(item["required"] and item["enabled"] for item in position.values["submission_requirements"])
    guide = plan.rows[2].values["verification_guide"]
    assert guide["observable_dimensions"] and 60 <= guide["time_budget_seconds"] <= 1800
    assert plan.rows[1].values["interview_level"] in {"entry", "junior", "senior"}


@pytest.mark.parametrize("profile", [ExecutionProfile.N01_NOTICE_V1, ExecutionProfile.N03_STALE_CONSENT_V1])
def test_same_run_is_deterministic_and_other_runs_share_no_ids(profile) -> None:
    run_id = uuid4()
    first, second, other = _plan(profile, run_id), _plan(profile, run_id), _plan(profile)
    assert first.digest == second.digest
    assert _ids(first) == _ids(second)
    assert first.lanes == second.lanes
    assert not set(_ids(first)) & set(_ids(other))
    assert first.digest != other.digest


@pytest.mark.parametrize("profile", [ExecutionProfile.N01_NOTICE_V1, ExecutionProfile.N03_STALE_CONSENT_V1])
def test_raw_credentials_never_leave_the_definition(profile) -> None:
    plan = _plan(profile)
    raws = [
        value
        for subject in plan.subjects
        for value in (subject.raw_invitation_token, subject.raw_session_cookie)
        if value
    ]
    assert len(raws) == 2
    surfaces = [
        repr(plan),
        json.dumps(plan.manifest(), sort_keys=True),
        json.dumps([row.values for row in plan.rows], default=str),
    ]
    for subject in plan.subjects:
        surfaces.append(json.dumps(subject.subject_payload()))
        surfaces.append(subject.lane.model_dump_json())
        surfaces.append(repr(subject))
    for raw in raws:
        assert all(raw not in surface for surface in surfaces)


def test_subject_payload_carries_the_consent_adapter_keys() -> None:
    plan = _plan(ExecutionProfile.N03_STALE_CONSENT_V1)
    payload = plan.subject_payload(N03LaneId.STALE)
    assert {"run_id", "lane_id", "subject_ref", "invitation_id", "applicant_id"} <= set(payload)
    assert payload["schema_version"] == "controlproof.spec009-subject-lane.v1"
    assert Spec009SubjectLane.model_validate(payload) == plan.by_lane(N03LaneId.STALE).lane


def test_profile_outside_spec009_is_rejected() -> None:
    with pytest.raises(ValueError):
        _plan(ExecutionProfile.N02_CONSENT_ORDER_V1)


def test_lane_rejects_a_seed_kind_from_the_other_profile() -> None:
    lane = _plan(ExecutionProfile.N01_NOTICE_V1).lanes[0]
    with pytest.raises(ValueError):
        Spec009SubjectLane.model_validate(lane.model_dump() | {"seed_kind": "identity-verified-session"})
