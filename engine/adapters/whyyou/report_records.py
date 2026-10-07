"""WhyYou report request, stored-record and company-API projections for Spec 004 (T037).

Raw facts only. Free text (report summary, item observation/rationale/uncertainty, axis rationale, transcript
text) never leaves this module: it becomes SHA-256 + length. API responses are projected through an allowlist;
any response field this contract does not know is reported by name only (`unknown_fields`) so a later WhyYou
change that adds an evidence-availability indicator is visible without being guessed at (scenario contract
E01-A3).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid5

import httpx
from sqlalchemy import create_engine, text

from engine.adapters.base import AdapterResult
from engine.config import Settings
from engine.models import (
    EvidenceProjection,
    Presence,
    ReportItemProjection,
    ReportLane,
    ReportReadSnapshot,
    ReportRecordSnapshot,
    StoredAxisProjection,
    TranscriptSegmentProjection,
    canonical_json_bytes,
    sha256_bytes,
    utcnow,
)

_EVENT_NAMESPACE = UUID("5b1d7f0c-7a2e-5b8e-9a64-6c2d4c7e9f04")
#: WhyYou `_UNVERIFIED_RATIONALE` (reporting/application/assessment_prompt.py).
UNVERIFIED_NOTICE = "인용한 답변을 확인할 수 없어 점수를 보류했습니다."
#: H-4 (a) allowlist of evidence-availability indicators (scenario contract E01-A3).
AVAILABILITY_FIELDS = frozenset({"playable", "available", "transcript_available"})

_TOP_KEEP = {
    "report_id",
    "report_version",
    "status",
    "overall_score",
    "communication_score",
    "communication_scored_criteria_count",
    "unscored_criteria_count",
    "scoring_breakdown",
    "items",
}
_TOP_DROP = {
    "summary",
    "ai_original_immutable",
    "requirement_assessments",
    "human_reviews",
    "retryable",
    "message",
}
_BREAKDOWN_KEEP = {"numerator", "denominator", "contributions", "exclusions"}
_CONTRIBUTION_KEEP = {
    "key",
    "score",
    "weight",
    "normalized_weight",
    "contribution",
    "assessment_state",
}
_CONTRIBUTION_DROP = {"criterion_name", "reason"}
_ITEM_KEEP = {
    "report_item_id",
    "criterion_id",
    "assessment_state",
    "average_score",
    "criterion_weight",
    "axis_assessments",
    "evidence",
}
_ITEM_DROP = {
    "criterion_name",
    "observation",
    "rationale",
    "uncertainty",
    "follow_up_question",
    "axis_breakdown",
}
_AXIS_KEEP = {"axis", "score", "quoted_evidence_ids", "weight"}
_AXIS_DROP = {"label", "rationale"}
_EVIDENCE_KEEP = {
    "evidence_id",
    "answer_turn_id",
    "transcript_segment_id",
    "video_start_ms",
    "video_end_ms",
    "sufficiency",
} | AVAILABILITY_FIELDS
_EVIDENCE_DROP = {"observation", "rationale"}
_ENTRY_KEEP = {"entry_id", "entry_type", "start_ms", "end_ms", "technical_failure"}
_ENTRY_DROP = {"text", "question_rationale"}


def _text_digest(value: Any) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _jsonable(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _loaded(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


class WhyYouSpec004ReportAdapter:
    """Implements `ReportRequestAdapter` and `ReportRecordAdapter`."""

    def __init__(
        self,
        settings: Settings,
        *,
        transaction_factory: Callable[[], AbstractContextManager] | None = None,
        http_client: httpx.Client | None = None,
        rows_reader: Callable[[ReportLane], Mapping[str, Any]] | None = None,
    ) -> None:
        self.settings = settings
        self._engine = None
        if transaction_factory is None and rows_reader is None:
            self._engine = create_engine(settings.whyyou_database_url)
            transaction_factory = self._engine.begin
        self._transaction_factory = transaction_factory
        self._rows_reader = rows_reader or self._read_rows
        self.http = http_client or httpx.Client(
            base_url=settings.whyyou_base_url, timeout=10, trust_env=False
        )
        self._ordinals: dict[str, int] = {}

    # --- requests ---------------------------------------------------------------------------------

    def request_report(self, *, lane: ReportLane) -> AdapterResult:
        key = f"{lane.run_id}:{lane.lane_id.value}"
        ordinal = self._ordinals.get(key, 0)
        self._ordinals[key] = ordinal + 1
        event_id = uuid5(_EVENT_NAMESPACE, f"{key}:report-event:{ordinal}")
        trace_id = f"controlproof:{lane.run_id}:{lane.lane_id.value}:{lane.subject_ref}"
        params = {
            "outbox_event_id": event_id,
            "company_id": UUID(str(self.settings.whyyou_company_id)),
            "aggregate_id": lane.interview_session_id,
            "event_type": "report.generation_requested",
            "payload": json.dumps({"interview_session_id": str(lane.interview_session_id)}),
            "idempotency_key": str(event_id),
            "trace_id": trace_id,
            "occurred_at": utcnow(),
        }
        if self._transaction_factory is None:
            return AdapterResult(False, "REPORT_REQUEST_UNAVAILABLE")
        try:
            with self._transaction_factory() as connection:
                connection.execute(
                    text(
                        """
                        INSERT INTO outbox_events (
                            outbox_event_id, company_id, aggregate_type, aggregate_id,
                            aggregate_version, event_type, event_version, payload,
                            idempotency_key, trace_id, occurred_at, publish_status,
                            publish_attempts
                        ) VALUES (
                            :outbox_event_id, :company_id, 'interview_session', :aggregate_id,
                            1, :event_type, 1, CAST(:payload AS jsonb),
                            :idempotency_key, :trace_id, :occurred_at, 'pending', 0
                        )
                        """
                    ),
                    params,
                )
        except Exception as exc:  # noqa: BLE001 - normalize database detail
            return AdapterResult(False, "REPORT_REQUEST_WRITE_FAILED", detail=type(exc).__name__)
        return AdapterResult(
            True,
            "REPORT_REQUESTED",
            {
                "event_id": str(event_id),
                "trace_id_digest": hashlib.sha256(trace_id.encode()).hexdigest(),
            },
        )

    def read_processing(self, *, lane: ReportLane) -> AdapterResult:
        try:
            rows = self._rows_reader(lane)
        except Exception as exc:  # noqa: BLE001 - unavailability is an evidence fact
            return AdapterResult(False, "REPORT_PROCESSING_UNAVAILABLE", detail=type(exc).__name__)
        # The WhyYou observer keeps receipts for N-02 lanes only (ID-004-11); presence comes from the DB.
        return AdapterResult(
            True,
            "REPORT_PROCESSING_READ",
            {"report_present": bool(rows.get("report")), "receipts": self._receipts(lane)},
        )

    def _receipts(self, lane: ReportLane) -> tuple[Mapping[str, Any], ...]:
        path = self.settings.observer_root / "receipts" / f"{lane.run_id}.jsonl"
        try:
            lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
            return tuple(
                payload
                for line in lines
                if (payload := json.loads(line)).get("lane_id") == lane.lane_id.value
                and payload.get("subject_ref") == lane.subject_ref
            )
        except (OSError, ValueError):
            return ()

    # --- stored records ------------------------------------------------------------------------------

    def _read_rows(self, lane: ReportLane) -> Mapping[str, Any]:
        company = UUID(str(self.settings.whyyou_company_id))
        with self._transaction_factory() as connection:
            reports = (
                connection.execute(
                    text(
                        "SELECT report_id, version, model_version, prompt_version, config_version, status, "
                        "summary, overall_score, scoring_inputs FROM reports WHERE company_id=:company "
                        "AND interview_session_id=:session ORDER BY version DESC"
                    ),
                    {"company": company, "session": lane.interview_session_id},
                )
                .mappings()
                .all()
            )
            segments = (
                connection.execute(
                    text(
                        "SELECT * FROM transcript_segments WHERE company_id=:company "
                        "AND interview_session_id=:session ORDER BY transcript_segment_id"
                    ),
                    {"company": company, "session": lane.interview_session_id},
                )
                .mappings()
                .all()
            )
            if not reports:
                return {
                    "report": None,
                    "items": [],
                    "evidence": [],
                    "segments": [dict(row) for row in segments],
                }
            report = dict(reports[0])
            items = (
                connection.execute(
                    text(
                        "SELECT report_item_id, criterion_id, competency_model_version_id, assessment_state, "
                        "observation, rationale, uncertainty, criterion_weight, axis_weights, axis_assessments "
                        "FROM report_items WHERE company_id=:company AND report_id=:report ORDER BY criterion_id"
                    ),
                    {"company": company, "report": report["report_id"]},
                )
                .mappings()
                .all()
            )
            evidence = (
                connection.execute(
                    text(
                        "SELECT e.evidence_id, e.report_item_id, e.criterion_id, e.competency_model_version_id, "
                        "e.answer_turn_id, e.transcript_segment_id, e.video_start_ms, e.video_end_ms, "
                        "e.sufficiency, e.observation, e.rationale FROM evidence e JOIN report_items i "
                        "ON i.company_id=e.company_id AND i.report_item_id=e.report_item_id "
                        "WHERE e.company_id=:company AND i.report_id=:report ORDER BY e.evidence_id"
                    ),
                    {"company": company, "report": report["report_id"]},
                )
                .mappings()
                .all()
            )
        return {
            "report": report,
            "report_count": len(reports),
            "items": [dict(row) for row in items],
            "evidence": [dict(row) for row in evidence],
            "segments": [dict(row) for row in segments],
        }

    def read_records(self, *, lane: ReportLane, phase: str) -> ReportRecordSnapshot | AdapterResult:
        base = {
            "run_id": lane.run_id,
            "lane_id": lane.lane_id,
            "subject_ref": lane.subject_ref,
            "phase": phase,
        }
        try:
            rows = self._rows_reader(lane)
            report = rows.get("report")
            if report is None:
                return ReportRecordSnapshot(
                    **base,
                    report_id=None,
                    source_status=Presence.ABSENT,
                    state_digest=sha256_bytes(
                        canonical_json_bytes({"lane": lane.lane_id.value, "report": None})
                    ),
                )
            if not report.get("report_id"):
                raise ValueError("report row without report_id")
            items = tuple(_item(item) for item in rows.get("items", ()))
            evidence = tuple(_evidence(item) for item in rows.get("evidence", ()))
            segments = tuple(_segment(item) for item in rows.get("segments", ()))
        except Exception as exc:  # noqa: BLE001 - unavailability is an evidence fact
            return ReportRecordSnapshot(
                **base,
                report_id=None,
                source_status=Presence.UNAVAILABLE,
                source_error_code=type(exc).__name__.upper(),
                state_digest=sha256_bytes(
                    canonical_json_bytes({"lane": lane.lane_id.value, "error": type(exc).__name__})
                ),
            )
        body = {
            "report_id": str(report["report_id"]),
            "overall_score": report.get("overall_score"),
            "scoring_inputs": _jsonable(_loaded(report.get("scoring_inputs")) or {}),
            "items": [item.model_dump(mode="json") for item in items],
            "evidence": [item.model_dump(mode="json") for item in evidence],
            "segments": [item.model_dump(mode="json") for item in segments],
        }
        return ReportRecordSnapshot(
            **base,
            report_id=UUID(str(report["report_id"])),
            report_version=report.get("version"),
            model_version=report.get("model_version"),
            prompt_version=report.get("prompt_version"),
            config_version=report.get("config_version"),
            status=report.get("status"),
            summary_sha256=_text_digest(report.get("summary")),
            summary_length=len(str(report.get("summary") or "")),
            overall_score=report.get("overall_score"),
            scoring_inputs=body["scoring_inputs"],
            items=items,
            evidence=evidence,
            transcript_segments=segments,
            source_status=Presence.PRESENT,
            state_digest=sha256_bytes(canonical_json_bytes(body)),
        )

    # --- company API ---------------------------------------------------------------------------------

    def read_api(
        self, *, lane: ReportLane, phase: str, include_timeline: bool = False
    ) -> ReportReadSnapshot | AdapterResult:
        headers = {"Authorization": f"Bearer {self.settings.whyyou_company_token}"}
        base = f"/v1/interview-sessions/{lane.interview_session_id}"
        unknown: set[str] = set()
        try:
            response = self.http.get(f"{base}/report", headers=headers)
            report = (
                _project_report(_json(response), unknown) if response.status_code == 200 else None
            )
            timeline = None
            if include_timeline:
                timeline_response = self.http.get(f"{base}/timeline", headers=headers)
                if timeline_response.status_code == 200:
                    timeline = _project_timeline(_json(timeline_response), unknown)
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            return AdapterResult(False, "REPORT_API_UNAVAILABLE", detail=type(exc).__name__)
        payload = {"status_code": response.status_code, "report": report, "timeline": timeline}
        return ReportReadSnapshot(
            phase=phase,
            request_id=uuid5(_EVENT_NAMESPACE, f"{lane.run_id}:{lane.lane_id.value}:{phase}:read"),
            status_code=response.status_code,
            report=report,
            timeline=timeline,
            unknown_fields=tuple(sorted(unknown)),
            read_digest=sha256_bytes(canonical_json_bytes(payload)),
        )


def _json(response: httpx.Response) -> Mapping[str, Any]:
    body = response.json()
    if not isinstance(body, Mapping):
        raise TypeError("response body is not an object")
    return body


def _keep(
    value: Mapping[str, Any], keep: set[str], drop: set[str], unknown: set[str]
) -> dict[str, Any]:
    unknown.update(str(key) for key in value if key not in keep and key not in drop)
    return {key: value[key] for key in value if key in keep}


def _project_report(body: Mapping[str, Any], unknown: set[str]) -> dict[str, Any]:
    report = _keep(body, _TOP_KEEP, _TOP_DROP, unknown)
    breakdown = report.get("scoring_breakdown")
    if isinstance(breakdown, Mapping):
        kept = _keep(breakdown, _BREAKDOWN_KEEP, set(), unknown)
        for name in ("contributions", "exclusions"):
            kept[name] = [
                _keep(entry, _CONTRIBUTION_KEEP, _CONTRIBUTION_DROP, unknown)
                for entry in kept.get(name, [])
            ]
        report["scoring_breakdown"] = kept
    items = []
    for raw in report.get("items", []):
        item = _keep(raw, _ITEM_KEEP, _ITEM_DROP, unknown)
        item["axis_assessments"] = [
            _keep(axis, _AXIS_KEEP, _AXIS_DROP, unknown)
            for axis in item.get("axis_assessments", [])
        ]
        item["evidence"] = [
            _keep(entry, _EVIDENCE_KEEP, _EVIDENCE_DROP, unknown)
            for entry in item.get("evidence", [])
        ]
        items.append(item)
    report["items"] = items
    return _jsonable(report)


def _project_timeline(body: Mapping[str, Any], unknown: set[str]) -> dict[str, Any]:
    entries = []
    for raw in body.get("entries", []):
        entry = _keep(raw, _ENTRY_KEEP, _ENTRY_DROP, unknown)
        entry["text_sha256"] = _text_digest(raw.get("text"))
        entries.append(entry)
    playback = body.get("playback") if isinstance(body.get("playback"), Mapping) else {}
    return _jsonable({"entries": entries, "playback_status": playback.get("status")})


def _axis(raw: Mapping[str, Any]) -> StoredAxisProjection:
    rationale = raw.get("rationale")
    return StoredAxisProjection(
        axis=str(raw["axis"]),
        score=raw.get("score"),
        quoted_evidence_ids=tuple(
            UUID(str(value)) for value in raw.get("quoted_evidence_ids") or ()
        ),
        rationale_sha256=_text_digest(rationale),
        rationale_is_unverified_notice=rationale == UNVERIFIED_NOTICE,
    )


def _item(raw: Mapping[str, Any]) -> ReportItemProjection:
    return ReportItemProjection(
        report_item_id=raw["report_item_id"],
        criterion_id=raw["criterion_id"],
        competency_model_version_id=raw["competency_model_version_id"],
        assessment_state=str(raw["assessment_state"]),
        criterion_weight=1.0
        if raw.get("criterion_weight") is None
        else float(raw["criterion_weight"]),
        axis_weights=dict(_loaded(raw.get("axis_weights")) or {}),
        axes=tuple(_axis(axis) for axis in _loaded(raw.get("axis_assessments")) or ()),
        observation_sha256=_text_digest(raw.get("observation")),
        rationale_sha256=_text_digest(raw.get("rationale")),
        uncertainty_sha256=_text_digest(raw.get("uncertainty")),
    )


def _evidence(raw: Mapping[str, Any]) -> EvidenceProjection:
    return EvidenceProjection(
        evidence_id=raw["evidence_id"],
        report_item_id=raw["report_item_id"],
        criterion_id=raw["criterion_id"],
        competency_model_version_id=raw["competency_model_version_id"],
        answer_turn_id=raw["answer_turn_id"],
        transcript_segment_id=raw["transcript_segment_id"],
        video_start_ms=raw["video_start_ms"],
        video_end_ms=raw["video_end_ms"],
        sufficiency=str(raw["sufficiency"]),
        observation_sha256=_text_digest(raw.get("observation")),
        rationale_sha256=_text_digest(raw.get("rationale")),
    )


def _segment(raw: Mapping[str, Any]) -> TranscriptSegmentProjection:
    return TranscriptSegmentProjection(
        transcript_segment_id=raw["transcript_segment_id"],
        turn_id=raw["turn_id"],
        version=raw["version"],
        session_start_ms=raw["session_start_ms"],
        session_end_ms=raw["session_end_ms"],
        text_sha256=_text_digest(raw.get("text")),
        text_length=len(str(raw.get("text") or "")),
        row_digest=sha256_bytes(canonical_json_bytes(_jsonable(dict(raw)))),
    )
