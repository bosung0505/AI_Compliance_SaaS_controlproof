"""Shared execution lifecycle for Spec 002 profile executors."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from engine.lifecycle import RestoreBlockStore, TargetSubjectLock, transition
from engine.models import (
    BusinessEffectSnapshot,
    Phase,
    Presence,
    RedriveReceipt,
    Run,
    RunState,
    utcnow,
)


@dataclass(frozen=True, slots=True)
class ReportingRecoveryOutcome:
    restore: Any
    redrive: RedriveReceipt | None
    recovered_effects: tuple[BusinessEffectSnapshot, ...]
    restore_safe: bool

    def __bool__(self) -> bool:
        """Let ExecutionSession map recovery uncertainty to RESTORE_FAILED."""

        return self.restore_safe


def coordinate_reporting_recovery(
    *,
    fault: Any,
    redrive: Any,
    effects: Any | None,
    run_id: Any,
    source_event_id: Any,
    logical_operation_id: Any,
    subject: Mapping[str, Any],
    clock: Any,
    poll_seconds: float,
    deadline_seconds: float,
    append_receipt: Callable[[str, Any], None] | None = None,
) -> ReportingRecoveryOutcome:
    """Restore the marker first, redrive one selected message, then poll its effects."""

    restored = fault.restore(run_id=str(run_id), subject=dict(subject))
    safe = bool(
        restored.ok
        and restored.data.get("marker_inactive") is True
        and restored.data.get("worker_healthy") is True
    )
    if not safe:
        return ReportingRecoveryOutcome(restored, None, (), False)

    receipt = redrive.redrive(source_event_id=str(source_event_id))
    if append_receipt is not None:
        append_receipt("redrive-receipts.jsonl", receipt.model_dump(mode="json"))
    if not receipt.send_succeeded or not receipt.delete_succeeded:
        return ReportingRecoveryOutcome(restored, receipt, (), False)
    if effects is None:
        return ReportingRecoveryOutcome(restored, receipt, (), True)

    iterations = max(1, int(deadline_seconds / poll_seconds))
    latest: tuple[BusinessEffectSnapshot, ...] = ()
    for index in range(iterations):
        latest = effects.read_reporting_effects(
            subject=subject,
            phase=Phase.RECOVERED,
            run_id=run_id,
            logical_operation_id=logical_operation_id,
            source_event_id=source_event_id,
            step_id="recovered-reporting-effects",
            attempt=index + 1,
        )
        if _reporting_result_observed(latest):
            break
        if index + 1 < iterations:
            clock.sleep(poll_seconds)
    return ReportingRecoveryOutcome(restored, receipt, latest, True)


def _reporting_result_observed(
    snapshots: tuple[BusinessEffectSnapshot, ...],
) -> bool:
    if not snapshots:
        return False
    snapshot = snapshots[0]
    return (
        snapshot.source_status is Presence.UNAVAILABLE
        or bool(snapshot.effects.get("logical_report_ids"))
    )


class SessionWriter(Protocol):
    run: Run

    def write_json(self, relative_path: str, value: Any, **kwargs: Any) -> Any: ...

    def append_jsonl(self, relative_path: str, value: Any) -> None: ...

    def seal(self) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class SessionOutcome:
    run: Run
    error: BaseException | None
    restore_success: bool | None
    manifest: dict[str, Any]


class ExecutionSession:
    """Own lock, checkpoint, mandatory restore, terminal state and sealing order.

    Profile executors own scenario actions. This class owns the safety envelope around them.
    It intentionally does not create partial scenario verdicts.
    """

    def __init__(
        self,
        run_root: Path,
        run: Run,
        subject_ref: str,
        *,
        writer: SessionWriter,
    ) -> None:
        self.run_root = run_root.resolve()
        self.run = run
        self.subject_ref = subject_ref
        self.writer = writer
        self.blocks = RestoreBlockStore(self.run_root)
        self._checkpoint_sequence = 0

    def _persist_run(self) -> None:
        self.writer.run = self.run
        self.writer.write_json("run.json", self.run.model_dump(mode="json"))

    def checkpoint(
        self,
        phase: Phase | str,
        step_id: str,
        outcome: str,
        *,
        attempt: int = 1,
        error_code: str | None = None,
    ) -> None:
        self._checkpoint_sequence += 1
        active_phase = phase if isinstance(phase, Phase) else Phase(phase)
        self.writer.append_jsonl(
            "checkpoints.jsonl",
            {
                "schema_version": "controlproof.checkpoint.v1",
                "run_id": str(self.run.run_id),
                "subject_ref": self.subject_ref,
                "phase": active_phase.value,
                "step_id": step_id,
                "attempt": attempt,
                "sequence": self._checkpoint_sequence,
                "outcome": outcome,
                "error_code": error_code,
                "recorded_at": utcnow().isoformat(),
            },
        )

    def mark_fault_applied(self) -> None:
        if self.run.fault_ever_applied:
            return
        self.run = Run.model_validate(
            {**self.run.model_dump(mode="python"), "fault_ever_applied": True}
        )
        self._persist_run()

    def recover_reporting(self, **kwargs: Any) -> ReportingRecoveryOutcome:
        """Run shared recovery while durably appending every mutation receipt."""

        return coordinate_reporting_recovery(
            **kwargs,
            append_receipt=self.writer.append_jsonl,
        )

    def recover_n02_consent_fault(
        self, restore: Callable[[], Any]
    ) -> bool:
        """Persist the N-02 restore boundary and return only verified-safe recovery."""

        step_id = "n02-consent-fault-restore"
        self.checkpoint(Phase.RECOVERED, step_id, "STARTED")
        try:
            result = restore()
        except BaseException as exc:
            self.checkpoint(
                Phase.RECOVERED,
                step_id,
                "FAILED",
                error_code=type(exc).__name__.upper(),
            )
            raise
        data = dict(getattr(result, "data", {}))
        safe = bool(
            getattr(result, "ok", False)
            and data.get("marker_removed") is True
            and data.get("consumed_token_removed") is True
            and data.get("hook_inactive") is True
            and data.get("failed_request_effects_zero") is True
            and data.get("manual_cleanup_required") is False
        )
        self.writer.append_jsonl(
            "n02-recovery-receipts.jsonl",
            {
                "schema_version": "controlproof.n02-restore-receipt.v1",
                "run_id": str(self.run.run_id),
                "subject_ref": self.subject_ref,
                "code": str(getattr(result, "code", "N02_RESTORE_RESULT_INVALID")),
                "restore_safe": safe,
                "marker_removed": data.get("marker_removed"),
                "consumed_token_removed": data.get("consumed_token_removed"),
                "hook_inactive": data.get("hook_inactive"),
                "failed_request_effects_zero": data.get(
                    "failed_request_effects_zero"
                ),
                "manual_cleanup_required": data.get("manual_cleanup_required"),
                "recorded_at": utcnow().isoformat(),
            },
        )
        self.checkpoint(
            Phase.RECOVERED,
            step_id,
            "PASSED" if safe else "FAILED",
            error_code=None if safe else str(getattr(result, "code", "N02_RESTORE_UNSAFE")),
        )
        return safe

    def execute(
        self,
        work: Callable[[ExecutionSession], Any],
        *,
        restore: Callable[[], bool],
        finalize: Callable[[SessionOutcome], None] | None = None,
    ) -> SessionOutcome:
        if self.blocks.blocked(self.run.target_id, self.subject_ref):
            raise RuntimeError("target+subject is blocked after a restore failure")
        error: BaseException | None = None
        restore_success: bool | None = None
        lock = TargetSubjectLock(self.run_root, self.run.target_id, self.subject_ref)
        with lock:
            self.run = transition(self.run, RunState.RUNNING)
            self._persist_run()
            try:
                work(self)
            except BaseException as exc:  # noqa: BLE001 - restore must include interrupts
                error = exc
            finally:
                if self.run.fault_ever_applied:
                    self.run = transition(self.run, RunState.RESTORING)
                    self._persist_run()
                    try:
                        restore_success = bool(restore())
                    except BaseException as exc:  # noqa: BLE001 - preserve restore diagnostic
                        restore_success = False
                        error = error or exc
                    destination = (
                        RunState.COMPLETED
                        if restore_success and error is None
                        else RunState.ABORTED
                        if restore_success
                        else RunState.RESTORE_FAILED
                    )
                    self.run = transition(self.run, destination)
                    if destination is RunState.RESTORE_FAILED:
                        self.blocks.block(self.run.target_id, self.subject_ref, self.run)
                else:
                    error = error or RuntimeError("fault profile ended before applying its fault")
                    self.run = transition(self.run, RunState.ABORTED)
                self._persist_run()

        provisional = SessionOutcome(
            run=self.run,
            error=error,
            restore_success=restore_success,
            manifest={},
        )
        if finalize is not None:
            finalize(provisional)
        manifest = self.writer.seal()
        return SessionOutcome(
            run=self.run,
            error=error,
            restore_success=restore_success,
            manifest=manifest,
        )
