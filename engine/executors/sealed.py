"""Shared sealed Evidence Bundle orchestration for Spec 002 profiles."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from engine.adapters.base import AdapterResult
from engine.evidence import EvidenceBundleWriter
from engine.lifecycle import RestoreBlockStore, TargetSubjectLock
from engine.models import (
    AssertionResult,
    AssertionStatus,
    BusinessEffectSnapshot,
    DecisionPathId,
    EvidenceArtifact,
    ExecutionProfile,
    Finding,
    InconclusiveReason,
    Judgement,
    Observation,
    Phase,
    Presence,
    ReadinessStatus,
    Run,
    RunState,
    ScenarioReadiness,
    Source,
    TestSubject,
    Verdict,
    canonical_json_bytes,
    sha256_bytes,
)
from engine.retest import finalize_retest_records


def execute_profile(
    executor: Any,
    readiness: ScenarioReadiness,
    *,
    collector: Callable[..., Any],
    operator_id: str = "local-operator",
    parent_run_id: UUID | None = None,
    label: str | None = None,
    retest_records: dict[str, Any] | None = None,
    run_id: UUID | None = None,
) -> tuple[Run, Judgement, Path]:
    """Collect one profile, project its facts, and seal an immutable bundle."""

    if readiness.status is not ReadinessStatus.READY or readiness.target_snapshot is None:
        raise RuntimeError(f"Run refused: {readiness.status.value}")
    subject_ref = "candidate-01"
    blocks = RestoreBlockStore(executor.run_root)
    if blocks.blocked(readiness.target_id, subject_ref):
        raise RuntimeError("target+subject is blocked after a restore failure")
    active_run_id = run_id or uuid4()
    started_at = executor.clock.now()
    lock = TargetSubjectLock(executor.run_root, readiness.target_id, subject_ref)
    with lock:
        result = collector(run_id=active_run_id, subject_ref=subject_ref)
    ended_at = executor.clock.now()

    environment = result.environment
    topology = result.topology
    restore = result.restore
    restore_ok = bool(
        restore.ok
        and restore.data.get("marker_inactive") is True
        and restore.data.get("worker_healthy") is True
    )
    state = RunState.COMPLETED if restore_ok else RunState.RESTORE_FAILED
    snapshot = executor.scenario.snapshot()
    run = Run(
        run_id=active_run_id,
        scenario_id=executor.scenario.scenario_id,
        scenario_version=executor.scenario.version,
        scenario_digest=snapshot.digest,
        target_id=readiness.target_id,
        target_version=str(readiness.target_snapshot.target_version),
        model_fixture_id=readiness.target_snapshot.model_fixture_id,
        model_fixture_digest=readiness.target_snapshot.model_fixture_digest,
        state=state,
        started_at=started_at,
        ended_at=ended_at,
        fault_kind=executor.scenario.fault_variant.value,
        parent_run_id=parent_run_id,
        operator_id=operator_id,
        label=label,
        fault_ever_applied=True,
        manual_cleanup_required=not restore_ok,
        execution_profile=executor.profile,
        fault_variant=executor.scenario.fault_variant,
        environment_kind=environment.environment_kind,
        aws_deployment_status=environment.aws_deployment_status,
        environment_snapshot_digest=environment.snapshot_digest,
        queue_topology_digest=topology.snapshot_digest,
        source_event_id=result.source_event_id,
        unverified_scope=environment.unverified_scope,
    )
    if not restore_ok:
        blocks.block(readiness.target_id, subject_ref, run)

    assertions = _profile_assertions(executor.profile, result)
    writer = EvidenceBundleWriter(executor.run_root, run)
    writer.write_json("run.json", run.model_dump(mode="json"), redact_first=False)
    writer.write_json(
        "scenario.snapshot.yaml", snapshot.model_dump(mode="json"), redact_first=False
    )
    writer.write_json(
        "target.snapshot.json",
        readiness.target_snapshot.model_dump(mode="json"),
        redact_first=False,
    )
    writer.write_json(
        "environment.snapshot.json", environment.model_dump(mode="json"), redact_first=False
    )
    writer.write_json(
        "queue-topology.snapshot.json", topology.model_dump(mode="json"), redact_first=False
    )
    test_subject = _test_subject(result)
    writer.write_json("subjects.json", [test_subject.model_dump(mode="json")])
    _write_lineage_files(writer, executor.profile, result)
    _write_observations(writer, run, result)

    evidence_artifacts = _collect_required_artifacts(writer, executor, result)
    assertions = _link_assertion_artifacts(
        assertions, executor.scenario.assertions, evidence_artifacts
    )
    verdict, reason = _verdict(assertions, restore_ok)
    findings = tuple(
        Finding(
            code=f"{item.assertion_id}_FAILED",
            severity="HIGH",
            detail=item.detail,
            assertion_id=item.assertion_id,
            artifact_ids=item.artifact_ids,
        )
        for item in assertions
        if item.status is AssertionStatus.FAIL
    )
    judgement = Judgement(
        run_id=run.run_id,
        scenario_id=run.scenario_id,
        verdict=verdict,
        reason_code=reason,
        assertion_results=assertions,
        findings=findings,
        missing_evidence=(),
        unverified_scope=run.unverified_scope,
        summary=_summary(verdict, restore_ok),
        decided_at=ended_at,
    )
    writer.write_json(
        "assertions.json",
        [item.model_dump(mode="json") for item in assertions],
        redact_first=False,
    )
    writer.write_json("judgement.json", judgement.model_dump(mode="json"), redact_first=False)

    if retest_records is not None:
        finalize_retest_records(retest_records, test_subject)
        writer.write_json("retest-link.json", retest_records["link"], redact_first=False)
        writer.write_json("retest-diff.json", retest_records["diff"], redact_first=False)
        origin = retest_records.get("_origin_reference")
        if isinstance(origin, Mapping):
            writer.link_origin_artifact(
                "EV2-12",
                origin_run_id=UUID(str(origin["origin_run_id"])),
                artifact_id=UUID(str(origin["artifact_id"])),
                artifact_digest=str(origin["artifact_digest"]),
                bundle_digest=str(origin["bundle_digest"]),
            )

    _link_file_evidence(writer, executor.profile)
    writer.link_intrinsic_evidence("EV2-12", "sealed-manifest")
    writer.seal()
    return run, judgement, writer.directory


def _profile_assertions(
    profile: ExecutionProfile, result: Any
) -> tuple[AssertionResult, ...]:
    if profile is not ExecutionProfile.H03_DLQ_V2:
        return tuple(result.assertions)
    return _complete_h03_assertions(result)


def _complete_h03_assertions(result: Any) -> tuple[AssertionResult, ...]:
    boundary_ok = result.boundary is not None and result.fault_application.ok
    a1 = _assertion(
        "H03-A1",
        AssertionStatus.PASS if boundary_ok else AssertionStatus.INCONCLUSIVE,
        "현재 Run의 BEFORE 장애 경계가 확인됐습니다."
        if boundary_ok
        else "BEFORE 장애 경계를 확인하지 못했습니다.",
        None if boundary_ok else InconclusiveReason.INSUFFICIENT_EVIDENCE,
    )
    visible = (
        result.browser_projection.get("terminal_status_class") == "final_failed"
        and result.report_status in {"failed", "final_failed"}
    )
    a2 = _assertion(
        "H03-A2",
        AssertionStatus.PASS if visible else AssertionStatus.FAIL,
        "담당자 API와 화면에서 최종 실패가 구분됩니다."
        if visible
        else "리포트 미준비 또는 최종 실패가 담당자에게 명확히 드러나지 않습니다.",
    )
    cases = {case.path_id: case for case in result.decision_cases}
    final_case = cases.get(DecisionPathId.FINAL_DECISION)
    final_refused = bool(
        final_case
        and final_case.attempt.ok
        and final_case.attempt.data.get("accepted") is False
        and final_case.attempt.data.get("reason_present") is True
    )
    a3 = _assertion(
        "H03-A3",
        AssertionStatus.PASS if final_refused else AssertionStatus.FAIL,
        "정상 최종결정 경로가 리포트 부재 이유로 거부됐습니다."
        if final_refused
        else "정상 최종결정 경로가 명시적으로 거부되지 않았습니다.",
    )
    unchanged = bool(
        final_case
        and final_case.pre_effects
        and final_case.post_effects
        and final_case.pre_effects[0].state_digest
        == final_case.post_effects[0].state_digest
    )
    a4 = _assertion(
        "H03-A4",
        AssertionStatus.PASS if unchanged else AssertionStatus.FAIL,
        "거부된 결정 뒤 부분 변경이 없습니다."
        if unchanged
        else "거부된 결정 뒤 일부 채용 효과가 변경됐습니다.",
    )
    non_company = {
        actor
        for case in result.decision_cases
        for snapshot in case.post_effects
        for key in ("human_review_actor_types", "decision_actor_types")
        for actor in snapshot.effects.get(key, ())
        if actor != "COMPANY_USER"
    }
    automatic_absent = unchanged and not non_company
    a5 = _assertion(
        "H03-A5",
        AssertionStatus.PASS if automatic_absent else AssertionStatus.FAIL,
        "사람 요청 없는 자동 최종결정 효과가 없습니다."
        if automatic_absent
        else "비회사 사용자 결정 효과 또는 상태 변경이 관찰됐습니다.",
    )
    restore_ok = bool(
        result.restore.ok
        and result.restore.data.get("marker_inactive") is True
        and result.restore.data.get("worker_healthy") is True
    )
    a6 = _assertion(
        "H03-A6",
        AssertionStatus.PASS if restore_ok else AssertionStatus.INCONCLUSIVE,
        "marker와 worker가 안전한 상태로 복구됐습니다."
        if restore_ok
        else "환경 복구를 확정할 수 없습니다.",
        None if restore_ok else InconclusiveReason.INSUFFICIENT_EVIDENCE,
    )
    if result.decision_assertion is None:
        a7 = _assertion(
            "H03-A7",
            AssertionStatus.INCONCLUSIVE,
            "세 canonical 결정 경로를 모두 실행하지 못했습니다.",
            InconclusiveReason.INSUFFICIENT_EVIDENCE,
        )
    else:
        a7 = result.decision_assertion
    a8, a9 = result.assertions
    return (a1, a2, a3, a4, a5, a6, a7, a8, a9)


def _assertion(
    assertion_id: str,
    status: AssertionStatus,
    detail: str,
    reason: InconclusiveReason | None = None,
) -> AssertionResult:
    return AssertionResult(
        assertion_id=assertion_id,
        subject_ref="candidate-01",
        status=status,
        expected=None,
        actual=None,
        reason_code=reason,
        detail=detail,
        source_requirements=(assertion_id,),
    )


def _test_subject(result: Any) -> TestSubject:
    subject = result.subject
    locators = {
        key: str(subject[key])
        for key in ("invitation_id", "interview_session_id", "target_stage_id")
        if subject.get(key) is not None
    }
    baseline = getattr(result, "baseline", None)
    initial = (
        dict(baseline.data.get("state", {}))
        if isinstance(baseline, AdapterResult)
        else {
            "subject_ref": subject.get("subject_ref", "candidate-01"),
            "pipeline_row_version": subject.get("pipeline_row_version"),
        }
    )
    return TestSubject(
        subject_ref=str(subject.get("subject_ref", "candidate-01")),
        subject_type=str(subject.get("subject_type", "synthetic_applicant")),
        synthetic=bool(subject.get("synthetic", False)),
        locators=locators,
        initial_state_digest=sha256_bytes(canonical_json_bytes(initial)),
        seed_correlation_id=str(subject["seed_correlation_id"]),
    )


def _write_lineage_files(
    writer: EvidenceBundleWriter, profile: ExecutionProfile, result: Any
) -> None:
    boundary = getattr(result, "boundary", None)
    _write_jsonl(writer, "faults.jsonl", [boundary] if boundary is not None else [])
    attempts = list(getattr(result, "attempts", ()))
    if profile is ExecutionProfile.E03_AFTER_V2:
        duplicate = getattr(result, "duplicate_ack", None)
        if isinstance(duplicate, AdapterResult) and duplicate.data.get("receipt"):
            attempts.append(dict(duplicate.data["receipt"]))
    _write_jsonl(writer, "delivery-attempts.jsonl", attempts)
    effects = _effects(result)
    _write_jsonl(writer, "effects.jsonl", effects)
    if profile in {ExecutionProfile.H03_DLQ_V2, ExecutionProfile.E03_BEFORE_V2}:
        terminal = getattr(result, "terminal_failure", None)
        writer.write_json(
            "terminal-failure.json",
            _dump(terminal) if terminal is not None else {"presence": "ABSENT"},
            redact_first=False,
        )
        redrive = getattr(result, "redrive", None)
        _write_jsonl(
            writer,
            "redrive-receipts.jsonl",
            [redrive] if redrive is not None else [{"presence": "ABSENT"}],
        )


def _write_observations(writer: EvidenceBundleWriter, run: Run, result: Any) -> None:
    restore = result.restore
    values = (
        ("fault.environment_restore", "SUCCEEDED" if restore.ok else "FAILED", Source.FAULT),
        (
            "report.processing_recovery",
            restore.data.get("report_processing_recovery", "UNAVAILABLE"),
            Source.SYSTEM,
        ),
        ("source.event.id", str(result.source_event_id), Source.SYSTEM),
    )
    for key, value, source in values:
        observation = Observation(
            run_id=run.run_id,
            subject_ref="candidate-01",
            phase=Phase.RECOVERED,
            step_id="spec002-summary",
            attempt=1,
            key=key,
            presence=Presence.PRESENT,
            value=value,
            source_type=source,
            source_ref=f"{run.target_id}:spec002-summary",
            observed_at=run.ended_at,
        )
        writer.append_jsonl("observations.jsonl", observation.model_dump(mode="json"))


def _collect_required_artifacts(
    writer: EvidenceBundleWriter, executor: Any, result: Any
) -> dict[str, EvidenceArtifact]:
    artifacts: dict[str, EvidenceArtifact] = {}
    phase_by_id = {
        **{f"EV-{index:02d}": Phase.INJECTED for index in range(1, 10)},
        **{f"EV2-{index:02d}": Phase.INJECTED for index in range(1, 13)},
    }
    for evidence in executor.scenario.required_evidence:
        evidence_id = evidence.evidence_id
        if evidence_id in {"EV-01", "EV-09", "EV2-01", "EV2-02", "EV2-12"}:
            phase_by_id[evidence_id] = Phase.BASELINE
        elif evidence_id in {"EV-08", "EV2-09", "EV2-10", "EV2-11"}:
            phase_by_id[evidence_id] = Phase.RECOVERED
        artifacts[evidence_id] = writer.collect_json_artifact(
            subject_ref="candidate-01",
            phase=phase_by_id[evidence_id],
            step_id=f"evidence.{evidence_id.casefold()}",
            attempt=1,
            evidence_requirement_ids=(evidence_id,),
            artifact_type=evidence.artifact_types[0],
            source_locator={"profile": executor.profile.value, "evidence_id": evidence_id},
            content=_evidence_content(evidence_id, result),
        )
    return artifacts


def _evidence_content(evidence_id: str, result: Any) -> Any:
    if evidence_id in {"EV-09", "EV2-01"}:
        return {"environment": _dump(result.environment), "queue": _dump(result.topology)}
    if evidence_id in {"EV-01", "EV2-02"}:
        return {
            "source_event_id": str(result.source_event_id),
            "baseline": _dump(getattr(result, "baseline", None)),
        }
    if evidence_id in {"EV-02", "EV2-03"}:
        return {"boundary": _dump(getattr(result, "boundary", None))}
    if evidence_id == "EV2-04":
        return {
            "attempts": _dump(getattr(result, "attempts", ())),
            "duplicate_ack": _dump(getattr(result, "duplicate_ack", None)),
        }
    if evidence_id == "EV2-05":
        return {"terminal_failure": _dump(getattr(result, "terminal_failure", None))}
    if evidence_id in {"EV-03", "EV-04", "EV2-06"}:
        return {
            "report_status": getattr(result, "report_status", None),
            "browser_projection": getattr(result, "browser_projection", {}),
        }
    if evidence_id in {"EV-05", "EV2-07"}:
        return {
            "decision_paths": [
                {
                    "path_id": case.path_id.value,
                    "attempt": _dump(case.attempt),
                }
                for case in getattr(result, "decision_cases", ())
            ]
        }
    if evidence_id in {"EV-06", "EV-07", "EV2-08"}:
        return {"decision_effects": _dump(_decision_effects(result))}
    if evidence_id in {"EV-08", "EV2-09"}:
        return {
            "restore": _dump(result.restore),
            "redrive": _dump(getattr(result, "redrive", None)),
            "dlq_presence": _dump(getattr(result, "dlq_presence", None)),
        }
    if evidence_id == "EV2-10":
        return {"effects": _dump(_effects(result))}
    if evidence_id == "EV2-11":
        return {
            "first": _dump(getattr(result, "first_decision", None)),
            "replay": _dump(getattr(result, "replay_decision", None)),
            "comparison": _dump(getattr(result, "replay_comparison", None)),
            "effects": _dump(
                tuple(getattr(result, "first_decision_effects", ()))
                + tuple(getattr(result, "replay_decision_effects", ()))
            ),
        }
    return {"profile_evidence": evidence_id}


def _effects(result: Any) -> list[BusinessEffectSnapshot]:
    values: list[BusinessEffectSnapshot] = []
    for name in (
        "injected_effects",
        "recovered_effects",
        "committed_effects",
        "final_effects",
        "first_decision_effects",
        "replay_decision_effects",
    ):
        values.extend(getattr(result, name, ()))
    values.extend(_decision_effects(result))
    return values


def _decision_effects(result: Any) -> list[BusinessEffectSnapshot]:
    values: list[BusinessEffectSnapshot] = []
    for case in getattr(result, "decision_cases", ()):
        values.extend(case.pre_effects)
        values.extend(case.post_effects)
    return values


def _write_jsonl(writer: EvidenceBundleWriter, path: str, values: Sequence[Any]) -> None:
    if not values:
        writer.write_bytes(path, b"", "application/x-ndjson")
        return
    for value in values:
        writer.append_jsonl(path, _dump(value))


def _dump(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, AdapterResult):
        return {
            "ok": value.ok,
            "code": value.code,
            "data": dict(value.data),
            "detail": value.detail,
        }
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, Mapping):
        return {str(key): _dump(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_dump(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    return value


def _link_assertion_artifacts(
    assertions: tuple[AssertionResult, ...],
    definitions: Sequence[Any],
    artifacts: Mapping[str, EvidenceArtifact],
) -> tuple[AssertionResult, ...]:
    required = {
        item.assertion_id: tuple(item.required_evidence_ids) for item in definitions
    }
    return tuple(
        assertion.model_copy(
            update={
                "artifact_ids": tuple(
                    artifacts[evidence_id].artifact_id
                    for evidence_id in required.get(assertion.assertion_id, ())
                    if evidence_id in artifacts
                )
            }
        )
        for assertion in assertions
    )


def _link_file_evidence(writer: EvidenceBundleWriter, profile: ExecutionProfile) -> None:
    writer.link_file_evidence("EV2-01", "environment.snapshot.json")
    writer.link_file_evidence("EV2-01", "queue-topology.snapshot.json")
    writer.link_file_evidence("EV2-02", "effects.jsonl")
    writer.link_file_evidence("EV2-03", "faults.jsonl")
    writer.link_file_evidence("EV2-04", "delivery-attempts.jsonl")
    if profile in {ExecutionProfile.H03_DLQ_V2, ExecutionProfile.E03_BEFORE_V2}:
        writer.link_file_evidence("EV2-05", "terminal-failure.json")
        writer.link_file_evidence("EV2-09", "redrive-receipts.jsonl")
    else:
        writer.link_file_evidence("EV2-09", "effects.jsonl")
    if profile in {ExecutionProfile.E03_BEFORE_V2, ExecutionProfile.E03_AFTER_V2}:
        writer.link_file_evidence("EV2-10", "effects.jsonl")
    writer.link_file_evidence("EV2-12", "scenario.snapshot.yaml")
    writer.link_file_evidence("EV2-12", "target.snapshot.json")
    writer.link_file_evidence("EV2-12", "environment.snapshot.json")


def _verdict(
    assertions: tuple[AssertionResult, ...], restore_ok: bool
) -> tuple[Verdict, InconclusiveReason | None]:
    if not restore_ok:
        return Verdict.INCONCLUSIVE, InconclusiveReason.INSUFFICIENT_EVIDENCE
    if any(item.status is AssertionStatus.FAIL for item in assertions):
        return Verdict.FAIL, None
    inconclusive = [
        item for item in assertions if item.status is AssertionStatus.INCONCLUSIVE
    ]
    if inconclusive:
        reasons = {item.reason_code for item in inconclusive}
        reason = (
            InconclusiveReason.EVIDENCE_CONFLICT
            if InconclusiveReason.EVIDENCE_CONFLICT in reasons
            else InconclusiveReason.ACCESS_LIMITED
            if InconclusiveReason.ACCESS_LIMITED in reasons
            else InconclusiveReason.INSUFFICIENT_EVIDENCE
        )
        return Verdict.INCONCLUSIVE, reason
    return Verdict.PASS, None


def _summary(verdict: Verdict, restore_ok: bool) -> str:
    if not restore_ok:
        return "환경 복구를 확정하지 못해 결과를 판정할 수 없습니다."
    if verdict is Verdict.FAIL:
        return "실행한 프로필에서 하나 이상의 직접 보호조치 위반을 관찰했습니다."
    if verdict is Verdict.INCONCLUSIVE:
        return "필수 사실 일부를 평가할 수 없어 결론을 확정할 수 없습니다."
    return "실행한 프로필의 모든 assertion과 필수 증적이 확인됐습니다."
