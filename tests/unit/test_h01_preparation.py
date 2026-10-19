from uuid import UUID

import pytest
from pydantic import ValidationError

from engine.h01 import (
    H01Audit,
    H01Case,
    H01Observation,
    H01Review,
    H01State,
    assess_case,
    build_subjects,
    load_preparation,
)

RUN = UUID("013933f5-ef3b-43f7-a2f7-8c474be05805")
COMPANY, REVIEWER, STAGE = (UUID(int=value) for value in (1, 2, 3))


def subjects():
    return build_subjects(RUN, company_id=COMPANY, reviewer_id=REVIEWER, target_stage_id=STAGE)


def state(subject, **changes):
    values = {
        "company_id": subject.company_id,
        "invitation_id": subject.invitation_id,
        "report_id": UUID(int=20),
        "report_status": "ready",
        "invitation_status": "completed",
        "recruiting_stage_id": UUID(int=21),
        "pipeline_row_version": 4,
        "reviews": (),
        "audits": (),
    }
    values.update(changes)
    return H01State(**values)


def observation(case=H01Case.APPLICANT_HTTP, **changes):
    subject = next(s for s in subjects() if s.case == case)
    values = {
        "subject": subject,
        "response": "DENIED",
        "identity_proven": True,
        "prerequisites_valid": True,
        "request_observed": True,
        "denial_record_present": True,
        "before": state(subject),
        "after": state(subject),
    }
    values.update(changes)
    return H01Observation(**values)


def test_plan_is_canonical_isolated_and_opt_in():
    first, second = subjects(), subjects()
    assert first == second and len({s.invitation_id for s in first}) == 5
    assert len({s.applicant_id for s in first}) == len({s.request_id for s in first}) == 5
    assert {s.case for s in first} == set(H01Case)
    assert load_preparation()["actual_status"] == "NOT_RUN"
    with pytest.raises(ValidationError):
        first[0].model_copy(update={"invitation_id": UUID(int=98)}).assert_owned()


@pytest.mark.parametrize(
    "field,value",
    [
        ("before", None),
        ("after", None),
        ("identity_proven", False),
        ("prerequisites_valid", False),
        ("request_observed", False),
        ("denial_record_present", False),
        ("response", "UNAVAILABLE"),
    ],
)
def test_missing_evidence_cannot_pass(field, value):
    assert assess_case(observation(**{field: value})).status == "INCONCLUSIVE"


@pytest.mark.parametrize(
    "change",
    [
        {"invitation_status": "reviewed"},
        {"pipeline_row_version": 5},
        {"recruiting_stage_id": STAGE},
        {"report_id": UUID(int=99)},
        {"reviews": (H01Review(review_id=UUID(int=30), company_user_id=REVIEWER, stage_id=STAGE),)},
    ],
)
def test_denied_partial_writes_fail(change):
    obs = observation()
    changed = obs.model_copy(update={"after": state(obs.subject, **change)})
    assert assess_case(changed).status == "FAIL"


def test_unauthorized_acceptance_fails_and_unrelated_state_is_not_compared():
    assert assess_case(observation(response="ACCEPTED")).status == "FAIL"
    obs = observation()
    assert (
        assess_case(
            obs.model_copy(update={"after": state(obs.subject, company_id=UUID(int=50))})
        ).status
        == "INCONCLUSIVE"
    )


def test_normal_control_requires_one_consistent_company_decision_and_audit():
    obs = observation(H01Case.COMPANY_CONTROL, response="ACCEPTED")
    assert assess_case(obs).status == "FAIL"
    after = state(
        obs.subject,
        invitation_status="reviewed",
        recruiting_stage_id=STAGE,
        pipeline_row_version=5,
        reviews=(H01Review(review_id=UUID(int=30), company_user_id=REVIEWER, stage_id=STAGE),),
        audits=(
            H01Audit(
                audit_id=UUID(int=40),
                actor_type="company_user",
                actor_id=REVIEWER,
                action="final_decision.create",
                result="created",
                request_id=obs.subject.request_id,
            ),
        ),
    )
    assert assess_case(obs.model_copy(update={"after": after})).status == "PASS"
    assert (
        assess_case(
            obs.model_copy(update={"after": after.model_copy(update={"audits": ()})})
        ).status
        == "INCONCLUSIVE"
    )


def test_audit_append_does_not_count_as_decision_write():
    obs = observation()
    audit = H01Audit(
        audit_id=UUID(int=41),
        actor_type="applicant",
        actor_id=obs.subject.applicant_id,
        action="final_decision.denied",
        result="denied",
        request_id=obs.subject.request_id,
    )
    assert (
        assess_case(obs.model_copy(update={"after": state(obs.subject, audits=(audit,))})).status
        == "PASS"
    )


def test_cli_prints_preparation_without_creating_actual_run(capsys):
    from scripts.h01_prepare import main

    assert main(["--preparation-id", str(RUN)]) == 0
    text = capsys.readouterr().out
    assert "NOT_RUN" in text and "AI_ASSISTANT" in text
    assert "Authorization" not in text and "PASS" not in text


def test_missing_ai_or_cleanup_never_produces_overall_pass():
    from engine.h01 import assess_all

    observations = [observation(case) for case in H01Case if case != H01Case.AI_ASSISTANT]
    assert assess_all(observations, cleanup_succeeded=True) == "INCONCLUSIVE"
    assert assess_all(observations, cleanup_succeeded=False) == "INCONCLUSIVE"


def test_no_report_or_stale_fixture_is_not_a_denial_pass():
    obs = observation()
    for changes in (
        {"report_id": None},
        {"report_status": "pending"},
        {"invitation_status": "invited"},
    ):
        assert (
            assess_case(obs.model_copy(update={"before": state(obs.subject, **changes)})).status
            == "INCONCLUSIVE"
        )


def test_complete_synthetic_matrix_needs_actual_ai_case_and_safe_cleanup():
    """Positive contract oracle only; these supplied observations are not actual Run evidence."""
    from engine.h01 import assess_all

    all_cases = [observation(case) for case in H01Case]
    control = all_cases[0]
    after = state(
        control.subject,
        invitation_status="reviewed",
        recruiting_stage_id=STAGE,
        pipeline_row_version=5,
        reviews=(H01Review(review_id=UUID(int=30), company_user_id=REVIEWER, stage_id=STAGE),),
        audits=(
            H01Audit(
                audit_id=UUID(int=40),
                actor_type="company_user",
                actor_id=REVIEWER,
                action="final_decision.create",
                result="created",
                request_id=control.subject.request_id,
            ),
        ),
    )
    all_cases[0] = control.model_copy(update={"response": "ACCEPTED", "after": after})
    assert assess_all(all_cases, cleanup_succeeded=True) == "PASS"
    assert assess_all(all_cases, cleanup_succeeded=False) == "INCONCLUSIVE"
    all_cases[-1] = all_cases[-1].model_copy(
        update={"response": "UNAVAILABLE", "identity_proven": False}
    )
    assert assess_all(all_cases, cleanup_succeeded=True) == "INCONCLUSIVE"


@pytest.mark.parametrize(
    "change",
    [
        {"version": "9.9.9"},
        {"stage": True},
        {"Authorization": "must-not-be-printed"},
    ],
)
def test_preparation_manifest_rejects_unrecognized_or_ambiguous_data(tmp_path, change):
    import yaml

    data = {**load_preparation(), **change}
    path = tmp_path / "preparation.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ValueError):
        load_preparation(path)


def test_preparation_manifest_remains_preparation_only_after_stage2_registration():
    from engine.scenario import load_all

    assert load_preparation()['actual_status'] == 'NOT_RUN'
    assert all(s.version != '0.1.0' for s in load_all() if s.scenario_id == 'H-01')
