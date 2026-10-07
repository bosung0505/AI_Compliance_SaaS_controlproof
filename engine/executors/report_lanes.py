"""Shared Spec 004 lane orchestration: seed, consent, report request, stable wait, bundle (T040).

Both E-01 and E-02 executors build on this. Reads follow the scenario snapshot's timing policy
(Spec 003 ID-003-10): a report is accepted only after `stability_consecutive` equal record digests
spanning `stability_seconds`; a report that never appears before the Run deadline is returned as
`ABSENT` and judged as a precondition, never as a target verdict.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from engine.adapters.base import AdapterResult, AdapterSet, Clock
from engine.evidence import SPEC004_REQUIRED_FILE_LINKS, EvidenceBundleWriter, verify_bundle
from engine.lifecycle import RestoreBlockStore, TargetSubjectLock
from engine.models import (
    SPEC004_UNVERIFIED_SCOPE,
    AssertionResult,
    AssertionStatus,
    AwsDeploymentStatus,
    EnvironmentKind,
    InconclusiveReason,
    Judgement,
    Presence,
    ReportLane,
    ReportRecordSnapshot,
    Run,
    RunState,
    ScenarioReadiness,
    TargetEnvironmentSnapshot,
    Verdict,
    canonical_json_bytes,
    sha256_bytes,
    utcnow,
)
from engine.readiness import evaluate_readiness
from engine.scenario import ScenarioDefinition

PRECONDITION_NOT_MET = "PRECONDITION_NOT_MET"


class _SystemClock:
    def now(self):
        return utcnow()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


class Spec004ExecutionError(RuntimeError):
    """A Spec 004 runner defect or unsealable Run (never a target verdict)."""


def lane_subject(lane: ReportLane) -> dict[str, str]:
    """The consent adapter's subject mapping (policy read and commit are lane-agnostic)."""
    return {
        "run_id": str(lane.run_id),
        "lane_id": lane.lane_id.value,
        "subject_ref": lane.subject_ref,
        "invitation_id": str(lane.invitation_id),
    }


def unassessed(
    assertion_id: str, subject_ref: str, detail: str, sources: tuple[str, ...]
) -> AssertionResult:
    return AssertionResult(
        assertion_id=assertion_id,
        subject_ref=subject_ref,
        status=AssertionStatus.INCONCLUSIVE,
        expected={"evaluated": True},
        actual={"evaluated": False},
        reason_code=InconclusiveReason.INSUFFICIENT_EVIDENCE,
        detail=detail,
        source_requirements=sources,
    )


def judge_spec004_run(
    *,
    run_id: UUID,
    scenario_id: str,
    assertion_ids: tuple[str, ...],
    assertion_results: tuple[AssertionResult, ...],
    run_state: RunState,
    decided_at: datetime,
) -> Judgement:
    """Combine profile assertions: RESTORE_FAILED → INCONCLUSIVE, else direct FAIL first."""
    by_id = {item.assertion_id: item for item in assertion_results}
    if set(by_id) - set(assertion_ids) or len(by_id) != len(assertion_results):
        raise ValueError("Spec 004 aggregate requires unique canonical assertions")
    ordered = tuple(
        by_id.get(assertion_id)
        or unassessed(
            assertion_id,
            "synthetic-unassessed",
            f"{PRECONDITION_NOT_MET}: 이 assertion은 평가되지 않았습니다.",
            ("EV4-10",),
        )
        for assertion_id in assertion_ids
    )
    inconclusive = [item for item in ordered if item.status is AssertionStatus.INCONCLUSIVE]
    if run_state is RunState.RESTORE_FAILED:
        verdict, reason = Verdict.INCONCLUSIVE, InconclusiveReason.INSUFFICIENT_EVIDENCE
        summary = "변경 주입의 복구 안전을 확인하지 못해 전체 결과를 판정하지 않았습니다."
    elif any(item.status is AssertionStatus.FAIL for item in ordered):
        verdict, reason = Verdict.FAIL, None
        summary = "점수 근거 또는 평가 기준 보존의 직접 위반이 관찰되었습니다."
    elif inconclusive:
        verdict = Verdict.INCONCLUSIVE
        conflict = any(
            item.reason_code is InconclusiveReason.EVIDENCE_CONFLICT for item in inconclusive
        )
        reason = (
            InconclusiveReason.EVIDENCE_CONFLICT
            if conflict
            else InconclusiveReason.INSUFFICIENT_EVIDENCE
        )
        summary = "필수 증적이 부족하거나 전제가 충족되지 않아 전체 PASS를 확정하지 않았습니다."
    else:
        verdict, reason = Verdict.PASS, None
        summary = f"{', '.join(assertion_ids)}와 해당 실행 증적이 모두 확인되었습니다."
    return Judgement(
        run_id=run_id,
        scenario_id=scenario_id,
        verdict=verdict,
        reason_code=reason,
        assertion_results=ordered,
        missing_evidence=tuple(item.assertion_id for item in inconclusive),
        unverified_scope=tuple(sorted(SPEC004_UNVERIFIED_SCOPE)),
        summary=summary,
        decided_at=decided_at,
    )


class Spec004LaneExecutor:
    """Base executor: subclasses implement `_journey` and declare profile, assertions, subject."""

    profile: Any = None
    assertion_ids: tuple[str, ...] = ()
    block_subject = ""
    seed_kind = "spec004_report_lanes_v1"
    fault_kind = "spec004_change_injection_v1"

    def __init__(
        self,
        scenario: ScenarioDefinition,
        adapters: AdapterSet,
        run_root: Path,
        *,
        clock: Clock | None = None,
    ) -> None:
        self.scenario = scenario
        self.adapters = adapters
        self.run_root = run_root.resolve()
        self.clock = clock or _SystemClock()
        self._deadline: datetime | None = None
        self._restore_seconds = 0.0
        self._timing: dict[str, Any] = {}

    # --- readiness -----------------------------------------------------------------------------

    def preflight(self, target_id: str) -> ScenarioReadiness:
        try:
            target_snapshot = self.adapters.target.capture_target_snapshot()
        except Exception:  # noqa: BLE001 - readiness must remain sanitized
            target_snapshot = None
        probes = [
            self.adapters.capability.probe(item) for item in self.scenario.required_capabilities
        ]
        return evaluate_readiness(
            self.scenario,
            target_id=target_id,
            registrations=self.adapters.capability.registrations,
            probe_results=probes,
            target_feature_exists=self.adapters.target.target_feature_exists(),
            target_snapshot=target_snapshot,
        )

    def timing_report(self) -> dict[str, Any]:
        return dict(self._timing)

    # --- lane helpers --------------------------------------------------------------------------

    def restore_operation(self, action, **kwargs):
        """Only restore/teardown work counts against the restore budget (ID-003-19)."""
        started = self.clock.now()
        try:
            return action(**kwargs)
        finally:
            self._restore_seconds += (self.clock.now() - started).total_seconds()

    def commit_consent(self, lane: ReportLane) -> AdapterResult:
        consent = self.adapters.spec004_consent
        subject = lane_subject(lane)
        policy = consent.read_policy(subject=subject)
        if isinstance(policy, AdapterResult):
            return policy
        request_id = str(UUID(int=lane.applicant_id.int ^ lane.invitation_id.int))
        return consent.commit(
            subject=subject, policy=policy, request_id=request_id, trace_id=lane.trace_namespace
        )

    def report_refused(self, lane: ReportLane) -> bool:
        """The worker's own refusal receipt ends the wait early (best effort)."""
        processing = self.adapters.spec004_requests.read_processing(lane=lane)
        receipts = processing.data.get("receipts", ()) if processing.ok else ()
        return "REPORT_ASSESSMENT_REFUSED" in receipts

    def wait_for_report(self, lane: ReportLane, phase: str) -> ReportRecordSnapshot:
        """Poll the stored report until present and stable, or the Run deadline passes."""
        timing = self.scenario.timing_policy
        records = self.adapters.spec004_records
        current = records.read_records(lane=lane, phase=phase)
        while not _present(current) and self.clock.now() < self._deadline:
            if self.report_refused(lane):
                break
            self.clock.sleep(timing.poll_seconds)
            current = records.read_records(lane=lane, phase=phase)
        if not _present(current):
            return current if isinstance(current, ReportRecordSnapshot) else _absent(lane, phase)
        return self.stable_records(lane, phase, first=current)

    def stable_records(
        self, lane: ReportLane, phase: str, *, first: ReportRecordSnapshot | None = None
    ) -> ReportRecordSnapshot:
        timing = self.scenario.timing_policy
        records = self.adapters.spec004_records
        value = first or records.read_records(lane=lane, phase=phase)
        if not isinstance(value, ReportRecordSnapshot):
            return _absent(lane, phase)
        streak, started = 1, self.clock.now()
        while True:
            elapsed = (self.clock.now() - started).total_seconds()
            if streak >= timing.stability_consecutive and elapsed >= timing.stability_seconds:
                return value
            if self.clock.now() >= self._deadline:
                return value
            self.clock.sleep(timing.poll_seconds)
            current = records.read_records(lane=lane, phase=phase)
            if not isinstance(current, ReportRecordSnapshot):
                return value
            if current.state_digest == value.state_digest:
                streak += 1
            else:
                streak, started = 1, self.clock.now()
            value = current

    # --- run lifecycle -------------------------------------------------------------------------

    def execute(
        self,
        readiness: ScenarioReadiness,
        *,
        operator_id: str = "local-operator",
        parent_run_id: UUID | None = None,
        label: str | None = None,
        retest_records: dict[str, Any] | None = None,
        run_id: UUID | None = None,
    ):
        del retest_records
        if readiness.status.value != "READY" or readiness.target_snapshot is None:
            raise RuntimeError(f"Run refused: {readiness.status.value}")
        if self.adapters.spec004_seed is None or self.adapters.spec004_records is None:
            raise Spec004ExecutionError("Spec 004 adapters are not composed")
        blocks = RestoreBlockStore(self.run_root)
        active_run_id = run_id or uuid4()
        scenario_id = self.scenario.scenario_id
        with TargetSubjectLock(self.run_root, readiness.target_id, self.block_subject):
            if blocks.blocked(readiness.target_id, self.block_subject):
                raise RuntimeError(f"target is blocked after a {scenario_id} restore failure")
            started_at = self.clock.now()
            budget = float(self.scenario.timing_policy.run_deadline_seconds or 0)
            self._deadline = started_at + timedelta(seconds=budget)
            self._restore_seconds = 0.0
            outcome = self._journey(active_run_id)
        ended_at = self.clock.now()
        restore_deadline = float(self.scenario.timing_policy.environment_restore_deadline_seconds)
        within = self._restore_seconds <= restore_deadline
        restore_ok = outcome["restore_ok"] and within
        self._timing = {
            "environment_restore_deadline_seconds": restore_deadline,
            "environment_restore_seconds": self._restore_seconds,
            "environment_restore_within_deadline": within,
        }
        state = RunState.COMPLETED if restore_ok else RunState.RESTORE_FAILED
        environment_raw = self.adapters.environment.capture_environment()
        environment = TargetEnvironmentSnapshot.model_validate(
            environment_raw.model_dump(mode="json", exclude={"snapshot_digest"})
            | {"unverified_scope": sorted(SPEC004_UNVERIFIED_SCOPE)}
        )
        target = readiness.target_snapshot
        capabilities = {
            "capabilities": sorted(self.scenario.required_capabilities),
            "model_fixture_id": target.model_fixture_id,
            "model_fixture_digest": target.model_fixture_digest,
            **outcome.get("capability_extra", {}),
        }
        lanes_doc = {"lanes": [lane.model_dump(mode="json") for lane in outcome["lanes"]]}
        snapshot = self.scenario.snapshot()
        run = Run(
            run_id=active_run_id,
            scenario_id=scenario_id,
            scenario_version=self.scenario.version,
            scenario_digest=snapshot.digest,
            target_id=readiness.target_id,
            target_version=str(target.target_version),
            model_fixture_id=target.model_fixture_id,
            model_fixture_digest=target.model_fixture_digest,
            state=state,
            started_at=started_at,
            ended_at=ended_at,
            seed_kind=self.seed_kind,
            fault_kind=self.fault_kind,
            parent_run_id=parent_run_id,
            operator_id=operator_id,
            label=label,
            fault_ever_applied=outcome.get("injected", False),
            manual_cleanup_required=not restore_ok,
            execution_profile=self.profile,
            environment_kind=EnvironmentKind.LOCAL_EMULATED,
            aws_deployment_status=AwsDeploymentStatus.NOT_RUN,
            environment_snapshot_digest=environment.snapshot_digest,
            lane_manifest_digest=sha256_bytes(canonical_json_bytes(lanes_doc)),
            path_capability_digest=sha256_bytes(canonical_json_bytes(capabilities)),
            scoring_rule_source_digest=outcome.get("scoring_rule_source_digest"),
            unverified_scope=tuple(sorted(SPEC004_UNVERIFIED_SCOPE)),
        )
        if not restore_ok:
            blocks.block(readiness.target_id, self.block_subject, run)
        judgement = judge_spec004_run(
            run_id=active_run_id,
            scenario_id=scenario_id,
            assertion_ids=self.assertion_ids,
            assertion_results=outcome["assertions"],
            run_state=state,
            decided_at=ended_at,
        )
        writer = EvidenceBundleWriter(self.run_root, run)
        documents = {
            "run.json": run.model_dump(mode="json"),
            "scenario.snapshot.yaml": snapshot.model_dump(mode="json"),
            "target.snapshot.json": target.model_dump(mode="json"),
            "environment.snapshot.json": environment.model_dump(mode="json"),
            "subjects.json": [lane_subject(lane) for lane in outcome["lanes"]],
            "assertions.json": [
                item.model_dump(mode="json") for item in judgement.assertion_results
            ],
            "judgement.json": judgement.model_dump(mode="json"),
            "spec004-capabilities.json": capabilities,
            "spec004-lanes.json": lanes_doc,
            "recovery.json": outcome["recovery"] | {"restore_timing": dict(self._timing)},
            **outcome["documents"],
        }
        for name, value in documents.items():
            writer.write_json(name, value, redact_first=False)
        writer.write_bytes("observations.jsonl", b"", "application/x-ndjson")
        for name, rows in outcome["rows"].items():
            if not rows:
                writer.write_bytes(name, b"", "application/x-ndjson")
            for row in rows:
                writer.append_jsonl(name, row)
        for evidence_id, files in SPEC004_REQUIRED_FILE_LINKS[self.profile].items():
            for name in sorted(files):
                writer.link_file_evidence(evidence_id, name)
        writer.link_intrinsic_evidence("EV4-10", "sealed-manifest")
        writer.seal()
        verify_started = self.clock.now()
        verified = verify_bundle(writer.directory)
        verify_seconds = (self.clock.now() - verify_started).total_seconds()
        verify_budget = self.scenario.timing_policy.bundle_verify_deadline_seconds
        self._timing.update(
            {
                "bundle_verify_seconds": verify_seconds,
                "bundle_verify_deadline_seconds": verify_budget,
                "bundle_verify_within_budget": None
                if verify_budget is None
                else verify_seconds <= float(verify_budget),
            }
        )
        if verified["bundle_status"] != "VERIFIED":
            raise Spec004ExecutionError(
                f"{scenario_id} sealed bundle failed verification: "
                f"{verified.get('mismatched_files', [])[:5]}"
            )
        return run, judgement, writer.directory

    def _journey(self, run_id: UUID) -> dict[str, Any]:  # pragma: no cover - abstract
        raise NotImplementedError


def _present(value: Any) -> bool:
    return isinstance(value, ReportRecordSnapshot) and value.source_status is Presence.PRESENT


def _absent(lane: ReportLane, phase: str) -> ReportRecordSnapshot:
    return ReportRecordSnapshot(
        run_id=lane.run_id,
        lane_id=lane.lane_id,
        subject_ref=lane.subject_ref,
        phase=phase,
        report_id=None,
        source_status=Presence.ABSENT,
        state_digest=sha256_bytes(
            canonical_json_bytes({"lane": lane.lane_id.value, "report": None})
        ),
    )
