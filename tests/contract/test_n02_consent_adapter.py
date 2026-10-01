from __future__ import annotations

from uuid import uuid4

import httpx

from engine.adapters.whyyou.consent import WhyYouConsentAdapter
from engine.adapters.whyyou.n02_seed import N02CredentialStore
from engine.models import ConsentPurpose, N02LaneId, Phase, Presence


def _subject():
    return {
        "run_id": str(uuid4()),
        "lane_id": N02LaneId.NORMAL_ORDER.value,
        "subject_ref": "synthetic-normal-order",
        "invitation_id": str(uuid4()),
        "applicant_id": str(uuid4()),
    }


def _client(settings, handler):
    return httpx.Client(
        base_url=settings.whyyou_base_url,
        transport=httpx.MockTransport(handler),
    )


def test_policy_and_commit_use_exact_contract_and_never_persist_raw_content(settings) -> None:
    subject = _subject()
    credentials = N02CredentialStore()
    credentials.put(subject["subject_ref"], "raw-secret-cookie")
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        assert "raw-secret-cookie" in request.headers["cookie"]
        if request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "policy_version": "2026-10-v1",
                    "content_digest": "a" * 64,
                    "required_purposes": [item.value for item in ConsentPurpose],
                    "retention_days": 180,
                    "policy_text": "must never be stored",
                    "ai_role": "raw display copy",
                },
            )
        assert request.headers["idempotency-key"] == "consent-command-0001"
        assert request.headers["x-trace-id"] == "controlproof:trace"
        return httpx.Response(
            201,
            json={
                "consent_record_id": str(uuid4()),
                "policy_version": "2026-10-v1",
                "accepted_purposes": [item.value for item in ConsentPurpose],
                "retention_days": 180,
                "accepted_at": "2026-10-01T00:00:00Z",
                "presigned_url": "https://secret.invalid/value",
            },
        )

    adapter = WhyYouConsentAdapter(
        settings,
        http_client=_client(settings, handler),
        credentials=credentials,
    )
    policy = adapter.read_policy(subject=subject)
    committed = adapter.commit(
        subject=subject,
        policy=policy,
        request_id="consent-command-0001",
        trace_id="controlproof:trace",
    )
    assert policy.required_purposes == tuple(ConsentPurpose)
    assert "policy_text" not in policy.model_dump_json()
    assert committed.ok and committed.code == "CONSENT_COMMIT_RESPONSE_RECEIVED"
    assert "raw-secret-cookie" not in str(committed.data)
    assert "secret.invalid" not in str(committed.data)
    assert len(seen) == 2


def test_commit_timeout_is_unknown_until_durable_state_is_read(settings) -> None:
    subject = _subject()
    credentials = N02CredentialStore()
    credentials.put(subject["subject_ref"], "cookie")

    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("late response")

    adapter = WhyYouConsentAdapter(
        settings,
        http_client=_client(settings, handler),
        credentials=credentials,
    )
    from tests.fixtures.fake_adapters import FakeN02Adapters

    policy = FakeN02Adapters().read_policy(subject=subject)
    result = adapter.commit(
        subject=subject,
        policy=policy,
        request_id="consent-command-0002",
        trace_id="controlproof:trace",
    )
    assert not result.ok
    assert result.code == "CONSENT_COMMIT_RESPONSE_UNKNOWN"
    assert result.data["durable_state"] == "UNKNOWN"


def test_state_projection_distinguishes_successful_empty_from_unavailable(settings) -> None:
    subject = _subject()
    empty = WhyYouConsentAdapter(
        settings,
        state_reader=lambda _subject: {
            "source_status": "PRESENT",
            "invitation_status": "identity_verified",
            "invitation_row_version": 1,
        },
    ).read_state(subject=subject, phase=Phase.INJECTED.value, step_id="empty")
    unavailable = WhyYouConsentAdapter(
        settings,
        state_reader=lambda _subject: (_ for _ in ()).throw(TimeoutError()),
    ).read_state(subject=subject, phase=Phase.INJECTED.value, step_id="unavailable")
    assert empty.source_status is Presence.ABSENT
    assert empty.consent_record_ids == ()
    assert unavailable.source_status is Presence.UNAVAILABLE
    assert unavailable.source_error_code == "TIMEOUTERROR"


def test_state_projection_keeps_only_transaction_identity(settings) -> None:
    subject = _subject()
    consent_id, transition_id, event_id = uuid4(), uuid4(), uuid4()
    adapter = WhyYouConsentAdapter(
        settings,
        state_reader=lambda _subject: {
            "invitation_status": "consented",
            "invitation_row_version": 2,
            "consent_record_ids": [consent_id],
            "active_consent_count": 1,
            "consent_policy_versions": ["2026-10-v1"],
            "consent_content_digests": ["a" * 64],
            "accepted_purpose_sets": [[item.value for item in ConsentPurpose]],
            "consented_state_change_ids": [transition_id],
            "consent_completed_event_ids": [event_id],
            "trace_ids": ["raw-trace-id"],
            "candidate_email": "must-not-appear@example.com",
        },
    )
    state = adapter.read_state(
        subject=subject, phase=Phase.INJECTED.value, step_id="committed"
    )
    assert state.source_status is Presence.PRESENT
    assert state.consent_record_ids == (consent_id,)
    assert state.consented_state_change_ids == (transition_id,)
    assert state.consent_completed_event_ids == (event_id,)
    assert "must-not-appear" not in state.model_dump_json()
    assert len(state.trace_ids[0]) == 64
