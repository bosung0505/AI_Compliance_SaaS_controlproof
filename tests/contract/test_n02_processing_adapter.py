from __future__ import annotations

import json
from dataclasses import replace
from uuid import uuid4

import httpx

from engine.adapters.whyyou.n02_seed import N02CredentialStore
from engine.adapters.whyyou.protected_processing import WhyYouProtectedProcessingAdapter
from engine.models import (
    N02LaneId,
    Phase,
    Presence,
    ProcessingEntryKind,
    ProcessingResponseClass,
    ProtectedPathId,
)


def _subject(lane=N02LaneId.DOCUMENT_BYPASS):
    return {
        "run_id": str(uuid4()),
        "lane_id": lane.value,
        "subject_ref": f"synthetic-{lane.value.casefold()}",
        "invitation_id": str(uuid4()),
        "applicant_id": str(uuid4()),
        "equipment_check_id": str(uuid4()),
        "strategy_id": str(uuid4()),
        "interview_session_id": str(uuid4()),
        "allowed_fixture_effect_ids": [],
    }


def test_path_capabilities_name_the_three_actual_boundaries(settings) -> None:
    adapter = WhyYouProtectedProcessingAdapter(settings)
    paths = {item.path_id: item for item in adapter.paths()}
    assert paths[ProtectedPathId.DOCUMENT_ANALYSIS].entry_boundary == (
        "createSubmissionUploadIntent"
    )
    assert paths[ProtectedPathId.RECORDING].entry_boundary == "createInterviewSession"
    assessment = paths[ProtectedPathId.AI_ASSESSMENT]
    assert assessment.entry_boundary == "report.generation_requested"
    assert assessment.entry_kind is ProcessingEntryKind.DOMAIN_EVENT
    assert assessment.independent_direct_route is False
    assert all(
        not value.startswith(("/", "C:/"))
        for item in paths.values()
        for value in item.source_locator.values()
    )


def test_document_and_recording_attempts_store_only_sanitized_response(settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "iep_applicant_session=raw-local-cookie" in request.headers["cookie"]
        return httpx.Response(
            403,
            json={"detail": "consent required", "presigned_url": "https://secret.invalid"},
        )

    credentials = N02CredentialStore()
    subjects = [_subject(), _subject(N02LaneId.RECORDING_BOUNDARY_PROBE)]
    for subject in subjects:
        credentials.put(subject["subject_ref"], "raw-local-cookie")
    client = httpx.Client(
        base_url=settings.whyyou_base_url, transport=httpx.MockTransport(handler)
    )
    adapter = WhyYouProtectedProcessingAdapter(
        settings, http_client=client, credentials=credentials
    )
    document = adapter.attempt(path_id="DOCUMENT_ANALYSIS", subject=subjects[0])
    recording = adapter.attempt(path_id="RECORDING", subject=subjects[1])
    assert document.response_class is ProcessingResponseClass.DENIED
    assert recording.response_class is ProcessingResponseClass.DENIED
    assert document.status_code == recording.status_code == 403
    assert "secret.invalid" not in document.model_dump_json()
    assert "raw-local-cookie" not in recording.model_dump_json()


def test_assessment_attempt_uses_real_domain_event_boundary(settings) -> None:
    inserted = []

    class _Tx:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, _statement, params):
            inserted.append(dict(params))

    subject = _subject(N02LaneId.ASSESSMENT_BOUNDARY_PROBE)
    adapter = WhyYouProtectedProcessingAdapter(
        settings, transaction_factory=lambda: _Tx()
    )
    result = adapter.attempt(path_id="AI_ASSESSMENT", subject=subject)
    assert result.response_class is ProcessingResponseClass.SUBMITTED
    assert inserted[0]["event_type"] == "report.generation_requested"
    assert result.probe_input_effect_id == f"event:{inserted[0]['outbox_event_id']}"
    assert inserted[0]["trace_id"].startswith(
        f"controlproof:{subject['run_id']}:{subject['lane_id']}:"
    )


def test_assessment_probe_input_is_not_counted_as_target_effect(settings) -> None:
    inserted = []

    class _Tx:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, _statement, params):
            inserted.append(dict(params))

    subject = _subject(N02LaneId.ASSESSMENT_BOUNDARY_PROBE)
    adapter = WhyYouProtectedProcessingAdapter(
        settings,
        transaction_factory=lambda: _Tx(),
        effect_reader=lambda _subject, _path: {
            "source_status": "PRESENT",
            "effect_ids": [f"event:{inserted[0]['outbox_event_id']}"],
        },
    )
    attempt = adapter.attempt(path_id="AI_ASSESSMENT", subject=subject)
    effects = adapter.read_effects(
        path_id="AI_ASSESSMENT",
        subject=subject,
        phase=Phase.INJECTED.value,
        step_id="capture-assessment-effects",
    )
    assert effects.probe_input_effect_ids == (attempt.probe_input_effect_id,)
    assert effects.new_effect_ids == ()
    assert effects.current_effect_ids == (attempt.probe_input_effect_id,)


def test_assessment_start_requires_matching_target_receipt(settings, tmp_path) -> None:
    inserted = []

    class _Tx:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, _statement, params):
            inserted.append(dict(params))

    subject = _subject(N02LaneId.ASSESSMENT_BOUNDARY_PROBE)
    adapter = WhyYouProtectedProcessingAdapter(
        replace(settings, observer_enabled=True, observer_root=tmp_path),
        transaction_factory=lambda: _Tx(),
        effect_reader=lambda _subject, _path: {
            "source_status": "PRESENT",
            "effect_ids": [f"event:{inserted[0]['outbox_event_id']}"],
        },
    )
    attempt = adapter.attempt(path_id="AI_ASSESSMENT", subject=subject)
    receipt_path = tmp_path / "receipts" / f"{subject['run_id']}.jsonl"
    receipt_path.parent.mkdir()
    receipt_path.write_text(
        json.dumps(
            {
                "receipt_id": "target-start-1",
                "run_id": subject["run_id"],
                "lane_id": subject["lane_id"],
                "subject_ref": subject["subject_ref"],
                "path_id": "AI_ASSESSMENT",
                "boundary": "REPORT_ASSESSMENT_STARTED",
                "request_or_event_id": str(inserted[0]["outbox_event_id"]),
            }
        )
        + "\n"
        + json.dumps(
            {
                "receipt_id": "wrong-event",
                "run_id": subject["run_id"],
                "lane_id": subject["lane_id"],
                "subject_ref": subject["subject_ref"],
                "path_id": "AI_ASSESSMENT",
                "boundary": "REPORT_ASSESSMENT_STARTED",
                "request_or_event_id": str(uuid4()),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    effects = adapter.read_effects(
        path_id="AI_ASSESSMENT",
        subject=subject,
        phase=Phase.INJECTED.value,
        step_id="capture-assessment-effects",
    )
    assert attempt.probe_input_effect_id == effects.probe_input_effect_ids[0]
    assert effects.start_receipt_ids == ("target-start-1",)
    assert effects.new_effect_ids == ()


def test_effect_read_distinguishes_absent_unavailable_and_fixture_delta(settings) -> None:
    values = iter(
        [
            {"source_status": "PRESENT", "effect_ids": ["fixture-1"]},
            {
                "source_status": "PRESENT",
                "effect_ids": ["fixture-1", "session-new"],
            },
            {"source_status": "UNAVAILABLE", "error_code": "DB_TIMEOUT"},
        ]
    )
    subject = _subject(N02LaneId.RECORDING_BOUNDARY_PROBE)
    subject["allowed_fixture_effect_ids"] = ["fixture-1"]
    adapter = WhyYouProtectedProcessingAdapter(
        settings, effect_reader=lambda _subject, _path: next(values)
    )
    baseline = adapter.read_effects(
        path_id="RECORDING",
        subject=subject,
        phase=Phase.BASELINE.value,
        step_id="capture-recording-baseline",
    )
    current = adapter.read_effects(
        path_id="RECORDING",
        subject=subject,
        phase=Phase.INJECTED.value,
        step_id="capture-recording-effects",
    )
    unavailable = adapter.read_effects(
        path_id="RECORDING",
        subject=subject,
        phase=Phase.INJECTED.value,
        step_id="capture-recording-effects-retry",
    )
    assert baseline.new_effect_ids == ()
    assert current.new_effect_ids == ("session-new",)
    assert unavailable.source_status is Presence.UNAVAILABLE
    assert unavailable.source_error_code == "DB_TIMEOUT"


class _UniqueOutboxTx:
    """Fake transaction that enforces the real outbox primary key."""

    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, _statement, params):
        if any(row["outbox_event_id"] == params["outbox_event_id"] for row in self.rows):
            raise RuntimeError("duplicate key value violates unique constraint")
        self.rows.append(dict(params))


def test_repeated_assessment_attempts_in_one_lane_use_distinct_identities(settings) -> None:
    """ID-003-11: the fault lane attempts each path in the failure phase and again after
    recovery. Child Run on 2026-10-04 crashed with N02_ASSESSMENT_EVENT_WRITE_FAILED because
    both attempts derived the same outbox_event_id from (run, lane, path) only."""
    rows = []
    subject = _subject(N02LaneId.CONSENT_FAULT_RECOVERY)
    adapter = WhyYouProtectedProcessingAdapter(
        settings, transaction_factory=lambda: _UniqueOutboxTx(rows)
    )
    first = adapter.attempt(path_id="AI_ASSESSMENT", subject=subject)
    second = adapter.attempt(path_id="AI_ASSESSMENT", subject=subject)

    assert not hasattr(second, "code"), getattr(second, "code", None)
    assert first.request_id != second.request_id
    assert first.probe_input_effect_id != second.probe_input_effect_id
    assert len({row["outbox_event_id"] for row in rows}) == 2


def test_every_runner_probe_input_in_a_lane_is_excluded_from_target_effects(settings) -> None:
    rows = []
    subject = _subject(N02LaneId.CONSENT_FAULT_RECOVERY)
    adapter = WhyYouProtectedProcessingAdapter(
        settings,
        transaction_factory=lambda: _UniqueOutboxTx(rows),
        effect_reader=lambda _subject, _path: {
            "source_status": "PRESENT",
            "effect_ids": [f"event:{row['outbox_event_id']}" for row in rows],
        },
    )
    first = adapter.attempt(path_id="AI_ASSESSMENT", subject=subject)
    second = adapter.attempt(path_id="AI_ASSESSMENT", subject=subject)
    effects = adapter.read_effects(
        path_id="AI_ASSESSMENT",
        subject=subject,
        phase=Phase.RECOVERED.value,
        step_id="recovered-ai_assessment-effects",
    )

    assert set(effects.probe_input_effect_ids) == {
        first.probe_input_effect_id,
        second.probe_input_effect_id,
    }
    assert effects.new_effect_ids == ()


def test_repeated_http_attempts_in_one_lane_send_distinct_idempotency_keys(settings) -> None:
    keys = []

    def handler(request: httpx.Request) -> httpx.Response:
        keys.append(request.headers["Idempotency-Key"])
        return httpx.Response(403, json={"detail": "consent required"})

    credentials = N02CredentialStore()
    subject = _subject(N02LaneId.CONSENT_FAULT_RECOVERY)
    credentials.put(subject["subject_ref"], "raw-local-cookie")
    client = httpx.Client(base_url=settings.whyyou_base_url, transport=httpx.MockTransport(handler))
    adapter = WhyYouProtectedProcessingAdapter(settings, http_client=client, credentials=credentials)
    for _ in range(2):
        adapter.attempt(path_id="DOCUMENT_ANALYSIS", subject=subject)

    assert len(keys) == 2 and keys[0] != keys[1]


def test_assessment_refusal_and_consumer_bookkeeping_stay_apart_from_effects(
    settings, tmp_path
) -> None:
    """ID-003-17: a target refusal of the runner's input is its own receipt, and the
    consumer's processed row for that input is bookkeeping, not a protected effect."""
    inserted = []

    class _Tx:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, _statement, params):
            inserted.append(dict(params))

    subject = _subject(N02LaneId.ASSESSMENT_BOUNDARY_PROBE)
    adapter = WhyYouProtectedProcessingAdapter(
        replace(settings, observer_enabled=True, observer_root=tmp_path),
        transaction_factory=lambda: _Tx(),
        effect_reader=lambda _subject, _path: {
            "source_status": "PRESENT",
            "effect_ids": [
                f"event:{inserted[0]['outbox_event_id']}",
                f"processed:{inserted[0]['outbox_event_id']}",
            ],
        },
    )
    adapter.attempt(path_id="AI_ASSESSMENT", subject=subject)
    event_id = str(inserted[0]["outbox_event_id"])
    receipt_path = tmp_path / "receipts" / f"{subject['run_id']}.jsonl"
    receipt_path.parent.mkdir()
    receipt_path.write_text(
        json.dumps(
            {
                "receipt_id": "target-refusal-1",
                "run_id": subject["run_id"],
                "lane_id": subject["lane_id"],
                "subject_ref": subject["subject_ref"],
                "path_id": "AI_ASSESSMENT",
                "boundary": "REPORT_ASSESSMENT_REFUSED",
                "request_or_event_id": event_id,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    effects = adapter.read_effects(
        path_id="AI_ASSESSMENT",
        subject=subject,
        phase=Phase.INJECTED.value,
        step_id="capture-assessment-effects",
    )
    assert effects.refusal_receipt_ids == ("target-refusal-1",)
    assert effects.start_receipt_ids == ()
    assert effects.probe_bookkeeping_effect_ids == (f"processed:{event_id}",)
    assert effects.new_effect_ids == ()


def _driven_adapter(settings, log: list[str]):
    """A fake WhyYou that honours the applicant product flow the runner drives (ID-003-18)."""
    session_id = "00000000-0000-7000-8000-000000000071"
    upload_id = "00000000-0000-7000-8000-000000000072"

    def api(request: httpx.Request) -> httpx.Response:
        log.append(f"{request.method} {request.url.path}")
        if request.url.path == "/v1/applicant/equipment-checks":
            return httpx.Response(201, json={"equipment_check_id": "00000000-0000-7000-8000-000000000073"})
        if request.url.path == "/v1/applicant/interview-sessions":
            body = json.loads(request.content)
            log.append(f"session-equipment:{body['equipment_check_id']}")
            return httpx.Response(201, json={"interview_session_id": session_id})
        if request.url.path.endswith("/media-upload-intents"):
            return httpx.Response(201, json={"method": "PUT", "url": "http://store.test/chunk", "required_headers": {}})
        if request.url.path.endswith("/media-uploads"):
            return httpx.Response(201, json={"recording_chunk_id": "00000000-0000-7000-8000-000000000074"})
        if request.url.path == "/v1/applicant/submissions/upload-intents":
            body = json.loads(request.content)
            assert body["byte_size"] > 1 and body["sha256"] != "0" * 64
            return httpx.Response(201, json={"upload_id": upload_id, "method": "PUT", "url": "http://store.test/resume", "required_headers": {"Content-Type": "application/pdf"}})
        if request.url.path == "/v1/applicant/submissions":
            assert json.loads(request.content)["upload_id"] == upload_id
            return httpx.Response(202, json={"submission_id": "00000000-0000-7000-8000-000000000075"})
        return httpx.Response(404)

    def store(request: httpx.Request) -> httpx.Response:
        log.append(f"{request.method} {request.url}")
        return httpx.Response(200)

    credentials = N02CredentialStore()
    return WhyYouProtectedProcessingAdapter(
        settings,
        http_client=httpx.Client(base_url=settings.whyyou_base_url, transport=httpx.MockTransport(api)),
        upload_client=httpx.Client(transport=httpx.MockTransport(store)),
        credentials=credentials,
    ), credentials, session_id


def test_driven_recording_attempt_runs_the_applicant_flow_to_the_confirmed_chunk(settings) -> None:
    """ID-003-18: equipment check, session, upload intent, PUT and confirmation."""
    log: list[str] = []
    adapter, credentials, session_id = _driven_adapter(settings, log)
    subject = _subject(N02LaneId.NORMAL_ORDER)
    credentials.put(subject["subject_ref"], "cookie")
    attempt = adapter.attempt(path_id="RECORDING", subject=subject, drive=True)
    assert attempt.response_class is ProcessingResponseClass.ACCEPTED
    assert attempt.created_session_id == session_id
    assert attempt.drive_steps == ("equipment-check:201", "request:201", "media-intent:201", "upload:200", "confirm:201")
    assert "session-equipment:00000000-0000-7000-8000-000000000073" in log
    assert "PUT http://store.test/chunk" in log


def test_driven_document_attempt_uploads_and_registers_the_submission(settings) -> None:
    log: list[str] = []
    adapter, credentials, _ = _driven_adapter(settings, log)
    subject = _subject(N02LaneId.NORMAL_ORDER)
    credentials.put(subject["subject_ref"], "cookie")
    attempt = adapter.attempt(path_id="DOCUMENT_ANALYSIS", subject=subject, drive=True)
    assert attempt.response_class is ProcessingResponseClass.ACCEPTED
    assert attempt.drive_steps == ("request:201", "upload:200", "register:202")
    assert attempt.created_session_id is None


def test_probe_attempt_without_drive_stops_at_the_first_request(settings) -> None:
    log: list[str] = []
    adapter, credentials, _ = _driven_adapter(settings, log)
    subject = _subject(N02LaneId.RECORDING_BOUNDARY_PROBE)
    credentials.put(subject["subject_ref"], "cookie")
    attempt = adapter.attempt(path_id="RECORDING", subject=subject)
    assert attempt.drive_steps == () and attempt.created_session_id is None
    assert log[0] == "POST /v1/applicant/interview-sessions"
    assert "POST /v1/applicant/equipment-checks" not in log and len(log) == 2


def test_results_are_only_what_the_attempt_newly_produced(settings, tmp_path) -> None:
    """ID-003-18: a fixture strategy present before the attempt is not a document result."""
    fixture = "strategy:00000000-0000-7000-8000-000000000081"
    subject = {**_subject(N02LaneId.NORMAL_ORDER), "allowed_fixture_effect_ids": [fixture]}
    adapter = WhyYouProtectedProcessingAdapter(
        replace(settings, observer_enabled=True, observer_root=tmp_path),
        effect_reader=lambda _subject, _path: {
            "source_status": "PRESENT",
            "effect_ids": [fixture, "upload:00000000-0000-7000-8000-000000000082"],
        },
    )
    effects = adapter.read_effects(
        path_id="DOCUMENT_ANALYSIS", subject=subject, phase=Phase.INJECTED.value, step_id="x"
    )
    assert effects.new_effect_ids == ("upload:00000000-0000-7000-8000-000000000082",)
    assert effects.result_ids == ()
