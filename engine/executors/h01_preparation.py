"""Preparation driver with injected lifecycle; no official Run registration or live binding."""

from typing import Literal, Protocol

from engine.h01 import (
    H01Attempt,
    H01Case,
    H01Model,
    H01Observation,
    H01State,
    H01Subject,
    assess_all,
    ready_state,
)
from engine.models import Verdict


class H01Lifecycle(Protocol):
    def prepare(self, subject: H01Subject) -> bool: ...
    def observe(self, subject: H01Subject) -> H01State: ...
    def attempt(self, subject: H01Subject) -> H01Attempt: ...
    def cleanup(self, subjects: tuple[H01Subject, ...]) -> bool: ...


class H01PreparationResult(H01Model):
    actual_status: Literal["NOT_RUN"] = "NOT_RUN"
    observations: tuple[H01Observation, ...]
    assessment: Verdict
    cleanup_succeeded: bool
    errors: tuple[str, ...]


def execute_preparation(subjects, lifecycle: H01Lifecycle):
    subjects = tuple(subjects)
    if (
        len(subjects) != len(H01Case)
        or {s.case for s in subjects} != set(H01Case)
        or len({s.run_id for s in subjects}) != 1
        or len({s.company_id for s in subjects}) != 1
        or len({s.reviewer_id for s in subjects}) != 1
        or len({s.target_stage_id for s in subjects}) != 1
    ):
        raise ValueError("one canonical subject per case from one Run/company is required")
    for subject in subjects:
        subject.assert_owned()
    registered, observations, errors = [], [], []
    cleanup_succeeded = False
    try:
        for subject in subjects:
            registered.append(subject)  # preparation can partially create resources then fail
            before = after = None
            valid = False
            attempt = H01Attempt(
                case=subject.case,
                request_id=subject.request_id,
                response="UNAVAILABLE",
                identity_proven=False,
                request_observed=False,
                denial_record_present=False,
            )
            phase = "PREPARE"
            try:
                prepared = lifecycle.prepare(subject)
                phase = "BEFORE_OBSERVE"
                before = H01State.model_validate(lifecycle.observe(subject))
                valid = (
                    prepared is True
                    and ready_state(before)
                    and before.company_id == subject.company_id
                    and before.invitation_id == subject.invitation_id
                )
                if valid:
                    phase = "ATTEMPT"
                    actual = H01Attempt.model_validate(lifecycle.attempt(subject))
                    if actual.case != subject.case or actual.request_id != subject.request_id:
                        raise ValueError("attempt does not match case/request")
                    attempt = actual
            except Exception as error:  # noqa: BLE001 - preserve failure class, not provider data
                errors.append(f"{subject.case}:{phase}:{type(error).__name__}")
            finally:
                try:
                    after = H01State.model_validate(lifecycle.observe(subject))
                except Exception as error:  # noqa: BLE001
                    errors.append(f"{subject.case}:OBSERVE:{type(error).__name__}")
            observations.append(
                H01Observation(
                    subject=subject,
                    before=before,
                    after=after,
                    prerequisites_valid=valid,
                    response=attempt.response,
                    identity_proven=attempt.identity_proven,
                    request_observed=attempt.request_observed,
                    denial_record_present=attempt.denial_record_present,
                )
            )
    finally:
        try:
            cleanup_succeeded = lifecycle.cleanup(tuple(registered)) is True
        except Exception as error:  # noqa: BLE001 - cleanup must not erase original error
            errors.append(f"CLEANUP:{type(error).__name__}")
    assessment = assess_all(observations, cleanup_succeeded=cleanup_succeeded)
    if errors and assessment == Verdict.PASS:
        assessment = Verdict.INCONCLUSIVE
    return H01PreparationResult(
        observations=tuple(observations),
        assessment=assessment,
        cleanup_succeeded=cleanup_succeeded,
        errors=tuple(errors),
    )
