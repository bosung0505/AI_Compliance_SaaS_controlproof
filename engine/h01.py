"""H-01 preparation contracts; no official Run/profile or live-result publication."""

from enum import StrEnum
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid5

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from engine.models import Verdict

NAMESPACE = UUID("c63883d8-ec38-5f91-9c96-b16598f46db8")


class H01Case(StrEnum):
    COMPANY_CONTROL = "COMPANY_CONTROL"
    APPLICANT_HTTP = "APPLICANT_HTTP"
    ANONYMOUS_HTTP = "ANONYMOUS_HTTP"
    SYSTEM_BOUNDARY = "SYSTEM_BOUNDARY"
    AI_ASSISTANT = "AI_ASSISTANT"


class H01Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class H01Subject(H01Model):
    run_id: UUID
    case: H01Case
    company_id: UUID
    reviewer_id: UUID
    target_stage_id: UUID
    applicant_id: UUID
    invitation_id: UUID
    request_id: UUID

    @model_validator(mode="after")
    def canonical_ids(self):
        for name in ("applicant_id", "invitation_id", "request_id"):
            suffix = name.removesuffix("_id")
            if getattr(self, name) != uuid5(NAMESPACE, f"{self.run_id}:{self.case}:{suffix}"):
                raise ValueError("subject identifiers must belong to this Run and case")
        return self

    def assert_owned(self):
        return type(self).model_validate(self.model_dump())


def build_subjects(run_id, *, company_id, reviewer_id, target_stage_id):
    run_id = UUID(str(run_id))
    return tuple(
        H01Subject(
            run_id=run_id,
            case=case,
            company_id=company_id,
            reviewer_id=reviewer_id,
            target_stage_id=target_stage_id,
            **{
                name + "_id": uuid5(NAMESPACE, f"{run_id}:{case}:{name}")
                for name in ("applicant", "invitation", "request")
            },
        )
        for case in H01Case
    )


class H01Review(H01Model):
    review_id: UUID
    company_user_id: UUID
    stage_id: UUID | None
    review_type: str = "final_decision"
    value_digest: str | None = None
    reason_digest: str | None = None


class H01Audit(H01Model):
    audit_id: UUID
    actor_type: str
    actor_id: UUID
    action: str
    result: str
    request_id: UUID


class H01State(H01Model):
    company_id: UUID
    invitation_id: UUID
    report_id: UUID | None
    report_status: str | None
    invitation_status: str
    recruiting_stage_id: UUID | None
    pipeline_row_version: int = Field(ge=0)
    reviews: tuple[H01Review, ...]
    audits: tuple[H01Audit, ...]

    def business(self):
        return self.model_dump(mode="json", exclude={"audits"})


class H01Attempt(H01Model):
    case: H01Case
    request_id: UUID
    response: Literal["ACCEPTED", "DENIED", "ERROR", "UNAVAILABLE"]
    identity_proven: bool
    request_observed: bool
    denial_record_present: bool
    http_status: int | None = None


class H01Observation(H01Model):
    subject: H01Subject
    response: Literal["ACCEPTED", "DENIED", "ERROR", "UNAVAILABLE"]
    identity_proven: bool
    prerequisites_valid: bool
    request_observed: bool
    denial_record_present: bool
    before: H01State | None
    after: H01State | None


class H01Assessment(H01Model):
    case: H01Case
    status: Verdict
    reason: str
    changed_fields: tuple[str, ...] = ()


def ready_state(state):
    return bool(
        state
        and state.report_id
        and state.report_status == "ready"
        and state.invitation_status == "completed"
        and not state.reviews
    )


def assess_case(observation):
    obs = observation
    subject, before, after = obs.subject, obs.before, obs.after

    def result(status, reason, changed=()):
        return H01Assessment(
            case=subject.case, status=status, reason=reason, changed_fields=changed
        )

    subject.assert_owned()
    if before is None or after is None:
        return result("INCONCLUSIVE", "STATE_EVIDENCE_MISSING")
    if any(
        s.company_id != subject.company_id or s.invitation_id != subject.invitation_id
        for s in (before, after)
    ):
        return result("INCONCLUSIVE", "STATE_SUBJECT_MISMATCH")
    if not (
        obs.prerequisites_valid
        and ready_state(before)
        and obs.identity_proven
        and obs.request_observed
    ):
        return result("INCONCLUSIVE", "PRECONDITION_OR_IDENTITY_UNPROVEN")
    old, new = before.business(), after.business()
    changed = tuple(sorted(key for key in old if old[key] != new[key]))
    if subject.case != H01Case.COMPANY_CONTROL:
        if changed or obs.response == "ACCEPTED":
            return result("FAIL", "UNAUTHORIZED_ACCEPTANCE_OR_STATE_CHANGE", changed)
        if obs.response != "DENIED" or not obs.denial_record_present:
            return result("INCONCLUSIVE", "DENIAL_EVIDENCE_MISSING")
        return result("PASS", "DENIED_WITHOUT_DECISION_CHANGE")
    if obs.response in {"ERROR", "UNAVAILABLE"}:
        return result("INCONCLUSIVE", "CONTROL_RESPONSE_UNPROVEN")
    consistent = (
        obs.response == "ACCEPTED"
        and after.report_id == before.report_id
        and after.report_status == before.report_status
        and after.recruiting_stage_id == subject.target_stage_id
        and after.pipeline_row_version == before.pipeline_row_version + 1
        and after.invitation_status == "reviewed"
        and len(after.reviews) == 1
        and after.reviews[0].review_type == "final_decision"
        and after.reviews[0].company_user_id == subject.reviewer_id
        and after.reviews[0].stage_id == subject.target_stage_id
    )
    if not consistent:
        return result("FAIL", "CONTROL_DECISION_INCONSISTENT", changed)
    matching_audit = [
        a
        for a in after.audits
        if a.request_id == subject.request_id
        and a.actor_type == "company_user"
        and a.actor_id == subject.reviewer_id
        and a.action == "final_decision.create"
        and a.result == "created"
    ]
    if len(matching_audit) != 1:
        return result("INCONCLUSIVE", "CONTROL_AUDIT_UNPROVEN", changed)
    return result("PASS", "HUMAN_CONTROL_SAVED_ONCE", changed)


def assess_all(observations, *, cleanup_succeeded):
    cases = [obs.subject.case for obs in observations]
    if not cleanup_succeeded:
        return Verdict.INCONCLUSIVE
    if len(cases) != len(H01Case) or set(cases) != set(H01Case):
        return Verdict.INCONCLUSIVE
    if any(
        len({getattr(obs.subject, field) for obs in observations}) != 1
        for field in ("run_id", "company_id", "reviewer_id", "target_stage_id")
    ):
        return Verdict.INCONCLUSIVE
    results = [assess_case(obs).status for obs in observations]
    if Verdict.FAIL in results:
        return Verdict.FAIL
    if Verdict.INCONCLUSIVE in results:
        return Verdict.INCONCLUSIVE
    return Verdict.PASS


def load_preparation(path=None):
    source = (
        Path(path)
        if path
        else Path(__file__).resolve().parents[1] / "scenarios/_H-01-preparation.yaml"
    )
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    if (
        not isinstance(data, dict)
        or set(data) != {"schema", "scenario_id", "version", "stage", "actual_status", "cases"}
        or data.get("schema") != "controlproof.h01-preparation.v1"
        or data.get("scenario_id") != "H-01"
        or data.get("version") != "0.1.0"
        or data.get("actual_status") != "NOT_RUN"
        or type(data.get("stage")) is not int
        or data.get("stage") != 1
        or data.get("cases") != [c.value for c in H01Case]
    ):
        raise ValueError("invalid H-01 preparation definition")
    return data
