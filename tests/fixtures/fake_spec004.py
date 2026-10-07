"""Deterministic fake WhyYou for Spec 004 (T019).

One object implements every Spec 004 protocol in `engine/adapters/base.py` and models the WhyYou behaviour the
Spec 004 source baseline established:

- the report worker stores the fixed model's citations only when they are non-empty and belong to the
  criterion's own Evidence (`verified_against`); otherwise the axis score is emptied with the fixed notice;
- the company report read does not look at transcript segments (prediction P1), unless `removal_indicator`
  simulates a WhyYou change that exposes a missing segment;
- reading stored axes drops a "score without citation" axis (`_restored_axes`);
- versions are created and published through the product API; a published version never changes;
- scores follow WhyYou's arithmetic (the ControlProof copy, verified against WhyYou in T017).

Options turn single facts wrong so judges and executors can be driven to FAIL/INCONCLUSIVE.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from engine.adapters.base import AdapterResult
from engine.judges.e02_scoring import (
    COMMUNICATION_SEPARATED_CONFIG_VERSION,
    PINNED_SOURCES,
    communication_aggregate,
    criterion_aggregate,
    report_aggregate,
)
from engine.models import (
    ChangeInjection,
    ChangeInjectionKind,
    ChangeInjectionState,
    CitationMode,
    ConsentPolicySnapshot,
    ConsentPurpose,
    CriteriaVersionSnapshot,
    EvidenceProjection,
    ModelEmissionReceipt,
    Presence,
    ReportItemProjection,
    ReportLane,
    ReportReadSnapshot,
    ReportRecordSnapshot,
    RestoreAction,
    StoredAxisProjection,
    TranscriptSegmentProjection,
    canonical_json_bytes,
    sha256_bytes,
)

AXES = ("correctness", "depth", "fundamentals", "ownership", "communication")
NOTICE_DIGEST = sha256_bytes("인용한 답변을 확인할 수 없어 점수를 보류했습니다.".encode())
TEXT_DIGEST = sha256_bytes(b"synthetic fixture rationale")
OTHER_POSITIONS_DIGEST = "f" * 64
INDICATORS = {None, "score_null", "average_null", "state", "playable"}


def _uid(*parts: object) -> UUID:
    return uuid5(NAMESPACE_URL, "fake-spec004:" + ":".join(str(part) for part in parts))


def _digest(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


class FakeSpec004Adapters:
    def __init__(
        self,
        *,
        citation_storage: str = "VERIFY",
        emission_overrides: dict[str, list[str]] | None = None,
        emissions_available: bool = True,
        removal_indicator: str | None = None,
        removal_effective: bool = True,
        removal_breaks_report: bool = False,
        restore_mismatch: bool = False,
        probe_restore_fails: bool = False,
        refuse_lanes: frozenset[str] = frozenset(),
        second_version_binding_wrong: bool = False,
        stored_overall_offset: int = 0,
        api_overall_offset: int = 0,
        report_mutates_after_change: bool = False,
        scoring_source_drift: bool = False,
        other_positions_changed: bool = False,
        teardown_fails: bool = False,
        records_unavailable: frozenset[str] = frozenset(),
    ) -> None:
        if removal_indicator not in INDICATORS:
            raise ValueError(f"unknown removal indicator {removal_indicator}")
        self.citation_storage = citation_storage
        self.emission_overrides = emission_overrides or {}
        self.emissions_available = emissions_available
        self.removal_indicator = removal_indicator
        self.removal_effective = removal_effective
        self.removal_breaks_report = removal_breaks_report
        self.restore_mismatch = restore_mismatch
        self.probe_restore_fails = probe_restore_fails
        self.refuse_lanes = refuse_lanes
        self.second_version_binding_wrong = second_version_binding_wrong
        self.stored_overall_offset = stored_overall_offset
        self.api_overall_offset = api_overall_offset
        self.report_mutates_after_change = report_mutates_after_change
        self.scoring_source_drift = scoring_source_drift
        self.other_positions_changed = other_positions_changed
        self.teardown_fails = teardown_fails
        self.records_unavailable = records_unavailable
        self.now = datetime(2026, 10, 7, 9, 0, tzinfo=UTC)
        self.lanes: dict[str, ReportLane] = {}
        self.positions: set[str] = set()
        self.reports: dict[str, dict[str, Any]] = {}
        self.segments: dict[str, dict[str, Any]] = {}
        self.present_segments: set[str] = set()
        self.emissions: list[ModelEmissionReceipt] = []
        self.versions: dict[str, dict[str, Any]] = {}
        self.committed: set[str] = set()
        self.injections: dict[str, dict[str, Any]] = {}
        self.calls: list[str] = []
        self.torn_down = False

    # --- seed -------------------------------------------------------------------------------------

    def seed_position(self, *, run_id: str, position_id: str) -> AdapterResult:
        self.calls.append(f"seed_position:{position_id}")
        self.positions.add(position_id)
        return AdapterResult(True, "POSITION_SEEDED", {"position_id": position_id})

    def seed_lanes(self, *, run_id: str, lanes: tuple[ReportLane, ...]) -> AdapterResult:
        digests = {}
        for lane in lanes:
            key = lane.lane_id.value
            self.calls.append(f"seed:{key}")
            self.lanes[key] = lane
            for criterion in lane.criteria:
                segment_id = str(criterion.transcript_segment_id)
                self.segments[segment_id] = {
                    "lane_id": key,
                    "transcript_segment_id": segment_id,
                    "turn_id": str(criterion.answer_turn_id),
                    "version": 1,
                    "session_start_ms": 1000,
                    "session_end_ms": 9000,
                    "text_sha256": TEXT_DIGEST,
                    "text_length": 24,
                }
                self.present_segments.add(segment_id)
            digests[key] = lane.fixture_digest
        return AdapterResult(True, "LANES_SEEDED", {"fixture_digests": digests})

    def teardown(self, *, run_id: str, lanes, position_ids) -> AdapterResult:
        self.calls.append("teardown")
        if self.teardown_fails:
            return AdapterResult(False, "SPEC004_TEARDOWN_FAILED")
        self.torn_down = True
        return AdapterResult(
            True,
            "SPEC004_TEARDOWN_COMPLETE",
            {"remaining_run_rows": 0, "other_positions_digest": self._other_positions()},
        )

    # --- consent (same protocol as N-02) ----------------------------------------------------------

    def read_policy(self, *, subject):
        return ConsentPolicySnapshot(
            policy_version="fixture-v1",
            content_digest="d" * 64,
            required_purposes=tuple(ConsentPurpose),
            retention_days=365,
            received_at=self.now,
            request_id=uuid4(),
            source_ref="fixture:policy",
        )

    def commit(self, *, subject, policy, request_id: str, trace_id: str):
        self.committed.add(str(subject["subject_ref"]))
        return AdapterResult(
            True, "CONSENT_COMMIT_RESPONSE_RECEIVED", {"status_code": 201, "request_id": request_id}
        )

    def read_state(self, *, subject, phase: str, step_id: str):
        return AdapterResult(False, "NOT_USED_BY_SPEC004")

    # --- report requests ---------------------------------------------------------------------------

    def request_report(self, *, lane: ReportLane) -> AdapterResult:
        key = lane.lane_id.value
        self.calls.append(f"request:{key}")
        event_id = str(_uid(key, "report-event"))
        if key in self.refuse_lanes or lane.subject_ref not in self.committed:
            self.reports.pop(key, None)
            return AdapterResult(True, "REPORT_REQUESTED", {"event_id": event_id})
        self.lanes[key] = lane
        self._generate(lane)
        return AdapterResult(True, "REPORT_REQUESTED", {"event_id": event_id})

    def read_processing(self, *, lane: ReportLane) -> AdapterResult:
        key = lane.lane_id.value
        if key in self.reports:
            receipts = ["REPORT_HANDLER_ENTERED", "REPORT_ASSESSMENT_STARTED"]
        else:
            receipts = ["REPORT_HANDLER_ENTERED", "REPORT_ASSESSMENT_REFUSED"]
        return AdapterResult(
            True, "PROCESSING_READ", {"report_present": key in self.reports, "receipts": receipts}
        )

    def _version_for(self, lane: ReportLane) -> dict[str, Any] | None:
        return self.versions.get(str(lane.competency_model_version_id))

    def _generate(self, lane: ReportLane) -> None:
        key = lane.lane_id.value
        version = self._version_for(lane)
        axis_weights = dict(version["body"].get("axis_weights") or {}) if version else {}
        evidence_by_criterion = {
            str(item.criterion_id): str(_uid(key, item.criterion_id, "evidence"))
            for item in lane.criteria
        }
        items = []
        for criterion in lane.criteria:
            criterion_id = str(criterion.criterion_id)
            own = evidence_by_criterion[criterion_id]
            mode = criterion.citation_mode or CitationMode.VALID
            if mode is CitationMode.VALID:
                emitted = [own]
            elif mode is CitationMode.EMPTY:
                emitted = []
            elif mode is CitationMode.OTHER_CRITERION:
                emitted = [evidence_by_criterion[str(criterion.mode_argument)]]
            else:
                emitted = [str(criterion.mode_argument)]
            emitted = self.emission_overrides.get(mode.value, emitted)
            score = 72 if criterion.fixture_score is None else criterion.fixture_score
            self.emissions.append(
                ModelEmissionReceipt(
                    schema_version="controlproof.spec004-model-emission.v1",
                    receipt_id=_uid(key, criterion_id, "receipt"),
                    fixture_id="spec004-report-v1",
                    criterion_id=criterion.criterion_id,
                    mode=mode.value,
                    provided_evidence_ids=(UUID(own),),
                    emitted_quoted_ids=tuple(UUID(value) for value in emitted),
                    emitted_score=score,
                    mode_status="EMITTED",
                    emitted_at=self.now,
                )
            )
            verified = bool(emitted) and set(emitted) <= {own}
            keep = verified or self.citation_storage == "STORE_AS_EMITTED"
            axes = [
                {
                    "axis": axis,
                    "score": score if keep else None,
                    "quoted": list(emitted) if keep else [],
                    "notice": not keep,
                }
                for axis in AXES
            ]
            items.append(
                {
                    "report_item_id": str(_uid(key, criterion_id, "item")),
                    "criterion_id": criterion_id,
                    "competency_model_version_id": str(lane.competency_model_version_id),
                    "criterion_weight": criterion.weight,
                    "axis_weights": axis_weights,
                    "axes": axes,
                    "evidence": [
                        {
                            "evidence_id": own,
                            "answer_turn_id": str(criterion.answer_turn_id),
                            "transcript_segment_id": str(criterion.transcript_segment_id),
                            "video_start_ms": 1000,
                            "video_end_ms": 9000,
                        }
                    ],
                }
            )
        self.reports[key] = {
            "report_id": str(_uid(key, "report")),
            "config_version": COMMUNICATION_SEPARATED_CONFIG_VERSION,
            "items": items,
            "probe_axes": {},
        }
        self._freeze_scores(key)

    def _score_items(self, key: str) -> list[dict[str, Any]]:
        report = self.reports[key]
        return [
            {
                "criterion_id": item["criterion_id"],
                "criterion_weight": item["criterion_weight"],
                "axis_weights": item["axis_weights"],
                "axes": [(axis["axis"], axis["score"]) for axis in self._axes(key, item)],
            }
            for item in report["items"]
        ]

    def _freeze_scores(self, key: str) -> None:
        report = self.reports[key]
        aggregate = report_aggregate(self._score_items(key), report["config_version"])
        communication = communication_aggregate(self._score_items(key))
        report["overall_score"] = (
            None if aggregate.score is None else aggregate.score + self.stored_overall_offset
        )
        report["scoring_inputs"] = {
            "criteria": [
                {
                    "criterion_id": item.key,
                    "score": item.score,
                    "weight": item.weight,
                    "normalized_weight": item.normalized_weight,
                    "contribution": item.contribution,
                }
                for item in aggregate.contributions
            ],
            "excluded": [
                {
                    "criterion_id": item.key,
                    "weight": item.weight,
                    "normalized_weight": item.normalized_weight,
                }
                for item in aggregate.exclusions
            ],
            "numerator": aggregate.numerator,
            "denominator": aggregate.denominator,
            "axis_weights": {
                item["criterion_id"]: dict(item["axis_weights"])
                for item in report["items"]
                if item["axis_weights"]
            },
            "communication": {
                "score": communication.score,
                "numerator": communication.numerator,
                "denominator": communication.denominator,
                "scored_criteria": [item.key for item in communication.contributions],
                "unscored_criteria": [item.key for item in communication.exclusions],
            },
        }

    def _axes(self, key: str, item: dict[str, Any]) -> list[dict[str, Any]]:
        return self.reports[key]["probe_axes"].get(item["report_item_id"], item["axes"])

    # --- records and reads ---------------------------------------------------------------------------

    def read_records(self, *, lane: ReportLane, phase: str):
        key = lane.lane_id.value
        if key in self.records_unavailable:
            return ReportRecordSnapshot(
                run_id=lane.run_id,
                lane_id=lane.lane_id,
                subject_ref=lane.subject_ref,
                phase=phase,
                report_id=None,
                source_status=Presence.UNAVAILABLE,
                source_error_code="DB_TIMEOUT",
                state_digest="e" * 64,
            )
        report = self.reports.get(key)
        if report is None:
            return ReportRecordSnapshot(
                run_id=lane.run_id,
                lane_id=lane.lane_id,
                subject_ref=lane.subject_ref,
                phase=phase,
                report_id=None,
                source_status=Presence.ABSENT,
                state_digest=_digest({"lane": key, "report": None}),
            )
        items = tuple(
            ReportItemProjection(
                report_item_id=item["report_item_id"],
                criterion_id=item["criterion_id"],
                competency_model_version_id=item["competency_model_version_id"],
                assessment_state="confirmed",
                criterion_weight=item["criterion_weight"],
                axis_weights=item["axis_weights"],
                axes=tuple(
                    StoredAxisProjection(
                        axis=axis["axis"],
                        score=axis["score"],
                        quoted_evidence_ids=tuple(UUID(value) for value in axis["quoted"]),
                        rationale_sha256=NOTICE_DIGEST if axis["notice"] else TEXT_DIGEST,
                        rationale_is_unverified_notice=axis["notice"],
                    )
                    for axis in self._axes(key, item)
                ),
                observation_sha256=TEXT_DIGEST,
                rationale_sha256=TEXT_DIGEST,
                uncertainty_sha256=TEXT_DIGEST,
            )
            for item in report["items"]
        )
        evidence = tuple(
            EvidenceProjection(
                evidence_id=value["evidence_id"],
                report_item_id=item["report_item_id"],
                criterion_id=item["criterion_id"],
                competency_model_version_id=item["competency_model_version_id"],
                answer_turn_id=value["answer_turn_id"],
                transcript_segment_id=value["transcript_segment_id"],
                video_start_ms=value["video_start_ms"],
                video_end_ms=value["video_end_ms"],
                sufficiency="direct",
                observation_sha256=TEXT_DIGEST,
                rationale_sha256=TEXT_DIGEST,
            )
            for item in report["items"]
            for value in item["evidence"]
        )
        segments = tuple(
            TranscriptSegmentProjection(
                **{
                    name: row[name]
                    for name in (
                        "transcript_segment_id",
                        "turn_id",
                        "version",
                        "session_start_ms",
                        "session_end_ms",
                        "text_sha256",
                        "text_length",
                    )
                },
                row_digest=_digest(row),
            )
            for segment_id, row in sorted(self.segments.items())
            if row["lane_id"] == key and segment_id in self.present_segments
        )
        body = {
            "report_id": report["report_id"],
            "overall_score": report["overall_score"],
            "scoring_inputs": report["scoring_inputs"],
            "items": [item.model_dump(mode="json") for item in items],
            "evidence": [item.model_dump(mode="json") for item in evidence],
            "segments": [item.model_dump(mode="json") for item in segments],
        }
        return ReportRecordSnapshot(
            run_id=lane.run_id,
            lane_id=lane.lane_id,
            subject_ref=lane.subject_ref,
            phase=phase,
            report_id=report["report_id"],
            report_version=1,
            model_version="bedrock-model-v1",
            prompt_version="assessment-prompt-v2",
            config_version=report["config_version"],
            status="ready",
            summary_sha256=TEXT_DIGEST,
            summary_length=24,
            overall_score=report["overall_score"],
            scoring_inputs=report["scoring_inputs"],
            items=items,
            evidence=evidence,
            transcript_segments=segments,
            source_status=Presence.PRESENT,
            state_digest=_digest(body),
        )

    def read_api(self, *, lane: ReportLane, phase: str, include_timeline: bool = False):
        key = lane.lane_id.value
        report = self.reports.get(key)
        request_id = _uid(key, phase, "read", len(self.calls))
        self.calls.append(f"read:{key}:{phase}")
        if report is None:
            body = {"status": "queued"}
            return ReportReadSnapshot(
                phase=phase,
                request_id=request_id,
                status_code=202,
                report=body,
                read_digest=_digest(body),
            )
        missing = {
            segment_id
            for segment_id, row in self.segments.items()
            if row["lane_id"] == key and segment_id not in self.present_segments
        }
        if missing and self.removal_breaks_report:
            return ReportReadSnapshot(
                phase=phase,
                request_id=request_id,
                status_code=500,
                read_digest=_digest({"status": 500}),
            )
        items = []
        for item in report["items"]:
            removed = any(value["transcript_segment_id"] in missing for value in item["evidence"])
            axes = [
                axis
                for axis in self._axes(key, item)
                if not (axis["score"] is not None and not axis["quoted"])  # WhyYou _restored_axes
            ]
            if removed and self.removal_indicator == "score_null":
                axes = [axis | {"score": None} for axis in axes]
            pairs = [(axis["axis"], axis["score"]) for axis in axes]
            average = criterion_aggregate(
                pairs, item["axis_weights"], report["config_version"]
            ).score
            if removed and self.removal_indicator == "average_null":
                average = None
            state = "confirmed"
            if removed and self.removal_indicator == "state":
                state = "insufficient_evidence"
            evidence = []
            for value in item["evidence"]:
                entry = {
                    name: value[name]
                    for name in (
                        "evidence_id",
                        "answer_turn_id",
                        "transcript_segment_id",
                        "video_start_ms",
                        "video_end_ms",
                    )
                } | {"sufficiency": "direct"}
                if self.removal_indicator == "playable":
                    entry["playable"] = value["transcript_segment_id"] not in missing
                evidence.append(entry)
            items.append(
                {
                    "report_item_id": item["report_item_id"],
                    "criterion_id": item["criterion_id"],
                    "assessment_state": state,
                    "average_score": average,
                    "criterion_weight": item["criterion_weight"],
                    "axis_assessments": [
                        {
                            "axis": axis["axis"],
                            "score": axis["score"],
                            "quoted_evidence_ids": list(axis["quoted"]),
                            "weight": item["axis_weights"].get(axis["axis"]),
                        }
                        for axis in axes
                    ],
                    "evidence": evidence,
                }
            )
        aggregate = report_aggregate(self._score_items(key), report["config_version"])
        communication = communication_aggregate(self._score_items(key))
        body = {
            "report_id": report["report_id"],
            "status": "ready",
            "overall_score": None
            if aggregate.score is None
            else aggregate.score + self.api_overall_offset,
            "communication_score": communication.score,
            "scoring_breakdown": {
                "numerator": aggregate.numerator,
                "denominator": aggregate.denominator,
                "contributions": [
                    {
                        "key": item.key,
                        "score": item.score,
                        "weight": item.weight,
                        "normalized_weight": item.normalized_weight,
                        "contribution": item.contribution,
                    }
                    for item in aggregate.contributions
                ],
                "exclusions": [
                    {
                        "key": item.key,
                        "weight": item.weight,
                        "normalized_weight": item.normalized_weight,
                    }
                    for item in aggregate.exclusions
                ],
            },
            "items": items,
        }
        timeline = None
        if include_timeline:
            timeline = {
                "entries": [
                    {
                        "entry_id": segment_id,
                        "entry_type": "transcript",
                        "text_sha256": row["text_sha256"],
                    }
                    for segment_id, row in sorted(self.segments.items())
                    if row["lane_id"] == key and segment_id in self.present_segments
                ]
            }
        return ReportReadSnapshot(
            phase=phase,
            request_id=request_id,
            status_code=200,
            report=body,
            timeline=timeline,
            unknown_fields=(),
            read_digest=_digest({"report": body, "timeline": timeline}),
        )

    # --- change injections ----------------------------------------------------------------------------

    def _segment_row_digest(self, segment_id: str) -> str:
        return _digest(self.segments[segment_id])

    def remove_segment(self, *, lane: ReportLane, transcript_segment_id: str, injection_id: str):
        row = self.segments.get(transcript_segment_id)
        if row is None or row["lane_id"] != lane.lane_id.value:
            return AdapterResult(False, "SEGMENT_NOT_OWNED_BY_LANE")
        pre = self._segment_row_digest(transcript_segment_id)
        if self.removal_effective:
            self.present_segments.discard(transcript_segment_id)
        self.injections[injection_id] = {"lane": lane, "segment": transcript_segment_id, "pre": pre}
        return ChangeInjection(
            injection_id=injection_id,
            kind=ChangeInjectionKind.EVIDENCE_SEGMENT_REMOVAL,
            run_id=lane.run_id,
            lane_id=lane.lane_id,
            subject_ref=lane.subject_ref,
            target_table="transcript_segments",
            target_ids=(UUID(transcript_segment_id),),
            pre_projection_digest=pre,
            applied_at=self.now,
            apply_receipt={
                "affected_rows": 1 if self.removal_effective else 0,
                "absence_confirmed": self.removal_effective,
            },
            restore_action=RestoreAction.REINSERT,
            state=ChangeInjectionState.APPLIED,
        )

    def restore_segment(self, *, injection: ChangeInjection):
        record = self.injections[str(injection.injection_id)]
        self.present_segments.add(record["segment"])
        post = "9" * 64 if self.restore_mismatch else self._segment_row_digest(record["segment"])
        if post != injection.pre_projection_digest:
            return injection.model_copy(
                update={
                    "state": ChangeInjectionState.RESTORE_FAILED,
                    "failure_code": "RESTORE_DIGEST_MISMATCH",
                    "post_restore_digest": post,
                }
            )
        return injection.model_copy(
            update={
                "state": ChangeInjectionState.RESTORED,
                "restored_at": self.now + timedelta(seconds=1),
                "post_restore_digest": post,
            }
        )

    def write_probe_axes(self, *, lane: ReportLane, report_item_id: str, axes, injection_id: str):
        key = lane.lane_id.value
        report = self.reports[key]
        item = next(item for item in report["items"] if item["report_item_id"] == report_item_id)
        pre = _digest(item["axes"])
        report["probe_axes"][report_item_id] = [
            {
                "axis": axis["axis"],
                "score": axis["score"],
                "quoted": list(axis["quoted_evidence_ids"]),
                "notice": False,
            }
            for axis in axes
        ]
        self.injections[injection_id] = {"lane": lane, "item": report_item_id, "pre": pre}
        return ChangeInjection(
            injection_id=injection_id,
            kind=ChangeInjectionKind.STORAGE_PROBE_WRITE,
            run_id=lane.run_id,
            lane_id=lane.lane_id,
            subject_ref=lane.subject_ref,
            target_table="report_items",
            target_ids=(UUID(report_item_id),),
            pre_projection_digest=pre,
            applied_at=self.now,
            apply_receipt={"affected_rows": 1},
            restore_action=RestoreAction.REWRITE,
            state=ChangeInjectionState.APPLIED,
        )

    def restore_probe_axes(self, *, injection: ChangeInjection):
        record = self.injections[str(injection.injection_id)]
        report = self.reports[record["lane"].lane_id.value]
        if self.probe_restore_fails:
            return injection.model_copy(
                update={
                    "state": ChangeInjectionState.RESTORE_FAILED,
                    "failure_code": "PROBE_RESTORE_FAILED",
                }
            )
        report["probe_axes"].pop(record["item"], None)
        item = next(item for item in report["items"] if item["report_item_id"] == record["item"])
        return injection.model_copy(
            update={
                "state": ChangeInjectionState.RESTORED,
                "restored_at": self.now + timedelta(seconds=1),
                "post_restore_digest": _digest(item["axes"]),
            }
        )

    # --- criteria versions -----------------------------------------------------------------------------

    def create_version(self, *, position_id: str, body, idempotency_key: str) -> AdapterResult:
        number = 1 + sum(
            1 for version in self.versions.values() if version["position_id"] == position_id
        )
        version_id = str(_uid(position_id, "version", number))
        self.versions[version_id] = {
            "position_id": position_id,
            "version_number": number,
            "row_version": 1,
            "status": "draft",
            "published_at": None,
            "body": dict(body),
        }
        return AdapterResult(
            True,
            "VERSION_CREATED",
            {"version_id": version_id, "row_version": 1, "version_number": number},
        )

    def publish_version(
        self, *, version_id: str, row_version: int, idempotency_key: str
    ) -> AdapterResult:
        version = self.versions[version_id]
        if version["row_version"] != row_version or version["status"] != "draft":
            return AdapterResult(False, "VERSION_PUBLISH_CONFLICT", {"status_code": 409})
        version.update(status="published", row_version=2, published_at=self.now)
        if self.report_mutates_after_change and version["version_number"] > 1:
            for key, report in self.reports.items():
                for item in report["items"]:
                    item["criterion_weight"] = 100.0 - item["criterion_weight"]
                self._freeze_scores(key)
        return AdapterResult(
            True, "VERSION_PUBLISHED", {"version_id": version_id, "row_version": 2}
        )

    def criterion_id(self, version_id: str, code: str) -> str:
        return str(_uid(version_id, "criterion", code))

    def latest_published(self, *, position_id: str, snapshot_phase: str):
        published = [
            (version_id, version)
            for version_id, version in self.versions.items()
            if version["position_id"] == position_id and version["status"] == "published"
        ]
        if not published:
            return AdapterResult(False, "NO_PUBLISHED_VERSION")
        published.sort(key=lambda pair: pair[1]["version_number"])
        version_id, version = published[0] if self.second_version_binding_wrong else published[-1]
        return CriteriaVersionSnapshot(
            position_id=position_id,
            competency_model_version_id=version_id,
            version_number=version["version_number"],
            row_version=version["row_version"],
            status=version["status"],
            published_at=version["published_at"],
            criteria=tuple(
                {
                    "criterion_id": self.criterion_id(version_id, criterion["code"]),
                    "code": criterion["code"],
                    "weight": criterion["weight"],
                }
                for criterion in version["body"]["criteria"]
            ),
            axis_weights=dict(version["body"].get("axis_weights") or {}),
            request_ids=(_uid(version_id, "request"),),
            snapshot_phase=snapshot_phase,
            other_positions_digest=self._other_positions(),
        )

    def _other_positions(self) -> str:
        published_v2 = any(version["version_number"] > 1 for version in self.versions.values())
        return "0" * 64 if self.other_positions_changed and published_v2 else OTHER_POSITIONS_DIGEST

    def other_positions_digest(self, *, excluded_position_ids) -> AdapterResult:
        return AdapterResult(True, "OTHER_POSITIONS_READ", {"digest": self._other_positions()})

    # --- emissions and scoring source ----------------------------------------------------------------

    def read_emissions(self, *, criterion_ids):
        if not self.emissions_available:
            return AdapterResult(False, "EMISSION_RECEIPTS_UNAVAILABLE")
        wanted = {str(value) for value in criterion_ids}
        return tuple(receipt for receipt in self.emissions if str(receipt.criterion_id) in wanted)

    def read_blob_shas(self) -> AdapterResult:
        shas = {source["path"]: source["blob_sha"] for source in PINNED_SOURCES}
        if self.scoring_source_drift:
            first = PINNED_SOURCES[0]["path"]
            shas[first] = hashlib.sha1(b"drifted").hexdigest()
        return AdapterResult(True, "BLOB_SHAS_READ", {"blob_shas": shas})
