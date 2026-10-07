"""T031 — Spec 004 report request/record/read adapter contract (contracts/whyyou-spec004-adapter.md).

RED until T037 creates `engine/adapters/whyyou/report_records.py`. The record reader is injected (raw WhyYou
rows including free text); the adapter must keep only identifiers, numbers, states and SHA-256/length of text.
"""

from __future__ import annotations

import hashlib
import json
from importlib import import_module
from uuid import uuid4

import httpx
import pytest

from engine.models import Presence, ReportLane
from tests.fixtures import spec004 as fx

SECRET_TEXTS = (
    "합성 요약 원문",
    "합성 관찰 원문",
    "합성 사유 원문",
    "합성 자막 원문",
    "합성 축 사유 원문",
)


def module():
    return import_module("engine.adapters.whyyou.report_records")


def _lane() -> ReportLane:
    return ReportLane.model_validate(fx.report_lane("E01_EVIDENCE_REMOVAL"))


def _raw_rows(lane: ReportLane) -> dict:
    criterion = lane.criteria[0]
    item_id = str(fx.sid("item", "1"))
    evidence_id = str(fx.uuid7_at(fx.FIXED_AT, 1))
    return {
        "report": {
            "report_id": str(fx.sid("report", "1")),
            "version": 1,
            "model_version": "bedrock-model-v1",
            "prompt_version": "assessment-prompt-v2",
            "config_version": fx.COMMUNICATION_SEPARATED,
            "status": "ready",
            "summary": SECRET_TEXTS[0],
            "overall_score": 72,
            "scoring_inputs": {
                "numerator": 72.0,
                "denominator": 1.0,
                "criteria": [],
                "excluded": [],
            },
        },
        "items": [
            {
                "report_item_id": item_id,
                "criterion_id": str(criterion.criterion_id),
                "competency_model_version_id": str(lane.competency_model_version_id),
                "assessment_state": "confirmed",
                "observation": SECRET_TEXTS[1],
                "rationale": SECRET_TEXTS[2],
                "uncertainty": "합성 불확실성",
                "criterion_weight": 100.0,
                "axis_weights": {},
                "axis_assessments": [
                    {
                        "axis": axis,
                        "label": axis,
                        "score": 72,
                        "rationale": SECRET_TEXTS[4],
                        "quoted_evidence_ids": [evidence_id],
                    }
                    for axis in fx.AXES
                ],
            }
        ],
        "evidence": [
            {
                "evidence_id": evidence_id,
                "report_item_id": item_id,
                "criterion_id": str(criterion.criterion_id),
                "competency_model_version_id": str(lane.competency_model_version_id),
                "answer_turn_id": str(criterion.answer_turn_id),
                "transcript_segment_id": str(criterion.transcript_segment_id),
                "video_start_ms": 1000,
                "video_end_ms": 9000,
                "sufficiency": "direct",
                "observation": SECRET_TEXTS[1],
                "rationale": SECRET_TEXTS[2],
            }
        ],
        "segments": [
            {
                "transcript_segment_id": str(criterion.transcript_segment_id),
                "turn_id": str(criterion.answer_turn_id),
                "version": 1,
                "session_start_ms": 1000,
                "session_end_ms": 9000,
                "speaker": "applicant",
                "confidence": 1.0,
                "text": SECRET_TEXTS[3],
            }
        ],
    }


class _Transaction:
    def __init__(self) -> None:
        self.statements: list[tuple[str, dict]] = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, statement, params=None):
        self.statements.append((str(statement), dict(params or {})))


def _adapter(settings, *, rows=None, reader_error=False, handler=None, transaction=None):
    def reader(_lane):
        if reader_error:
            raise RuntimeError("db down")
        return rows

    client = httpx.Client(
        base_url="http://whyyou.test",
        transport=httpx.MockTransport(handler or (lambda r: httpx.Response(404))),
    )
    return module().WhyYouSpec004ReportAdapter(
        settings,
        transaction_factory=(lambda: transaction) if transaction else None,
        http_client=client,
        rows_reader=reader,
    )


def test_report_request_inserts_one_outbox_event_with_a_controlproof_trace(settings) -> None:
    lane = _lane()
    transaction = _Transaction()
    adapter = _adapter(settings, rows=None, transaction=transaction)
    first = adapter.request_report(lane=lane)
    second = adapter.request_report(lane=lane)
    assert first.ok and second.ok
    assert first.data["event_id"] != second.data["event_id"]
    sql, params = transaction.statements[0]
    assert "INSERT INTO outbox_events" in sql
    assert params["event_type"] == "report.generation_requested"
    assert str(params["aggregate_id"]) == str(lane.interview_session_id)
    assert (
        params["trace_id"] == f"controlproof:{lane.run_id}:{lane.lane_id.value}:{lane.subject_ref}"
    )
    assert json.loads(params["payload"]) == {"interview_session_id": str(lane.interview_session_id)}


def test_records_keep_ids_and_numbers_and_hash_free_text(settings) -> None:
    lane = _lane()
    snapshot = _adapter(settings, rows=_raw_rows(lane)).read_records(lane=lane, phase="GENERATED")
    assert snapshot.source_status is Presence.PRESENT
    assert snapshot.overall_score == 72
    assert snapshot.summary_sha256 == hashlib.sha256(SECRET_TEXTS[0].encode()).hexdigest()
    assert snapshot.items[0].axes[0].quoted_evidence_ids
    assert snapshot.transcript_segments[0].text_length == len(SECRET_TEXTS[3])
    dumped = snapshot.model_dump_json()
    for text in SECRET_TEXTS:
        assert text not in dumped


def test_records_distinguish_absent_and_unavailable(settings) -> None:
    lane = _lane()
    absent = _adapter(
        settings, rows={"report": None, "items": [], "evidence": [], "segments": []}
    ).read_records(lane=lane, phase="GENERATED")
    assert absent.source_status is Presence.ABSENT
    unavailable = _adapter(settings, reader_error=True).read_records(lane=lane, phase="GENERATED")
    assert unavailable.source_status is Presence.UNAVAILABLE
    assert unavailable.source_error_code


def test_processing_read_reports_presence_from_records(settings) -> None:
    lane = _lane()
    assert (
        _adapter(settings, rows=_raw_rows(lane)).read_processing(lane=lane).data["report_present"]
        is True
    )
    empty = {"report": None, "items": [], "evidence": [], "segments": []}
    assert _adapter(settings, rows=empty).read_processing(lane=lane).data["report_present"] is False


def _api_body(lane: ReportLane, *, extra_evidence_field: dict | None = None) -> dict:
    criterion = lane.criteria[0]
    return {
        "report_id": str(fx.sid("report", "1")),
        "report_version": 1,
        "status": "ready",
        "summary": SECRET_TEXTS[0],
        "ai_original_immutable": True,
        "overall_score": 72,
        "communication_score": 72,
        "communication_scored_criteria_count": 1,
        "unscored_criteria_count": 0,
        "scoring_breakdown": {
            "numerator": 72.0,
            "denominator": 1.0,
            "contributions": [
                {
                    "key": str(criterion.criterion_id),
                    "score": 72,
                    "weight": 100.0,
                    "normalized_weight": 1.0,
                    "contribution": 72.0,
                    "criterion_name": "x",
                    "assessment_state": "confirmed",
                    "reason": SECRET_TEXTS[2],
                }
            ],
            "exclusions": [],
        },
        "items": [
            {
                "report_item_id": str(fx.sid("item", "1")),
                "criterion_id": str(criterion.criterion_id),
                "criterion_name": "기준",
                "assessment_state": "confirmed",
                "observation": SECRET_TEXTS[1],
                "rationale": SECRET_TEXTS[2],
                "uncertainty": "u",
                "follow_up_question": None,
                "average_score": 72,
                "criterion_weight": 100.0,
                "axis_breakdown": {"numerator": 72.0},
                "axis_assessments": [
                    {
                        "axis": "depth",
                        "label": "깊이",
                        "score": 72,
                        "rationale": SECRET_TEXTS[4],
                        "quoted_evidence_ids": [str(fx.uuid7_at(fx.FIXED_AT, 1))],
                        "weight": None,
                    }
                ],
                "evidence": [
                    {
                        "evidence_id": str(fx.uuid7_at(fx.FIXED_AT, 1)),
                        "answer_turn_id": str(criterion.answer_turn_id),
                        "transcript_segment_id": str(criterion.transcript_segment_id),
                        "video_start_ms": 1000,
                        "video_end_ms": 9000,
                        "observation": SECRET_TEXTS[1],
                        "rationale": SECRET_TEXTS[2],
                        "sufficiency": "direct",
                    }
                    | (extra_evidence_field or {})
                ],
            }
        ],
        "requirement_assessments": [],
        "human_reviews": [],
    }


def test_api_read_projects_the_allowlist_and_reports_unknown_fields(settings) -> None:
    lane = _lane()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("Authorization")
        if request.url.path.endswith("/report"):
            return httpx.Response(
                200, json=_api_body(lane, extra_evidence_field={"playable": False, "new_flag": 1})
            )
        return httpx.Response(
            200,
            json={
                "entries": [
                    {
                        "entry_id": "t1",
                        "entry_type": "answer",
                        "start_ms": 0,
                        "end_ms": 9,
                        "text": SECRET_TEXTS[3],
                        "technical_failure": False,
                        "question_rationale": None,
                    }
                ],
                "playback": {
                    "url": "http://localhost:4566/media/final.mp4?X-Amz-Signature=s",
                    "expires_at": None,
                    "status": "ready",
                },
            },
        )

    read = _adapter(settings, handler=handler).read_api(
        lane=lane, phase="POST_REMOVAL", include_timeline=True
    )
    assert read.status_code == 200
    assert seen["auth"] == f"Bearer {settings.whyyou_company_token}"
    item = read.report["items"][0]
    assert item["average_score"] == 72
    assert item["evidence"][0]["playable"] is False
    assert "new_flag" in read.unknown_fields
    dumped = read.model_dump_json()
    for text in (*SECRET_TEXTS, "final.mp4", settings.whyyou_company_token):
        assert text not in dumped
    assert read.timeline["playback_status"] == "ready"


def test_api_read_keeps_non_200_status_without_body(settings) -> None:
    lane = _lane()
    read = _adapter(
        settings, handler=lambda r: httpx.Response(500, json={"detail": "boom"})
    ).read_api(lane=lane, phase="POST_REMOVAL")
    assert read.status_code == 500
    assert read.report is None


def test_api_read_transport_failure_is_an_adapter_error(settings) -> None:
    def handler(_request):
        raise httpx.ConnectError("down")

    result = _adapter(settings, handler=handler).read_api(lane=_lane(), phase="PRE_REMOVAL")
    assert result.ok is False and result.code == "REPORT_API_UNAVAILABLE"


def test_missing_report_id_in_records_never_invents_one(settings) -> None:
    lane = _lane()
    rows = _raw_rows(lane)
    rows["report"]["report_id"] = None
    snapshot = _adapter(settings, rows=rows).read_records(lane=lane, phase="GENERATED")
    assert snapshot.source_status is Presence.UNAVAILABLE


@pytest.mark.parametrize("lane_id", ["E01_REFERENCE", "E02_FIRST_APPLICANT"])
def test_report_event_identity_is_per_lane(settings, lane_id) -> None:
    lane = ReportLane.model_validate(
        fx.report_lane(lane_id, [fx.lane_criterion(lane_id, "c-1", fixture_score=72, weight=100.0)])
        if lane_id.startswith("E02")
        else fx.report_lane(lane_id)
    )
    other = ReportLane.model_validate(fx.report_lane("E01_STORAGE_PROBE"))
    adapter = _adapter(settings, transaction=_Transaction())
    assert (
        adapter.request_report(lane=lane).data["event_id"]
        != adapter.request_report(lane=other).data["event_id"]
    )
    assert uuid4()


def test_api_read_keeps_a_non_200_timeline_status(settings) -> None:
    """T078 (SD-1): a failing timeline read must stay visible as a status, not vanish as None."""
    lane = _lane()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/report"):
            return httpx.Response(200, json=_api_body(lane))
        return httpx.Response(500, json={"detail": "boom"})

    read = _adapter(settings, handler=handler).read_api(
        lane=lane, phase="POST_REMOVAL", include_timeline=True
    )
    assert read.status_code == 200
    assert read.timeline == {"status_code": 500, "entries": None, "playback_status": None}
