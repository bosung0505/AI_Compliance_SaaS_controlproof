from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from engine.models import (
    AssertionStatus,
    ComparatorKind,
    ImplementationStatus,
    InconclusiveReason,
    Judgement,
    Phase,
    Presence,
    ReadinessStatus,
    RunState,
    TargetSnapshot,
    TargetSourceKind,
    Verdict,
)


def test_contract_enum_values_are_exact():
    assert {item.value for item in ReadinessStatus} == {
        "READY",
        "RUNNER_NOT_READY",
        "ACCESS_BLOCKED",
        "NO_TEST_TARGET",
    }
    assert {item.value for item in RunState} == {
        "PENDING",
        "RUNNING",
        "RESTORING",
        "COMPLETED",
        "ABORTED",
        "RESTORE_FAILED",
    }
    assert {item.value for item in Verdict} == {"PASS", "FAIL", "INCONCLUSIVE", "NOT_RUN"}
    assert {item.value for item in InconclusiveReason} == {
        "NO_TEST_TARGET",
        "ACCESS_LIMITED",
        "INSUFFICIENT_EVIDENCE",
        "EVIDENCE_CONFLICT",
    }
    assert {item.value for item in Phase} == {"BASELINE", "INJECTED", "RECOVERED"}
    assert {item.value for item in Presence} == {"PRESENT", "ABSENT", "UNAVAILABLE"}
    assert {item.value for item in AssertionStatus} == {"PASS", "FAIL", "INCONCLUSIVE"}
    assert {item.value for item in ImplementationStatus} == {
        "NOT_IMPLEMENTED",
        "PARTIAL",
        "IMPLEMENTED",
    }
    assert {item.value for item in ComparatorKind} == {"EXACT", "ABSOLUTE_TOLERANCE"}
    assert {item.value for item in TargetSourceKind} == {
        "GIT_WORKTREE",
        "CONTAINER_IMAGE",
        "GIT_AND_CONTAINER",
    }


def test_created_run_requires_implemented(run_factory):
    with pytest.raises(ValidationError, match="IMPLEMENTED"):
        run_factory(implementation_status=ImplementationStatus.PARTIAL)


def test_not_run_cannot_be_persisted(run_factory):
    run = run_factory()
    with pytest.raises(ValidationError, match="NOT_RUN"):
        Judgement(
            run_id=run.run_id,
            scenario_id="H-03",
            verdict=Verdict.NOT_RUN,
            summary="not executed",
        )


def test_target_snapshot_digest_excludes_capture_time():
    common = {
        "target_id": "whyyou-local",
        "source_kind": TargetSourceKind.GIT_WORKTREE,
        "git_commit_sha": "a" * 40,
        "git_dirty": False,
        "openapi_digest": "b" * 64,
        "schema_migration_head": "head",
        "schema_signature_digest": "c" * 64,
        "model_fixture_id": "h03-report-v1",
        "model_fixture_digest": "d" * 64,
    }
    first = TargetSnapshot(**common, captured_at=datetime(2026, 1, 1, tzinfo=UTC))
    second = TargetSnapshot(**common, captured_at=datetime(2026, 2, 1, tzinfo=UTC))
    assert first.target_version == second.target_version


def test_dirty_snapshot_requires_diagnostic_digest():
    with pytest.raises(ValidationError, match="git_diff_digest"):
        TargetSnapshot(
            target_id="whyyou-local",
            source_kind=TargetSourceKind.GIT_WORKTREE,
            git_commit_sha="a" * 40,
            git_dirty=True,
            openapi_digest="b" * 64,
            schema_migration_head="head",
            schema_signature_digest="c" * 64,
            model_fixture_id="h03-report-v1",
            model_fixture_digest="d" * 64,
        )
