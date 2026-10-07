"""E-01 executor: citation matrix journey (US1, T040).

Order (scenarios/E-01.yaml): seed REFERENCE/REMOVAL/PROBE lanes → consent → request → stable reference
report → seed the matrix with the reference report's Evidence ID → consent → request → stable matrix
report + emission receipts → judge E01-A1/A2 → re-read the reference → teardown.

Evidence removal and the storage probe (E01-A3/A4, E01-D1) belong to US2; until then they are reported
as `PRECONDITION_NOT_MET` INCONCLUSIVE and the overall verdict cannot be PASS.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from engine.adapters.base import AdapterResult
from engine.executors.report_lanes import (
    PRECONDITION_NOT_MET,
    Spec004LaneExecutor,
    unassessed,
)
from engine.judges.e01 import build_citation_cases, judge_e01_citations
from engine.models import (
    E01_ASSERTIONS,
    E01LaneId,
    ExecutionProfile,
    ModelEmissionReceipt,
    Presence,
    ReportLane,
    ReportPhase,
    ReportRecordSnapshot,
)
from seeds.spec004_subjects import e01_lanes, e01_matrix_lane

_US2_PENDING = f"{PRECONDITION_NOT_MET}: evidence removal and storage probe run in US2"


class E01Executor(Spec004LaneExecutor):
    profile = ExecutionProfile.E01_CITATION_EVIDENCE_V1
    assertion_ids = tuple(E01_ASSERTIONS)
    block_subject = "e01-citation-evidence"

    def _start_lane(self, lane: ReportLane, steps: list[dict[str, Any]]) -> bool:
        consent = self.commit_consent(lane)
        steps.append(
            {"step": "consent", "lane_id": lane.lane_id.value, "ok": consent.ok, "code": consent.code}
        )
        request = self.adapters.spec004_requests.request_report(lane=lane)
        steps.append(
            {"step": "request", "lane_id": lane.lane_id.value, "ok": request.ok, "code": request.code}
        )
        return consent.ok and request.ok

    def _journey(self, run_id: UUID) -> dict[str, Any]:
        seed = self.adapters.spec004_seed
        steps: list[dict[str, Any]] = []
        records: list[dict[str, Any]] = []
        seeded: list[ReportLane] = []
        receipts: tuple[ModelEmissionReceipt, ...] = ()
        cases = ()
        reference_before: ReportRecordSnapshot | None = None
        reference_after: ReportRecordSnapshot | None = None
        matrix_record: ReportRecordSnapshot | None = None
        emission_problem: str | None = None

        initial = e01_lanes(run_id)
        result = seed.seed_lanes(run_id=str(run_id), lanes=initial)
        steps.append({"step": "seed", "lanes": [lane.lane_id.value for lane in initial],
                      "ok": result.ok, "code": result.code})
        by_id = {lane.lane_id: lane for lane in initial}
        if result.ok:
            seeded.extend(initial)
            for lane in initial:
                self._start_lane(lane, steps)
            reference = by_id[E01LaneId.E01_REFERENCE]
            reference_before = self.wait_for_report(reference, ReportPhase.GENERATED.value)
            records.append(reference_before.model_dump(mode="json"))
            reference_evidence = (
                reference_before.evidence[0].evidence_id
                if reference_before.source_status is Presence.PRESENT and reference_before.evidence
                else None
            )
            if reference_evidence is not None:
                matrix = e01_matrix_lane(run_id, reference_evidence)
                result = seed.seed_lanes(run_id=str(run_id), lanes=(matrix,))
                steps.append({"step": "seed", "lanes": [matrix.lane_id.value],
                              "ok": result.ok, "code": result.code})
                if result.ok:
                    seeded.append(matrix)
                    self._start_lane(matrix, steps)
                    matrix_record = self.wait_for_report(matrix, ReportPhase.GENERATED.value)
                    records.append(matrix_record.model_dump(mode="json"))
                    emitted = self.adapters.spec004_emissions.read_emissions(
                        criterion_ids=tuple(str(item.criterion_id) for item in matrix.criteria)
                    )
                    if isinstance(emitted, AdapterResult):
                        emission_problem = emitted.code
                    else:
                        receipts = emitted
                    cases = build_citation_cases(
                        lane=matrix, record=matrix_record, receipts=receipts
                    )
            reference_after = self.stable_records(reference, ReportPhase.GENERATED.value)
            records.append(reference_after.model_dump(mode="json") | {"step": "recapture"})

        a1, a2 = self._citation_assertions(
            cases, receipts, reference_before, reference_after, matrix_record, emission_problem
        )
        teardown = (
            self.restore_operation(
                seed.teardown, run_id=str(run_id), lanes=tuple(seeded), position_ids=()
            )
            if seeded
            else AdapterResult(True, "SPEC004_NOTHING_SEEDED")
        )
        steps.append({"step": "teardown", "ok": teardown.ok, "code": teardown.code})
        assertions = (
            a1,
            a2,
            unassessed("E01-A3", "E01_EVIDENCE_REMOVAL", _US2_PENDING, ("FR-020",)),
            unassessed("E01-A4", "E01_EVIDENCE_REMOVAL", _US2_PENDING, ("FR-022",)),
        )
        return {
            "restore_ok": teardown.ok,
            "injected": False,
            "lanes": tuple(seeded),
            "assertions": assertions,
            "recovery": {"steps": steps, "teardown": {"ok": teardown.ok, "code": teardown.code}},
            "documents": {"storage-probe.json": {"status": "NOT_RUN", "detail": _US2_PENDING}},
            "rows": {
                "citation-cases.jsonl": [case.model_dump(mode="json") for case in cases],
                "model-emissions.jsonl": [item.model_dump(mode="json") for item in receipts],
                "report-records.jsonl": records,
                "report-reads.jsonl": [],
                "change-injections.jsonl": [],
            },
        }

    def _citation_assertions(
        self, cases, receipts, reference_before, reference_after, matrix_record, emission_problem
    ):
        def digest(record: ReportRecordSnapshot | None) -> str | None:
            if record is None or record.source_status is not Presence.PRESENT:
                return None
            return record.state_digest

        if matrix_record is None:
            detail = f"{PRECONDITION_NOT_MET}: citation matrix report was not requested"
            return (
                unassessed("E01-A1", "E01_CITATION_MATRIX", detail, ("FR-010",)),
                unassessed("E01-A2", "E01_CITATION_MATRIX", detail, ("FR-010",)),
            )
        a1, a2 = judge_e01_citations(
            cases=cases,
            receipts=receipts,
            reference_digests=(digest(reference_before), digest(reference_after)),
        )
        if emission_problem is None:
            return a1, a2
        # Without receipts a PASS cannot be confirmed; a direct FAIL still stands.
        return tuple(
            item
            if item.status.value == "FAIL"
            else unassessed(
                item.assertion_id,
                "E01_CITATION_MATRIX",
                f"FIXTURE_EMISSION_MISMATCH: {emission_problem}",
                item.source_requirements,
            )
            for item in (a1, a2)
        )
