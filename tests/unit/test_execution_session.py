from __future__ import annotations

from dataclasses import dataclass, field

from engine.adapters.base import AdapterResult
from engine.execution import ExecutionSession
from engine.models import RunState
from tests.fixtures.spec002 import EVENT_ID, OPERATION_ID, redrive_receipt


@dataclass
class RecordingWriter:
    run: object
    checkpoints: list[dict] = field(default_factory=list)
    appended: list[tuple[str, dict]] = field(default_factory=list)
    sealed: bool = False

    def write_json(self, _path, _value, **_kwargs):
        return None

    def append_jsonl(self, path, value):
        self.appended.append((path, value))
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


def test_delete_uncertainty_persists_receipt_and_maps_to_restore_failed(
    tmp_path, run_factory
):
    writer = RecordingWriter(run_factory())
    session = ExecutionSession(tmp_path, writer.run, "candidate-01", writer=writer)

    class Fault:
        def restore(self, **_kwargs):
            return AdapterResult(
                True,
                "ENVIRONMENT_RESTORED",
                {"marker_inactive": True, "worker_healthy": True},
            )

    class Redrive:
        def redrive(self, **_kwargs):
            return redrive_receipt(delete_succeeded=False)

    class Clock:
        def sleep(self, _seconds):
            return None

    def work(active):
        active.mark_fault_applied()

    def restore():
        return session.recover_reporting(
            fault=Fault(),
            redrive=Redrive(),
            effects=None,
            run_id=session.run.run_id,
            source_event_id=EVENT_ID,
            logical_operation_id=OPERATION_ID,
            subject={"subject_ref": "candidate-01"},
            clock=Clock(),
            poll_seconds=1,
            deadline_seconds=1,
        )

    outcome = session.execute(work, restore=restore)

    assert outcome.run.state is RunState.RESTORE_FAILED
    receipt_rows = [item for item in writer.appended if item[0] == "redrive-receipts.jsonl"]
    assert len(receipt_rows) == 1
    assert receipt_rows[0][1]["send_succeeded"] is True
    assert receipt_rows[0][1]["delete_succeeded"] is False
