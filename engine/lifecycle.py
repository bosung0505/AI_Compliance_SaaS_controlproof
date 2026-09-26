"""Run lifecycle persistence, target/subject locks, and restore-failure blocks."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Self

from engine.models import TERMINAL_RUN_STATES, Run, RunState, canonical_json_bytes, utcnow

TRANSITIONS: dict[RunState, frozenset[RunState]] = {
    RunState.PENDING: frozenset({RunState.RUNNING, RunState.ABORTED}),
    RunState.RUNNING: frozenset({RunState.RESTORING, RunState.ABORTED}),
    RunState.RESTORING: frozenset({RunState.COMPLETED, RunState.ABORTED, RunState.RESTORE_FAILED}),
    RunState.COMPLETED: frozenset(),
    RunState.ABORTED: frozenset(),
    RunState.RESTORE_FAILED: frozenset(),
}


def transition(run: Run, destination: RunState, *, fault_applied: bool | None = None) -> Run:
    if destination not in TRANSITIONS[run.state]:
        raise ValueError(f"invalid Run transition: {run.state} -> {destination}")
    ever_applied = run.fault_ever_applied or bool(fault_applied)
    if run.state is RunState.RUNNING and destination is RunState.ABORTED and ever_applied:
        raise ValueError("fault-applied Run must enter RESTORING before ABORTED")
    updates: dict[str, Any] = {"state": destination, "fault_ever_applied": ever_applied}
    if destination is RunState.RUNNING:
        updates["started_at"] = utcnow()
    if destination in TERMINAL_RUN_STATES:
        updates["ended_at"] = utcnow()
    if destination is RunState.RESTORE_FAILED:
        updates["manual_cleanup_required"] = True
    payload = run.model_dump(mode="python")
    payload.update(updates)
    return Run.model_validate(payload)


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


class RunRepository:
    def __init__(self, run_root: Path) -> None:
        self.run_root = run_root.resolve()
        self.run_root.mkdir(parents=True, exist_ok=True)

    def directory(self, run_id) -> Path:
        return self.run_root / str(run_id)

    def create(self, run: Run) -> Path:
        directory = self.directory(run.run_id)
        directory.mkdir(parents=False, exist_ok=False)
        self.save(run)
        return directory

    def save(self, run: Run) -> None:
        path = self.directory(run.run_id) / "run.json"
        if (path.parent / "manifest.json").exists():
            raise PermissionError("sealed Run is immutable")
        atomic_write(path, canonical_json_bytes(run.model_dump(mode="json")))

    def load(self, run_id) -> Run:
        data = json.loads((self.directory(run_id) / "run.json").read_text(encoding="utf-8"))
        return Run.model_validate(data)

    def move(self, run: Run, destination: RunState, *, fault_applied: bool | None = None) -> Run:
        updated = transition(run, destination, fault_applied=fault_applied)
        self.save(updated)
        return updated


def _safe_component(value: str) -> str:
    safe = "".join(
        character if character.isalnum() or character in "-_" else "_" for character in value
    )
    if not safe:
        raise ValueError("lock component cannot be empty")
    return safe


class TargetSubjectLock:
    """Single-host lock using exclusive file creation."""

    def __init__(self, root: Path, target_id: str, subject_ref: str) -> None:
        self.path = (
            root.resolve()
            / "locks"
            / f"{_safe_component(target_id)}--{_safe_component(subject_ref)}.lock"
        )
        self._fd: int | None = None

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise RuntimeError("another Run owns the target+subject lock") from exc
        os.write(self._fd, f"pid={os.getpid()}".encode())
        os.fsync(self._fd)

    def release(self) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
        self.path.unlink(missing_ok=True)

    def __enter__(self) -> Self:
        self.acquire()
        return self

    def __exit__(self, *_args) -> None:
        self.release()


class RestoreBlockStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve() / "blocks"

    def path_for(self, target_id: str, subject_ref: str) -> Path:
        return self.root / f"{_safe_component(target_id)}--{_safe_component(subject_ref)}.json"

    def blocked(self, target_id: str, subject_ref: str) -> bool:
        return self.path_for(target_id, subject_ref).exists()

    def block(self, target_id: str, subject_ref: str, run: Run) -> Path:
        payload = {
            "schema_version": "controlproof.restore-block.v1",
            "target_id": target_id,
            "subject_ref": subject_ref,
            "run_id": str(run.run_id),
            "created_at": utcnow().isoformat(),
        }
        path = self.path_for(target_id, subject_ref)
        atomic_write(path, canonical_json_bytes(payload))
        return path

    def confirm_cleanup(
        self,
        target_id: str,
        subject_ref: str,
        *,
        evidence_sha256: str,
        target_safe: bool,
    ) -> dict[str, Any]:
        path = self.path_for(target_id, subject_ref)
        if not path.exists():
            raise FileNotFoundError("no restore block exists")
        if not target_safe:
            raise RuntimeError("target safety probe did not pass")
        previous = json.loads(path.read_text(encoding="utf-8"))
        record = {
            "schema_version": "controlproof.cleanup-confirmation.v1",
            "target_id": target_id,
            "subject_ref": subject_ref,
            "blocked_run_id": previous["run_id"],
            "evidence_sha256": evidence_sha256,
            "confirmed_at": utcnow().isoformat(),
        }
        maintenance = self.root / "maintenance" / f"{previous['run_id']}.json"
        atomic_write(maintenance, canonical_json_bytes(record))
        path.unlink()
        return record
