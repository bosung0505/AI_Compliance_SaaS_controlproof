from __future__ import annotations

from dataclasses import dataclass, field

from engine.execution import ExecutionSession
from engine.models import RunState


@dataclass
class RecordingWriter:
    run: object
    checkpoints: list[dict] = field(default_factory=list)
    sealed: bool = False

    def write_json(self, _path, _value, **_kwargs):
        return None

    def append_jsonl(self, path, value):
        if path == "checkpoints.jsonl":
            self.checkpoints.append(value)

    def seal(self):
        self.sealed = True
        return {"sealed": True}


def test_faulted_exception_restores_and_seals(tmp_path, run_factory):
    writer = RecordingWriter(run_factory())
    restored = []
    session = ExecutionSession(tmp_path, writer.run, "candidate-01", writer=writer)

    def work(active):
        active.mark_fault_applied()
        active.checkpoint("INJECTED", "fault", "STARTED")
        raise RuntimeError("synthetic")

    outcome = session.execute(work, restore=lambda: restored.append(True) or True)
    assert restored == [True]
    assert outcome.run.state is RunState.ABORTED
    assert writer.sealed
    assert [item["sequence"] for item in writer.checkpoints] == [1]


def test_restore_failure_blocks_later_session(tmp_path, run_factory):
    writer = RecordingWriter(run_factory())
    first = ExecutionSession(tmp_path, writer.run, "candidate-01", writer=writer)
    outcome = first.execute(lambda active: active.mark_fault_applied(), restore=lambda: False)
    assert outcome.run.state is RunState.RESTORE_FAILED

    second = ExecutionSession(tmp_path, run_factory(), "candidate-01", writer=RecordingWriter(run_factory()))
    try:
        second.execute(lambda _active: None, restore=lambda: True)
    except RuntimeError as exc:
        assert "blocked" in str(exc)
    else:
        raise AssertionError("restore block must prevent a later fault session")
