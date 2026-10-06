"""N-02 consent-order profile executor and six-lane evidence journey."""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from datetime import timedelta
from pathlib import Path
from typing import Any, ClassVar
from uuid import UUID, uuid4, uuid5

from engine.adapters.base import AdapterResult, AdapterSet, Clock
from engine.evidence import SPEC003_REQUIRED_FILE_LINKS, EvidenceBundleWriter, verify_bundle
from engine.judges.n02 import (
    N02BypassCase,
    N02FaultFailureCase,
    N02NormalOrderCase,
    judge_n02_bypass,
    judge_n02_fault_recovery,
    judge_n02_normal_order,
    judge_n02_run,
    validate_n02_baseline,
)
from engine.lifecycle import RestoreBlockStore, TargetSubjectLock
from engine.models import (
    SPEC003_UNVERIFIED_SCOPE,
    AssertionResult,
    AssertionStatus,
    AwsDeploymentStatus,
    CausalEdge,
    CausalEvent,
    ConsentFaultReceipt,
    ConsentPolicySnapshot,
    ConsentPurpose,
    ConsentStateSnapshot,
    EnvironmentKind,
    ExecutionProfile,
    N02LaneId,
    Phase,
    Presence,
    ProcessingAttemptReceipt,
    ProtectedEffectSnapshot,
    ProtectedPathId,
    ReadinessStatus,
    RecoveryRecord,
    RecoveryStatus,
    Run,
    RunState,
    RunSubjectLane,
    ScenarioReadiness,
    TargetEnvironmentSnapshot,
    canonical_json_bytes,
    sha256_bytes,
    utcnow,
)
from engine.readiness import evaluate_readiness
from engine.retest import RetestError, finalize_n02_retest_records
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
_N02_BLOCK_SUBJECT = "n02-consent-order"


class _SharedSeed:
    """Give the three collectors one lane set and postpone their local teardowns."""

    def __init__(self, delegate: Any) -> None:
        self.delegate = delegate
        self.lanes: tuple[RunSubjectLane, ...] | None = None

    def seed_lanes(self, *, run_id: str):
        if self.lanes is None:
            result = self.delegate.seed_lanes(run_id=run_id)
            if isinstance(result, AdapterResult):
                return result
            self.lanes = result
        return self.lanes

    def teardown_lanes(self, *, run_id: str, lanes: tuple[RunSubjectLane, ...]):
        return AdapterResult(True, "N02_TEARDOWN_DEFERRED")

    def __getattr__(self, name: str):
        return getattr(self.delegate, name)


class N02RunDeadlineExceeded(N02ExecutionError):
    """The snapshot Run deadline expired before an observation became stable."""


class _Stabilizer:
    """Apply the scenario snapshot's polling policy to one N-02 observation.

    A read is accepted only after ``stability_consecutive`` consecutive reads with the same
    digest spanning at least ``stability_seconds``, sleeping ``poll_seconds`` between reads.
    A single immediate read is never treated as proof that an asynchronous effect is absent.
    """

    def __init__(self, timing: Any, clock: Any, deadline: Any) -> None:
        self.timing = timing
        self.clock = clock
        self.deadline = deadline

    def read(self, fetch: Any, key: Any, label: str) -> Any:
        value = fetch()
        marker = key(value)
        if marker is None:
            return value
        streak = 1
        window_started = self.clock.now()
        while True:
            elapsed = (self.clock.now() - window_started).total_seconds()
            if (
                streak >= self.timing.stability_consecutive
                and elapsed >= self.timing.stability_seconds
            ):
                return value
            if self.deadline is not None and self.clock.now() >= self.deadline:
                raise N02RunDeadlineExceeded(f"N02_RUN_DEADLINE_EXCEEDED:{label}")
            self.clock.sleep(self.timing.poll_seconds)
            current = fetch()
            current_marker = key(current)
            if current_marker is None:
                return current
            if current_marker == marker:
                streak += 1
            else:
                streak = 1
                window_started = self.clock.now()
            value, marker = current, current_marker


def _digest_key(value: Any) -> Any:
    return None if isinstance(value, AdapterResult) else getattr(value, "state_digest", None)


def _receipts_key(value: Any) -> Any:
    if not isinstance(value, AdapterResult) or not value.ok:
        return None
    rows = value.data.get("receipts", ()) if isinstance(value.data, dict) else ()
    return tuple(sorted(str(row.get("receipt_id")) for row in rows if isinstance(row, dict)))


class _StableReads:
    """Adapter proxy: snapshot-reading methods go through the stabilizer; others pass through."""

    _KEYS: ClassVar[dict[str, Any]] = {
        "read_effects": _digest_key,
        "read_state": _digest_key,
        "read_processing_receipts": _receipts_key,
    }

    def __init__(self, delegate: Any, stabilizer: _Stabilizer) -> None:
        self._delegate = delegate
        self._stabilizer = stabilizer

    def __getattr__(self, name: str) -> Any:
        attribute = getattr(self._delegate, name)
        key = self._KEYS.get(name)
        if key is None or not callable(attribute):
            return attribute

        def stable(*args: Any, **kwargs: Any) -> Any:
            return self._stabilizer.read(lambda: attribute(*args, **kwargs), key, name)

        return stable


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
        if readiness.status is not ReadinessStatus.READY or readiness.target_snapshot is None:
            raise RuntimeError(f"Run refused: {readiness.status.value}")
        if retest_records is not None:
            link = retest_records.get("link", {})
            if (
                parent_run_id is None
                or run_id is None
                or link.get("parent_run_id") != str(parent_run_id)
                or link.get("child_run_id") != str(run_id)
            ):
                raise RetestError("N-02 child Run requires matching parent and child identities")
        if self.adapters.n02_seed is None or self.adapters.n02_processing is None:
            raise RuntimeError("N-02 adapters are not composed")
        blocks = RestoreBlockStore(self.run_root)
        if blocks.blocked(readiness.target_id, _N02_BLOCK_SUBJECT):
            raise RuntimeError("target is blocked after an N-02 restore failure")
        active_run_id = run_id or uuid4()
        started_at = self.clock.now()
        shared_seed = _SharedSeed(self.adapters.n02_seed)
        stabilizer = _Stabilizer(
            self.scenario.timing_policy,
            self.clock,
            started_at
            + timedelta(seconds=float(self.scenario.timing_policy.run_deadline_seconds or 0)),
        )
        collector = N02Executor(
            self.scenario,
            replace(
                self.adapters,
                n02_seed=shared_seed,
                n02_processing=_StableReads(self.adapters.n02_processing, stabilizer),
                n02_consent=_StableReads(self.adapters.n02_consent, stabilizer),
                n02_observer=(
                    None
                    if self.adapters.n02_observer is None
                    else _StableReads(self.adapters.n02_observer, stabilizer)
                ),
            ),
            self.run_root,
            clock=self.clock,
        )
        fault_stage_started = False
        with TargetSubjectLock(self.run_root, readiness.target_id, _N02_BLOCK_SUBJECT):
            if blocks.blocked(readiness.target_id, _N02_BLOCK_SUBJECT):
                raise RuntimeError("target is blocked after an N-02 restore failure")
            try:
                us1 = collector.collect_us1(run_id=active_run_id)
                us2 = collector.collect_us2(run_id=active_run_id)
                fault_stage_started = True
                us3 = collector.collect_us3(run_id=active_run_id)
                recovered = us3.recovery.restore_status is RecoveryStatus.SUCCEEDED
                teardown = (
                    self.adapters.n02_seed.teardown_lanes(
                        run_id=str(active_run_id), lanes=us1.lanes
                    )
                    if recovered
                    else AdapterResult(False, "N02_TEARDOWN_HELD_FOR_MANUAL_CLEANUP")
                )
            except Exception:
                # A collector may fail after creating lanes or applying the fault.
                # Never silently discard the only cleanup obligation.
                cleanup_ok = not fault_stage_started
                if fault_stage_started and shared_seed.lanes and self.adapters.n02_fault:
                    try:
                        lane = next(
                            item for item in shared_seed.lanes
                            if item.lane_id is N02LaneId.CONSENT_FAULT_RECOVERY
                        )
                        subject = _subject(shared_seed, str(active_run_id), lane)
                        cleanup_ok = self.adapters.n02_fault.restore_consent_fault(
                            run_id=str(active_run_id), subject=subject
                        ).ok
                    except Exception:  # noqa: BLE001 - uncertain restore remains blocked
                        cleanup_ok = False
                if shared_seed.lanes and cleanup_ok:
                    try:
                        cleanup_ok = self.adapters.n02_seed.teardown_lanes(
                            run_id=str(active_run_id), lanes=shared_seed.lanes
                        ).ok
                    except Exception:  # noqa: BLE001 - uncertain teardown remains blocked
                        cleanup_ok = False
                if not cleanup_ok:
                    blocks.block_run_id(
                        readiness.target_id, _N02_BLOCK_SUBJECT, active_run_id
                    )
                raise
        ended_at = self.clock.now()
        restore_ok = recovered and teardown.ok
        state = RunState.COMPLETED if restore_ok else RunState.RESTORE_FAILED
        environment_raw = self.adapters.environment.capture_environment()
        environment = TargetEnvironmentSnapshot.model_validate(
            environment_raw.model_dump(mode="json", exclude={"snapshot_digest"})
            | {"unverified_scope": sorted(SPEC003_UNVERIFIED_SCOPE)}
        )
        if (
            retest_records is not None
            and retest_records["diff"]["environment"]["after_digest"]
            != environment.snapshot_digest
        ):
            raise RetestError("N-02 child environment changed after retest preparation")
        paths = {"paths": [item.model_dump(mode="json") for item in self.adapters.n02_processing.paths()]}
        lanes = {"lanes": [item.model_dump(mode="json") for item in us1.lanes]}
        policy = {
            "policy": us2.policy.model_dump(mode="json"),
            "consent": us2.consent_state.model_dump(mode="json"),
            "normal_commit": _commit_evidence(us2.commit),
            "failed_request_id": us3.failed_commit.data.get("request_id"),
            "failed_commit": _commit_evidence(us3.failed_commit),
            "failed_state": us3.failed_state.model_dump(mode="json"),
        }
        observer_rows = _collect_n02_observer_rows(
            self.adapters.n02_observer, active_run_id, us1.lanes
        )
        if retest_records is not None:
            finalize_n02_retest_records(
                retest_records,
                child_run_id=active_run_id,
                child_lanes=us1.lanes,
                child_paths=paths,
                child_policy=policy["policy"],
            )
        target = readiness.target_snapshot
        snapshot = self.scenario.snapshot()
        run = Run(
            run_id=active_run_id,
            scenario_id=self.scenario.scenario_id,
            scenario_version=self.scenario.version,
            scenario_digest=snapshot.digest,
            target_id=readiness.target_id,
            target_version=str(target.target_version),
            model_fixture_id=target.model_fixture_id,
            model_fixture_digest=target.model_fixture_digest,
            state=state,
            started_at=started_at,
            ended_at=ended_at,
            seed_kind="n02_six_lane_v1",
            fault_kind="consent_atomic_fault_v1",
            parent_run_id=parent_run_id,
            operator_id=operator_id,
            label=label,
            fault_ever_applied=us3.fault_apply.ok,
            manual_cleanup_required=not restore_ok,
            execution_profile=self.profile,
            environment_kind=EnvironmentKind.LOCAL_EMULATED,
            aws_deployment_status=AwsDeploymentStatus.NOT_RUN,
            environment_snapshot_digest=environment.snapshot_digest,
            lane_manifest_digest=sha256_bytes(canonical_json_bytes(lanes)),
            path_capability_digest=sha256_bytes(canonical_json_bytes(paths)),
            policy_snapshot_digest=sha256_bytes(canonical_json_bytes(policy)),
            unverified_scope=tuple(sorted(SPEC003_UNVERIFIED_SCOPE)),
        )
        if not restore_ok:
            blocks.block(readiness.target_id, _N02_BLOCK_SUBJECT, run)
        assertions = (*us1.assertions, us2.assertion, *us3.assertions)
        judgement = judge_n02_run(
            run_id=active_run_id,
            assertion_results=assertions,
            run_state=state,
            baseline_valid=True,
            bundle_verified=True,
            decided_at=ended_at,
        )
        writer = EvidenceBundleWriter(self.run_root, run)
        for name, value in (
            ("run.json", run.model_dump(mode="json")),
            ("scenario.snapshot.yaml", snapshot.model_dump(mode="json")),
            ("target.snapshot.json", target.model_dump(mode="json")),
            ("environment.snapshot.json", environment.model_dump(mode="json")),
            ("subjects.json", [item.model_dump(mode="json") for item in us1.lanes]),
            ("assertions.json", [item.model_dump(mode="json") for item in judgement.assertion_results]),
            ("judgement.json", judgement.model_dump(mode="json")),
            ("n02-capabilities.json", paths),
            ("n02-lanes.json", lanes),
            ("policy-and-consent.json", policy),
            ("recovery.json", us3.recovery.model_dump(mode="json")),
        ):
            writer.write_json(name, value, redact_first=False)
        _write_n02_rows(writer, us1, us2, us3, observer_rows)
        if observer_rows:
            writer.link_file_evidence("EV3-05", "observations.jsonl")
        if retest_records is not None:
            writer.write_json("retest-link.json", retest_records["link"], redact_first=False)
            writer.write_json("retest-diff.json", retest_records["diff"], redact_first=False)
            writer.link_file_evidence("EV3-10", "retest-link.json")
            writer.link_file_evidence("EV3-10", "retest-diff.json")
        for evidence_id, files in SPEC003_REQUIRED_FILE_LINKS.items():
            for name in sorted(files):
                writer.link_file_evidence(evidence_id, name)
        writer.link_intrinsic_evidence("EV3-10", "sealed-manifest")
        writer.seal()
        verified = verify_bundle(writer.directory)
        if verified["bundle_status"] != "VERIFIED":
            raise N02ExecutionError("N-02 sealed bundle failed verification")
        return run, judgement, writer.directory

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
                expires_at=self.clock.now()
                + timedelta(seconds=float(self.scenario.timing_policy.fault_ttl_seconds or 0)),
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
            safe_state_confirmed: bool | None = None
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
                safe_state_confirmed = True
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
            # Restore safety alone decides RESTORE_FAILED and the block (FR-032, ID-003-14);
            # an unproven or failed retry is an A7 result, not an unsafe target.
            restore_safe = (
                restore.ok
                and overlay_cleanup_succeeded
                and safe_state_confirmed is True
                and all(
                    bool(restore_data.get(name))
                    for name in ("marker_removed", "consumed_token_removed", "hook_inactive")
                )
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
                condition_cleanup_succeeded=restore.ok and overlay_cleanup_succeeded,
                safe_state_confirmed=safe_state_confirmed,
                retry_commit_code=retry_commit.code,
                retry_target_reason_code=retry_commit.data.get("target_reason_code"),
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
                    RecoveryStatus.SUCCEEDED if restore_safe else RecoveryStatus.FAILED
                ),
                manual_cleanup_required=not restore_safe,
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


def _write_n02_rows(
    writer: EvidenceBundleWriter,
    us1: N02BypassSliceResult,
    us2: N02NormalOrderSliceResult,
    us3: N02FaultRecoverySliceResult,
    observer_rows: tuple[dict[str, str], ...] = (),
) -> None:
    """Write every canonical stream, including legitimately empty streams."""
    streams = {
        "faults.jsonl": [],
        "observations.jsonl": list(observer_rows),
        "baseline-effects.jsonl": list(us1.baseline),
        "bypass-attempts.jsonl": [
            *(case.attempt for case in us1.cases),
            *us2.attempts,
            *us3.failure_attempts,
        ],
        "protected-effects.jsonl": [
            *(case.effects for case in us1.cases),
            *us2.effects,
            *us3.failure_effects,
        ],
        "causal-events.jsonl": list(us2.events),
        "causal-edges.jsonl": list(us2.edges),
        "fault-receipts.jsonl": [us3.fault_receipt] if us3.fault_receipt else [],
    }
    for name, rows in streams.items():
        if not rows:
            writer.write_bytes(name, b"", "application/x-ndjson")
            continue
        for row in rows:
            writer.append_jsonl(
                name, row.model_dump(mode="json") if hasattr(row, "model_dump") else row
            )


def _commit_evidence(result: AdapterResult) -> dict[str, Any]:
    return {
        "code": result.code,
        "ok": result.ok,
        "request_id": result.data.get("request_id"),
        "status_code": result.data.get("status_code"),
        "target_reason_code": result.data.get("target_reason_code"),
    }


def _collect_n02_observer_rows(
    observer: Any, run_id: UUID, lanes: tuple[RunSubjectLane, ...]
) -> tuple[dict[str, str], ...]:
    if observer is None:
        return ()
    rows: list[dict[str, str]] = []
    for lane in lanes:
        observed = observer.read_processing_receipts(
            run_id=str(run_id),
            lane_id=lane.lane_id.value,
            subject_ref=lane.subject_ref,
        )
        if not observed.ok:
            continue
        for item in observed.data.get("receipts", ()):
            if not isinstance(item, dict):
                continue
            try:
                if (
                    item.get("run_id") != str(run_id)
                    or item.get("lane_id") != lane.lane_id.value
                    or item.get("subject_ref") != lane.subject_ref
                    or item.get("path_id") not in {path.value for path in ProtectedPathId}
                    or item.get("boundary") not in {
                        "ANALYSIS_HANDLER_ENTERED",
                        "INTERVIEW_SESSION_CREATED",
                        "INTERVIEW_SESSION_STARTED",
                        "RECORDING_CONFIRMED",
                        "REPORT_HANDLER_ENTERED",
                        "REPORT_ASSESSMENT_STARTED",
                        "REPORT_ASSESSMENT_REFUSED",
                    }
                ):
                    continue
                receipt_id = str(UUID(str(item["receipt_id"])))
                event_id = str(UUID(str(item["request_or_event_id"])))
                observed_at = str(item["observed_at"])
                trace_digest = str(item["trace_id_digest"])
                if len(trace_digest) != 64 or any(c not in "0123456789abcdef" for c in trace_digest):
                    continue
            except (KeyError, TypeError, ValueError):
                continue
            rows.append({
                "schema_version": "controlproof.whyyou-processing-receipt.v1",
                "receipt_id": receipt_id,
                "run_id": str(run_id),
                "lane_id": lane.lane_id.value,
                "subject_ref": lane.subject_ref,
                "path_id": str(item["path_id"]),
                "boundary": str(item["boundary"]),
                "request_or_event_id": event_id,
                "trace_id_digest": trace_digest,
                "observed_at": observed_at,
            })
    return tuple(rows)


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
