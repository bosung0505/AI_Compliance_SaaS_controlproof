"""Synchronous H-03 orchestration with durable checkpoints and mandatory restore."""

from __future__ import annotations

import time
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from engine.adapters.base import AdapterResult, AdapterSet, Clock
from engine.evidence import EvidenceBundleWriter
from engine.judge import judge_h03
from engine.lifecycle import RestoreBlockStore, TargetSubjectLock, transition
from engine.models import (
    EvidenceArtifact,
    Observation,
    Phase,
    Presence,
    Run,
    RunState,
    ScenarioReadiness,
    Source,
    utcnow,
)
from engine.readiness import evaluate_readiness
from engine.scenario import ScenarioDefinition


class SystemClock:
    def now(self):
        return utcnow()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


class RunRefused(RuntimeError):
    def __init__(self, readiness: ScenarioReadiness) -> None:
        super().__init__(f"Run refused: {readiness.status}")
        self.readiness = readiness


class RunOrchestrator:
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
        self.clock = clock or SystemClock()
        self.blocks = RestoreBlockStore(self.run_root)

    def preflight(self, target_id: str) -> ScenarioReadiness:
        target_snapshot = None
        try:
            target_snapshot = self.adapters.target.capture_target_snapshot()
        except Exception as exc:  # noqa: BLE001 - preserve sanitized adapter diagnostic
            target_snapshot = getattr(exc, "diagnostic", None)
        target_exists = self.adapters.target.target_feature_exists()
        probes = [
            self.adapters.capability.probe(capability)
            for capability in self.scenario.required_capabilities
        ]
        return evaluate_readiness(
            self.scenario,
            target_id=target_id,
            registrations=self.adapters.capability.registrations,
            probe_results=probes,
            target_feature_exists=target_exists,
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
    ) -> tuple[Run, Any, Path]:
        if readiness.status.value != "READY":
            raise RunRefused(readiness)
        snapshot = self.scenario.snapshot()
        target = readiness.target_snapshot
        if target is None:
            raise RunRefused(readiness)
        subject_ref = "candidate-01"
        if self.blocks.blocked(readiness.target_id, subject_ref):
            raise RuntimeError("target+subject is blocked after a restore failure")
        run = Run(
            run_id=run_id or uuid4(),
            scenario_id=self.scenario.scenario_id,
            scenario_version=self.scenario.version,
            scenario_digest=snapshot.digest,
            target_id=readiness.target_id,
            target_version=str(target.target_version),
            model_fixture_id=target.model_fixture_id,
            model_fixture_digest=target.model_fixture_digest,
            parent_run_id=parent_run_id,
            operator_id=operator_id,
            label=label,
        )
        writer = EvidenceBundleWriter(self.run_root, run)
        observations: list[Observation] = []
        artifacts: list[EvidenceArtifact] = []
        subject: dict[str, Any] = {}
        execution_error: BaseException | None = None
        restored = False

        writer.write_json("run.json", run.model_dump(mode="json"))
        writer.write_json(
            "scenario.snapshot.yaml", snapshot.model_dump(mode="json"), redact_first=False
        )
        writer.write_json(
            "target.snapshot.json", target.model_dump(mode="json"), redact_first=False
        )
        artifacts.append(
            writer.collect_json_artifact(
                subject_ref=subject_ref,
                phase=Phase.BASELINE,
                step_id="capture-baseline",
                attempt=1,
                evidence_requirement_ids=("EV-09",),
                artifact_type="VERSION_SNAPSHOT",
                source_locator={"target_id": readiness.target_id},
                content={
                    "scenario_digest": snapshot.digest,
                    "target_version": target.target_version,
                    "model_fixture_id": target.model_fixture_id,
                    "model_fixture_digest": target.model_fixture_digest,
                },
            )
        )
        lock = TargetSubjectLock(self.run_root, readiness.target_id, subject_ref)
        try:
            with lock:
                run = transition(run, RunState.RUNNING)
                writer.run = run
                writer.write_json("run.json", run.model_dump(mode="json"))
                seeded = self.adapters.seed.seed(run_id=str(run.run_id), subject_ref=subject_ref)
                _require(seeded, "seed")
                subject = dict(seeded.data)
                writer.write_json("subjects.json", [subject])

                baseline = self.adapters.state.snapshot(subject=subject, phase="BASELINE")
                _require(baseline, "baseline")
                artifacts.append(
                    self._state_artifact(
                        writer, subject_ref, Phase.BASELINE, "capture-baseline", "EV-01", baseline
                    )
                )
                self._record_state(
                    observations,
                    writer,
                    run,
                    subject_ref,
                    Phase.BASELINE,
                    "capture-baseline",
                    baseline,
                )

                expires_at = self.clock.now() + timedelta(minutes=5)
                applied = self.adapters.fault.apply(
                    run_id=str(run.run_id),
                    subject=subject,
                    expires_at=expires_at,
                )
                _require(applied, "fault apply")
                run = Run.model_validate(
                    {**run.model_dump(mode="python"), "fault_ever_applied": True}
                )
                writer.run = run
                writer.write_json("run.json", run.model_dump(mode="json"))
                writer.append_jsonl("faults.jsonl", applied.data)
                artifacts.append(
                    self._json_artifact(
                        writer,
                        subject_ref,
                        Phase.INJECTED,
                        "apply-reporting-fault",
                        "EV-02",
                        "FAULT_RECEIPT",
                        applied,
                    )
                )
                self._observe(
                    observations,
                    writer,
                    run,
                    subject_ref,
                    Phase.INJECTED,
                    "apply-reporting-fault",
                    "fault.marker.applied",
                    True,
                    Source.FAULT,
                )

                triggered = self.adapters.seed.trigger(run_id=str(run.run_id), subject=subject)
                _require(triggered, "reporting trigger")
                effect = self.adapters.fault.probe_effect(
                    run_id=str(run.run_id),
                    subject=subject,
                    trigger=dict(triggered.data),
                )
                artifacts.append(
                    self._json_artifact(
                        writer,
                        subject_ref,
                        Phase.INJECTED,
                        "confirm-fault-effect",
                        "EV-03",
                        "FAULT_RECEIPT",
                        effect,
                    )
                )
                self._observe(
                    observations,
                    writer,
                    run,
                    subject_ref,
                    Phase.INJECTED,
                    "confirm-fault-effect",
                    "fault.effect.receipt_match",
                    effect.ok,
                    Source.FAULT,
                )

                report = self._poll_report(
                    writer, observations, artifacts, run, subject_ref, subject
                )
                _require(report, "report observation")

                browser = self.adapters.browser.capture_review(subject=subject)
                _require(browser, "browser capture")
                projection = dict(browser.data["projection"])
                artifacts.append(
                    writer.collect_json_artifact(
                        subject_ref=subject_ref,
                        phase=Phase.INJECTED,
                        step_id="observe-company-console",
                        attempt=1,
                        evidence_requirement_ids=("EV-04",),
                        artifact_type="BROWSER_PROJECTION",
                        source_locator={"route": projection["route"]},
                        content=projection,
                    )
                )
                screenshot = browser.data.get("screenshot_bytes", b"")
                artifacts.append(
                    writer.collect_binary_artifact(
                        subject_ref=subject_ref,
                        phase=Phase.INJECTED,
                        step_id="observe-company-console",
                        attempt=1,
                        evidence_requirement_ids=("EV-04",),
                        artifact_type="SCREENSHOT",
                        source_locator={"route": projection["route"]},
                        payload=bytes(screenshot) or b"CONTROLPROOF_SYNTHETIC_SCREENSHOT",
                        mime_type="image/png",
                        suffix="png",
                    )
                )
                self._observe(
                    observations,
                    writer,
                    run,
                    subject_ref,
                    Phase.INJECTED,
                    "observe-company-console",
                    "report.ui.ready_content_visible",
                    projection["ready_content_visible"],
                    Source.BROWSER,
                )
                self._observe(
                    observations,
                    writer,
                    run,
                    subject_ref,
                    Phase.INJECTED,
                    "observe-company-console",
                    "report.ui.status_class",
                    projection["status_class"],
                    Source.BROWSER,
                )

                decision = self.adapters.state.attempt_final_decision(subject=subject)
                _require(decision, "decision attempt")
                artifacts.append(
                    self._json_artifact(
                        writer,
                        subject_ref,
                        Phase.INJECTED,
                        "attempt-final-decision",
                        "EV-05",
                        "HTTP_EXCHANGE",
                        decision,
                    )
                )
                for key, field in (
                    ("decision.attempt.accepted", "accepted"),
                    ("decision.attempt.reason_present", "reason_present"),
                    ("decision.attempt.reason_code", "reason_code"),
                ):
                    self._observe_value(
                        observations,
                        writer,
                        run,
                        subject_ref,
                        Phase.INJECTED,
                        "attempt-final-decision",
                        key,
                        decision.data.get(field),
                        Source.HTTP,
                    )

                post = self.adapters.state.snapshot(subject=subject, phase="INJECTED")
                _require(post, "post-decision state")
                artifacts.append(
                    self._state_artifact(
                        writer,
                        subject_ref,
                        Phase.INJECTED,
                        "capture-post-decision-state",
                        "EV-06",
                        post,
                    )
                )
                self._record_state(
                    observations,
                    writer,
                    run,
                    subject_ref,
                    Phase.INJECTED,
                    "capture-post-decision-state",
                    post,
                )

                automatic = self._observe_automatic_window(
                    writer, observations, run, subject_ref, subject
                )
                artifacts.append(
                    self._state_artifact(
                        writer,
                        subject_ref,
                        Phase.INJECTED,
                        "observe-automatic-decision-window",
                        "EV-07",
                        automatic,
                    )
                )
        except BaseException as exc:  # noqa: BLE001 - restore must run for interrupts too
            execution_error = exc
        finally:
            try:
                if run.fault_ever_applied:
                    run = transition(run, RunState.RESTORING)
                    writer.run = run
                    writer.write_json("run.json", run.model_dump(mode="json"))
                    restore = self.adapters.fault.restore(run_id=str(run.run_id), subject=subject)
                    writer.append_jsonl("faults.jsonl", restore.data)
                    artifacts.append(
                        self._json_artifact(
                            writer,
                            subject_ref,
                            Phase.RECOVERED,
                            "restore-environment",
                            "EV-08",
                            "FAULT_RECEIPT",
                            restore,
                        )
                    )
                    self._observe(
                        observations,
                        writer,
                        run,
                        subject_ref,
                        Phase.RECOVERED,
                        "restore-environment",
                        "fault.environment_restore",
                        restore.data.get("environment_restore", "FAILED"),
                        Source.FAULT,
                    )
                    self._observe(
                        observations,
                        writer,
                        run,
                        subject_ref,
                        Phase.RECOVERED,
                        "restore-environment",
                        "report.processing_recovery",
                        restore.data.get("report_processing_recovery", "UNAVAILABLE"),
                        Source.HTTP,
                    )
                    restored = restore.ok
                    destination = (
                        RunState.COMPLETED
                        if restore.ok and execution_error is None
                        else RunState.ABORTED
                        if restore.ok
                        else RunState.RESTORE_FAILED
                    )
                    run = transition(run, destination)
                    if destination is RunState.RESTORE_FAILED:
                        self.blocks.block(readiness.target_id, subject_ref, run)
                elif run.state is RunState.RUNNING or run.state is RunState.PENDING:
                    run = transition(run, RunState.ABORTED)
                writer.run = run
                writer.write_json("run.json", run.model_dump(mode="json"))
            finally:
                if subject and restored:
                    teardown = self.adapters.seed.teardown(run_id=str(run.run_id), subject=subject)
                    if not teardown.ok:
                        execution_error = execution_error or RuntimeError(
                            "synthetic fixture teardown failed"
                        )
                self.adapters.browser.close()

        if not (writer.directory / "subjects.json").exists():
            writer.write_json("subjects.json", [])
        for name in ("faults.jsonl", "observations.jsonl"):
            if not (writer.directory / name).exists():
                writer.write_bytes(name, b"", "application/x-ndjson")
        judgement = judge_h03(run, observations, artifacts)
        writer.write_json(
            "assertions.json",
            [result.model_dump(mode="json") for result in judgement.assertion_results],
        )
        writer.write_json("judgement.json", judgement.model_dump(mode="json"))
        if retest_records is not None:
            writer.write_json("retest-link.json", retest_records["link"], redact_first=False)
            writer.write_json("retest-diff.json", retest_records["diff"], redact_first=False)
        writer.seal()
        if execution_error and not run.fault_ever_applied:
            # The sealed ABORTED bundle is the result; do not erase the diagnostic by raising.
            pass
        return run, judgement, writer.directory

    def _poll_report(self, writer, observations, artifacts, run, subject_ref, subject):
        attempts = int(
            self.scenario.timing_policy.injected_deadline_seconds
            / self.scenario.timing_policy.poll_seconds
        )
        last = None
        for attempt in range(1, attempts + 1):
            last = self.adapters.state.report_status(subject=subject)
            artifacts.append(
                writer.collect_json_artifact(
                    subject_ref=subject_ref,
                    phase=Phase.INJECTED,
                    step_id="observe-report",
                    attempt=attempt,
                    evidence_requirement_ids=("EV-03",),
                    artifact_type="HTTP_EXCHANGE",
                    source_locator={"route": "/v1/interview-sessions/{session_id}/report"},
                    content=last.data,
                )
            )
            self._observe_value(
                observations,
                writer,
                run,
                subject_ref,
                Phase.INJECTED,
                "observe-report",
                "report.api.presence",
                last.data.get("presence"),
                Source.HTTP,
                attempt,
            )
            self._observe_value(
                observations,
                writer,
                run,
                subject_ref,
                Phase.INJECTED,
                "observe-report",
                "report.api.status",
                last.data.get("status"),
                Source.HTTP,
                attempt,
            )
            if attempt < attempts:
                self.clock.sleep(self.scenario.timing_policy.poll_seconds)
        return last

    def _observe_automatic_window(self, writer, observations, run, subject_ref, subject):
        attempts = int(
            self.scenario.timing_policy.automatic_decision_window_seconds
            / self.scenario.timing_policy.poll_seconds
        )
        last = None
        for attempt in range(1, attempts + 1):
            last = self.adapters.state.snapshot(subject=subject, phase="INJECTED")
            _require(last, "automatic-decision window")
            self._record_state(
                observations,
                writer,
                run,
                subject_ref,
                Phase.INJECTED,
                "observe-automatic-decision-window",
                last,
                attempt,
            )
            if attempt < attempts:
                self.clock.sleep(self.scenario.timing_policy.poll_seconds)
        return last

    def _state_artifact(self, writer, subject_ref, phase, step, evidence_id, result):
        return self._json_artifact(
            writer, subject_ref, phase, step, evidence_id, "STATE_SNAPSHOT", result
        )

    def _json_artifact(self, writer, subject_ref, phase, step, evidence_id, artifact_type, result):
        return writer.collect_json_artifact(
            subject_ref=subject_ref,
            phase=phase,
            step_id=step,
            attempt=1,
            evidence_requirement_ids=(evidence_id,),
            artifact_type=artifact_type,
            source_locator={"adapter_code": result.code},
            content={
                "ok": result.ok,
                "code": result.code,
                "data": dict(result.data),
                "detail": result.detail,
            },
        )

    def _record_state(self, observations, writer, run, subject_ref, phase, step, result, attempt=1):
        state = dict(result.data["state"])
        mapping = {
            "invitation.status": "invitation_status",
            "recruiting.stage_id": "recruiting_stage_id",
            "pipeline.row_version": "pipeline_row_version",
            "final_decision.count": "final_decision_count",
            "final_decision.latest_actor_type": "latest_final_decision_actor_type",
        }
        for key, field in mapping.items():
            self._observe_value(
                observations,
                writer,
                run,
                subject_ref,
                phase,
                step,
                key,
                state.get(field),
                Source.DB,
                attempt,
            )

    def _observe_value(
        self, observations, writer, run, subject_ref, phase, step, key, value, source, attempt=1
    ):
        presence = Presence.PRESENT if value is not None else Presence.ABSENT
        self._observe(
            observations,
            writer,
            run,
            subject_ref,
            phase,
            step,
            key,
            value,
            source,
            attempt,
            presence,
        )

    def _observe(
        self,
        observations,
        writer,
        run,
        subject_ref,
        phase,
        step,
        key,
        value,
        source,
        attempt=1,
        presence=Presence.PRESENT,
    ):
        observation = Observation(
            run_id=run.run_id,
            subject_ref=subject_ref,
            phase=phase,
            step_id=step,
            attempt=attempt,
            key=key,
            presence=presence,
            value=value if presence is Presence.PRESENT else None,
            source_type=source,
            source_ref=f"{run.target_id}:{step}",
            observed_at=self.clock.now(),
        )
        observations.append(observation)
        writer.append_jsonl("observations.jsonl", observation.model_dump(mode="json"))


def _require(result: AdapterResult | None, step: str) -> AdapterResult:
    if result is None or not result.ok:
        code = "NO_RESULT" if result is None else result.code
        raise RuntimeError(f"{step} failed: {code}")
    return result
