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
