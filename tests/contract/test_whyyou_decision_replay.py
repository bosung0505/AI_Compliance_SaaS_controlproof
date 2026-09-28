from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

from engine.adapters.whyyou.decisions import (
    WhyYouDecisionAdapter,
    compare_decision_replay,
)
from engine.models import DecisionPathId

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


class ReplayHttp:
    def __init__(self, *, lose_first_response=False, distinct_response_ids=False):
        self.lose_first_response = lose_first_response
        self.distinct_response_ids = distinct_response_ids
        self.posts = []

    def get(self, path, **kwargs):
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
        self.posts.append((path, kwargs))
        if self.lose_first_response and len(self.posts) == 1:
            raise ConnectionError("response lost after target processing")
        suffix = len(self.posts) if self.distinct_response_ids else 1
        return Response(201, {"human_review_id": f"review-{suffix}", "status": "reviewed"})

    def patch(self, path, **kwargs):
        raise AssertionError((path, kwargs))


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


def _adapter(http):
    return WhyYouDecisionAdapter(
        _settings(),
        SimpleNamespace(http=http),
        source_commit="b" * 40,
    )


def test_same_key_body_and_stage_share_one_logical_decision_identity():
    raw_key = "controlproof-e03-private-replay-key"
    http = ReplayHttp()
    adapter = _adapter(http)

    first = adapter.attempt(
        path_id=DecisionPathId.FINAL_DECISION,
        subject=_subject(),
        idempotency_key=raw_key,
    )
    replay = adapter.attempt(
        path_id=DecisionPathId.FINAL_DECISION,
        subject=_subject(),
        idempotency_key=raw_key,
    )
    comparison = compare_decision_replay(first, replay)

    assert first.ok and replay.ok and comparison.ok
    assert first.data["logical_decision_id"] == replay.data["logical_decision_id"]
    assert first.data["request_body_digest"] == replay.data["request_body_digest"]
    assert first.data["idempotency_key_digest"] == replay.data["idempotency_key_digest"]
    assert first.data["target_stage_id"] == replay.data["target_stage_id"]
    assert comparison.data["request_equivalent"] is True
    assert comparison.data["response_equivalent"] is True
    assert [call[1]["headers"]["Idempotency-Key"] for call in http.posts] == [
        raw_key,
        raw_key,
    ]
    assert raw_key not in repr((first.data, replay.data, comparison.data))


def test_lost_first_response_still_preserves_identity_for_safe_replay():
    raw_key = "controlproof-e03-lost-response-key"
    http = ReplayHttp(lose_first_response=True)
    adapter = _adapter(http)

    first = adapter.attempt(
        path_id=DecisionPathId.FINAL_DECISION,
        subject=_subject(),
        idempotency_key=raw_key,
    )
    replay = adapter.attempt(
        path_id=DecisionPathId.FINAL_DECISION,
        subject=_subject(),
        idempotency_key=raw_key,
    )
    comparison = compare_decision_replay(first, replay)

    assert not first.ok
    assert first.code == "DECISION_RESPONSE_UNAVAILABLE"
    assert replay.ok
    assert comparison.ok
    assert comparison.data["request_equivalent"] is True
    assert comparison.data["response_equivalent"] is None
    assert first.data["logical_decision_id"] == replay.data["logical_decision_id"]
    assert raw_key not in repr((first.data, replay.data, comparison.data))


def test_matching_requests_never_claim_target_deduplication_without_effect_evidence():
    http = ReplayHttp(distinct_response_ids=True)
    adapter = _adapter(http)
    key = "target-may-ignore-this-key"

    first = adapter.attempt(
        path_id=DecisionPathId.FINAL_DECISION,
        subject=_subject(),
        idempotency_key=key,
    )
    replay = adapter.attempt(
        path_id=DecisionPathId.FINAL_DECISION,
        subject=_subject(),
        idempotency_key=key,
    )
    comparison = compare_decision_replay(first, replay)

    assert comparison.ok
    assert comparison.data["request_equivalent"] is True
    assert comparison.data["target_idempotency_confirmed"] is False
    assert comparison.data["response_equivalent"] is True


def test_changed_key_is_a_different_logical_decision_even_with_same_body():
    adapter = _adapter(ReplayHttp())
    first = adapter.attempt(
        path_id=DecisionPathId.FINAL_DECISION,
        subject=_subject(),
        idempotency_key="first-logical-key",
    )
    changed = adapter.attempt(
        path_id=DecisionPathId.FINAL_DECISION,
        subject=_subject(),
        idempotency_key="second-logical-key",
    )

    comparison = compare_decision_replay(first, changed)

    assert not comparison.ok
    assert comparison.code == "DECISION_REPLAY_NON_EQUIVALENT"
    assert first.data["logical_decision_id"] != changed.data["logical_decision_id"]
