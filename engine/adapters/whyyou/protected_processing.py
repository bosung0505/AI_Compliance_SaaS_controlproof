"""WhyYou protected-processing attempts and scoped effect projections for N-02."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from datetime import datetime
from typing import Any
from uuid import UUID, uuid5

import httpx
from sqlalchemy import create_engine, text

from engine.adapters.base import AdapterResult
from engine.adapters.whyyou.n02_seed import N02CredentialStore
from engine.adapters.whyyou.synthetic_media import (
    sha256_hex,
    synthetic_recording_chunk,
    synthetic_resume_pdf,
)
from engine.config import Settings
from engine.models import (
    ConsentPurpose,
    N02EffectGroup,
    N02LaneId,
    Phase,
    Presence,
    ProcessingAttemptReceipt,
    ProcessingEntryKind,
    ProcessingResponseClass,
    ProtectedEffectSnapshot,
    ProtectedPathId,
    ProtectedProcessingPath,
    canonical_json_bytes,
    sha256_bytes,
    utcnow,
)

_PATHS = (
    ProtectedProcessingPath(
        path_id=ProtectedPathId.DOCUMENT_ANALYSIS,
        entry_boundary="createSubmissionUploadIntent",
        entry_kind=ProcessingEntryKind.HTTP,
        independent_direct_route=True,
        request_effect_keys=("submission_upload_intents.upload_id",),
        start_effect_keys=("submissions.submission_id",),
        result_effect_keys=("submission_analyses.submission_analysis_id",),
        consent_purpose=ConsentPurpose.DOCUMENT_ANALYSIS,
        source_locator={
            "path": "backend/src/interview_evidence/submission_analysis/api/applicant_routes.py",
            "symbol": "createSubmissionUploadIntent",
        },
    ),
    ProtectedProcessingPath(
        path_id=ProtectedPathId.RECORDING,
        entry_boundary="createInterviewSession",
        entry_kind=ProcessingEntryKind.HTTP,
        independent_direct_route=False,
        earliest_real_boundary="SessionApplicationService._create_session_once",
        required_fixture_kind="n02-recording-boundary-probe-fixture-v1",
        request_effect_keys=("interview_sessions.interview_session_id",),
        start_effect_keys=("session_checkpoints.checkpoint_id",),
        result_effect_keys=("recording_chunks.recording_chunk_id",),
        consent_purpose=ConsentPurpose.RECORDING,
        source_locator={
            "path": "backend/src/interview_evidence/interview_engine/application/session_service.py",
            "symbol": "_create_session_once",
        },
    ),
    ProtectedProcessingPath(
        path_id=ProtectedPathId.AI_ASSESSMENT,
        entry_boundary="report.generation_requested",
        entry_kind=ProcessingEntryKind.DOMAIN_EVENT,
        independent_direct_route=False,
        earliest_real_boundary="ReportRequestedEventHandler.__call__",
        required_fixture_kind="n02-assessment-boundary-probe-fixture-v1",
        request_effect_keys=("outbox_events.outbox_event_id",),
        start_effect_keys=("processing_receipts.receipt_id",),
        result_effect_keys=("reports.report_id",),
        consent_purpose=ConsentPurpose.AI_ASSESSMENT,
        source_locator={
            "path": "backend/src/interview_evidence/runtime/worker.py",
            "symbol": "ReportRequestedEventHandler.__call__",
        },
    ),
)
_ATTEMPT_NAMESPACE = UUID("0ffbda5e-6d56-54af-a426-69b59b6793fc")


class WhyYouProtectedProcessingAdapter:
    def __init__(
        self,
        settings: Settings,
        *,
        http_client: httpx.Client | None = None,
        upload_client: httpx.Client | None = None,
        credentials: N02CredentialStore | None = None,
        effect_reader: Callable[[Mapping[str, Any], ProtectedPathId], Mapping[str, Any]]
        | None = None,
        transaction_factory: Callable[[], AbstractContextManager] | None = None,
    ) -> None:
        self.settings = settings
        self.credentials = credentials or N02CredentialStore()
        self.upload_client = upload_client or httpx.Client(timeout=30)
        self.receipt_wait_seconds: float = 0.0
        self.http = http_client or httpx.Client(
            base_url=settings.whyyou_base_url,
            timeout=10,
            trust_env=False,
        )
        self._engine = None
        if transaction_factory is None:
            self._engine = create_engine(settings.whyyou_database_url)
            transaction_factory = self._engine.begin
        self._transaction_factory = transaction_factory
        self._effect_reader = effect_reader or self._read_effect_projection
        self._baselines: dict[tuple[str, ProtectedPathId], tuple[str, ...]] = {}
        # A lane may attempt one path more than once (fault lane: failure phase, then
        # recovery). Each attempt needs its own identity, and every runner-created input
        # must stay excluded from target effects (ID-003-11).
        self._probe_inputs: dict[tuple[str, ProtectedPathId], tuple[str, ...]] = {}
        self._attempt_ordinals: dict[tuple[str, ProtectedPathId], int] = {}

    def paths(self) -> tuple[ProtectedProcessingPath, ...]:
        return _PATHS

    def attempt(
        self, *, path_id: str, subject: Mapping[str, Any], drive: bool = False
    ) -> ProcessingAttemptReceipt | AdapterResult:
        path = ProtectedPathId(path_id)
        key = (str(subject["subject_ref"]), path)
        ordinal = self._attempt_ordinals.get(key, 0)
        self._attempt_ordinals[key] = ordinal + 1
        if path is ProtectedPathId.AI_ASSESSMENT:
            return self._attempt_assessment(subject, ordinal=ordinal)
        credential = self.credentials.get(str(subject["subject_ref"]))
        if credential is None:
            return AdapterResult(False, "N02_APPLICANT_CREDENTIAL_MISSING")
        sent_at = utcnow()
        request_id = str(_attempt_id(subject, path, "request", ordinal))
        trace_id = _trace_id(subject, path)
        headers = {
            "X-Trace-Id": trace_id,
            "Cookie": f"iep_applicant_session={credential}",
        }
        steps: list[str] = []
        equipment_check_id = str(subject["equipment_check_id"])
        if drive and path is ProtectedPathId.RECORDING:
            # The product flow starts with the applicant's own equipment check (ID-003-18).
            equipment = self._post(
                "/v1/applicant/equipment-checks",
                {
                    "camera": {"status": "ready", "sanitized_code": None},
                    "microphone": {"status": "ready", "sanitized_code": None},
                    "network": {"status": "ready", "sanitized_code": None},
                },
                headers | {"Idempotency-Key": str(_attempt_id(subject, path, "equipment", ordinal))},
            )
            steps.append(f"equipment-check:{_status(equipment)}")
            if equipment is None or not 200 <= equipment.status_code < 300:
                return _attempt_receipt(
                    path=path, subject=subject, request_id=request_id, trace_id=trace_id,
                    sent_at=sent_at, response_class=ProcessingResponseClass.ERROR,
                    status_code=None if equipment is None else equipment.status_code,
                    reason="EQUIPMENT_CHECK_FAILED", drive_steps=tuple(steps),
                )
            equipment_check_id = str(equipment.json()["equipment_check_id"])
        document_bytes = synthetic_resume_pdf()
        if path is ProtectedPathId.DOCUMENT_ANALYSIS:
            route = "/v1/applicant/submissions/upload-intents"
            payload = {
                "source_type": "resume",
                "filename": "controlproof-synthetic-resume.pdf",
                "media_type": "application/pdf",
                "byte_size": len(document_bytes) if drive else 1,
                "sha256": sha256_hex(document_bytes) if drive else "0" * 64,
            }
        else:
            route = "/v1/applicant/interview-sessions"
            payload = {
                "equipment_check_id": equipment_check_id,
                "strategy_id": str(subject["strategy_id"]),
                "acknowledged_partial_analysis": True,
            }
        response = self._post(route, payload, headers | {"Idempotency-Key": request_id})
        if response is None:
            return _attempt_receipt(
                path=path, subject=subject, request_id=request_id, trace_id=trace_id,
                sent_at=sent_at, response_class=ProcessingResponseClass.NO_RESPONSE,
                status_code=None, reason="TRANSPORT_UNAVAILABLE", drive_steps=tuple(steps),
            )
        response_class = (
            ProcessingResponseClass.ACCEPTED
            if 200 <= response.status_code < 300
            else (
                ProcessingResponseClass.DENIED
                if response.status_code in {401, 403}
                else ProcessingResponseClass.ERROR
            )
        )
        reason = (
            "CONSENT_REQUIRED"
            if response_class is ProcessingResponseClass.DENIED
            else response_class.value
        )
        created_session_id: str | None = None
        if drive and response_class is ProcessingResponseClass.ACCEPTED:
            steps.append(f"request:{response.status_code}")
            if path is ProtectedPathId.RECORDING:
                created_session_id = str(response.json()["interview_session_id"])
                steps.extend(self._drive_recording(subject, created_session_id, headers, ordinal))
            else:
                steps.extend(
                    self._drive_document(subject, response.json(), document_bytes, headers, ordinal)
                )
        return _attempt_receipt(
            path=path, subject=subject, request_id=request_id, trace_id=trace_id,
            sent_at=sent_at, response_class=response_class, status_code=response.status_code,
            reason=reason, created_session_id=created_session_id, drive_steps=tuple(steps),
        )

    def _post(self, route: str, payload: Mapping[str, Any], headers: Mapping[str, str]):
        try:
            return self.http.post(route, json=payload, headers=dict(headers))
        except httpx.HTTPError:
            return None

    def _upload(self, intent: Mapping[str, Any], data: bytes) -> str:
        """PUT the bytes to the presigned URL the target issued; returns the step outcome."""
        try:
            response = self.upload_client.request(
                str(intent.get("method", "PUT")),
                str(intent["url"]),
                content=data,
                headers=dict(intent.get("required_headers") or {}),
            )
        except (httpx.HTTPError, KeyError):
            return "upload:none"
        return f"upload:{response.status_code}"

    def _drive_recording(self, subject, session_id: str, headers, ordinal: int) -> list[str]:
        chunk = synthetic_recording_chunk()
        body = {
            "chunk_sequence": 0,
            "byte_size": len(chunk),
            "sha256": sha256_hex(chunk),
            "session_start_ms": 0,
            "session_end_ms": 2000,
        }
        key = str(_attempt_id(subject, ProtectedPathId.RECORDING, "media", ordinal))
        base = f"/v1/applicant/interview-sessions/{session_id}"
        intent = self._post(f"{base}/media-upload-intents", body, headers | {"Idempotency-Key": key})
        steps = [f"media-intent:{_status(intent)}"]
        if intent is None or not 200 <= intent.status_code < 300:
            return steps
        steps.append(self._upload(intent.json(), chunk))
        if not steps[-1].endswith(("200", "201", "204")):
            return steps
        # The confirmation reuses the intent's idempotency key and body (target contract).
        confirm = self._post(f"{base}/media-uploads", body, headers | {"Idempotency-Key": key})
        steps.append(f"confirm:{_status(confirm)}")
        return steps

    def _drive_document(self, subject, intent, data: bytes, headers, ordinal: int) -> list[str]:
        steps = [self._upload(intent, data)]
        if not steps[-1].endswith(("200", "201", "204")):
            return steps
        register = self._post(
            "/v1/applicant/submissions",
            {"material_type": "resume", "source_type": "resume", "upload_id": str(intent["upload_id"])},
            headers | {"Idempotency-Key": str(_attempt_id(subject, ProtectedPathId.DOCUMENT_ANALYSIS, "register", ordinal))},
        )
        steps.append(f"register:{_status(register)}")
        return steps

    def _attempt_assessment(
        self, subject: Mapping[str, Any], *, ordinal: int = 0
    ) -> ProcessingAttemptReceipt | AdapterResult:
        sent_at = utcnow()
        request_id = str(
            _attempt_id(subject, ProtectedPathId.AI_ASSESSMENT, "request", ordinal)
        )
        event_id = _attempt_id(subject, ProtectedPathId.AI_ASSESSMENT, "event", ordinal)
        trace_id = _trace_id(subject, ProtectedPathId.AI_ASSESSMENT)
        params = {
            "outbox_event_id": event_id,
            "company_id": UUID(str(self.settings.whyyou_company_id)),
            "aggregate_id": UUID(str(subject["interview_session_id"])),
            "event_type": "report.generation_requested",
            "payload": json.dumps(
                {"interview_session_id": str(subject["interview_session_id"])}
            ),
            "idempotency_key": request_id,
            "trace_id": trace_id,
            "occurred_at": sent_at,
        }
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
        except Exception as exc:  # noqa: BLE001 - normalize database/provider detail
            return AdapterResult(
                False, "N02_ASSESSMENT_EVENT_WRITE_FAILED", detail=type(exc).__name__
            )
        probe_input_effect_id = f"event:{event_id}"
        probe_key = (str(subject["subject_ref"]), ProtectedPathId.AI_ASSESSMENT)
        self._probe_inputs[probe_key] = (*self._probe_inputs.get(probe_key, ()), probe_input_effect_id)
        return _attempt_receipt(
            path=ProtectedPathId.AI_ASSESSMENT,
            subject=subject,
            request_id=request_id,
            trace_id=trace_id,
            sent_at=sent_at,
            response_class=ProcessingResponseClass.SUBMITTED,
            status_code=None,
            reason="PROBE_INPUT_PERSISTED",
            probe_input_effect_id=probe_input_effect_id,
        )

    def read_effects(
        self,
        *,
        path_id: str,
        subject: Mapping[str, Any],
        phase: str,
        step_id: str,
    ) -> ProtectedEffectSnapshot | AdapterResult:
        path = ProtectedPathId(path_id)
        key = (str(subject["subject_ref"]), path)
        try:
            projection = self._effect_reader(subject, path)
        except Exception as exc:  # noqa: BLE001 - source errors are evidence, not exceptions
            projection = {
                "source_status": Presence.UNAVAILABLE.value,
                "error_code": type(exc).__name__.upper(),
            }
        status = Presence(str(projection.get("source_status", Presence.PRESENT.value)))
        if status is Presence.UNAVAILABLE:
            return ProtectedEffectSnapshot(
                run_id=UUID(str(subject["run_id"])),
                lane_id=N02LaneId(str(subject["lane_id"])),
                subject_ref=str(subject["subject_ref"]),
                path_id=path,
                phase=Phase(phase),
                step_id=step_id,
                attempt=1,
                effect_group=N02EffectGroup(path.value),
                source_status=status,
                source_error_code=str(projection.get("error_code", "SOURCE_UNAVAILABLE")),
                state_digest=sha256_bytes(b"unavailable"),
                captured_at=utcnow(),
            )
        current = tuple(sorted(str(value) for value in projection.get("effect_ids", ())))
        fixtures = tuple(
            sorted(
                {str(value) for value in subject.get("allowed_fixture_effect_ids", ())}
                & set(current)
            )
        )
        if Phase(phase) is Phase.BASELINE:
            self._baselines[key] = current
        baseline = self._baselines.get(key, ())
        recorded_inputs = self._probe_inputs.get(key, ())
        # The latest runner input drives start-receipt matching; all of them are excluded.
        probe_input = recorded_inputs[-1] if recorded_inputs else None
        probe_inputs = tuple(sorted(item for item in recorded_inputs if item in current))
        # The consumer's processed row for a runner input records that the target handled
        # the input (refused or started); it is not a protected effect (ID-003-17).
        bookkeeping = tuple(
            sorted(
                f"processed:{item.removeprefix('event:')}"
                for item in probe_inputs
                if f"processed:{item.removeprefix('event:')}" in current
            )
        )
        new = tuple(
            sorted(
                set(current)
                - set(baseline)
                - set(fixtures)
                - set(probe_inputs)
                - set(bookkeeping)
            )
        )
        status = Presence.PRESENT if current else Presence.ABSENT
        status_projection = dict(projection.get("status_projection", {}))
        start_receipt_ids: tuple[str, ...] = ()
        refusal_receipt_ids: tuple[str, ...] = ()
        if (
            path is ProtectedPathId.AI_ASSESSMENT
            and probe_input is not None
            and self.settings.observer_enabled
        ):
            event_id = probe_input.removeprefix("event:")
            # The wait budget comes from the scenario poll interval via the executor's
            # stabilizer (ID-003-10/T085); without it there is no pre-wait at all.
            deadline = time.monotonic() + float(self.receipt_wait_seconds)
            while True:
                observed = self.read_processing_receipts(
                    run_id=str(subject["run_id"]),
                    lane_id=str(subject["lane_id"]),
                    subject_ref=str(subject["subject_ref"]),
                )
                if not observed.ok:
                    status_projection["observer_status"] = "UNAVAILABLE"
                    break
                matched = [
                    row
                    for row in observed.data.get("receipts", ())
                    if isinstance(row, dict)
                    and row.get("path_id") == ProtectedPathId.AI_ASSESSMENT.value
                    and row.get("request_or_event_id") == event_id
                    and isinstance(row.get("receipt_id"), str)
                ]
                # Every delivery of the input leaves its own receipt; a start in any
                # delivery outweighs a refusal in another (judged by the A4/A6 rules).
                start_receipt_ids = tuple(
                    sorted(
                        str(row["receipt_id"])
                        for row in matched
                        if row.get("boundary") == "REPORT_ASSESSMENT_STARTED"
                    )
                )
                refusal_receipt_ids = tuple(
                    sorted(
                        str(row["receipt_id"])
                        for row in matched
                        if row.get("boundary") == "REPORT_ASSESSMENT_REFUSED"
                    )
                )
                if start_receipt_ids or refusal_receipt_ids or time.monotonic() >= deadline:
                    break
                time.sleep(min(_RECEIPT_POLL_GRANULARITY, float(self.receipt_wait_seconds)))
        digest = sha256_bytes(
            canonical_json_bytes(
                {
                    "path_id": path.value,
                    "current": current,
                    "fixture": fixtures,
                    "probe_input": probe_inputs,
                    "probe_bookkeeping": bookkeeping,
                    "start_receipts": start_receipt_ids,
                    "refusal_receipts": refusal_receipt_ids,
                    "status_projection": status_projection,
                }
            )
        )
        return ProtectedEffectSnapshot(
            run_id=UUID(str(subject["run_id"])),
            lane_id=N02LaneId(str(subject["lane_id"])),
            subject_ref=str(subject["subject_ref"]),
            path_id=path,
            phase=Phase(phase),
            step_id=step_id,
            attempt=1,
            effect_group=N02EffectGroup(path.value),
            request_ids=tuple(
                item
                for item in current
                if item.startswith(
                    {
                        ProtectedPathId.DOCUMENT_ANALYSIS: ("upload:", "analysis-event:"),
                        ProtectedPathId.RECORDING: ("session:",),
                        ProtectedPathId.AI_ASSESSMENT: ("event:",),
                    }[path]
                )
            ),
            # Results are what this attempt newly produced: a fixture strategy, a baseline row
            # or the runner's own input is never a result (ID-003-18).
            result_ids=tuple(
                item
                for item in new
                if item.startswith(
                    {
                        ProtectedPathId.DOCUMENT_ANALYSIS: ("analysis:", "strategy:"),
                        ProtectedPathId.RECORDING: ("chunk:", "asset:"),
                        ProtectedPathId.AI_ASSESSMENT: ("report:", "item:", "assistant:"),
                    }[path]
                )
            ),
            start_receipt_ids=start_receipt_ids,
            refusal_receipt_ids=refusal_receipt_ids,
            status_projection=status_projection,
            baseline_effect_ids=baseline,
            fixture_effect_ids=fixtures,
            probe_input_effect_ids=probe_inputs,
            probe_bookkeeping_effect_ids=bookkeeping,
            current_effect_ids=current,
            new_effect_ids=new,
            source_status=status,
            state_digest=digest,
            captured_at=utcnow(),
        )

    def read_processing_receipts(
        self, *, run_id: str, lane_id: str, subject_ref: str
    ) -> AdapterResult:
        path = self.settings.observer_root / "receipts" / f"{UUID(run_id)}.jsonl"
        if not path.exists():
            return AdapterResult(True, "N02_PROCESSING_RECEIPTS_ABSENT", {"receipts": ()})
        try:
            receipts = tuple(
                payload
                for line in path.read_text(encoding="utf-8").splitlines()
                if (payload := json.loads(line)).get("run_id") == str(UUID(run_id))
                and payload.get("lane_id") == lane_id
                and payload.get("subject_ref") == subject_ref
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return AdapterResult(
                False, "N02_PROCESSING_RECEIPTS_UNAVAILABLE", detail=type(exc).__name__
            )
        return AdapterResult(True, "N02_PROCESSING_RECEIPTS_READ", {"receipts": receipts})

    def _read_effect_projection(
        self, subject: Mapping[str, Any], path: ProtectedPathId
    ) -> Mapping[str, Any]:
        queries = {
            ProtectedPathId.DOCUMENT_ANALYSIS: (
                "SELECT 'upload:' || upload_id::text AS effect_id "
                "FROM submission_upload_intents WHERE company_id=:company_id "
                "AND applicant_id=:applicant_id UNION ALL "
                "SELECT 'submission:' || submission_id::text FROM submissions "
                "WHERE company_id=:company_id AND applicant_id=:applicant_id UNION ALL "
                "SELECT CASE WHEN a.status IN ('ready', 'partial') THEN 'analysis:' "
                "ELSE 'analysis-' || a.status || ':' END || a.analysis_id::text "
                "FROM submission_analyses a JOIN submissions s "
                "ON s.company_id=a.company_id AND s.submission_id=a.submission_id "
                "WHERE s.company_id=:company_id AND s.applicant_id=:applicant_id UNION ALL "
                "SELECT 'strategy:' || interview_strategy_id::text "
                "FROM interview_strategies WHERE company_id=:company_id "
                "AND applicant_id=:applicant_id UNION ALL "
                "SELECT 'analysis-event:' || o.outbox_event_id::text "
                "FROM outbox_events o JOIN submissions s "
                "ON s.company_id=o.company_id AND s.submission_id=o.aggregate_id "
                "WHERE s.company_id=:company_id AND s.applicant_id=:applicant_id "
                "AND o.event_type='submission.analysis_requested'"
            ),
            ProtectedPathId.RECORDING: (
                "SELECT 'session:' || interview_session_id::text AS effect_id "
                "FROM interview_sessions WHERE company_id=:company_id "
                "AND applicant_id=:applicant_id UNION ALL "
                "SELECT 'chunk:' || c.recording_chunk_id::text "
                "FROM recording_chunks c JOIN interview_sessions s "
                "ON s.company_id=c.company_id "
                "AND s.interview_session_id=c.interview_session_id "
                "WHERE s.company_id=:company_id AND s.applicant_id=:applicant_id UNION ALL "
                "SELECT 'asset:' || a.recording_asset_id::text "
                "FROM recording_assets a JOIN interview_sessions s "
                "ON s.company_id=a.company_id "
                "AND s.interview_session_id=a.interview_session_id "
                "WHERE s.company_id=:company_id AND s.applicant_id=:applicant_id"
            ),
            ProtectedPathId.AI_ASSESSMENT: (
                "SELECT 'event:' || outbox_event_id::text AS effect_id FROM outbox_events "
                "WHERE company_id=:company_id AND aggregate_id=:session_id "
                "AND event_type='report.generation_requested' UNION ALL "
                "SELECT 'report:' || report_id::text AS effect_id FROM reports "
                "WHERE company_id=:company_id AND interview_session_id=:session_id "
                "UNION ALL SELECT 'item:' || i.report_item_id::text "
                "FROM report_items i JOIN reports r ON r.company_id=i.company_id "
                "AND r.report_id=i.report_id WHERE r.company_id=:company_id "
                "AND r.interview_session_id=:session_id UNION ALL "
                "SELECT 'assistant:' || d.assistant_document_id::text "
                "FROM assistant_retrieval_documents d JOIN reports r "
                "ON r.company_id=d.company_id AND r.report_id=d.report_id "
                "WHERE r.company_id=:company_id "
                "AND r.interview_session_id=:session_id UNION ALL "
                "SELECT 'processed:' || p.event_id::text FROM processed_messages p "
                "JOIN outbox_events o ON o.outbox_event_id=p.event_id "
                "WHERE o.company_id=:company_id AND o.aggregate_id=:session_id "
                "AND o.event_type='report.generation_requested'"
            ),
        }
        params = {
            "company_id": UUID(self.settings.whyyou_company_id),
            "applicant_id": UUID(str(subject["applicant_id"])),
            "session_id": UUID(str(subject["interview_session_id"])),
        }
        with self._transaction_factory() as connection:
            rows = connection.execute(text(queries[path]), params)
            ids = [row[0] for row in rows]
        return {"source_status": Presence.PRESENT.value, "effect_ids": ids}


def _trace_id(subject: Mapping[str, Any], path: ProtectedPathId) -> str:
    return (
        f"controlproof:{UUID(str(subject['run_id']))}:"
        f"{N02LaneId(str(subject['lane_id'])).value}:{subject['subject_ref']}"
    )


def _attempt_id(
    subject: Mapping[str, Any], path: ProtectedPathId, identity_kind: str, ordinal: int = 0
) -> UUID:
    parts = [
        str(UUID(str(subject["run_id"]))),
        N02LaneId(str(subject["lane_id"])).value,
        path.value,
        identity_kind,
    ]
    if ordinal:
        # First attempt keeps the original identity; later attempts in the same lane differ.
        parts.append(f"attempt-{ordinal + 1}")
    return uuid5(_ATTEMPT_NAMESPACE, ":".join(parts))


def _attempt_receipt(
    *,
    path: ProtectedPathId,
    subject: Mapping[str, Any],
    request_id: str,
    trace_id: str,
    sent_at: datetime,
    response_class: ProcessingResponseClass,
    status_code: int | None,
    reason: str,
    probe_input_effect_id: str | None = None,
    created_session_id: str | None = None,
    drive_steps: tuple[str, ...] = (),
) -> ProcessingAttemptReceipt:
    entry = (
        ProcessingEntryKind.DOMAIN_EVENT
        if path is ProtectedPathId.AI_ASSESSMENT
        else ProcessingEntryKind.HTTP
    )
    return ProcessingAttemptReceipt(
        run_id=UUID(str(subject["run_id"])),
        lane_id=N02LaneId(str(subject["lane_id"])),
        subject_ref=str(subject["subject_ref"]),
        path_id=path,
        entry_kind=entry,
        operation_id={item.path_id: item.entry_boundary for item in _PATHS}[path],
        request_id=request_id,
        trace_id_digest=hashlib.sha256(trace_id.encode("utf-8")).hexdigest(),
        sent_at=sent_at,
        response_at=(None if response_class is ProcessingResponseClass.NO_RESPONSE else utcnow()),
        response_class=response_class,
        status_code=status_code,
        sanitized_reason_code=reason,
        probe_input_effect_id=probe_input_effect_id,
        created_session_id=created_session_id,
        drive_steps=drive_steps,
        source_ref=f"whyyou:{path.value.casefold()}:v1",
    )


_RECEIPT_POLL_GRANULARITY = 0.05


def _status(response) -> str:
    return "none" if response is None else str(response.status_code)
