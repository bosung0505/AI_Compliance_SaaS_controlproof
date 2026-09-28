from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest

from engine.adapters.whyyou.decisions import DecisionContractError, WhyYouDecisionAdapter
from engine.adapters.whyyou.effects import WhyYouEffectAdapter
from engine.models import DecisionPathId, Phase, Presence
from tests.fixtures.spec002 import EVENT_ID, OPERATION_ID, RUN_ID

ACCEPT_STAGE_ID = UUID("00000000-0000-7000-8000-000000000501")
REJECT_STAGE_ID = UUID("00000000-0000-7000-8000-000000000502")
INVITATION_ID = UUID("00000000-0000-7000-8000-000000000503")
POSITION_ID = UUID("00000000-0000-7000-8000-000000000504")
COMPANY_USER_ID = UUID("00000000-0000-7000-8000-000000000505")


class Response:
    def __init__(self, status_code=200, body=None):
        self.status_code = status_code
        self._body = body or {}

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP_{self.status_code}")


class RecordingHttp:
    def __init__(self, *, batch_status=409, batch_body=None):
        self.batch_status = batch_status
        self.batch_body = batch_body or {
            "code": "REPORT_NOT_AVAILABLE",
            "detail": "Final report is not available.",
        }
        self.calls = []

    def get(self, path, **kwargs):
        self.calls.append(("GET", path, kwargs))
        if path == "/openapi.json":
            return Response(
                body={
                    "paths": {
                        "/v1/invitations/{invitation_id}/final-decisions": {
                            "post": {"operationId": "recordHumanFinalDecision"}
                        },
                        "/v1/positions/{position_id}/invitations/recruiting-stage": {
                            "patch": {"operationId": "moveApplicantsToRecruitingStage"}
                        },
                    }
                }
            )
        if path == "/v1/recruiting-stages":
            return Response(
                body={
                    "items": [
                        {
                            "recruiting_stage_id": str(ACCEPT_STAGE_ID),
                            "position_id": str(POSITION_ID),
                            "name": "최종합격",
                        },
                        {
                            "recruiting_stage_id": str(REJECT_STAGE_ID),
                            "position_id": str(POSITION_ID),
                            "name": "불합격",
                        },
                    ]
                }
            )
        raise AssertionError(path)

    def post(self, path, **kwargs):
        self.calls.append(("POST", path, kwargs))
        return Response(
            409,
            {"code": "REPORT_NOT_AVAILABLE", "detail": "Final report is not available."},
        )

    def patch(self, path, **kwargs):
        self.calls.append(("PATCH", path, kwargs))
        return Response(self.batch_status, self.batch_body)


def _settings():
    return SimpleNamespace(
        whyyou_company_user_id=str(COMPANY_USER_ID),
        whyyou_database_url="postgresql+psycopg://local:local@localhost/test",
    )


def _subject():
    return {
        "subject_ref": "candidate-01",
        "company_id": "00000000-0000-7000-8000-000000000506",
        "company_user_id": str(COMPANY_USER_ID),
        "position_id": str(POSITION_ID),
        "invitation_id": str(INVITATION_ID),
        "pipeline_row_version": 1,
    }


def test_two_openapi_operations_expand_to_three_canonical_company_decision_paths():
    http = RecordingHttp()
    adapter = WhyYouDecisionAdapter(
        _settings(), SimpleNamespace(http=http), source_commit="b" * 40
    )

    capabilities = adapter.capabilities(subject=_subject())

    assert [item.path_id for item in capabilities] == list(DecisionPathId)
    assert {item.operation_id for item in capabilities} == {
        "recordHumanFinalDecision",
        "moveApplicantsToRecruitingStage",
    }
    assert capabilities[0].target_stage_id == ACCEPT_STAGE_ID
    assert capabilities[1].target_stage_id == ACCEPT_STAGE_ID
    assert capabilities[2].target_stage_id == REJECT_STAGE_ID
    assert all(item.source_commit == "b" * 40 for item in capabilities)


def test_each_path_uses_company_actor_and_returns_explicit_sanitized_refusal():
    raw_key = "controlproof-secret-idempotency-key"
    http = RecordingHttp()
    adapter = WhyYouDecisionAdapter(
        _settings(), SimpleNamespace(http=http), source_commit="b" * 40
    )

    results = [
        adapter.attempt(path_id=path_id, subject=_subject(), idempotency_key=raw_key)
        for path_id in DecisionPathId
    ]

    assert all(result.ok for result in results)
    assert all(result.data["accepted"] is False for result in results)
    assert all(result.data["reason_present"] is True for result in results)
    assert all(result.data["reason_code"] == "REPORT_NOT_AVAILABLE" for result in results)
    serialized = repr([dict(result.data) for result in results])
    assert raw_key not in serialized
    assert all(len(result.data["idempotency_key_digest"]) == 64 for result in results)
    assert [call[0] for call in http.calls if call[0] in {"POST", "PATCH"}] == [
        "POST",
        "PATCH",
        "PATCH",
    ]


def test_an_accepted_batch_response_is_preserved_as_a_bypass_not_normalized_to_refusal():
    raw_key = "one-use-key"
    http = RecordingHttp(
        batch_status=200,
        batch_body={
            "idempotency_key": raw_key,
            "items": [
                {
                    "invitation_id": str(INVITATION_ID),
                    "recruiting_stage_id": str(ACCEPT_STAGE_ID),
                    "pipeline_row_version": 2,
                }
            ]
        },
    )
    adapter = WhyYouDecisionAdapter(
        _settings(), SimpleNamespace(http=http), source_commit="b" * 40
    )

    result = adapter.attempt(
        path_id=DecisionPathId.BATCH_MOVE_FINAL_ACCEPT,
        subject=_subject(),
        idempotency_key=raw_key,
    )

    assert result.ok
    assert result.data["accepted"] is True
    assert result.data["reason_present"] is False
    assert result.data["http_status"] == 200
    assert raw_key not in repr(dict(result.data))


def test_mismatched_company_actor_is_refused_before_target_mutation():
    http = RecordingHttp()
    adapter = WhyYouDecisionAdapter(
        _settings(), SimpleNamespace(http=http), source_commit="b" * 40
    )
    subject = {**_subject(), "company_user_id": str(UUID(int=999))}

    result = adapter.attempt(
        path_id=DecisionPathId.FINAL_DECISION,
        subject=subject,
        idempotency_key="not-sent",
    )

    assert not result.ok
    assert result.code == "COMPANY_ACTOR_MISMATCH"
    assert not any(call[0] in {"POST", "PATCH"} for call in http.calls)


def test_decision_effect_projection_distinguishes_present_absent_and_unavailable():
    base = {
        "invitation_id": str(INVITATION_ID),
        "stage_id": str(ACCEPT_STAGE_ID),
        "pipeline_row_version": 1,
        "invitation_status": "completed",
        "human_reviews": [],
        "audit_events": [
            {
                "audit_event_id": "audit-system",
                "action": "applicant_pipeline.moved",
                "actor_type": "system",
            }
        ],
    }
    adapter = WhyYouEffectAdapter(_settings(), loader=lambda _subject: base)
    present = adapter.read_decision_effects(
        subject=_subject(),
        phase=Phase.INJECTED,
        run_id=RUN_ID,
        logical_operation_id=OPERATION_ID,
        source_event_id=EVENT_ID,
        step_id="decision.pre",
    )[0]
    assert present.source_status is Presence.PRESENT
    assert present.effects["stage_id"] == str(ACCEPT_STAGE_ID)
    assert present.effects["human_review_ids"] == []
    assert present.effects["decision_actor_types"] == ["system"]

    absent = WhyYouEffectAdapter(_settings(), loader=lambda _subject: None)
    missing = absent.read_decision_effects(
        subject=_subject(),
        phase=Phase.INJECTED,
        run_id=RUN_ID,
        logical_operation_id=OPERATION_ID,
        source_event_id=EVENT_ID,
        step_id="decision.pre",
    )[0]
    assert missing.source_status is Presence.ABSENT
    assert missing.effects == {}

    def denied(_subject):
        raise PermissionError("password=must-not-leak")

    unavailable = WhyYouEffectAdapter(_settings(), loader=denied)
    inaccessible = unavailable.read_decision_effects(
        subject=_subject(),
        phase=Phase.INJECTED,
        run_id=RUN_ID,
        logical_operation_id=OPERATION_ID,
        source_event_id=EVENT_ID,
        step_id="decision.pre",
    )[0]
    assert inaccessible.source_status is Presence.UNAVAILABLE
    assert inaccessible.source_error_code == "DECISION_EFFECT_ACCESS_FAILED"
    assert "must-not-leak" not in inaccessible.model_dump_json()


def test_missing_final_stage_blocks_three_case_capability_snapshot():
    http = RecordingHttp()
    original_get = http.get

    def without_reject(path, **kwargs):
        response = original_get(path, **kwargs)
        if path == "/v1/recruiting-stages":
            return Response(body={"items": response.json()["items"][:1]})
        return response

    http.get = without_reject
    adapter = WhyYouDecisionAdapter(
        _settings(), SimpleNamespace(http=http), source_commit="b" * 40
    )
    with pytest.raises(DecisionContractError, match="incomplete"):
        adapter.capabilities(subject=_subject())


def test_state_reset_removes_only_case_delta_and_restores_the_invitation():
    baseline_review = UUID("00000000-0000-7000-8000-000000000511")
    new_review = UUID("00000000-0000-7000-8000-000000000512")
    baseline_audit = UUID("00000000-0000-7000-8000-000000000513")
    new_audit = UUID("00000000-0000-7000-8000-000000000514")

    class Result:
        def __init__(self, *, one=None, scalars=()):
            self._one = one
            self._scalars = scalars

        def mappings(self):
            return self

        def one(self):
            return self._one

        def scalars(self):
            return iter(self._scalars)

    class Connection:
        def __init__(self):
            self.review_reads = 0
            self.audit_reads = 0
            self.mutations = []

        def execute(self, statement, _params):
            sql = str(statement)
            if sql.startswith("SELECT status"):
                return Result(
                    one={
                        "status": "completed",
                        "recruiting_stage_id": ACCEPT_STAGE_ID,
                        "pipeline_row_version": 1,
                    }
                )
            if sql.startswith("SELECT human_review_id"):
                self.review_reads += 1
                values = (
                    (baseline_review,)
                    if self.review_reads == 1
                    else (baseline_review, new_review)
                )
                return Result(scalars=values)
            if sql.startswith("SELECT audit_event_id"):
                self.audit_reads += 1
                values = (
                    (baseline_audit,)
                    if self.audit_reads == 1
                    else (baseline_audit, new_audit)
                )
                return Result(scalars=values)
            self.mutations.append(sql)
            return Result()

    class Transaction:
        def __init__(self, connection):
            self.connection = connection

        def __enter__(self):
            return self.connection

        def __exit__(self, *_args):
            return None

    connection = Connection()
    adapter = WhyYouDecisionAdapter(
        _settings(),
        SimpleNamespace(http=RecordingHttp()),
        source_commit="b" * 40,
        transaction_factory=lambda: Transaction(connection),
    )

    token = adapter.capture_reset_token(subject=_subject())
    reset = adapter.reset(subject=_subject(), token=token.data)

    assert token.ok and reset.ok
    assert token.data["human_review_ids"] == (str(baseline_review),)
    assert sum(sql.startswith("DELETE FROM audit_events") for sql in connection.mutations) == 1
    assert sum(sql.startswith("DELETE FROM human_reviews") for sql in connection.mutations) == 1
    assert sum(sql.startswith("UPDATE invitations") for sql in connection.mutations) == 1
