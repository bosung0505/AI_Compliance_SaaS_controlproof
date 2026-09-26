from engine.lifecycle import RestoreBlockStore, TargetSubjectLock, transition
from engine.models import RunState


def test_permitted_lifecycle_and_terminal_immutability(run_factory):
    pending = run_factory()
    running = transition(pending, RunState.RUNNING)
    restoring = transition(running, RunState.RESTORING, fault_applied=True)
    completed = transition(restoring, RunState.COMPLETED)
    assert completed.ended_at is not None
    try:
        transition(completed, RunState.RUNNING)
    except ValueError:
        pass
    else:
        raise AssertionError("terminal state accepted a transition")


def test_fault_applied_run_cannot_abort_directly(run_factory):
    running = transition(run_factory(), RunState.RUNNING)
    try:
        transition(running, RunState.ABORTED, fault_applied=True)
    except ValueError as exc:
        assert "RESTORING" in str(exc)
    else:
        raise AssertionError("fault-applied Run aborted without restore")


def test_target_subject_lock_and_restore_block(deterministic_environment, run_factory):
    root = deterministic_environment["run_root"]
    with TargetSubjectLock(root, "whyyou-local", "candidate-01"):
        try:
            TargetSubjectLock(root, "whyyou-local", "candidate-01").acquire()
        except RuntimeError:
            pass
        else:
            raise AssertionError("concurrent lock unexpectedly succeeded")
    running = transition(run_factory(), RunState.RUNNING)
    restoring = transition(running, RunState.RESTORING, fault_applied=True)
    failed = transition(restoring, RunState.RESTORE_FAILED)
    blocks = RestoreBlockStore(root)
    blocks.block("whyyou-local", "candidate-01", failed)
    assert blocks.blocked("whyyou-local", "candidate-01")
    record = blocks.confirm_cleanup(
        "whyyou-local",
        "candidate-01",
        evidence_sha256="a" * 64,
        target_safe=True,
    )
    assert record["blocked_run_id"] == str(failed.run_id)
    assert not blocks.blocked("whyyou-local", "candidate-01")
