from __future__ import annotations

import hashlib
from datetime import timedelta
from uuid import uuid4

from engine.adapters.base import AdapterResult
from engine.adapters.whyyou.consent_fault import WhyYouConsentFaultAdapter
from engine.adapters.whyyou.n02_seed import WhyYouN02SeedAdapter
from engine.execution import ExecutionSession
from engine.lifecycle import RestoreBlockStore
from engine.models import (
    ConsentStateSnapshot,
    N02LaneId,
    Presence,
    ProtectedPathId,
    RunState,
    utcnow,
)
from tests.unit.test_execution_session import RecordingWriter


class _EmptyResult:
    """Real connections return rows; the FK catalog query has nothing to report here."""

    def mappings(self):
        return self

    def all(self):
        return []

class _Transaction:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, _statement, _params=None):
        return _EmptyResult()


class _AbsentConsent:
    def read_state(self, *, subject, phase, step_id):
        return ConsentStateSnapshot(
            run_id=subject["run_id"],
            lane_id=subject["lane_id"],
            subject_ref=subject["subject_ref"],
            phase=phase,
            step_id=step_id,
            attempt=1,
            invitation_status="identity_verified",
            invitation_row_version=1,
            captured_at=utcnow(),
            source_status=Presence.ABSENT,
            state_digest="a" * 64,
        )


def _safe_restore() -> AdapterResult:
    return AdapterResult(
        True,
        "CONSENT_FAULT_RESTORED",
        {
            "marker_removed": True,
            "consumed_token_removed": True,
            "hook_inactive": True,
            "failed_request_effects_zero": True,
            "manual_cleanup_required": False,
        },
    )


def test_owned_marker_and_one_shot_token_are_removed_only_after_zero_state_probe(
    settings,
) -> None:
    subject = {
        "run_id": str(uuid4()),
        "lane_id": N02LaneId.CONSENT_FAULT_RECOVERY.value,
        "subject_ref": "synthetic-fault-restore",
        "invitation_id": str(uuid4()),
        "applicant_id": str(uuid4()),
    }
    adapter = WhyYouConsentFaultAdapter(
        settings,
        consent_adapter=_AbsentConsent(),
    )
    applied = adapter.apply_consent_fault(
        run_id=subject["run_id"],
        subject=subject,
        expires_at=utcnow() + timedelta(minutes=5),
    )
    marker = settings.fault_root / "consent" / f"{subject['invitation_id']}.json"
    token = (
        settings.fault_root
        / "consumed"
        / f"{subject['run_id']}-{subject['invitation_id']}.consent"
    )
    token.parent.mkdir(parents=True)
    token.write_text("consumed", encoding="utf-8")

    restored = adapter.restore_consent_fault(
        run_id=subject["run_id"], subject=subject
    )

    assert applied.ok and restored.ok
    assert not marker.exists() and not token.exists()
    assert restored.data["hook_inactive"] is True
    assert restored.data["failed_request_effects_zero"] is True


def test_each_probe_overlay_is_removed_back_to_the_original_seed_digest(settings) -> None:
    adapter = WhyYouN02SeedAdapter(
        settings,
        transaction_factory=lambda: _Transaction(),
    )
    run_id = uuid4()
    lanes = adapter.seed_lanes(run_id=str(run_id))
    lane = next(
        item for item in lanes if item.lane_id is N02LaneId.CONSENT_FAULT_RECOVERY
    )
    subject = adapter.subject_for(
        run_id=str(run_id), lane_id=N02LaneId.CONSENT_FAULT_RECOVERY
    )
    restored_digests = set()
    for path in ProtectedPathId:
        applied = adapter.apply_probe_overlay(subject=subject, path_id=path.value)
        removed = adapter.remove_probe_overlay(subject=subject, path_id=path.value)
        assert applied.ok and removed.ok
        restored_digests.add(removed.data["seed_digest_restored"])
    teardown = adapter.teardown_lanes(run_id=str(run_id), lanes=lanes)
    assert teardown.ok
    assert restored_digests == {teardown.data["seed_digest"]}
    assert lane.subject_ref == subject["subject_ref"]


def test_n02_restore_checkpoints_and_manual_cleanup_block_are_durable(
    tmp_path, run_factory
) -> None:
    run = run_factory()
    writer = RecordingWriter(run)
    session = ExecutionSession(tmp_path, run, "candidate-n02", writer=writer)
    unsafe = AdapterResult(
        False,
        "CONSENT_FAULT_FOREIGN_MARKER",
        {"manual_cleanup_required": True},
    )

    outcome = session.execute(
        lambda active: active.mark_fault_applied(),
        restore=lambda: session.recover_n02_consent_fault(lambda: unsafe),
    )
    assert outcome.run.state is RunState.RESTORE_FAILED
    assert [row["outcome"] for row in writer.checkpoints] == ["STARTED", "FAILED"]
    receipts = [
        value
        for path, value in writer.appended
        if path == "n02-recovery-receipts.jsonl"
    ]
    assert len(receipts) == 1 and receipts[0]["restore_safe"] is False

    blocks = RestoreBlockStore(tmp_path)
    assert blocks.blocked(run.target_id, "candidate-n02")
    later_run = run_factory()
    later = ExecutionSession(
        tmp_path,
        later_run,
        "candidate-n02",
        writer=RecordingWriter(later_run),
    )
    try:
        later.execute(lambda _active: None, restore=lambda: True)
    except RuntimeError as exc:
        assert "blocked" in str(exc)
    else:
        raise AssertionError("unsafe N-02 restore must block a later fault Run")

    evidence_digest = hashlib.sha256(b"operator-verified-cleanup").hexdigest()
    blocks.confirm_cleanup(
        run.target_id,
        "candidate-n02",
        evidence_sha256=evidence_digest,
        target_safe=True,
    )
    assert not blocks.blocked(run.target_id, "candidate-n02")


def test_verified_n02_restore_persists_passed_checkpoint(tmp_path, run_factory) -> None:
    run = run_factory()
    writer = RecordingWriter(run)
    session = ExecutionSession(tmp_path, run, "candidate-n02-safe", writer=writer)
    outcome = session.execute(
        lambda active: active.mark_fault_applied(),
        restore=lambda: session.recover_n02_consent_fault(_safe_restore),
    )
    assert outcome.run.state is RunState.COMPLETED
    assert [row["outcome"] for row in writer.checkpoints] == ["STARTED", "PASSED"]
