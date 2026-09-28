"""Shared execution lifecycle for Spec 002 profile executors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from engine.lifecycle import RestoreBlockStore, TargetSubjectLock, transition
from engine.models import Phase, Run, RunState, utcnow


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
