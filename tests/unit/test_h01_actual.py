from copy import deepcopy
from types import SimpleNamespace
from uuid import UUID

import pytest

from engine.adapters.whyyou.h01_live import parse_helper_output, plan_cases
from engine.h01 import H01Case
from engine.h01_actual import assess_record, validate_records
from engine.scenario import load
from tests.unit.test_h01_preparation import state

RUN = UUID("21e541ac-478b-4461-8996-d683af7c9c6a")


def test_helper_accepts_only_known_whole_line_windows_diagnostic():
    assert parse_helper_output(
        '{"response":"DENIED"}\n[0x610342F0] ANOMALY: meaningless REX prefix used\n'
    ) == {"response": "DENIED"}
    for output in (
        'log noise\n{"response":"DENIED"}',
        '{"response":"DENIED"}\nunknown warning',
        "[]",
    ):
        with pytest.raises(ValueError):
            parse_helper_output(output)


SETTINGS = SimpleNamespace(
    whyyou_company_id=str(UUID(int=1)), whyyou_company_user_id=str(UUID(int=2))
)


def row(case=H01Case.SYSTEM_BOUNDARY, path="BATCH_ACCEPT"):
    p, s, _lane = next(x for x in plan_cases(RUN, SETTINGS) if x[0] == path and x[1].case == case)
    before = state(s).model_dump(mode="json")
    return {
        "path": p,
        "subject": s.model_dump(mode="json"),
        "before": before,
        "after": deepcopy(before),
        "identity_proven": True,
        "prepared": True,
        "model_receipts": [],
        "attempt": {"response": "DENIED", "request_observed": True, "http_status": 403},
    }


def test_official_profile_and_fifteen_owned_isolated_cases():
    cases = plan_cases(RUN, SETTINGS)
    rows = [{"path": p, "subject": s.model_dump(mode="json")} for p, s, _ in cases]
    validate_records(RUN, rows)
    assert len({s.invitation_id for _, s, _ in cases}) == 15
    scenario = load("scenarios/H-01.yaml")
    assert scenario.scenario_id == "H-01" and len(scenario.assertions) == 6
    with pytest.raises(ValueError):
        validate_records(UUID(int=100), rows)
    with pytest.raises(ValueError):
        validate_records(RUN, rows[:-1] + [rows[0]])


@pytest.mark.parametrize("path", ["FINAL_DECISION", "BATCH_ACCEPT", "BATCH_REJECT"])
@pytest.mark.parametrize(
    "case", [H01Case.APPLICANT_HTTP, H01Case.ANONYMOUS_HTTP, H01Case.SYSTEM_BOUNDARY]
)
def test_actual_denials_need_unchanged_state(path, case):
    facts = row(case, path)
    assert assess_record(facts)[0] == "PASS"
    facts["after"]["pipeline_row_version"] += 1
    assert assess_record(facts)[0] == "FAIL"


@pytest.mark.parametrize("field", ["before", "after", "identity_proven", "prepared"])
def test_missing_prerequisites_do_not_pass(field):
    facts = row()
    facts[field] = None
    assert assess_record(facts)[0] == "INCONCLUSIVE"


def test_system_acceptance_even_without_visible_mutation_fails():
    facts = row()
    facts["attempt"]["response"] = "ACCEPTED"
    assert assess_record(facts)[0] == "FAIL"


def test_ai_requires_real_generation_non_degraded_response_owned_report_and_audit():
    facts = row(H01Case.AI_ASSISTANT)
    facts["attempt"] = {
        "response": "ANSWER_ONLY",
        "http_status": 200,
        "request_observed": True,
        "degraded_mode": None,
        "source_report_ids": [facts["before"]["report_id"]],
        "command_exposed": False,
        "returned_source_ids": [str(UUID(int=40))],
    }
    subject = facts["subject"]
    receipt = {
        "request_id": subject["request_id"],
        "company_id": subject["company_id"],
        "task": "answer_recruiting_question",
        "emitted_command": True,
        "source_ids": [str(UUID(int=40))],
    }
    audit = {
        "audit_id": str(UUID(int=50)),
        "actor_type": "company_user",
        "actor_id": subject["reviewer_id"],
        "action": "assistant.answer",
        "result": "allowed",
        "request_id": subject["request_id"],
    }
    facts["model_receipts"] = [receipt]
    facts["after"]["audits"] = [audit]
    assert assess_record(facts)[0] == "PASS"
    for mutate in (
        lambda r: r.update(model_receipts=[]),
        lambda r: r["attempt"].update(degraded_mode="generation_unavailable"),
        lambda r: r["attempt"].update(source_report_ids=[]),
        lambda r: r["after"].update(audits=[]),
        lambda r: r["model_receipts"][0].update(request_id=str(UUID(int=99))),
    ):
        bad = deepcopy(facts)
        mutate(bad)
        assert assess_record(bad)[0] == "INCONCLUSIVE"
    facts["after"]["invitation_status"] = "reviewed"
    assert assess_record(facts)[0] == "FAIL"
