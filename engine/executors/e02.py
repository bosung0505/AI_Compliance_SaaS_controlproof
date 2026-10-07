"""E-02 executor: v1 publish → first report → v2 publish → second report → compare and recompute (T057).

The v2 publication is the change injection; its restore is the Run-owned position teardown, confirmed by the
other positions' version digest being unchanged (`verify-other-positions-unchanged`). Teardown and that check are
always-run. Preflight refuses when the WhyYou scoring sources differ from the pinned copy
(`SCORING_RULE_SOURCE_DRIFT`, T059) before anything is written.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from engine.adapters.base import AdapterResult
from engine.executors.report_lanes import Spec004LaneExecutor
from engine.judges.e02 import (
    frozen_input_set,
    judge_e02_frozen,
    judge_e02_recompute,
    judge_e02_unchanged,
    recompute,
)
from engine.judges.e02_scoring import PINNED_SOURCES, RULE_COPY_ID
from engine.models import (
    E02_ASSERTIONS,
    ChangeInjection,
    ChangeInjectionKind,
    ChangeInjectionState,
    CriteriaVersionSnapshot,
    E02LaneId,
    ExecutionProfile,
    ReadinessStatus,
    ReportLane,
    ReportPhase,
    ReportReadSnapshot,
    ReportRecordSnapshot,
    RestoreAction,
    ScenarioReadiness,
    VersionSnapshotPhase,
    canonical_json_bytes,
    sha256_bytes,
    utcnow,
)
from seeds.spec004_subjects import e02_lane, e02_position_id, e02_version_body


def scoring_rule_source_digest(target_blob_shas: dict[str, str] | None) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {
                "rule_copy_id": RULE_COPY_ID,
                "pinned": list(PINNED_SOURCES),
                "target": target_blob_shas or {},
            }
        )
    )


@dataclass
class _Journey:
    run_id: UUID
    steps: list[dict[str, Any]] = field(default_factory=list)
    records: list[dict[str, Any]] = field(default_factory=list)
    reads: list[dict[str, Any]] = field(default_factory=list)
    seeded: list[ReportLane] = field(default_factory=list)
    position_id: str | None = None
    blob_shas: dict[str, str] = field(default_factory=dict)
    other_before: str | None = None
    other_after: str | None = None
    v1: CriteriaVersionSnapshot | None = None
    v2: CriteriaVersionSnapshot | None = None
    v2_id: str | None = None
    injection: ChangeInjection | None = None
    pre_record: ReportRecordSnapshot | None = None
    pre_read: ReportReadSnapshot | None = None
    post_record: ReportRecordSnapshot | None = None
    post_read: ReportReadSnapshot | None = None
    second_record: ReportRecordSnapshot | None = None
    second_read: ReportReadSnapshot | None = None
    teardown: AdapterResult | None = None


class _Stop(Exception):
    pass


class E02Executor(Spec004LaneExecutor):
    profile = ExecutionProfile.E02_SCORING_FREEZE_V1
    assertion_ids = tuple(E02_ASSERTIONS)
    block_subject = "e02-scoring-freeze"
    seed_kind = "spec004_e02_position_v1"

    def preflight(self, target_id: str) -> ScenarioReadiness:
        readiness = super().preflight(target_id)
        if readiness.status is not ReadinessStatus.READY:
            return readiness
        source = self.adapters.spec004_scoring_source.read_blob_shas()
        pinned = {item["path"]: item["blob_sha"] for item in PINNED_SOURCES}
        if source.ok and dict(source.data.get("blob_shas") or {}) == pinned:
            return readiness
        code = "SCORING_RULE_SOURCE_DRIFT" if source.ok else source.code
        return readiness.model_copy(
            update={
                "status": ReadinessStatus.RUNNER_NOT_READY,
                "operator_action": (
                    f"{code}: WhyYou scoring.py/report.py differ from the pinned recompute copy; "
                    "re-pin engine/judges/e02_scoring.py after reviewing the scoring change"
                ),
            }
        )

    # --- helpers -------------------------------------------------------------------------------

    def _step(self, journey: _Journey, step: str, result: AdapterResult) -> AdapterResult:
        journey.steps.append({"step": step, "code": result.code})
        if not result.ok:
            raise _Stop(step)
        return result

    def _record(self, journey: _Journey, value: ReportRecordSnapshot, step: str) -> None:
        journey.records.append(value.model_dump(mode="json") | {"step": step})

    def _read(self, journey: _Journey, lane: ReportLane, phase: str) -> ReportReadSnapshot | None:
        value = self.adapters.spec004_records.read_api(lane=lane, phase=phase)
        if isinstance(value, AdapterResult):
            journey.steps.append({"step": f"read:{lane.lane_id.value}:{phase}", "code": value.code})
            return None
        journey.reads.append(value.model_dump(mode="json") | {"lane_id": lane.lane_id.value})
        return value

    def _publish(self, journey: _Journey, key: str) -> tuple[str, CriteriaVersionSnapshot]:
        versions = self.adapters.spec004_versions
        created = self._step(
            journey,
            f"create-{key}",
            versions.create_version(
                position_id=journey.position_id,
                body=e02_version_body(key),
                idempotency_key=f"controlproof-{journey.run_id}-{key}-create",
            ),
        )
        version_id = str(created.data["version_id"])
        self._step(
            journey,
            f"publish-{key}",
            versions.publish_version(
                version_id=version_id,
                row_version=int(created.data["row_version"]),
                idempotency_key=f"controlproof-{journey.run_id}-{key}-publish",
            ),
        )
        phase = VersionSnapshotPhase.V1_PUBLISHED if key == "v1" else VersionSnapshotPhase.V2_PUBLISHED
        snapshot = versions.latest_published(
            position_id=journey.position_id, snapshot_phase=phase.value
        )
        if isinstance(snapshot, AdapterResult):
            self._step(journey, f"read-{key}", snapshot)
        return version_id, snapshot

    def _applicant(self, journey: _Journey, lane: ReportLane) -> None:
        self._step(
            journey,
            f"seed:{lane.lane_id.value}",
            self.adapters.spec004_seed.seed_lanes(run_id=str(journey.run_id), lanes=(lane,)),
        )
        journey.seeded.append(lane)
        self._step(journey, f"consent:{lane.lane_id.value}", self.commit_consent(lane))
        self._step(
            journey,
            f"request:{lane.lane_id.value}",
            self.adapters.spec004_requests.request_report(lane=lane),
        )

    # --- journey -------------------------------------------------------------------------------

    def _journey(self, run_id: UUID) -> dict[str, Any]:
        journey = _Journey(run_id=run_id)
        try:
            self._steps(journey)
        except _Stop as stop:
            journey.steps.append({"step": "stopped", "at": str(stop)})
        except Exception as exc:  # noqa: BLE001 - a failed step is evidence, not a crash
            journey.steps.append({"step": "error", "error": type(exc).__name__})
        finally:
            self._teardown(journey)
        return self._outcome(journey)

    def _steps(self, journey: _Journey) -> None:
        source = self.adapters.spec004_scoring_source.read_blob_shas()
        journey.blob_shas = dict(source.data.get("blob_shas") or {}) if source.ok else {}
        journey.steps.append({"step": "capture-scoring-rule-source", "code": source.code})
        position = str(e02_position_id(journey.run_id))
        self._step(
            journey,
            "seed-e02-position",
            self.adapters.spec004_seed.seed_position(run_id=str(journey.run_id), position_id=position),
        )
        journey.position_id = position
        other = self.adapters.spec004_versions.other_positions_digest(
            excluded_position_ids=(position,)
        )
        journey.other_before = other.data.get("digest") if other.ok else None
        _, journey.v1 = self._publish(journey, "v1")
        first = e02_lane(journey.run_id, E02LaneId.E02_FIRST_APPLICANT, journey.v1)
        self._applicant(journey, first)
        generated = self.wait_for_report(first, ReportPhase.GENERATED.value)
        self._record(journey, generated, "request-first-report")
        journey.pre_record = self.stable_records(first, ReportPhase.PRE_CHANGE.value)
        self._record(journey, journey.pre_record, "capture-pre-change")
        journey.pre_read = self._read(journey, first, ReportPhase.PRE_CHANGE.value)
        journey.v2_id, journey.v2 = self._publish(journey, "v2")
        journey.injection = ChangeInjection(
            injection_id=uuid4(),
            kind=ChangeInjectionKind.CRITERIA_VERSION_PUBLISH,
            run_id=journey.run_id,
            lane_id=E02LaneId.E02_FIRST_APPLICANT,
            subject_ref=first.subject_ref,
            target_table="competency_model_versions",
            target_ids=(UUID(journey.v2_id),),
            pre_projection_digest=journey.other_before or sha256_bytes(b""),
            applied_at=utcnow(),
            apply_receipt={"published_version_id": journey.v2_id},
            restore_action=RestoreAction.TEARDOWN,
            state=ChangeInjectionState.APPLIED,
        )
        second = e02_lane(journey.run_id, E02LaneId.E02_SECOND_APPLICANT, journey.v2)
        self._applicant(journey, second)
        journey.second_record = self.wait_for_report(second, ReportPhase.POST_CHANGE.value)
        self._record(journey, journey.second_record, "capture-second-report")
        journey.second_read = self._read(journey, second, ReportPhase.POST_CHANGE.value)
        journey.post_record = self.stable_records(first, ReportPhase.POST_CHANGE.value)
        self._record(journey, journey.post_record, "capture-post-change")
        journey.post_read = self._read(journey, first, ReportPhase.POST_CHANGE.value)

    def _teardown(self, journey: _Journey) -> None:
        if journey.position_id is None and not journey.seeded:
            journey.teardown = AdapterResult(True, "SPEC004_NOTHING_SEEDED")
            return
        try:
            journey.teardown = self.restore_operation(
                self.adapters.spec004_seed.teardown,
                run_id=str(journey.run_id),
                lanes=tuple(journey.seeded),
                position_ids=(journey.position_id,) if journey.position_id else (),
            )
        except Exception as exc:  # noqa: BLE001 - teardown uncertainty is RESTORE_FAILED
            journey.teardown = AdapterResult(False, "SPEC004_TEARDOWN_RAISED", detail=type(exc).__name__)
        journey.steps.append({"step": "teardown-e02-position", "code": journey.teardown.code})
        other = self.adapters.spec004_versions.other_positions_digest(
            excluded_position_ids=(journey.position_id,) if journey.position_id else ()
        )
        journey.other_after = other.data.get("digest") if other.ok else None
        journey.steps.append({"step": "verify-other-positions-unchanged", "code": other.code})
        if journey.injection is None:
            return
        safe = (
            journey.teardown.ok
            and journey.other_after is not None
            and journey.other_after == journey.injection.pre_projection_digest
        )
        if safe:
            journey.injection = journey.injection.model_copy(
                update={
                    "state": ChangeInjectionState.RESTORED,
                    "restored_at": utcnow(),
                    "post_restore_digest": journey.other_after,
                }
            )
        else:
            journey.injection = journey.injection.model_copy(
                update={
                    "state": ChangeInjectionState.RESTORE_FAILED,
                    "failure_code": "SPEC004_TEARDOWN_FAILED"
                    if not journey.teardown.ok
                    else "OTHER_POSITIONS_CHANGED",
                    "post_restore_digest": journey.other_after,
                }
            )

    # --- outcome -------------------------------------------------------------------------------

    def _outcome(self, journey: _Journey) -> dict[str, Any]:
        records = (
            recompute(
                record=journey.post_record, read=journey.post_read, target_blob_shas=journey.blob_shas
            ),
            recompute(
                record=journey.second_record,
                read=journey.second_read,
                target_blob_shas=journey.blob_shas,
            ),
        )
        assertions = (
            judge_e02_frozen(first=journey.pre_record, v1=journey.v1),
            judge_e02_unchanged(
                v2=journey.v2,
                published_v2_id=journey.v2_id,
                second=journey.second_record,
                pre_record=journey.pre_record,
                post_record=journey.post_record,
                pre_read=journey.pre_read,
                post_read=journey.post_read,
            ),
            judge_e02_recompute(records=records),
        )
        teardown = journey.teardown or AdapterResult(False, "SPEC004_TEARDOWN_NOT_RUN")
        others_unchanged = (
            journey.other_before is not None and journey.other_before == journey.other_after
        )
        restored = journey.injection is None or (
            journey.injection.state is ChangeInjectionState.RESTORED
        )
        frozen = {
            name: frozen_input_set(record, version).model_dump(mode="json")
            for name, record, version in (
                ("first", journey.pre_record, journey.v1),
                ("second", journey.second_record, journey.v2),
            )
            if record is not None and record.report_id is not None and version is not None
        }
        return {
            "restore_ok": teardown.ok and others_unchanged and restored,
            "injected": journey.injection is not None,
            "lanes": tuple(journey.seeded),
            "assertions": assertions,
            "scoring_rule_source_digest": scoring_rule_source_digest(journey.blob_shas),
            "capability_extra": {"scoring_rule_source": journey.blob_shas},
            "recovery": {
                "steps": journey.steps,
                "teardown": {"ok": teardown.ok, "code": teardown.code},
                "other_positions": {
                    "before": journey.other_before,
                    "after": journey.other_after,
                    "unchanged": others_unchanged,
                },
            },
            "documents": {
                "criteria-versions.json": {
                    "position_id": journey.position_id,
                    "v1": journey.v1.model_dump(mode="json") if journey.v1 else None,
                    "v2": journey.v2.model_dump(mode="json") if journey.v2 else None,
                    "published_v2_id": journey.v2_id,
                },
                "frozen-inputs.json": frozen,
                "recompute.json": {
                    "rule_copy_id": RULE_COPY_ID,
                    "target_blob_shas": journey.blob_shas,
                    "records": [
                        None if item is None else item.model_dump(mode="json") for item in records
                    ],
                },
            },
            "rows": {
                "report-records.jsonl": journey.records,
                "report-reads.jsonl": journey.reads,
                "change-injections.jsonl": [journey.injection.model_dump(mode="json")]
                if journey.injection
                else [],
            },
        }
