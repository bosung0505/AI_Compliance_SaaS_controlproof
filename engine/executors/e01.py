"""E-01 executor: citation matrix, evidence removal and storage probe (T040, T048).

Order (scenarios/E-01.yaml): seed REFERENCE/REMOVAL/PROBE lanes → consent → request → stable reference
report → seed the matrix with the reference report's Evidence ID → consent → request → stable matrix
report + emission receipts → remove one Run-owned transcript segment → POST_REMOVAL read → restore →
POST_RESTORE reads → storage probe write → POST_PROBE read → probe restore → reference recapture →
teardown.

Restores and teardown are always-run: they execute after an adapter exception, after the Run deadline
and before a cancellation propagates. Only restore and teardown work counts against the restore budget
(ID-003-19). E01-D1 is written to `storage-probe.json` and never becomes an assertion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from engine.adapters.base import AdapterResult
from engine.executors.report_lanes import (
    PRECONDITION_NOT_MET,
    Spec004LaneExecutor,
    unassessed,
)
from engine.judges.e01 import (
    build_citation_cases,
    judge_e01_citations,
    judge_e01_removal,
    judge_e01_restore,
    storage_probe_exposure,
)
from engine.models import (
    E01_ASSERTIONS,
    ChangeInjection,
    ChangeInjectionState,
    E01LaneId,
    ExecutionProfile,
    ModelEmissionReceipt,
    Presence,
    ReportLane,
    ReportPhase,
    ReportReadSnapshot,
    ReportRecordSnapshot,
)
from seeds.spec004_subjects import e01_lanes, e01_matrix_lane, nonexistent_evidence_id

PROBE_RATIONALE = "controlproof storage probe"


@dataclass
class _Journey:
    steps: list[dict[str, Any]] = field(default_factory=list)
    records: list[dict[str, Any]] = field(default_factory=list)
    reads: list[dict[str, Any]] = field(default_factory=list)
    seeded: list[ReportLane] = field(default_factory=list)
    lanes: dict[E01LaneId, ReportLane] = field(default_factory=dict)
    receipts: tuple[ModelEmissionReceipt, ...] = ()
    cases: tuple = ()
    emission_problem: str | None = None
    reference_before: ReportRecordSnapshot | None = None
    reference_after: ReportRecordSnapshot | None = None
    reference_evidence: UUID | None = None
    matrix_record: ReportRecordSnapshot | None = None
    removal: ChangeInjection | AdapterResult | None = None
    removal_pre_read: ReportReadSnapshot | None = None
    removal_post_read: ReportReadSnapshot | None = None
    removal_restored_read: ReportReadSnapshot | None = None
    removal_pre_record: ReportRecordSnapshot | None = None
    removal_restored_record: ReportRecordSnapshot | None = None
    probe: ChangeInjection | AdapterResult | None = None
    probe_document: dict[str, Any] = field(
        default_factory=lambda: {
            "diagnostic_id": "E01-D1",
            "status": "NOT_RUN",
            "exposure": [],
        }
    )
    teardown: AdapterResult | None = None


class E01Executor(Spec004LaneExecutor):
    profile = ExecutionProfile.E01_CITATION_EVIDENCE_V1
    assertion_ids = tuple(E01_ASSERTIONS)
    block_subject = "e01-citation-evidence"

    # --- step helpers --------------------------------------------------------------------------

    def _in_time(self, journey: _Journey, step: str) -> bool:
        if self.clock.now() < self._deadline:
            return True
        journey.steps.append({"step": step, "skipped": "RUN_DEADLINE"})
        return False

    def _guarded(self, journey: _Journey, step: str, action) -> None:
        """Adapter exceptions become step facts; cancellation still propagates."""
        try:
            action(journey)
        except Exception as exc:  # noqa: BLE001 - a failed step is evidence, not a crash
            journey.steps.append({"step": step, "error": type(exc).__name__})

    def _start_lane(self, lane: ReportLane, journey: _Journey) -> None:
        consent = self.commit_consent(lane)
        journey.steps.append(
            {"step": "consent", "lane_id": lane.lane_id.value, "code": consent.code}
        )
        request = self.adapters.spec004_requests.request_report(lane=lane)
        journey.steps.append(
            {"step": "request", "lane_id": lane.lane_id.value, "code": request.code}
        )

    def _record(self, journey: _Journey, value: ReportRecordSnapshot, step: str) -> None:
        journey.records.append(value.model_dump(mode="json") | {"step": step})

    def _read(self, journey: _Journey, lane: ReportLane, phase: str) -> ReportReadSnapshot | None:
        value = self.adapters.spec004_records.read_api(
            lane=lane, phase=phase, include_timeline=True
        )
        if isinstance(value, AdapterResult):
            journey.steps.append({"step": f"read:{phase}", "code": value.code})
            return None
        journey.reads.append(value.model_dump(mode="json") | {"lane_id": lane.lane_id.value})
        return value

    # --- journey -------------------------------------------------------------------------------

    def _journey(self, run_id: UUID) -> dict[str, Any]:
        journey = _Journey()
        try:
            self._guarded(journey, "citation", lambda state: self._citation(run_id, state))
            if E01LaneId.E01_EVIDENCE_REMOVAL in journey.lanes:
                self._guarded(journey, "removal", self._removal)
            self._restore_removal(journey)
            if E01LaneId.E01_STORAGE_PROBE in journey.lanes:
                self._guarded(journey, "storage-probe", lambda state: self._probe(run_id, state))
            self._restore_probe(journey)
            reference = journey.lanes.get(E01LaneId.E01_REFERENCE)
            if reference is not None and self._in_time(journey, "recapture-reference-report"):
                self._guarded(journey, "recapture-reference-report", self._recapture)
        finally:
            self._restore_removal(journey)
            self._restore_probe(journey)
            journey.teardown = (
                self.restore_operation(
                    self.adapters.spec004_seed.teardown,
                    run_id=str(run_id),
                    lanes=tuple(journey.seeded),
                    position_ids=(),
                )
                if journey.seeded
                else AdapterResult(True, "SPEC004_NOTHING_SEEDED")
            )
            journey.steps.append({"step": "teardown", "code": journey.teardown.code})
        return self._outcome(journey)

    def _citation(self, run_id: UUID, journey: _Journey) -> None:
        seed = self.adapters.spec004_seed
        initial = e01_lanes(run_id)
        result = seed.seed_lanes(run_id=str(run_id), lanes=initial)
        journey.steps.append({"step": "seed-report-lanes", "code": result.code})
        if not result.ok:
            return
        journey.seeded.extend(initial)
        journey.lanes.update({lane.lane_id: lane for lane in initial})
        for lane in initial:
            self._start_lane(lane, journey)
        reference = journey.lanes[E01LaneId.E01_REFERENCE]
        journey.reference_before = self.wait_for_report(reference, ReportPhase.GENERATED.value)
        self._record(journey, journey.reference_before, "capture-reference-report")
        before = journey.reference_before
        if before.source_status is not Presence.PRESENT or not before.evidence:
            return
        journey.reference_evidence = before.evidence[0].evidence_id
        matrix = e01_matrix_lane(run_id, journey.reference_evidence)
        result = seed.seed_lanes(run_id=str(run_id), lanes=(matrix,))
        journey.steps.append({"step": "seed-citation-matrix", "code": result.code})
        if not result.ok:
            return
        journey.seeded.append(matrix)
        journey.lanes[matrix.lane_id] = matrix
        self._start_lane(matrix, journey)
        journey.matrix_record = self.wait_for_report(matrix, ReportPhase.GENERATED.value)
        self._record(journey, journey.matrix_record, "request-matrix-report")
        emitted = self.adapters.spec004_emissions.read_emissions(
            criterion_ids=tuple(str(item.criterion_id) for item in matrix.criteria)
        )
        if isinstance(emitted, AdapterResult):
            journey.emission_problem = emitted.code
        else:
            journey.receipts = tuple(emitted)
        journey.cases = build_citation_cases(
            lane=matrix, record=journey.matrix_record, receipts=journey.receipts
        )

    def _removal(self, journey: _Journey) -> None:
        lane = journey.lanes[E01LaneId.E01_EVIDENCE_REMOVAL]
        generated = self.wait_for_report(lane, ReportPhase.GENERATED.value)
        if generated.source_status is not Presence.PRESENT:
            journey.removal = AdapterResult(False, "REMOVAL_REPORT_ABSENT")
            return
        if not self._in_time(journey, "capture-removal-baseline"):
            return
        records = self.adapters.spec004_records
        journey.removal_pre_record = records.read_records(
            lane=lane, phase=ReportPhase.PRE_REMOVAL.value
        )
        self._record(journey, journey.removal_pre_record, "capture-removal-baseline")
        journey.removal_pre_read = self._read(journey, lane, ReportPhase.PRE_REMOVAL.value)
        segment = str(lane.criteria[0].transcript_segment_id)
        journey.removal = self.adapters.spec004_mutation.remove_segment(
            lane=lane, transcript_segment_id=segment, injection_id=str(uuid4())
        )
        journey.steps.append(
            {
                "step": "apply-evidence-removal",
                "code": getattr(journey.removal, "code", "EVIDENCE_SEGMENT_REMOVED"),
            }
        )
        if not isinstance(journey.removal, ChangeInjection):
            return
        if self._in_time(journey, "capture-post-removal"):
            self.clock.sleep(self.scenario.timing_policy.poll_seconds)
            journey.removal_post_read = self._read(journey, lane, ReportPhase.POST_REMOVAL.value)

    def _restore_removal(self, journey: _Journey) -> None:
        injection = journey.removal
        if not isinstance(injection, ChangeInjection) or (
            injection.state is not ChangeInjectionState.APPLIED
        ):
            return
        try:
            journey.removal = self.restore_operation(
                self.adapters.spec004_mutation.restore_segment, injection=injection
            )
        except Exception as exc:  # noqa: BLE001 - restore uncertainty is RESTORE_FAILED
            journey.removal = injection.model_copy(
                update={
                    "state": ChangeInjectionState.RESTORE_FAILED,
                    "failure_code": f"RESTORE_RAISED:{type(exc).__name__}",
                }
            )
        journey.steps.append({"step": "restore-evidence-removal", "state": journey.removal.state})
        lane = journey.lanes[E01LaneId.E01_EVIDENCE_REMOVAL]

        def verify(state: _Journey) -> None:
            state.removal_restored_record = self.adapters.spec004_records.read_records(
                lane=lane, phase=ReportPhase.POST_RESTORE.value
            )
            self._record(state, state.removal_restored_record, "verify-removal-restored")
            if self._in_time(state, "capture-post-restore"):
                state.removal_restored_read = self._read(
                    state, lane, ReportPhase.POST_RESTORE.value
                )

        self._guarded(journey, "verify-removal-restored", verify)

    def _probe(self, run_id: UUID, journey: _Journey) -> None:
        lane = journey.lanes[E01LaneId.E01_STORAGE_PROBE]
        generated = self.wait_for_report(lane, ReportPhase.GENERATED.value)
        if generated.source_status is not Presence.PRESENT or not generated.items:
            journey.probe_document["detail"] = f"{PRECONDITION_NOT_MET}: probe report absent"
            return
        if not self._in_time(journey, "capture-probe-baseline"):
            return
        before = self.adapters.spec004_records.read_records(
            lane=lane, phase=ReportPhase.PRE_PROBE.value
        )
        self._record(journey, before, "capture-probe-baseline")
        # Use seed identity, not database/API ordering. All four modes must have
        # verified prerequisites before the first probe write.
        owned = (
            before.source_status is Presence.PRESENT
            and before.run_id == lane.run_id
            and before.lane_id == lane.lane_id
            and before.subject_ref == lane.subject_ref
            and before.report_id == generated.report_id
            and len(lane.criteria) == 2
        )
        target = donor = evidence = None
        if owned:
            target = next(
                (
                    item
                    for item in before.items
                    if item.criterion_id == lane.criteria[0].criterion_id
                    and item.competency_model_version_id == lane.competency_model_version_id
                ),
                None,
            )
            donor = next(
                (
                    item
                    for item in before.items
                    if item.criterion_id == lane.criteria[1].criterion_id
                    and item.competency_model_version_id == lane.competency_model_version_id
                ),
                None,
            )
        if (
            target is not None
            and donor is not None
            and target.report_item_id != donor.report_item_id
        ):
            criterion = lane.criteria[1]
            evidence = next(
                (
                    row
                    for row in before.evidence
                    if row.report_item_id == donor.report_item_id
                    and row.criterion_id == donor.criterion_id
                    and row.competency_model_version_id == donor.competency_model_version_id
                    and row.answer_turn_id == criterion.answer_turn_id
                    and row.transcript_segment_id == criterion.transcript_segment_id
                    and any(
                        segment.transcript_segment_id == row.transcript_segment_id
                        and segment.turn_id == row.answer_turn_id
                        for segment in before.transcript_segments
                    )
                    and any(
                        axis.score is not None and row.evidence_id in axis.quoted_evidence_ids
                        for axis in donor.axes
                    )
                ),
                None,
            )
        if target is None or evidence is None or journey.reference_evidence is None:
            journey.probe_document["detail"] = (
                f"{PRECONDITION_NOT_MET}: PROBE_PREREQUISITE_UNVERIFIED"
            )
            return
        item_id = str(target.report_item_id)
        written = [
            {"mode": "EMPTY", "axis": "correctness", "quoted_evidence_ids": []},
            {
                "mode": "NONEXISTENT",
                "axis": "depth",
                "quoted_evidence_ids": [str(nonexistent_evidence_id(run_id))],
            },
        ]
        written.extend(
            [
                {
                    "mode": "OTHER_APPLICANT",
                    "axis": "fundamentals",
                    "quoted_evidence_ids": [str(journey.reference_evidence)],
                },
                {
                    "mode": "OTHER_CRITERION",
                    "axis": "ownership",
                    "quoted_evidence_ids": [str(evidence.evidence_id)],
                },
            ]
        )
        axes = [
            {
                "axis": axis["axis"],
                "label": axis["axis"],
                "score": 80,
                "rationale": PROBE_RATIONALE,
                "quoted_evidence_ids": axis["quoted_evidence_ids"],
            }
            for axis in written
        ]
        journey.probe = self.adapters.spec004_mutation.write_probe_axes(
            lane=lane, report_item_id=item_id, axes=axes, injection_id=str(uuid4())
        )
        journey.probe_document |= {
            "report_item_id": item_id,
            "written_axes": [axis | {"score": 80} for axis in written],
            "other_criterion_source": {
                "report_id": str(before.report_id),
                "report_item_id": str(evidence.report_item_id),
                "criterion_id": str(evidence.criterion_id),
                "competency_model_version_id": str(evidence.competency_model_version_id),
                "evidence_id": str(evidence.evidence_id),
                "answer_turn_id": str(evidence.answer_turn_id),
                "transcript_segment_id": str(evidence.transcript_segment_id),
            },
        }
        if not isinstance(journey.probe, ChangeInjection):
            journey.probe_document["detail"] = journey.probe.code
            return
        journey.probe_document["injection_id"] = str(journey.probe.injection_id)
        if self._in_time(journey, "capture-storage-probe-reads"):
            read = self.adapters.spec004_records.read_api(
                lane=lane, phase=ReportPhase.POST_PROBE.value, include_timeline=False
            )
            if isinstance(read, ReportReadSnapshot):
                journey.reads.append(read.model_dump(mode="json") | {"lane_id": lane.lane_id.value})
            journey.probe_document |= {
                "status": "RECORDED",
                "read_after_write": getattr(read, "read_digest", None),
                "exposure": storage_probe_exposure(
                    written_axes=journey.probe_document["written_axes"],
                    read=read,
                    report_item_id=item_id,
                ),
            }

    def _restore_probe(self, journey: _Journey) -> None:
        injection = journey.probe
        if not isinstance(injection, ChangeInjection) or (
            injection.state is not ChangeInjectionState.APPLIED
        ):
            return
        try:
            journey.probe = self.restore_operation(
                self.adapters.spec004_mutation.restore_probe_axes, injection=injection
            )
        except Exception as exc:  # noqa: BLE001 - restore uncertainty is RESTORE_FAILED
            journey.probe = injection.model_copy(
                update={
                    "state": ChangeInjectionState.RESTORE_FAILED,
                    "failure_code": f"RESTORE_RAISED:{type(exc).__name__}",
                }
            )
        journey.steps.append({"step": "restore-storage-probe", "state": journey.probe.state})
        lane = journey.lanes[E01LaneId.E01_STORAGE_PROBE]

        def verify(state: _Journey) -> None:
            after = self.adapters.spec004_records.read_records(
                lane=lane, phase=ReportPhase.POST_RESTORE.value
            )
            self._record(state, after, "verify-storage-probe-restored")

        self._guarded(journey, "verify-storage-probe-restored", verify)

    def _recapture(self, journey: _Journey) -> None:
        reference = journey.lanes[E01LaneId.E01_REFERENCE]
        journey.reference_after = self.stable_records(reference, ReportPhase.GENERATED.value)
        self._record(journey, journey.reference_after, "recapture-reference-report")

    # --- outcome -------------------------------------------------------------------------------

    def _outcome(self, journey: _Journey) -> dict[str, Any]:
        a1, a2 = self._citation_assertions(journey)
        a3 = judge_e01_removal(
            injection=journey.removal, pre=journey.removal_pre_read, post=journey.removal_post_read
        )
        a4 = judge_e01_restore(
            injection=journey.removal,
            pre_read=journey.removal_pre_read,
            post_restore_read=journey.removal_restored_read,
            pre_record=journey.removal_pre_record,
            post_restore_record=journey.removal_restored_record,
        )
        injections = [
            item for item in (journey.removal, journey.probe) if isinstance(item, ChangeInjection)
        ]
        restored = all(item.state is ChangeInjectionState.RESTORED for item in injections)
        teardown = journey.teardown or AdapterResult(False, "SPEC004_TEARDOWN_NOT_RUN")
        return {
            "restore_ok": teardown.ok and restored,
            "injected": bool(injections),
            "lanes": tuple(journey.seeded),
            "assertions": (a1, a2, a3, a4),
            "recovery": {
                "steps": journey.steps,
                "injections_restored": restored,
                "teardown": {"ok": teardown.ok, "code": teardown.code},
            },
            "documents": {"storage-probe.json": journey.probe_document},
            "rows": {
                "citation-cases.jsonl": [case.model_dump(mode="json") for case in journey.cases],
                "model-emissions.jsonl": [
                    item.model_dump(mode="json") for item in journey.receipts
                ],
                "report-records.jsonl": journey.records,
                "report-reads.jsonl": journey.reads,
                "change-injections.jsonl": [item.model_dump(mode="json") for item in injections],
            },
        }

    def _citation_assertions(self, journey: _Journey):
        def digest(record: ReportRecordSnapshot | None) -> str | None:
            if record is None or record.source_status is not Presence.PRESENT:
                return None
            return record.state_digest

        if journey.matrix_record is None:
            detail = f"{PRECONDITION_NOT_MET}: citation matrix report was not requested"
            return (
                unassessed("E01-A1", "E01_CITATION_MATRIX", detail, ("FR-010",)),
                unassessed("E01-A2", "E01_CITATION_MATRIX", detail, ("FR-010",)),
            )
        a1, a2 = judge_e01_citations(
            cases=journey.cases,
            receipts=journey.receipts,
            reference_digests=(digest(journey.reference_before), digest(journey.reference_after)),
        )
        if journey.emission_problem is None:
            return a1, a2
        # Without receipts a PASS cannot be confirmed; a direct FAIL still stands.
        return tuple(
            item
            if item.status.value == "FAIL"
            else unassessed(
                item.assertion_id,
                "E01_CITATION_MATRIX",
                f"FIXTURE_EMISSION_MISMATCH: {journey.emission_problem}",
                item.source_requirements,
            )
            for item in (a1, a2)
        )
