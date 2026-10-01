"""N-02 consent-order profile executor foundation.

The full journey is composed by later user-story tasks. This foundation deliberately
performs read-only preflight only and refuses execution before any Run/subject/marker
side effect can be created.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

from engine.adapters.base import AdapterResult, AdapterSet, Clock
from engine.judges.n02 import (
    N02BypassCase,
    N02FaultFailureCase,
    N02NormalOrderCase,
    judge_n02_bypass,
    judge_n02_fault_recovery,
    judge_n02_normal_order,
    validate_n02_baseline,
)
from engine.models import (
    AssertionResult,
    AssertionStatus,
    CausalEdge,
    CausalEvent,
    ConsentFaultReceipt,
    ConsentPolicySnapshot,
    ConsentPurpose,
    ConsentStateSnapshot,
    ExecutionProfile,
    N02LaneId,
    Phase,
    Presence,
    ProcessingAttemptReceipt,
    ProtectedEffectSnapshot,
    ProtectedPathId,
    RecoveryRecord,
    RecoveryStatus,
    RunSubjectLane,
    ScenarioReadiness,
    utcnow,
)
from engine.readiness import evaluate_readiness
from engine.scenario import ScenarioDefinition


class _SystemClock:
    def now(self):
        return utcnow()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


class N02ExecutionError(RuntimeError):
    """Normalized adapter failure during the N-02 journey."""


@dataclass(frozen=True, slots=True)
class N02BypassSliceResult:
    lanes: tuple[RunSubjectLane, ...]
    baseline: tuple[ProtectedEffectSnapshot, ...]
    cases: tuple[N02BypassCase, ...]
    assertions: tuple[AssertionResult, ...]
    teardown: AdapterResult


@dataclass(frozen=True, slots=True)
class N02NormalOrderSliceResult:
    lanes: tuple[RunSubjectLane, ...]
    policy: ConsentPolicySnapshot
    commit: AdapterResult
    consent_state: ConsentStateSnapshot
    attempts: tuple[ProcessingAttemptReceipt, ...]
    effects: tuple[ProtectedEffectSnapshot, ...]
    events: tuple[CausalEvent, ...]
    edges: tuple[CausalEdge, ...]
    assertion: AssertionResult
    teardown: AdapterResult


@dataclass(frozen=True, slots=True)
class N02FaultRecoverySliceResult:
    lanes: tuple[RunSubjectLane, ...]
    fault_apply: AdapterResult
    failed_commit: AdapterResult
    fault_receipt: ConsentFaultReceipt | None
    failed_state: ConsentStateSnapshot
    failure_attempts: tuple[ProcessingAttemptReceipt, ...]
    failure_effects: tuple[ProtectedEffectSnapshot, ...]
    recovery: RecoveryRecord
    recovered_order: AssertionResult | None
    assertions: tuple[AssertionResult, AssertionResult]
    teardown: AdapterResult


_N02_REQUEST_NAMESPACE = UUID("7c5f737a-5d6f-5b9f-87ab-3de2b55c5514")


class N02Executor:
    """Own the additive N-02 profile without inheriting Spec 002 queue semantics."""

    profile = ExecutionProfile.N02_CONSENT_ORDER_V1

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

    def preflight(self, target_id: str) -> ScenarioReadiness:
        target_snapshot = None
        try:
            target_snapshot = self.adapters.target.capture_target_snapshot()
        except Exception:  # noqa: BLE001 - readiness must remain sanitized
            target_snapshot = None
        probes = [
            self.adapters.capability.probe(capability)
            for capability in self.scenario.required_capabilities
        ]
        return evaluate_readiness(
            self.scenario,
            target_id=target_id,
            registrations=self.adapters.capability.registrations,
            probe_results=probes,
            target_feature_exists=self.adapters.target.target_feature_exists(),
            target_snapshot=target_snapshot,
        )

    def execute(self, readiness: ScenarioReadiness, **_: Any):
        raise RuntimeError(
            "N-02 execution is fail-closed until the protected-processing journey is composed"
        )

    def collect_us1(self, *, run_id: UUID) -> N02BypassSliceResult:
        seed = self.adapters.n02_seed
        processing = self.adapters.n02_processing
        if seed is None or processing is None:
            raise RuntimeError("N-02 seed and processing adapters must be composed")
        seeded = seed.seed_lanes(run_id=str(run_id))
        if isinstance(seeded, AdapterResult):
            raise N02ExecutionError(f"N-02 seed failed: {seeded.code}")
        lanes = seeded
        teardown = AdapterResult(False, "N02_TEARDOWN_NOT_ATTEMPTED")
        try:
            pristine = next(
                lane for lane in lanes if lane.lane_id is N02LaneId.PRISTINE_BASELINE
            )
            pristine_subject = _subject(seed, str(run_id), pristine)
            baseline_rows = []
            for path in ProtectedPathId:
                effect = processing.read_effects(
                    path_id=path.value,
                    subject=pristine_subject,
                    phase=Phase.BASELINE.value,
                    step_id=f"capture-pristine-{path.value.casefold()}",
                )
                if isinstance(effect, AdapterResult):
                    raise N02ExecutionError(f"N-02 baseline read failed: {effect.code}")
                baseline_rows.append(effect)
            baseline = tuple(baseline_rows)
            validate_n02_baseline(baseline)

            lane_by_path = {
                ProtectedPathId.DOCUMENT_ANALYSIS: N02LaneId.DOCUMENT_BYPASS,
                ProtectedPathId.RECORDING: N02LaneId.RECORDING_BOUNDARY_PROBE,
                ProtectedPathId.AI_ASSESSMENT: N02LaneId.ASSESSMENT_BOUNDARY_PROBE,
            }
            cases = []
            for path, lane_id in lane_by_path.items():
                lane = next(item for item in lanes if item.lane_id is lane_id)
                subject = _subject(seed, str(run_id), lane)
                attempt = processing.attempt(path_id=path.value, subject=subject)
                if isinstance(attempt, AdapterResult):
                    raise N02ExecutionError(
                        f"N-02 processing attempt failed: {attempt.code}"
                    )
                effects = processing.read_effects(
                    path_id=path.value,
                    subject=subject,
                    phase=Phase.INJECTED.value,
                    step_id=f"capture-{path.value.casefold()}-effects",
                )
                if isinstance(effects, AdapterResult):
                    raise N02ExecutionError(f"N-02 effect read failed: {effects.code}")
                cases.append(
                    N02BypassCase(
                        path_id=path,
                        lane_id=lane_id,
                        attempt=attempt,
                        effects=effects,
                    )
                )
            case_tuple = tuple(cases)
            assertions = judge_n02_bypass(baseline, case_tuple)
        finally:
            teardown = seed.teardown_lanes(run_id=str(run_id), lanes=lanes)
        if not teardown.ok:
            raise N02ExecutionError(f"N-02 teardown failed: {teardown.code}")
        return N02BypassSliceResult(
            lanes=lanes,
            baseline=baseline,
            cases=case_tuple,
            assertions=assertions,
            teardown=teardown,
        )

    def collect_us2(self, *, run_id: UUID) -> N02NormalOrderSliceResult:
        seed = self.adapters.n02_seed
        consent = self.adapters.n02_consent
        processing = self.adapters.n02_processing
        causality = self.adapters.n02_causality
        if seed is None or consent is None or processing is None or causality is None:
            raise RuntimeError("N-02 US2 adapters must be composed")
        seeded = seed.seed_lanes(run_id=str(run_id))
        if isinstance(seeded, AdapterResult):
            raise N02ExecutionError(f"N-02 seed failed: {seeded.code}")
        lanes = seeded
        teardown = AdapterResult(False, "N02_TEARDOWN_NOT_ATTEMPTED")
        attempts: tuple[ProcessingAttemptReceipt, ...] = ()
        effects: tuple[ProtectedEffectSnapshot, ...] = ()
        events: tuple[CausalEvent, ...] = ()
        edges: tuple[CausalEdge, ...] = ()
        try:
            lane = next(item for item in lanes if item.lane_id is N02LaneId.NORMAL_ORDER)
            subject = _subject(seed, str(run_id), lane)
            policy = consent.read_policy(subject=subject)
            if isinstance(policy, AdapterResult):
                raise N02ExecutionError(f"N-02 policy read failed: {policy.code}")
            request_id = str(uuid5(_N02_REQUEST_NAMESPACE, f"{run_id}:normal-consent"))
            trace_id = f"controlproof:{run_id}:{lane.lane_id.value}:{lane.subject_ref}"
            commit = consent.commit(
                subject=subject,
                policy=policy,
                request_id=request_id,
                trace_id=trace_id,
            )
            state = consent.read_state(
                subject=subject,
                phase=Phase.INJECTED.value,
                step_id="capture-normal-consent",
            )
            if isinstance(state, AdapterResult):
                raise N02ExecutionError(f"N-02 consent state read failed: {state.code}")
            if _durable_consent_matches(policy, state):
                attempt_rows = []
                effect_rows = []
                for path in ProtectedPathId:
                    attempt = processing.attempt(path_id=path.value, subject=subject)
                    if isinstance(attempt, AdapterResult):
                        raise N02ExecutionError(
                            f"N-02 normal processing attempt failed: {attempt.code}"
                        )
                    attempt_rows.append(attempt)
                    effect = processing.read_effects(
                        path_id=path.value,
                        subject=subject,
                        phase=Phase.INJECTED.value,
                        step_id=f"capture-normal-{path.value.casefold()}-effects",
                    )
                    if isinstance(effect, AdapterResult):
                        raise N02ExecutionError(
                            f"N-02 normal effect read failed: {effect.code}"
                        )
                    effect_rows.append(effect)
                attempts = tuple(attempt_rows)
                effects = tuple(effect_rows)
                receipts: tuple[dict[str, Any], ...] = ()
                if self.adapters.n02_observer is not None:
                    observed = self.adapters.n02_observer.read_processing_receipts(
                        run_id=str(run_id),
                        lane_id=lane.lane_id.value,
                        subject_ref=lane.subject_ref,
                    )
                    if observed.ok:
                        receipts = tuple(observed.data.get("receipts", ()))
                if hasattr(causality, "capture_normal_order"):
                    captured = causality.capture_normal_order(
                        subject=subject,
                        policy=policy,
                        consent_state=state,
                        attempts=attempts,
                        effects=effects,
                        receipts=receipts,
                    )
                    if isinstance(captured, AdapterResult) and not captured.ok:
                        events, edges = (), ()
                graph = causality.read_graph(subject=subject)
                if not isinstance(graph, AdapterResult):
                    events, edges = graph
            normal_case = N02NormalOrderCase(
                policy=policy,
                consent_state=state,
                attempts=attempts,
                effects=effects,
                events=events,
                edges=edges,
            )
            assertion = judge_n02_normal_order(normal_case)
        finally:
            teardown = seed.teardown_lanes(run_id=str(run_id), lanes=lanes)
        if not teardown.ok:
            raise N02ExecutionError(f"N-02 teardown failed: {teardown.code}")
        return N02NormalOrderSliceResult(
            lanes=lanes,
            policy=policy,
            commit=commit,
            consent_state=state,
            attempts=attempts,
            effects=effects,
            events=events,
            edges=edges,
            assertion=assertion,
            teardown=teardown,
        )

    def collect_us3(self, *, run_id: UUID) -> N02FaultRecoverySliceResult:
        seed = self.adapters.n02_seed
        consent = self.adapters.n02_consent
        processing = self.adapters.n02_processing
        causality = self.adapters.n02_causality
        fault = self.adapters.n02_fault
        if any(item is None for item in (seed, consent, processing, causality, fault)):
            raise RuntimeError("N-02 US3 adapters must be composed")
        seeded = seed.seed_lanes(run_id=str(run_id))
        if isinstance(seeded, AdapterResult):
            raise N02ExecutionError(f"N-02 seed failed: {seeded.code}")
        lanes = seeded
        teardown = AdapterResult(False, "N02_TEARDOWN_NOT_ATTEMPTED")
        restore = AdapterResult(False, "CONSENT_FAULT_RESTORE_NOT_ATTEMPTED")
        fault_apply = AdapterResult(False, "CONSENT_FAULT_NOT_APPLIED")
        overlay_cleanup_succeeded = True
        active_overlays: set[ProtectedPathId] = set()
        subject: dict[str, Any] = {}
        try:
            lane = next(
                item for item in lanes if item.lane_id is N02LaneId.CONSENT_FAULT_RECOVERY
            )
            subject = _subject(seed, str(run_id), lane)
            policy = consent.read_policy(subject=subject)
            if isinstance(policy, AdapterResult):
                raise N02ExecutionError(f"N-02 policy read failed: {policy.code}")
            fault_apply = fault.apply_consent_fault(
                run_id=str(run_id),
                subject=subject,
                expires_at=self.clock.now() + timedelta(minutes=5),
            )
            if not fault_apply.ok:
                raise N02ExecutionError(f"N-02 fault apply failed: {fault_apply.code}")
            failed_commit = consent.commit(
                subject=subject,
                policy=policy,
                request_id=str(uuid5(_N02_REQUEST_NAMESPACE, f"{run_id}:faulted-consent")),
                trace_id=f"controlproof:{run_id}:{lane.lane_id.value}:{lane.subject_ref}",
            )
            receipt_value = fault.read_consent_fault_receipt(
                run_id=str(run_id), subject=subject
            )
            fault_receipt = (
                None if isinstance(receipt_value, AdapterResult) else receipt_value
            )
            failed_state_value = consent.read_state(
                subject=subject,
                phase=Phase.INJECTED.value,
                step_id="capture-failed-consent-effects",
            )
            if isinstance(failed_state_value, AdapterResult):
                raise N02ExecutionError(
                    f"N-02 failed-consent state read failed: {failed_state_value.code}"
                )
            failed_state = failed_state_value

            restore = fault.restore_consent_fault(run_id=str(run_id), subject=subject)
            failure_attempts: tuple[ProcessingAttemptReceipt, ...] = ()
            failure_effects: tuple[ProtectedEffectSnapshot, ...] = ()
            recovered_order: AssertionResult | None = None
            recovered_state = failed_state
            retry_commit = AdapterResult(False, "RECOVERY_RETRY_NOT_ATTEMPTED")
            if restore.ok:
                attempt_rows = []
                effect_rows = []
                for path in ProtectedPathId:
                    overlay = seed.apply_probe_overlay(
                        subject=subject, path_id=path.value
                    )
                    if not overlay.ok:
                        raise N02ExecutionError(
                            f"N-02 overlay apply failed: {overlay.code}"
                        )
                    active_overlays.add(path)
                    try:
                        attempt = processing.attempt(path_id=path.value, subject=subject)
                        if isinstance(attempt, AdapterResult):
                            raise N02ExecutionError(
                                f"N-02 failed-consent attempt failed: {attempt.code}"
                            )
                        attempt_rows.append(attempt)
                        effect = processing.read_effects(
                            path_id=path.value,
                            subject=subject,
                            phase=Phase.RECOVERED.value,
                            step_id=f"capture-failed-{path.value.casefold()}-effects",
                        )
                        if isinstance(effect, AdapterResult):
                            raise N02ExecutionError(
                                f"N-02 failed-consent effect read failed: {effect.code}"
                            )
                        effect_rows.append(effect)
                    finally:
                        removed = seed.remove_probe_overlay(
                            subject=subject, path_id=path.value
                        )
                        overlay_cleanup_succeeded &= removed.ok
                        if removed.ok:
                            active_overlays.discard(path)
                failure_attempts = tuple(attempt_rows)
                failure_effects = tuple(effect_rows)
                safe_state = consent.read_state(
                    subject=subject,
                    phase=Phase.RECOVERED.value,
                    step_id="verify-pristine-before-retry",
                )
                if isinstance(safe_state, AdapterResult):
                    raise N02ExecutionError(
                        f"N-02 safe-state read failed: {safe_state.code}"
                    )
                if not (
                    safe_state.source_status is Presence.ABSENT
                    and safe_state.invitation_status == "identity_verified"
                    and not safe_state.consent_record_ids
                    and not safe_state.consented_state_change_ids
                    and not safe_state.consent_completed_event_ids
                ):
                    raise N02ExecutionError(
                        "N-02 safe-state verification failed before retry"
                    )
                retry_commit = consent.commit(
                    subject=subject,
                    policy=policy,
                    request_id=str(
                        uuid5(_N02_REQUEST_NAMESPACE, f"{run_id}:recovered-consent")
                    ),
                    trace_id=(
                        f"controlproof:{run_id}:{lane.lane_id.value}:{lane.subject_ref}"
                    ),
                )
                recovered_state_value = consent.read_state(
                    subject=subject,
                    phase=Phase.RECOVERED.value,
                    step_id="capture-recovered-consent",
                )
                if isinstance(recovered_state_value, AdapterResult):
                    raise N02ExecutionError(
                        f"N-02 recovered state read failed: {recovered_state_value.code}"
                    )
                recovered_state = recovered_state_value
                if _durable_consent_matches(policy, recovered_state):
                    recovered_attempts, recovered_effects = _collect_processing(
                        processing,
                        subject,
                        phase=Phase.RECOVERED,
                        step_prefix="capture-recovered",
                    )
                    receipts = _read_receipts(self.adapters, run_id, lane)
                    if hasattr(causality, "capture_normal_order"):
                        causality.capture_normal_order(
                            subject=subject,
                            policy=policy,
                            consent_state=recovered_state,
                            attempts=recovered_attempts,
                            effects=recovered_effects,
                            receipts=receipts,
                        )
                    graph = causality.read_graph(subject=subject)
                    events, edges = ((), ()) if isinstance(graph, AdapterResult) else graph
                    recovered_order = judge_n02_normal_order(
                        N02NormalOrderCase(
                            policy=policy,
                            consent_state=recovered_state,
                            attempts=recovered_attempts,
                            effects=recovered_effects,
                            events=events,
                            edges=edges,
                        )
                    )

            failed_zero = (
                failed_state.source_status is Presence.ABSENT
                and not failed_state.consent_record_ids
                and not failed_state.consented_state_change_ids
                and not failed_state.consent_completed_event_ids
                and all(not item.new_effect_ids for item in failure_effects)
            )
            order_proven = (
                None
                if recovered_order is None
                or recovered_order.status is AssertionStatus.INCONCLUSIVE
                else recovered_order.status is AssertionStatus.PASS
            )
            restore_data = restore.data
            recovered_exactly_once = (
                recovered_state.active_consent_count == 1
                and len(recovered_state.consent_completed_event_ids) == 1
            )
            recovery_succeeded = (
                restore.ok
                and overlay_cleanup_succeeded
                and failed_zero
                and retry_commit.ok
                and recovered_exactly_once
                and order_proven is True
            )
            recovery = RecoveryRecord(
                run_id=run_id,
                lane_id=N02LaneId.CONSENT_FAULT_RECOVERY,
                subject_ref=lane.subject_ref,
                marker_removed=bool(restore_data.get("marker_removed")),
                consumed_token_removed=bool(
                    restore_data.get("consumed_token_removed")
                ),
                hook_inactive=bool(restore_data.get("hook_inactive")),
                failed_request_effects_zero=failed_zero if restore.ok else None,
                normal_retry_succeeded=(
                    _durable_consent_matches(policy, recovered_state)
                    if restore.ok
                    else None
                ),
                logical_consent_count=(
                    recovered_state.active_consent_count if restore.ok else None
                ),
                consent_completed_event_count=(
                    len(recovered_state.consent_completed_event_ids)
                    if restore.ok
                    else None
                ),
                processing_order_proven=order_proven,
                restore_status=(
                    RecoveryStatus.SUCCEEDED
                    if recovery_succeeded
                    else RecoveryStatus.FAILED
                ),
                manual_cleanup_required=not recovery_succeeded,
            )
            failure_case = N02FaultFailureCase(
                failed_commit=failed_commit,
                receipt=fault_receipt,
                consent_state=failed_state,
                attempts=failure_attempts,
                effects=failure_effects,
                overlay_cleanup_succeeded=overlay_cleanup_succeeded,
            )
            assertions = judge_n02_fault_recovery(
                failure_case, recovery, recovered_order
            )
        finally:
            for path in tuple(active_overlays):
                removed = seed.remove_probe_overlay(subject=subject, path_id=path.value)
                overlay_cleanup_succeeded &= removed.ok
            if fault_apply.ok and not restore.ok:
                restore = fault.restore_consent_fault(run_id=str(run_id), subject=subject)
            teardown = seed.teardown_lanes(run_id=str(run_id), lanes=lanes)
        if not teardown.ok:
            raise N02ExecutionError(f"N-02 teardown failed: {teardown.code}")
        return N02FaultRecoverySliceResult(
            lanes=lanes,
            fault_apply=fault_apply,
            failed_commit=failed_commit,
            fault_receipt=fault_receipt,
            failed_state=failed_state,
            failure_attempts=failure_attempts,
            failure_effects=failure_effects,
            recovery=recovery,
            recovered_order=recovered_order,
            assertions=assertions,
            teardown=teardown,
        )


def _subject(seed: Any, run_id: str, lane: RunSubjectLane) -> dict[str, Any]:
    if hasattr(seed, "subject_for"):
        return seed.subject_for(run_id=run_id, lane_id=lane.lane_id)
    return lane.model_dump(mode="json") | {"allowed_fixture_effect_ids": []}


def _durable_consent_matches(
    policy: ConsentPolicySnapshot, state: ConsentStateSnapshot
) -> bool:
    return (
        state.source_status is Presence.PRESENT
        and state.invitation_status == "consented"
        and state.active_consent_count == 1
        and state.consent_policy_versions == (policy.policy_version,)
        and state.consent_content_digests == (policy.content_digest,)
        and len(state.accepted_purpose_sets) == 1
        and set(state.accepted_purpose_sets[0]) == set(ConsentPurpose)
        and len(state.consented_state_change_ids) == 1
        and len(state.consent_completed_event_ids) == 1
    )


def _collect_processing(processing, subject, *, phase: Phase, step_prefix: str):
    attempts = []
    effects = []
    for path in ProtectedPathId:
        attempt = processing.attempt(path_id=path.value, subject=subject)
        if isinstance(attempt, AdapterResult):
            raise N02ExecutionError(f"N-02 processing attempt failed: {attempt.code}")
        attempts.append(attempt)
        effect = processing.read_effects(
            path_id=path.value,
            subject=subject,
            phase=phase.value,
            step_id=f"{step_prefix}-{path.value.casefold()}-effects",
        )
        if isinstance(effect, AdapterResult):
            raise N02ExecutionError(f"N-02 effect read failed: {effect.code}")
        effects.append(effect)
    return tuple(attempts), tuple(effects)


def _read_receipts(adapters: AdapterSet, run_id: UUID, lane: RunSubjectLane):
    if adapters.n02_observer is None:
        return ()
    result = adapters.n02_observer.read_processing_receipts(
        run_id=str(run_id), lane_id=lane.lane_id.value, subject_ref=lane.subject_ref
    )
    return tuple(result.data.get("receipts", ())) if result.ok else ()
