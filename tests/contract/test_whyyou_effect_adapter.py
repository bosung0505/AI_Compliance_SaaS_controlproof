from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

from engine.adapters.whyyou.effects import WhyYouEffectAdapter
from engine.models import Phase, Presence
from tests.fixtures.spec002 import (
    EVENT_ID,
    OPERATION_ID,
    RUN_ID,
    SESSION_ID,
)

REPORT_ID = UUID("00000000-0000-7000-8000-000000000601")
DOCUMENT_A = UUID("00000000-0000-7000-8000-000000000602")
DOCUMENT_B = UUID("00000000-0000-7000-8000-000000000603")


def _settings():
    return SimpleNamespace(whyyou_database_url="postgresql+psycopg://local/test")


def _subject():
    return {
        "subject_ref": "candidate-01",
        "company_id": "00000000-0000-7000-8000-000000000010",
        "invitation_id": "00000000-0000-7000-8000-000000000011",
        "interview_session_id": str(SESSION_ID),
    }


def _source(*, reverse=False):
    documents = [
        {
            "assistant_document_id": DOCUMENT_B,
            "report_id": REPORT_ID,
            "report_item_id": None,
            "document_type": "report_summary",
            "source_version": "report-v1",
            "content_hash": "b" * 64,
        },
        {
            "assistant_document_id": DOCUMENT_A,
            "report_id": REPORT_ID,
            "report_item_id": "00000000-0000-7000-8000-000000000604",
            "document_type": "criterion",
            "source_version": "report-v1",
            "content_hash": "a" * 64,
        },
    ]
    if reverse:
        documents.reverse()
    return {
        "reports": [
            {
                "report_id": REPORT_ID,
                "interview_session_id": SESSION_ID,
                "invitation_id": UUID(_subject()["invitation_id"]),
                "version": 1,
                "status": "ready",
            }
        ],
        "projections": documents,
        "processed_messages": [
            {
                "consumer_name": "reporting-worker",
                "event_id": EVENT_ID,
                "event_version": 1,
            }
        ],
        "outbox_events": [
            {
                "outbox_event_id": EVENT_ID,
                "event_type": "report.generation_requested",
                "event_version": 1,
                "publish_status": "published",
            },
            {
                "outbox_event_id": UUID(int=999),
                "event_type": "report.completed",
                "event_version": 1,
                "publish_status": "published",
            },
        ],
    }


def _read(adapter):
    return adapter.read_reporting_effects(
        subject=_subject(),
        phase=Phase.RECOVERED,
        run_id=RUN_ID,
        logical_operation_id=OPERATION_ID,
        source_event_id=EVENT_ID,
        step_id="recovered-reporting-effects",
    )[0]


def test_reporting_projection_is_scoped_canonical_and_order_independent():
    first = _read(WhyYouEffectAdapter(_settings(), reporting_loader=lambda _scope: _source()))
    second = _read(
        WhyYouEffectAdapter(
            _settings(), reporting_loader=lambda _scope: _source(reverse=True)
        )
    )

    assert first.source_status is Presence.PRESENT
    assert first.effects["logical_report_ids"] == [str(REPORT_ID)]
    assert first.effects["projection_document_ids"] == [str(DOCUMENT_A), str(DOCUMENT_B)]
    assert first.effects["projection_report_ids"] == [str(REPORT_ID), str(REPORT_ID)]
    assert first.effects["processed_keys"] == [
        {
            "consumer_name": "reporting-worker",
            "event_id": str(EVENT_ID),
            "event_version": 1,
        }
    ]
    assert first.effects["source_outbox_event_ids"] == [str(EVENT_ID)]
    assert "report_completed_event_ids" not in first.effects
    assert first.state_digest == second.state_digest


def test_successful_empty_query_is_absent_but_access_failure_is_unavailable():
    empty = _read(WhyYouEffectAdapter(_settings(), reporting_loader=lambda _scope: None))
    assert empty.source_status is Presence.ABSENT
    assert empty.effects == {}

    def denied(_scope):
        raise PermissionError("password=must-not-leak")

    unavailable = _read(WhyYouEffectAdapter(_settings(), reporting_loader=denied))
    assert unavailable.source_status is Presence.UNAVAILABLE
    assert unavailable.source_error_code == "REPORTING_EFFECT_ACCESS_FAILED"
    assert "must-not-leak" not in unavailable.model_dump_json()


def test_outbox_only_snapshot_proves_zero_durable_reporting_effects_during_fault():
    source = {
        "reports": [],
        "projections": [],
        "processed_messages": [],
        "outbox_events": _source()["outbox_events"][:1],
    }
    snapshot = _read(
        WhyYouEffectAdapter(_settings(), reporting_loader=lambda _scope: source)
    )

    assert snapshot.source_status is Presence.PRESENT
    assert snapshot.effects["logical_report_ids"] == []
    assert snapshot.effects["projection_document_ids"] == []
    assert snapshot.effects["processed_keys"] == []
    assert snapshot.effects["source_outbox_event_ids"] == [str(EVENT_ID)]
